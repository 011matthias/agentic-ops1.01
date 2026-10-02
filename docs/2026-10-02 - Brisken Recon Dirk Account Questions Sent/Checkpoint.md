# Checkpoint: Brisken Recon Dirk Account Questions Sent

**Date:** 2026-10-02 (session ran 2026-09-25 to 2026-09-28)
**Status:** Dirk's card-account questions sent 2026-09-28; no answer as of 2026-10-02

---

## Summary
The owner asked whether Criss's past Zoho bookings are a sound way to set up the GL categorization, then had the three owner-gated AI vendors handed to a fresh session, the questions for Dirk narrowed by reading the actual booking sequences, and the result sent to Dirk. The one finding that outlives the session: the "split" vendors are mostly one-time switches or several products under one name, not random splits, and the account map's majority rule cannot see either.

---

## What Was Done This Session

### Strategy answer (past Zoho data)
1. Confirmed the account map already is that strategy: Criss's 2,234 card postings pulled through the read-only Books API, 98 of 100 agreeing out of sample. Showed the reach limit through the real categorizer: the uncontested write plan decides 26 of 164 guessed charges; the rest is gated vendors 52, never booked 33, resolver spelling 14, thin 14, split 13 (+5-6 Google).

### Owner-gated AI vendors
1. Wrote the continuation prompt for OpenAI / Anthropic / Lovable (the owner raised the 2026-09-18 gate). A sibling session built it as backlog item 219 (PR #1457, `accounts_locked`, Anthropic and OpenAI written live, Lovable and Consulting held for Dirk).

### Dirk's questions, read from the data
1. Reproduced the proof per row: the 13 split charges are Network Solutions 6, Microsoft 5, Mega 1, GoDaddy 1; the 5 receipts Rize 3, Amazon 1, Lidl 1; Google held 6 (3 Workspace, 3 Cloud).
2. Read every split vendor's booking sequence in `zoho-books-24mo.json` and backtested "the account since her last switch, at least 2 in a row" (learn before 2026-07-01, score Jul-Sep): 7 of 20 non-travel split bookings answered, 7 agreed (Microsoft 1, Network Solutions 4, OpenAI 2). Lovable 2 of 9 under that rule.
3. Found the product splits: Microsoft's 4.26/4.47 monthly item goes to IT Expenses since 2025-01, the 365 licences to Microsoft office; the 2026-04-20 annual renewal (140.71) went to Other Advertising, read as a slip. Lovable's receipt lines name the plan: Pro renews on the 5th (IT), Business on the 21st (mostly Marketing), Business paid on the Consulting card since August.
4. Caught two date errors in the draft against the records before handing it over (Microsoft "23 since July 2025" was 7 before + 16 since; OpenAI's run starts 2025-08-31, not September).

### Open-asks sweep and the send
1. Swept backlog, status, 09-24..09-27 checkpoints, staged drafts and live `/api/settings` for questions waiting on Dirk. Only cost centers were still open (registry `{}`); card gaps, statements (0113/6013/8311 `statement_expected: false`) and alert recipients are closed live; the Leonid and Dorta mails went in July; the hosting-org move sits with the licence proposal held to 10-01; the Lead Desk packet is p2.
2. Added cost centers, then removed them on the owner's order and sent: Graph send-by-id from matthias.silva to dirk.neumann only, pre-send check (no earlier copy, none of Dirk's 7 mails since 09-20 answers these), AskUserQuestion yes on the preview, verified in Sent Items 2026-09-28T08:42:02Z, one copy, isDraft false, the 3 unrelated drafts untouched. Logged verbatim in `context/comms-log.md`; draft file deleted (W1).

---

## Key Decisions Made

### What goes to Dirk
- **Choice:** vendors that switched account once follow Criss's current account and are sent as FYI; only product splits and policy calls are asked (6 questions).
- **Rationale:** each switch held every booking since (OpenAI 18 in a row, Network Solutions 15, Namecheap 7, Rize/Fireflies 4); the backtest agreed 7 of 7.

### Cost centers left out (owner, 2026-09-28)
- **Choice:** the email went without the cost-center question.
- **Rationale:** owner order; item 118's list stays un-asked until he raises it.

---

## What Did NOT Work (and why)
- **`derive_account_map.py` majority rule on split vendors:** it needs one account at 80% of all 24 months AND the last three postings; a one-time switch leaves the old account above 20% of history, so it abstained on every switched vendor that the trailing-run rule then got 7 of 7 right.
- **Trailing-run rule on Lovable:** 2 of 9 in July-September. The Pro and Business plans interleave on one card, so time does not separate them; the plan line on the receipt does.
- **Two triple-quoted Python heredocs:** blocked by the heredoc-size gate (correctly); rewritten via the Write tool.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/drafts/account-map-questions-to-dirk.md` | revised, then deleted after the send | the email (gitignored) |
| `workspace/clients/brisken/context/comms-log.md` | appended 2026-09-28 entry | sent message verbatim (gitignored) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | top paragraph | send + pattern finding |
| `docs/friction-register.md`, `docs/friction-register-archive.md` | 82 resolved rows archived | register size advisory |

---

## Current Status
Email with Dirk since 2026-09-28 08:42 UTC, unanswered on 2026-10-02 (his only mail since is an unrelated 09-30 "Thoughts on this..." on ChatGPT Ads). Waiting on his answers: Lovable and every Consulting cell (item 219), the Microsoft charges since July 2026, Google Workspace/Cloud (held in the write plan), AWS in Cloud Services, the never-booked tools. The 44-vendor uncontested write plan is still unexecuted. brisken ops: platform unknown plan; comms-log last entry 2026-09-28.

---

## Next Steps
1. When Dirk answers: fold the answers into `derive_account_map.py` (`HOLD_FOR_DIRK`, the split rows), rebuild the write plan from a fresh `GET /api/settings`, one owner-approved `PUT /api/settings`; Lovable keyed on the receipt plan line (Pro -> CorpServ IT Expenses, Business -> his answer, a 21st/22nd charge with no receipt read as Business).
2. Add the trailing-run class to `derive_account_map.py` ("account since her last switch, at least 2 in a row") and re-run its out-of-sample section; drop the bare `google` and `Microsoft` aliases from the Google Ads / Microsoft Ads merchants in the write plan before any write.
3. Owner call, open since 2026-09-25: write the 44 uncontested vendors now instead of after Dirk (none of his six questions touches them).
4. Cost centers (item 118): un-asked; raise with Dirk when the owner chooses.
5. p2 status files `p2-lovable-rebuild.md` and `p2-onepilot-site.md` are 22 days stale; refresh in the next p2 session.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/comms-log.md` (2026-09-28 entry: the questions as sent)
- `workspace/clients/brisken/context/expense-reconciliation/account-map-260925.md` and `derive_account_map.py`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (2026-09-28 paragraph)

### Open Questions
- Does the owner want the uncontested 44 vendors written before Dirk answers?

### Working Notes
- Backtest scaffold (session scratchpad, re-derive if lost): import `derive_account_map.py` by path, `build_clusters` + `classify` on `load_books()` rows split at 2026-07-01, score each test row against the train set's trailing run; run with the module venv (`uv run --extra dev --extra web` in an up-to-date module checkout).
- Graph send helper pattern: create -> validate (to == [dirk], no cc/bcc, subject, isDraft) -> `/send` by id -> verify the subject in Sent Items with isDraft false and gone from Drafts. The message id changes on send, so verify by subject + time, not by id.

### Reference Materials
- `docs/2026-09-25 - Brisken Recon Account Map/Mini-Checkpoint-1.md`
- `docs/2026-09-25 - Brisken Recon Categorization Analysis/Checkpoint.md`

---

## How to Continue
`/comd_resume brisken`, then check Matthias's inbox (Graph app-only) for Dirk's reply to "Expense tool: your calls on card accounts" before any account-map work.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the booking sequence per vendor instead of its share turned four "ask Dirk" items into FYI lines with a 7-of-7 backtest behind them, and made the two real questions (Lovable, Microsoft) product questions he can answer in a word.

### Suggestions
- Before routing any "split" to a human, print the vendor's dated sequence; a split that is a single switch point is settled by the data. Build it into `derive_account_map.py` as the trailing-run class (Next Step 2) so the next map does not need the user to ask.

### System Health
- Autonomy: 2 human interventions (one redirect, "is there no pattern"; one required send approval). The send path (pre-send check, AskUserQuestion, send-by-id, Sent Items verify) ran without a hook stop.
