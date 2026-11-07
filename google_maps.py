"""Look up graph makers on Google Maps (via fwdproxy) and write the project's data/google_places.json.

Uses the same search request the Maps web app makes (tbm=map), biased to a
Taipei viewport. One search returns the place card: rating, review count, star
distribution, the review topics Google extracts (with mention counts), review
snippets and a handful of full reviews. Raw replies are cached in
data/google_raw/ (gitignored).

A Google place is matched to an Instagram account when its website links to
that account ("ig"), or when the names agree ("name").

usage: python3 -I google_maps.py -p PROJECT [handle ...]
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import project  # noqa: E402

CFG = project.current()
RAW = os.path.join(project.SHARED, "google_raw")
OUT_PATH = os.path.join(CFG.DATA, "google_places.json")
os.makedirs(RAW, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
MIN_INTERVAL = float(os.environ.get("GMAPS_INTERVAL", "2.5"))
_last = [0.0]
ELSEWHERE = re.compile(
    r"新竹|竹北|台中|臺中|台南|臺南|高雄|桃園|中壢|宜蘭|羅東|花蓮|台東|臺東|嘉義|彰化|基隆|屏東|苗栗|南投|"
    r"雲林|澎湖|金門|taichung|tainan|kaohsiung|hsinchu|taoyuan|香港|hong ?kong",
    re.I,
)


def _curl(url):
    wait = MIN_INTERVAL - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    r = subprocess.run(
        ["curl", "-s", "--http2", "-x", "fwdproxy:8080", "--max-time", "30", "-A", UA,
         "-H", "Accept-Language: zh-TW,zh;q=0.9,en;q=0.8", "-w", "\n%{http_code}", url],
        capture_output=True, text=True, errors="replace",
    )
    body, _, code = r.stdout.rpartition("\n")
    if code != "200":
        raise RuntimeError(f"HTTP {code} for {url[:100]}")
    return body


def _template():
    """The Maps app's own search request for a Taipei viewport, with the query as a placeholder."""
    path = os.path.join(RAW, "_template.txt")
    if os.path.exists(path):
        return open(path).read()
    html = _curl("https://www.google.com/maps/search/bakery/@25.04,121.53,12z?hl=zh-TW")
    m = re.search(r'href="(/search\?tbm=map[^"]*)"', html)
    if not m:
        raise RuntimeError("no tbm=map preload link on the Maps page")
    url = m.group(1).replace("&amp;", "&").replace("gl=us", "gl=tw")
    url = url.replace("q=bakery", "q={Q}").replace("%211sbakery", "%211s{PBQ}")
    if "{PBQ}" not in url:
        raise RuntimeError("search template has no query slot")
    open(path, "w").write(url)
    return url


# Google categories of places that can be the kind of shop being ranked.
FOOD_CATEGORY = CFG.GOOGLE_CATEGORY


def _pb_escape(s):
    return s.replace("*", "*2A").replace("!", "*21")


def search(query):
    key = hashlib.sha1(query.encode()).hexdigest()
    path = os.path.join(RAW, key + ".json")
    if os.path.exists(path):
        raw = open(path).read()
    else:
        url = "https://www.google.com" + _template().replace(
            "{Q}", urllib.parse.quote_plus(query)
        ).replace("{PBQ}", urllib.parse.quote(_pb_escape(query), safe=""))
        raw = _curl(url)
        with open(path, "w") as f:
            f.write(raw)
    data = json.loads(raw[raw.index("\n") + 1:])
    # A query that resolves to one place comes back as data[0][1][0][14]; a list of
    # results comes back as data[64] = [[None, info], ...].
    infos = [r[14] for r in _get(data, 0, 1) or [] if isinstance(r, list) and len(r) > 14 and isinstance(r[14], list)]
    infos += [r[1] for r in _get(data, 64) or [] if isinstance(r, list) and len(r) > 1 and isinstance(r[1], list)]
    return [parse_place(i) for i in infos[:10]]


def _get(o, *path):
    for p in path:
        if not isinstance(o, list) or p >= len(o) or o[p] is None:
            return None
        o = o[p]
    return o


