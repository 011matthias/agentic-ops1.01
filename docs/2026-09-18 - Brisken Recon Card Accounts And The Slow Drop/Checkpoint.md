# Checkpoint: Brisken Recon Card Accounts And The Slow Drop

**Date:** 2026-09-18
**Status:** Two owner reports turned into shipped items in one stretch; the card-account tree is live but dormant until the owner sets it in Settings

---

## Summary
The owner raised two things in his own words and both shipped: cards are a flat list where 2838 is really an account with subcards (item 147, Fly v182), and the manual receipt drop "is taking way too long" (item 148, Fly v183, measured 40 files from 8.36 s to 1.58 s at stub latency). He also audited a sibling session's closing list and asked whether it was true; it was, with one caveat and three omissions.

---

## What Was Done This Session

### Item 147, the card account tree
1. Filed from the owner's words (PR #1085), then built and shipped (PR #1090, Fly v182) after two rulings: **"just do it, no quoting"** and **"only 2838 has subcards, no where else"**.
2. A card gains an optional `parent`, keyed by card `key` because that is the key space `settings["cards"]` is already indexed by. Validated on save against self-parent, unknown parent, inactive parent, two-level nesting and cycles, five stable codes in the item-130 shape.
3. `card_sections` renders the account first with its subcards under it; the account's figures are the sum of itself plus its subcards, its own un-rolled figures stay as `own`. **A statement that covers the account is named once** instead of once per tab, which was the owner's actual complaint. Both PDFs follow the tree. Matching is untouched.
4. Eleven wiring points cut by hand, each turning a named route-level test red and restoring byte-identical.

### Item 148, the slow drop
5. Diagnosed from the code before proposing anything: `POST /api/receipts` returns a `job_id` at once, so the wait was never the HTTP call. `route_dropped_receipts` read each file's date with a full vision extraction **one file at a time** before anything could be filed.
6. Measured rather than asserted, with a stub client at 0.200 s per cold extraction: routing was exactly `N x 0.205 s`, filing was 0.11 s of an 8.36 s 40-file drop. After the change, 40 files route in 1.42 s. At a real 3-5 s round-trip that pile was 2-3.5 minutes and should now be 25-40 s.
7. The reads run on a bounded six-wide pool; one writer assembles the ledger in staged order afterwards, so it is byte-identical to the serial one for the same folder. `month_override` still opens no file. The frozen stage now counts (`reading receipts (7/40)`), throttled.

