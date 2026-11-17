# Greater Taipei shop rankings from the Instagram food graph

A pipeline that ranks one kind of shop in Greater Taipei and turns the rankings into
Instagram countdown series. It crawls public Instagram profiles to see which shops food
bloggers and fellow shops tag, matches the shops to Google Maps, collects press and food-blog
coverage, scores everything, and renders each series' top N as carousel posts.

Each kind of shop is a **project** in `projects/<name>/`: its candidates and their scores.
A **series** in `series/<id>/` draws from one project (all of it, or one district) and has
**entries** (the venues it ranks), **posts** (the installments counting them down) and
**snapshots** (editions frozen on a date). A venue can be an entry in several series.

| Series | Project | Ranks | Posts |
|---|---|---|---|
| `bakeries-top100` | `bakeries` | top 100 of 205 bakeries & sweets shops | 11 |
| `coffee-top50` | `coffee` | top 50 of 127 coffee shops & roasteries | 6 |
| `coffee-daan-top10` | `coffee` | top 10 of the 27 in Da'an | 1 |
| `coffee-xinyi-top10` | `coffee` | top 10 of the 11 in Xinyi | 1 |

`series/index.html` is the dashboard for all of them (see [Series](#series)).

All fetching (Instagram, Google Maps, search, blogs, articles) goes through `fwdproxy:8080`.

## Layout

```
pipeline.py            runs the steps in order; shows a project's status
project.py             picks the project (-p NAME) and its paths
series.py              series: entries, snapshots, publishing, the series dashboard
series_server.py       series.py serve: the dashboard with editing
crawl.py ... posts.py  the steps (each takes -p NAME; posts.py also -s SERIES)
ig_api.py              Instagram profiles through the Graph API (not used by the steps yet, see below)
*_template.html        dashboard / graph / slide / preview templates, labelled from the project config
projects/<name>/
  config.py            everything category-specific (see below)
  seeds.json           crawl seeds and handles to skip
  overrides.json       hand-reviewed account labels
  data/                inputs: Google places, press, review notes, photo picks, trusted blogs
  output/              graph (index.html), ranking (ranking.html), photos/ (gitignored photo cache)
series/
  index.html           the series dashboard
  <id>/series.json     what the series ranks and how it is worded
  <id>/snapshots/      editions: <date>.json
  <id>/posts/          slides and captions (gitignored)
data/                  caches shared by all projects (gitignored): profiles/, profiles_api/, google_raw/,
                       blogs/, search_raw/, articles/; related_snapshot.json (saved related-account lists)
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
| product | `product.py` | Fetches the articles in `press.json` and counts, per shop, how many of its Google reviews, review highlights and articles praise or criticise the product itself (the config's `PRODUCT` words). `product.py report --weights ...` shows the top N with what-if ranks | `data/product.json` |
| notes | *manual*, `review_notes.py` | `review_notes.py export` writes each top shop's Google material to `output/review_input.json`; a person or an LLM writes the summary, must-try items, highlights and lowlights into `data/review_notes.json`; `review_notes.py check` validates them | `data/review_notes.json` |
| rank | `rank.py` | Scores and dashboard: network endorsement 35%, review-adjusted Google rating 30%, press 15%, review volume 10%, followers 10% | `output/ranking.*` |
| series | `series.py dashboard` | Reranks every series from the new ranking and rewrites the series dashboard | `series/index.html` |
| posts | `posts.py` | For each of the project's series: picks a photo from each shop's own Instagram, renders 1080×1350 slides with headless Chromium and writes captions | `series/<id>/posts/` |
| photos | *manual* | Look through `series/<id>/posts/index.html`; pin better photos in `data/post_overrides.json` (`posts.py -p PROJECT --candidates HANDLE` downloads options), then rerun `posts` | `data/post_overrides.json` |

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

## Instagram through the Graph API

`ig_api.py` reads profiles through the Graph API's Business Discovery instead of the logged-out
page: a Business or Creator account's posts from the last year (up to 400) rather than its
latest 12, read as the app user's own professional account. It needs a long-lived user access
token in `~/.config/tpe-food-graph/ig_token`; the script's docstring says how to get one, and
`ig_api.py whoami` checks it. `ig_api.py fetch HANDLE ...` and `ig_api.py crawl N` fill
`data/profiles_api/`, which no step reads yet. From the first test (2026-11-16):

- It returns captions only: no photo tags, no related accounts, nothing for personal accounts.
  In the 278 labelled accounts whose cached posts still have photo tags, captions show 64% of
  makers' links but 38% of bloggers'; foodie.taiwan @mentions 1 account in a year of posts and
  tags 128 in its latest 12.
- It's slow: the app's server time per hour runs out after about 600 posts ("Application request
  limit reached"), so a year of posts for the 788 labelled accounts takes about 33 hours, and
  coffee's about 5.
- It suits coffee best, whose graph is caption-only already. Before its posts count in a graph,
  `build.py` needs one time window for every account, and the 3-post standing-tag rule has to
  allow for accounts with many more posts.
- The photo tags in profiles cached before 2026-11-03 exist nowhere else: don't refetch those
  profiles (`ig.profile(..., refresh=True)` would replace them with tagless posts).

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
- **Product**: `PRODUCT` words for the product itself (not the place), praise and complaints;
  `rank.py` scores it only if `WEIGHTS` has a `product` weight
- **Ranking**: weights, `TOP_N`, which subtypes are ranked, `REQUIRE_GOOGLE`, `GOOGLE_PRIMARY`
  (optional: a shop whose first, main Google category doesn't match is left out, whatever its
  label), `EXCLUDE` (shops left out by hand, with the reason), dashboard wording and chart items
- **Instagram series defaults**: title, headline, colours, caption wording, hashtags, what a good
  photo shows. Each series can override them

and follow `python3 -I pipeline.py brunch`. Then add a series:
`python3 -I series.py new brunch-top30 --project brunch --top 30`.

## Series

A series is `series/<id>/series.json`:

```json
{
 "project": "coffee",
 "title": "Top 10 coffee shops in Xinyi",
 "top_n": 10,
 "filter": {"district": ["信義區"]},
 "where": "Xinyi, Taipei",
 "posts": [[10, 1]],
 "series": {"short": "Xinyi Top 10 Coffee", "title": "Xinyi's Top 10 Coffee Shops", "zh": "信義區咖啡廳 TOP 10",
            "hashtag": "#信義區咖啡top10", "headline": ["The", "Top 10", "coffee shops in\nXinyi"]},
 "caption": {"outro_last": "That's Xinyi's top 10! ..."}
}
```

Only `project` is required. With no `filter`, the series ranks every candidate, like the
project's own ranking. A `filter` keeps candidates whose `district`, `area` or `type` is one of
the listed values, and the series ranks them again by score (the dashboard shows each venue's
project-wide rank too). A brand qualifies through any of its branches. If the branch in the
district isn't the brand's best-scoring one, the series enters that branch, with its own
score, Google rating and address. The brand's menu items stay on its slide, but its summary
doesn't, since the summary may describe another neighbourhood. `posts` lists each post's rank
range. By default the countdown goes in tens and ends with 10-4 and the top 3; a top 10 of one
district fits one 11-slide carousel. Wording comes from the project's `SERIES`, `CAPTION` and
`HASHTAGS`, with `{top}` and `{where}` filled in, and anything under `series`, `caption` or
`hashtags` overrides it.

**To create and edit series in the browser**, run

```
python3 -I series.py serve          # http://localhost:8765/  (--port to change)
```

and open the link (from a laptop, forward the port: `ssh -L 8765:localhost:8765 <devserver>`, or
use your editor's port forwarding). It's the same dashboard with editing turned on:

- **New series** opens a form: project, districts (each with its candidate count), city, shop
  type, top N, and the post split. As the filter changes it shows how many candidates match
  and suggests the id, name, place and wording (e.g. Xinyi's Top 10 Coffee Shops, 信義區咖啡廳
  TOP 10, #信義區咖啡top10). Change any of it before saving.
- On a series page: **Edit** (the same form; empty wording fields fall back to the project's,
  and a new top N rewrites the old number in the wording), **Take snapshot**, and **Delete**
  (only a series with no snapshots).
- On the Rankings tab, each row has **↑ / ↓** (move one place), **Pin…** (put at a rank, with an
  optional note), **Unpin**, and **Remove…** (leave out of this series, with a reason). See
  [Hand edits](#hand-edits).
- On the Posts tab: **Render posts** runs `posts.py -s <id>` and shows its log; **Mark published**
  takes the post's link and date, and **Mark not published** undoes it.

Changes are written to `series/` in the repo; commit them like any other edit. The server answers
only on localhost, and every change needs a token that is only in the page it served. The file
`series/index.html` (and any copy of it, e.g. on Drive) stays read-only.

The same things from the command line:

```
python3 -I series.py                                   list series
python3 -I series.py new coffee-zhongshan-top10 --project coffee --top 10 --district 中山區
                                                       (also --area 台北市, --type roaster, --where; wording is suggested as in the form)
python3 -I series.py show coffee-xinyi-top10           entries, posts and what moved since the last snapshot
python3 -I posts.py -s coffee-xinyi-top10              photos, slides and captions (-p coffee: every coffee series)
python3 -I series.py snapshot coffee-top50 --label "First edition"
python3 -I series.py publish coffee-top50 1 --url https://www.instagram.com/p/...  [--date 2026-11-20]
python3 -I series.py unpublish coffee-top50 1
python3 -I series.py dashboard                         rewrite series/index.html
```

### Hand edits

The scores set each series' order, but you can change it per series. Hand edits are saved under
`adjust` in that series' `series.json` and change nothing else (not the project's ranking or other
series):

```json
"adjust": {
 "exclude": {"whood_drinkandfood": "more restaurant than café"},
 "pin": {"southcity_coffee": {"rank": 2, "note": "best pour-over in the district"}}
}
```

Venues left out are dropped from the series (the dashboard lists them with the reason and
where they would rank). Each pinned venue takes its rank; everyone else fills the remaining places in
score order. So after a rerank months later, pins stay where you put them and the rest move with
their scores. The dashboard marks pinned rows with their score rank, and a pin or removal whose
venue is no longer a candidate is listed as having no effect. ↑ / ↓ pin the venue one place up
or down; if another pinned venue is in that place, the two swap. Posts, captions, snapshots and
the review-notes check all follow the adjusted order. From the command line:

```
python3 -I series.py pin coffee-xinyi-top10 southcity_coffee 2 --note "best pour-over in the district"
python3 -I series.py unpin coffee-xinyi-top10 southcity_coffee
python3 -I series.py exclude coffee-xinyi-top10 whood_drinkandfood --reason "more restaurant than café"
python3 -I series.py restore coffee-xinyi-top10 whood_drinkandfood
```

**Snapshots** are editions. `series.py snapshot` writes `snapshots/<date>.json` with every
candidate's rank, score and score components, the commit the ranking came from, and each post's
shops and caption, plus the hand edits in effect. Take one when an edition's posts go out, then mark each post published
(date and link) as it goes up. Publication records belong to the snapshot. Months later, recrawl
and rerank the project. The dashboard then compares the live ranking with the last snapshot:
who entered or left the top N, who moved and how far. When the new edition is ready, take a
new snapshot and publish again. `--replace` retakes a snapshot for the same date and keeps the
publication records of posts whose rank ranges haven't changed.

**The dashboard** (`series/index.html`, rewritten by every `series.py` command, by `posts.py`
and by the pipeline's `series` step) has:

- an overview of every series, grouped by project: its top 3, the latest snapshot, whether the
  live ranking has moved since, and how many posts are published and rendered
- a venues table: each venue's rank in every series, to see which venues appear in more than one
- a page per series:
  - **Rankings**: the top N and, if you choose, every candidate, with the change since a chosen
    snapshot, the other series a venue ranks in, and the score's components on hover
  - **Posts**: each installment's shops, rendered slides (when `posts/` exists on this machine),
    caption, and publication status. Slots where the live ranking now differs are flagged
  - **Snapshots**: each edition, plus what changed between any two snapshots or a snapshot and the
    live ranking

## Project notes

**coffee** (series: top 50 in 6 posts; top 10 in Da'an and in Xinyi, one post each): 127 Greater Taipei coffee shops ranked (one entry per brand) out of 178 in a
262-account graph. Seeds came from 49 articles (`data/article_urls.txt`) and per-district
searches for café profiles (`data/extra_handles.txt`); three crawl rounds were reviewed by
hand. Differences from bakeries, all in `projects/coffee/config.py`:

- Network endorsement weighs 25% and press 25% (bakeries 35% / 15%): logged-out Instagram
  now shows only caption @mentions, so the coffee graph has 186 tags to the bakery graph's
  840 and a couple of tags would otherwise swing a shop's score.
- `REQUIRE_GOOGLE`: only shops with a Google Maps listing are ranked (no bean-only brands).
- `GOOGLE_PRIMARY`: a shop Google lists first as something other than a coffee shop is left out,
  even if it is labelled a café: 9 so far (brunch restaurants, dessert shops, cocktail bars, a
  restaurant and a cake shop). The dashboard's methodology names them with their category.
- Press search is scripted (`press_search.py`, top 100); the trusted blogs add six café-heavy
  blogs to the bakery list.
- One entry per brand: branches (Rufous, Oasis, Now Chance, Yokoso) are represented by their
  best-scoring branch and listed on its slide and in its caption. `classify.same_brand` finds
  them (a bio naming the other account, or the same handle apart from generic words and branch
  numbers); `BRANDS` / `NOT_BRANDS` in the config add or split groups. Press coverage of one
  branch goes to that branch when the title names it ("Rufous Coffee Roasters 2").
- The district series rank the coffee pool again within a district. Da'an has 27 candidates;
  Xinyi has only 11, so its top 10 is nearly all of them. A deeper crawl of Xinyi cafés
  (`search.py "instagram 信義區 咖啡廳"`, then `fetch_list.py`, review and rerank) would make it
  more selective.
- Google matches fixed by hand, including flagships listed under Chinese names, are in
  `data/google_overrides.json`; 24 photos and a few slide names are pinned in
  `data/post_overrides.json`.

**bakeries** (series: top 100 in 11 posts): moved into `projects/bakeries/` unchanged. With the
refactored scripts, `google_maps.py`, `press.py`, `rank.py` and `posts.py` reproduce the
committed outputs exactly. `build.py` needs the profile cache (`data/profiles/`, not committed). One entry per brand
leaves the top 100 unchanged; Celebread-TM (No. 178) is now listed under Celebread. The graph
rules above (staff, line-ups, business ties) came after the bakery graph was built; they apply
once `build.py -p bakeries` is rerun with a profile cache. The committed bakery ranking also
predates the PageRank change (links adding up to less than one tag pass on only that share):
rerunning `rank.py -p bakeries` moves scores by under 0.5 and swaps No. 100 (come_up_patisserie.tw
in, ponpie out).
