"""Series: ranked countdowns drawn from a project's pool, with their posts and snapshots.

A project (projects/<name>/) scores one kind of shop: rank.py writes every candidate to
output/ranking.json. A series picks from that pool and turns it into Instagram posts:

  series/<id>/
    series.json        what the series is (below)
    snapshots/<date>.json   the series frozen on a date: every candidate's rank and score, and
                       each post's shops and caption, with when and where it was published
    posts/             slides and captions from posts.py -s <id> (gitignored)
  series/index.html    the dashboard: every series, its rankings, posts and snapshots, and the
                       venues that appear in more than one series

Model: a series has entries (venues ranked within the series) and posts (installments that
count the entries down). A venue is an Instagram handle; the same venue can be an entry in
several series (No. 3 in the top 50, No. 1 in Xinyi). Snapshots are editions: snapshot a
series when its posts go out, mark each post published, and when the project is reranked a
few months later the dashboard shows what moved since.

series.json:
  {"project": "coffee",                 the pool it ranks
   "title": "...",                      dashboard name (default: the series title below)
   "top_n": 10,                         default: the project's TOP_N
   "filter": {"district": ["信義區"]},   optional: keep candidates whose field is one of these
                                        (district, area, type); a brand qualifies through any
                                        branch that matches, and is entered as that branch
   "where": "Xinyi, Taipei",            fills {where} in the wording (default "Greater Taipei")
   "posts": [[10, 1]],                  optional rank ranges per post, in posting order
                                        (default: tens, then 10-4 and the top 3)
   "series": {...}, "caption": {...},   optional: override the project's SERIES / CAPTION
   "hashtags": [...],                   optional: override the project's HASHTAGS
   "adjust": {                          optional hand edits, applied after the score order:
     "exclude": {"handle": "reason"},   left out of this series
     "pin": {"handle": {"rank": 1, "note": "..."}}}}   put at this rank; the rest fill in by score

usage:
  python3 -I series.py                          list series
  python3 -I series.py show ID                  entries and post plan
  python3 -I series.py serve [--port 8765]      the dashboard with buttons: new / edit / delete series,
                                                snapshot, publish, render posts (localhost only)
  python3 -I series.py new ID --project NAME [--top N] [--district 信義區 ...] [--area 台北市] [--type roaster]
                                                [--where "Xinyi, Taipei"]
  python3 -I series.py pin ID HANDLE RANK [--note TEXT]   hand edits to the order (see "adjust")
  python3 -I series.py unpin ID HANDLE
  python3 -I series.py exclude ID HANDLE --reason TEXT
  python3 -I series.py restore ID HANDLE
  python3 -I series.py snapshot ID [--label TEXT] [--date YYYY-MM-DD] [--replace]
  python3 -I series.py publish ID N [--url URL] [--date YYYY-MM-DD] [--snapshot DATE]
  python3 -I series.py unpublish ID N [--snapshot DATE]
  python3 -I series.py dashboard                write series/index.html

Every command that changes something rewrites the dashboard. series/index.html is read-only
(open it from disk or Drive); `serve` shows the same dashboard with editing turned on.
"""

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402

DIR = os.path.join(ROOT, "series")
DASHBOARD = os.path.join(DIR, "index.html")
# Fields a branch has of its own in ranking.json (rank.py lists branches under their brand's
# best-scoring branch); everything else on a row describes the lead branch's place.
BRANCH_FIELDS = ("handle", "display", "area", "district", "address", "rating", "reviews", "score", "ig", "maps")
# Lead-branch fields that would be wrong on another branch: its Google place and reviews, its
# Instagram audience and endorsements, and a summary that may name its neighbourhood.
LEAD_ONLY = ("gname", "name", "stars", "bayes", "topics", "categories", "match", "followers", "endorsers",
             "centrality", "related", "press", "outlets", "trusted", "comp", "contrib", "product", "bio",
             "follower_rank")
# What a snapshot keeps of each candidate.
SNAP_FIELDS = ("rank", "score_rank", "pinned", "pool_rank", "handle", "brand", "display", "type", "area", "district", "score", "comp",
               "rating", "reviews", "followers", "outlets")


def available(project_name=None):
    if not os.path.isdir(DIR):
        return []
    out = sorted(d for d in os.listdir(DIR) if os.path.exists(os.path.join(DIR, d, "series.json")))
    if project_name:
        out = [d for d in out if load(d).project == project_name]
    return out


def countdown(top):
    """(hi, lo) rank ranges in posting order: tens from the bottom, then 10-4 and the top 3."""
    out, hi = [], top
    while hi > 10:
        out.append((hi, hi - 9))
        hi -= 10
    return out + ([(10, 4), (3, 1)] if top >= 10 else [(hi, 1)])