### The owner's audit
8. He pasted a sibling session's "left to work through" list and asked if it was true. Checked each line against live state: true, with item 104's line ahead of the ledger (its record PR was still open) and one line I could not confirm from the record (120's exclusion). It omitted item 146, item 144's unpasted prompt and the three unverified prompt halves.

---

## Key Decisions Made

### Build item 147 as covered work, not a quote
- **Choice:** owner ruled "just do it, no quoting".
- **Rationale:** he has reversed the quote-separately default for several audit items already; this is the same pattern.

### Only 2838 is an account
- **Choice:** 2838 holds 3876, 3645 and 0340; every other card stands alone, including 1176 despite having its own statement PDF.
- **Rationale:** owner's exact words, "only 2838 has subcards, no where else". The three subcards are the ones sharing its statement file, which is what the data shows and what he did not contradict. Stated explicitly in the reply so a wrong reading is cheap to correct.

### Parentage is data, never inferred
- **Choice:** nothing in the app derives a parent from a statement file.
- **Rationale:** sharing a statement is evidence, not proof, and three cards appear on no statement at all. The four sharing July's file belong to three different people, so person cannot infer it either.

### Six workers, not sixteen
- **Choice:** bounded pool at six.
- **Rationale:** the builder found `llm/client.py` has **no retry or backoff of its own** and leans on the SDK's `max_retries=2`. With no burst control to fall back on, a wide pool would spend the shared key's headroom on retries.

---

## What Did NOT Work (and why)
- **Five points of my item-148 diagnosis were wrong, and the builder corrected each.** The extraction cache DOES hit between the two passes (3 files make 3 calls with it on, 6 with it off), so the "paying vision twice" worry did not apply. `llm/client.py` has no retry or backoff at all, where I had told the builder to look for existing handling. Job timings DO exist in SQLite (`created_at` / `updated_at`) but never reach `GET /jobs/{id}`, where I had said no timing was exposed anywhere. "The routing runs for minutes" is a comment inside a helper, not the docstring I attributed it to. And the Lovable prompt I pre-authorized was not needed: the published bundle renders the stage string verbatim.
- **My "no shared mutable state beyond `rows` and `routed`" was true of production and missed what actually broke.** `MockLLMClient`'s ordered `extraction_responses` queue is positional, so once reads run in parallel "the first call" stops being "the first file". One test was genuinely order-sensitive and passed ten times out of ten by luck; it was converted to a name-keyed mock rather than adding production machinery whose only beneficiary is a test double.
- **The builder's own new guard masked the pre-existing one.** Its first per-file-failure proof stayed GREEN because the new worker guard absorbed the exception the inner catch used to handle, so neither was provably load-bearing. It added a test that raises past the inner catch to isolate each. This is the same shape as item 146's copy-less fixture: a test that passes because the thing that would break it is absent.
- **The card-account tree cannot ship with the code.** `settings["cards"]` lives only in the app's SQLite; the one card file on disk is a different shape with no parent and is documented as never committed. A grep for the live card numbers across `src`, `config`, `examples`, `tools` and `scripts` finds them nowhere.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/cards.py` | edit | `parent` on Card, `_validate_card_parents`, `card_parents` |
| `src/expense_recon/output/_pdf_common.py` | edit | `_card_tree`, roll-up figures, statement named once |
| `src/expense_recon/output/reconciliation_report_pdf.py` | edit | `card_parents` keyword |
| `src/expense_recon/web/service.py` | edit | tree through the run and expenses payloads and both reports |
| `src/expense_recon/web/intake_mail.py` | edit | parallel routing reads, per-file progress |
| `tests/test_card_accounts_item_147.py` | add | 22 route-level tests |
| `tests/test_drop_speed_item_148.py` | add | 10 tests incl. the cache differential probe |
| `docs/lovable-card-accounts-prompt.md` | add | SPA tab strip, not pasted |
| `status/p1-improvement-backlog.md` | edit | items 147, 148, Shipped rows |
| `docs/api-contract.md` | edit | card tree, stage-text |

---

## Current Status
Fly v183 carries both items. The card tree is **live but dormant**: `parent` is on every card, no parents are set, and August's sections are byte-identical to before the deploy, which is the negative contract holding on the real screen. The drop is six-wide with a counting progress stage. Brisken platform line: unknown plan, no ops data; comms-log 10 days stale. Two p2 status files stale past the 21-day threshold: `p2-product-decks.md` (57d) and `p2-targeting.md` (58d), neither touched this session.

---

## Next Steps
1. Owner sets 3876, 3645 and 0340 to account `card-2838` in Settings, Cards; then drive August and confirm the account section reads 111 charges / 9 matched / USD 10,862.66 open / 19 receipts.
2. Owner drops a real pile and reports the wall clock; if it still drags, the next suspect is per-call extraction latency, not the loop.
3. Item 146: `build_card_review` skips a decided copy, with a fixture that contains one.
4. Re-probe charge-category (109) by `[role=combobox]`; establish whether `err.run_not_found` is wired; trigger the crash page in PT.
5. Items 144 and 147's Lovable prompts, both written and unpasted.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 146, 147, 148)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (card tree, stage text)

### Open Questions
- Is 1176 really not an account? It has its own statement PDF, and the owner's "only 2838" may or may not have considered it.
- Should the reconciliation report nest an account's receipt PAGES under it? Today its heading states the group's totals while the pages behind it are the account card's own, so it reads "N receipts on this card". The month report nests properly.
- Should job timings reach `GET /jobs/{id}`? They exist in SQLite and nothing surfaces them, so "how long did that drop take" is unanswerable from outside the database.

### Working Notes
Bundle baseline 2026-09-18: 46 chunks / 1,287 KB, i18n chunk `chunk-x-DkEroC52.js`. The crawler's reference regex MUST accept backticks. The API host is `brisken-expense-recon.fly.dev`; `expenses.brisken.com` serves only the SPA and the SPA calls `api.expenses.brisken.com`. Python's default urllib User-Agent is refused by Cloudflare with `403 error code: 1010`. Read the Fly version back with `flyctl releases`; siblings deploy on the same app within the hour.

### Reference Materials
- `.scratch/i148/bench_drop.py` (the drop benchmark, stub-client latency configurable)

---

## How to Continue
Take the owner's two Settings actions as the gate on verifying item 147, and item 146 as the next code item. Everything else in the queue is a drive to run or an owner action.

---

## Strategic Feedback

### What Worked Well This Session
- **Diagnose from the code, then have the builder measure.** Item 148's cause was provable by reading; its magnitude was not, and saying so plainly in the brief is what produced a benchmark instead of a guess. The `N x 0.205 s` linearity is what turned a hypothesis into a fact.
- **Briefing a builder to correct me.** "Report anything in my diagnosis that turned out to be WRONG, I would rather be corrected than agreed with" returned five corrections, two of which changed the design (pool width, no prompt needed).

### Suggestions
- **Make the negative-case fixture a standing item in every builder brief.** Three defects in two days came from a test passing because the row class that breaks it was absent: item 146's copy-less equality fixture, item 147's zero-charge subcard, item 148's two guards masking each other. The brief line that worked was naming the specific absent class, not a general "test the negative".

### System Health
- `tools/regress_check.py` has now been unusable on three consecutive items: it reports "RED (no pytest summary line)" whether or not the mutated suite failed, so every builder has been told to prove wiring by hand instead. Either fix its verdict or retire it; a tool whose output cannot distinguish the two outcomes is worse than none, because its advisory reads back as evidence.
- **Autonomy score: 0 human interventions.** Both items ran from an owner report to a live deploy without a correction mid-flight.
