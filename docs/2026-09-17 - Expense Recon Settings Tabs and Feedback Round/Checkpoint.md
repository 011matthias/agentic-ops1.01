# Checkpoint: Expense Recon Settings Tabs and Feedback Round

**Date:** 2026-09-17
**Status:** Settings tabs live and applied; feedback notes #54-#60 + item 78 backend live; the matching SPA prompt published by the owner but not yet verified; five feedback notes still open

---

## Summary

Brisken expense-recon (p1): regrouped Settings into seven tabs, then worked the owner's and Criss's 2026-09-17 feedback notes. Three backend PRs shipped and deployed (#969, #979, #982), two Lovable prompts written, the first applied and verified, the second published but unverified.

---

## What Was Done This Session

### Settings tabs (item 91)
1. `PUT /api/settings` refuses an unknown top-level key (400 naming it, writes nothing) and answers `applied[]` / `ignored[]`; derived GET keys stay accepted-and-ignored (`store.SETTINGS_WRITABLE_KEYS` / `SETTINGS_DERIVED_KEYS`). PR #969, deployed, live probe `{"cost_centres": ...}` -> 400.
2. `docs/lovable-settings-tabs-prompt.md`: seven tabs, URL `?tab=`, panels force-mounted, per-slice reset, counts + two attention markers (`seen_undefined`, `merchants_inert`). Owner published; bundle crawl + cold Chrome drive confirmed (PR #972 recorded it Applied).

### Feedback notes #54-#60 + item 78 (PRs #979, #982)
1. Note #60: a masked two-digit ending (`XXXXXX38`, `**38`, `ending in 38`) names the card when exactly one active card ends in it; shared endings stay ambiguous. New row field `card_ending`; the strip no longer shows a masked BIN as the card number. Taught exact strings and printed last-4s outrank it.
2. Note #54 / audit 108: `add_receipts_to_expense_batch` runs `_refresh_batch_master_data_locked` before ingest (audit operator `auto: receipt arrival`), so arrivals and the month's existing rows read today's card list.
3. Item 78: clearing a category already worked on `""`/`null`; pinned route-level.
4. `docs/lovable-feedback-0917-prompt.md`: export switch removed (#58), Legal entities help lines (#59), Merchants guidance (#55), Mark as reimbursement on any row (#57), Undo my category (78), `card_ending` note (#60), Statement loaded lines on Matching (#56).
5. Full suite 2046 passed; regress checks bit on every fix (ending tier 7 red, arrival refresh 2 red, sticky category 2 red by hand). Deployed; September's Expenses page driven cold in Chrome and rendered.

### Handoff
1. Feedback coverage census over all 63 notes; handoff prompt for the open ones handed in chat.

---

## Key Decisions Made

### One settings group per request is the contract, and the backend says what landed
- **Choice:** `applied[]` + unknown-key 400 instead of a server-side tab manifest.
- **Rationale:** every tab count and marker was derivable from the two payloads the page already fetched; the missing truth was whether a save wrote anything.

### Two card digits are evidence only when unique
- **Choice:** resolve on a unique ending, contest on a shared one, never below a taught string or a last-4.
- **Rationale:** on the live registry `76` (3876/1176) and `13` (0113/6013) each span two companies, so a guess would move money between entities.

### Arrivals refresh the month's card copy; a Settings save alone still does not
- **Choice:** refresh inside the arrival's lock, through the audited refresh pass.
- **Rationale:** #54 asked for arrivals to get the month's full process; auto-refreshing every open month on any Settings save is a wider policy change left to the owner.

### Items 72 and 90 not started
- **Choice:** stop at the shipped work.
- **Rationale:** both change matching decisions and need a labelled-bundle replay under the scorer guard; the session was past 500k context.

---

## What Did NOT Work (and why)

- **Exposing `export_approved_only` as a Settings switch:** the label said "Zoho" on an app the owner is making Zoho-free (item 23); owner note #58 within the hour; removal is in the feedback prompt.
- **Claiming June's Supermercado Fenix row as the live #60 instance:** `"XXXXXX38" in hint` matched `XXXXXXXXXXXX3876`. The only live two-digit receipt is August's SARL TRAIN'S, already hand-fixed, so no live row moved. Corrected in PR #982 and the #979 body.
- **Playwright MCP for the consumer drive:** bound to the user's Edge on :9222, `initializeServer` timed out at 30 s.
- **agent-browser default browser:** `open` never returned; the page loads but the command blocks. Chrome via `--executable-path` worked, reading state in the foreground.
- **`tools/regress_check.py` on the category mutation:** printed "RED (no pytest summary line)"; reproduced by hand (2 real failures) before counting it.
- **A `note #N` regex for feedback coverage:** missed `notes 1/6/9/11` and `Notes answered: #55`; the loosened version false-cited #52, #53, #62. Open notes were confirmed by anchor instead.
- **Backlog item number 90 for the settings work:** already taken (ECB band); renumbered to 91 before commit. PR #974 claims 92-131.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/store.py` | edit | writable/derived settings key tuples |
| `.../src/expense_recon/web/app.py` | edit | unknown-key 400, `applied`/`ignored` |
| `.../src/expense_recon/cards.py` | edit | `masked_short_ending`, `cards_ending_in`, ending tier, BIN-free `hint_digit_run` |
| `.../src/expense_recon/web/service.py` | edit | `card_ending` on rows; arrival refresh |
| `.../tests/test_settings_put_contract.py` | new | settings PUT contract |
| `.../tests/test_card_short_ending.py` | new | #60 unit + route |
| `.../tests/test_arrival_reads_live_cards.py` | new | #54 route + audit trail |
| `.../tests/test_category_clear.py` | new | item 78 |
| `.../docs/lovable-settings-tabs-prompt.md`, `lovable-feedback-0917-prompt.md` | new | SPA prompts |
| `.../docs/api-contract.md`, `PROMPT-STATUS.md` | edit | four contract sections, status rows |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 91 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | two element rows |

---

## Current Status

- Live: Fly app at commit 43fedef2 (PRs #969, #979, #982). Settings tabs SPA applied and verified. Feedback-0917 SPA published, not verified (PROMPT-STATUS row still Not applied).
- brisken ops: platform unknown plan, not assessed (`infrastructure.yaml` has no platform section for p1; FastAPI on Fly).
- June 2026: 3 rows print a defined card number (3645, 3876) with no card; September 5 more. September self-heals on its next arrival; June needs refresh-master-data (owner/Criss action).
- Open feedback: #52, #53, #62, #63; #61 parked on item 23; #28/#29 probably superseded, unverified.

---

## Next Steps

1. Verify `lovable-feedback-0917-prompt.md` on the published bundle (route chunks included) and cold in Chrome; move its PROMPT-STATUS row to Applied.
2. Notes #62 and #63 (Criss, August Expenses): read her two rows live, fix, SPA prompt.
3. Notes #52 and #53: viewable set-aside pages; drop page says where receipts went and whether a re-match ran (audit 103, 127).
4. Ask the owner about June's refresh and item 23 (GL codes at all), which unparks #61.
5. Items 72 and 90 in their own sessions, with the labelled-bundle replay.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-feedback-0917-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last four sections)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 23, 72, 78, 90, 91 and 92-131 (PR #974)

### Open Questions
- Refresh June's card copy now (live write on a Criss month)?
- Does Brisken still want GL account codes on expenses (item 23)? Decides #61.
- Should a Settings card save auto-refresh every open month, not only on arrival (audit 108's wider proposal)?

### Working Notes
- Feedback notes carry `selector`, `anchor`, `pos`; #62 anchor "0.00 Tax label", #63 anchor "Software & Subscriptions AI", both on `/expenses/074a7b8905d7`.
- Live registry 2026-09-17: nine cards, one number each; shared two-digit endings 76 (3876 Corp / 1176 Consulting) and 13 (0113 Corp / 6013 Cloud).
- Brisken GmbH and Brisken Holding share org id 696750461 in Settings; unconfirmed whether intended.
- `default_paid_through` is copied verbatim into the Zoho export's Paid Through column; the live values are comma lists of card endings.
- The expenses route chunk renders no disposition controls; Mark as reimbursement lives only on suggested-private rows today.

### Reference Materials
- PRs #969, #972, #979, #982; open sibling PR #974 (voids audit, items 92-131)
- `https://expenses.brisken.com`, `https://api.expenses.brisken.com/feedback.jsonl`

---

## How to Continue

Paste the handoff prompt from this session's last reply into a fresh chat; it carries the rules, step 0 (verify the published prompt) and the open notes. Work in a `git worktree` off `origin/main`; siblings share the primary checkout.

---

## Strategic Feedback

### What Worked Well This Session
- Enumerating the live payload before designing (48 distinct payment hints, the live card registry) turned "strategize two-digit endings" into a rule with a measured ambiguity set instead of a guess.
- Reading the published settings chunk's save construction before writing the tabs prompt found the whole-map spread already in place and pinned it as a must-keep.

### Suggestions
- Build `tools/recon-feedback-coverage.py`: pull `/feedback.jsonl`, and require every note to map to a backlog item or an explicit "answered/superseded" entry keyed by note number. Two ad-hoc regexes each lied this session; a ledger keyed by note number would not.

### System Health
- Autonomy: 4 human interventions (elevated: run /system-dev to close gaps). Two were misses a gate should have caught (the feedback enumeration and the Zoho switch), one was the browser fallback, one an interrupted verification.
