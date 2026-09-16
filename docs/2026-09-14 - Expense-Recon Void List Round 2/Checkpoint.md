# Checkpoint: Expense-Recon Void List Round 2

**Date:** 2026-09-14
**Status:** Items 59 and 56 shipped on the owner's two rulings (PR #815), deployed Fly v116, both live months refreshed on an explicit yes and driven in the browser. The prediction made before that yes was wrong; the correction is recorded (#818).

---

## Summary

The two rulings the previous round left open were taken and built: a charge's legal entity now comes from the card it printed, blank when the registry cannot name that card, and an invoice and its receipt are one matcher candidate instead of an ambiguous pick. Refreshing the two live months turned July's 24 reconciled into 27 and cleared every ambiguous pair on both, at zero model cost. The entity-gap the item was written against turned out to be a stale batch snapshot rather than missing card data.

---

## What Was Done This Session

### Item 59: a charge's entity comes from its card
1. `service.stamp_charge_entities` resolves each charge that printed a card (`card_last4`) through the batch's registry snapshot, via the same `resolve_card` identity the coverage panel and the card scoping already use, ambiguity resolving to nothing. Empty when the registry cannot name the card or names it without an entity; a workbook with no card column keeps the upload's entity, because there the account id is the card.
2. Stamped inside `rematch_month`, before the match, so the entity the matcher scoped on is the entity the row shows. Ids do not hash the entity, so re-stamping never moves a charge or its decisions.
3. `summary.n_charges_no_entity` on both payloads, its own name beside `n_needs_entity` (which is the receipt-side question).
4. The hand-match guard was sharpened to the matcher's own rule, since a charge can now legitimately carry no entity: empty on either side is unscoped, only two named entities that differ refuse.

### Item 56: an invoice and its receipt are one candidate
5. `duplicates.collapsed_duplicate_copies` names every copy after the first in each duplicate receipt group the reviewer has not ruled `ignore`; `rematch_month` keeps those out of the candidate pool.
6. Nothing is dropped: the copy stays in the snapshot, the counts, the exports, and rejoins `unmatched_receipts[]` carrying its duplicate marker, so the reconciliation guarantee holds.
7. `POST /api/runs/{id}/duplicates/resolve` now re-matches a reconciling month (off the event loop, `_resolve_duplicate_rematch`), because the resolution decides what the pool holds; without it an `ignore` ruling would be recorded and inert.

### Verification
8. `test_charge_entity.py` (6 route-level) and `test_duplicate_collapse.py` (5). Suite 1542 to 1547, green. Five `regress_check.py` proofs RED under mutation.
9. CI green after merging a sibling's day-boundary fix (#814); squash-merged as `75f006b8`; deployed v116 from a detached origin/main worktree with `fly.toml` verified equal to `flyctl config show` first.
10. Live months refreshed after an explicit owner yes, then both workbenches driven in agent-browser (session `recon-voids`): 1108 rendered cells on August, zero fallback strings, coverage rows naming the real cards.

---

## Key Decisions Made

### The entity is stamped at match time, not at read time
- **Choice:** `stamp_charge_entities` runs inside `rematch_month` rather than in `build_view`.
- **Rationale:** matching is entity-scoped, so a read-time stamp would show one entity while the matcher used another. The cost is that an existing month needs a re-match to pick the change up, which is what the master-data refresh already is.

### Refresh master data, not re-read statements
- **Choice:** the live months were brought current with `refresh-master-data`, not the statement re-read the previous round used.
- **Rationale:** a re-read rebuilds charges from files and changes every id; a refresh keeps ids, so reviewer decisions stay put and the LLM judgment cache (keyed on those ids) answers everything. Measured: zero new model calls on both months.

### The prediction was wrong and the correction is the finding
- **Choice:** recorded in the status file, the backlog and memory rather than quietly moved past.
- **Rationale:** the owner approved the refresh on "about 77 charges move to a blank company". They did not: all nine cards are defined in the live registry with entities. `coverage[].known` reflects the BATCH's upload-time registry snapshot; `/api/settings` is the live registry. Reading a live consequence off the first is the mistake to not repeat.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../src/expense_recon/web/service.py` | edit | `stamp_charge_entities` + its call in `rematch_month`; pool collapse; `n_charges_no_entity` on both views; manual-match guard |
| `.../src/expense_recon/duplicates.py` | edit | `collapsed_duplicate_copies` |
| `.../src/expense_recon/web/app.py` | edit | `_resolve_duplicate_rematch`; the resolve route re-matches |
| `.../tests/test_charge_entity.py`, `tests/test_duplicate_collapse.py` | new | route-level tests |
| `.../docs/api-contract.md`, `docs/lovable-charge-entity-prompt.md`, `docs/PROMPT-STATUS.md` | edit / new | contract, SPA half, applied-state ledger |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | items 59 + 56 ruled and shipped, Shipped row 33, the live correction |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | round-2 paragraph, elements row, the live correction |
| memory `project_brisken_expense_recon_usability_loop.md`, `MEMORY.md` | edit | round-2 outcome and the coverage-vs-settings rule |

Merged in PR #815 (`75f006b8`) and PR #818 (`36258262`).

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ? (no `platform` section; Fly hosts the FastAPI app).

Backend live at v116. Both live months carry the new behaviour, measured after the refresh:

| Month | Reconciled | Review | Unmatched receipts | Ambiguous picks | Charges with no entity |
|---|---|---|---|---|---|
| August 2026 | 14 | 3 (was 7) | 14 | 0 (was 2) | 0 |
| July 2026 | 27 (was 24) | 11 (was 15) | 13 | 0 (was 1) | 0 |

