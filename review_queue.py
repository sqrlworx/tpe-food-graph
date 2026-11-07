"""The accounts to review by hand: output/review_queue.csv.

Lists every cached, public, Taiwan-looking account the project reached that overrides.json
doesn't label yet: the seeds, accounts that seeds or reviewed makers / bloggers tag, mention
or get suggested next to, and accounts the heuristics already call a maker or blogger.
Each row has the heuristic label (auto_kind), followers, name, bio and who links to it.

Review from name and bio, then add a label per handle to the project's overrides.json:
  "maker:<subtype>"        a shop of the kind being ranked (subtypes in the config's SUBTYPES)
  "maker:<subtype>:<role>" a person or brand account, not a shop (e.g. "maker:cafe:barista")
  "blogger:"               food blogger / curator ("blogger:media" for magazines)
  "venue"                  another food business in Taiwan (shown as a hidden layer)
  "other"                  chains, overseas and non-food accounts (left out of the graph)

usage: python3 -I review_queue.py -p PROJECT
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ig  # noqa: E402
import project  # noqa: E402
from classify import classify, taiwan_score  # noqa: E402

CFG = project.current()


def main():
    overrides = project.json_file(os.path.join(CFG.DIR, "overrides.json"), {})
    seeds = json.load(open(os.path.join(CFG.DIR, "seeds.json")))
    seed_set = {h.lower() for h in seeds["bloggers"] + seeds["makers"]}
    profiles = {}
    for fn in os.listdir(ig.CACHE):
        p = json.load(open(os.path.join(ig.CACHE, fn)))
        if p:
            profiles[p["username"].lower()] = p
    auto = {h: classify(p) for h, p in profiles.items()}
    sources = {h for h in profiles if h in seed_set
               or str(overrides.get(h, "")).split(":")[0] in ("maker", "blogger")}
    linked_by = {}
    for a in sources:
        p = profiles[a]
        for b in set(ig.outlinks(p)) | set(ig.related(p)):
            linked_by.setdefault(b, set()).add(a)
    rows = []
    for h, p in profiles.items():
        if h in overrides or p["is_private"] or taiwan_score(p) < 2:
            continue
        kind, sub = auto[h]
        if not (h in seed_set or h in linked_by or kind in ("maker", "blogger")):
            continue
        rows.append({
            "username": h,
            "seed": "yes" if h in seed_set else "",
            "linked_by": len(linked_by.get(h, ())),
            "auto_kind": ":".join(x for x in (kind, sub) if x),
            "followers": p["followers"],
            "taiwan_score": taiwan_score(p),
            "name": p.get("full_name") or "",
            "bio": (p.get("biography") or "").replace("\n", " / "),
            "linked_from": " ".join(sorted(linked_by.get(h, ()))[:8]),
            "url": f"https://www.instagram.com/{h}/",
        })
    rows.sort(key=lambda r: (-r["linked_by"], -r["followers"]))
    path = os.path.join(CFG.OUT, "review_queue.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["username"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(rows)} accounts to review "
          f"({sum(1 for r in rows if r['auto_kind'].startswith('maker'))} look like makers)")


if __name__ == "__main__":
    main()
