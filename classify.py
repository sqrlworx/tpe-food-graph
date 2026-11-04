"""Heuristic classification of IG profiles into Taiwan food bloggers / food makers."""

import re

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

MAKER_WORDS = re.compile(
    r"bakery|bakehouse|boulangerie|bread|baker\b|baking|sourdough|levain|patisserie|"
    r"p[aâ]tisserie|pastry|pastries|viennoiserie|croissant|cro\b|canel[eé]|dessert|"
    r"cake|cookie|biscuit|bagel|donut|doughnut|scone|tart|gelato|ice ?cream|chocolat|"
    r"confection|brioche|focaccia|cinnamon roll|"
    r"麵包|面包|烘焙|烘培|酸種|天然酵母|甜點|甜品|蛋糕|可頌|可麗露|塔專賣|餅乾|吐司|貝果|"
    r"甜甜圈|司康|冰淇淋|義式冰|巧克力|糕|菓子|肉桂捲|布丁|生乳|千層|馬卡龍|鹼水|乳酪|"
    r"餅|酥|月餅|鳳梨酥|蛋黃酥|牛軋糖|果醬|醬料|辣油|jam\b|sauce|granola|chili oil",
    re.I,
)
BAKERY_WORDS = re.compile(
    r"bakery|bakehouse|boulangerie|bread|baker\b|sourdough|levain|viennoiserie|croissant|"
    r"bagel|brioche|focaccia|麵包|面包|烘焙|烘培|酸種|天然酵母|可頌|吐司|貝果",
    re.I,
)
VENUE_WORDS = re.compile(
    r"caf[eé]|coffee|roaster|espresso|咖啡|restaurant|bistro|kitchen|bar\b|wine|"
    r"餐廳|餐酒|小館|食堂|料理|居酒屋|拉麵|ramen|burger|pizza|taco|brunch|早午餐|"
    r"bbq|燒肉|火鍋|omakase|sushi|鮨|tea\b|茶",
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
    maker = bool(MAKER_WORDS.search(t))
    blogger = bool(BLOGGER_WORDS.search(bio + " " + (p.get("full_name") or "")))
    blogger_name = re.search(r"foodie|eat|hungry|美食|吃", p["username"] + (p.get("full_name") or ""), re.I)
    if blogger_name and not p.get("address") and n_out >= 3:
        return "blogger", None
    if maker and not (blogger and not p.get("address") and n_out >= 8):
        return "maker", "bakery" if BAKERY_WORDS.search(t) else "dessert"
    if blogger and n_out >= 5:
        return "blogger", None
    if VENUE_WORDS.search(t):
        return "venue", None
    return "other", None
