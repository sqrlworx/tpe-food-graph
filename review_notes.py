"""Review notes: what Google reviewers praise and complain about, per shop.

The notes in the project's data/review_notes.json are written by reading each shop's Google
Maps material (a person, or an LLM given the export), not by this script:

  {"<handle>": {
     "summary": "One sentence for the slide, 75-160 characters.",
     "signature": ["Item in English (中文名)", ...],     # 4-6 must-try items, best known first
     "highlights": ["Recurring praise", ...],           # about 3
     "lowlights": ["Recurring complaints", ...]}}       # about 3

  export  writes output/review_input.json: for each shop near the top of the current
          ranking, its Google rating, topic chips with mention counts, review snippets and
          full review sample, plus the Instagram bio. That is the reading material.
  check   validates review_notes.json and lists shops in the top N that still lack notes.

usage: python3 -I review_notes.py -p PROJECT export [--top N]
       python3 -I review_notes.py -p PROJECT check
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402

CFG = project.current()
NOTES = os.path.join(CFG.DATA, "review_notes.json")
SUMMARY_MAX = 160  # the slide's summary paragraph fits about this much
ITEM = re.compile(r"^[^()]+\([^()]+\)$|^[^()]+$")


def ranking():
    return json.load(open(os.path.join(CFG.OUT, "ranking.json")))["rows"]


def export(top):
    google = project.data(CFG, "google_places.json", {})
    notes = project.json_file(NOTES, {})
    out = []
    for r in ranking()[:top]:
        gp = google.get(r["handle"]) or {}
        out.append({
            "handle": r["handle"],
            "rank": r["rank"],
            "has_notes": r["handle"] in notes,
            "name": r["display"],
            "google_name": r["gname"],
            "type": r["type"],
            "district": r["district"],
            "categories": r["categories"],
            "rating": r["rating"],
            "reviews": r["reviews"],
            "topics": r["topics"],
            "snippets": gp.get("snippets") or [],
            "review_texts": gp.get("review_texts") or [],
            "bio": r["bio"],
        })
    path = os.path.join(CFG.OUT, "review_input.json")
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    todo = [x["handle"] for x in out if not x["has_notes"]]
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(out)} shops, {len(todo)} without notes")


def check():
    notes = project.json_file(NOTES, {})
    problems = []
    for h, n in notes.items():
        if not isinstance(n.get("summary"), str) or not n["summary"].strip():
            problems.append(f"{h}: no summary")
        elif len(n["summary"]) > SUMMARY_MAX:
            problems.append(f"{h}: summary is {len(n['summary'])} characters (max {SUMMARY_MAX})")
        sig = n.get("signature") or []
        if not sig:
            problems.append(f"{h}: no signature items")
        problems += [f"{h}: signature item {s!r} is not 'English (中文)'" for s in sig if not ITEM.match(s)]
        for k in ("highlights", "lowlights"):
            if not isinstance(n.get(k, []), list):
                problems.append(f"{h}: {k} is not a list")
    rows = ranking()
    missing = [f"#{r['rank']} {r['handle']}" for r in rows[:CFG.TOP_N] if r["handle"] not in notes]
    print(f"{len(notes)} shops have notes; {len(problems)} problems; "
          f"{len(missing)} of the top {CFG.TOP_N} lack notes")
    for p in problems:
        print("  " + p)
    if missing:
        print("  missing: " + ", ".join(missing))
    return not problems and not missing


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["export", "check"])
    ap.add_argument("--top", type=int, help="export the top N of the current ranking (default 1.3 x TOP_N)")
    args = ap.parse_args()
    if args.command == "export":
        export(args.top or round(CFG.TOP_N * 1.3))
    else:
        sys.exit(0 if check() else 1)


if __name__ == "__main__":
    main()
