# Vinted API notes (all facts live-verified; dates given)

Unofficial surface, observed not documented. Re-verify before relying on
anything here after a long gap.

## Catalog API (probed 2026-09-05, in production since 2026-09-06)

`GET https://www.vinted.de/api/v2/catalog/items` with an anonymous session
cookie. Params that work: `search_text`, `per_page` (96 ok), `page`,
`order=newest_first`. Returns per item: `id`, `title`, `brand_title`,
`size_title`, `status` (condition, German: Neu mit Etikett / Neu ohne
Etikett / Sehr gut / Gut / Zufriedenstellend), `price{amount}`,
`total_item_price{amount}` (incl. buyer fee - the price buyers compare),
`service_fee`, `favourite_count`, `view_count`, `promoted`, `user{id,login}`,
`photos`, `url`, plus `item_box`, `search_tracking_params`, `content_source`
(unexamined - possible ranking signals). NOT verified: country/shipping
fields, category filter params (`catalog[]`), item-detail endpoint auth.

## Session mechanics (the hard-won part, probed 2026-09-08)

- `GET /` hands an anonymous `access_token_web` cookie: a JWT with a
  **24-hour** lifetime, plus `refresh_token_web` (90 days).
- **A request already carrying a token cookie gets NO reissue** - the
  homepage answers 200 and leaves the stale cookie untouched. Recovery from
  expiry therefore REQUIRES clearing the cookie jar first. This asymmetry
  caused the 09-07 outage.
- `POST /oauth/token` with `{client_id:"web", scope:"public",
  grant_type:"refresh_token", refresh_token:<refresh_token_web>}` returns a
  fresh access token (200, verified). Not used by the watcher (clean-slate
  homepage GET is simpler and proven); documented as fallback.
- Cookie domains differ (`.vinted.de` vs `.www.vinted.de`); duplicate names
  across domains make httpx `Cookies.get()` raise CookieConflict - read the
  jar directly.
- Anti-bot: served via Cloudflare; DataDome cookie present but cleared for
  plain requests. No wall was hit at ~1 req/2-3 s from this residential IP
  through 09-08. Datacenter IPs (Fly etc.) untested.

## Incident 2026-09-07: 46h silent outage + fabricated outcome data

Token expired 09-07 10:41:41Z; last successful poll 10:40:51Z. Old refresh
path (homepage GET with stale jar) could never mint a token, so every cycle
401'd and re-armed a 1h backoff. Scheduled task showed LastTaskResult 0
throughout because run-hidden.vbs launched detached. Worse: hourly
`recheck_gone` kept visiting item pages on the dead session, was bounced off
`/items/`, and recorded **375 rows gone across 15 batches of exactly 25,
0 sold flags, 100% gone-rate per batch** - fabricated sales. All 375 were
reset on 2026-09-08 (backup `data/vinted.db.bak-2026-09-08`); trustworthy
outcome data therefore starts 2026-09-08 with `gone_source` provenance.

v2 hardening (shipped 2026-09-08, tests in
`tools/tests/test_vinted_watcher_session.py`): jar-clear before refresh;
proactive renewal 45 min pre-expiry; 401 = 10 min backoff vs 403/429 = 60
min escalating to 6 h (Retry-After honored); SessionWall aborts the whole
cycle; non-JSON 200 treated as wall; recheck needs a same-cycle API success
AND a live token; login/consent redirects abort the pass writing nothing;
>40% gone batches discarded; re-sighted listings clear their gone verdict;
stall alert to phone after 45 min, re-nag 6 h; vbs waits and propagates exit
codes; in-place schema migration (never delete the DB).

## Kleinanzeigen (probed 2026-09-05, parked)

Search page is a client-rendered microfrontend behind Akamai Bot Manager:
200 OK but zero listing data in HTML (no prices, no ad IDs, empty JSON-LD
itemList). Plain-HTTP scraping is out; would need Scrapling browser
fetchers or the unofficial mobile API.
