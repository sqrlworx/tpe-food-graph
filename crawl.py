"""Snowball crawl: expand from seed bloggers/makers along tag/mention links
and Instagram's related-account suggestions.

Unfetched handles are prioritised by how many distinct Taiwan food accounts
point at them, so the request budget goes to the most-endorsed accounts first.
A related suggestion counts for less than a tag, but handles suggested by many
accounts still rise to the top.

usage: python3 crawl.py BUDGET
       python3 crawl.py --related BUDGET   # refetch cached accounts to get their related lists
"""

import json
import os
import sys

import ig
from classify import classify, taiwan_score

ROOT = os.path.dirname(os.path.abspath(__file__))
SEEDS = json.load(open(os.path.join(ROOT, "seeds.json")))
SKIP = set(SEEDS.get("skip", []))
EXPAND_WEIGHT = {"blogger": 1.0, "maker": 2.0, "venue": 0.3}
RELATED_WEIGHT = 0.5
_ov_path = os.path.join(ROOT, "overrides.json")
OVERRIDES = json.load(open(_ov_path)) if os.path.exists(_ov_path) else {}


def kind_of(h, p):
    """Hand-reviewed label if available; auto 'blogger' labels are noisy so damp them."""
    if h in OVERRIDES:
        return OVERRIDES[h].split(":")[0], 1.0
    kind = classify(p)[0]
    return kind, 0.3 if kind == "blogger" else 1.0


def relevant(p):
    return bool(p) and not p["is_private"] and taiwan_score(p) >= 2


def leads(p):
    """{handle: weight}: outlinks from posts and @handles in the bio (owner/affiliate
    accounts) at full weight, Instagram's related suggestions at RELATED_WEIGHT."""
    out = {h: RELATED_WEIGHT for h in ig.related(p)}
    out.update({h: 1.0 for h in ig.outlinks(p)})
    out.update({m.lower().rstrip("."): 1.0 for m in ig.MENTION_RE.findall(p.get("biography") or "")})
    out.pop(p["username"], None)
    return out


def refresh_related(budget):
    """Refetch cached accounts saved without related lists: hand-reviewed accounts
    first, then other relevant ones, largest first."""
    todo = []
    for fn in os.listdir(ig.CACHE):
        p = json.load(open(os.path.join(ig.CACHE, fn)))
        if not p or "related" in p:
            continue
        h = p["username"].lower()
        reviewed = h in OVERRIDES and OVERRIDES[h].split(":")[0] != "other"
        if reviewed or relevant(p):
            todo.append((not reviewed, -p["followers"], h))
    todo.sort()
    print(f"{len(todo)} accounts lack related lists; refreshing {min(budget, len(todo))}")
    for i, (_, _, h) in enumerate(todo[:budget], 1):
        try:
            p = ig.profile(h, need_related=True)
        except RuntimeError as e:
            print(e)
            break
        n = len(ig.related(p)) if p else "missing"
        print(f"[{i}/{budget}] {h:28s} related={n}", flush=True)


def main(budget):
    fetched = {}
    for h in SEEDS["bloggers"] + SEEDS["makers"]:
        fetched[h.lower()] = ig.profile(h)
    # Load everything already in cache too.
    for fn in os.listdir(ig.CACHE):
        h = fn[:-5]
        if h not in fetched:
            fetched[h] = json.load(open(os.path.join(ig.CACHE, fn)))

    seeds = {h.lower() for h in SEEDS["bloggers"] + SEEDS["makers"]}
    spent = 0
    is_rel = {h: relevant(p) for h, p in fetched.items()}
    base, lead_sets = {}, {}

    def prep(h, p):
        if not p:
            base[h] = 0
            return
        kind, damp = kind_of(h, p)
        reviewed = h in OVERRIDES and not h.startswith("_")
        w = EXPAND_WEIGHT.get(kind, 0) * damp if (is_rel[h] or reviewed) else 0
        base[h] = max(w, 1.0 if h in seeds else 0)
        lead_sets[h] = leads(p)

    for h, p in fetched.items():
        prep(h, p)
    while spent < budget:
        score = {}
        for h in fetched:
            w = base[h]
            if not w:
                continue
            ls = lead_sets[h]
            done = [t for t in ls if t in fetched]
            # Down-weight sources whose links mostly lead outside the Taiwan food scene.
            w *= (sum(is_rel[t] for t in done) + 1) / (len(done) + 2)
            for t, f in ls.items():
                if t not in fetched and t not in SKIP:
                    score[t] = score.get(t, 0) + w * f
        if not score:
            break
        nxt = max(score, key=score.get)
        try:
            p = ig.profile(nxt)
        except RuntimeError as e:
            print(e)
            break
        fetched[nxt] = p
        is_rel[nxt] = relevant(p)
        prep(nxt, p)
        spent += 1
        if p:
            kind, sub = classify(p)
            print(
                f"[{spent}/{budget}] {nxt:28s} score={score[nxt]:.1f} "
                f"tw={taiwan_score(p)} {kind:7s} {p['followers']:>8}  "
                f"{(p['full_name'] or '')[:30]}",
                flush=True,
            )
        else:
            print(f"[{spent}/{budget}] {nxt:28s} missing", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--related":
        refresh_related(int(sys.argv[2]))
    else:
        main(int(sys.argv[1]))
