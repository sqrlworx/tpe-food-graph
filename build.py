"""Build the endorsement graph, rankings, and the HTML visualisation.

Edge A -> B means A tagged / @mentioned / co-posted with B in one of A's
recent posts (Instagram only exposes the latest 12 posts without login).
A "related" link A - B means Instagram suggests B on A's profile (or the
reverse). Related links are drawn but do not count as endorsements.

Not every tag is an endorsement:
  - sister accounts, and staff or founders tagging their own shop, are left out (sisters());
  - a post tagging many accounts (an event line-up, a roundup) is split: up to LIST_FULL
    tags count in full, beyond that every tag gets LIST_FULL / n;
  - a tag between two businesses that shows a business tie (supply, collaboration, a shared
    event, or a standing tag in STANDING_POSTS+ recent posts; see business_tie()) is marked
    "business"; rank.py counts it once, at a low weight.

usage: python3 -I build.py -p PROJECT
"""

import csv
import json
import math
import os
import re
import unicodedata

import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ig  # noqa: E402
import project  # noqa: E402
from classify import _brand_stem, affiliated, brands, classify, same_brand, taiwan_score  # noqa: E402

CFG = project.current()
OUT = CFG.OUT
OVERRIDES = project.json_file(os.path.join(CFG.DIR, "overrides.json"), {})
SEEDS = json.load(open(os.path.join(CFG.DIR, "seeds.json")))
SEED_SET = {h.lower() for h in SEEDS["bloggers"] + SEEDS["makers"]}

LIST_FULL = 3
STANDING_POSTS = 3
BUSINESS_EDGE = 0.4  # a business tie's weight in the PageRank, as rank.BUSINESS_WEIGHT
# Words next to a mention that show a business tie rather than a recommendation: collaborations,
# guest spots, events and stalls, supply; plus the project's own supply words (beans, flour...).
BUSINESS_WORDS = re.compile(
    r"合作|聯名|快閃|客座|進駐|駐店|出攤|攤位|市集|展覽|咖啡展|麵包祭|供應|批發|經銷|代理|贊助|寄賣|販售點|"
    r"takeover|take over|pop.?up|collab|guest|sponsor|partner|wholesale|" + CFG.SUPPLY_WORDS,
    re.I,
)
MENTION = re.compile(r"@[A-Za-z0-9._]+")


def post_tags(p):
    """[(post, accounts it tags)] for a profile's recent posts (tags, @mentions, co-authors)."""
    me = p["username"].lower()
    out = []
    for post in p["posts"]:
        hs = {h.lower() for k in ("tagged", "mentions", "coauthors") for h in post[k]} - {me}
        if hs:
            out.append((post, hs))
    return out


def business_tie(post, b):
    """Business wording on the line that mentions @b or the lines next to it (handles removed)."""
    lines = (post["caption"] or "").split("\n")
    for i, line in enumerate(lines):
        if "@" + b in line.lower():
            near = MENTION.sub(" ", " ".join(lines[max(0, i - 1):i + 2]))
            if BUSINESS_WORDS.search(near):
                return True
    return False


