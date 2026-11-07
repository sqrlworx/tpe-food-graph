"""Heuristic classification of IG profiles into Taiwan food bloggers / food makers.

What counts as a maker (the kind of shop being ranked) and a venue comes from the
project config (project.py).
"""

import re

import project

CFG = project.current()

CJK = re.compile(r"[一-鿿]")
JP_KANA = re.compile(r"[぀-ヿ]")
KR = re.compile(r"[가-힯]")
# Characters whose form differs between Traditional and Simplified Chinese.
TRAD = re.compile(r"[們這個會來說對時麵點餐廳灣臺過還沒讓開關買賣鬆蘋與為經頭樂動體愛氣發現種裡間門題見長馬車東國學實寫聽寶貝]")
SIMP = re.compile(r"[们这个会来说对时面点餐厅湾台过还没让开关买卖松苹与为经头乐动体爱气发现种里间门题见长马车东国学实写听宝贝]")
HK = re.compile(r"香港|hong ?kong|\bhk\b|嘅|係|咗|唔|冇|啲|旺角|銅鑼灣|尖沙咀|中環|澳門|macau", re.I)

TW_WORDS = re.compile(
    r"taipei|taiwan|台北|臺北|新北|台中|臺中|台南|臺南|高雄|新竹|桃園|宜蘭|花蓮|台東|嘉義|彰化|"
    r"基隆|屏東|苗栗|南投|雲林|大安|信義|中山|松山|士林|內湖|板橋|永和|中和|三重|新店|天母|"
    r"捷運|\btw\b|\btpe\b|\.tw\b|_tw\b|tw$|tpe$|taichung|tainan|kaohsiung|hsinchu",
    re.I,
)

BLOGGER_WORDS = re.compile(
    r"foodie|food ?blog|blogger|food ?lover|eats?\b|eating|eater|hungry|吃貨|吃吃|愛吃|"
    r"美食|部落客|食記|探店|吃什麼|吃喝|合作|邀約|collab|📩|✉|email|mail|podcast|"
    r"youtube|vlog|creator|kol|網紅|food ?guide|food ?diary|日記",
    re.I,
)
# Accounts that are clearly not small food businesses.
NOT_FOOD = re.compile(
    r"hotel|飯店|酒店|resort|magazine|雜誌|media|news|新聞|agency|travel agency|"
    r"official account of|basketball|nba|football|athlete|actor|actress|singer|演員|歌手|"
    r"model\b|模特|photographer|攝影師|fashion|boutique|eyewear|jewel|clothing|服飾|"
    r"department store|百貨|mall|airline|bank|銀行",
    re.I,
)


def text_of(p):
    return " ".join(
        filter(None, [p["username"], p.get("full_name"), p.get("biography"), p.get("category")])
    )


def taiwan_score(p):
    s = 0
    addr = p.get("address") or {}
    city = (addr.get("city_name") or "") + " " + (addr.get("street_address") or "")
    if TW_WORDS.search(city):
        s += 3
    t = text_of(p)
    if TW_WORDS.search(t):
        s += 2
    locs = [post.get("location") or "" for post in p["posts"]]
    s += min(2, sum(1 for l in locs if TW_WORDS.search(l)))
    # Written in Traditional (not Simplified) Chinese, and not Cantonese / HK.
    allt = t + " " + " ".join(post["caption"] for post in p["posts"])
    trad, simp = len(TRAD.findall(allt)), len(SIMP.findall(allt))
    if trad >= 3 and trad > 2 * simp and len(JP_KANA.findall(allt)) < 20:
        s += 2 if trad >= 15 else 1
    if HK.search(allt) and not TW_WORDS.search(allt):
        s -= 3
    # Japanese styling is common for Taiwanese brands; only penalise kana when
    # the account shows no Traditional Chinese at all.
    if KR.search(t) or (JP_KANA.search(t) and trad < 3 and s < 3):
        s -= 2
    return s


def classify(p):
    """Return (kind, subtype) where kind in {maker, blogger, venue, other}."""
    t = text_of(p)
    bio = p.get("biography") or ""
    n_out = len({h for post in p["posts"] for h in post["tagged"] + post["mentions"]})
    if NOT_FOOD.search(t):
        return "other", None
    maker = bool(CFG.MAKER_WORDS.search(t))
    blogger = bool(BLOGGER_WORDS.search(bio + " " + (p.get("full_name") or "")))
    blogger_name = re.search(r"foodie|eat|hungry|美食|吃", p["username"] + (p.get("full_name") or ""), re.I)
    if blogger_name and not p.get("address") and n_out >= 3:
        return "blogger", None
    if maker and not (blogger and not p.get("address") and n_out >= 8):
        return "maker", next((k for k, rx in CFG.SUBTYPES if rx.search(t)), CFG.DEFAULT_SUBTYPE)
    if blogger and n_out >= 5:
        return "blogger", None
    if CFG.VENUE_WORDS.search(t):
        return "venue", None
    return "other", None


def _brand_stem(h):
    """The handle's letters without generic words or branch numbers: rufous_coffee_2 -> rufous,
    oasis_coffee_roasting_lab -> oasis, celebread.acs_tm -> celeacstm (bakeries: "bread" is generic)."""
    s = CFG.GOOGLE_GENERIC.sub("", re.sub(r"[^a-z0-9]", "", h.lower()))
    return re.sub(r"\d+(st|nd|rd|th)?$", "", s)


def affiliated(a, bio_a, b, bio_b):
    """Sister accounts / same brand: one names the other in its bio, or the handles are the
    same brand name apart from generic words and branch numbers (rufous_coffee_1 /
    rufous_coffee_2, aufglet / aufglet_taipei). Brands this misses go in the config's BRANDS."""
    a, b = a.lower(), b.lower()
    if "@" + b in (bio_a or "").lower() or "@" + a in (bio_b or "").lower():
        return True
    sa = _brand_stem(a)
    return len(re.sub(r"[^a-z]", "", sa)) >= 4 and sa == _brand_stem(b)


def same_brand(a, bio_a, b, bio_b):
    """affiliated(), corrected by the project's BRANDS (groups to join) and NOT_BRANDS (pairs to keep apart)."""
    pair = {a.lower(), b.lower()}
    if any(pair == set(p) for p in CFG.NOT_BRANDS):
        return False
    return any(pair <= set(g) for g in CFG.BRANDS) or affiliated(a, bio_a, b, bio_b)


def brands(shops):
    """{handle: brand lead handle} for shops ({handle: bio}) grouped by same_brand(). The lead is
    the first handle of the group in the order given."""
    order = list(shops)
    parent = {h: h for h in order}

    def find(h):
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h

    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:] if same_brand(a, shops[a], b, shops[b])]
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            # keep the earlier handle as the root, so the lead is the first in order
            if order.index(ra) < order.index(rb):
                parent[rb] = ra
            else:
                parent[ra] = rb
    return {h: find(h) for h in order}

