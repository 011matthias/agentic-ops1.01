# Checkpoint: Brisken Recon Accuracy Score and Refused Re-run

**Date:** 2026-09-25
**Status:** Categorization score runs end to end from our own Zoho token; refused rows re-run on July to September; 38/120 vs Criss

---

## Summary
The item 216 accuracy test now runs in one command with a fresh Zoho Books pull (PR #1460), after an attempt to run it through the owner's Zoho agent (Verve) was dropped. On the owner's order the refused rows of July, August and September were re-run with item 219's decided OpenAI / Anthropic accounts, lifting agreement with Criss from 21/100 to 38/120.

---

## What Was Done This Session

### Scorer (PR #1460, merged `c8c7e6fe`)
1. Found `tools/recon-categorization-score.py` blind since #1451: it read only `posting_category`, so the model's answers (moved to `suggested_category`) read 0/0 on live data.
2. Now reads `posting_category`, else `suggested_category`, and carries `origin`; splits accuracy by origin (person / rule / suggestion) and by timing (Criss created or last changed the posting before / after 2026-09-24 23:17 UTC); lists charges booked in another company; `--pull-zoho` pulls her postings through the module's read-only `list_expenses` with `ZOHO_BOOKS_REFRESH_TOKEN`.
3. 29 tests (8 new), both wiring points regress-checked red; preflight OK; CI green.
4. Probe: Zoho's default expense list already applies `Status.All` (2,359 = 2,359 Corporate Services expenses, same ids).

### Live measurement and write
1. Fresh run (app `9d945667`, pull 15:29 UTC): 21/100; rules 11/12, model 10/88; all 100 postings independent of the tool; no other-company bookings; open rows 1/26.
2. Owner order "apply those changes to the months": split into `recategorize-refused` (refused rows only) vs a forced re-match (`statements/reread`, lands every pending re-match change); owner chose refused rows only via AskUserQuestion.
3. Read-only readiness check green (both entries `accounts_locked`, months GL, unpublished), then one job per month: lines answered July 46/101, August 6/46, September 10/67; charges 8/13, 3/6, 0/0; AI cost 0.016 USD.
4. Re-score: 38/120; rules 22/23 (all 11 new rule answers agree), model 16/97, no answer 34 -> 14. Status file entry via PR #1464 (`373b1356`).

### Verve (dropped)
1. Built a tool-side CSV and a one-shot, then a 12-slice prompt set; answered its setup questions; reviewed brief (3 unchanged returns) and plan (fixes landed on the 3rd pass; Zoho parameter names corrected from the docs: `filter_by=Status.All`, `AccountType.All`); a bundled turn aborted at its 5-tool-call cap. Owner: "this is not working".

### Housekeeping
1. Dirk draft `context/drafts/account-map-questions-to-dirk.md`: roll-up question removed (settled by owner ruling, shipped #1447); six questions remain.
2. Memories updated: categorization analysis (instrument + numbers), Verve (not a measurement path), no-live-writes (explicit-order exception and protocol).

---

## Key Decisions Made

### Measure with our own Books token
- **Choice:** the scorer pulls Criss's postings itself; Verve is not used.
- **Rationale:** our token already holds `expenses.READ`; Verve's document edits did not land and its turns abort at 5 tool calls.

### Refused rows only, no forced re-match (owner)
- **Choice:** `recategorize-refused` on the three months; the 20 receiptless OpenAI / Anthropic charges wait for each month's natural re-match.
- **Rationale:** a forced `statements/reread` rebuilds the charge set and lands every pending change (September's 12 duplicate switches, a model re-ask of every receiptless charge); the standing no-live-writes ruling holds for everything not named.

---

## What Did NOT Work (and why)
- **Running the test through Verve:** its brief came back word for word unchanged three times and the plan twice while it reported "updated"; a turn carrying three edits plus approval aborted with "Exceeded maximum tool call iterations (5)".
- **One-shot Verve prompt with a 304-row attachment:** too heavy for the agent's capacity (owner: "very fragile").
- **Scorer as it stood after #1451:** model 0/0 on live data, because the model's answer had moved to `suggested_category`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `tools/recon-categorization-score.py` | edited (#1460) | suggestion read, origin + timing split, other-company, `--pull-zoho` |
| `tools/tests/test_recon_categorization_score.py` | edited (#1460) | 8 new tests incl. caller-level |
| `tools/INDEX.md` | edited (#1460) | usage + fresh numbers |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edited (#1464) | refused re-run + 38/120 |
| `workspace/clients/brisken/context/drafts/account-map-questions-to-dirk.md` | edited (gitignored) | roll-up question dropped |
| Live months July / August / September | `recategorize-refused` | item 219 accounts on refused rows |

---

## Current Status
Score 38/120 against Criss's postings, every posting independent of the tool. 23 rows still carry a wrong model suggestion where a decided account exists: 20 receiptless charges (pick it up at the next natural re-match) and 3 receipts (neither path reaches them). Lovable, no-company and non-curated rows stay refused. brisken platform: unknown plan, ~?/? ops/mo, last assessed ? (no `platform` section; FastAPI on Fly).

---

## Next Steps
1. Owner: send Dirk the six questions (`workspace/clients/brisken/context/drafts/account-map-questions-to-dirk.md`); his answers unlock the 44-merchant history map (98/100 out of sample).
2. After Criss's next edit in each month, re-run the score; expected about 58/120 once the 20 receiptless charges take the decided accounts.
3. Upgrade `.claude/patterns/warn-stop-merge-left-pending.md` from `warn` to `block` (third recurrence).
4. Compact `MEMORY.md` below 140 lines (162 now; the index hook asked).

---

## Context for Next Session

### Files to Read First
- `tools/recon-categorization-score.py` (docstring + constants)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (top entry)

### Open Questions
- Does a natural re-match re-ask receipt lines that carry a model suggestion, or only receiptless charges? The 3 receipts suggest not.

### Working Notes
- Re-measure: `uv run tools/recon-categorization-score.py --fetch --pull-zoho --payload-dir .scratch/recon-score-<date> --batch 50622baec444 --batch 074a7b8905d7 --batch 51a22ad72864`.
- Of the 33 rows the decided accounts cover: 20 receiptless suggestions (July 11, August 2, September 7), 10 refused July Anthropic receipts (now answered, all agree), 3 receipts with a suggestion (July 1, September 2).
- Last natural re-matches: all three months 2026-09-25 01:25-01:51 UTC (`GET /api/operator/state` `rematches[]`).
- Criss's newest Corporate Services posting was created 2026-09-20; nothing she booked yet postdates the GL switch.

### Reference Materials
- Payloads + reports: `.scratch/recon-score-2026-09-25/` (before) and `.scratch/recon-score-2026-09-25-after/` (after), main clone.
- Zoho API list-expenses params: `filter_by` Status.*, `date_start` / `date_end`, no `expense_id` sort, no total count.

---

## How to Continue
`/resume brisken`; read the status entry; if Criss has edited a month since, re-run the score and compare with 38/120.

---

## Strategic Feedback

### What Worked Well This Session
- Probing before trusting: the Status.All differential and the rematch log read turned two assumptions into measured facts before either shaped a write.
- Splitting the invasive action into its narrow and broad paths let the owner pick the one with no side effects on Criss's pending work.

### Suggestions
- Flip `warn-stop-merge-left-pending` to `block`: a stop-event warn surfaces only after the turn has ended, which is why it recurred twice today.

### System Health
- A change that moves a field (#1451) broke the instrument measuring it the same day; tests on the scorer now pin the new field, but nothing ties module field moves to `tools/` consumers.
- Autonomy: 3 human interventions (break the prompt down, make it interactive, "this is not working").
