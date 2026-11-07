"""Fetch a list of handles (one per line) into the profile cache.

usage: python3 -I fetch_list.py handles.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ig  # noqa: E402

for h in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    p = ig.profile(h)
    print(h, p["followers"] if p else "missing", flush=True)
