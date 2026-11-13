"""Greater Taipei coffee shops: the top 50, counted down in 6 Instagram posts."""

import re

# --- Classification (classify.py: unreviewed accounts, crawl priorities) ---------------

# The kind of business being ranked ("maker" in the graph): coffee shops and roasters.
MAKER_WORDS = re.compile(
    r"coffee|caf[eé]|caff[eèé]|kaff[ea]|koffie|kopi|espresso|roast(?:er|ery|ing)|barista|pour ?over|"
    r"hand ?drip|specialty|latte|咖啡|珈琲|珈啡|烘豆|咖啡烘焙|自家烘焙|手沖|拿鐵|コーヒー|カフェ|喫茶|焙煎",
    re.I,
)
SUBTYPES = [
    ("roaster", re.compile(r"roast(?:er|ery|ers|ing)|烘豆|烘焙所|烘焙廠|自家烘焙|焙煎|coffee beans?|咖啡豆", re.I)),
]
DEFAULT_SUBTYPE = "cafe"
# Other food businesses: in the graph as a hidden layer, and their tags count as endorsements
# (a bakery or restaurant naming the roaster whose beans it serves).
VENUE_WORDS = re.compile(
    r"bakery|boulangerie|bread|patisserie|pâtisserie|pastry|dessert|cake|gelato|ice ?cream|chocolat|"
    r"restaurant|bistro|kitchen|bar\b|wine|cocktail|brunch|tea\b|"
    r"麵包|烘焙坊|甜點|甜品|蛋糕|冰淇淋|餐廳|餐酒|小館|食堂|料理|居酒屋|拉麵|早午餐|酒吧|茶",
    re.I,
)

# --- Graph (build.py, template.html, report.py) ----------------------------------------

GRAPH_TITLE = "Taipei coffee shops × food bloggers"
GROUPS = {"cafe": "Café", "roaster": "Roastery"}
VENUE_LABEL = "Bakery / restaurant"
MAKERS_LABEL = "Coffee shops"

# Words next to a tag between two businesses that show a supply tie (build.py marks such tags
# "business"; collaboration and event words are shared, in build.BUSINESS_WORDS).
SUPPLY_WORDS = r"咖啡豆|豆子|用豆|豆單|供豆|烘豆|選豆|roasted by|beans"

# --- Google Maps (google_maps.py) ------------------------------------------------------

# Google categories of places that can be a coffee shop (zh-HK / ja labels included).
GOOGLE_CATEGORY = re.compile(r"咖啡|珈琲|コーヒー|カフェ|喫茶|cafe|coffee|烘焙|餐廳|早午餐|甜|麵包|茶|酒吧|食品")
# Words every coffee shop name shares; they say nothing about which shop it is.
GOOGLE_GENERIC = re.compile(
    r"coffee|cafe|café|caffe|caffè|kaffe|koffie|roasters?|roastery|roasting|espresso|brew|bar|"
    r"studio|kitchen|taipei|taiwan|official|shop|store|lab|house|the|and|co|"
    r"咖啡館|咖啡廳|咖啡店|咖啡|珈琲|自家烘焙|烘豆|烘焙|工作室|工坊|台北|臺北|新北|門市|總店|本店|店",
    re.I,
)

# --- Press (press.py, press_search.py) -------------------------------------------------

PRESS_GENERIC = re.compile(
    r"咖啡館|咖啡廳|咖啡店|咖啡|珈琲|自家烘焙|烘豆|工作室|坊|專賣店?|分店|門市|[一-鿿]{1,3}店|"
    r"coffee|cafe|caffe|kaffe|roasters?|roastery|espresso|bar|studio|official|taipei|tw$"
)
PRESS_PRODUCT = re.compile(
    r"手沖|義式|拿鐵|濃縮|單品|精品|咖啡豆|甜點|早午餐|自家|烘焙|手作|不限時|老宅|"
    r"latte|espresso|pourover|specialty|brunch|dessert|beans?"
)
PRESS_AMBIGUOUS = {
    "specialty", "specialtycoffee", "coffee", "daily", "simple", "normal", "local", "common", "corner",
    "moment", "light", "slow", "white", "black", "single", "origin", "morning", "sunday", "weekend",
    "together", "little", "petit", "maison", "house", "home", "happy", "sunny", "honest", "honestly",
    "picnic", "noon", "tomorrow", "folks", "thefolks", "photon", "after", "rebirth", "ferment", "oasis",
    # Taipei place names that branch accounts carry in their names ("Oasis Coffee Roasters - Nanjing")
    "nanjing", "dunhua", "zhongshan", "xinyi", "songshan", "tianmu", "dihua", "minsheng", "huashan",
    "taipei", "dadaocheng", "yongkang",
}
CURATED = []
SEARCH_SUFFIX = "台北 咖啡"
# press_search.py searches the top PRESS_SEARCH_TOP shops of a ranking.
PRESS_SEARCH_TOP = 100

