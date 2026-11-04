"""Instagram public profile fetcher (via fwdproxy) with on-disk cache.

Reads what a logged-out browser gets: the profile page embeds the profile and
its 12 latest posts, and the page's "accounts you may like" graphql query gives
the related accounts. (The old web_profile_info API answers 404 to logged-out
requests since 2026-11-03.) The logged-out page no longer shows tagged users or
business address/category, so those stay empty for newly fetched profiles.
"""

import json
import os
import re
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "data", "profiles")
os.makedirs(CACHE, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# Without the navigation headers IG serves an empty app shell instead of the profile.
PAGE_HEADERS = [
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: en-US,en;q=0.9",
    "-H", "Sec-Fetch-Dest: document", "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Sec-Fetch-Site: none", "-H", "Sec-Fetch-User: ?1",
    "-H", "Upgrade-Insecure-Requests: 1",
]
AYML_QUERY = "PolarisLoggedOutDesktopWWWAYMLQuery"
# Relay persisted-query id for AYML_QUERY, taken from instagram.com's own requests.
# If IG redeploys and it stops working, copy the new doc_id from the browser's network tab.
AYML_DOC_ID = "27840486182295820"
MIN_INTERVAL = float(os.environ.get("IG_INTERVAL", "3"))
_last = [0.0]
# A known-good account, used to tell "no such user" from IG blocking us.
CANARY = "celebread.acs"

MENTION_RE = re.compile(r"@([A-Za-z0-9._]{2,30})")
JSON_SCRIPT_RE = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)
LSD_RE = re.compile(r'"LSD",\[\],\{"token":"([^"]+)"')


def _curl(args):
    # curl over HTTP/2 is required: IG answers 429 to urllib's HTTP/1.1 requests.
    cmd = [
        "curl", "-s", "--http2", "-x", "fwdproxy:8080", "--max-time", "30",
        "-A", UA, "-w", "\n%{http_code}", *args,
    ]
    backoff = 60
    for _ in range(6):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        body, _, code = out.rpartition("\n")
        if code == "200":
            return body
        print(f"  HTTP {code} for {args[-1]}: {body[:120]!r}; sleeping {backoff}s")
        time.sleep(backoff)
        backoff = min(backoff * 2, 600)
    raise RuntimeError(f"giving up on {args[-1]}")


def _page(username, jar):
    return _curl(["-c", jar, *PAGE_HEADERS, f"https://www.instagram.com/{username}/"])


def _find_all(o, key, out):
    if isinstance(o, dict):
        if key in o:
            out.append(o[key])
        for v in o.values():
            _find_all(v, key, out)
    elif isinstance(o, list):
        for v in o:
            _find_all(v, key, out)
    return out


def _parse_page(html, username):
    """Slim profile dict from the page's embedded relay data, or None if the page
    has no profile (missing account, or IG served the bare app shell)."""
    found = []
    for block in JSON_SCRIPT_RE.findall(html):
        if "xig_user_by_username" in block:
            _find_all(json.loads(block), "xig_user_by_username", found)
    u = {}
    for part in found:
        if isinstance(part, dict):
            u.update(part)
    if "follower_count" not in u or u.get("username", "").lower() != username:
        return None
    posts = []
    for e in (u.get("polaris_ordered_timeline_connection") or {}).get("edges", []):
        n = e["node"]
        cap = (n.get("caption") or {}).get("text") or ""
        posts.append(
            {
                "shortcode": n["code"],
                "ts": n.get("taken_at"),
                "caption": cap,
                "tagged": [],
                "coauthors": [],
                "mentions": sorted(
                    {m.lower().rstrip(".") for m in MENTION_RE.findall(cap)}
                ),
                "location": None,
            }
        )
    links = [l.get("url") for l in u.get("bio_links") or [] if l.get("link_type") == "external" and l.get("url")]
    return {
        "username": u["username"],
        "id": u["pk"],
        "full_name": u.get("full_name"),
        "biography": u.get("biography"),
        "external_url": links[0] if links else None,
        "followers": u["follower_count"],
        "following": u.get("following_count"),
        "media_count": u.get("all_media_count"),
        "is_business": None,
        "is_verified": u.get("is_verified"),
        "is_private": u.get("is_private"),
        "category": None,
        "address": None,
        "profile_pic": u.get("profile_pic_url"),
        "posts": posts,
    }


