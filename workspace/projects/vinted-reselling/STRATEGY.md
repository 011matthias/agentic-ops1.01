# Strategy

Assessment 2026-09-05, refined through 09-08. Decisions here are the why
behind the build order; operational detail lives in README + api-notes.

## Why Vinted

Europe's main second-hand clothing market, Germany among its biggest pools.
No listing fees and no seller commission (buyer pays the protection fee), so
small flips stay profitable and listing volume costs only time. Supply side
is mostly casual sellers clearing closets, which produces constant
mispricings; those go to whoever sees them first. Speed games favor
automation, and the feasibility probe showed Vinted is unusually watchable
(anonymous JSON API, see api-notes).

## Leverage ranking (from scratch)

1. **Price/demand knowledge** - the actual asset. Knowing what an item is
   worth and how fast it sells scores watcher alerts, prices future own
   listings, guides thrift/kilo sourcing where bots cannot go, and picks the
   niche. Compounds with data; sniping edges erode with competition.
2. **Sourcing watcher** - first build, works from day zero, and its polling
   is simultaneously the data collection for #1. Alerts are the byproduct;
   the database is the point.
3. **Listing throughput** (photo -> draft listing via vision LLM) - the 5x
   time multiplier once stock flows. Not built.
4. **Pricing/markdown engine, inventory P&L, buyer-comms drafting** - later.
   Cross-listing and relist/bump automation deprioritized (complexity, ban
   risk).

## Calibration plan (the optimize loop)

Manual thresholds (searches.yaml) are judgment values. The proper
calibration is a /comd_optimize run: asset = the settings block; scorer = a
deterministic offline backtest over a frozen DB snapshot (replay each
listing at first_seen using only comps visible then; score would-have-
alerted decisions against outcomes; alert-budget penalty); guard =
time-split holdout per docs/optimize/RECIPES.md (constructed metric: scorer
ships as its own PR first). Trigger: a few hundred TRUSTWORTHY gone events
(gone_source-tagged, post-v2 only - the 375 pre-v2 rows were fabricated by a
dead session and were reset). Polling cadence never goes in the loop: it is
a ban-risk surface, not a fitness surface.

Next round of improvements (fake detection, feedback loop, size/country
filters, data-driven brand rules): `improvement-prompt.md`.

## Risk posture

The watcher reads an unofficial API against Vinted ToS. Mitigations: gentle
paced polling, hard backoff on any wall, read-only (no auto-buy, no
auto-list, no bump). Account/IP risk sits with the operator and is accepted.
Kleinanzeigen expansion parked: its search page is client-rendered behind
Akamai; would need browser-grade scraping for uncertain marginal value.
