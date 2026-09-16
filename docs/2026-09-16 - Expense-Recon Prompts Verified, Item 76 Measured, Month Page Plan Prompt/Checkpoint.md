# Checkpoint: Expense-Recon Prompts Verified, Item 76 Measured, Month Page Plan Prompt

**Date:** 2026-09-16
**Status:** Items 70 and 71 closed live; item 76 measured and unbuilt; item 79 (month page restructure) handed off as a planning prompt

---

## Summary

The owner published the two pending Lovable prompts (month-edits, card-chips) and both were verified live by bundle audit plus a cold browser drive, including one reversible write on August. Item 76 was measured before any build: the owner's "exact pairs only" ruling, read literally, would auto-confirm a vendor-46 pair, so a vendor-agreement working rule is recorded. A new owner direction to restructure a month's page became backlog item 79 with a self-contained planning prompt for a fresh session.

---

## What Was Done This Session

### Explained to the owner, plain language
1. PR #881 (Zoho vocabulary out of every human-read string, the writeback column's permanent dual-read header, the account layer kept on the 64-of-341 GL-code evidence), then the day's other fixes: item 70, item 69 rounds A and B, items 51 and 52.

### Two Lovable prompts verified live
1. Handed both prompts as pasteable text. PROMPT-STATUS showed view-receipt already applied, so the pending set was two, not the three I had first told the owner.
2. Bundle audit through a scratchpad copy of `tools/lovable-bundle-audit.py` with this round's six keys: 49 chunks, 1,015 KB, controls 5 of 5, keys 6 of 6.
3. Browser drive cold from the login gate at 1440x900 over July and August on both pages. Card chips, counts, breakdown line, banner, collapsed strip and fold position all checked; the unlocked grid (0 of 412 buttons disabled), View receipt on Review expenses, and the proposed-category note (7 renders for 7 flagged rows) checked. Evidence rows are in PROMPT-STATUS.
4. Reversible live write with an owner yes. Category had no blank option, so the test moved to tax label on August `0025__Invoice-H0LHY2WQ-0032.pdf`: `TEST-0916`, PUT 200, survived a full reload, cleared, August counts identical before and after.

