"""Rank Greater Taipei bakeries / sweets shops and write output/ranking.html.

Combines five signals, each scaled to 0..1 (see METHOD below / the dashboard):
  network   - endorsements (tags) from the graph, weighted by who tagged and how
              often, plus centrality in the tag + Instagram-related graph
  quality   - Google Maps rating, shrunk towards the average by review count
  volume    - number of Google reviews (log-scaled)
  press     - distinct food blogs / media that covered the shop; a dedicated post on
              a trusted food blog counts its outlet TRUSTED_BLOG_WEIGHT times
  reach     - Instagram followers (log-scaled)

Shops in NOT_SWEETS are left out by hand.

Inputs: output/graph.json and output/food_creators.csv (from build.py), plus the
optional data/google_places.json (google_maps.py), data/press.json and
data/review_notes.json. Missing optional inputs just score as unknown.

Pipeline: python3 build.py; python3 -I google_maps.py; python3 -I press.py; python3 rank.py
"""

import csv
import json
import math
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
DATA = os.path.join(ROOT, "data")

WEIGHTS = {"network": 0.35, "quality": 0.30, "volume": 0.10, "press": 0.15, "reach": 0.10}
# Who is tagging: bloggers curate for an audience, makers tagging peers is chef
# respect, cafés tagging a supplier is mostly business.
ENDORSER_WEIGHT = {"blogger": 1.0, "maker": 0.8, "venue": 0.4}
RELATED_EDGE = 0.35  # weight of an Instagram "related account" link vs a tag
PRIOR_REVIEWS = 40   # Bayesian prior strength for Google ratings
TOP_N = 100
# A post on a trusted food blog (data/trusted_blogs.json) whose title names the shop is a
# dedicated review, so that outlet counts this many times in the press signal.
TRUSTED_BLOG_WEIGHT = 2.0

# Labelled bakery / dessert shops in the graph, but not what this ranking is about.
NOT_SWEETS = {
    "aufglet", "aufglet_taipei",  # brunch café (Google: café); both accounts match one place
    "skiff.tw",                   # matcha drinks shop (Google: non-alcoholic drinks)
    "heureuxvegan",               # light-meal restaurant that also sells desserts
    "icegyaru",                   # soft-serve shop
}

DISTRICTS = {
    "中正區": "Zhongzheng", "大同區": "Datong", "中山區": "Zhongshan", "松山區": "Songshan",
    "大安區": "Da'an", "萬華區": "Wanhua", "信義區": "Xinyi", "士林區": "Shilin", "北投區": "Beitou",
    "內湖區": "Neihu", "南港區": "Nangang", "文山區": "Wenshan",
    "板橋區": "Banqiao", "三重區": "Sanchong", "中和區": "Zhonghe", "永和區": "Yonghe",
    "新莊區": "Xinzhuang", "新店區": "Xindian", "土城區": "Tucheng", "蘆洲區": "Luzhou",
    "汐止區": "Xizhi", "樹林區": "Shulin", "鶯歌區": "Yingge", "三峽區": "Sanxia", "淡水區": "Tamsui",
    "瑞芳區": "Ruifang", "五股區": "Wugu", "泰山區": "Taishan", "林口區": "Linkou", "深坑區": "Shenkeng",
    "石碇區": "Shiding", "坪林區": "Pinglin", "三芝區": "Sanzhi", "石門區": "Shimen", "八里區": "Bali",
    "平溪區": "Pingxi", "雙溪區": "Shuangxi", "貢寮區": "Gongliao", "金山區": "Jinshan",
    "萬里區": "Wanli", "烏來區": "Wulai",
}

TPE = re.compile(r"台北|臺北|taipei|大安|信義|中山區|松山|士林|內湖|北投|萬華|文山|南港|中正|大同區|天母|民生社區", re.I)
NTPE = re.compile(r"新北|板橋|永和|中和|三重|新店|新莊|土城|汐止|淡水|林口|蘆洲|樹林|鶯歌|三峽|五股|泰山|深坑", re.I)
ELSEWHERE = re.compile(
    r"新竹|竹北|台中|臺中|台南|臺南|高雄|桃園|中壢|宜蘭|羅東|花蓮|台東|臺東|嘉義|彰化|基隆|屏東|苗栗|南投|"
    r"雲林|澎湖|金門|taichung|tainan|kaohsiung|hsinchu|taoyuan|yilan|香港|hong ?kong|tokyo|東京|osaka",
    re.I,
)


def load_json(name, default):
    path = os.path.join(DATA, name)
    return json.load(open(path)) if os.path.exists(path) else default


def area(shop, gp):
    """'台北市' / '新北市' / 'elsewhere' / '' (unknown). The Google address wins over the bio."""
    addr = (gp or {}).get("address") or ""
    if addr:
        if re.search(r"[台臺]北市", addr):
            return "台北市"
        if "新北市" in addr:
            return "新北市"
        return "elsewhere"
    text = " ".join([shop["bio"], shop["city"], shop["address"], shop["name"]])
    if ELSEWHERE.search(text):
        return "elsewhere"
    if NTPE.search(text) and not TPE.search(text):
        return "新北市"
    if TPE.search(text):
        return "台北市"
    return ""


