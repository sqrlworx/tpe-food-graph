# Greater Taipei shop rankings from the Instagram food graph

A pipeline that ranks one kind of shop in Greater Taipei and turns the ranking into an
Instagram countdown series. It crawls public Instagram profiles to see which shops food
bloggers and fellow shops tag, matches the shops to Google Maps, collects press and food-blog
coverage, scores everything, and renders the top N as carousel posts.

Each kind of shop is a **project** in `projects/<name>/`:

| Project | Ranks | Series |
|---|---|---|
| `bakeries` | bakeries & sweets shops | top 100 in 11 posts |
| `coffee` | coffee shops & roasteries | top 50 in 6 posts |

All fetching (Instagram, Google Maps, search, blogs, articles) goes through `fwdproxy:8080`.

## Layout

```
pipeline.py            runs the steps in order; shows a project's status
project.py             picks the project (-p NAME) and its paths
crawl.py ... posts.py  the steps (each takes -p NAME)
*_template.html        dashboard / graph / slide / preview templates, labelled from the project config
projects/<name>/
  config.py            everything category-specific (see below)
  seeds.json           crawl seeds and handles to skip
  overrides.json       hand-reviewed account labels
  data/                inputs: Google places, press, review notes, photo picks, trusted blogs
  output/              graph (index.html), ranking (ranking.html), posts/ (gitignored)
data/                  caches shared by all projects (gitignored): profiles/, google_raw/,
                       blogs/, search_raw/; related_snapshot.json (saved related-account lists)
```

## Steps

`python3 -I pipeline.py coffee` lists the steps with their commands and status;
`python3 -I pipeline.py coffee STEP ...` runs them, and `... coffee all` runs every scripted step
from `build` on, stopping at a manual step that isn't done.