# --- What reviewers say about the coffee itself (product.py) ---------------------------

# A clause of a Google review or a blog post that names the drink ("terms": not the place, so
# 咖啡廳 / 咖啡店 don't count, and a tea latte isn't coffee) and says something good or bad
# about it. A praise word after a negation (不好喝, 不推薦) counts as a complaint.
PRODUCT = {
    "label": "Coffee",
    "terms": (
        r"咖啡(?!廳|店|館|屋|色|師|因)|珈琲|(?<!茶)(?<!可可)(?<!芋頭)(?<!玫瑰)拿鐵|手沖|濃縮|"
        r"冰美式|熱美式|卡布|虹吸|冰滴|冷萃|咖啡豆|烘焙度|淺焙|中焙|深焙|澳白|馥列白|摩卡|髒髒|"
        r"\b(?:espresso|coffee(?! ?shop)|cappuccino|flat ?white|americano|pour.?over|cold ?brew|mocha|"
        r"cortado|macchiato|dirty)\b|(?<!matcha )\blatte\b"
    ),
    "praise": (
        r"好好喝|超好喝|很好喝|好喝|不錯|不俗|推薦|大推|激推|強推|必點|必喝|香醇|香氣|很香|好香|濃郁|醇厚|回甘|"
        r"層次|驚艷|驚豔|喜歡|最愛|愛喝|讚|很棒|好棒|超棒|厲害|優秀|出色|有水準|順口|滑順|順滑|絲滑|平衡|"
        r"乾淨|果香|花香|甘甜|甜感|完美|一流|好咖啡|合我口味|合口味|"
        r"\b(?:delicious|great|excellent|amazing|recommend\w*|love\w*|best|perfect|smooth|tasty|good)\b"
    ),
    "complaint": (
        r"普通|普普|一般般|很一般|蠻一般|滿一般|有點一般|比較一般|偏酸|太酸|過酸|酸澀|澀|偏苦|太苦|過苦|苦澀|"
        r"焦味|燒焦|難喝|不好喝|沒特色|無特色|沒什麼特色|太淡|偏淡|淡而無味|水水|失望|不推|踩雷|很雷|"
        r"有點雷|不怎麼樣|稍弱|偏弱|不突出|沒味道|不習慣|"
        r"\b(?:bland|bitter|sour|watery|weak|disappoint\w*|mediocre|average|burnt)\b"
    ),
}

# --- Ranking (rank.py, ranking_template.html) ------------------------------------------

# The coffee graph has about a quarter of the bakery graph's tags (logged-out Instagram shows only
# caption @mentions, and coffee bloggers mention shops less), so a few tags would swing the
# network score: endorsements weigh 25% here (bakeries: 35%) and press 25% (bakeries: 15%).
WEIGHTS = {"network": 0.25, "quality": 0.30, "volume": 0.10, "press": 0.25, "reach": 0.10}
# Who is tagging: bloggers curate for an audience, coffee shops tagging peers is barista
# respect (or a roaster crediting a café that pours its beans), restaurants and bakeries
# tagging a roaster is mostly a supplier credit.
ENDORSER_WEIGHT = {"blogger": 1.0, "maker": 0.8, "venue": 0.4}
TOP_N = 50
RANKED_SUBTYPES = ("cafe", "roaster")
# A coffee shop you can't visit isn't one: bean brands with no Google listing are left out.
REQUIRE_GOOGLE = True
# Google lists a place's main category first. A shop Google files first as something else (a brunch
# restaurant, a dessert shop, a bar) is left out, whatever its other categories or its label here.
GOOGLE_PRIMARY = re.compile(r"咖啡|珈琲|コーヒー|カフェ|喫茶|cafe|coffee", re.I)
# Labelled coffee shops in the graph, but not what this ranking is about.
EXCLUDE = {
    "bean__u": "temporarily closed (bio: 暫停營業)",
}

# Branches of one brand the automatic check (classify.affiliated: a bio naming the other account,
# or the same handle apart from generic words and branch numbers) misses; and pairs it wrongly joins.
BRANDS = [
    ["oasis_coffee_roasting_lab", "oasis_coffee_roasters_anhe", "oasis_coffee_roasters_nanjing"],
]
NOT_BRANDS = []


def type_of(subtype):
    return "roaster" if subtype == "roaster" else "cafe"


TYPES = {"cafe": "Café", "roaster": "Roastery"}
TYPES_PLURAL = {"cafe": "Cafés", "roaster": "Roasteries"}

