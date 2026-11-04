"""Build the endorsement graph, rankings, and the HTML visualisation.

Edge A -> B means A tagged / @mentioned / co-posted with B in one of A's
recent posts (Instagram only exposes the latest 12 posts without login).
A "related" link A - B means Instagram suggests B on A's profile (or the
reverse). Related links are drawn but do not count as endorsements.
"""

import csv
import json
import math
import os
import re

import ig
from classify import classify, taiwan_score

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

overrides_path = os.path.join(ROOT, "overrides.json")
OVERRIDES = json.load(open(overrides_path)) if os.path.exists(overrides_path) else {}
SEEDS = json.load(open(os.path.join(ROOT, "seeds.json")))
SEED_SET = {h.lower() for h in SEEDS["bloggers"] + SEEDS["makers"]}


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


def _stem(h):
    return re.sub(r"[^a-z0-9]", "", h)


def affiliated(pa, pb):
    """Same brand / owner: one names the other in its bio, or handles share a brand stem."""
    a, b = pa["username"].lower(), pb["username"].lower()
    if "@" + b in (pa.get("biography") or "").lower() or "@" + a in (pb.get("biography") or "").lower():
        return True
    sa, sb = _stem(a), _stem(b)
    n = 0
    while n < min(len(sa), len(sb)) and sa[n] == sb[n]:
        n += 1
    return n >= 6


def pagerank(nodes, edges, damping=0.85, iters=60):
    out_w = {n: 0.0 for n in nodes}
    for (a, _b), w in edges.items():
        out_w[a] += w
    pr = {n: 1 / len(nodes) for n in nodes}
    for _ in range(iters):
        nxt = {n: (1 - damping) / len(nodes) for n in nodes}
        dangling = sum(pr[n] for n in nodes if out_w[n] == 0)
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

    edges = {}
    for a in keep:
        for b, w in ig.outlinks(profiles[a]).items():
            # Sister accounts / owners tagging their own shops are not endorsements.
            if b in keep and b != a and not affiliated(profiles[a], profiles[b]):
                edges[(a, b)] = edges.get((a, b), 0) + w

    # Drop venues that nobody in the network points to and that point to no maker.
    def touches_core(h):
        return any(
            (a == h and kinds[b][0] != "venue") or (b == h and kinds[a][0] != "venue")
            for a, b in edges
        )

    keep = {h for h in keep if kinds[h][0] != "venue" or touches_core(h)}
    edges = {e: w for e, w in edges.items() if e[0] in keep and e[1] in keep}

    pr = pagerank(sorted(keep), edges)
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
            if b in keep and not affiliated(profiles[a], profiles[b]):
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
        "links": [{"source": a, "target": b, "weight": w, "type": "tag"} for (a, b), w in edges.items()]
        + [{"source": a, "target": b, "weight": 1, "type": "related"} for a, b in sorted(related_pairs)],
    }
    with open(os.path.join(OUT, "graph.json"), "w") as f:
        json.dump(graph, f, ensure_ascii=False)

    tmpl = open(os.path.join(ROOT, "template.html")).read()
    d3 = open(os.path.join(ROOT, "vendor", "d3.v7.min.js")).read()
    html = tmpl.replace("/*D3*/", d3).replace(
        "/*GRAPH*/null", json.dumps(graph, ensure_ascii=False)
    )
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
