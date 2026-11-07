"""Merge press / food-blogger coverage into the project's data/press.json ({handle: [{outlet, url, title}]}).

Sources, in the project's data/:
  harvest.json             articles harvested while building the graph (harvest.py)
  CURATED files            curated line-ups named in the project config, {vendor: handle}
                           (bakeries: the Bon Pain 2026 bread fair)
  press_search.json        coverage found by web search ({handle: [{outlet, url, title}]};
                           press_search.py)
  trusted_blogs.json       established Taipei food blogs: every post title since
                           BLOG_SINCE is fetched (via fwdproxy, cached in the gitignored
                           data/blogs/ shared by all projects) from the blog's Blogger feed or
                           WordPress REST API, and a post whose title names the shop is a
                           dedicated review, marked "trusted" (rank.py weighs those outlets higher)

usage: python3 -I press.py -p PROJECT
"""

import csv
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402
from classify import brands  # noqa: E402

CFG = project.current()
DATA = CFG.DATA
BLOG_CACHE = os.path.join(project.SHARED, "blogs")
CURATED_URLS = {c["url"] for c in CFG.CURATED}
# Not editorial coverage: social networks, forums, maps, delivery, listing and job sites.
NOT_PRESS = re.compile(
    r"instagram|facebook|threads|google\.|goo\.gl|youtube|uber|foodpanda|tripadvisor|linktr|"
    r"inline\.app|line\.me|shopee|pinkoi|104\.com|1111\.com|yes123|"
    r"yelp|tabelog|cafenomad|openrice|trip\.com|klook|kkday|agoda|booking\.com|"
    r"ptt\.cc|dcard|reddit|tiktok|wikipedia|"
    # SEO content farms rather than food writing.
    r"uptogo|upssmile|tyaward|icoco\.tw|lordcat|cafe-belt|findglocal|wheree|cybo\.com",
    re.I,
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BLOG_SINCE = "2022-01-01"

# Matching shop names in blog post titles.
SEP = re.compile(r"[|｜•·‧/、,，。()（）\[\]【】「」『』《》<>＜＞~～\-–—_:：!！?？#＃@＠✦★☆♡❤️\n]+")
# Words that describe what a shop sells rather than name it.
FILLER = re.compile(
    r"訂購中|預訂|預購|開單|營業|公休|官方|門市|工作室$|客製化?|生日蛋糕|"
    r"\d+月|since \d+|全預訂制|專賣店?$|台北|臺北",
    re.I,
)
GENERIC = CFG.PRESS_GENERIC
# Product words: a name made mostly of them ("手作甜點") names no shop in particular.
PRODUCT = CFG.PRESS_PRODUCT
# Shop names that are also everyday English words, too ambiguous to match alone in a
# post title ("1881 Heritage"); those shops still match on their fuller names.
AMBIGUOUS = CFG.PRESS_AMBIGUOUS
# A post titled with another city or country is about a shop there (a branch, a namesake),
# unless the title also names Taipei.
ELSEWHERE = re.compile(
    r"新竹|竹北|台中|臺中|台南|臺南|高雄|桃園|中壢|宜蘭|羅東|花蓮|台東|臺東|嘉義|彰化|基隆|屏東|苗栗|南投|"
    r"雲林|澎湖|金門|香港|澳門|日本|東京|大阪|京都|福岡|北海道|沖繩|韓國|首爾|釜山|曼谷|新加坡|"
    r"taichung|tainan|kaohsiung|hsinchu|tokyo|osaka|kyoto|seoul|hong ?kong|bangkok|singapore",
    re.I,
)
TAIPEI = re.compile(r"[台臺]北|新北|taipei", re.I)


def outlet_of(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    host = re.sub(r"^(www|m|stage)\.", "", host)
    return host


def load(name, default):
    path = os.path.join(DATA, name)
    return json.load(open(path)) if os.path.exists(path) else default


def norm(s):
    s = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z一-鿿぀-ヿ]", "", s)


def words(s):
    s = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", s or "")).lower()
    return re.findall(r"[0-9a-z]+", "".join(c for c in s if not unicodedata.combining(c)))


def word_run(name, text):
    """name's Latin letters equal a run of whole words in text ("SussuBakery" ~ "Sussu Bakery",
    but "smile" is not in "Opensmile")."""
    target, ws = "".join(words(name)), words(text)
    return any("".join(ws[i:j]) == target for i in range(len(ws)) for j in range(i + 1, len(ws) + 1))


def distinctive(a):
    rest = PRODUCT.sub("", GENERIC.sub("", norm(a)))
    return len(re.findall(r"[一-鿿]", rest)) >= 2 or len(re.findall(r"[a-z]", rest)) >= 4


def name_parts(name):
    parts = [p.strip() for p in SEP.split(unicodedata.normalize("NFKC", name or ""))]
    return [p for p in parts if len(norm(p)) >= 2 and not FILLER.fullmatch(p)]


def aliases(handle, ig_name, google_name):
    """Shop names to look for in titles: the IG name's first part and any English part, the
    first part of the Google place name, and the handle; each in full and without shop words."""
    parts = name_parts(ig_name)
    names = parts[:1] + [p for p in parts[1:] if re.fullmatch(r"[A-Za-z0-9 &'’.]{5,}", p)]
    names += name_parts(google_name)[:1]
    out = set()
    for name in names:
        if not distinctive(name):
            continue
        for a in (norm(name), GENERIC.sub("", norm(name))):
            cjk, latin = len(re.findall(r"[一-鿿]", a)), len(re.findall(r"[a-z]", a))
            if cjk >= 3 or latin >= 5 or (cjk >= 2 and latin >= 3):
                out.add(a)
    h = norm(handle)
    if len(h) >= 6 and distinctive(h):
        out.add(h)
    return out - AMBIGUOUS


def name_tokens(*names):
    """Latin words, numbers and CJK runs in names / handles, lowercased."""
    out = set()
    for n in names:
        n = unicodedata.normalize("NFKC", n or "").lower()
        out |= set(re.findall(r"[a-z]{2,}|\d+|[一-鿿]{2,}", n))
    return {t for t in out if not GENERIC.fullmatch(t) and not CFG.GOOGLE_GENERIC.fullmatch(t)}


def names_token(title, t):
    if re.match(r"[一-鿿]", t):
        return t in title
    return t in re.findall(r"[a-z]+|\d+", unicodedata.normalize("NFKC", title).lower())


def get_json(url):
    out = subprocess.run(
        ["curl", "-s", "--http2", "-x", "fwdproxy:8080", "--max-time", "60", "-A", UA, url],
        capture_output=True, text=True, errors="replace",
    ).stdout
    try:
        return json.loads(out)
    except ValueError:
        return None


def blog_posts(blog):
    """[{title, url, date}] for every post on a trusted blog since BLOG_SINCE, cached."""
    os.makedirs(BLOG_CACHE, exist_ok=True)
    path = os.path.join(BLOG_CACHE, blog["site"] + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    posts = []
    if blog["platform"] == "blogger":
        start = 1
        while True:
            d = get_json(f"https://{blog['site']}/feeds/posts/summary?alt=json&max-results=150"
                         f"&start-index={start}&published-min={BLOG_SINCE}T00:00:00")
            if d is None:
                print(f"  {blog['site']}: feed request failed; not cached, rerun to retry")
                return posts
            entries = d["feed"].get("entry", [])
            for e in entries:
                link = next(l["href"] for l in e["link"] if l["rel"] == "alternate")
                posts.append({"title": e["title"]["$t"], "url": link, "date": e["published"]["$t"][:10]})
            if len(entries) < 150:
                break
            start += 150
    else:
        page = 1
        while True:
            batch = get_json(f"https://{blog['site']}/wp-json/wp/v2/posts?per_page=100&page={page}"
                             f"&after={BLOG_SINCE}T00:00:00&_fields=title,link,date")
            if batch is None:
                print(f"  {blog['site']}: REST request failed on page {page}; not cached, rerun to retry")
                return posts
            # Past the last page WordPress answers with an error object instead of a list.
            if not isinstance(batch, list) or not batch:
                break
            posts += [{"title": html.unescape(p["title"]["rendered"]), "url": p["link"], "date": p["date"][:10]}
                      for p in batch]
            page += 1
    json.dump(posts, open(path, "w"), ensure_ascii=False)
    return posts


def main():
    shops = {s["username"]: s for s in csv.DictReader(open(os.path.join(CFG.OUT, "food_creators.csv")))}
    google = load("google_places.json", {})
    press = {}

    def add(h, item):
        if NOT_PRESS.search(item["url"]) and item["url"] not in CURATED_URLS:
            return
        lst = press.setdefault(h, [])
        for x in lst:
            if x["url"] == item["url"]:
                if item.get("trusted"):
                    x["trusted"] = True
                return
        lst.append(item)

    for url, found in load("harvest.json", {}).items():
        for h in found:
            if h in shops:
                add(h, {"outlet": outlet_of(url), "url": url, "title": ""})

    # Vendor names -> handles, reviewed by hand (fuzzy name matching mislabels too many).
    for c in CFG.CURATED:
        for vendor, h in load(c["file"], {}).items():
            add(h, {"outlet": c["outlet"], "url": c["url"], "title": c["title"].format(vendor=vendor)})

    for h, items in load("press_search.json", {}).items():
        if h in shops:
            for it in items:
                if it.get("url"):
                    # Count outlets by domain; agents name the same site differently.
                    add(h, {"outlet": outlet_of(it["url"]), "label": it.get("outlet") or "",
                            "url": it["url"], "title": it.get("title", "")})

    blogs = [(b, [(norm(p["title"]), p) for p in blog_posts(b)]) for b in load("trusted_blogs.json", [])]
    n_trusted = 0
    shop_aliases = {}
    for h, s in shops.items():
        if s["role"] != "shop":
            continue
        gp = google.get(h) or {}
        al = shop_aliases[h] = aliases(h, s["name"], gp.get("name") if gp.get("match") else "")
        cjk = [a for a in al if re.search(r"[一-鿿぀-ヿ]", a)]
        latin = [a for a in al if a not in cjk]
        for b, posts in blogs:
            for t, p in posts:
                if ELSEWHERE.search(p["title"]) and not TAIPEI.search(p["title"]):
                    continue
                if any(a in t for a in cjk) or any(word_run(a, p["title"]) for a in latin):
                    add(h, {"outlet": outlet_of(p["url"]), "label": b["name"], "url": p["url"],
                            "title": p["title"], "date": p["date"], "trusted": True})
                    n_trusted += 1

    # A post about one branch also reads as the brand ("RUFOUS COFFEE ROASTERS 2" names "Rufous
    # Coffee Roasters"). Among branches of one brand, a post whose title names a word only one
    # branch has (the 2 of Rufous Coffee Roasters 2, the TM of Celebread-TM, Anhe) goes to that
    # branch alone; otherwise it stays with the branches it was found for.
    brand = brands({h: shops[h]["bio"] for h in shop_aliases})
    members = {}
    for h, lead in brand.items():
        members.setdefault(lead, []).append(h)
    n_moved = 0
    for group in (g for g in members.values() if len(g) > 1):
        gname = {h: (google.get(h) or {}).get("name", "") if (google.get(h) or {}).get("match") else "" for h in group}
        tokens = {h: name_tokens(h, shops[h]["name"], gname[h]) for h in group}
        own = {h: tokens[h] - set().union(*(tokens[o] for o in group if o != h)) for h in group}
        posts = {it["url"]: it for h in group for it in press.get(h, [])
                 if it["title"] and it["url"] not in CURATED_URLS}
        for url, it in posts.items():
            hits = {h: sum(names_token(it["title"], t) for t in own[h]) for h in group}
            best = max(hits.values())
            if not best:
                continue
            for h in group:
                have = next((x for x in press.get(h, []) if x["url"] == url), None)
                if hits[h] == best and not have:
                    press.setdefault(h, []).append(dict(it))
                    n_moved += 1
                elif have and hits[h] != best:
                    press[h].remove(have)
    press = {h: items for h, items in press.items() if items}

    json.dump(press, open(os.path.join(DATA, "press.json"), "w"), ensure_ascii=False, indent=1)
    for b, posts in blogs:
        print(f"{len(posts):>6} posts  {b['site']}")
    print(f"shops with coverage: {len(press)}; items: {sum(len(v) for v in press.values())}; "
          f"trusted blog posts naming a shop: {n_trusted}; posts moved to the sister branch they are about: {n_moved}")


if __name__ == "__main__":
    main()
