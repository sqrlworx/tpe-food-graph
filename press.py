"""Merge press / food-blogger coverage into data/press.json ({handle: [{outlet, url, title}]}).

Sources:
  data/harvest.json             articles harvested while building the graph (harvest.py)
  data/bonpain_2026_handles.json  the curated Bon Pain 2026 bread fair line-up (vendor -> handle)
  data/press_search.json        coverage found by web search ({handle: [{outlet, url, title}]})
  data/trusted_blogs.json       established Taipei food blogs: every post title since
                                BLOG_SINCE is fetched (via fwdproxy, cached in the gitignored
                                data/blogs/) from the blog's Blogger feed or WordPress REST API,
                                and a post whose title names the shop is a dedicated review,
                                marked "trusted" (rank.py weighs those outlets higher)

usage: python3 -I press.py
"""

import csv
import html
import json
import os
import re
import subprocess
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
BLOG_CACHE = os.path.join(DATA, "blogs")
BONPAIN_URL = "https://www.herenow.city/taipei/style/2026_bon-pain/"
# Not editorial coverage: social networks, maps, delivery and listing sites.
NOT_PRESS = re.compile(
    r"instagram|facebook|threads|google\.|goo\.gl|youtube|uber|foodpanda|tripadvisor|linktr|"
    r"inline\.app|line\.me|shopee|pinkoi|104\.com|"
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
GENERIC = re.compile(
    r"甜點|甜品|工作室|蛋糕|cake|麵包|烘焙|烘培|坊|專賣店?|咖啡|分店|門市|[一-鿿]{1,3}店|"
    r"bakery|bakehouse|boulangerie|patisseries?|dessert|cafe|coffee|studio|official|taipei|tw$"
)
# Product words: a name made mostly of them ("手作甜點") names no shop in particular.
PRODUCT = re.compile(
    r"可麗露|生乳捲|泡芙|肉桂捲|可頌|貝果|吐司|馬卡龍|千層|布丁|戚風|巴斯克|乳酪|起司|塔|酸種|法式|"
    r"手工|手作|客製化?|喜餅|彌月|禮盒|冰淇淋|義式|巧克力|水果|季節|專門|專賣|生日|婚禮|韓式|錶花|"
    r"croissant|canele|bagel|gelato|chocolate|cake|pastry|bread|sweets?"
)
# Shop names that are also everyday English words, too ambiguous to match alone in a
# post title ("1881 Heritage"); those shops still match on their fuller names.
AMBIGUOUS = {"heritage", "smile", "specialty", "specialtycoffee", "peckish", "comeup", "ontheroad",
             "rise", "season", "terra", "double", "butter", "bread",
             # common food words that a shop name can reduce to ("Cookie_Tea" -> "cookie")
             "cookie", "cookies", "scone", "scones", "brownie", "brownies", "cheesecake", "pudding",
             "waffle", "waffles", "donut", "donuts", "macaron", "macarons", "chiffon", "crepe", "crepes",
             "toast", "cream", "sugar", "honey", "cocoa", "matcha", "lemon", "berry", "happy", "sunny",
             "little", "petit", "maison"}
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
    shops = {s["username"]: s for s in csv.DictReader(open(os.path.join(ROOT, "output", "food_creators.csv")))}
    google = load("google_places.json", {})
    press = {}

    def add(h, item):
        if NOT_PRESS.search(item["url"]) and not item["url"] == BONPAIN_URL:
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
    for vendor, h in load("bonpain_2026_handles.json", {}).items():
        add(h, {"outlet": "Bon Pain 2026 line-up", "url": BONPAIN_URL,
                "title": f"Bon Pain 2026 bread fair curated vendor ({vendor})"})

    for h, items in load("press_search.json", {}).items():
        if h in shops:
            for it in items:
                if it.get("url"):
                    # Count outlets by domain; agents name the same site differently.
                    add(h, {"outlet": outlet_of(it["url"]), "label": it.get("outlet") or "",
                            "url": it["url"], "title": it.get("title", "")})

    blogs = [(b, [(norm(p["title"]), p) for p in blog_posts(b)]) for b in load("trusted_blogs.json", [])]
    n_trusted = 0
    for h, s in shops.items():
        if s["role"] != "shop":
            continue
        gp = google.get(h) or {}
        al = aliases(h, s["name"], gp.get("name") if gp.get("match") else "")
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

    json.dump(press, open(os.path.join(DATA, "press.json"), "w"), ensure_ascii=False, indent=1)
    for b, posts in blogs:
        print(f"{len(posts):>6} posts  {b['site']}")
    print(f"shops with coverage: {len(press)}; items: {sum(len(v) for v in press.values())}; "
          f"trusted blog posts naming a shop: {n_trusted}")


if __name__ == "__main__":
    main()
