"""Turn a series' entries into a countdown of Instagram carousel posts.

A series (series.py) ranks a project's candidates, all of them or a filtered set, and splits
its top N into posts: by default tens, e.g. No. 100-91, 90-81, ... 20-11, then 10-4 and the
top 3. Each post is a title card (same layout every time, only the rank range changes)
followed by one slide per shop, showing a photo from one of the shop's own recent Instagram
posts. The series title, caption wording, hashtags and slide colours come from the project
config, overridden by the series' series.json.

Writes, under series/<id>/posts/:
  NN_hi-lo/        one folder per post, ready to upload
    00_title.jpg, 01_no100_<handle>.jpg, ...   slides in carousel order (1080x1350)
    caption.txt    the caption to paste: shop details, @mentions, hashtags
    post.json      the post's template: slide data, alt text and accounts to tag per slide
  photos/          the photos the slides show, copied from the project's photo cache
  slides.html      slide_template.html filled with every post; #<post>/<slide> shows one slide
  index.html       preview of the series: profile grid, each carousel and its caption

Photos are picked from IG's alt text (food beats posters, menus and text overlays) and cached
per project in projects/<name>/output/photos/ (with photos.json: handle -> IG shortcode), so
series of one project share them. Pin a different photo, or reword a slide, in the project's
data/post_overrides.json:
  {"<handle>": {"photo": "<post shortcode>", "name": "...", "summary": "...", "signature": ["...", ...]}}

Rendering uses headless Chromium (Playwright's download, or $CHROME).

usage: python3 -I posts.py -s SERIES [-s SERIES ...] [--no-fetch] [--no-render] [--post N ...]
       python3 -I posts.py -p PROJECT [...]     every series of the project
       python3 -I posts.py -p PROJECT --candidates HANDLE ...
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
import series as series_mod  # noqa: E402

# Instagram caps captions at 2,200 characters and, since Dec 2025, posts at 5 hashtags.
CAPTION_MAX = 2200
HASHTAG_MAX = 5
CITY = {"台北市": "Taipei", "新北市": "New Taipei"}
MEDAL = {1: "gold", 2: "silver", 3: "bronze"}
MEDAL_EMOJI = {"gold": "🥇", "silver": "🥈", "bronze": "🥉"}
TEXTY = re.compile(r"\b(poster|doodle|menu|screenshot|map|qr code|diagram|logo|card|calendar)\b", re.I)
PEOPLE = re.compile(r"\b(people|person|child|baby|smiling)\b", re.I)
# Headlines of notices rather than food posts: closures, opening days, winners, pop-ups, order rules.
NOTICE = re.compile(
    r"公告|公休|休假|營業時間|營業日|暫停營業|中獎|抽獎|得獎|名單|入選|快閃|說明|招募|徵才|截止|"
    r"announcement|giveaway|closed",
    re.I,
)


def photo_dir(cfg):
    """The project's photo cache, shared by its series. It used to sit in output/posts/photos."""
    d = os.path.join(cfg.OUT, "photos")
    old = os.path.join(cfg.OUT, "posts", "photos")
    if not os.path.exists(d) and os.path.isdir(old):
        shutil.move(old, d)
    return d


def overrides_of(cfg):
    ov = project.data(cfg, "post_overrides.json", {})
    return {k: v for k, v in ov.items() if not k.startswith("_")}


def photo_score(post, handle, i, food):
    """food: what a good photo shows in IG's alt text (the project's PHOTO_SUBJECT)."""
    alt = post.get("alt") or ""
    s = min(len(set(m.lower() for m in food.findall(alt))), 3) * 2.0
    s -= 3.0 * bool(TEXTY.search(alt))
    s -= 1.5 * bool(re.search(r"\btext\b", alt))
    s -= 2.0 * ("text that says" in alt)  # IG read a lot of words off the image
    headline = re.sub(r"\s+", "", (post.get("caption") or "").split("\n")[0])[:40]
    s -= 4.0 * bool(NOTICE.search(headline))
    s -= 1.0 * bool(PEOPLE.search(alt))
    s -= 1.0 * (post.get("kind") == "clips")
    s -= 2.0 * (post.get("owner", handle) != handle)
    return s - 0.15 * i  # prefer recent posts on ties


def candidates(handle, fetch, food):
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
    return sorted(posts, key=lambda q: -photo_score(q, handle, posts.index(q), food))


