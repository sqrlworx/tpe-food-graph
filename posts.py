"""Turn a project's ranking into a countdown series of Instagram carousel posts.

The series counts down the top N in tens: e.g. No. 100-91, 90-81, ... 20-11, then 10-4 and
the top 3. Each post is a title card (same layout every time, only the rank range changes)
followed by one slide per shop, showing a photo from one of the shop's own recent Instagram
posts. The series title, caption wording, hashtags and slide colours come from the project
config.

Writes, under the project's output/posts/:
  NN_hi-lo/        one folder per post, ready to upload
    00_title.jpg, 01_no100_<handle>.jpg, ...   slides in carousel order (1080x1350)
    caption.txt    the caption to paste: shop details, @mentions, hashtags
    post.json      the post's template: slide data, alt text and accounts to tag per slide
  photos/          the photo picked for each shop, and photos.json (handle -> IG shortcode)
  slides.html      slide_template.html filled with every post; #<post>/<slide> shows one slide
  index.html       preview of the series: profile grid, each carousel and its caption

Photos are picked from IG's alt text (food beats posters, menus and text overlays).
Pin a different photo, or reword a slide, in the project's data/post_overrides.json:
  {"<handle>": {"photo": "<post shortcode>", "name": "...", "summary": "...", "signature": ["...", ...]}}

Rendering uses headless Chromium (Playwright's download, or $CHROME).

usage: python3 -I posts.py -p PROJECT [--no-fetch] [--no-render] [--post N ...]
"""

import argparse
import collections
import concurrent.futures
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import ig  # noqa: E402
import project  # noqa: E402

CFG = project.current()
OUT = os.path.join(CFG.OUT, "posts")
PHOTOS = os.path.join(OUT, "photos")
OVERRIDES = os.path.join(CFG.DATA, "post_overrides.json")

SERIES = dict(CFG.SERIES)
CAPTION = CFG.CAPTION
# Instagram caps captions at 2,200 characters and, since Dec 2025, posts at 5 hashtags.
CAPTION_MAX = 2200
HASHTAG_MAX = 5
CITY = {"台北市": "Taipei", "新北市": "New Taipei"}
TYPE = CFG.TYPES
MEDAL = {1: "gold", 2: "silver", 3: "bronze"}
MEDAL_EMOJI = {"gold": "🥇", "silver": "🥈", "bronze": "🥉"}

# What a good photo shows, in IG's alt text.
FOOD = CFG.PHOTO_SUBJECT
TEXTY = re.compile(r"\b(poster|doodle|menu|screenshot|map|qr code|diagram|logo|card|calendar)\b", re.I)
PEOPLE = re.compile(r"\b(people|person|child|baby|smiling)\b", re.I)
# Headlines of notices rather than food posts: closures, opening days, winners, pop-ups, order rules.
NOTICE = re.compile(
    r"公告|公休|休假|營業時間|營業日|暫停營業|中獎|抽獎|得獎|名單|入選|快閃|說明|招募|徵才|截止|"
    r"announcement|giveaway|closed",
    re.I,
)


def batches(top):
    """(hi, lo) rank ranges in posting order."""
    out, hi = [], top
    while hi > 10:
        out.append((hi, hi - 9))
        hi -= 10
    return out + [(10, 4), (3, 1)]


def photo_score(post, handle, i):
    alt = post.get("alt") or ""
    s = min(len(set(m.lower() for m in FOOD.findall(alt))), 3) * 2.0
    s -= 3.0 * bool(TEXTY.search(alt))
    s -= 1.5 * bool(re.search(r"\btext\b", alt))
    s -= 2.0 * ("text that says" in alt)  # IG read a lot of words off the image
    headline = re.sub(r"\s+", "", (post.get("caption") or "").split("\n")[0])[:40]
    s -= 4.0 * bool(NOTICE.search(headline))
    s -= 1.0 * bool(PEOPLE.search(alt))
    s -= 1.0 * (post.get("kind") == "clips")
    s -= 2.0 * (post.get("owner", handle) != handle)
    return s - 0.15 * i  # prefer recent posts on ties


