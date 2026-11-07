"""Greater Taipei bakeries & sweets shops: the top 100, counted down in 11 Instagram posts."""

import re

# --- Classification (classify.py: unreviewed accounts, crawl priorities) ---------------

# The kind of business being ranked ("maker" in the graph).
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
# Maker subtypes: the first pattern that matches, else DEFAULT_SUBTYPE.
SUBTYPES = [
    ("bakery", re.compile(
        r"bakery|bakehouse|boulangerie|bread|baker\b|sourdough|levain|viennoiserie|croissant|"
        r"bagel|brioche|focaccia|麵包|面包|烘焙|烘培|酸種|天然酵母|可頌|吐司|貝果",
        re.I,
    )),
]
DEFAULT_SUBTYPE = "dessert"
# Other food businesses: in the graph as a hidden layer, and their tags count as endorsements.
VENUE_WORDS = re.compile(
    r"caf[eé]|coffee|roaster|espresso|咖啡|restaurant|bistro|kitchen|bar\b|wine|"
    r"餐廳|餐酒|小館|食堂|料理|居酒屋|拉麵|ramen|burger|pizza|taco|brunch|早午餐|"
    r"bbq|燒肉|火鍋|omakase|sushi|鮨|tea\b|茶",
    re.I,
)

# --- Graph (build.py, template.html, report.py) ----------------------------------------

GRAPH_TITLE = "Taiwan food creators × food bloggers"
# Legend groups for makers: subtype -> label; other subtypes fall into the last group.
GROUPS = {"bakery": "Bakery", "dessert": "Sweets"}
VENUE_LABEL = "Café / restaurant"
MAKERS_LABEL = "Food creators"

# Words next to a tag between two businesses that show a supply tie (build.py marks such tags
# "business"; collaboration and event words are shared, in build.BUSINESS_WORDS).
SUPPLY_WORDS = r"麵粉|用料|進貨|指定用|食材供應"

# --- Google Maps (google_maps.py) ------------------------------------------------------

# Google categories of places that can be a bakery / dessert shop (zh-HK / ja labels included).
GOOGLE_CATEGORY = re.compile(r"餅|甜|糕|麵包|面包|包圈|雪糕|冰|朱古力|巧克力|咖啡|コーヒー|カフェ|ケーキ|喫茶|餐廳|禮盒|糖果|到會|食品|芝士")
# Words every bakery / dessert shop name shares; they say nothing about which shop it is.
GOOGLE_GENERIC = re.compile(
    r"bakery|bakehouse|boulangerie|patisserie|pâtisserie|pastry|dessert|desserts|sweets|cafe|café|coffee|"
    r"studio|bread|cake|kitchen|taipei|taiwan|official|shop|store|lab|the|and|"
    r"甜點|甜品|麵包|面包|烘焙|烘培|蛋糕|製菓|菓子|工作室|工坊|專賣店|專門店|專賣|咖啡|手作|台北|臺北|新北|門市|總店|本店|店",
    re.I,
)

# --- Press (press.py, press_search.py) -------------------------------------------------

