# Checkpoint: Recon Date Decides Month

**Date:** 2026-10-07
**Status:** Backend LIVE (Fly `60196a0c`); SPA prompt not pasted; two rows for Criss to fix by hand

---

## Summary
A July receipt sat in January because the upload filed it by a misread date and a later re-read corrected the date without moving it. Owner ruling: the receipt's date decides its month, so a changed date now moves the receipt (backlog item 251), with a guard that holds a typed day/month swap.

---

## What Was Done This Session

### Diagnosis (notes #114, #117, #118 in `/feedback.jsonl`, 118 notes)
1. January's row is `0001__CARD-136_2026-07-05_USD-6.20_MP-PARADAOBRIGAT__BENCH-010.pdf`, uploaded on the Receipts page 2026-09-23 23:55 UTC. The upload's full extraction read the slip's faint `04/07/26` as a January date; item 240's re-read (2026-09-28) wrote 2026-07-04 in place; item 77 only offered a move on a TYPED date, so it stayed. `2026-07-04 23:56` is the printed date and time (receipt image read), not the upload time.
2. It is a second copy: July holds `0071__20260704_Receipt_Food_ParadaObrigatoria.pdf` (same operation 16727/5113354, BRL 32.00), matched to `MP *PARADAOBRIGAT` USD 6.20.

### Build (PRs #1594 + #1602, deployed via `deploy.py`)
1. `route_expense_by_date` (service.py): a changed date (PUT typed/cleared, dated POST add, real re-read where no date was typed) moves the receipt to its calendar month through `move_expense_to_month`; replies carry `moved` / `move_held` / `move_error`; re-read dry run names `moves_to`, never moves.
2. `date_month_target`: the upload's plausibility rule from the batch's month (1 day future grace, 366 days); published months hold the move.
3. Offer (`month_move`): read dates outside the item-25 window; typed dates whenever the month differs.
4. Swap guard (owner choice via AskUserQuestion): a typed date whose day/month swap lands in the batch's month is held (`held: "day_month_swap"`, `date`, `swap`).
5. Bug fixed: the move's same-bytes check matched the target's own soft-deleted copy, so moving a receipt back into a month it left lost it.
6. SPA prompt `docs/lovable-date-moves-month-prompt.md` (toast + months-list refresh on `moved`, swap/held/failed strings), PROMPT-STATUS row.

