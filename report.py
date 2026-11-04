"""Write output/REPORT.md from the CSVs produced by build.py."""

import csv
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")


def fmt(n):
    n = int(n)
    return f"{n / 1000:.1f}K" if n < 100000 else f"{n // 1000}K"


makers = list(csv.DictReader(open(os.path.join(OUT, "food_creators.csv"))))
bloggers = list(csv.DictReader(open(os.path.join(OUT, "food_bloggers.csv"))))

lines = [
    "# Taiwan food creators × food bloggers (Instagram)",
    "",
    "Interactive graph: `index.html` (open in a browser; click a node to see who tagged it).",
    "Full data: `food_creators.csv`, `food_bloggers.csv`, `graph.json`.",
    "",
    "**Edge A → B** = A tagged / @mentioned / co-posted with B in one of A's 12 most recent posts.",
    "Links between affiliated accounts (sister shops, an owner tagging their own shop) are excluded.",
    "**Bloggers / Makers** = how many distinct food bloggers / food makers tagged the account.",
    "**Taste (creators)** = PageRank over the endorsement graph (1.0 = average).",
    "**Taste (bloggers)** = Σ over makers they tag of log₂(1 + other accounts that also tagged that maker).",
    "",
    f"## Top 50 food creators by followers ({len(makers)} total)",
    "",
    "| # | Account | Name | Type | Followers | Tagged by bloggers | Tagged by makers | Taste |",
    "|---|---|---|---|---|---|---|---|",
]
for r in makers[:50]:
    # Same grouping as the graph legend: bakeries, and sweets for every other maker.
    kind = ("bakery" if r["subtype"] == "bakery" else "sweets") + (" (chef)" if r["role"] == "chef" else "")
    lines.append(
        f"| {r['rank']} | [@{r['username']}]({r['url']}) | {r['name'][:30]} | {kind} | "
        f"{fmt(r['followers'])} | {r['endorsed_by_bloggers']} | {r['endorsed_by_makers']} | {r['pagerank']} |"
    )

by_taste = sorted(
    makers, key=lambda r: (-len(r["endorsers"].split()), -float(r["pagerank"]))
)[:20]
lines += ["", "## Most-endorsed creators (distinct accounts tagging them)", "",
          "| Account | Name | Followers | # endorsers | Taste | Tagged by |", "|---|---|---|---|---|---|"]
for r in by_taste:
    lines.append(f"| [@{r['username']}]({r['url']}) | {r['name'][:30]} | {fmt(r['followers'])} | "
                 f"{len(r['endorsers'].split())} | {r['pagerank']} | {', '.join(r['endorsers'].split()[:8])} |")

lines += ["", f"## Food bloggers & curators by followers ({len(bloggers)} total)", "",
          "| # | Account | Name | Followers | Makers tagged | Taste |", "|---|---|---|---|---|---|"]
for r in bloggers:
    name = r["name"][:34] + (" *(media/curator)*" if r["subtype"] == "media" else "")
    lines.append(f"| {r['rank']} | [@{r['username']}]({r['url']}) | {name} | {fmt(r['followers'])} | "
                 f"{r['links_out_to_makers']} | {r['hub']} |")

open(os.path.join(OUT, "REPORT.md"), "w").write("\n".join(lines) + "\n")
print("wrote REPORT.md")