def pick_photos(cfg, rows, overrides, fetch):
    """handle -> {"shortcode", "owner"} for each shop whose photo is downloaded.

    The pick is recomputed from the cached profile on every run; a photo is only
    downloaded when the pick differs from the one already on disk."""
    photos = photo_dir(cfg)
    os.makedirs(photos, exist_ok=True)
    index_path = os.path.join(photos, "photos.json")
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    out = {}
    for r in rows:
        h = r["handle"]
        file = os.path.join(photos, h + ".jpg")
        have = index.get(h) if os.path.exists(file) else None
        try:
            posts = candidates(h, fetch, cfg.PHOTO_SUBJECT)
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
            picked = glob.glob(os.path.join(photos, "candidates", h, f"*_{q['shortcode']}.jpg"))
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


def download_candidates(cfg, handles, n):
    """Save a shop's best-scoring photos as photos/candidates/<handle>/<i>_<shortcode>.jpg.
    Pin one with {"<handle>": {"photo": "<shortcode>"}} in data/post_overrides.json."""
    for h in handles:
        h = h.lower().lstrip("@")
        d = os.path.join(photo_dir(cfg), "candidates", h)
        os.makedirs(d, exist_ok=True)
        for i, q in enumerate(candidates(h, True, cfg.PHOTO_SUBJECT)[:n], 1):
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


