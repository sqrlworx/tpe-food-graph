"""Instagram profiles through the official Graph API (Business Discovery).

The logged-out page (ig.py) shows a profile's latest posts (12, about 100 since mid-November
2026). Business Discovery returns a Business or Creator account's profile and the captions of
all its posts, as far back as we ask, read through the app user's own professional account. It
has no photo tags, no related accounts and nothing for personal accounts, and its captions lose
the @ of every mention ("@bonami_tw" arrives as "bonami_tw"), so "mentions" misses most of them.

Setup: a Meta app using the Instagram API with Facebook Login, an Instagram professional
account linked to a Facebook Page, and a long-lived user access token with PERMISSIONS: in the
Graph API Explorer choose Get User Access Token and select the Page and the Instagram account in
the login dialog, then extend the token in the Access Token Debugger. Save it alone in
~/.config/tpe-food-graph/ig_token (or the file $IG_TOKEN_FILE names), readable only by you.
Tokens last 60 days; whoami shows when this one expires.

Posts from the last SINCE_DAYS are kept, up to MAX_POSTS. Profiles are cached in the
gitignored data/profiles_api/, one file per handle in ig.py's shape (tagged, coauthors and
related stay empty); an account the API can't read (a personal one) is cached as
{"username", "unavailable"}. Requests go through fwdproxy, MIN_INTERVAL apart. The app's server
time per hour runs out first, after about 600 posts: the fetcher pauses when X-App-Usage nears
it and retries requests refused for it.

usage: python3 -I ig_api.py whoami                       the token's expiry and permissions, the account it reads as
       python3 -I ig_api.py fetch [--refresh] HANDLE ...  fetch accounts and compare them with the logged-out cache
       python3 -I ig_api.py crawl N                       fetch N more of the accounts the projects label blogger,
                                                          maker or venue: bloggers first, larger accounts first
"""

import argparse
import datetime
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ig  # noqa: E402
import project  # noqa: E402

CACHE = os.path.join(ROOT, "data", "profiles_api")
os.makedirs(CACHE, exist_ok=True)
TOKEN_FILE = os.environ.get("IG_TOKEN_FILE") or os.path.expanduser("~/.config/tpe-food-graph/ig_token")
API = "https://graph.facebook.com/v27.0/"
PERMISSIONS = ("instagram_basic", "instagram_manage_insights", "pages_read_engagement", "pages_show_list")
PROFILE = "id,username,name,biography,website,followers_count,follows_count,media_count,profile_picture_url"
MEDIA = "id,caption,timestamp,permalink"
SINCE_DAYS = 365
MAX_POSTS = 400
PAGE = 50           # posts per request; Graph API error 1 for a page too big to build, then SMALL_PAGE
SMALL_PAGE = 20
MIN_INTERVAL = 20   # seconds between requests
THROTTLED = {4, 17, 32, 613, 80002}
UNAVAILABLE = {110}  # "Cannot find User": no such account, or not a Business or Creator one
HANDLE = re.compile(r"[a-z0-9._]{1,30}")
SHORTCODE = re.compile(r"/(?:p|reel|tv)/([^/?#]+)")
# urllib rather than curl, so the token never shows in the process list.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({"https": "http://fwdproxy:8080"}))
_last = [0.0]
_token = []
_account = []


class ApiError(Exception):
    def __init__(self, err):
        self.code = err.get("code")
        self.message = err.get("error_user_msg") or err.get("message") or "no error message"
        super().__init__(f"Graph API error {self.code}/{err.get('error_subcode')}: {self.message}")


def token():
    if not _token:
        if not os.path.exists(TOKEN_FILE):
            raise SystemExit(f"no access token in {TOKEN_FILE} (see the top of ig_api.py)")
        if os.stat(TOKEN_FILE).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise SystemExit(f"{TOKEN_FILE} is readable by others: chmod 600 it")
        _token.append(open(TOKEN_FILE).read().strip())
    return _token[0]