def _values(v):
    return v if isinstance(v, list) else [v]


def _today():
    return datetime.date.today().isoformat()


class Series:
    def __init__(self, sid):
        path = os.path.join(DIR, sid, "series.json")
        if not os.path.exists(path):
            raise SystemExit(f"no series {sid!r}; series: {', '.join(available()) or 'none'}")
        self.id = sid
        self.dir = os.path.dirname(path)
        self.path = path
        self.defn = d = json.load(open(path))
        self.project = d["project"]
        self.cfg = cfg = project.load(self.project)
        self.top = d.get("top_n", cfg.TOP_N)
        self.where = d.get("where", "Greater Taipei")
        self.filter = d.get("filter") or {}
        self.adjust = normalize_adjust(d.get("adjust"))
        fmt = {"top": self.top, "where": self.where}
        self.info = {k: _fill(v, fmt) for k, v in {**cfg.SERIES, **d.get("series", {})}.items()}
        self.caption = {k: _fill(v, fmt) for k, v in {**cfg.CAPTION, **d.get("caption", {})}.items()}
        self.title = d.get("title") or self.info["title"]
        self.hashtags = d.get("hashtags", cfg.HASHTAGS)
        self.district_hashtag = d.get("district_hashtag", cfg.DISTRICT_HASHTAG)
        self.plan = [tuple(x) for x in d["posts"]] if d.get("posts") else countdown(self.top)
        ranks = sorted(k for hi, lo in self.plan for k in range(lo, hi + 1))
        if ranks != list(range(1, self.top + 1)):
            raise SystemExit(f"posts {d.get('posts')} must cover No. {self.top} to 1 once each")
        self.posts_dir = os.path.join(self.dir, "posts")
        self.snap_dir = os.path.join(self.dir, "snapshots")
        self._pool = None
        self.excluded, self.stale = [], []

    # --- Entries ----------------------------------------------------------------------

    def ranking(self):
        return project.json_file(os.path.join(self.cfg.OUT, "ranking.json"), {"meta": {}, "rows": []})

    def pool(self):
        """(candidates, project ranking meta): the project's candidates that pass the filter,
        ranked by score within the series. Each keeps its project-wide rank as pool_rank."""
        if self._pool is None:
            ranking = self.ranking()
            cands, self.excluded, self.stale = apply_adjust(pool_of(ranking["rows"], self.filter), self.adjust)
            self._pool = (cands, ranking["meta"])
        return self._pool

    def entries(self):
        return self.pool()[0][:self.top]

    # --- Snapshots --------------------------------------------------------------------

    def snapshots(self):
        """Snapshot dates, oldest first."""
        return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(self.snap_dir, "*.json")))

    def snapshot_path(self, date):
        return os.path.join(self.snap_dir, f"{date}.json")

    def read_snapshot(self, date=None):
        dates = self.snapshots()
        if not dates:
            raise SystemExit(f"{self.id} has no snapshots yet: python3 -I series.py snapshot {self.id}")
        date = date or dates[-1]
        if date not in dates:
            raise SystemExit(f"{self.id} has no snapshot {date}; snapshots: {', '.join(dates)}")
        return date, json.load(open(self.snapshot_path(date)))

    def write_snapshot(self, date, snap):
        """One candidate per line, so a retaken snapshot diffs line by line in git."""
        os.makedirs(self.snap_dir, exist_ok=True)
        head = json.dumps({k: v for k, v in snap.items() if k != "entries"}, ensure_ascii=False, indent=1)
        rows = ",\n  ".join(json.dumps(e, ensure_ascii=False) for e in snap["entries"])
        with open(self.snapshot_path(date), "w") as f:
            f.write(head[:-2] + ',\n "entries": [\n  ' + rows + "\n ]\n}\n")


def pool_of(rows, flt):
    """The ranking rows that pass a filter, ranked again by score."""
    out = [e for e in (_entry(r, flt) for r in rows) if e]
    out.sort(key=lambda e: -e["score"])
    for i, e in enumerate(out, 1):
        e["rank"] = i
    return out


# --- Hand edits ---------------------------------------------------------------------------
# series.json "adjust": {"exclude": {handle: reason}, "pin": {handle: {"rank": n, "note": "..."}}}.
# A handle names the venue as the series enters it (or its brand, for a branch entry).

def normalize_adjust(a):
    a = a or {}
    pins = {h: (v if isinstance(v, dict) else {"rank": v}) for h, v in (a.get("pin") or {}).items()}
    return {"exclude": dict(a.get("exclude") or {}), "pin": pins}


def _hit(e, handles):
    return next((h for h in (e["handle"], e.get("brand")) if h and h in handles), None)


