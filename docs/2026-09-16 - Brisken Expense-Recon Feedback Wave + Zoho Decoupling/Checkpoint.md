# Checkpoint: Brisken Expense-Recon Feedback Wave + Zoho Decoupling

**Date:** 2026-09-16
**Status:** Feedback wave recorded as backlog items 73-77; Zoho decoupling rounds 1/3/6a shipped and deployed; seven rounds ordered and queued

---

## Summary

Read the app's own `/feedback.jsonl` for the first time and found 42 operator notes going back to 2026-07-15, seven of them left that day. Turned the wave into five ownable backlog items, then executed the owner's follow-on directive to decouple the app from Zoho: the account layer is renamed and kept, the Zoho-shaped export is queued for deletion behind its SPA prompt.

---

## What Was Done This Session

### The feedback wave (items 73-77, PR #875)

1. Pulled `/feedback.jsonl` off the backend (bearer from `POST /api/login`, code in vault entry "Expense Recon App"). 42 notes, 11 from September, 7 from 2026-09-15.
2. Grounded every note against the live July (`50622baec444`) and August (`074a7b8905d7`) payloads rather than its wording. Two of the seven turned out to be already fixed and waiting on a Lovable paste; one was the report backlog item 27 had been parked on for five days.
3. Recorded five items with the evidence attached, renumbered 73-77 after a sibling session claimed 72 mid-review.

### The Zoho decoupling (PRs #881 + #883)

4. Four-way read-only inventory (Workflow, 5 agents, 106 classified references) producing an ordered ten-round plan with a collision map. It corrected three of its own sweeps.
5. Shipped round 1 (`output/posting_common.py` lifts the nine helpers two surviving modules import out of `zoho_export.py`), round 3 (every backend-owned human string), and round 6a (the writeback column, with a permanent dual-read).
6. Deployed to Fly and verified on live data, including a cold browser drive through the login gate.
7. Recorded the remaining seven rounds under backlog item 23.

---

## Key Decisions Made

### Keep the chart-of-accounts mechanism, delete the Zoho-shaped export

- **Choice:** Rename the account layer; delete the journal export in a later, SPA-gated round.
- **Rationale:** Measured rather than assumed. On the live July workbook 64 of 341 account cells carry a real GL code the category alone does not give (`Meals & Entertainment` resolving to `E100010-31 - Travel Expense | Food`); 236 are the fallback echo and 41 are blank. Deleting the layer would lose real accounting data. The journal export meanwhile emits 3 of July's 26 reconciled charges with every account line a placeholder.

### One glossary, decided once

- **Choice:** **Account** in the report PDFs (already there), **Posting account** wherever a distinction is needed, **Expense report category** only for the source document's own category.
- **Rationale:** Three sweeps independently proposed four different words. Criss reads the PDF, the workbook and the CSV; without one glossary she reads three names for one thing.

### Rename the spreadsheet headers now, accept the formula risk

- **Choice:** Owner picked rename-now over a dual-header month.
- **Rationale:** The risk is a VLOOKUP in her private workbooks going silent. Mitigated where it actually bites: the writeback module reads the old header permanently, so a workbook she has already had written back reuses its column instead of growing a second one.

### The duplicate concept is two concepts

- **Choice:** Delete charge-side duplicate detection outright; split the receipt side into same-document (identity) and one-purchase-two-documents.
- **Rationale:** Every charge-side group on both live months is a set of genuinely distinct transactions, and the July Google group is `resolution: confirmed`, so a real 71.64 charge is suppressed today.

### Clean rows confirm themselves, but only after the precision work

- **Choice:** Sequence precision before autonomy.
- **Rationale:** August's reconciled set is 7 right and 7 not. Auto-confirming first would bless wrong money, and since `export_approved_only` defaults `False` those rows already reach the journal.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `status/p1-improvement-backlog.md` | edit | Items 73-77 (the wave) + the ordered Zoho plan under item 23 |
| `output/posting_common.py` | create | The nine shared posting helpers, lifted verbatim |
| `output/zoho_export.py` | edit | Imports the lifted helpers back; behaviour unchanged |
| `output/report_xlsx.py` · `reconciled_csv.py` · `sheet_writeback.py` | edit | Column headers and note text to the new glossary |
| `web/service.py` · `web/app.py` · `matching/deterministic.py` · `categorize.py` · `cli.py` · `doctor.py` · `learning_cli.py` | edit | Advisory, match reason, FX prose, download filename, CLI and doctor output |
| 11 test modules | edit | Assertions moved to the new vocabulary; one new legacy-header test |
| `status/p1-expense-reconciliation.md` | edit | Element row for the decoupling |

---

## Current Status

The app no longer tells anyone it is connected to Zoho in any string the backend owns. Live after deploy: the workbook reads `Posting account` on three sheets and `already posted (yellow row)`, the download is `expenses-<id>.csv`, and a cold browser drive shows zero Zoho on the workbench.

The word survives in three places, all deliberate and all queued: the API field names (`zoho_account`, `zoho_category`), which the SPA both reads and writes; the journal route and its two SPA buttons; and the i18n copy only a Lovable prompt can reach.

The drive also caught the sibling session's matching work landing: July moved from 26 reconciled / 12 review to **31 / 7**, match rate 23.2% to 27.7%.

Ops status line was not printed by pre-flight for brisken (no `platform` section in `infrastructure.yaml`); the app is Fly-hosted and healthy, machine 7843d54b579598 in `fra`, deploy verified.

---