def usage(headers):
    """The highest share (percent) of its hourly limit the app has used, from the reply's headers."""
    high = 0
    for name in ("X-App-Usage", "X-Business-Use-Case-Usage"):
        try:
            data = json.loads(headers.get(name) or "{}")
        except ValueError:
            continue
        entries = [data] if name == "X-App-Usage" else [e for v in data.values() for e in v]
        for e in entries:
            high = max([high] + [e.get(k, 0) for k in ("call_count", "total_time", "total_cputime")])
    return high


def call(path, params=None):
    """GET a Graph API path and return the parsed reply, waiting out rate limits."""
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    backoff = 300
    for _ in range(6):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            with OPENER.open(req, timeout=60) as r:
                reply, used = json.load(r), usage(r.headers)
            if used >= 90:
                print(f"  {used}% of the hourly API limit used; pausing 15 minutes", flush=True)
                time.sleep(900)
            return reply
        except urllib.error.HTTPError as e:
            try:
                err = json.load(e).get("error") or {}
            except ValueError:
                err = {"message": f"HTTP {e.code}"}
            if err.get("code") not in THROTTLED and not err.get("is_transient"):
                raise ApiError(err)
            print(f"  {err.get('message')}; retrying in {backoff}s", flush=True)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  {e}; retrying in {backoff}s", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 3600)
    raise RuntimeError(f"giving up on {path}")


def account():
    """The Instagram professional account the token reads as: {"id", "username"}. That's the account
    selected in the login dialog (me/accounts can leave out Pages the token was granted)."""
    if not _account:
        scopes = call("debug_token", {"input_token": token()})["data"].get("granular_scopes") or []
        ids = [i for s in scopes if s["scope"] == "instagram_basic" for i in s.get("target_ids", [])]
        if not ids:
            pages = call("me/accounts", {"fields": "instagram_business_account"})["data"]
            ids = [p["instagram_business_account"]["id"] for p in pages if p.get("instagram_business_account")]
        if not ids:
            raise SystemExit("the token reaches no Instagram professional account: select it and its Page "
                             "in the login dialog")
        _account.append(call(ids[0], {"fields": "id,username"}))
    return _account[0]


def discover(handle, after=None, page=PAGE):
    """One Business Discovery request: the profile and its first page of posts, or a later page."""
    media = f"media.after({after}).limit({page}){{{MEDIA}}}" if after else f"media.limit({page}){{{MEDIA}}}"
    fields = media if after else f"{PROFILE},{media}"
    query = {"fields": f"business_discovery.username({handle}){{{fields}}}"}
    try:
        return call(account()["id"], query)["business_discovery"]
    except ApiError as e:
        if e.code != 1 or page == SMALL_PAGE:
            raise
        return discover(handle, after, SMALL_PAGE)


def to_post(m):
    cap = m.get("caption") or ""
    code = SHORTCODE.search(m.get("permalink") or "")
    return {
        "shortcode": code.group(1) if code else m["id"],
        "ts": int(datetime.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()),
        "caption": cap,
        "tagged": [],
        "coauthors": [],
        "mentions": sorted({h.lower().rstrip(".") for h in ig.MENTION_RE.findall(cap)}),
        "location": None,
    }


def fetch(handle):
    since = int(time.time()) - SINCE_DAYS * 86400
    u = discover(handle)
    posts, media = [], u.get("media") or {}
    while True:
        batch = [to_post(m) for m in media.get("data", [])]
        posts += batch
        after = ((media.get("paging") or {}).get("cursors") or {}).get("after")
        if not after or not batch or len(posts) >= MAX_POSTS or batch[-1]["ts"] < since:
            break
        media = discover(handle, after).get("media") or {}
    return {
        "username": u["username"].lower(),
        "api_id": u["id"],
        "full_name": u.get("name"),
        "biography": u.get("biography"),
        "external_url": u.get("website"),
        "followers": u.get("followers_count"),
        "following": u.get("follows_count"),
        "media_count": u.get("media_count"),
        "profile_pic": u.get("profile_picture_url"),
        "since": since,
        "posts": [p for p in posts if p["ts"] >= since][:MAX_POSTS],
    }


