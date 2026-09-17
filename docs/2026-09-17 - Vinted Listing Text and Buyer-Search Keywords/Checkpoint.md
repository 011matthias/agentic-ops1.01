# Checkpoint: Vinted Listing Text and Buyer-Search Keywords

**Date:** 2026-09-17
**Status:** Live on all 19 open listings; bot-side buyer-search ranking not built

---

## Summary

Started as "the notification no longer opens Vinted" and ended with every open listing rewritten and re-keyworded from evidence. Along the way the watcher gained description capture, the listing bot gained a truth gate and a slop validator, and 11 listings turned out to be sold rather than broken.

---

## What Was Done This Session

### Watcher
1. Tap-to-open fixed (#892): the svc-catalogue payload from #889 returns `url` as a path. ntfy could not open it, and `recheck_gone` would have skipped every new row (httpx `UnsupportedProtocol` is an `HTTPError`, swallowed by `continue`). 2,235 stored paths backfilled; ntfy read-back confirmed 87 path-only alerts before, absolute after.
2. Description capture (#928): the hourly recheck stores the description from the page it already fetches. Live pages carry a schema.org Product block; sold pages only `<meta name="description">`. The first live run stored 21 of 25.

### Listing bot
3. Hashtag vocabulary (#929): `keyword_research --tags` splits run-together tags into buyer words, gives one vote per listing, falls back to the whole class, rejects brand names, and gates `tag_demand` on sold counts.
4. Truth gate (#930): a market term reaches a description only when the item's facts justify every word. Before this, title-mined cell terms put "baggy fit / washed blau" on a Diesel pair nobody had called either.
5. Text voice (#936): `build_description` writes only facts (cut, details, one measurements line, named flaws) with no TBD. `validate()` blocks seller notes and warns on sales fluff; on the live texts it flagged exactly #32–34.

### Live account (owner-approved passes)
6. v3 descriptions on 19 listings: measurements now on 20 of 30 rewrites (was 3), review corrections applied (#18 light blue + jersey), unsourced fabric and blanket "keine Schäden" dropped. #32–34 carry "sitzt locker und weit" after the owner confirmed Baggy Fit.
7. v4 keyword lines on the same 19, from Vinted's German buyer-search suggestions: 15 changed, 4 unchanged, each verified by reloading the edit form, plus one public-page read.

---

## Key Decisions Made

### Keywords from buyer searches, not seller vocabulary
- **Choice:** Rank keyword candidates by `api.vinted.de/search-bar/v2/suggestions` with `locale: de-DE`, `source: query_data`.
- **Rationale:** It is the only demand-side signal found. The watcher corpus is supply-side, and sold counts per class (35 pants, 14 shirts) are too thin for term ranking. Words Vinted parses as entities ("herren" = Men category) are never added.

### Only fact-justified words are written
- **Choice:** Market terms without full fact support go to `keyword_candidates`, never into text.
- **Rationale:** An untrue word is a return and a "nicht zugehörige" hide reason. The 2026-09-16 review marked exactly that class do-not-apply.

### Owner's titles win over file titles
- **Choice:** #32–34 texts follow the owner's "Baggy Fit"; the applier skips any live text that is neither the file text nor a known version.
- **Rationale:** The owner had retitled after publish, and the v3 pass briefly reasserted "gerades Bein" against those titles.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/vinted-reselling/watcher/vinted_watcher.py` | Modified | `item_url()`, `item_page_description()`, `descriptions` table, recheck capture |
| `workspace/projects/vinted-reselling/listing/keyword_research.py` | Modified | tag mining, class fallback, `tag_demand`, `--tags` |
| `workspace/projects/vinted-reselling/listing/keyword_engine.py` | Modified | truth gate, `details`/`flaws` facts, new `build_description`, slop checks |
| `tools/tests/test_vinted_{watcher_session,outcomes,keyword_research,keyword_engine}.py` | Modified | caller-level tests for each change |
| `tools/fixtures/vinted-item-page/item_{alive,sold}_description.snippet.html` | Created | real-byte page fixtures |
| `workspace/projects/vinted-reselling/status/{watcher,listing}.md` | Modified / Created | status roll-ups |
| `.scratch/vinted/driver/{descriptions-v3,descriptions-v4,descriptions-backup-2026-09-16}.json`, `apply_descriptions_v3.py`, `build_v4_keywords.py` | Created (gitignored) | live texts, backups, applier |
| `.scratch/vinted/{harvest_suggestions.py,suggestions-2026-09-16.json}` | Created (gitignored) | buyer-search harvest |

---

## Current Status

Watcher runs from `agentic-ops1-watcher` at origin/main (8f66519 or later) and stores descriptions; `descriptions` had 59 rows on 09-16 night. All 19 open listings carry v3 text + v4 keywords, verified. 11 batch-1 listings plus #27's relist are sold. vinted-reselling has no `infrastructure.yaml` (a Windows scheduled task, not an orchestrator).

---

## Next Steps

1. Build buyer-search ranking into `keyword_research` (suggestions endpoint, `query_data` only, entity words filtered), so new listings get v4-grade lines without a hand pass.
2. Owner in-hand checks: #23 size S, #29 black vs navy, #30 colour, #18 colour field (Red only for a red/light-blue/navy polo).
3. Watch the 19 for hearts and sales against the v4 change; the price-position finding (under 50% of median sells 49% vs 9–12% above 75%) is the larger lever.
4. Re-run `keyword_research.py --tags */pants` once 40 descriptions per class exist; `tag_demand` needs 30 sold per class.

---

## Context for Next Session

### Files to Read First
- `workspace/projects/vinted-reselling/status/listing.md`
- memory `project_vinted_resale_intake`, `reference_vinted_watcher_corpus_limits`, `reference_vinted_has_no_hashtags`

### Open Questions
- Does "Thermal" belong on waffle-knit listings? Buyer search exists (402), but the 09-16 critic called it a warmth claim. Not applied; #25 sold anyway.

### Working Notes
- Logged-in wardrobe feed includes SOLD items (`is_closed`, `item_closing_action: sold`, `can_edit: false`); their `/edit` crashes in server render and `item_upload` GET answers 404 code 104. Filter on `can_edit`.
- Reading public item pages (2 MB each) from the owner's Chrome drew 429 after 10. The edit form is cheaper and is the verification source.
- An automation tab left open goes stale (wardrobe 401); reload the home page before API calls.
- The Playwright MCP browser is attached to the same Chrome (port 9222), so it is not a cold/logged-out view. On item pages `document.body.innerText` exposes ~150 chars; read the `[itemprop="description"]` element instead.
- Description split: 19 live listing ids are in `.scratch/vinted/driver/apply-v4-results.json`.

### Reference Materials
- PRs #892, #894, #928, #929, #930, #933, #936
- `.scratch/vinted/review-2026-09-16.json` + `review-2026-09-16-critic.md`

---

## How to Continue

`/resume` on vinted-reselling, read `status/listing.md`, then pick Next Step 1. Any live-listing edit needs the owner's explicit yes per pass; rerun `apply_descriptions_v3.py --source=vN` (readiness first, without `--apply`).

---

## Strategic Feedback

### What Worked Well This Session
- Differential probes settled every "why" in one read-only step: locale de-DE vs en-US on suggestions, #01 vs #05 edit forms, sold vs live pages for the description source, and the wardrobe field diff that found `can_edit`.

### Suggestions
- `apply_descriptions_v3.py` should move from `.scratch` into `listing/` with tests. It now encodes three hard-won rules (can_edit filter, owner-edit guard, edit-form verification) that a fresh session would re-derive.

### System Health
- An unvalidated negative ("11 edit pages broken") reached the owner as a LIMITATION with a user action. The feed's semantics came from a memory written for the anonymous view. The instrument-validity clause covers this; applying it before reporting would have saved a round trip.
- Autonomy: 3 human interventions (two owner decisions via AskUserQuestion, one correction "it should work").
