"""Web search (via fwdproxy) with an on-disk cache.

Uses Yahoo! JAPAN's results page: it serves Google's index to plain requests, where
Bing serves unrelated results, Google needs JavaScript and DuckDuckGo blocks the proxy.
Replies are cached in data/search_raw/ (gitignored), keyed by query.

usage: python3 -I search.py "query" ...    # print results, e.g. to find articles for harvest.py
"""

import hashlib
import html
import os
import re
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "search_raw")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
MIN_INTERVAL = float(os.environ.get("SEARCH_INTERVAL", "3"))
_last = [0.0]
RESULT_RE = re.compile(
    r'<a href="(https?://(?!search\.yahoo|[a-z.]*yahoo\.co\.jp)[^"]+)"[^>]*>(?:(?!</a>).)*?<h3[^>]*>(.*?)</h3>', re.S
)


def _fetch(query, n):
    url = f"https://search.yahoo.co.jp/search?p={urllib.parse.quote_plus(query)}&n={n}"
    backoff = 30
    for _ in range(4):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        out = subprocess.run(
            ["curl", "-s", "--http2", "-x", "fwdproxy:8080", "--max-time", "30", "-A", UA,
             "-H", "Accept-Language: zh-TW,zh;q=0.9,ja;q=0.5", "-w", "\n%{http_code}", url],
            capture_output=True, text=True, errors="replace",
        ).stdout
        body, _, code = out.rpartition("\n")
        if code == "200":
            return body
        print(f"  search HTTP {code} for {query!r}; sleeping {backoff}s", file=sys.stderr)
        time.sleep(backoff)
        backoff *= 2
    raise RuntimeError(f"search failed for {query!r}")


def results(query, n=20):
    """[{url, title}] for a query, best first."""
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, hashlib.sha1(f"{n}:{query}".encode()).hexdigest() + ".html")
    if os.path.exists(path):
        body = open(path).read()
    else:
        body = _fetch(query, n)
        open(path, "w").write(body)
    out, seen = [], set()
    for url, title in RESULT_RE.findall(body):
        url = html.unescape(url)
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip()})
    return out


if __name__ == "__main__":
    for q in sys.argv[1:]:
        print(f"# {q}")
        for r in results(q):
            print(f"{r['url']}\t{r['title']}")