# Words that describe what a shop sells rather than name it.
PRESS_GENERIC = re.compile(
    r"甜點|甜品|工作室|蛋糕|cake|麵包|烘焙|烘培|坊|專賣店?|咖啡|分店|門市|[一-鿿]{1,3}店|"
    r"bakery|bakehouse|boulangerie|patisseries?|dessert|cafe|coffee|studio|official|taipei|tw$"
)
# Product words: a name made mostly of them ("手作甜點") names no shop in particular.
PRESS_PRODUCT = re.compile(
    r"可麗露|生乳捲|泡芙|肉桂捲|可頌|貝果|吐司|馬卡龍|千層|布丁|戚風|巴斯克|乳酪|起司|塔|酸種|法式|"
    r"手工|手作|客製化?|喜餅|彌月|禮盒|冰淇淋|義式|巧克力|水果|季節|專門|專賣|生日|婚禮|韓式|錶花|"
    r"croissant|canele|bagel|gelato|chocolate|cake|pastry|bread|sweets?"
)
# Shop names that are also everyday English words, too ambiguous to match alone in a
# post title ("1881 Heritage"); those shops still match on their fuller names.
PRESS_AMBIGUOUS = {
    "heritage", "smile", "specialty", "specialtycoffee", "peckish", "comeup", "ontheroad",
    "rise", "season", "terra", "double", "butter", "bread",
    # common food words that a shop name can reduce to ("Cookie_Tea" -> "cookie")
    "cookie", "cookies", "scone", "scones", "brownie", "brownies", "cheesecake", "pudding",
    "waffle", "waffles", "donut", "donuts", "macaron", "macarons", "chiffon", "crepe", "crepes",
    "toast", "cream", "sugar", "honey", "cocoa", "matcha", "lemon", "berry", "happy", "sunny",
    "little", "petit", "maison",
}
# Curated line-ups: a hand-reviewed {vendor name: handle} file in data/; each listed shop
# gets the line-up as one press outlet.
CURATED = [
    {"file": "bonpain_2026_handles.json", "outlet": "Bon Pain 2026 line-up",
     "url": "https://www.herenow.city/taipei/style/2026_bon-pain/",
     "title": "Bon Pain 2026 bread fair curated vendor ({vendor})"},
]
# press_search.py: what to add to a shop's name when searching for coverage.
SEARCH_SUFFIX = "台北 甜點"
# press_search.py searches the top PRESS_SEARCH_TOP shops of a ranking.
PRESS_SEARCH_TOP = 150

# --- Ranking (rank.py, ranking_template.html) ------------------------------------------

WEIGHTS = {"network": 0.35, "quality": 0.30, "volume": 0.10, "press": 0.15, "reach": 0.10}
# Who is tagging: bloggers curate for an audience, makers tagging peers is chef
# respect, cafés tagging a supplier is mostly business.
ENDORSER_WEIGHT = {"blogger": 1.0, "maker": 0.8, "venue": 0.4}
TOP_N = 100
RANKED_SUBTYPES = ("bakery", "dessert", "pastry")
# Shops with no Google listing (studios, online-only) can still rank, at the average rating.
REQUIRE_GOOGLE = False
# Labelled bakery / dessert shops in the graph, but not what this ranking is about.
EXCLUDE = {
    "aufglet": "brunch café (Google: café); both accounts match one place",
    "aufglet_taipei": "brunch café (Google: café); both accounts match one place",
    "skiff.tw": "matcha drinks shop (Google: non-alcoholic drinks)",
    "heureuxvegan": "light-meal restaurant that also sells desserts",
    "icegyaru": "soft-serve shop",
}

# Branches of one brand the automatic check (classify.affiliated: a bio naming the other account,
# or the same handle apart from generic words and branch numbers) misses; and pairs it wrongly joins.
BRANDS = [
    ["celebread.acs", "celebread.acs_tm", "celebread.acs.hc"],
]
NOT_BRANDS = [
    ["somedaydessert", "someday_2023533"],  # 有一天 (Taichung) and 有添甜室: different shops
]


def type_of(subtype):
    """The shop type shown in the dashboard and on the slides (a key of TYPES)."""
    return "bakery" if subtype == "bakery" else "sweets"


TYPES = {"bakery": "Bakery", "sweets": "Sweets"}
TYPES_PLURAL = {"bakery": "Bakeries", "sweets": "Sweets"}

