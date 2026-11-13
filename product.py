"""What reviewers and bloggers say about the product itself (coffee, bread), per shop.

The Google rating measures a whole visit: a brunch place with good eggs and a café whose coffee
nobody mentions can both score 4.8. This step reads the texts we have about each ranked shop
and counts how many praise or criticise the product the project ranks (config PRODUCT):

  texts      each Google review in the place card (up to 5) and each review highlight (up to 3)
             from data/google_places.json, and each article linked to the shop in
             data/press.json. An article whose title names the shop counts in full; for any
             other article (a listicle), only the passages after the shop's name are read.
  judging    a text is split into clauses. A clause that names the product (PRODUCT "terms")
             and has a praise word praises it; with a complaint word, or a praise word after
             a negation (不好喝, 不推薦), it criticises it; a negated complaint (不會太苦) or
             a taste rather than a verdict (不喜歡酸的咖啡, 如果喜歡喝咖啡) doesn't count. A text praises the product when it
             has more praising clauses than criticising ones, and the other way round.
  score      (praising texts - criticising texts) / texts, shrunk towards the pool average
             by PRIOR_TEXTS, then scaled to 0..1 between the pool's 10th and 90th percentile.

Writes the project's data/product.json; rank.py uses it as the "product" signal when the
project's WEIGHTS give it a weight. Articles are fetched via fwdproxy and cached in the
gitignored data/articles/ shared by all projects.

usage: python3 -I product.py -p PROJECT                  fetch the articles, then score
       python3 -I product.py -p PROJECT fetch | score
       python3 -I product.py -p PROJECT report [--top N] [--weights network=0.25,quality=0.15,...]
"""

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402
from press import aliases, norm  # noqa: E402

CFG = project.current()
OUT_PATH = os.path.join(CFG.DATA, "product.json")
ARTICLES = os.path.join(project.SHARED, "articles")
P = CFG.PRODUCT
TERMS = re.compile(P["terms"], re.I)
PRAISE = re.compile(P["praise"], re.I)
COMPLAINT = re.compile(P["complaint"], re.I)
NEGATED = re.compile(
    r"(?:不|沒|沒有|不太|不夠|不算|不是很|不會|不會到|不至於|沒那麼|並不|稱不上|一點也不|一點都不|完全不|"
    r"(?:\bnot|n't|\bnever)\s+(?:(?:a|an|the|very|so|that|really)\s+)?)$",
    re.I,
)
# Taste words: 不喜歡酸的咖啡 or 如果喜歡喝咖啡 is about the writer, not a verdict on the cup.
TASTE = re.compile(r"喜歡|愛喝|最愛|\b(?:like|love\w*)\b", re.I)
CONDITIONAL = re.compile(r"如果|假如|若是|要是|\bif\b", re.I)
CLAUSE = re.compile(r"[。！？!?\n；;，,、~～…]+|(?<=[一-鿿])\s+(?=[一-鿿])")

PRIOR_TEXTS = 3      # a shop with few texts sits near the pool average
WINDOW = 500         # characters read after each mention of the shop in a listicle
MIN_INTERVAL = 1.5
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# Page furniture rather than the article.
BOILERPLATE = re.compile(r"版權|copyright|留言|回覆|上一篇|下一篇|相關文章|延伸閱讀|訂閱|分享到|all rights", re.I)


def judge(clause):
    """'praise', 'complaint' or 'mention' for a clause that names the product, else None."""
    if not TERMS.search(clause):
        return None
    good = bad = False
    for m in COMPLAINT.finditer(clause):
        if not NEGATED.search(clause[max(0, m.start() - 12):m.start()]):  # 不會太苦 isn't a complaint
            bad = True
    for m in PRAISE.finditer(clause):
        taste = bool(TASTE.fullmatch(m.group()))
        if NEGATED.search(clause[max(0, m.start() - 12):m.start()]):
            bad = bad or not taste
        elif not (taste and CONDITIONAL.search(clause)):
            good = True
    if good and not bad:
        return "praise"
    if bad and not good:
        return "complaint"
    return "mention"