## Next Steps

1. **Paste the three pending Lovable prompts**, in order: `lovable-month-edits-prompt.md` (item 70, backend live on v129), `lovable-card-chips-prompt.md` (item 71, answers note #36), `lovable-view-receipt-prompt.md` (item 52, answers note #32). Two of these are the fix for notes in this very wave.
2. **Round 4, the journal deletion.** Its prompt publishes and is re-audited BEFORE the backend PR, because the published SPA calls `/runs/{id}/zoho.csv` from two lazy chunks.
3. **Items 73-75** (the honest-labels round): statement row types so a card payoff stops reading as a refund; the duplicate split; the Unmatched list saying why.
4. **Reset the July Google duplicate group** (`POST /api/runs/50622baec444/duplicates/resolve`, group `03ba84fadeebe2a5`, `ignore`). Live write on Criss's data, needs a per-action yes. Until then a real 71.64 charge stays suppressed whatever the code does.
5. Two p2 status files are stale (`p2-product-decks` 55d, `p2-targeting` 56d). Not this workstream; bring current in a lead-gen session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` — items 73-77 and the ordered plan under item 23
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` — the three pending pastes

### Open Questions
- Does Criss have formulas keyed on the old spreadsheet headers? Owner accepted the risk; if something of hers goes quiet, the writeback dual-read is the precedent for how to fix it.
- `export_approved_only`: recorded as delete-with-the-journal. Its only consumer is `regenerate_zoho`, so it becomes a toggle that changes nothing.
- The legacy `card_accounts` / `card_entities` settings keys are composed at read time, so retiring them needs a live read of the settings row on the volume first.

### Working Notes

**Read `/feedback.jsonl` at the START of any recon round.** It is the best source in the project and it had never been read. Notes are anchored to the exact page, section and clicked element.

**The matcher is wrong in both directions at once, and that is one root cause.** `EXACT` is amount + date ±1 + currency with the vendor not consulted, which is how `BASE44 50.00` auto-committed a Lovable invoice at `vendor_pct: 40`, `requires_review: false`. Meanwhile all 12 July review rows were FX and seven carried `vendor_pct: 100` with `date_pct: 100`, demoted only because the bilateral uniqueness gate found a rival that merely exists.

**Traps hit this session, worth not re-hitting:**
- A case-sensitive grep for `Zoho` reported zero on a payload holding 294 lowercase `zoho` field names. Grep both cases, and run a control.
- `agent-browser text` is not a command; it exits 0 with "Unknown command", so a grep over its output returns a confident zero. Validate the instrument before believing a negative.
- Playwright MCP here connects over CDP to `:9222` and fails unless the user's Edge is running with remote debugging. `agent-browser --session <name>` works; the first `open` takes several minutes.
- A stray `types.py` in the scratchpad shadows stdlib and breaks any `python <scratchpad>/script.py`. Pipe the script over stdin instead.
- Rebasing an already-pushed PR branch needs a gated force-push. Merge `origin/main` into it instead; the push stays a fast-forward.
- `gh pr merge` prints `fatal: 'main' is already used by worktree` and still merges. Check the PR state, not the exit code.

**The SPA redirects** `brisken-reconcile-dash.lovable.app` to `expenses.brisken.com`.

### Reference Materials
- `https://brisken-expense-recon.fly.dev` — API, operator code in vault entry "Expense Recon App"
- Inventory workflow output: `wf_b1c77a52-659` transcript dir (106 classified items + the 31 KB plan)

---

## How to Continue

Clear the paste queue first; it is three pastes and it closes two notes from this wave with no engineering. Then take round 4 (journal deletion, prompt first) or items 73-75 (honest labels), one item per session in its own worktree per the parallel-round protocol. The main checkout is shared by live siblings and was 72 commits behind at session start; read from `origin/main`, never the working tree.

---

## Strategic Feedback

### What Worked Well This Session

- Grounding every note in the live payload before believing its wording. Three of the seven notes meant something different from what they said, and one (`#40`, auto-match) turned out to describe a mechanism that already works, where the real gap was a list that never says what it contains.
- Measuring the account layer before deciding its fate. The 64-of-341 count turned a preference question into a settled one, and it reversed the direction I was leaning.
- The regress proof. `TEST BITES` on the writeback dual-read is the difference between a green suite and a verified fix.

### Suggestions

- Add feedback notes to `tools/brisken-recon-notify.py`. It already runs every 15 minutes and already mails on new runs and re-matches; one more line per new `feedback.jsonl` entry is the whole fix, and it is what stops the next wave sitting unread for two months. Queued as round 5 of the plan; build it before the next wave arrives rather than after.
- During a parallel round, backlog item numbers need reserving. A sibling claimed 72 while my PR was in CI, costing a rebase, a renumber and a rebuild of the merge.

### System Health

- Autonomy: **4 human interventions** (three decision points put through `AskUserQuestion`, one plan approval). Each decision was one I could not resolve from the code: the coverage-panel degree, the confirmation model, the charge-duplicate feature, the first-round order, and the spreadsheet-header risk in Criss's private workbooks.
- The B2 instrument-validity sub-clause fired correctly twice and was missed once: I told the user "zero Zoho in the payload" on a case-sensitive grep before the differential probe caught it. Same class as the 2026-09-10 rows; the rule exists and still did not hold at the moment of the claim.
- The deploy-consumer gate closed itself on seeing the string `agent-browser` in a command that had not driven anything. Worth knowing that the marker is pattern-matched, not evidence.