def apply_adjust(cands, adj):
    """(entries in their final order, venues left out by hand, hand edits naming no candidate).
    Venues left out are dropped; each pinned venue takes its rank; the rest fill the other
    places in score order. score_rank is a venue's place before the pins."""
    excluded, kept = [], []
    for i, e in enumerate(cands, 1):
        h = _hit(e, adj["exclude"])
        if h:
            # score_rank: where it would be by score if it were kept
            excluded.append({**{k: v for k, v in e.items() if k != "rank"}, "score_rank": i, "reason": adj["exclude"][h]})
        else:
            kept.append(e)
    for i, e in enumerate(kept, 1):
        e["score_rank"] = i
    slots = [None] * len(kept)
    rest = []
    for e in kept:
        h = _hit(e, adj["pin"])
        if h:
            e["pinned"], e["pin_note"] = True, adj["pin"][h].get("note") or ""
        else:
            rest.append(e)
    # Pins in rank order; a pin past the end goes last, a taken place gives the next free one.
    for e in sorted((e for e in kept if e.get("pinned")), key=lambda e: adj["pin"][_hit(e, adj["pin"])]["rank"]):
        i = min(adj["pin"][_hit(e, adj["pin"])]["rank"], len(slots)) - 1
        while slots[i] is not None:
            i = (i + 1) % len(slots)
        slots[i] = e
    it = iter(rest)
    out = [s if s is not None else next(it) for s in slots]
    for i, e in enumerate(out, 1):
        e["rank"] = i
    found = {h for e in cands for h in (e["handle"], e.get("brand")) if h}
    stale = sorted(h for h in [*adj["exclude"], *adj["pin"]] if h not in found)
    return out, excluded, stale


def edit_adjust(s, action, handle=None, rank=None, note=None, reason=None):
    """Change a series' hand edits and save series.json. Actions: pin, unpin, move (pin at a rank,
    swapping with a venue already pinned there), exclude, restore, reset."""
    adj = normalize_adjust(s.defn.get("adjust"))
    cands, _ = s.pool()
    by_handle = {h: e for e in [*cands, *s.excluded] for h in (e["handle"], e.get("brand")) if h}
    if action != "reset" and handle not in by_handle and handle not in adj["pin"] and handle not in adj["exclude"]:
        raise SystemExit(f"@{handle} isn't a candidate of {s.id}")
    if action in ("pin", "move"):
        if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= len(cands):
            raise SystemExit(f"rank must be 1-{len(cands)}")
        if handle in adj["exclude"]:
            raise SystemExit(f"@{handle} is left out of this series; restore it first")
        if action == "move":
            # Whoever is pinned at the target takes this venue's current place.
            here = by_handle[handle]["rank"]
            for h, pin in adj["pin"].items():
                if pin["rank"] == rank and h != handle:
                    pin["rank"] = here
        old = adj["pin"].get(handle, {})
        adj["pin"][handle] = {"rank": rank, **({"note": note} if note else {"note": old["note"]} if old.get("note") else {})}
    elif action == "unpin":
        adj["pin"].pop(handle, None)
    elif action == "exclude":
        if not reason or not str(reason).strip():
            raise SystemExit("say why it is left out (the reason shows on the dashboard)")
        adj["pin"].pop(handle, None)
        adj["exclude"][handle] = str(reason).strip()
    elif action == "restore":
        adj["exclude"].pop(handle, None)
    elif action == "reset":
        adj = {"exclude": {}, "pin": {}}
    else:
        raise SystemExit(f"unknown action {action!r}")
    d = {k: v for k, v in s.defn.items() if k != "adjust"}
    adj = {k: v for k, v in adj.items() if v}
    if adj:
        d["adjust"] = adj
    return save_definition(s.id, d, create=False)


def _entry(r, flt):
    e = {**r, "pool_rank": r["rank"]}
    if not flt:
        return e
    branches = r.get("branches") or []
    hits = [b for b in [r, *branches] if _matches({**r, **b}, flt)]
    if not hits:
        return None
    best = max(hits, key=lambda b: b["score"])
    if best is r:
        return e
    # Entered as a branch of a brand whose best-scoring branch is elsewhere.
    e = {k: v for k, v in e.items() if k not in LEAD_ONLY}
    e.update({k: best.get(k) for k in BRANCH_FIELDS})
    e["brand"] = r["handle"]
    e["notes"] = {k: v for k, v in (r.get("notes") or {}).items() if k == "signature"}
    lead = {k: r.get(k) for k in BRANCH_FIELDS}
    e["branches"] = [lead, *(b for b in branches if b is not best)]
    return e


def _matches(row, flt):
    return all(row.get(k) in _values(v) for k, v in flt.items())


def _fill(v, fmt):
    """Fill {top} / {where} in wording, leaving other fields ({n}, {hi}, {lo}) for later."""
    if isinstance(v, str):
        return re.sub(r"\{(top|where)\}", lambda m: str(fmt[m.group(1)]), v)
    if isinstance(v, list):
        return [_fill(x, fmt) for x in v]
    return v