def judge_text(text):
    """('praise' | 'complaint' | 'mention' | None, [(verdict, clause), ...])."""
    found = [(v, c) for c in CLAUSE.split(text or "") for v in [judge(c.strip())] if v]
    good = sum(v == "praise" for v, _ in found)
    bad = sum(v == "complaint" for v, _ in found)
    verdict = "praise" if good > bad else "complaint" if bad > good else "mention" if found else None
    return verdict, found


# --- Articles -------------------------------------------------------------------------

def article_path(url):
    return os.path.join(ARTICLES, hashlib.sha1(url.encode()).hexdigest() + ".html")


def fetch(urls):
    os.makedirs(ARTICLES, exist_ok=True)
    todo = [u for u in urls if not os.path.exists(article_path(u)) and not os.path.exists(article_path(u) + ".err")]
    print(f"{len(urls)} articles, {len(todo)} to fetch")
    last = 0.0
    for i, url in enumerate(todo, 1):
        time.sleep(max(0.0, MIN_INTERVAL - (time.time() - last)))
        last = time.time()
        r = subprocess.run(
            ["curl", "-sL", "--http2", "-x", "fwdproxy:8080", "--max-time", "30", "-A", UA,
             "-H", "Accept-Language: zh-TW,zh;q=0.9,en;q=0.8", "-w", "\n%{http_code}", url],
            capture_output=True, text=True, errors="replace",
        )
        body, _, code = r.stdout.rpartition("\n")
        if code == "200" and body.strip():
            open(article_path(url), "w").write(body)
        else:
            open(article_path(url) + ".err", "w").write(code or "no reply")
        if i % 20 == 0:
            print(f"  {i}/{len(todo)}", flush=True)


def article_text(raw):
    """The article's running text: tags dropped, short lines (menus, links, sidebars) skipped."""
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|section|article|blockquote)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        long_enough = len(re.findall(r"[一-鿿]", line)) >= 12 or len(line) >= 80
        if long_enough and not BOILERPLATE.search(line):
            lines.append(line)
    return "\n".join(lines)


def about_shop(text, names, dedicated):
    """The parts of an article about the shop: all of it for a dedicated post, else the
    WINDOW characters after each mention of one of its names ('' when none is found)."""
    if dedicated:
        return text
    # Map positions in the normalised text (press.norm) back to the article text.
    flat, where = [], []
    for i, ch in enumerate(text):
        for c in norm(ch):
            flat.append(c)
            where.append(i)
    flat = "".join(flat)
    spans = []
    for name in names:
        for m in re.finditer(re.escape(name), flat):
            start = where[m.start()]
            spans.append((start, start + WINDOW))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return "\n".join(text[a:b] for a, b in merged)


# --- Scoring --------------------------------------------------------------------------

def load(rel, default):
    path = os.path.join(CFG.DIR, rel)
    return json.load(open(path)) if os.path.exists(path) else default


def shop_texts(row, gp, press_items):
    """[(source, text)] for one shop; source is 'review', 'highlight' or 'article'."""
    out = [("review", r.get("text") or "") for r in gp.get("review_texts") or []]
    out += [("highlight", s) for s in gp.get("snippets") or []]
    names = aliases(row["handle"], row.get("name") or "", row.get("gname") or "")
    for item in press_items:
        path = article_path(item["url"])
        if not os.path.exists(path):
            continue
        dedicated = bool(item.get("title")) and any(n in norm(item["title"]) for n in names)
        part = about_shop(article_text(open(path, errors="replace").read()), names, dedicated)
        if part.strip():
            out.append(("article", part))
    return out


def percentile(values, q):
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0