def candidates(handle, fetch):
    """The profile's posts, best photo first."""
    path = os.path.join(ig.CACHE, handle + ".json")
    if not fetch and not os.path.exists(path):
        return []
    p = ig.profile(handle)
    # Profiles cached before alt text was kept can't be judged; refetch them.
    if fetch and p and p["posts"] and "alt" not in p["posts"][0]:
        p = ig.profile(handle, refresh=True)
    if not p:
        return []
    posts = p["posts"]
    return sorted(posts, key=lambda q: -photo_score(q, handle, posts.index(q)))


def pick_photos(rows, overrides, fetch):
    """handle -> {"shortcode", "owner"} for each shop whose photo is downloaded.

    The pick is recomputed from the cached profile on every run; a photo is only
    downloaded when the pick differs from the one already on disk."""
    os.makedirs(PHOTOS, exist_ok=True)
    index_path = os.path.join(PHOTOS, "photos.json")
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    out = {}
    for r in rows:
        h = r["handle"]
        file = os.path.join(PHOTOS, h + ".jpg")
        have = index.get(h) if os.path.exists(file) else None
        try:
            posts = candidates(h, fetch)
        except RuntimeError as e:
            print(f"  {h}: {e}")
            posts = []
        pinned = overrides.get(h, {}).get("photo")
        if pinned:
            posts = [q for q in posts if q["shortcode"] == pinned] or [{"shortcode": pinned, "owner": h}]
        if have and (not posts or have["shortcode"] == posts[0]["shortcode"] or not fetch):
            out[h] = have
            continue
        if not fetch:
            continue
        for q in posts[:4]:
            picked = glob.glob(os.path.join(PHOTOS, "candidates", h, f"*_{q['shortcode']}.jpg"))
            if picked:
                shutil.copy(picked[0], file)
            if picked or ig.photo(q["shortcode"], file):
                out[h] = index[h] = {"shortcode": q["shortcode"], "owner": q.get("owner") or h}
                print(f"  #{r['rank']} {h}: {q['shortcode']}  {(q.get('alt') or '')[-80:]}")
                break
        else:
            print(f"  #{r['rank']} {h}: no photo")
            if have:
                out[h] = have
        json.dump(index, open(index_path, "w"), indent=1, ensure_ascii=False)
    return out


def download_candidates(handles, n):
    """Save a shop's best-scoring photos as photos/candidates/<handle>/<i>_<shortcode>.jpg.
    Pin one with {"<handle>": {"photo": "<shortcode>"}} in data/post_overrides.json."""
    for h in handles:
        h = h.lower().lstrip("@")
        d = os.path.join(PHOTOS, "candidates", h)
        os.makedirs(d, exist_ok=True)
        for i, q in enumerate(candidates(h, fetch=True)[:n], 1):
            path = os.path.join(d, f"{i}_{q['shortcode']}.jpg")
            if os.path.exists(path) or ig.photo(q["shortcode"], path):
                print(f"  {os.path.relpath(path, ROOT)}  {(q.get('alt') or '')[-70:]}")


def split_item(s):
    """'Red guava (紅心芭樂)' -> ('Red guava', '紅心芭樂')."""
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", s)
    return (m.group(1), m.group(2)) if m else (s, "")


def place(r, districts):
    city = CITY.get(r["area"], r["area"])
    d = districts.get(r["district"])
    return f"{d}, {city}" if d else city


def shop(r, districts, photo, ov):
    notes = r.get("notes") or {}
    sig = ov.get("signature") or notes.get("signature") or [t for t, _ in r.get("topics", [])[:3]]
    return {
        "kind": "shop",
        "rank": r["rank"],
        "medal": MEDAL.get(r["rank"]),
        "handle": r["handle"],
        "name": ov.get("name") or r["display"],
        "type": TYPE.get(r["type"], r["type"].title()),
        "place": place(r, districts),
        "district_zh": r["district"],
        "rating": r.get("rating"),
        "reviews": r.get("reviews"),
        "summary": ov.get("summary") or notes.get("summary", ""),
        "signature": [split_item(s) for s in sig[:4]],
        "maps": r.get("maps"),
        # Other branches of the same brand (rank.py lists them under the best-scoring one).
        "branches": [{"handle": b["handle"], "place": place(b, districts)} for b in r.get("branches", [])],
        "photo": f"photos/{r['handle']}.jpg" if photo else None,
        "credit": photo["owner"] if photo else None,
        "photo_source": f"https://www.instagram.com/p/{photo['shortcode']}/" if photo else None,
    }


