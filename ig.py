"""Instagram public profile fetcher (via fwdproxy) with on-disk cache."""

import json
import os
import re
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "data", "profiles")
os.makedirs(CACHE, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
MIN_INTERVAL = float(os.environ.get("IG_INTERVAL", "3"))
_last = [0.0]

MENTION_RE = re.compile(r"@([A-Za-z0-9._]{2,30})")


def _get(username):
    url = (
        "https://www.instagram.com/api/v1/users/web_profile_info/?username="
        + username
    )
    # curl over HTTP/2 is required: IG answers 429 to urllib's HTTP/1.1 requests.
    cmd = [
        "curl", "-s", "--http2", "-x", "fwdproxy:8080", "--max-time", "30",
        "-A", UA, "-H", "x-ig-app-id: 936619743392459",
        "-w", "\n%{http_code}", url,
    ]
    backoff = 60
    for _ in range(6):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        body, _, code = out.rpartition("\n")
        if code == "404":
            return None
        if code == "200":
            try:
                return json.loads(body).get("data", {}).get("user")
            except json.JSONDecodeError:
                pass
        print(f"  HTTP {code} for {username}: {body[:120]!r}; sleeping {backoff}s")
        time.sleep(backoff)
        backoff = min(backoff * 2, 600)
    raise RuntimeError(f"giving up on {username}")


def _slim(u):
    posts = []
    for e in u["edge_owner_to_timeline_media"]["edges"]:
        n = e["node"]
        caps = n["edge_media_to_caption"]["edges"]
        cap = caps[0]["node"]["text"] if caps else ""
        tagged = [
            t["node"]["user"]["username"]
            for t in n.get("edge_media_to_tagged_user", {}).get("edges", [])
        ]
        coauthors = [c["username"] for c in n.get("coauthor_producers", []) or []]
        posts.append(
            {
                "shortcode": n["shortcode"],
                "ts": n.get("taken_at_timestamp"),
                "caption": cap,
                "tagged": tagged,
                "coauthors": coauthors,
                "mentions": sorted(
                    {m.lower().rstrip(".") for m in MENTION_RE.findall(cap)}
                ),
                "location": (n.get("location") or {}).get("name"),
            }
        )
    addr = u.get("business_address_json")
    return {
        "username": u["username"],
        "id": u["id"],
        "full_name": u.get("full_name"),
        "biography": u.get("biography"),
        "external_url": u.get("external_url"),
        "followers": u["edge_followed_by"]["count"],
        "following": u["edge_follow"]["count"],
        "media_count": u["edge_owner_to_timeline_media"]["count"],
        "is_business": u.get("is_business_account"),
        "is_verified": u.get("is_verified"),
        "is_private": u.get("is_private"),
        "category": u.get("category_name") or u.get("business_category_name"),
        "address": json.loads(addr) if addr else None,
        "profile_pic": u.get("profile_pic_url"),
        "posts": posts,
    }


def profile(username, refresh=False):
    """Return slim profile dict, or None if the account doesn't exist."""
    username = username.lower().strip().strip("@").rstrip(".")
    path = os.path.join(CACHE, username + ".json")
    if os.path.exists(path) and not refresh:
        with open(path) as f:
            return json.load(f)
    u = _get(username)
    slim = _slim(u) if u else None
    with open(path, "w") as f:
        json.dump(slim, f, ensure_ascii=False)
    return slim


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