| Step | Script | What it does | Writes |
|---|---|---|---|
| seeds | *manual*, `search.py`, `harvest.py` | Find articles listing the shops (`search.py "台北 咖啡廳 推薦"`), list them in `data/article_urls.txt`, harvest their Instagram handles (`harvest.py data/article_urls.txt > data/harvest.json`) and pick seed shops and bloggers. Profiles found directly by search (`search.py "instagram 大安區 咖啡廳"`) can be listed in a file and fetched with `fetch_list.py FILE` | `seeds.json` |
| crawl | `crawl.py N` | Fetch the seeds, then the N accounts the graph points at most (tags, mentions, Instagram's related accounts). About 6 profiles a minute | `data/profiles/` |
| review | *manual*, `review_queue.py` | Label accounts from name and bio in `overrides.json`: `maker:<subtype>`, `maker:<subtype>:<role>` (a person, not a shop), `blogger:`, `venue`, `other`. `output/review_queue.csv` lists what's left. Crawl and review again until the shops stop changing | `overrides.json` |
| build | `build.py` | Endorsement graph (A → B: A tagged B in a recent post), creator and blogger tables | `output/graph.json`, `index.html`, `food_creators.csv` |
| report | `report.py` | Markdown summary of the graph | `output/REPORT.md` |
| google | `google_maps.py` | Match shops to Google Maps places (by the place's linked Instagram, else an exact name): rating, review count, stars, topics, review sample. `data/google_overrides.json` fixes bad matches | `data/google_places.json` |
| prerank | `rank.py` | A first ranking, to choose whose coverage to search | `output/ranking.json` |
| search | `press_search.py` | One web search per top candidate; keeps articles whose title names the shop | `data/press_search.json` |
| press | `press.py` | Merges search results, harvested articles, curated line-ups and every post title on the trusted food blogs (`data/trusted_blogs.json`) | `data/press.json` |
| notes | *manual*, `review_notes.py` | `review_notes.py export` writes each top shop's Google material to `output/review_input.json`; a person or an LLM writes the summary, must-try items, highlights and lowlights into `data/review_notes.json`; `review_notes.py check` validates them | `data/review_notes.json` |
| rank | `rank.py` | Scores and dashboard: network endorsement 35%, review-adjusted Google rating 30%, press 15%, review volume 10%, followers 10% | `output/ranking.*` |
| posts | `posts.py` | Picks a photo from each shop's own Instagram, renders 1080×1350 slides with headless Chromium and writes captions | `output/posts/` |
| photos | *manual* | Look through `output/posts/index.html`; pin better photos in `data/post_overrides.json` (`posts.py --candidates HANDLE` downloads options), then rerun `posts` | `data/post_overrides.json` |

How a tag counts in the graph (`build.py`, scored in `rank.py`):

- Sister accounts don't endorse each other: same brand (`classify.same_brand`), a bio naming the
  other account, or a person whose bio names the shop (staff, founders) tagging that shop or any
  of its branches.
- A post tagging more than 3 accounts (an event line-up, a roundup) gives each tag 3 / n.
- A tag between two businesses that shows a business tie counts once, at weight 0.4
  (`rank.BUSINESS_WEIGHT`), however often it repeats. A tie is business wording on the
  mention's line or the lines around it (合作, 聯名, 快閃, 客座, 市集, 供應, pop-up, collab, ...,
  plus the project's `SUPPLY_WORDS`, e.g. 咖啡豆 / 用豆 for coffee, 麵粉 / 用料 for bakeries), a
  standing tag in 3+ of the 12 visible posts, or the reverse of such a tie. Only tags between
  shops, the people behind them and venues can be business ties; a blogger's tag is always an
  endorsement.
- In both PageRanks (endorser authority in `build.py`, centrality in `rank.py`) an account whose
  links add up to less than one full tag passes on only that share, so two shops tagging only
  each other don't keep their rank in a closed loop.

Run every script with `python3 -I` from the repo root, and pass `-p PROJECT`
(`$PROJECT` works too, but `-I` ignores environment variables).

## Starting a new project

```
python3 -I pipeline.py new brunch --like coffee
```

copies a config to `projects/brunch/` with empty seeds and overrides. Then go through
`config.py` section by section:

- **Classification**: `MAKER_WORDS` (what the ranked shops say in their bios), `SUBTYPES`,
  `VENUE_WORDS` (other food businesses whose tags count as endorsements)
- **Graph**: title and legend labels
- **Google Maps**: `GOOGLE_CATEGORY` (place categories a match may have), `GOOGLE_GENERIC`
  (name words to ignore when comparing names)
- **Press**: generic and product words that don't identify a shop, ambiguous names, curated
  line-ups, the search suffix
- **Ranking**: weights, `TOP_N`, which subtypes are ranked, `REQUIRE_GOOGLE`, `EXCLUDE`
  (shops left out by hand, with the reason), dashboard wording and chart items
- **Instagram series**: title, headline, colours, caption wording, hashtags, what a good photo shows

and follow `python3 -I pipeline.py brunch`.

## Project notes

**coffee** (top 50, 6 posts): 142 Greater Taipei coffee shops ranked out of 178 in a
262-account graph. Seeds came from 49 articles (`data/article_urls.txt`) and per-district
searches for café profiles (`data/extra_handles.txt`); three crawl rounds were reviewed by
hand. Differences from bakeries, all in `projects/coffee/config.py`:

- Network endorsement weighs 25% and press 25% (bakeries 35% / 15%): logged-out Instagram
  now shows only caption @mentions, so the coffee graph has 186 tags to the bakery graph's
  840 and a couple of tags would otherwise swing a shop's score.
- `REQUIRE_GOOGLE`: only shops with a Google Maps listing are ranked (no bean-only brands).
- Press search is scripted (`press_search.py`, top 100); the trusted blogs add six café-heavy
  blogs to the bakery list.
- One entry per brand: branches (Rufous, Oasis, Now Chance, Yokoso) are represented by their
  best-scoring branch and listed on its slide and in its caption. `classify.same_brand` finds
  them (a bio naming the other account, or the same handle apart from generic words and branch
  numbers); `BRANDS` / `NOT_BRANDS` in the config add or split groups. Press coverage of one
  branch goes to that branch when the title names it ("Rufous Coffee Roasters 2").
- Google matches fixed by hand, including flagships listed under Chinese names, are in
  `data/google_overrides.json`; 24 photos and a few slide names are pinned in
  `data/post_overrides.json`.

**bakeries** (top 100, 11 posts): moved into `projects/bakeries/` unchanged. With the
refactored scripts, `google_maps.py`, `press.py`, `rank.py` and `posts.py` reproduce the
committed outputs exactly. `build.py` needs the profile cache (`data/profiles/`, not committed). One entry per brand
leaves the top 100 unchanged; Celebread-TM (No. 178) is now listed under Celebread. The graph
rules above (staff, line-ups, business ties) came after the bakery graph was built; they apply
once `build.py -p bakeries` is rerun with a profile cache. The committed bakery ranking also
predates the PageRank change (links adding up to less than one tag pass on only that share):
rerunning `rank.py -p bakeries` moves scores by under 0.5 and swaps No. 100 (come_up_patisserie.tw
in, ponpie out).