def _related(user_id, html, jar, username):
    """Instagram's "accounts you may like" for a profile, via the page's own graphql query."""
    lsd = LSD_RE.search(html)
    if not lsd:
        raise RuntimeError(f"no LSD token on {username}'s page")
    body = _curl([
        "-b", jar,
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", f"X-FB-LSD: {lsd.group(1)}", "-H", "X-IG-App-ID: 936619743392459",
        "-H", f"X-FB-Friendly-Name: {AYML_QUERY}",
        "-H", "Origin: https://www.instagram.com", "-H", f"Referer: https://www.instagram.com/{username}/",
        "-H", "Sec-Fetch-Site: same-origin", "-H", "Sec-Fetch-Mode: cors", "-H", "Sec-Fetch-Dest: empty",
        "--data-urlencode", "av=0", "--data-urlencode", "__user=0", "--data-urlencode", "__a=1",
        "--data-urlencode", f"lsd={lsd.group(1)}",
        "--data-urlencode", "fb_api_caller_class=RelayModern",
        "--data-urlencode", f"fb_api_req_friendly_name={AYML_QUERY}",
        "--data-urlencode", "variables=" + json.dumps({"id": str(user_id)}),
        "--data-urlencode", "server_timestamps=true",
        "--data-urlencode", f"doc_id={AYML_DOC_ID}",
        "https://www.instagram.com/api/graphql",
    ])
    try:
        accounts = json.loads(body)["data"]["xig_user_by_igid_v2"]["ayml_logged_out"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise RuntimeError(f"unexpected related-accounts reply for {username}: {body[:200]!r}")
    return [a["username"].lower() for a in accounts or []]


def _get(username):
    with tempfile.TemporaryDirectory() as tmp:
        jar = os.path.join(tmp, "cookies")
        html = _page(username, jar)
        p = _parse_page(html, username)
        if p is None:
            # A missing account and a blocked request both get the bare app shell,
            # so only treat the account as missing if a known account still parses.
            if username != CANARY and _parse_page(_page(CANARY, jar), CANARY) is None:
                raise RuntimeError(
                    f"no profile data even for {CANARY}; not caching {username} as missing"
                )
            return None
        p["related"] = _related(p["id"], html, jar, username)
        return p


def profile(username, refresh=False, need_related=False):
    """Return slim profile dict, or None if the account doesn't exist.

    need_related adds related accounts to profiles cached before they were kept,
    keeping the cached posts (older entries still have tagged users and addresses).
    """
    username = username.lower().strip().strip("@").rstrip(".")
    path = os.path.join(CACHE, username + ".json")
    cached = None
    if os.path.exists(path) and not refresh:
        with open(path) as f:
            cached = json.load(f)
        if not (need_related and cached and "related" not in cached):
            return cached
    p = _get(username)
    if cached:
        cached["related"] = p["related"] if p else []
        p = cached
    with open(path, "w") as f:
        json.dump(p, f, ensure_ascii=False)
    return p


def outlinks(p):
    """Accounts this profile tags / mentions / co-authors with in recent posts."""
    out = {}
    for post in p["posts"]:
        for kind in ("tagged", "mentions", "coauthors"):
            for h in post[kind]:
                h = h.lower()
                if h != p["username"]:
                    out[h] = out.get(h, 0) + 1
    return out


def related(p):
    """Instagram's related-account suggestions (empty for profiles cached before they were kept)."""
    return [h for h in p.get("related") or [] if h != p["username"]]
