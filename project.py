"""The project a pipeline script runs for: one category of shop (bakeries, coffee, ...).

Each project lives in projects/<name>/:
  config.py       what is category-specific: classification words, ranking weights and
                  exclusions, dashboard labels, the Instagram series' title and wording
  seeds.json      crawl seeds and handles to skip
  overrides.json  hand-reviewed account labels
  data/           project inputs (Google places, press, review notes, photo picks)
  output/         graph, ranking dashboard, Instagram posts

Caches that don't depend on the category stay shared in data/: Instagram profiles,
Google Maps replies, blog post lists and search results.

Scripts pick the project from --project NAME (or -p NAME) anywhere on the command line,
else $PROJECT. The flag is removed from sys.argv so scripts parse the rest as before.
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
SHARED = os.path.join(ROOT, "data")


def available():
    return sorted(d for d in os.listdir(PROJECTS) if os.path.exists(os.path.join(PROJECTS, d, "config.py")))


def _name_from_argv():
    for flag in ("--project", "-p"):
        if flag in sys.argv[1:]:
            i = sys.argv.index(flag)
            if i + 1 >= len(sys.argv):
                raise SystemExit(f"{flag} needs a project name: {', '.join(available())}")
            name = sys.argv[i + 1]
            del sys.argv[i:i + 2]
            return name
        for i, a in enumerate(sys.argv[1:], 1):
            if a.startswith(flag + "="):
                del sys.argv[i]
                return a.split("=", 1)[1]
    return os.environ.get("PROJECT")


def load(name):
    path = os.path.join(PROJECTS, name, "config.py")
    if not os.path.exists(path):
        raise SystemExit(f"no project {name!r}; projects: {', '.join(available())}")
    spec = importlib.util.spec_from_file_location(f"projects.{name}.config", path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    cfg.NAME = name
    cfg.DIR = os.path.dirname(path)
    cfg.DATA = os.path.join(cfg.DIR, "data")
    cfg.OUT = os.path.join(cfg.DIR, "output")
    os.makedirs(cfg.DATA, exist_ok=True)
    os.makedirs(cfg.OUT, exist_ok=True)
    return cfg


_current = []


def current():
    """The project chosen on the command line; every module that asks gets the same one."""
    if not _current:
        name = _name_from_argv()
        if not name:
            raise SystemExit(f"pick a project with --project NAME (or $PROJECT): {', '.join(available())}")
        _current.append(load(name))
    return _current[0]


def data(cfg, name, default=None):
    """A project data file (JSON), or default if it doesn't exist."""
    path = os.path.join(cfg.DATA, name)
    return json.load(open(path)) if os.path.exists(path) else default


def json_file(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default
