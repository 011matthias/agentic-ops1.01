# Checkpoint: Expense-Recon Notes 43-46 Planned

**Date:** 2026-09-16
**Status:** Planned and recorded (backlog items 80-82 plus amendments to 23/74/76/77/79); implementation prompts handed; nothing built

---

## Summary

Reviewer notes #43-46 were re-verified live, researched (#44 against 141 human-labelled pairs and card-network primary sources), ruled on by the owner in three decisions, and written into the backlog through PRs #896 and #897. Four self-contained implementation prompts (items 80, 81, 74, 82) were handed in the conversation.

---

## What Was Done This Session

### Re-verification of the planning brief
1. Held: all four notes verbatim (46 in the store); the FX block values; Settings rates; the #44 pair; SPA-derived "date mismatch" (`getRowWarnings`, `date_pct` < 99); resolved duplicate groups beside open ones; no time-of-day extraction field.
2. Did not hold: the FX `zoho_rate` / `zoho_converted` / `converted_gap(_pct)` names are not in item 23's ordered plan, and they need renaming rather than deleting (expense-report PDF receipts still fill them). Card networks lock the FX rate at authorization, not the processing date. The chip sits on 6 July rows, not 7.
3. Settled: Settings holds ONE rate per pair, frozen into each run's config by `apply_master_data` (`setdefault`); July and August both use EUR:USD 1.162275, which equals the ECB daily rate of 2026-09-04..10. "Monthly" is wording only; the 2026-07-23 self-derived rates have no inputs today.

### Research
1. #44 internal: charge Transaction Date minus receipt date over 141 confirmed pairs on eight statement months: 0 days 124, within one day 136, outliers +5/+6 (MEGA CENTE), +14 (Namecheap), -3 x2 (one likely a wrong label). Post Date trails Transaction Date by 1 day, 2 over weekends.
2. #44 external (research subagent): Visa Core Rules, Mastercard TPR, Chase, Amazon, Stripe, Fed holidays; quotes and URLs are in backlog item 80.
3. #43: at ECB July monthly average, July's 17 FX pairs deviate 0.50% on average against 1.79% at the Settings rate.
4. #45: 16 receipt duplicate groups on the live months, 15 copies plus the Google pair. Item 74(b) as written would split two true Stripe copies. A PDF text-layer probe showed Stripe receipts print their invoice number, which let an evidence ladder reach the labelled verdict on 16 of 16.

### Owner rulings (AskUserQuestion)
1. Date zones: silent -1..+1; note +2..+7 and -3..-2; mismatch beyond.
2. Time of day plus invoice/receipt numbers bundled into item 77's prompt change.
3. FX rate per month from the ECB, operator-typed rate wins (item 82).

### Recorded and handed
1. PR #896 (merged `26c99dfe`): items 80, 81, 82; amendments to 23, 74, 76, 77, 79; wave paragraph.
2. PR #897 (merged `d8b66307`): corrected the 15-group miscount to 16 and added the expected ladder rung per group id.
3. Four pasteable prompts in the conversation: items 80 and 81 now (parallel), item 74 gated on 73 shipped, item 82 gated on 77 shipped.

---

## Key Decisions Made

### Items 80 and 81 do not wait for item 76 to merge
- **Choice:** paste both now in two chats; they touch different functions than 76 and 79.
- **Rationale:** the owner's ordering ruling covers 73-77 only; the backlog's "after 76" was a placement, not a ruling.

### EXACT's date window stays one day
- **Choice:** the matcher half of #44 closed with evidence (item 76 note); only the label changes.
- **Rationale:** 5 of 141 labelled pairs fall outside one day, `PROBABLE` already reaches five days, and EXACT ignores the vendor.

