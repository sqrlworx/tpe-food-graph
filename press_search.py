"""Search the web for press / food-blog coverage of the top candidates (search.py, via fwdproxy)
and write the project's data/press_search.json ({handle: [{outlet, url, title}]}), which press.py
merges.

One search per shop: its short name in quotes plus the project's SEARCH_SUFFIX ("台北 咖啡").
A result counts when its title names the shop (the same name matching press.py uses for
trusted blogs), it isn't the shop's own site, social media, a listing site or a content farm
(press.NOT_PRESS), and it isn't about another city.

The candidates are the top --top shops of the current output/ranking.json, so run rank.py
first (a ranking without press is fine), then this, then press.py and rank.py again.

usage: python3 -I press_search.py -p PROJECT [--top N] [handle ...]
"""

import argparse
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import press  # noqa: E402
import project  # noqa: E402
import search  # noqa: E402

CFG = project.current()
PER_SHOP = 6
# Search turns up more kinds of non-coverage than the hand-picked sources press.NOT_PRESS was
# written for: directories, menu / ordering / reservation pages, shops and brand sites.
NOT_COVERAGE = re.compile(
    r"wanderlog|menutaiwan|autoreserve|ichefpos|localking|eatsy\.tech|metrobites|wingontravel|funnow|"
    r"typica\.coffee|skm\.com|cyberbiz|shopline|91app|momoshop|pchome|bettermilk|treeman\.tw",
    re.I,
)


def host(url):
    return re.sub(r"^(www|m)\.", "", urllib.parse.urlparse(url).netloc.lower())


def names_shop(title, al):
    t = press.norm(title)
    cjk = [a for a in al if re.search(r"[一-鿿぀-ヿ]", a)]
    latin = [a for a in al if a not in cjk]
    return any(a in t for a in cjk) or any(press.word_run(a, title) for a in latin)


def own_site(url, row):
    """The shop's own site: its Google website, or a host named after its handle
    (coffeeimmerse.com for @coffeeimmerse, daonanguan.com for @daonanguan_specialty_coffee)."""
    h = host(url)
    if row.get("website") and h == host(row["website"]):
        return True
    stem = re.sub(r"[^a-z0-9]", "", row["handle"])
    return any(len(part) >= 5 and (part in stem or stem in part) for part in h.split("."))


def coverage(row):
    al = press.aliases(row["handle"], row["name"], row["gname"])
    if not al:
        return []
    out = []
    for r in search.results(f'"{row["display"]}" {CFG.SEARCH_SUFFIX}'):
        if press.NOT_PRESS.search(r["url"]) or NOT_COVERAGE.search(r["url"]) or own_site(r["url"], row):
            continue
        if press.ELSEWHERE.search(r["title"]) and not press.TAIPEI.search(r["title"]):
            continue
        if names_shop(r["title"], al):
            out.append({"outlet": host(r["url"]), "url": r["url"], "title": r["title"]})
    return out[:PER_SHOP]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top", type=int, default=CFG.PRESS_SEARCH_TOP,
                    help=f"search the top N of the current ranking (default {CFG.PRESS_SEARCH_TOP})")
    ap.add_argument("handles", nargs="*", help="only these shops")
    args = ap.parse_args()
    rows = json.load(open(os.path.join(CFG.OUT, "ranking.json")))["rows"]
    google = project.data(CFG, "google_places.json", {})
    for r in rows:
        r["website"] = (google.get(r["handle"]) or {}).get("website")
    rows = [r for r in rows if r["handle"] in args.handles] if args.handles else rows[:args.top]
    path = os.path.join(CFG.DATA, "press_search.json")
    found = project.json_file(path, {})
    for i, r in enumerate(rows, 1):
        try:
            found[r["handle"]] = coverage(r)
        except RuntimeError as e:
            print(f"stopping: {e}")
            break
        print(f"{i}/{len(rows)} #{r['rank']} {r['handle']:<28} {len(found[r['handle']])} "
              f"{' '.join(x['outlet'] for x in found[r['handle']])}", flush=True)
        if i % 10 == 0:
            json.dump(found, open(path, "w"), ensure_ascii=False, indent=1)
    json.dump(found, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"shops with coverage: {sum(1 for v in found.values() if v)} of {len(found)} searched")


if __name__ == "__main__":
    main()
