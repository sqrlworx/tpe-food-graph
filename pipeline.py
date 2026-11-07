"""Run a project through the pipeline, from Instagram crawl to Instagram countdown posts.

  python3 -I pipeline.py                      list projects
  python3 -I pipeline.py PROJECT              status: each step, what it writes, and how far along it is
  python3 -I pipeline.py PROJECT STEP ...     run steps (a manual step prints what to do)
  python3 -I pipeline.py PROJECT all          run every scripted step from build on, stopping at a
                                              manual step that isn't done
  python3 -I pipeline.py new NAME --like coffee   start a project from another one's config

Every step is a script that takes -p PROJECT; the pipeline only runs them in order. All
fetching goes through fwdproxy. See README.md for what each step does.
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402

# (name, command or None for a manual step, what it does, files it writes in the project folder)
STEPS = [
    ("seeds", None, "find articles listing shops (search.py), harvest their Instagram handles "
     "(harvest.py data/article_urls.txt > data/harvest.json) and write seeds.json", ["seeds.json"]),
    ("crawl", ["crawl.py", "300"], "fetch the seeds, then the 300 accounts they point at most "
     "(rerun to go further)", []),
    ("review", None, "label accounts in overrides.json from output/review_queue.csv "
     "(review_queue.py writes it; rerun after each crawl)", ["overrides.json"]),
    ("build", ["build.py"], "endorsement graph, creator / blogger tables", ["output/graph.json", "output/index.html"]),
    ("report", ["report.py"], "markdown summary of the graph", ["output/REPORT.md"]),
    ("google", ["google_maps.py"], "match shops to Google Maps places: rating, reviews, topics",
     ["data/google_places.json"]),
    ("prerank", ["rank.py"], "a first ranking, to pick whose press to search", ["output/ranking.json"]),
    ("search", ["press_search.py"], "search the web for coverage of the top candidates", ["data/press_search.json"]),
    ("press", ["press.py"], "merge coverage with harvested articles and trusted food blogs", ["data/press.json"]),
    ("notes", None, "write review notes for the top shops: review_notes.py export, write "
     "data/review_notes.json from output/review_input.json, then review_notes.py check", ["data/review_notes.json"]),
    ("rank", ["rank.py"], "final ranking and dashboard", ["output/ranking.json", "output/ranking.html"]),
    ("posts", ["posts.py"], "photos, slides and captions for the countdown", ["output/posts/index.html"]),
    ("photos", None, "look through output/posts/index.html; pin better photos in data/post_overrides.json "
     "(posts.py --candidates HANDLE downloads options), then run the posts step again", []),
]
AUTO_FROM = "build"


def mtime(cfg, rel):
    path = os.path.join(cfg.DIR, rel)
    return os.path.getmtime(path) if os.path.exists(path) else None


def manual_done(cfg, name):
    if name == "seeds":
        return os.path.exists(os.path.join(cfg.DIR, "seeds.json"))
    if name == "review":
        ov = project.json_file(os.path.join(cfg.DIR, "overrides.json"), {})
        return any(str(v).startswith("maker") for v in ov.values())
    if name == "notes":
        return subprocess.run([sys.executable, "-I", "review_notes.py", "-p", cfg.NAME, "check"],
                              cwd=ROOT, capture_output=True).returncode == 0
    return None  # can't tell


def status(cfg):
    print(f"project {cfg.NAME}: {cfg.DIR}")
    for name, cmd, what, outs in STEPS:
        times = [mtime(cfg, o) for o in outs]
        if cmd is None:
            done = manual_done(cfg, name)
            mark = {True: "done", False: "TODO", None: "check"}[done]
        else:
            mark = "done" if outs and all(times) else ("-" if not outs else "TODO")
        run = " ".join(["python3 -I", cmd[0], "-p", cfg.NAME, *cmd[1:]]) if cmd else "manual"
        print(f"  {name:<8} {mark:<5} {what}\n           {run}")


def run(cfg, name):
    step = next((s for s in STEPS if s[0] == name), None)
    if not step:
        raise SystemExit(f"no step {name!r}; steps: {', '.join(s[0] for s in STEPS)}")
    _, cmd, what, _ = step
    if cmd is None:
        print(f"[{name}] manual step: {what}")
        if name == "review":
            subprocess.run([sys.executable, "-I", "review_queue.py", "-p", cfg.NAME], cwd=ROOT, check=True)
        if name == "notes":
            subprocess.run([sys.executable, "-I", "review_notes.py", "-p", cfg.NAME, "export"], cwd=ROOT, check=True)
        return manual_done(cfg, name)
    print(f"[{name}] python3 -I {' '.join(cmd)} -p {cfg.NAME}", flush=True)
    subprocess.run([sys.executable, "-I", *cmd, "-p", cfg.NAME], cwd=ROOT, check=True)
    return True


def new(name, like):
    src, dst = os.path.join(project.PROJECTS, like), os.path.join(project.PROJECTS, name)
    if os.path.exists(dst):
        raise SystemExit(f"{dst} already exists")
    os.makedirs(os.path.join(dst, "data"))
    shutil.copy(os.path.join(src, "config.py"), dst)
    json.dump({"bloggers": [], "makers": [], "skip": []}, open(os.path.join(dst, "seeds.json"), "w"), indent=1)
    json.dump({"_strict": True}, open(os.path.join(dst, "overrides.json"), "w"), indent=1)
    print(f"created {dst}: edit config.py (every section), then follow: python3 -I pipeline.py {name}")


def main(args):
    if not args:
        print("projects: " + ", ".join(project.available()))
        return
    if args[0] == "new":
        if len(args) < 2:
            raise SystemExit("usage: pipeline.py new NAME [--like PROJECT]")
        like = args[args.index("--like") + 1] if "--like" in args else "coffee"
        return new(args[1], like)
    cfg = project.load(args[0])
    steps = args[1:]
    if not steps:
        return status(cfg)
    if steps == ["all"]:
        steps = [s[0] for s in STEPS[[s[0] for s in STEPS].index(AUTO_FROM):]]
        for name in steps:
            if run(cfg, name) is False:
                print(f"stopping at the manual step {name!r}; run `pipeline.py {cfg.NAME} all` again once it's done")
                return
        return
    for name in steps:
        run(cfg, name)


if __name__ == "__main__":
    main(sys.argv[1:])