def district_of(gp):
    """Google's district, else the first known district named in the address."""
    if gp.get("district"):
        return gp["district"]
    addr = gp.get("address") or ""
    return next((d for d in DISTRICTS if d in addr), "")


def display_name(*names):
    """Short shop name: NFKC (folds 𝐟𝐚𝐧𝐜𝐲 letters), first segment before | or (, emoji dropped."""
    out = []
    for n in names:
        n = unicodedata.normalize("NFKC", n or "")
        n = re.split(r"\s*[|｜/／(（\[【]\s*", n)[0]
        n = "".join(c for c in n if unicodedata.category(c)[0] in "LNZ" or c in "&'’.·・-")
        n = re.sub(r"\s+", " ", n).strip(" .-·")
        if len(n) >= 2:
            out.append(n)
    # Google names often carry a sales pitch; the shorter of the two is usually the name.
    return min(out, key=len)[:28] if out else ""


def pagerank(nodes, edges, damping=0.85, iters=80):
    out_w = {n: 0.0 for n in nodes}
    for (a, _), w in edges.items():
        out_w[a] += w
    n = len(nodes)
    pr = {v: 1 / n for v in nodes}
    for _ in range(iters):
        dangling = sum(pr[v] for v in nodes if out_w[v] == 0)
        nxt = {v: (1 - damping) / n + damping * dangling / n for v in nodes}
        for (a, b), w in edges.items():
            nxt[b] += damping * pr[a] * w / out_w[a]
        pr = nxt
    return {v: pr[v] * n for v in nodes}  # 1.0 = average


def scaled(x, hi):
    """log-damped 0..1, saturating at hi."""
    return min(1.0, math.log1p(max(x, 0)) / math.log1p(hi)) if hi > 0 else 0.0