DASHBOARD = {
    "title": "Top 100 bakeries & sweets in Greater Taipei",
    "subtitle": "Ranked by peer endorsement in the Instagram food graph, Google Maps ratings, press coverage "
                "and reach — not by followers alone.",
    "kinds": {"blogger": "blogger", "maker": "maker", "venue": "café"},
    "tagged_note": "endorsed by ≥1 blogger, maker or café",
    # Rank bands in the "where the score comes from" chart.
    "bands": [[1, 10], [11, 25], [26, 50], [51, 75], [76, 100]],
    "pool": "every hand-reviewed bakery / sweets <em>shop</em> in our Instagram food graph ({n_nodes} accounts: "
            "bloggers, makers and cafés; chefs' personal accounts and non-dessert makers excluded)",
    "excluded": "A few accounts labelled bakery / dessert are left out by hand because they are mainly something else "
                "(a brunch café, a drinks shop, a light-meal restaurant, a soft-serve shop)",
    "endorser_note": "maker {maker} (peer respect), café {venue} (often a wholesale client)",
    "press_sources": "food blogs and media found by a web search for every top-150 candidate, articles harvested "
                     "while building the graph, and the curated <b>Bon Pain 2026</b> bread-fair line-up (counted as one outlet)",
    "press_caveat": "Press search covered the top 150 candidates by one or two searches each; small shops may have coverage we missed.",
    "unlisted": "Shops without a Google listing (online-only studios, pick-up-only kitchens) get the average rating but no "
                "review volume, so they rank below comparable walk-in shops.",
    # Must-try items to count across shops: label, regex source, flags (over the review notes' signature items).
    "items": [
        ["Croissant 可頌", "可頌|croissant", "i"],
        ["Cinnamon roll 肉桂捲", "肉桂捲|cinnamon", "i"],
        ["Sourdough 酸種", "酸種|sourdough", "i"],
        ["Canelé 可麗露", "可麗露|canel", "i"],
        ["Saint-Honoré 聖多諾黑", "聖多諾黑|honor", "i"],
        ["Mille-crêpe / feuille 千層", "千層|mille", "i"],
        ["Chiffon 戚風", "戚風|chiffon", "i"],
        ["Cheesecake / Basque 乳酪", "巴斯克|起司蛋糕|乳酪|cheesecake", "i"],
        ["Tart 塔", "塔|tart", "i"],
        ["Dacquoise 達克瓦茲", "達克瓦茲|dacquoise", "i"],
        ["Scone 司康", "司康|scone", "i"],
        ["Gelato / ice cream", "冰淇淋|霜淇淋|gelato|ice cream", "i"],
        ["Cookie 餅乾", "餅乾|cookie", "i"],
        ["Macaron 馬卡龍", "馬卡龍|卡龍|macaron", "i"],
        ["Pudding 布丁", "布丁|pudding", "i"],
        ["Toast / milk bread 吐司", "吐司|toast", "i"],
        ["Egg-yolk pastry 蛋黃酥", "蛋黃酥", ""],
        ["Brownie 布朗尼", "布朗尼|brownie", "i"],
    ],
}

# --- Instagram series (posts.py, slide_template.html, posts_template.html) -------------

SERIES = {
    "short": "Taipei Top 100",
    "title": "Taipei's Top 100 Bakeries & Sweets Shops",
    "zh": "大台北麵包甜點 TOP 100",
    "hashtag": "#台北甜點top100",
    "location": "Taipei, Taiwan",
    # Title card: "The <b>Top 100</b> bakeries &<br>sweets shops in Greater Taipei"
    "headline": ["The", "Top 100", "bakeries &\nsweets shops in Greater Taipei"],
    "page_title": "Instagram series: Taipei Top 100 bakeries & sweets",
}
CAPTION = {
    "emoji": "🥐",
    "item_emoji": "🍰",
    "intro": "We ranked {n} bakeries and dessert shops across Greater Taipei by how often local food creators "
             "and fellow bakers tag them, their Google reviews, and press coverage.",
    "outro_last": "That's the full top 100! Catch the rest of the countdown on our grid. Who would you crown No. 1? 👇",
    "outro_next": "Next up: No. {hi} → {lo}. Which of these is your go-to? Tell us below 👇 and save this for your "
                  "next bakery run 🔖",
}
HASHTAGS = ["#台北甜點", "#台北麵包", "#taipeifood"]
DISTRICT_HASHTAG = "#{district}美食"
# What a good photo shows, in IG's alt text.
PHOTO_SUBJECT = re.compile(
    r"\b(food|dessert|cake|cupcake|cheesecake|bread|baked goods|pastry|pastries|doughnut|donut|"
    r"cookie|biscuit|ice cream|gelato|chocolate|macaron|pie|tart|croissant|sandwich|waffle|"
    r"pancake|pudding|crêpe|crepe|fruit|strawberr\w*|bun|bagel|scone|muffin|brownie|candy|"
    r"sweets|cream|baguette|toast|shaved ice|eclair|mousse|chiffon|turnover|wafer|cracker|"
    r"breadstick|pretzel|roll|dumpling|mochi|jelly|parfait|meringue|petit four|madeleine|caramel)s?\b",
    re.I,
)
