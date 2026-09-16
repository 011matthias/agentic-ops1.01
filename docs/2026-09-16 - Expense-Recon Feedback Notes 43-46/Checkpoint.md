# Checkpoint: Expense-Recon Feedback Notes 43-46

**Date:** 2026-09-16
**Status:** Planning prompt handed to the owner; nothing built, notes not yet in the backlog

---

## Summary

Read the expense-recon app's live feedback store and found four notes that nobody had read yet (#43-46, all left 2026-09-16 on the July run). Checked each against the live July/August payloads and handed the owner a self-contained planning prompt that fits them into the 73-79 wave.

---

## What Was Done This Session

### Feedback read (live API, read-only)
1. `GET /feedback.jsonl` now holds 46 notes; the 2026-09-15 read had 42. None of #43-46 appears in `p1-improvement-backlog.md` on origin/main (it ends at items 78 and 79).
2. #43 (Matthias): show the receipt converted to USD at our FX rate. #44 (Matthias): research the typical posting lag ("green zone") behind the "date mismatch" chip. #45 (Matthias): the tool decides duplicates; receipts compare on date, time, amount, vendor and content. #46 (shared code, Portuguese, probably Criss): resolved items should leave the to-do area.

### Live facts established per note
1. **#43:** the candidate's `fx` block carries `implied_rate` 1.143002 while `zoho_rate` / `zoho_converted` / `converted_gap` are empty, because `_fx_block` (web/service.py ~2125-2180) fills them from `receipt.base_amount`, the Zoho-booked rate. The tool's own rate is `/api/settings` `fx_reference_rates` (EUR:USD 1.162275, BRL:USD 0.192448) and appears only in the reason string. At that rate: 276.08 EUR = 320.88 USD vs 315.56 charged, -5.32 (-1.66%).
2. **#44:** the chip sits on a pair the matcher calls `exact` (receipt 07-13, charge 07-14, `date_pct` 80). "date mismatch" is not a backend string, so the SPA derives it. Charge-minus-receipt lag on every reconciled pair: July 25x0d + 6x1d, August 8x0d.
3. **#45:** fits the 2026-09-15 item-74 ruling (charge-side detection deleted); a grep found no time-of-day extraction field.
4. **#46:** July still lists resolved groups beside open ones: charge `4bc95012abf2bfb5` (ignore), receipts `3b0029eea1b11643` and `03ba84fadeebe2a5` (confirmed). The Google group reset from item 74(c) has still not happened.

### Handed over
1. A pasteable planning prompt (in the conversation, not a file): re-verify, research #44 from primary sources plus all batches and the human labels, plan per note with proofs, place against rulings 73-77/79 without re-asking them, append to the backlog via a docs PR, plain-language walkthrough first.

---

## Key Decisions Made

### Plan only, no backlog edit this session
- **Choice:** The planning session records #43-46 (amending 74/76 or taking new numbers); this session did not append stubs.
- **Rationale:** A sibling is building item 76, and a stub the planner then has to fold would duplicate the item it amends. The usability memory now records the count and the four topics so the notes cannot go unread again.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| memory `project_brisken_expense_recon_usability_loop.md` | edit | 46-note count; #43-46 not yet in backlog; diff the count before trusting "no new feedback" |
| memory `project_local_password_vault.md` | edit | Probe the envelope by key; never `head`/`cat` the vault |
| `docs/2026-09-16 - Expense-Recon Feedback Notes 43-46/Checkpoint.md` | create | This checkpoint |

---

## Current Status

Brisken p1 is live on Fly (FastAPI + Lovable SPA). Ops line from pre-flight: "platform: unknown plan, ~?/? ops/mo. Last assessed: ?", which does not apply here: this is a Fly-hosted FastAPI app, so there is no metered orchestrator to assess. Notes #43-46 exist only in the feedback store, this checkpoint, and the handed prompt. In flight elsewhere: item 76 (worktree `agentic-ops1-item76`) and the item-79 planning prompt.

---

## Next Steps

1. Owner pastes the planning prompt into a fresh session, **adding the addendum under Working Notes** (two of its open questions were partly answered on 2026-07-23).
2. That session appends #43-46 to the backlog (docs PR) and brings the decisions it cannot settle to the owner.
3. The item-74(c) Google group reset (`POST /api/runs/50622baec444/duplicates/resolve`, `03ba84fadeebe2a5` -> ignore) is still pending: live write, per-action yes.
4. The p2 status files `p2-product-decks.md` (55 days old) and `p2-targeting.md` (56 days) are stale per pre-flight. That belongs to a p2 session; not touched from p1.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 23, 69, 73-79
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` row "Date+amount accuracy program"

### Open Questions
- Is `fx_reference_rates` one static rate per pair, or do the "self-derived monthly rates" from the 2026-07-23 program feed the reason string's "monthly reference rate"?
- Does the Chase parser take Transaction Date or Post Date?

### Working Notes
- **Addendum for the handed prompt:** the 2026-07-23 date+amount accuracy program (PRs #404-#406) recorded "time verified nonexistent in all sources" and built "self-derived monthly rates". So time of day cannot help charge-to-receipt matching; it can only help receipt-vs-receipt duplicate comparison (#45), and only where receipts print a time. The planner should start from that finding rather than re-verify from zero.
- Read path that works: `POST /api/login {"code": vault["Expense Recon App"]["operator_code"]}` then Bearer on `/feedback.jsonl` and `/api/runs/{id}`. Under Git Bash, `MSYS_NO_PATHCONV=1` also stops `/c/...` becoming `C:/...`, so `git -C /c/...` fails "not a git repository"; use `C:/...` paths with it.

### Reference Materials
- Live API `https://brisken-expense-recon.fly.dev` (July `50622baec444`, August `074a7b8905d7`)

---

## How to Continue

Paste the planning prompt plus the Working Notes addendum into a fresh session. Do not build from this checkpoint.

---

## Strategic Feedback

### What Worked Well This Session
- Checking each note against the live payload before writing the prompt turned three vague asks into located defects (empty `fx` fields with a known cause, a chip on an exact pair, resolved groups still listed), so the planner starts from evidence.

### Suggestions
- Before writing a planning prompt for a workstream, grep its status file for the terms in the ask ("time", "rate"). One grep would have put the 2026-07-23 finding into the prompt instead of into an addendum.

### System Health
- The feedback store is still read by hand. A `seen_feedback` baseline in `brisken-recon-notify.py` (the pattern `seen_rematches` already uses) would mail new notes as they land, which kills the two-month-unread failure structurally.
- Autonomy: 0 human interventions (fully autonomous session).