def parse_place(info):
    blob = json.dumps(info, ensure_ascii=False)
    address = _get(info, 39) or ""
    district = re.search(r"[台臺新]北市(\S{1,3}?區)", address)
    reviews = []
    for rv in _get(info, 175, 9, 0, 0) or []:
        text = _get(rv, 0, 2, 15, 0, 0)
        if text:
            reviews.append({"stars": _get(rv, 0, 2, 0, 0), "when": _get(rv, 0, 1, 6), "text": text})
    snippets = [s[1].strip('"') for s in (_get(info, 31, 1) or []) if isinstance(s, list) and isinstance(_get(s, 1), str)]
    topics = []
    for t in _get(info, 153, 0) or []:
        if isinstance(_get(t, 1), str):
            topics.append([t[1], _get(t, 3, 4) or 0])
    fid = _get(info, 10) or ""
    return {
        "name": _get(info, 11) or "",
        "address": address,
        "district": district.group(1) if district else "",
        "lat": _get(info, 9, 2),
        "lng": _get(info, 9, 3),
        "rating": _get(info, 4, 7),
        "reviews": _get(info, 4, 8) or 0,
        "stars": _get(info, 175, 3),
        "website": _get(info, 7, 0) or "",
        "categories": _get(info, 13) or [],
        "fid": fid,
        "place_id": _get(info, 78) or "",
        "maps_url": f"https://www.google.com/maps/place/?q=place_id:{_get(info, 78)}" if _get(info, 78) else "",
        "closed": "永久停業" in blob or "permanently closed" in blob.lower(),
        "topics": topics,
        "snippets": snippets,
        "review_texts": reviews,
    }


# Words every shop name of the kind shares; they say nothing about which shop it is.
GENERIC = CFG.GOOGLE_GENERIC


def _norm(s):
    s = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))  # crèm -> crem
    return re.sub(r"[\W_]+", "", GENERIC.sub(" ", s))


def _segments(name):
    """The whole name plus its first segment before a tagline separator."""
    first = re.split(r"[|｜/／(（\[【\-–]", name or "")[0]
    return [name, first] if first.strip() and first != name else [name]


def _cjk(s):
    return set(re.findall(r"[一-鿿]", GENERIC.sub(" ", s or "")))


def name_sim(place, shop):
    """0..1 agreement between a Google place name and the IG account's name / handle,
    ignoring generic words like "bakery" or "甜點"."""
    cands = [_norm(n) for n in _segments(shop["name"])] + [_norm(shop["username"].replace("_", "").replace(".", ""))]
    best = 0.0
    for c, pn in ((c, pn) for c in cands for pn in map(_norm, _segments(place["name"]))):
        if not c or not pn:
            continue
        latin_p, latin_c = re.sub(r"[^a-z0-9]", "", pn), re.sub(r"[^a-z0-9]", "", c)
        # Containment only counts when the shorter name is most of the longer one's
        # latin part, so "ching" doesn't match "Ching Chun Jee".
        short, long_ = sorted((c, pn), key=len)
        letters = lambda x: re.sub(r"[^a-z]", "", x)
        if short in long_ and (
            (len(short) >= 2 and not re.search(r"[a-z0-9]", short))  # Chinese / Japanese name
            or (len(short) >= 4 and len(letters(short)) >= 0.8 * len(letters(long_)))
        ):
            best = max(best, 1.0)
        if len(latin_p) >= 4 and len(latin_c) >= 4:
            # longest common substring relative to the longer latin name
            m = max((k for i in range(len(latin_p)) for k in range(4, len(latin_p) - i + 1)
                     if latin_p[i:i + k] in latin_c), default=0)
            best = max(best, m / max(len(latin_p), len(latin_c)))
    a, b = _cjk(place["name"]), _cjk(shop["name"])
    if len(a) >= 2 and len(b) >= 2:
        best = max(best, len(a & b) / max(4, min(len(a), len(b))))
    return best


def queries(shop):
    name = unicodedata.normalize("NFKC", shop["name"] or "")
    name = re.sub(r"[|｜/\\·•,，、()（）\[\]【】「」~～!！?？#@:：]+", " ", name)
    name = re.sub(r"[^\w\s&'.-]", " ", name)  # emoji and symbols
    name = re.sub(r"\s+", " ", name).strip()
    spaced = re.sub(r"(?<=\w) (?=\w)", "", name) if re.fullmatch(r"(\w ){3,}\w.*", name) else name  # "K I T O Y A"
    qs = []
    if spaced:
        qs.append(spaced[:60])
    handle = re.sub(r"[._]+", " ", shop["username"]).strip()
    qs.append(handle)
    return list(dict.fromkeys(qs))