_loaded = {}


def load(sid):
    if sid not in _loaded:
        _loaded[sid] = Series(sid)
    return _loaded[sid]


def git_version(path):
    """The commit that last changed a file, and whether it has changed since."""
    rel = os.path.relpath(path, ROOT)
    try:
        commit = subprocess.run(["git", "log", "-1", "--format=%h %cs", "--", rel], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit or None, "modified": bool(dirty)}


def slim(e):
    return {k: e[k] for k in SNAP_FIELDS if e.get(k) is not None}


def take_snapshot(s, date, label, replace):
    import posts  # posts imports this module
    path = s.snapshot_path(date)
    old = json.load(open(path)) if os.path.exists(path) else None
    if old and not replace:
        raise SystemExit(f"{os.path.relpath(path, ROOT)} exists; pass --replace to retake it "
                         "(publication records are kept for posts whose ranks are unchanged)")
    cands, meta = s.pool()
    if not cands:
        raise SystemExit(f"{s.project} has no ranking yet: python3 -I rank.py -p {s.project}")
    plan = posts.build(s, photos={})
    published = {(p["hi"], p["lo"]): p.get("published") for p in (old or {}).get("posts", [])}
    snap = {
        "series": s.id,
        "date": date,
        "label": label or (old or {}).get("label") or "",
        "taken": datetime.datetime.now().isoformat(timespec="seconds"),
        "project": s.project,
        "ranking": git_version(os.path.join(s.cfg.OUT, "ranking.json")),
        "definition": s.defn,
        "top_n": s.top,
        "n_candidates": len(cands),
        "weights": meta.get("weights"),
        "posts": [{
            "n": p["n"], "hi": p["hi"], "lo": p["lo"], "slug": p["slug"],
            "handles": [x["handle"] for x in p["slides"][1:]],
            "caption": p["caption"],
            "published": published.get((p["hi"], p["lo"])),
        } for p in plan],
        "excluded": [{"handle": e["handle"], "display": e["display"], "reason": e["reason"]} for e in s.excluded],
        "entries": [slim(e) for e in cands],
    }
    s.write_snapshot(date, snap)
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(cands)} candidates, top {s.top} in {len(plan)} posts")


def set_published(s, n, date, value):
    date, snap = s.read_snapshot(date)
    post = next((p for p in snap["posts"] if p["n"] == n), None)
    if not post:
        raise SystemExit(f"snapshot {date} of {s.id} has posts 1-{len(snap['posts'])}")
    post["published"] = value
    s.write_snapshot(date, snap)
    state = f"published {value['date']}" + (f" at {value['url']}" if value.get("url") else "") if value else "not published"
    print(f"{s.id} {date}: post {n} (No. {post['hi']} → {post['lo']}) {state}")


# --- Series definitions ----------------------------------------------------------------

ID = re.compile(r"[a-z0-9][a-z0-9-]{1,60}")
FILTER_KEYS = ("district", "area", "type")
SERIES_KEYS = ("short", "title", "zh", "hashtag", "headline", "page_title")
CAPTION_KEYS = ("intro", "outro_last", "outro_next")
CITIES = {"台北市": "Taipei", "新北市": "New Taipei"}


def project_rows(name):
    return project.json_file(os.path.join(project.load(name).OUT, "ranking.json"), {"meta": {}, "rows": []})