def alt_text(s):
    known = ", ".join(en for en, _ in s["signature"][:2]).lower()
    alt = f"No. {s['rank']} {s['name']}, {s['type'].lower()} in {s['place']}"
    return f"{alt}, known for {known}" if known else alt


def entry(s, level):
    medal = MEDAL_EMOJI[s["medal"]] + " " if s["medal"] else ""
    lines = [f"{medal}No. {s['rank']} · {s['name']} @{s['handle']}"]
    where = f"📍 {s['place']}"
    if s["rating"]:
        where += f" · ⭐ {s['rating']:.1f} ({s['reviews']:,} reviews)"
    lines.append(where)
    if s["branches"]:
        lines.append("Also: " + " · ".join(f"@{b['handle']} ({b['place']})" for b in s["branches"]))
    n_sig = (3, 3, 2, 0)[level]
    if n_sig and s["signature"]:
        lines.append(CAPTION["item_emoji"] + " " + ", ".join(f"{en} ({zh})" if zh else en for en, zh in s["signature"][:n_sig]))
    if level == 0 and s["summary"]:
        lines.append(s["summary"])
    return "\n".join(lines)


def hashtags(shops):
    district = collections.Counter(s["district_zh"] for s in shops if s["district_zh"]).most_common(1)
    tags = list(CFG.HASHTAGS)
    if district:
        tags.append(CFG.DISTRICT_HASHTAG.format(district=district[0][0]))
    tags.append(SERIES["hashtag"])
    return tags[:HASHTAG_MAX]


def caption(post, shops, tags, n_candidates):
    n, of, hi, lo = post["n"], post["of"], post["hi"], post["lo"]
    head = f"{SERIES['title']} {CAPTION['emoji']} Part {n}/{of}: No. {hi} → {lo}"
    if lo == 1:
        head = f"{SERIES['title']} 👑 The top 3"
    intro = CAPTION["intro"].format(n=n_candidates)
    if n == 1:
        intro += " The countdown starts here."
    if lo == 1:
        outro = CAPTION["outro_last"]
    else:
        nhi, nlo = post["next"]
        outro = CAPTION["outro_next"].format(hi=nhi, lo=nlo)
    for level in range(4):
        text = "\n\n".join([head, intro, *(entry(s, level) for s in shops), outro, " ".join(tags)])
        if len(text) <= CAPTION_MAX:
            return text
    return text


def chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    home = os.path.expanduser("~/.cache/ms-playwright")
    for pat in ("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
                "chromium-*/chrome-linux*/chrome"):
        found = sorted(glob.glob(os.path.join(home, pat)))
        if found:
            return found[-1]
    for name in ("chrome-headless-shell", "chromium", "chromium-browser", "google-chrome"):
        if shutil.which(name):
            return shutil.which(name)
    raise SystemExit("no Chromium found; set $CHROME or run with --no-render")