### Item 82 reads "operator rate wins" as per month
- **Choice:** a typed rate wins for the month it is typed for; today's unkeyed Settings value becomes the fallback when the ECB is unreachable.
- **Rationale:** read literally, the one September value would override every month and item 82 would change nothing. Flagged to the owner; not yet confirmed.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit (PR #896, #897) | Items 80-82, amendments to 23/74/76/77/79, group-count correction and answer key |
| `C:\Users\neuma_p1qrsic\.claude\plans\nested-orbiting-tome.md` | create (local) | The approved plan, walkthrough plus technical appendix |
| `docs/2026-09-16 - Expense-Recon Notes 43-46 Planned/Checkpoint.md` | create | This checkpoint |

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ? (a Fly-hosted FastAPI app, no metered orchestrator to assess). No code, deploy or live write this session. Siblings at last read: item 76 in `agentic-ops1-item76` (no commits), item 79 in `agentic-ops1-monthviews` on `client/brisken/p1-month-views` (just started). The 74(c) Google group reset is still pending. `p2-product-decks.md` (55d) and `p2-targeting.md` (56d) are stale; that belongs to a p2 session.

---

## Next Steps

1. Paste the item-80 and item-81 prompts into two fresh chats.
2. Owner confirms the item-82 override reading before that prompt runs.
3. Item 74's prompt after item 73 ships; item 82's after item 77 ships.
4. 74(c): reset July group `03ba84fadeebe2a5` to ignore, per-action yes.
5. Check the printed documents behind ER-00183 `MSFT * E0100U9JTB 4.26` vs Hotel Ibis Lisboa 4.00 EUR (labelled confirmed, -3 days, different merchant); a wrong label skews the S1 scorer.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 74 (both 2026-09-16 amendments), 80, 81, 82
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- Does the owner accept the per-month reading of "operator rate wins" (item 82)?
- Do the 80/81 Lovable prompts ship alone or ride with 76's labelling prompt or 79's month-page prompt?
- Note #46 came from the owner's IPv6 /64 under the shared code in Portuguese: Criss or the owner? The design does not depend on it.

### Working Notes
- Label join for lag analysis: ER bundles key labels as `ER-xxxxx#NNN` while `receipts.csv` uses `#NNN-sNN` indices that restart, so take receipt dates from `labels-proposed.csv`. Statement ids = `transaction_content_id(account_id from run.json, card None, USD, Amount as printed, Description)`; ER-00216 needs the `Card` column as `card_last4`. Live months: join payload rows, parse the xlsx with `guess_column_map` for Post Date.
- ECB CSV: `https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?startPeriod=2026-06&format=csvdata`. USD per EUR: June 1.1518, July 1.14175, August 1.15931. BRL per EUR: July 5.84490, August 5.96841.
- Receipt PDF text without writing a file: `GET /api/runs/{id}/receipts/{doc}/image` into pypdf via `MSYS_NO_PATHCONV=1 uv run --no-sync --directory C:/.../expense-reconciliation python -c ...`. With `MSYS_NO_PATHCONV=1`, `/c/...` paths break; use `C:/...`. `rendered-body.pdf` files have no text layer.
- SPA at `c9f30bf`: `getRowWarnings` ~566, `FxSummary` ~1957, `FxPanel` ~2001, duplicates panel ~2508-2590 (pairs groups to legacy lists by index). Shallow-clone per session; no local checkout exists.
- Candidate emission in `web/service.py`: `date_pct` at ~2809 (normal) and ~2853 (held/manual, None); `_fx_breakdown` called at ~2824 and ~2860.

### Reference Materials
- Plan: `C:\Users\neuma_p1qrsic\.claude\plans\nested-orbiting-tome.md`
- PRs #896, #897; live runs July `50622baec444`, August `074a7b8905d7`

---

## How to Continue

Take the prompts from the 2026-09-16 conversation (items 80 and 81 first). If the conversation is gone, backlog items 80-82 plus the protocol carry everything the prompts restated; the gates are item 73 shipped before 74 and item 77 shipped before 82.

---

## Strategic Feedback

### What Worked Well This Session
- Using the human labels as ground truth turned "research the green zone" into measured numbers (141 pairs) instead of a literature summary, and showed the owner's lag lives in Post Date.
- One read-only PDF text probe refuted part of item 74's written spec before anyone built it.

### Suggestions
- Any count written into the backlog or an AskUserQuestion option should be a printed `len()` from the query in the same command, not a tally of printed rows. The 2026-09-16 prompts-verified checkpoint made the same suggestion about option text, and it recurred here (15 vs 16 groups, 7 vs 6 rows).

### System Health
- Autonomy: 2 human interventions (plan-mode approval; the three rulings were requested by the brief). The cd-guard and heredoc triple-quote guards fired again and held.
- A research subagent navigated the shared Playwright tab; subagent prompts do not inherit the working notes that warn about it.
