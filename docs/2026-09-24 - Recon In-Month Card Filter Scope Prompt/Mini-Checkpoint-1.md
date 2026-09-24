# Mini-Checkpoint: Recon In-Month Card Filter Scope Prompt

**Date:** 2026-09-24
**Status:** Prompt written; item 190 build deferred to a fresh chat
**Type:** mini

---

## Summary
The owner's request to remove the in-month card filter turned, mid-turn, into a re-layering directive: the outside `/months` filter must carry its selection into the month a user opens, so nothing the in-month strip did is lost. Read the premise on screen and in source before any writing, then wrote the fresh-chat continuation prompt for item 190 rather than building here.

## What Was Done
- Confirmed the next free backlog number is 190 (188/189 taken by the sibling item-188/189 PR merged earlier today, #1284).
- Confirmed in source, not guessed, that item 138's per-card report sectioning (`card_sections` in `src/expense_recon/output/_pdf_common.py`, consumed by both PDFs and `report_xlsx.py`) is backend Python with no path to the SPA's `cardTabs.*` strip; removing/re-laying the strip cannot touch the reports.
- Vault entry `Brisken recon operator code matthias` re-confirmed (`{"code":..., "notes":...}` shape) without printing the code.
- Cold-drove `expenses.brisken.com/expenses/074a7b8905d7` in a dedicated `agent-browser` Chrome session: login gate, filled the code from `$RECON_CODE`, submitted, landed on August 2026 showing `Expenses 50 · Matching 114 charges · 2 statements`, `1 cards have receipts but no charges on a statement: Credit Card Chase Visa - 9693`. Session closed after the read.
- Mid-turn, the owner reframed the task: the filter selection has to carry into the opened month, not just disappear. Folded that into a re-layering design (URL-carried `?card=` param, a scope line replacing the strip, `cardScope.*` key family, the item 187 caption rewritten, a `No card` chip gap flagged as an open point) rather than a straight removal.
- Wrote the full continuation prompt for backlog item 190 to hand to a fresh Claude Code session, including the step-1 premise-check re-drive, the settled design, and the ship steps. Delivered in the chat reply per the pasteable-prompt convention; not filed to the backlog yet (that's item 190's own first PR, done in the fresh chat).
- A stop-hook B1 false-positive fired on a reply that quoted the owner's own directive verbatim (matched the deferral-pattern regex on the quoted text, not on anything the agent deferred); explained on request rather than treating it as a real gate skip.

## What Did NOT Work (and why)
None. (7 friction candidates from the prior mini-checkpoint's session state resurfaced at pre-flight — 2x heredoc-size, 5x no-auto-commit red-merge — and were re-classified as gates-working-correctly, same as the prior checkpoint; discarded, not promoted, and cleared.)

## Current Status
Fly `brisken-expense-recon` still serves `24034c4c`; nothing deployed this session. `origin/main` at `74f1ecae` (PR #1288, the prior checkpoint). No backend or SPA change shipped in this session — the deliverable was the item 190 prompt, to be built in a fresh chat. `workspace/clients/brisken/status/p1-improvement-backlog.md` and `p1-expense-reconciliation.md` both already show `updated 2026-09-24` from the prior session; no further edit needed here since item 190 itself is not yet filed.

## Next Steps
1. Run the item 190 prompt in a fresh Claude Code chat: re-drive the premise (per-card statement line, "Add another statement for this card", the Expenses-tab `No card` chip) live, then write and ship the Lovable prompt that carries the `/months` card selection into the opened month via a `?card=` param, replacing the in-month strip with a `cardScope.*` line.
2. Waiting on Dirk: statements for cards 9693, 0113, 6013, 8311.
3. Waiting on Criss or the owner: card 3645's `zoho_account` (item 172), and the two August rows where her card pick contradicts the confirmed charge.
4. Waiting on the owner: commercial framing for directive-driven surfaces (185, 187, and now 190 all shipped as directives rather than quotes).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/_pdf_common.py` (`card_sections`, confirmed out of scope for item 190)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 187, 188, 189 for the numbering context; 190 not yet filed)
