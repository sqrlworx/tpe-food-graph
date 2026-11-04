"""Fetch a list of handles (one per line) into the profile cache."""
import sys
import ig

for h in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    p = ig.profile(h)
    print(h, p["followers"] if p else "missing", flush=True)
