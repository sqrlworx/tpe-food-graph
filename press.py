"""Merge press / food-blogger coverage into data/press.json ({handle: [{outlet, url, title}]}).

Sources:
  data/harvest.json             articles harvested while building the graph (harvest.py)
  data/bonpain_2026_handles.json  the curated Bon Pain 2026 bread fair line-up (vendor -> handle)
  data/press_search.json        coverage found by web search ({handle: [{outlet, url, title}]})

usage: python3 -I press.py
"""

import csv
import json
import os
import re
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
BONPAIN_URL = "https://www.herenow.city/taipei/style/2026_bon-pain/"
# Not editorial coverage: social networks, maps, delivery and listing sites.
NOT_PRESS = re.compile(
    r"instagram|facebook|threads|google\.|goo\.gl|youtube|uber|foodpanda|tripadvisor|linktr|"
    r"inline\.app|line\.me|shopee|pinkoi|104\.com|"
    # SEO content farms rather than food writing.
    r"uptogo|upssmile|tyaward|icoco\.tw|lordcat|cafe-belt|findglocal|wheree|cybo\.com",
    re.I,
)


def outlet_of(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    host = re.sub(r"^(www|m|stage)\.", "", host)
    return host


def load(name, default):
    path = os.path.join(DATA, name)
    return json.load(open(path)) if os.path.exists(path) else default


def main():
    shops = {s["username"]: s for s in csv.DictReader(open(os.path.join(ROOT, "output", "food_creators.csv")))}
    press = {}

    def add(h, item):
        if NOT_PRESS.search(item["url"]) and not item["url"] == BONPAIN_URL:
            return
        lst = press.setdefault(h, [])
        if all(x["url"] != item["url"] for x in lst):
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

    json.dump(press, open(os.path.join(DATA, "press.json"), "w"), ensure_ascii=False, indent=1)
    print(f"shops with coverage: {len(press)}; items: {sum(len(v) for v in press.values())}")


if __name__ == "__main__":
    main()