def validate(d):
    """A cleaned series definition, or SystemExit with what is wrong."""
    def fail(msg):
        raise SystemExit(msg)
    if not isinstance(d, dict):
        fail("a series definition is a JSON object")
    unknown = set(d) - {"project", "title", "top_n", "filter", "where", "posts", "series", "caption", "hashtags", "adjust"}
    if unknown:
        fail(f"unknown fields: {', '.join(sorted(unknown))}")
    if d.get("project") not in project.available():
        fail(f"project must be one of {', '.join(project.available())}")
    meta = project_rows(d["project"])["meta"]
    out = {"project": d["project"]}
    if d.get("title"):
        out["title"] = _text(d["title"], "title")
    top = d.get("top_n")
    if top is not None:
        if not isinstance(top, int) or isinstance(top, bool) or not 1 <= top <= 500:
            fail("top_n must be a whole number from 1 to 500")
        out["top_n"] = top
    flt = {}
    for k, v in (d.get("filter") or {}).items():
        if k not in FILTER_KEYS:
            fail(f"filter by {', '.join(FILTER_KEYS)}, not {k!r}")
        vals = [_text(x, f"filter {k}") for x in _values(v)]
        known = {"district": meta.get("districts", {}), "area": CITIES,
                 "type": {t["k"]: 1 for t in meta.get("types", [])}}[k]
        bad = [x for x in vals if known and x not in known]
        if bad:
            fail(f"unknown {k}: {', '.join(bad)}")
        if vals:
            flt[k] = vals
    if flt:
        out["filter"] = flt
    if d.get("where"):
        out["where"] = _text(d["where"], "where")
    if d.get("posts"):
        posts = d["posts"]
        if not isinstance(posts, list) or not all(isinstance(x, list) and len(x) == 2 and all(
                isinstance(n, int) and n > 0 for n in x) and x[0] >= x[1] for x in posts):
            fail("posts is a list of [highest, lowest] rank ranges, e.g. [[10, 4], [3, 1]]")
        out["posts"] = posts
    for key, allowed in (("series", SERIES_KEYS), ("caption", CAPTION_KEYS)):
        v = {k: x for k, x in (d.get(key) or {}).items() if x not in (None, "", [])}
        bad = set(v) - set(allowed)
        if bad:
            fail(f"{key} wording can set {', '.join(allowed)}, not {', '.join(sorted(bad))}")
        for k, x in v.items():
            if k == "headline":
                if not (isinstance(x, list) and len(x) == 3 and all(isinstance(t, str) for t in x)):
                    fail("headline is three strings: lead, bold, rest")
            else:
                v[k] = _text(x, f"{key} {k}", 600)
        if v:
            out[key] = v
    if d.get("adjust"):
        a = d["adjust"]
        if not isinstance(a, dict) or set(a) - {"exclude", "pin"}:
            fail("adjust has exclude {handle: reason} and pin {handle: {rank, note}}")
        ex = {}
        for h, why in (a.get("exclude") or {}).items():
            ex[_text(h, "handle", 60)] = _text(why, f"the reason @{h} is left out")
        pins, taken = {}, set()
        for h, v in (a.get("pin") or {}).items():
            v = v if isinstance(v, dict) else {"rank": v}
            r = v.get("rank")
            if not isinstance(r, int) or isinstance(r, bool) or r < 1:
                fail(f"pin rank for @{h} must be a whole number from 1")
            if r in taken:
                fail(f"two venues are pinned at No. {r}")
            if h in ex:
                fail(f"@{h} can't be both pinned and left out")
            taken.add(r)
            pins[_text(h, "handle", 60)] = {"rank": r, **({"note": _text(v["note"], "pin note")} if v.get("note") else {})}
        adj = {k: x for k, x in (("exclude", ex), ("pin", pins)) if x}
        if adj:
            out["adjust"] = adj
    if d.get("hashtags"):
        tags = [_text(t, "hashtag") for t in _values(d["hashtags"])]
        if not all(re.fullmatch(r"#[^\s#]+", t) for t in tags):
            fail("hashtags start with # and have no spaces")
        out["hashtags"] = tags
    return out


def _text(v, what, limit=200):
    if not isinstance(v, str) or not v.strip() or len(v) > limit:
        raise SystemExit(f"{what} must be text of 1-{limit} characters")
    return v.strip()


def dump_json(d):
    """Indented JSON with short lists of numbers or strings on one line."""
    text = json.dumps(d, ensure_ascii=False, indent=1)
    return re.sub(r"\[\s*\n\s*([^\[\]{}]*?)\s*\n\s*\]",
                  lambda m: "[" + re.sub(r",\s*\n\s*", ", ", m.group(1)) + "]", text) + "\n"


def save_definition(sid, d, create):
    """Write series/<id>/series.json after checking it, and return the loaded series. If the
    result doesn't load (e.g. posts that don't cover the top N), the old file is put back."""
    if not ID.fullmatch(sid or ""):
        raise SystemExit("a series id is 2-61 lowercase letters, digits and dashes, e.g. coffee-xinyi-top10")
    d = validate(d)
    path = os.path.join(DIR, sid, "series.json")
    exists = os.path.exists(path)
    if create and exists:
        raise SystemExit(f"series {sid} already exists")
    if not create and not exists:
        raise SystemExit(f"no series {sid}")
    old = open(path).read() if exists else None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(dump_json(d))
    _loaded.pop(sid, None)
    try:
        return load(sid)
    except SystemExit:
        if old is None:
            os.remove(path)
            os.rmdir(os.path.dirname(path))
        else:
            with open(path, "w") as f:
                f.write(old)
        _loaded.pop(sid, None)
        raise


def delete_series(sid):
    """Remove a series that has no snapshots (its rendered posts go with it)."""
    s = load(sid)
    if s.snapshots():
        raise SystemExit(f"{sid} has snapshots ({', '.join(s.snapshots())}); delete them by hand if you mean it")
    import shutil
    shutil.rmtree(s.dir)
    _loaded.pop(sid, None)