def profile(handle, refresh=False):
    """The account's profile and recent posts from Business Discovery (cached), or
    {"username", "unavailable": reason} for an account the API can't read."""
    handle = handle.lower().strip().strip("@").rstrip(".")
    if not HANDLE.fullmatch(handle):
        raise SystemExit(f"not an Instagram handle: {handle!r}")
    path = os.path.join(CACHE, handle + ".json")
    if os.path.exists(path) and not refresh:
        return json.load(open(path))
    try:
        p = fetch(handle)
    except ApiError as e:
        if e.code not in UNAVAILABLE:
            raise
        p = {"username": handle, "unavailable": e.message}
    p["fetched"] = int(time.time())
    with open(path, "w") as f:
        json.dump(p, f, ensure_ascii=False)
    return p


def summary(p):
    """One line: the API copy's posts and @mentions, next to the accounts the logged-out copy links to."""
    h = p["username"]
    if "unavailable" in p:
        return f"{h:28s} unavailable: {p['unavailable']}"
    named = {m for post in p["posts"] for m in post["mentions"]} - {h}
    oldest = min((post["ts"] for post in p["posts"]), default=None)
    line = f"{h:28s} {len(p['posts']):>3} posts"
    line += f" since {datetime.date.fromtimestamp(oldest)}" if oldest else ""
    line += f", @mentioning {len(named)} accounts"
    path = os.path.join(ig.CACHE, h + ".json")
    old = json.load(open(path)) if os.path.exists(path) else None
    if old:
        links = set(ig.outlinks(old))
        line += (f" | logged out: {len(old['posts'])} posts linking {len(links)}; "
                 f"{len(named - links)} new, {len(links - named)} only there")
    return line


def whoami():
    t = call("debug_token", {"input_token": token()})["data"]

    def day(ts):
        return datetime.date.fromtimestamp(ts).isoformat() if ts else "never"

    print(f"{'valid' if t.get('is_valid') else 'INVALID'} {(t.get('type') or '').lower()} token for "
          f"{t.get('application')}, expires {day(t.get('expires_at'))}, "
          f"data access until {day(t.get('data_access_expires_at'))}")
    scopes = set(t.get("scopes") or [])
    print("permissions:", ", ".join(sorted(scopes)))
    missing = [s for s in PERMISSIONS if s not in scopes]
    if missing:
        print("missing:", ", ".join(missing))
    a = account()
    print(f"reads as @{a['username']} (IG user {a['id']})")


def crawl(budget):
    order = {"blogger": 0, "maker": 1, "venue": 2}
    kind = {}
    for name in project.available():
        for h, label in project.json_file(os.path.join(project.PROJECTS, name, "overrides.json"), {}).items():
            k = label.split(":")[0] if isinstance(label, str) else None
            if k in order and order[k] < order.get(kind.get(h.lower()), len(order)):
                kind[h.lower()] = k
    todo = []
    for h, k in kind.items():
        path = os.path.join(ig.CACHE, h + ".json")
        p = json.load(open(path)) if os.path.exists(path) else None
        if p and not p["is_private"] and not os.path.exists(os.path.join(CACHE, h + ".json")):
            todo.append((order[k], -p["followers"], h))
    todo.sort()
    n = min(budget, len(todo))
    print(f"{len(todo)} labelled accounts have no API copy; fetching {n}")
    for i, (_, _, h) in enumerate(todo[:n], 1):
        try:
            p = profile(h)
        except ApiError as e:
            if e.code in (10, 190) or 200 <= (e.code or 0) < 300:  # the token or its permissions
                raise
            print(f"[{i}/{n}] {h:28s} skipped: {e}", flush=True)
            continue
        except RuntimeError as e:
            print(e)
            break
        print(f"[{i}/{n}] {summary(p)}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Instagram profiles through Business Discovery")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    f = sub.add_parser("fetch")
    f.add_argument("--refresh", action="store_true")
    f.add_argument("handles", nargs="+")
    c = sub.add_parser("crawl")
    c.add_argument("budget", type=int)
    args = ap.parse_args()
    try:
        if args.cmd == "whoami":
            whoami()
        elif args.cmd == "fetch":
            for h in args.handles:
                print(summary(profile(h, args.refresh)), flush=True)
        else:
            crawl(args.budget)
    except ApiError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
