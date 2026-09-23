# Mini-Checkpoint: Attribution Instrument And The Card Memory That Never Arrived

**Date:** 2026-09-23
**Status:** Item 169 shipped and deployed; items 170, 171, 172 measured and open
**Type:** mini

---

## Summary

Built the instrument the attribution work had been missing since it started
(`tools/recon-attribution-replay.py`), then shipped the one thing it said was
worth rows: a remembered card is read live instead of off the stamp ingest
left, which gives 12 live September rows a card, a company and a person. Three
of the four facts item 169 predicted turned out to be worth zero, one, and the
wrong diagnosis; the instrument is what separated them.

## What Was Done

- **`tools/recon-attribution-replay.py`** (PR #1220, merge `ee5b45c4`). Replays
  a hosted month through `build_expense_view` itself, so its rows are the rows
  Criss sees. Scores card / entity / person / category by link against the
  statement's own `Card` column on confirmed pairs, and against the reviewer's
  own fixes **held out**. `--what-if` re-runs with one link changed and diffs.
  Proven before trusted: a fabricated hint rule for a hint exactly one row
  prints moved the count by exactly one, in all three coupled columns.
- **Item 169 fixed and deployed.** `service.fill_remembered_cards`, wired into
  the grid and the CSV export (Cards R3), and through the export into the month
  report. Live after deploy: September card-less **26 -> 14**, no entity
  **25 -> 13**, no person **25 -> 13**, 12 rows sourced `learned`; July and
  August unmoved. Verified by API read AND a cold-Chrome SPA drive (the company
  cell renders "Corporate Services from card Credit Card Chase Visa - 3645 ·
  Dirk Neumann", 13 of 19 OpenAI rows show 3645, zero show a fallback).
- **Item 170 measured, not built.** Canonical keying is worth 7 live rows.
- **Item 171 filed** (the sign-off learner cannot see `settled_charge`; 24 rows
  waiting, zero live effect). Written and deliberately reverted: it writes
  durable memory and had no bite test.
- **Item 172 filed** (PR #1221): card `3645`'s registry entry holds
  `zoho_account: "Credit Card - 2838"`, another card's label in an account
  field. Found by the post-deploy consumer drive.

## What Did NOT Work (and why)

- **Item 169 fact 1** (narrowing `_card_keys` so a printed number naming no
  card stops blocking the fallbacks): moves **zero rows across all seven
  batches, 198 receipts**. The three July rows it would unblock (`...2544`,
  `0501-1462-9129`, `Cartao Credito 30 Dias`) have no matched charge and no
  remembered card, so nothing sits behind the guard; September has no
  statement. The patch was proven live (`{'2544'}` -> `()`) before the zero was
  believed.
- **Item 169 fact 3 as diagnosed** ("the learned `card_key` is keyed on a
  company the failing row does not have"): the key already matched. September's
  batch entity is `''`, every card-less row carries `''`, the rule is keyed
  `('', 'openai')`, and `lookup('', 'OPENAI')` returns `{'card_key': '3645'}`.
  The real cause was the ingest-time freeze beside it.
- **Measuring the alias fill by patching settings**: reported 0 rows, and a
  control that rewrote EVERY merchant's category to one value also reported 0.
  The probe is blind by construction, and the blindness is the finding:
  `categorize_receipts_with_registry` runs only when receipts are ADDED, so the
  registry CATEGORY is frozen at ingest exactly as the card was.
- **First held-out category score** (0 right / 0 wrong / 35 silent): the
  override key is `(document_id, line_index)` and I joined on document alone. A
  structurally blind probe returning a confident "the chain produces nothing".
- **Playwright MCP for the consumer drive**: attaches to the user's busy Edge
  on :9222 and timed out at 30s. agent-browser on a cold Chrome seat worked.

## Current Status

Item 169 is live on Fly (`ee5b45c4`, machine `7843d54b579598`), verified
through both the API and the SPA. No live writes were made to Criss's months.
`brisken` platform ops status: unknown plan (no `platform` section in
`infrastructure.yaml`), comms-log absent.

Two brisken status files are stale and were not touched (they belong to p2, not
this session): `p2-product-decks.md` (62d), `p2-targeting.md` (63d).

## Next Steps

1. **Item 171** — pass `settled_cards` into the sign-off learner's resolution,
   with a statement-attached month, a publish, and a regress-checked bite test.
2. **Item 170** — key learned rules on the registry canonical (7 rows), and
   decide whether the registry CATEGORY should be read live the way item 169
   made the card.
3. **Owner's**: the alias `PUT /api/settings` diff (prepared, not sent), and
   card 3645's real Zoho account for item 172.
4. The category chain's measured problem is **coverage, not accuracy**: silent
   on 15 of the 35 rows a human corrected, every silent one `REVIEW`.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 169-172)
- `tools/recon-attribution-replay.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`fill_remembered_cards`, `resolve_batch_row_cards`)
