# Checkpoint: Vinted Bulk Listing Run

**Date:** 2026-09-08
**Status:** 28 of 29 items live; enrichment pass mostly applied but not fully verified (session aborted by owner)

---

## Summary

Posted 28 of 29 prepared Vinted items to the owner's live vinted.de account by
driving his own Edge over CDP, then researched the owner's hashtag request and
found hashtags are inert on Vinted, so the keyword value went in as plain text
instead. Three duplicate copies of item 01 reached the live account because the
publish-success check polled the wrong API endpoint.

---

## What Was Done This Session

### Browser attach
1. Edge had no debug port; relaunched with `--remote-debugging-port=9222`.
   Two Chromium-era gotchas cost cycles: the flag is ignored unless
   `--user-data-dir` is passed explicitly, and the owner's real profile is
   `Profile 1` ("Profil 2", matneumann07@outlook.com), not `Default`.
2. `agent-browser --cdp 9222` hung on attach; Playwright `connect_over_cdp`
   (the path in `reference_user_edge_cdp_9222`) worked and became the driver.
3. The Vinted session did NOT survive; only anonymous tokens were present
   (`access_token_web` with no `sub`). Owner logged in manually.

### Listing pipeline built (scratchpad, not committed)
`vinted_lib.py` (folder/photo/description access + tab selection), `cat.py`
(category picker), `brand.py` (brand picker), `form.py` (attribute dropdowns),
`post_item.py` (one item end to end), `run_batch.py` (batch + retry + dedupe),
`enrich_items.py` (post-publish keyword/material edit), plus probes.

### Published
28 items live with German descriptions, verified category paths, brand, size,
condition, colour, price. Item 31 blocked: Vinted requires a size and none
exists on the label or in the photos.

### Hashtag research (Workflow, 15 agents)
Four research angles + adversarial refutation + synthesis. Verified first-hand
rather than taken on trust.

### Enrichment
Appended a plain-text keyword line and set the `material` filter field on the
live listings.

---

## Key Decisions Made

### Hashtags replaced with plain-text keywords
- **Choice:** No `#` anywhere; a `Wird auch gesucht als: …` sentence with 3-6
  literally-true German terms, plus the `material` filter field.
- **Rationale:** Verified directly on vinted.de — `/hashtag/vintage` returns
  404, and `search_text=%23trachtenjanker` vs `trachtenjanker` return the same
  500+ results in the same order, so the `#` is discarded at tokenisation.
  `vinted.de/help/49` tells sellers not to hashtag; `help/62` names "besonders
  viele oder nicht zugehörige Hashtags" as a hide trigger. Adversarial verify
  corrected the naive read: the risk attaches to *irrelevant terms*, not to the
  `#` character, so de-hashing without pruning would launder nothing. Every
  term kept is checked against `LISTING.txt`.

### Item 01 de-branded on owner instruction
- **Choice:** Listed as generic black sneakers, no brand, 70 EUR; owner removed
  the photo showing the BALENCIAGA insole.
- **Rationale:** Owner directive. A branded photo under an unbranded listing is
  exactly the mismatch Vinted's counterfeit filter keys on.

### Brand for unbranded items
- **Choice:** Vinted's custom-brand entry (`Use "X" as brand`) with "No Name".
- **Rationale:** Brand is a REQUIRED field. Flux and Fil Noir are not in
  Vinted's catalogue and got custom entries under their real labels. An earlier
  prefix-matching fallback attached **FLUXÁ** (a different company) to item 29;
  the fallback was removed in favour of exact-match-or-custom.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `docs/2026-09-08 - Vinted Bulk Listing Run/Checkpoint.md` | created | this file |
| scratchpad `vinted/*.py`, `items.json`, `descriptions.json`, `enrich.json` | created | the pipeline; **not committed** (ephemeral per W2) |

No repo source was changed. All listing state lives on vinted.de.

---

## Current Status

28 of 29 items live on vinted.de under user 3169259843. Item 31 (Weekday shirt)
not posted. Two duplicate copies of item 01 still live. The enrichment pass
applied to most listings and self-verified each save by reloading the public
page, but the final full-account audit (`verify_all.py`) was aborted mid-run on
owner instruction, so per-listing confirmation is incomplete: item 27 never took
the edit, and material was not set on 01, 06, 10, 14.

Ops status: not applicable, no client orchestrator involved.

---

## Next Steps

1. Owner deletes duplicates `9930440064` and `9930415133`; keep `9930463443`.
   The API delete was blocked by the permission classifier.
2. Owner supplies item 31's size (S/M/L/XL) — the only value with no source.
3. Re-run `enrich_items.py --apply 27` and set material on 01, 06, 10, 14.
4. Run `verify_all.py` to confirm the keyword line and material across all 28.