def shoot(exe, url, out):
    subprocess.run(
        [exe, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         "--window-size=1080,1350", "--virtual-time-budget=10000", "--screenshot-quality=92",
         f"--screenshot={out}", url],
        check=True, capture_output=True, timeout=120,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-fetch", action="store_true", help="only use photos already downloaded")
    ap.add_argument("--no-render", action="store_true", help="write data and captions, skip slide images")
    ap.add_argument("--post", type=int, nargs="*", help="only render these post numbers (1 = No. 100-91)")
    ap.add_argument("--candidates", nargs="+", metavar="HANDLE",
                    help="download each shop's top photo picks to photos/candidates/ to choose from, then exit")
    ap.add_argument("-n", type=int, default=6, help="how many candidates per shop (default 6)")
    args = ap.parse_args()
    if args.candidates:
        return download_candidates(args.candidates, args.n)

    ranking = json.load(open(os.path.join(CFG.OUT, "ranking.json")))
    meta = ranking["meta"]
    top = meta["top_n"]
    rows = [r for r in ranking["rows"] if r["rank"] <= top]
    overrides = json.load(open(OVERRIDES)) if os.path.exists(OVERRIDES) else {}
    overrides = {k: v for k, v in overrides.items() if not k.startswith("_")}

    print(f"photos for {len(rows)} shops")
    photos = pick_photos(rows, overrides, fetch=not args.no_fetch)
    SERIES["method"] = (
        f"Ranked from {meta['n_candidates']} Greater Taipei shops by food-creator tags, "
        "Google reviews and press coverage."
    )

    by_rank = {r["rank"]: r for r in rows}
    ranges = batches(top)
    posts = []
    for n, (hi, lo) in enumerate(ranges, 1):
        post = {"n": n, "of": len(ranges), "hi": hi, "lo": lo, "slug": f"{n:02d}_{hi}-{lo}",
                "next": ranges[n] if n < len(ranges) else None}
        shops = [
            shop(by_rank[k], meta["districts"], photos.get(by_rank[k]["handle"]),
                 overrides.get(by_rank[k]["handle"], {}))
            for k in range(hi, lo - 1, -1)
        ]
        tags = hashtags(shops)
        title = {
            "kind": "title", "file": "00_title.jpg", "tag": [],
            "alt": f"{SERIES['title']}, part {n} of {len(ranges)}: No. {hi} to {lo}",
        }
        for i, s in enumerate(shops, 1):
            s["file"] = f"{i:02d}_no{s['rank']}_{s['handle']}.jpg"
            s["alt"] = alt_text(s)
            s["tag"] = list(dict.fromkeys([s["handle"], s["credit"] or s["handle"]]))
        post.update(
            slides=[title, *shops],
            caption=caption(post, shops, tags, meta["n_candidates"]),
            hashtags=tags,
            mentions=[h for s in shops for h in [s["handle"], *(b["handle"] for b in s["branches"])]],
            location=SERIES["location"],
        )
        posts.append(post)

    os.makedirs(OUT, exist_ok=True)
    data = {"series": SERIES, "posts": posts}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    tmpl = open(os.path.join(ROOT, "slide_template.html")).read()
    open(os.path.join(OUT, "slides.html"), "w").write(tmpl.replace("/*DATA*/null", blob))
    tmpl = open(os.path.join(ROOT, "posts_template.html")).read()
    open(os.path.join(OUT, "index.html"), "w").write(tmpl.replace("/*DATA*/null", blob))

    todo = []
    for post in posts:
        d = os.path.join(OUT, post["slug"])
        if args.post and post["n"] not in args.post:
            continue
        if os.path.isdir(d) and not args.no_render:
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "caption.txt"), "w").write(post["caption"] + "\n")
        json.dump(post, open(os.path.join(d, "post.json"), "w"), indent=1, ensure_ascii=False)
        for i, s in enumerate(post["slides"]):
            todo.append((f"file://{OUT}/slides.html#{post['n']}/{i}", os.path.join(d, s["file"])))

    if not args.no_render:
        exe = chrome()
        print(f"rendering {len(todo)} slides with {exe}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda t: shoot(exe, *t), todo))

    missing = [s["rank"] for p in posts for s in p["slides"][1:] if not s["photo"]]
    print(f"wrote {len(posts)} posts to {os.path.relpath(OUT, ROOT)}/ (index.html to preview)")
    if missing:
        print(f"no photo for ranks {missing}; add one in {os.path.relpath(OVERRIDES, ROOT)}")
    for p in posts:
        print(f"  {p['slug']}: caption {len(p['caption'])} chars")


if __name__ == "__main__":
    main()