DASHBOARD = {
    "title": "Top 50 coffee shops in Greater Taipei",
    "subtitle": "Ranked by peer endorsement in the Instagram food graph, Google Maps ratings, press coverage "
                "and reach — not by followers alone.",
    "kinds": {"blogger": "blogger", "maker": "coffee shop", "venue": "bakery / restaurant"},
    "tagged_note": "endorsed by ≥1 blogger, coffee shop, bakery or restaurant",
    "bands": [[1, 10], [11, 20], [21, 30], [31, 40], [41, 50]],
    "pool": "every hand-reviewed coffee shop and roastery with a bar in our Instagram coffee graph ({n_nodes} accounts: "
            "bloggers, coffee shops, and the bakeries and restaurants around them; baristas' personal accounts, "
            "chains and bean-only brands excluded)",
    "excluded": "A few coffee shops are left out by hand (closed for now, or mainly something else)",
    "off_category": "Left out because Google lists them first as something other than a coffee shop",
    "endorser_note": "coffee shop {maker} (peer respect, or a roaster crediting a café), bakery / restaurant {venue} "
                     "(often crediting its bean supplier)",
    "press_sources": "food blogs and media found by a scripted web search (search.py) for every top-{press_top} "
                     "candidate, and articles harvested while building the graph",
    "press_caveat": "Press search covered the top {press_top} candidates with one search each; small shops may have "
                    "coverage we missed.",
    "unlisted": "Shops without a Google listing (bean brands, pop-ups) are left out: the ranking is of places you can visit.",
    "items": [
        ["Pour-over 手沖", "手沖|pour.?over|hand.?drip|filter", "i"],
        ["Espresso 濃縮", "濃縮|espresso", "i"],
        ["Latte / flat white 拿鐵", "拿鐵|latte|flat white|澳白|馥列白|cappuccino|卡布", "i"],
        ["Geisha 藝伎 / 瑰夏", "藝伎|藝妓|瑰夏|geisha|gesha", "i"],
        ["Single origin 單品", "單品|single.?origin", "i"],
        ["Signature drinks 特調", "特調|signature|創意", "i"],
        ["Cold brew 冷萃", "冷萃|冰滴|cold.?brew", "i"],
        ["Dirty 髒咖啡", "dirty|髒", "i"],
        ["Coffee beans 咖啡豆", "咖啡豆|beans", "i"],
        ["Cake 蛋糕", "蛋糕|cake|戚風|chiffon|巴斯克|乳酪", "i"],
        ["Pastry 甜點", "可頌|croissant|可麗露|canel|司康|scone|塔|tart|肉桂捲|cinnamon|布丁|pudding", "i"],
        ["Toast / sandwich 吐司", "吐司|toast|三明治|sandwich|鬆餅|pancake", "i"],
    ],
}

# --- Instagram series defaults (posts.py, slide_template.html, posts_template.html) ----
# Every series of this project (series/<id>/series.json) starts from this wording and can override
# any of it. {top} and {where} are filled from the series (its top N, and e.g. "Greater Taipei").

SERIES = {
    "short": "Taipei Top 50 Coffee",
    "title": "Taipei's Top 50 Coffee Shops",
    "zh": "大台北咖啡廳 TOP 50",
    "hashtag": "#台北咖啡top50",
    "location": "Taipei, Taiwan",
    "headline": ["The", "Top 50", "coffee shops in\nGreater Taipei"],
    "page_title": "Instagram series: Taipei Top 50 coffee shops",
    # Slide colours (slide_template.html): a roast-brown title card with crema accents.
    "theme": {"--espresso": "#24160f", "--crust": "#b4532a", "--butter": "#e8c48f", "--cream": "#f4ede4"},
}
CAPTION = {
    "emoji": "☕",
    "item_emoji": "☕",
    "intro": "We ranked {n} coffee shops and roasteries across {where} by how often local food creators "
             "and fellow baristas tag them, their Google reviews, and press coverage.",
    "outro_last": "That's the full top {top}! Catch the rest of the countdown on our grid. Who would you crown No. 1? 👇",
    "outro_next": "Next up: No. {hi} → {lo}. Which of these is your go-to? Tell us below 👇 and save this for your "
                  "next café crawl 🔖",
}
HASHTAGS = ["#台北咖啡廳", "#台北咖啡", "#taipeicoffee"]
DISTRICT_HASHTAG = "#{district}咖啡廳"
# What a good photo shows, in IG's alt text.
PHOTO_SUBJECT = re.compile(
    r"\b(coffee|latte|cappuccino|espresso|drink|beverage|cup|mug|coffee cup|coffee beans|coffee maker|"
    r"food|dessert|cake|pastry|pastries|bread|cookie|croissant|tart|toast|sandwich|pudding|cream|"
    r"tea|milk|ice|glass|tableware|indoor|table)s?\b",
    re.I,
)