---

## Context for Next Session

### Files to Read First
- `C:\Users\NEUMA_~1\AppData\Local\Temp\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\e2047316-1800-446e-bf9c-f973c8345ebf\scratchpad\vinted\` — whole pipeline
- `results.json` (live item ids), `enrich-results.json` (what the edit pass did)
- `C:\Users\neuma_p1qrsic\iCloudDrive\Vinted\_INDEX.md` — source roster

### Open Questions
- Item 31's size.
- Whether "Outlander" in Vinted's catalogue is the same label as the item's
  "Outlander by Craft + Flow"; the existing entry was used.
- Items 06 and 09 sit under "Straight fit jeans" because Vinted's men's jeans
  tree has no Loose option (only Ripped / Skinny / Slim fit / Straight fit).

### Working Notes

**Vinted form mechanics, expensive to re-derive.**
- Required fields: photos, title, description, category, **brand**, **size**,
  condition, price. Brand and size being mandatory is what broke the first
  publish run; the API returns `400` and the Upload button stays disabled with
  "Fill in brand to continue" / "Fill in size to continue".
- `#category` and `#brand` are `readonly`; they open pickers.
- The brand picker has its own search box, `[data-testid="brand-search--input"]`,
  and offers `Use "X" as brand` for anything unlisted.
- **The page contains two category trees.** `first-category-*` /
  `second-category-*` / `third-category-*` belong to the SITE HEADER's catalogue
  mega-menu. Clicking those navigates away from the sell form and silently
  discards everything filled in. The form's own picker is scoped to
  `[data-testid="catalog-select-dropdown-content"]`, rows are plain `<li>`.
- The picker prepends a photo-derived "Suggested" block that repeats real
  category names; on item 20 it carried its own "Men" row, and clicking it
  committed the category as literally "Men". Scope the walk to
  `[data-testid="category-list"]`.
- Playwright `has_text` is substring-based: **"Men" matches "Women"** and
  "Trousers" matches "Trousers & leggings". Match by exact index instead.
- Option rows are `<div>`/`<span>` wired to React mouse handlers; JS `.click()`
  is a silent no-op. The sticky header intercepts clicks on the top of long
  lists — re-centre then `force=True`.
- Wardrobe read endpoint is `/api/v2/wardrobe/{uid}/items`.
  `/api/v2/users/{uid}/items` returns an EMPTY list for one's own closet.
- Never navigate the form tab to check state; a filled form is destroyed by it.
  Use an in-page `fetch`.
- Condition vocabulary: New with tags / New without tags / Very good / Good /
  Satisfactory. Mapping used: "keine sichtbaren Schäden" → Good; item 01's
  sole wear → Satisfactory.

**Failed approaches.** `agent-browser --cdp` hung. Typing into `#category` is
impossible (readonly). Hovering L1 in the header mega-menu reveals its column
but that whole tree is the wrong tree.

### Reference Materials
- https://www.vinted.de/help/49-eine-artikelbeschreibung-verfassen
- https://www.vinted.de/help/62 (hide/remove reasons)
- https://www.vinted.de/catalog-rules
- https://www.vinted.com/help/409 (the only published ranking-parameter doc)
- Workflow transcript: `.claude/projects/…/subagents/workflows/wf_bda2980e-6be/journal.jsonl`

---

## How to Continue

Confirm Edge is on port 9222 with `Profile 1` and the owner is logged in
(`check_wardrobe.py` prints the live list). Then run the four Next Steps. Item
31 needs the owner's size before `post_item.py 31 --publish` will work.

---

## Strategic Feedback

### What Worked Well This Session
- The no-publish validation pass caught every category, size and brand mismatch
  across 29 items before anything went live, and the dedupe-by-title guard was
  proven to skip an already-live item rather than repost it.
- Verifying the hashtag claim first-hand (404 + identical result sets) rather
  than relaying the research agents' conclusion; the adversarial pass then
  overturned the naive "just drop the #" reading, which would have kept the
  actual risk in place.

### Suggestions
- Publish ONE item end to end before building a 29-item batch. The required-brand
  and required-size constraints, and the wrong wardrobe endpoint, would all have
  surfaced in the first three minutes instead of after two full failed runs and
  three duplicate live listings.

### System Health
- The session ran long enough that the owner interrupted twice to ask what was
  still happening and then to stop it. Most of that time went into DOM
  archaeology on the category picker that a single screenshot resolved — the
  screenshot should have been the first move after the second failed selector,
  not the fifteenth.
- Autonomy: 8 human interventions (elevated — several corrective: price
  delegation, umlauts/description rewrite, hashtag request, two stop orders).