def where_of(meta, flt):
    """'Xinyi, Taipei' / 'Da'an & Xinyi, Taipei' / 'New Taipei' / 'Greater Taipei' from a filter."""
    names = meta.get("districts", {})
    ds = flt.get("district") or []
    taipei = list(names)[:12]  # rank.DISTRICTS lists Taipei City's 12 districts first
    if ds:
        city = "Taipei" if all(x in taipei for x in ds) else "New Taipei" if not any(x in taipei for x in ds) else ""
        return " & ".join(names.get(x, x) for x in ds) + (f", {city}" if city else "")
    if len(flt.get("area") or []) == 1:
        return {"台北市": "Taipei City", "新北市": "New Taipei"}[flt["area"][0]]
    return "Greater Taipei"


def scaffold(project_name, top=None, flt=None, where=None):
    """A starting point for a new series: id, where, wording, and how many candidates match.
    The project's wording with its top N and place swapped for the series'."""
    cfg = project.load(project_name)
    ranking = project_rows(project_name)
    meta = ranking["meta"]
    flt = {k: _values(v) for k, v in (flt or {}).items() if v}
    top = top or cfg.TOP_N
    where = where or where_of(meta, flt)
    place = where.split(",")[0]  # "Xinyi"
    ds = flt.get("district") or []
    zh = ds[0] if len(ds) == 1 else {"台北市": "台北市", "新北市": "新北"}.get((flt.get("area") or [""])[0], "")

    def swap(v):
        if isinstance(v, list):
            return [swap(x) for x in v]
        v = re.sub(rf"(?<!\d){cfg.TOP_N}(?!\d)", str(top), v)
        if where != "Greater Taipei":
            v = v.replace("Greater Taipei", place)
            v = re.sub(r"\bTaipei's\b", f"{place}'s", v)
            v = re.sub(r"\bTaipei Top\b", f"{place} Top", v)
        if zh:
            v = v.replace("大台北", zh)
            v = re.sub(r"(?<=#)台北", zh, v)
        return v

    wording = {k: swap(cfg.SERIES[k]) for k in SERIES_KEYS if k in cfg.SERIES}
    slug = re.sub(r"[^a-z0-9]+", "-", place.lower().replace("'", "")).strip("-")
    sid = f"{project_name}-top{top}" if where == "Greater Taipei" else f"{project_name}-{slug}-top{top}"
    title = cfg.DASHBOARD.get("title", "")
    title = re.sub(rf"(?<!\d){cfg.TOP_N}(?!\d)", str(top), title)
    title = title.replace("in Greater Taipei", f"in {place}") if where != "Greater Taipei" else title
    return {"id": sid, "where": where, "title": title, "series": wording,
            "posts": [[top, 1]] if top <= 10 else None,
            "candidates": len(pool_of(ranking["rows"], flt)), "top_n": top}


def new_series(sid, project_name, top, flt, where):
    sc = scaffold(project_name, top, flt, where)
    d = {"project": project_name, "title": sc["title"], "top_n": sc["top_n"], "filter": flt or {},
         "where": sc["where"], "series": sc["series"]}
    if sc["posts"]:
        d["posts"] = sc["posts"]
    s = save_definition(sid, d, create=True)
    print(f"created {os.path.relpath(s.path, ROOT)}: {len(s.pool()[0])} candidates, top {s.top} "
          f"in {len(s.plan)} post(s). Check the wording under \"series\", then: python3 -I series.py show {sid}")


def show(s):
    cands, _ = s.pool()
    print(f"{s.id}: {s.title}")
    print(f"  project {s.project}, filter {s.filter or 'none'}, {len(cands)} candidates, top {s.top}")
    dates = s.snapshots()
    print(f"  snapshots: {', '.join(dates) if dates else 'none'}")
    live = {e["handle"] for e in s.entries()}
    if dates:
        _, snap = s.read_snapshot()
        was = {e["handle"] for e in snap["entries"] if e["rank"] <= snap["top_n"]}
        if live != was:
            print(f"  since {dates[-1]}: in {sorted(live - was)}, out {sorted(was - live)}")
        for p in snap["posts"]:
            pub = p.get("published")
            print(f"  post {p['n']}: No. {p['hi']} → {p['lo']}  "
                  + (f"published {pub['date']} {pub.get('url') or ''}" if pub else "not published"))
    for e in s.entries():
        branch = f"  (branch of {e['brand']})" if e.get("brand") else ""
        pin = f"  pinned (score rank {e['score_rank']})" if e.get("pinned") else ""
        print(f"  {e['rank']:>3} {e['score']:5.1f}  #{e['pool_rank']:<4} {e['handle']:<30} {e.get('district') or ''}{branch}{pin}")
    for e in s.excluded:
        print(f"  left out by hand: {e['handle']} ({e['reason']})")
    for h in s.stale:
        print(f"  hand edit for {h} has no effect: not a candidate of this series")


