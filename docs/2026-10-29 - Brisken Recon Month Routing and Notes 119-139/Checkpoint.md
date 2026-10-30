# Checkpoint: Brisken Recon Month Routing and Notes 119-139

**Date:** 2026-10-29
**Status:** items 263-265 LIVE (Fly `ab66b1a8`); one SPA prompt waiting to be pasted

---

## Summary
The app's feedback store had 21 notes the backlog had never seen (#119-#139). The GitHub "not matched" notes (#138/#139) turned out to be a routing fault, not a matching one: a mail carrying receipts from several months filed whole under its earliest date. Fixed for new mail, offered as a one-click move for the receipts already misfiled, and two of the notes' UI asks shipped as a published Lovable prompt.

---

## What Was Done This Session

### Feedback and the SPA
1. Read `GET /feedback.jsonl` live: 139 notes, the backlog last cited #118.
2. `docs/lovable-feedback-1029-prompt.md` (notes #123/#125/#126/#128/#130/#132/#136): written, owner published, bundle-audited (48 chunks, controls present) and cold-driven read-only.
3. `docs/lovable-card-account-picker-prompt.md` (note #124): written, NOT pasted.

### Backend (PRs #1683, #1697, both deployed via `deploy.py`)
1. **Item 263:** `intake_mail._file_mixed_months` hands each row of a `mixed_months` mail to `route_expense_by_date` after ingest. On the materialize path it runs only once `_MATERIALIZE_LOCK` is released, because the mover takes that lock and it is not reentrant. `split_to` is recorded on the archive and log row.
2. **Item 264 (#137):** `attach_expense_card_tabs` offers `month_move` on a row no charge holds, dated in another calendar month, on a month with a statement; `n_month_moves` is recounted.
3. **Item 265 (#124):** `card_account_options[]` on `GET /api/settings`, registered in `SETTINGS_DERIVED_KEYS` so the SPA's whole-object PUT stays legal.
4. Each new wire passed `regress_check.py` (red when unwired). The full module suite passed locally: 4348 passed, 2 skipped.

### Live data
1. On the owner's yes: moved 0063 (GitHub 09-05) from August to September. Its bytes matched September's 0007, so only August's row went; September's 11.56 charge now has one chosen candidate (`turn: decide`).
2. Audited Receipt Batch 01/02 read-only: 17 October receipts sit in September, 3 of them held by September charges.

---

## Key Decisions Made

### Mixed-month mail
- **Choice:** each receipt goes to the month of its own printed date (owner, AskUserQuestion), reversing the 2026-08-24 whole-mail rule. The mail still arrives in its earliest month and then splits.
- **Rationale:** the owner's 2026-10-07 ruling that the printed date decides the month (item 251); whole-mail routing stranded receipts with no charge to match.

### Existing strays are offered, not moved
- **Choice:** Criss gets "Move to {month}" on the 14 strays; the agent moved only the one receipt the owner named.
- **Rationale:** memory `feedback_recon_no_live_writes_criss_acts`. The offer requires a loaded statement, because without one "no charge holds it" only means "no statement yet".

---

## What Did NOT Work (and why)
- **Reading the backlog from the primary checkout:** it was 10 commits behind `origin/main`, so #126-#135 looked unrecorded while a sibling had already itemized them as 258-262. Caught only when claiming an item number. That prompted the new rule `warn-backlog-read-from-primary-checkout`.
- **Moving 0062 as approved:** moot. By the time of the move it had already left August, and October holds its own copy (0011, mailed 10-05). Re-reading before the write is what caught it.
- **Playwright MCP:** connects to CDP `:9222` (ECONNREFUSED, no browser listening). Headless Python Playwright with `channel="chrome"` was the working cold seat.
- **A stop-event pattern rule for "prompt named but not pasted":** the stop gate matches code-stripped text, so neither the backticked file name nor a fence is visible to it. Deleted unshipped.
- **First `gh pr merge` of #1676 / #1683:** "merge commit cannot be cleanly created". Sibling rows landed in `PROMPT-STATUS.md` (and main moved the chase-actions row to Applied) while CI ran; resolved by merging main and keeping both sides.
- **`python -I` on a scratchpad helper:** `-I` drops the script directory from `sys.path`, giving ModuleNotFoundError for a sibling module.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../web/intake_mail.py` | edit | item 263 split (ingest + materialize paths), `split_to` on log rows |
| `.../web/service.py` | edit | item 264 offer + banner count |
| `.../web/app.py` | edit | month lookup into the page payload; `card_account_options` |
| `.../web/store.py` | edit | `card_account_options` as a derived settings key |
| `.../category_vocabulary.py` | edit | `card_account_options()` |
| `tests/test_intake_mail.py`, `test_date_decides_month_item_251.py`, `test_card_account_check_item_172.py` | edit | caller-level tests for 263/264/265 |
| `docs/lovable-feedback-1029-prompt.md`, `docs/lovable-card-account-picker-prompt.md`, `docs/PROMPT-STATUS.md` | add/edit | SPA prompts + status |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edit | items 263-265, status paragraph |
| `.claude/patterns/warn-backlog-read-from-primary-checkout.md` | add | friction fix |

(`...` = `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon`)

---

## Current Status
Live on `ab66b1a8`; API and cold browser drive agree with the pre-ship prediction: September banner "13 receipts are dated in another month" (all to October), August 1 (SAP SE 2026-07-05, to July). Only August, September and October exist, so that click would open a July month. brisken platform: unknown plan, ~?/? ops/mo, last assessed ? (no `platform` section in `infrastructure.yaml`).

---

## Next Steps
1. Owner pastes `docs/lovable-card-account-picker-prompt.md`, then bundle-audit `card_account_options` / `set.cards.zoho.none` and drive its three checks.
2. Confirm on screen that note #128's buttons share the title line (the one unverified check of the published prompt), and decide #128's reading against the sibling's still-unpasted chase-actions section 4 (global nav bar).
3. Still unitemized: #118/#119 (only the expense date editable; Criss "Nao consigo incluir a data"), #120 (dynamic month/year grouping), #121 ("what is publish for?"), #122 (RBAC). #120 and #122 are quote-separately features under the licence ruling.
4. Siblings' items 261 (#129, intake misreads) and 262 (#126/#127/#130, delete documents, an owner call) are open.
5. Add a `platform` section for brisken in `infrastructure.yaml` (pre flags it as unknown).

---

## Context for Next Session

### Files to Read First
- `git show origin/main:workspace/clients/brisken/status/p1-improvement-backlog.md` (items 256-265), never the primary checkout's copy
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

### Open Questions
- Should the 3 October receipts held by September charges (0122, 0136, 0137) stay there? They match, so the tool leaves them.

### Working Notes
- Feedback store: 139 notes at 13:40 UTC. Diff against #139 next time.
- `GET /api/inbound/log` rows carry `mixed_months`, `pool_month`, `documents`, and now `split_to`; that is the instrument for this class.
- The move route answers `already_in_batch: true` when the target holds identical bytes and only removes the source row.

### Reference Materials
- PRs #1676, #1683, #1697; Fly `brisken-expense-recon` on `ab66b1a8`

---

## How to Continue
`/resume brisken`, read the backlog from `origin/main`, fetch `/feedback.jsonl`, and diff against #139.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the inbound log before touching the matcher: one GET (`mixed_months: true`, three printed dates) moved #138 from "matching bug" to "routing rule".
- Predicting the live effect from the payloads before shipping (14 offers by month and document id), then checking the deploy against that list exactly.

### Suggestions
- `checkpoint_scaffold.py pre` and the SessionStart hooks read the primary checkout. In a clone with live siblings that checkout is behind, so `pre` flagged status files as 22 days stale that are current on `origin/main`. `pre` should read status/ledger state through `git show origin/main:` when the checkout is behind.

### System Health
- Four hook-caught near-misses (B1 deferral, merge left pending, chained merge, heredoc shape), all corrected in the same turn.
- Autonomy: 3 human interventions (one decision via AskUserQuestion, two re-requests for a prompt body).
