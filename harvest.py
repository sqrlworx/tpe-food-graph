"""Harvest Instagram handles from food articles (via fwdproxy).

Picks up profile links (instagram.com/<handle>), embedded posts (resolved to
their author via oEmbed) and @handles in the article text.

usage: python3 -I harvest.py projects/NAME/data/article_urls.txt > projects/NAME/data/harvest.json
"""

import json
import re
import subprocess
import sys

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
PROFILE_RE = re.compile(r"instagram\.com/([A-Za-z0-9._]{2,30})(?=[/?\"'#\s]|$)")
POST_RE = re.compile(r"instagram\.com/(?:[A-Za-z0-9._]+/)?(?:p|reel|tv)/([A-Za-z0-9_-]{6,})")
AT_RE = re.compile(r"(?<![A-Za-z0-9._%+-])@([A-Za-z0-9._]{3,30})")
NOT_HANDLES = {
    "p", "reel", "reels", "tv", "explore", "accounts", "stories", "about", "developer",
    "legal", "direct", "web", "static", "embed.js", "instagram", "gmail.com",
}


def curl(url):
    r = subprocess.run(
        ["curl", "-sL", "--http2", "-x", "fwdproxy:8080", "--max-time", "30", "-A", UA, url],
        capture_output=True, text=True, errors="replace",
    )
    return r.stdout


def clean(h):
    h = h.lower().rstrip(".")
    if h in NOT_HANDLES or h.endswith((".com", ".tw", ".jpg", ".png", ".js")) and "." in h[:-3]:
        return None
    return h


def harvest(url):
    html = curl(url)
    found = {}
    for h in PROFILE_RE.findall(html):
        if (h := clean(h)):
            found[h] = "link"
    for code in sorted(set(POST_RE.findall(html))):
        o = curl(f"https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/p/{code}/")
        try:
            author = json.loads(o).get("author_name")
        except json.JSONDecodeError:
            author = None
        if author and (h := clean(author)):
            found.setdefault(h, "embed")
    text = re.sub(r"<[^>]+>", " ", html)
    for h in AT_RE.findall(text):
        if (h := clean(h)):
            found.setdefault(h, "mention")
    return len(html), found


def main(path):
    out = {}
    for url in [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]:
        size, found = harvest(url)
        out[url] = found
        print(f"{size:>8} bytes  {len(found):>3} handles  {url[:90]}", file=sys.stderr)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