# --- Dashboard -------------------------------------------------------------------------

DASH_FIELDS = ("rank", "score_rank", "pinned", "pin_note", "pool_rank", "handle", "brand", "display", "type", "area", "district", "score", "comp",
               "rating", "reviews", "followers", "outlets", "ig", "maps")


def _rendered(s, plan):
    """Slide images posts.py has rendered for each post, relative to series/."""
    out = {}
    for p in plan:
        d = os.path.join(s.posts_dir, p["slug"])
        files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(d, "*.jpg")))
        if files:
            out[p["slug"]] = {"slides": [f"{s.id}/posts/{p['slug']}/{f}" for f in files],
                              "time": datetime.datetime.fromtimestamp(os.path.getmtime(d)).isoformat(timespec="minutes")}
    return out


def project_info(name):
    """What the dashboard shows of a project, and what the series form needs to offer: its
    districts, cities and shop types with how many candidates each has, and its default wording."""
    cfg = project.load(name)
    ranking = os.path.join(cfg.OUT, "ranking.json")
    rows = project_rows(name)
    meta = rows["meta"]
    counts = {"district": {}, "area": {}, "type": {}}
    for r in rows["rows"]:
        for k in counts:
            for v in {(b.get(k) if k != "type" else None) or r.get(k) for b in [r, *(r.get("branches") or [])]}:
                if v:
                    counts[k][v] = counts[k].get(v, 0) + 1
    return {
        "title": getattr(cfg, "LABEL", name.capitalize()),
        "ranking_html": os.path.relpath(os.path.join(cfg.OUT, "ranking.html"), DIR),
        "n_candidates": meta.get("n_candidates", 0),
        "ranked": git_version(ranking),
        "updated": datetime.datetime.fromtimestamp(os.path.getmtime(ranking)).isoformat(timespec="minutes")
        if os.path.exists(ranking) else None,
        "types": cfg.TYPES,
        "districts": meta.get("districts", {}),
        "counts": counts,
        "top_n": cfg.TOP_N,
        "hashtags": cfg.HASHTAGS,
    }


def dashboard_data():
    import posts
    projects = {name: project_info(name) for name in project.available()}
    series, venues = [], {}
    # Grouped by project, the longest countdown first.
    for sid in sorted(available(), key=lambda i: (load(i).project, -load(i).top, i)):
        s = load(sid)
        cands, meta = s.pool()
        cfg = s.cfg
        fmt = {"top": s.top, "where": s.where}
        warning = None
        if len(cands) < s.top:
            plan, warning = [], (f"Only {len(cands)} candidates for a top {s.top}: lower top_n in {os.path.relpath(s.path, ROOT)} "
                                 "or crawl more shops for this pool.")
        else:
            plan = posts.build(s, photos={})
        snaps = []
        for date in s.snapshots():
            _, snap = s.read_snapshot(date)
            snaps.append(snap)
        for e in cands:
            for h in [e["handle"], *([e["brand"]] if e.get("brand") else [])]:
                v = venues.setdefault(h, {"handle": h, "projects": []})
                if s.project not in v["projects"]:
                    v["projects"].append(s.project)
            if not venues[e["handle"]].get("display") or not e.get("brand"):
                venues[e["handle"]].update({k: e.get(k) for k in ("display", "district", "area", "ig", "maps")})
        series.append({
            "id": sid,
            "project": s.project,
            "title": s.title,
            "short": s.info.get("short", ""),
            "zh": s.info.get("zh", ""),
            "where": s.where,
            "filter": s.filter,
            "top_n": s.top,
            "theme": s.info.get("theme") or {},
            "path": os.path.relpath(s.path, ROOT),
            "posts_preview": f"{sid}/posts/index.html" if os.path.exists(os.path.join(s.posts_dir, "index.html")) else None,
            "entries": [{**{k: e.get(k) for k in DASH_FIELDS if e.get(k) is not None},
                         "summary": (e.get("notes") or {}).get("summary", "")} for e in cands],
            "posts": [{"n": p["n"], "of": p["of"], "hi": p["hi"], "lo": p["lo"], "slug": p["slug"],
                       "handles": [x["handle"] for x in p["slides"][1:]], "caption": p["caption"]} for p in plan],
            "rendered": _rendered(s, plan),
            "snapshots": snaps,
            "warning": warning,
            "excluded": [{**{k: e.get(k) for k in DASH_FIELDS if e.get(k) is not None}, "reason": e["reason"]}
                         for e in s.excluded],
            "stale": s.stale,
            # For the edit form: what series.json sets, and what each wording field falls back to.
            "defn": s.defn,
            "inherited": {"series": {k: _fill(cfg.SERIES.get(k, ""), fmt) for k in SERIES_KEYS},
                          "caption": {k: _fill(cfg.CAPTION.get(k, ""), fmt) for k in CAPTION_KEYS},
                          "title": s.info["title"], "where": "Greater Taipei", "top_n": cfg.TOP_N,
                          "posts": [list(x) for x in countdown(s.top)]},
        })
    return {"generated": datetime.datetime.now().isoformat(timespec="minutes"),
            "projects": projects, "series": series, "venues": venues}