### Next actions proposed, owner ruled
1. Ranked: feedback wave 73-77, the missing 1176 and 9693 statements, naming cost centers (`settings.cost_centers` is `{}` though the feature is live), item 72, Zoho rounds 2 and 4. Checked first that cost centers are actually deployed (#834 merged, totals endpoint 200).
2. Owner ruled: auto-confirm exact pairs only; work 73-77 in order, 76 first.

### Item 76 measured, not built
1. Worktree `agentic-ops1-item76` cut on `client/brisken/p1-item-76`; no edits made.
2. Live API: precondition met, confirm burden 13 rows, literal rule qualifies 6, one at vendor_pct 46. Build stopped to surface it.

### Planning handoff and record
1. Owner gave a new direction (month page by overview class); wrote a self-contained planning prompt for a fresh session.
2. PR #891 on `client/brisken/p1-prompts-verified-item76-measured`: PROMPT-STATUS evidence, items 70 and 71 closed, item 76 measurement and rulings, new items 78 and 79, stale p1 status rows for 70 and 71 corrected.

---

## Key Decisions Made

### Auto-confirm working rule for item 76
- **Choice:** the owner's literal rule (chosen candidate exact, `requires_review` false, single candidate, `review.state` ready) plus vendor agreement. Threshold not yet set.
- **Rationale:** July's WEB*NETWORKSOLUTIONS 7.98 qualifies literally at vendor_pct 46, which is item 76's own mechanism-1 bug (EXACT never consults the vendor). Cost: July clears 2 of 3 blocked rows instead of 3.

### The labelling half of item 76 ships regardless
- **Choice:** separate "nothing to do" from "your turn" without waiting on the auto-confirm threshold.
- **Rationale:** `rows[].status` is `pending` on all 223 live rows while only 13 are the reviewer's turn; this changes no sign-off.

### Reversible write on tax label, not category
- **Choice:** stopped before a category write; tested persistence on an empty tax label.
- **Rationale:** the category dropdown has no blank option, so the approved "set and revert" was not reversible there; tax label is in the matcher's never-re-match list and round-trips to empty exactly.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` | Edit (PR #891) | 2026-09-16 re-audit, month-edits and card-chips rows moved to Applied with evidence, Not-applied empty |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit (PR #891) | Items 70, 71 closed; item 76 rulings and measurement; new items 78, 79 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit (PR #891) | Stale status rows for items 70 and 71 corrected to LIVE |

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ?.

Backend Fly v132; SPA carries both prompts; PROMPT-STATUS has nothing pending. Live months: July 31 reconciled / 7 review / 73 unmatched / 1 refund, 3 undecided; August 8 / 2 / 100 / 1, 10 undecided. PR #891 open at checkpoint time. Worktrees: `agentic-ops1-item76` (clean, unpushed, no commits), `agentic-ops1-p1record` (#891), `agentic-ops1-ckpt916b` (this docs PR).

---

## Next Steps

1. Run the item-79 planning prompt in a fresh session. First decision: does the restructure ship before or after the 73-77 wave.
2. Item 76 labelling half; then set the vendor threshold against the six measured rows and build auto-confirm.
3. Item 78: check whether the field PUT already accepts an empty category; if so it is one Lovable line.
4. Ask Dirk for the card 1176 and 9693 statements (August holds 4 and 2 receipts with no charges).
5. Owner names the first cost centers; the feature does nothing until then.
6. Remove `agentic-ops1-p1record` and `agentic-ops1-ckpt916b` once their PRs merge; keep or remove `agentic-ops1-item76` after the item-79 plan.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 76, 78, 79
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (2026-09-16 rows)

### Open Questions
- Vendor threshold for auto-confirm: ELEVENLABS.IO sits at 75, so 75 versus 80 decides whether July clears 2 or 1 of 3.
- Does the item-79 restructure precede or follow 73-77?

### Working Notes
- Browser probes that lied, both caught by a second instrument: Radix dialogs render in a fixed-position portal, so `offsetParent` is null and filtering on it reports "no dialog" while one is open (detect via `[role=dialog]` and the network log). The workbench persists filters per run in localStorage `brisken.workbench.filters.v2:{runId}` and overrides a `?bucket=` URL param, so counts taken after navigating read the restored filter.
- Operator bearer token in the SPA is localStorage `erc-token`; API base `https://api.expenses.brisken.com`. `/api/feedback*` paths 404; Criss's notes live on the volume (`/feedback.jsonl`).
- `review.state` is a CATEGORY verdict (`_matched_category_review`), not a match verdict; `ready_confirm_pairs` intersects it with pending auto-picks. `n_undecided` excludes posted rows, which is why July shows 3 while 38 rows are pending in reconciled or review.
- The Playwright MCP browser is shared with the owner's own tabs; open a new tab rather than navigating the current one.

### Reference Materials
- Month-page planning prompt: in the 2026-09-16 conversation (not saved to `docs/` by design until the walkthrough is approved).
- Live months: July run `50622baec444`, August run `074a7b8905d7`.

---

## How to Continue

Merge #891 if CI has not already. For item 79, paste the planning prompt into a fresh session. For item 76, start from the measurement block in the backlog, not from the original spec bullets.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring before building on item 76 caught that a just-given owner ruling would bless a vendor-46 pair; the build stopped at zero lines written.
- Checking the cost-centers suspicion before voicing it turned a wrong assumption into a real finding (feature live, registry empty).

### Suggestions
- Put no unmeasured claim into an AskUserQuestion option. The auto-confirm options promised "clears most of the 13" and "round B proved this class zero-wrong"; measured afterwards, 6 of 13 qualify and one is wrong on vendor. An owner rules on the option text.

### System Health
- Heredoc triple-quote and cd-guard both fired again; the guards hold every time but the reflex recurs across sessions.
- Autonomy: 1 human intervention (the owner had to ask for next actions after the verification report).