Unmatched receipts rose on both because the suppressed duplicate copies now surface there by design. Criss's remaining work is the undecided rows: 17 on August, 3 on July. Two Lovable prompts are unapplied (`lovable-month-health-prompt.md`, `lovable-charge-entity-prompt.md`). The notifier's scheduled task still runs from the main checkout, which is behind origin/main; re-match mails start once that checkout is pulled.

---

## Next Steps

1. Item 60: a charge with waiting candidates renders "No receipt found". Read the live rows first. The LOVABLE 25.00 row that prompted the item now renders "Awaiting decision" on the August workbench, so the live symptom may have moved with the re-matches; confirm before designing a fix.
2. Item 61: receipts routed by receipt date never meet a charge in the neighbouring statement period. Extend the trip-pool idea to adjacent company months under the `receipt_claims` protocol.
3. Items 62 (settled-outside-the-card disposition), 63 (same-currency candidates off the 20% FX band, with `calibrate` as the gate), 64 (column map + card currency per `statements[]` entry; unknown `Type` labels keep the printed sign).
4. Pull the main checkout once its dirty meji file is committed by its session, so the scheduled notifier runs the new script.
5. Four p2 status files are stale (85d / 53d / 54d / 54d); a p2 session should update or delete them.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 59, 56 ruled; 60-64 open; Shipped row 33)
- `.../docs/api-contract.md` ("An invoice and its receipt are one candidate", "A charge's entity comes from its card")
- `.../src/expense_recon/web/service.py` (`stamp_charge_entities`, the pool collapse in `rematch_month`)
- memory `project_brisken_expense_recon_usability_loop.md` (2026-09-14 paragraph)

### Open Questions
- Item 60: is the effective bucket wrong or the SPA's label? Needs a fresh read of the live rows, since the symptom may have changed.
- Does anything still want the entity-less charge path, now that every card is defined? The code is correct either way, but the `n_charges_no_entity` tile ships a count that is currently always 0.

### Working Notes

**The correction, stated once.** `coverage[].known` answers "did THIS BATCH know the card" (it reads the batch's config snapshot, frozen at upload). `/api/settings` `cards_effective` answers "is the card defined". All nine Brisken cards are defined with entities: 3645, 3876, 0113, 0340, 2838 are Corporate Services; 6013, 9693, 8311 are Cloud Services; 1176 is Consulting. The owner finished that data entry after these batches were uploaded, which is why the batches looked ignorant of it.

**The refresh is the cheap re-match.** `POST /api/expense-batches/{id}/refresh-master-data` pulls the current registry into the batch and re-matches without touching ids, so decisions survive and the judgment cache answers every pair. Both months reported `judgments_new: 0`.

**A regress proof that proved nothing.** The first mutation for the resolve-re-match was `rematch = None or await run_in_threadpool(...)`, which is semantically identical to the original. It reported TEST BITES anyway, so the red came from something other than the disabled behaviour. Re-run with `if reconciling:` to `if False:`, which is a real disable. A mutation has to actually change behaviour or its red is noise.

**Test fixture trap.** `.pdf` filenames carrying JPEG bytes skip the vision path entirely and fall back to a filename-derived vendor, so a duplicate group never forms. Use `.jpg` for mock-extraction fixtures.

**CI traps.** A branch whose PR was squash-merged conflicts on the next follow-up; cut a fresh branch off main instead of pushing more onto it. And the hooks job failed on a vinted day-boundary test that a sibling had already fixed upstream (#814); merging origin/main cleared it.

### Reference Materials
- PR #815 https://github.com/011matthias/agentic-ops1.01/pull/815 and PR #818 https://github.com/011matthias/agentic-ops1.01/pull/818
- Live API `https://brisken-expense-recon.fly.dev` (operator code in vault "Expense Recon App"); SPA `https://expenses.brisken.com`
- Fly release v116

---

## How to Continue

`/resume brisken`. Cut a fresh branch off `origin/main` (the round-2 branch is squash-merged and must not be reused). Read the live August rows for item 60 before designing anything, then items 61-64 in order: one PR per round, route-level tests, a `regress_check.py` proof per fix that genuinely disables the behaviour, CI-green merge, `flyctl deploy .` from a detached origin/main worktree, agent-browser drive.

---

## Strategic Feedback

### What Worked Well This Session
- Putting both rulings as decisions with a recommendation and a named consequence, rather than as open offers, got them answered in one turn and unblocked two items that had been waiting a round.
- Refusing to fire the live refresh until it was approved, and then reading the result honestly enough to notice it contradicted the prediction, is what turned a wrong assumption into a recorded rule instead of a silent one.

### Suggestions
- The SPA's coverage panel says "not in your card list" from a snapshot that can be months stale. It should say "not in this month's card list" or offer the refresh inline, because the current wording sent this session, and probably the owner, hunting for card data that already existed.

### System Health
- Autonomy: 1 human intervention (the two rulings, answered together; the live-refresh yes was a second, correctly asked). Gates: B1:0 B2:6 (five regress proofs, full suite, live distinguishing probe, two browser drives) B3:2 (the CI failure attributed to my own branch state first, then verified as a sibling's upstream fix; the wrong prediction traced to my own instrument) skipped:0.
- One self-caught verification failure worth the register row: a mutation that did not change behaviour still reported TEST BITES, which means `regress_check.py` cannot tell a no-op mutation from a real one. The discipline has to be the author's.
