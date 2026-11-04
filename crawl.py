"""Snowball crawl: expand from seed bloggers/makers along tag/mention links.

Unfetched handles are prioritised by how many distinct Taiwan food accounts
point at them, so the request budget goes to the most-endorsed accounts first.

usage: python3 crawl.py BUDGET
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
    """Outlinks from posts plus @handles in the bio (owner/affiliate accounts)."""
    out = set(ig.outlinks(p))
    out |= {m.lower().rstrip(".") for m in ig.MENTION_RE.findall(p.get("biography") or "")}
    out.discard(p["username"])
    return out


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
            for t in ls:
                if t not in fetched and t not in SKIP:
                    score[t] = score.get(t, 0) + w
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
    main(int(sys.argv[1]))