def shop(r, districts, types, photo, ov):
    notes = r.get("notes") or {}
    sig = ov.get("signature") or notes.get("signature") or [t for t, _ in r.get("topics", [])[:3]]
    return {
        "kind": "shop",
        "rank": r["rank"],
        "medal": MEDAL.get(r["rank"]),
        "handle": r["handle"],
        "name": ov.get("name") or r["display"],
        "type": types.get(r["type"], r["type"].title()),
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


def entry(s, level, item_emoji):
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
        lines.append(item_emoji + " " + ", ".join(f"{en} ({zh})" if zh else en for en, zh in s["signature"][:n_sig]))
    if level == 0 and s["summary"]:
        lines.append(s["summary"])
    return "\n".join(lines)


def hashtags(s, shops):
    district = collections.Counter(x["district_zh"] for x in shops if x["district_zh"]).most_common(1)
    tags = list(s.hashtags)
    if district:
        tags.append(s.district_hashtag.format(district=district[0][0]))
    tags.append(s.info["hashtag"])
    return tags[:HASHTAG_MAX]


def caption(s, post, shops, tags, n_candidates):
    n, of, hi, lo = post["n"], post["of"], post["hi"], post["lo"]
    title, cap = s.info["title"], s.caption
    if of == 1:
        head = f"{title} {cap['emoji']} No. {hi} → {lo}"
    elif lo == 1:
        head = f"{title} 👑 The top {hi}"
    else:
        head = f"{title} {cap['emoji']} Part {n}/{of}: No. {hi} → {lo}"
    intro = cap["intro"].format(n=n_candidates)
    if n == 1 and of > 1:
        intro += " The countdown starts here."
    if lo == 1:
        outro = cap["outro_last"]
    else:
        nhi, nlo = post["next"]
        outro = cap["outro_next"].format(hi=nhi, lo=nlo)
    for level in range(4):
        text = "\n\n".join([head, intro, *(entry(x, level, cap["item_emoji"]) for x in shops), outro, " ".join(tags)])
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


def build(s, photos):
    """The series' posts: slides, captions, hashtags and @mentions. photos: handle -> the
    picked photo ({"shortcode", "owner"}); with {} the slides have no photos but the captions
    are final."""
    cands, meta = s.pool()
    by_rank = {r["rank"]: r for r in cands[:s.top]}
    if len(by_rank) < s.top:
        raise SystemExit(f"{s.id}: top {s.top} but only {len(by_rank)} candidates")
    overrides = overrides_of(s.cfg)
    info = s.info
    posts = []
    for n, (hi, lo) in enumerate(s.plan, 1):
        post = {"n": n, "of": len(s.plan), "hi": hi, "lo": lo, "slug": f"{n:02d}_{hi}-{lo}",
                "next": s.plan[n] if n < len(s.plan) else None}
        shops = [
            shop(by_rank[k], meta["districts"], s.cfg.TYPES, photos.get(by_rank[k]["handle"]),
                 overrides.get(by_rank[k]["handle"], {}))
            for k in range(hi, lo - 1, -1)
        ]
        tags = hashtags(s, shops)
        title = {
            "kind": "title", "file": "00_title.jpg", "tag": [],
            "alt": f"{info['title']}, part {n} of {len(s.plan)}: No. {hi} to {lo}" if len(s.plan) > 1
            else f"{info['title']}: No. {hi} to {lo}",
        }
        for i, x in enumerate(shops, 1):
            x["file"] = f"{i:02d}_no{x['rank']}_{x['handle']}.jpg"
            x["alt"] = alt_text(x)
            x["tag"] = list(dict.fromkeys([x["handle"], x["credit"] or x["handle"]]))
        post.update(
            slides=[title, *shops],
            caption=caption(s, post, shops, tags, len(cands)),
            hashtags=tags,
            mentions=[h for x in shops for h in [x["handle"], *(b["handle"] for b in x["branches"])]],
            location=info["location"],
        )
        posts.append(post)
    return posts


def write(s, args):
    out = s.posts_dir
    rows = s.entries()
    print(f"[{s.id}] photos for {len(rows)} shops")
    picked = pick_photos(s.cfg, rows, overrides_of(s.cfg), fetch=not args.no_fetch)
    posts = build(s, picked)
    info = {**s.info, "method": f"Ranked from {len(s.pool()[0])} {s.where} shops by food-creator tags, "
                                "Google reviews and press coverage."}

    # The slides show photos/<handle>.jpg: copy this series' picks from the project cache.
    os.makedirs(os.path.join(out, "photos"), exist_ok=True)
    cache = photo_dir(s.cfg)
    for h in picked:
        src, dst = os.path.join(cache, h + ".jpg"), os.path.join(out, "photos", h + ".jpg")
        if os.path.exists(src) and (not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src)):
            shutil.copy2(src, dst)

    data = {"series": info, "posts": posts}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    tmpl = open(os.path.join(ROOT, "slide_template.html")).read()
    open(os.path.join(out, "slides.html"), "w").write(tmpl.replace("/*DATA*/null", blob))
    tmpl = open(os.path.join(ROOT, "posts_template.html")).read()
    open(os.path.join(out, "index.html"), "w").write(tmpl.replace("/*DATA*/null", blob))

    todo = []
    for post in posts:
        d = os.path.join(out, post["slug"])
        if args.post and post["n"] not in args.post:
            continue
        if os.path.isdir(d) and not args.no_render:
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "caption.txt"), "w").write(post["caption"] + "\n")
        json.dump(post, open(os.path.join(d, "post.json"), "w"), indent=1, ensure_ascii=False)
        for i, x in enumerate(post["slides"]):
            todo.append((f"file://{out}/slides.html#{post['n']}/{i}", os.path.join(d, x["file"])))

    if not args.no_render:
        exe = chrome()
        print(f"rendering {len(todo)} slides with {exe}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda t: shoot(exe, *t), todo))

    missing = [x["rank"] for p in posts for x in p["slides"][1:] if not x["photo"]]
    print(f"wrote {len(posts)} posts to {os.path.relpath(out, ROOT)}/ (index.html to preview)")
    if missing:
        print(f"no photo for ranks {missing}; add one in "
              f"{os.path.relpath(os.path.join(s.cfg.DATA, 'post_overrides.json'), ROOT)}")
    for p in posts:
        print(f"  {p['slug']}: caption {len(p['caption'])} chars")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-s", "--series", action="append", help="a series id (series/<id>/); repeat for more")
    ap.add_argument("-p", "--project", help="every series of this project")
    ap.add_argument("--no-fetch", action="store_true", help="only use photos already downloaded")
    ap.add_argument("--no-render", action="store_true", help="write data and captions, skip slide images")
    ap.add_argument("--post", type=int, nargs="*", help="only render these post numbers (1 = the first post)")
    ap.add_argument("--candidates", nargs="+", metavar="HANDLE",
                    help="download each shop's top photo picks to the project's photos/candidates/ to choose "
                         "from, then exit")
    ap.add_argument("-n", type=int, default=6, help="how many candidates per shop (default 6)")
    args = ap.parse_args()
    if args.candidates:
        name = args.project or (series_mod.load(args.series[0]).project if args.series else None)
        if not name:
            raise SystemExit("--candidates needs -p PROJECT (or -s SERIES)")
        return download_candidates(project.load(name), args.candidates, args.n)
    ids = args.series or (series_mod.available(args.project) if args.project else [])
    if not ids:
        raise SystemExit("pick series with -s ID or a project with -p NAME; series: "
                         + ", ".join(series_mod.available()))
    for sid in ids:
        write(series_mod.load(sid), args)
    series_mod.write_dashboard()


if __name__ == "__main__":
    main()