def score():
    rows = load("output/ranking.json", {"rows": []})["rows"]
    google = load("data/google_places.json", {})
    press = load("data/press.json", {})
    stats = {}
    for row in rows:
        h = row["handle"]
        st = {"texts": 0, "articles": 0, "praise": 0, "complaint": 0, "mention": 0, "examples": {}}
        for source, text in shop_texts(row, google.get(h) or {}, press.get(h, [])):
            verdict, found = judge_text(text)
            st["texts"] += 1
            st["articles"] += source == "article"
            if verdict:
                st[verdict] += 1
            for v, clause in found:
                ex = st["examples"].setdefault(v, [])
                if v != "mention" and len(ex) < 2 and len(clause) <= 80:
                    ex.append(clause)
        st["examples"].pop("mention", None)
        stats[h] = st
    texts = sum(s["texts"] for s in stats.values())
    mean = sum(s["praise"] - s["complaint"] for s in stats.values()) / texts if texts else 0.0
    for s in stats.values():
        s["rate"] = round((s["praise"] - s["complaint"] + PRIOR_TEXTS * mean) / (s["texts"] + PRIOR_TEXTS), 4)
    lo = percentile([s["rate"] for s in stats.values()], 0.10)
    hi = percentile([s["rate"] for s in stats.values()], 0.90)
    for s in stats.values():
        s["score"] = round(min(1.0, max(0.0, (s["rate"] - lo) / (hi - lo))) if hi > lo else 0.5, 4)
    json.dump(stats, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    print(f"scored {len(stats)} shops from {texts} texts; pool mean {mean:+.3f}, "
          f"10th..90th percentile {lo:+.3f}..{hi:+.3f}")


def report(top, weights):
    data = load("output/ranking.json", {"rows": [], "meta": {}})
    stats = load("data/product.json", {})
    rows = data["rows"]
    if weights:
        for r in rows:
            comp = {**r["comp"], "product": stats.get(r["handle"], {}).get("score", 0.5)}
            r["what_if"] = 100 * sum(w * comp.get(k, 0.0) for k, w in weights.items())
        order = sorted(rows, key=lambda r: -r["what_if"])
        new_rank = {r["handle"]: i for i, r in enumerate(order, 1)}
    label = P["label"].lower()
    print(f"{'rank':>4}  {'shop':<26} {'texts':>5} {'articles':>8} {'praise':>6} {'complain':>8} {label + ' score':>12}"
          + ("   what-if" if weights else ""))
    for r in rows[:top]:
        s = stats.get(r["handle"], {})
        line = (f"{r['rank']:>4}  {r['display'][:26]:<26} {s.get('texts', 0):>5} {s.get('articles', 0):>8} "
                f"{s.get('praise', 0):>6} {s.get('complaint', 0):>8} {100 * s.get('score', 0):>12.0f}")
        if weights:
            line += f"   {new_rank[r['handle']]:>4} ({r['what_if']:.1f})"
        print(line)
    if weights:
        cut = {r["handle"] for r in rows[:top]}
        new = [r for r in order[:top] if r["handle"] not in cut]
        print("into the top %d: %s" % (top, ", ".join(f"{r['display']} (No. {r['rank']} → {new_rank[r['handle']]})"
                                                      for r in new) or "none"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="all", choices=["all", "fetch", "score", "report"])
    ap.add_argument("--top", type=int, default=CFG.TOP_N)
    ap.add_argument("--weights", help="what-if weights for report, e.g. network=0.25,quality=0.15,product=0.15,...")
    args = ap.parse_args()
    if args.cmd in ("all", "fetch"):
        rows = load("output/ranking.json", {"rows": []})["rows"]
        press = load("data/press.json", {})
        fetch(sorted({i["url"] for r in rows for i in press.get(r["handle"], [])}))
    if args.cmd in ("all", "score"):
        score()
    if args.cmd == "report":
        weights = {k: float(v) for k, v in (kv.split("=") for kv in args.weights.split(","))} if args.weights else None
        report(args.top, weights)


if __name__ == "__main__":
    main()