### Checkpoint-time repairs
1. Backlog: the item merged as "248" while a sibling's Receipt overview also took 248 (249/250 taken too) -> renumbered 251. A sibling merge (`bfc96b57`, PR #1604) then kept both copies, leaving `### 248. The date decides...` with the body and an empty `### 251.` on main; restored 251 from `504a323b`, deleted the stale block.
2. `tools/tests/test_p1_backlog_item_numbers.py`: fails CI on any reused backlog item number (finds `248` on main's pre-repair backlog).
3. `.claude/patterns/warn-stop-merge-left-pending.md` -> `block-stop-merge-left-pending.md` (5th recurrence; tested: blocks this session's closing text, silent on a finished close).

---

## Key Decisions Made

### The date decides the month
- **Choice:** month = calendar month of the receipt's effective date when the date CHANGES; untouched rows only get an offer, read dates only outside the window.
- **Rationale:** owner ruling verbatim ("if user changes date, then the month changes accordingly"); live read showed 3 June-dated July rows held by July's 07-01 charges, which a month-equality offer would have invited Criss to break.

### Swap guard
- **Choice:** hold a typed date whose day/month swap lands in the batch's month (owner picked the recommended option).
- **Rationale:** July's NORMANDIE SEINE toll (file 2026-07-05) was typed as 2026-05-07 the morning the rule shipped; the date cell is the browser's native picker, which follows the browser locale.

---

## What Did NOT Work (and why)
- **Ending the turn while the full suite ran:** commit/push/PR/merge/deploy were only promised; the owner had to type "continue" (5th recurrence of this closing).
- **Picking the backlog number at branch time:** siblings took 247, then 248-250 during the session; the second clash merged and a sibling's conflict resolution duplicated the section.
- **Large Python patches through a Bash heredoc:** blocked by the heredoc-size / triple-quote gates (3x); Edit worked.
- **`regress_check.py --file` with a repo-relative path:** resolved against `--cwd` (the module), "no such file"; pass module-relative paths.
- **First full suite run:** files changed under it (renumber + merge) and `-x` stopped at the first failure, so later files never ran; rerun on the merged tree.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/web/service.py` | Modified | routing, plausibility, offer, swap guard, move fix |
| `expense-reconciliation/src/expense_recon/web/app.py` | Modified | PUT / add routing + reply keys |
| `expense-reconciliation/src/expense_recon/web/receipt_reread.py` | Modified | `moves_to`, `route_moved_dates` |
| `expense-reconciliation/tests/test_date_decides_month_item_251.py` | Created | 14 route-level tests |
| `expense-reconciliation/tests/test_{month_move,receipts_reread_item_240,neighbour_rematch_item_112,view_contract}.py` | Modified | old offer-only behaviour replaced |
| `expense-reconciliation/docs/{api-contract,PROMPT-STATUS,lovable-date-moves-month-prompt}.md` | Modified/Created | contract + SPA half |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Modified | item 251, duplicate 248 removed |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | element row for item 251 |
| `tools/tests/test_p1_backlog_item_numbers.py` | Created | duplicate item-number guard |
| `.claude/patterns/block-stop-merge-left-pending.md` | Created (warn version deleted) | Stop block |

---

## Current Status
LIVE on Fly `60196a0c` (deploy.py VERIFIED: healthz commit + machine size). Live read: January `n_month_moves` 1 (Parada -> July), July 2 (Crossmedia -> March, NORMANDIE -> May). SPA drive on the published bundle (payloads replayed, 0 writes) renders "Move to July 2026"; same drive before the deploy read none, and read an injected offer. brisken ops: platform unknown plan (no `platform` section in infrastructure.yaml).

---

## Next Steps
1. Owner: paste `expense-reconciliation/docs/lovable-date-moves-month-prompt.md` into Lovable; verify `expx.review.monthMove.swap` / `.held` / `.failed` in the bundle, then a replayed `moved` reply shows the "Moved to" toast.
2. Criss (her months, no agent writes): delete the January Parada copy (batch `4ceaeb461386`); retype July's `0027__...NORMANDIE_SEINE...` as 2026-07-05.
3. Itemize notes #118 (record details read-only, payment date editable) and #115 (old categories on the January row).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 251
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "The date decides the month"

### Open Questions
- Is Criss's browser on an English (US) locale, so the native date picker is month-first? Unverified; the swap guard covers only swaps that land in the batch's own month.

### Working Notes
- Live off-month rows before the deploy: 5 of 339, all machine-read.
- Read-only SPA drive script pattern: Playwright, `executable_path` = system Chrome, token in `localStorage['erc-token']`, heavy `/api/(expense-batches|runs)/{id}` read once and replayed, every non-GET except `/api/login` aborted and counted; the first-visit "Leave feedback anywhere" dialog covers the screenshot but not the DOM text.

### Reference Materials
- PRs #1594, #1602; feedback notes #114-#118 (`GET /feedback.jsonl`)

---

## How to Continue
`/resume brisken`, read item 251, then the next steps above. Never type a date into a live month to test the rule: the edit moves a real receipt.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring the live estate (one read per month, 5 of 339 rows) before choosing the offer rule kept three matched July receipts out of the offer.
- The control drive (pre-deploy absent, injected present) proved the SPA probe could see an offer before its post-deploy PASS was trusted.

### Suggestions
- Backlog item numbers are a shared counter edited by parallel sessions with no lock; the new test catches a clash at CI on the merge ref, but a PR whose CI ran before the sibling merged still lands one. Allocating the number at merge time (or a `next free item` helper in the ship chain) closes it.

### System Health
- Autonomy: 2 human interventions ("continue" after a stalled close; the swap-guard decision).