def dashboard_html(live=None):
    """The dashboard page. live: {"token": ...} when series_server.py serves it, which turns on
    the buttons that change things; without it the page is read-only."""
    data = dashboard_data()
    data["live"] = live
    tmpl = open(os.path.join(ROOT, "series_template.html")).read()
    return tmpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), data


def write_dashboard():
    html, data = dashboard_html()
    os.makedirs(DIR, exist_ok=True)
    with open(DASHBOARD, "w") as f:
        f.write(html)
    print(f"wrote {os.path.relpath(DASHBOARD, ROOT)}: {len(data['series'])} series, {len(data['venues'])} venues")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("new")
    p.add_argument("id")
    p.add_argument("--top", type=int)
    p.add_argument("--district", nargs="+", help="Google district names, e.g. 信義區")
    p.add_argument("--area", nargs="+", help="台北市 and / or 新北市")
    p.add_argument("--type", nargs="+", help="shop types, e.g. roaster")
    p.add_argument("--where", help='fills {where} in the wording (default: from the filter, e.g. "Xinyi, Taipei")')
    p = sub.add_parser("snapshot")
    p.add_argument("id")
    p.add_argument("--label", help='e.g. "First edition"')
    p.add_argument("--date", default=_today())
    p.add_argument("--replace", action="store_true")
    for cmd in ("publish", "unpublish"):
        p = sub.add_parser(cmd)
        p.add_argument("id")
        p.add_argument("n", type=int, help="post number (1 = the first post of the countdown)")
        p.add_argument("--snapshot", help="snapshot date (default: the latest)")
        if cmd == "publish":
            p.add_argument("--url", help="the Instagram post's link")
            p.add_argument("--date", default=_today())
    p = sub.add_parser("pin", help="put a venue at a rank in this series (others keep score order)")
    p.add_argument("id")
    p.add_argument("handle")
    p.add_argument("rank", type=int)
    p.add_argument("--note", help="why, shown on the dashboard")
    p = sub.add_parser("unpin")
    p.add_argument("id")
    p.add_argument("handle")
    p = sub.add_parser("exclude", help="leave a venue out of this series")
    p.add_argument("id")
    p.add_argument("handle")
    p.add_argument("--reason", required=True)
    p = sub.add_parser("restore", help="undo exclude")
    p.add_argument("id")
    p.add_argument("handle")
    sub.add_parser("dashboard")
    p = sub.add_parser("serve", help="the dashboard with buttons to create and edit series, snapshot and publish")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1 (this machine only)")
    # -p / --project names the project for `new`; pipeline.py also passes it to the dashboard step,
    # which covers every project's series.
    project_name = project._name_from_argv()
    args = ap.parse_args()

    if args.cmd in (None, "list"):
        for sid in available():
            s = load(sid)
            dates = s.snapshots()
            print(f"{sid:<24} {s.project:<10} top {s.top:<4} {len(s.pool()[0]):>4} candidates  "
                  f"{len(s.plan):>2} posts  snapshots: {', '.join(dates) or '-'}")
        return
    if args.cmd == "show":
        return show(load(args.id))
    if args.cmd == "serve":
        import series_server
        return series_server.serve(args.host, args.port)
    if args.cmd == "new":
        if not project_name:
            raise SystemExit(f"which project does {args.id} rank? add --project NAME: {', '.join(project.available())}")
        flt = {k: v for k, v in (("district", args.district), ("area", args.area), ("type", args.type)) if v}
        new_series(args.id, project_name, args.top, flt, args.where)
    elif args.cmd in ("pin", "unpin", "exclude", "restore"):
        s = edit_adjust(load(args.id), args.cmd, args.handle.lstrip("@"), getattr(args, "rank", None),
                        getattr(args, "note", None), getattr(args, "reason", None))
        show(s)
    elif args.cmd == "snapshot":
        take_snapshot(load(args.id), args.date, args.label, args.replace)
    elif args.cmd == "publish":
        set_published(load(args.id), args.n, args.snapshot, {"date": args.date, **({"url": args.url} if args.url else {})})
    elif args.cmd == "unpublish":
        set_published(load(args.id), args.n, args.snapshot, None)
    write_dashboard()


if __name__ == "__main__":
    main()