def percentile(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0


def network_metrics(graph):
    nodes = {n["username"]: n for n in graph["nodes"]}
    tags = [l for l in graph["links"] if l["type"] == "tag"]
    related = [l for l in graph["links"] if l["type"] == "related"]

    # Centrality over tags (directed, stronger when tagged in more posts) and
    # Instagram's related suggestions (undirected, weaker).
    edges = {}
    for l in tags:
        e = (l["source"], l["target"])
        edges[e] = edges.get(e, 0) + 1 + math.log2(l["weight"])
    for l in related:
        for e in ((l["source"], l["target"]), (l["target"], l["source"])):
            edges[e] = edges.get(e, 0) + RELATED_EDGE
    central = pagerank(sorted(nodes), edges)

    endorse = {h: 0.0 for h in nodes}
    endorsers = {h: [] for h in nodes}
    for l in tags:
        a, b = l["source"], l["target"]
        # Authority of the endorser: their own tag-graph PageRank (1.0 = average), damped.
        auth = min(3.0, math.sqrt(max(nodes[a]["pagerank"], 0.25)))
        s = ENDORSER_WEIGHT.get(nodes[a]["kind"], 0.4) * (1 + math.log2(l["weight"])) * auth
        endorse[b] += s
        endorsers[b].append({
            "handle": a, "kind": nodes[a]["kind"], "posts": l["weight"],
            "followers": nodes[a]["followers"], "score": round(s, 2),
        })
    related_by = {h: set() for h in nodes}
    for l in related:
        related_by[l["source"]].add(l["target"])
        related_by[l["target"]].add(l["source"])
    return nodes, central, endorse, endorsers, related_by


def main():
    graph = json.load(open(os.path.join(OUT, "graph.json")))
    shops = {r["username"]: r for r in csv.DictReader(open(os.path.join(OUT, "food_creators.csv")))}
    google = load_json("google_places.json", {})
    press = load_json("press.json", {})
    notes = load_json("review_notes.json", {})

    nodes, central, endorse, endorsers, related_by = network_metrics(graph)

    cands = []
    for h, s in shops.items():
        if s["role"] != "shop" or s["subtype"] not in ("bakery", "dessert", "pastry") or h in NOT_SWEETS:
            continue
        gp = google.get(h) or {}
        if gp.get("closed"):
            continue
        a = area(s, gp if gp.get("match") else None)
        if a not in ("台北市", "新北市"):
            continue
        cands.append((h, s, gp if gp.get("match") else {}, a))

    rated = [g for _, _, g, _ in cands if g.get("rating") and g.get("reviews")]
    mean_rating = (
        sum(g["rating"] * g["reviews"] for g in rated) / sum(g["reviews"] for g in rated)
        if rated else 4.3
    )

    # Saturation points for the log scales: high percentiles of the candidate pool,
    # so one outlier doesn't flatten everyone else.
    hi_endorse = percentile([endorse[h] for h, *_ in cands if endorse[h] > 0], 0.95)
    hi_central = percentile([central[h] for h, *_ in cands], 0.97)
    hi_reviews = percentile([g["reviews"] for g in rated], 0.95) if rated else 1000

    rows = []
    for h, s, gp, a in cands:
        n = nodes[h]
        v = gp.get("reviews") or 0
        r = gp.get("rating")
        bayes = (r * v + mean_rating * PRIOR_REVIEWS) / (v + PRIOR_REVIEWS) if r and v else None
        # 4.0 -> 0, 4.9 -> 1 after shrinkage; unlisted shops sit at the pool average.
        quality = min(1.0, max(0.0, ((bayes or mean_rating) - 4.0) / 0.9))
        pr_items = press.get(h, [])
        outlets = {}  # outlet -> weight
        for p in pr_items:
            w = TRUSTED_BLOG_WEIGHT if p.get("trusted") else 1.0
            outlets[p["outlet"]] = max(outlets.get(p["outlet"], 0.0), w)
        comp = {
            "network": 0.65 * scaled(endorse[h], hi_endorse) + 0.35 * scaled(central[h] - 0.15, hi_central),
            "quality": quality,
            "volume": scaled(v, hi_reviews),
            "press": scaled(sum(outlets.values()), 5),
            "reach": min(1.0, max(0.0, (math.log10(max(n["followers"], 1)) - 3) / 2.3)),  # 1K..200K
        }
        score = 100 * sum(WEIGHTS[k] * comp[k] for k in WEIGHTS)
        rows.append({
            "handle": h,
            "name": s["name"],
            "gname": gp.get("name") or "",
            "display": display_name(gp.get("name"), s["name"]) or h,
            "type": "bakery" if s["subtype"] == "bakery" else "sweets",
            "area": a,
            "district": district_of(gp),
            "address": gp.get("address") or "",
            "followers": n["followers"],
            "bio": s["bio"][:300],
            "ig": s["url"],
            "maps": gp.get("maps_url") or "",
            "rating": r,
            "reviews": v,
            "stars": gp.get("stars"),
            "bayes": round(bayes, 3) if bayes else None,
            "topics": gp.get("topics") or [],
            "categories": gp.get("categories") or [],
            "match": gp.get("match") or "",
            "endorse": round(endorse[h], 2),
            "endorsers": sorted(endorsers[h], key=lambda e: -e["score"]),
            "centrality": round(central[h], 2),
            "related": len(related_by[h]),
            "press": pr_items,
            "outlets": len(outlets),
            "trusted": sum(1 for w in outlets.values() if w > 1),
            "notes": notes.get(h) or {},
            "comp": {k: round(x, 4) for k, x in comp.items()},
            "contrib": {k: round(100 * WEIGHTS[k] * x, 2) for k, x in comp.items()},
            "score": round(score, 2),
        })
    rows.sort(key=lambda x: -x["score"])
    for i, x in enumerate(rows, 1):
        x["rank"] = i
        x["follower_rank"] = None
    for i, x in enumerate(sorted(rows, key=lambda x: -x["followers"]), 1):
        x["follower_rank"] = i

    meta = {
        "weights": WEIGHTS,
        "endorser_weight": ENDORSER_WEIGHT,
        "related_edge": RELATED_EDGE,
        "prior_reviews": PRIOR_REVIEWS,
        "trusted_blog_weight": TRUSTED_BLOG_WEIGHT,
        "not_sweets": sorted(NOT_SWEETS),
        "districts": DISTRICTS,
        "mean_rating": round(mean_rating, 3),
        "hi_endorse": round(hi_endorse, 2),
        "hi_central": round(hi_central, 2),
        "hi_reviews": hi_reviews,
        "n_candidates": len(rows),
        "n_shops": sum(1 for s in shops.values() if s["role"] == "shop"),
        "n_google": sum(1 for x in rows if x["rating"]),
        "n_press": sum(1 for x in rows if x["press"]),
        "n_nodes": len(graph["nodes"]),
        "n_tags": sum(1 for l in graph["links"] if l["type"] == "tag"),
        "n_related": sum(1 for l in graph["links"] if l["type"] == "related"),
        "top_n": TOP_N,
    }
    data = {"meta": meta, "rows": rows}

    with open(os.path.join(OUT, "ranking.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    cols = ["rank", "handle", "name", "gname", "type", "area", "district", "score", "network", "quality",
            "volume", "press", "reach", "rating", "reviews", "bayes", "followers", "endorse", "centrality",
            "related", "n_press", "n_trusted", "address", "ig", "maps"]
    with open(os.path.join(OUT, "ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for x in rows:
            w.writerow({**x, **x["contrib"], "n_press": len(x["press"]), "n_trusted": x["trusted"]})

    tmpl = open(os.path.join(ROOT, "ranking_template.html")).read()
    html = tmpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    with open(os.path.join(OUT, "ranking.html"), "w") as f:
        f.write(html)
    print(f"candidates={len(rows)} with_google={meta['n_google']} with_press={meta['n_press']} "
          f"mean_rating={mean_rating:.2f}")
    for x in rows[:15]:
        print(f"{x['rank']:>3} {x['score']:5.1f} {x['handle']:<28} {x['area']} "
              f"{x['rating'] or '-'}({x['reviews']}) {x['contrib']}")


if __name__ == "__main__":
    main()