# Hand-checked fixes: {handle: null} = no Google listing, {handle: "query"} = search this instead,
# {handle: {"query": "...", "place": "<exact Google place name>"}} = that place, for a listing whose
# name and website don't identify the account (a Chinese-only name, a flagship among pop-ups).
OVERRIDES = project.data(CFG, "google_overrides.json", {})


def match(shop):
    h = shop["username"]
    if h in OVERRIDES and OVERRIDES[h] is None:
        return {"match": "", "query": "(override: no listing)"}
    # Every place that links to the account or shares its name; brands with several
    # branches are represented by the branch with the most reviews (the flagship).
    found = {}
    ov = OVERRIDES.get(h)
    pinned = ov.get("place") if isinstance(ov, dict) else None
    for q in ([ov["query"] if isinstance(ov, dict) else ov] if ov else queries(shop)):
        for p in search(q):
            web = p["website"].lower()
            if pinned:
                if p["name"] != pinned:
                    continue
                how, sim = "override", 1.0
            elif re.search(r"instagram\.com/" + re.escape(h) + r"(?:[/?]|$)", web):
                how, sim = "ig", 1.0
            elif (re.search(r"台灣|臺灣|[台臺新]北市|縣|市", p["address"]) and FOOD_CATEGORY.search(" ".join(p["categories"]))
                  and name_sim(p, shop) >= 0.99):
                how, sim = "name", name_sim(p, shop)
            else:
                continue
            key = p["fid"] or p["name"] + p["address"]
            if key not in found or (how == "ig" and found[key]["match"] != "ig"):
                found[key] = {**p, "match": how, "query": q, "sim": round(sim, 2)}
        if any(f["match"] in ("ig", "override") or f["sim"] >= 0.99 for f in found.values()):
            break
    if not found:
        return {"match": "", "query": " | ".join(queries(shop))}
    best = max(found.values(), key=lambda f: (f["match"] in ("ig", "override") or f["sim"] >= 0.99, f["reviews"]))
    best["branches"] = len(found)
    if best["stars"] is None and best["reviews"]:
        # List results are slim; searching the exact place returns its full card.
        street = re.sub(r"^\d+|[台臺新]北市|\S{1,3}?區|\S{1,3}?里", "", best["address"])
        for q in (f"{best['name']} {best['address']}", best["name"], f"{best['address']} {best['name']}",
                  f"{best['name']} {street}"):
            full = [p for p in search(q) if p["fid"] == best["fid"] and p["stars"] is not None]
            if full:
                best.update({k: full[0][k] for k in ("stars", "topics", "snippets", "review_texts", "closed")})
                break
    return best


def main(only):
    shops = list(csv.DictReader(open(os.path.join(CFG.OUT, "food_creators.csv"))))
    shops = [s for s in shops if s["role"] == "shop" and s["subtype"] in CFG.RANKED_SUBTYPES]
    if only:
        shops = [s for s in shops if s["username"] in only]
    else:
        # Bios that clearly place the shop outside Greater Taipei aren't worth a lookup.
        shops = [s for s in shops if not ELSEWHERE.search(s["bio"] + " " + s["name"])
                 or re.search(r"台北|臺北|新北|taipei", s["bio"], re.I)]
    out = json.load(open(OUT_PATH)) if os.path.exists(OUT_PATH) else {}
    for i, s in enumerate(shops, 1):
        h = s["username"]
        if h in out and not only:
            continue
        try:
            out[h] = match(s)
        except RuntimeError as e:
            print(f"stopping: {e}")
            break
        r = out[h]
        print(f"{i}/{len(shops)} {h:<28} {r['match'] or '-':<4} {r.get('name', '')[:24]:<24} "
              f"{r.get('rating') or ''} ({r.get('reviews') or 0}) {r.get('district', '')}", flush=True)
        if i % 10 == 0:
            json.dump(out, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