def letters(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", s or "").lower())


def staff_of(pa, b):
    """pa's bio names shop b in plain text (a barista's "COFFEEUNDERWATER"): staff or founder."""
    stem = _brand_stem(b)
    return len(re.sub(r"[^a-z]", "", stem)) >= 5 and stem in letters(pa.get("biography"))


def load():
    profiles = {}
    for fn in os.listdir(ig.CACHE):
        p = json.load(open(os.path.join(ig.CACHE, fn)))
        if p:
            profiles[p["username"].lower()] = p
    return profiles


STRICT = OVERRIDES.get("_strict", False)


def node_kind(p):
    """(kind, subtype, role). In strict mode only hand-reviewed accounts are
    makers/bloggers; unreviewed accounts can at most be small venues."""
    o = OVERRIDES.get(p["username"].lower())
    if o:
        kind, sub, role = (o.split(":") + ["", ""])[:3]
        return kind, sub or None, role or None
    if p["is_private"] or taiwan_score(p) < 2:
        return "other", None, None
    kind, sub = classify(p)
    if STRICT and kind in ("maker", "blogger"):
        kind = "other"
    if STRICT and kind == "venue" and p["followers"] > 60000:
        kind = "other"
    return kind, sub, None


def pagerank(nodes, edges, damping=0.85, iters=60):
    out_w = {n: 0.0 for n in nodes}
    for (a, _b), w in edges.items():
        out_w[a] += w
    # A node whose tags add up to less than one full tag passes on only that share (see rank.py).
    leak = {n: 1 - min(w, 1.0) for n, w in out_w.items()}
    out_w = {n: max(w, 1.0) for n, w in out_w.items()}
    pr = {n: 1 / len(nodes) for n in nodes}
    for _ in range(iters):
        nxt = {n: (1 - damping) / len(nodes) for n in nodes}
        dangling = sum(pr[n] * leak[n] for n in nodes)
        for n in nodes:
            nxt[n] += damping * dangling / len(nodes)
        for (a, b), w in edges.items():
            nxt[b] += damping * pr[a] * w / out_w[a]
        pr = nxt
    return pr


def main():
    profiles = load()
    kinds = {h: node_kind(p) for h, p in profiles.items()}
    keep = {h for h, (k, _, _) in kinds.items() if k in ("blogger", "maker", "venue")}

    bio = {h: profiles[h].get("biography") for h in keep}
    # Brands among the shops, so that a founder named in one branch's bio counts for all of them.
    brand = brands({h: bio[h] for h in keep if kinds[h][0] == "maker" and (kinds[h][2] or "shop") == "shop"})
    members = {}
    for h, lead in brand.items():
        members.setdefault(lead, set()).add(h)

    def tied(a, b):
        return (affiliated(a, bio[a], b, bio[b]) or staff_of(profiles[a], b) or staff_of(profiles[b], a))

    def sisters(a, b):
        """Same brand, or staff / founder accounts of one of the brand's branches."""
        if same_brand(a, bio[a], b, bio[b]):
            return True
        return any(tied(x, y) for x in members.get(brand.get(a), {a}) for y in members.get(brand.get(b), {b}))

    edges = {}  # (a, b) -> {"posts", "weight", "business"}
    for a in keep:
        for post, hs in post_tags(profiles[a]):
            share = 1.0 if len(hs) <= LIST_FULL else LIST_FULL / len(hs)
            for b in hs:
                # Sister accounts / owners tagging their own shops are not endorsements.
                if b in keep and not sisters(a, b):
                    e = edges.setdefault((a, b), {"posts": 0, "weight": 0.0, "business": False})
                    e["posts"] += 1
                    e["weight"] += share
                    e["business"] |= business_tie(post, b)
    # Business ties between two businesses: wording next to the tag, a standing tag, or the
    # reverse direction of a tie.
    business = lambda h: kinds[h][0] in ("maker", "venue")  # noqa: E731
    for (a, b), e in edges.items():
        e["business"] = business(a) and business(b) and (e["business"] or e["posts"] >= STANDING_POSTS)
    for (a, b), e in edges.items():
        if business(a) and business(b) and edges.get((b, a), {}).get("business"):
            e["business"] = True

    # Drop venues that nobody in the network points to and that point to no maker.
    def touches_core(h):
        return any(
            (a == h and kinds[b][0] != "venue") or (b == h and kinds[a][0] != "venue")
            for a, b in edges
        )

    keep = {h for h in keep if kinds[h][0] != "venue" or touches_core(h)}
    edges = {e: w for e, w in edges.items() if e[0] in keep and e[1] in keep}

    # A business tie counts once, at a low weight.
    pr = pagerank(sorted(keep), {k: BUSINESS_EDGE * min(e["weight"], 1) if e["business"] else e["weight"]
                                 for k, e in edges.items()})
    endorsers_of = {}
    for a, b in edges:
        endorsers_of.setdefault(b, set()).add(a)
    # Taste in makers: for each maker an account tags, credit how many *other*
    # accounts independently tagged the same maker (log-damped).
    hub = {
        h: sum(
            math.log2(1 + len(endorsers_of[b] - {h}))
            for a, b in edges
            if a == h and kinds[b][0] == "maker"
        )
        for h in keep
    }
    in_from = {h: {"blogger": set(), "maker": set(), "venue": set()} for h in keep}
    out_to = {h: set() for h in keep}
    for a, b in edges:
        in_from[b][kinds[a][0]].add(a)
        out_to[a].add(b)

    related_pairs = set()
    related_by = {h: set() for h in keep}
    for a in keep:
        for b in ig.related(profiles[a]):
            if b in keep and not sisters(a, b):
                related_pairs.add(tuple(sorted((a, b))))
                related_by[b].add(a)

    rows = []
    for h in keep:
        p = profiles[h]
        k, sub, role = kinds[h]
        addr = p.get("address") or {}
        rows.append(
            {
                "username": h,
                "name": p.get("full_name") or "",
                "kind": k,
                "subtype": sub or "",
                "role": role or ("shop" if k == "maker" else ""),
                "followers": p["followers"],
                "following": p["following"],
                "posts": p["media_count"],
                "endorsed_by_bloggers": len(in_from[h]["blogger"]),
                "endorsed_by_makers": len(in_from[h]["maker"]),
                "endorsed_by_venues": len(in_from[h]["venue"]),
                "endorsers": sorted(set().union(*in_from[h].values())),
                "links_out": len(out_to[h]),
                "links_out_to_makers": sum(1 for b in out_to[h] if kinds[b][0] == "maker"),
                "related_by": len(related_by[h]),
                "pagerank": pr[h] * len(keep),
                "hub": hub[h],
                "seed": h in SEED_SET,
                "city": addr.get("city_name") or "",
                "address": addr.get("street_address") or "",
                "bio": (p.get("biography") or "").replace("\n", " / "),
                "url": f"https://www.instagram.com/{h}/",
                "pic": p.get("profile_pic") or "",
            }
        )

    makers = sorted(
        (r for r in rows if r["kind"] == "maker"), key=lambda r: -r["followers"]
    )
    bloggers = sorted(
        (r for r in rows if r["kind"] == "blogger"), key=lambda r: -r["followers"]
    )
    cols = [
        "rank", "username", "name", "subtype", "role", "followers", "endorsed_by_bloggers",
        "endorsed_by_makers", "related_by", "pagerank", "hub", "links_out_to_makers", "city", "address", "bio",
        "endorsers", "url",
    ]
    for name, data in (("food_creators", makers), ("food_bloggers", bloggers)):
        with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for i, r in enumerate(data, 1):
                w.writerow(
                    {**r, "rank": i, "pagerank": f"{r['pagerank']:.2f}", "hub": f"{r['hub']:.2f}",
                     "endorsers": " ".join(r["endorsers"])}
                )

    graph = {
        "nodes": [
            {k: r[k] for k in (
                "username", "name", "kind", "subtype", "role", "followers", "bio", "url",
                "endorsed_by_bloggers", "endorsed_by_makers", "related_by", "pagerank", "hub", "seed",
                "links_out_to_makers", "city",
            )}
            for r in rows
        ],
        "links": [{"source": a, "target": b, "weight": round(e["weight"], 3), "posts": e["posts"], "type": "tag",
                   **({"business": True} if e["business"] else {})} for (a, b), e in edges.items()]
        + [{"source": a, "target": b, "weight": 1, "type": "related"} for a, b in sorted(related_pairs)],
    }
    labels = {"title": CFG.GRAPH_TITLE, "groups": CFG.GROUPS, "venue": CFG.VENUE_LABEL, "makers": CFG.MAKERS_LABEL}
    with open(os.path.join(OUT, "graph.json"), "w") as f:
        json.dump(graph, f, ensure_ascii=False)

    tmpl = open(os.path.join(ROOT, "template.html")).read()
    d3 = open(os.path.join(ROOT, "vendor", "d3.v7.min.js")).read()
    html = tmpl.replace("/*D3*/", d3).replace(
        "/*GRAPH*/null", json.dumps(graph, ensure_ascii=False)
    ).replace("/*LABELS*/null", json.dumps(labels, ensure_ascii=False))
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(html)

    n_candidates = write_candidates(profiles, kinds)
    print(f"profiles={len(profiles)} nodes={len(keep)} edges={len(edges)} related={len(related_pairs)} "
          f"makers={len(makers)} bloggers={len(bloggers)} candidates={n_candidates}")
    return makers, bloggers


def write_candidates(profiles, kinds, min_suggested=2):
    """Accounts Instagram keeps suggesting next to hand-reviewed makers/bloggers but
    that are not reviewed yet: the queue for adding to overrides.json (or fetching)."""
    reviewed = {
        h for h, v in OVERRIDES.items()
        if isinstance(v, str) and v.split(":")[0] in ("maker", "blogger") and h in profiles
    }
    suggested_by = {}
    for a in reviewed:
        for b in ig.related(profiles[a]):
            if b not in OVERRIDES:
                suggested_by.setdefault(b, set()).add(a)
    rows = []
    for h, by in suggested_by.items():
        if len(by) < min_suggested:
            continue
        p = profiles.get(h)
        rows.append({
            "username": h,
            "suggested_by": len(by),
            "fetched": "yes" if p else "no",
            "followers": p["followers"] if p else "",
            "taiwan_score": taiwan_score(p) if p else "",
            "auto_kind": ":".join(x for x in classify(p) if x) if p else "",
            "name": (p.get("full_name") or "") if p else "",
            "bio": (p.get("biography") or "").replace("\n", " / ") if p else "",
            "suggested_next_to": " ".join(sorted(by)),
            "url": f"https://www.instagram.com/{h}/",
        })
    rows.sort(key=lambda r: (-r["suggested_by"], -(r["followers"] or 0)))
    with open(os.path.join(OUT, "candidates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["username"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    main()
