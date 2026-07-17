# Checkpoint: Brisken Outreach Staging

**Date:** 2026-07-17
**Status:** All three owner-ordered actions executed + verified; outreach now waits on Dirk's sends

---

## Summary

Closed out the Sanofi call-day notification (sent to Dirk, live-verified deck facts), staged the Ashok referral follow-up as a note-brief in Dirk's Drafts, then reconciled the whole staged-outreach state: verified via a full post-Rome both-mailbox all-folders scan that none of the 29 draft recipients has been contacted post-Rome (except Ashok's known 07-13 touch and a surprise 07-09 jeff.londres reply to the CrowdStrike inquiry), flipped the 25 T3 draft-holder rows to `draft ready` on the master sheet (0 collateral), confirmed the status propagates into the Lead Desk board, and deduped the Georgiou draft pair.

---

## What Was Done This Session

### Sanofi call-day notification (sent)
1. Discovered the 2026_PPTX library reorg was executed 2026-07-16 16:52Z by another session (Client Collateral WIP gone; deck now in `Client Deliverables/Sanofi/`).
2. Downloaded the LIVE Sanofi pptx (444,496 B) and verified structure before claiming it in the mail: 11 slides, THE SHORT VERSION at slide 2, softened close at slide 11. This overruled the comms-critic's objection, which came from a stale repo mirror.
3. Sent the notification via Graph as matthias.silva -> dirk.neumann (202, Sent-Items verified 22:07Z): deck links (live webUrls), softened-close note, 11-slide note. No ask, per owner instruction. Planner slide-10 tick NOT done (send-only approval).

### Ashok/Accenture referral (staged)
4. Mailbox-verified history: only the 06-19 E1 invite + Dirk's 07-13 link-drop (no ask) ever went to Ashok; only inbound = stale auto-OOO; silent since his 13-July return; Planner task 50%, due date passed.
5. Loaded an owner-approved note-brief into Dirk's Drafts via Graph (To k.ashok@accenture.com, BCC Zoho dropbox, threaded subject) carrying the two open Planner asks: confirm the 40-45 central-bank scope, and customer-decision status.

### T3 / staged-outreach reconciliation
6. Answered "has Dirk sent the T3 batch?": NO — all 25 T3 drafts (loaded 07-13) still parked, 0/29 sends since load, 0 replies; sheet statuses were already correct.
7. Full classified dump of Dirk's Drafts (47 items, 30 campaign-relevant) delivered to owner; flagged the Forst draft's address mismatch vs the sheet email column.
8. Full POST-ROME check (cutoff 2026-06-27, both mailboxes, ALL folders via the /messages collection, 5,549 + 179 messages, folder-resolved hits, OOO-stripped): 27/29 clean; only Ashok (07-13, known) and Tejay Lokhande (07-09 "Your OnePilot inquiry" response sent by jeff.londres, filed in `CrowdStrike | Website | OnePilot`) have post-Rome outbound.
9. Flipped the 25 T3 draft-holder rows `Not contacted` -> `draft ready` (col AA): backup `PRE-T3FLIP-BACKUP-2026-07-17.xlsx` uploaded first, current values asserted, 25 surgical range PATCHes (delegated token), whole-sheet diff = exactly 25 intended changes, 0 collateral. The 4 draft-less T3 rows (Opanasyk, Wandhoefer, Graham, Hill) correctly stay `Not contacted`.
10. Verified Lead Desk carry-over in code (origin/main `migrate.py` stores `email outreach_status` verbatim; `suppression()` only reacts to "no consent"/"do not contact") and live: `POST /sync` 200 (337 contacts), board Sheet-status shows `draft ready` x25, spot-checked Matos + Altschachl. Engine untouched: ticks still `kill=True paused=True claimed=0`.
11. Deduped the Georgiou pair: deleted `RE: Last day at Booth #2 in Rome, Thursday` from Dirk's Drafts (204, recoverable); `T2 Market Data Hub, picking it back up` is the survivor.

### Records
12. comms-log.md: two new entries (Sanofi notification verbatim + Ashok brief load), `last_contact` -> 2026-07-17.
13. Memory: `project_brisken_ashok_accenture_referral.md` updated (07-17 state + parked brief) + MEMORY.md index line.

---

## Key Decisions Made

### Trust the live SharePoint file over repo mirrors and checkpoint claims
- **Choice:** Downloaded the live Sanofi pptx and read its slide order before putting a structural claim in a client-facing mail; rejected the critic finding based on the stale repo mirror.
- **Rationale:** B4; Dirk presents from the live file today. Repo deck mirrors go stale within a day.

### Check post-Rome state BEFORE flipping statuses
- **Choice:** Ran the full post-Rome scan first; only clean rows flipped.
- **Rationale:** A row with a real send needs `Contacted - awaiting reply`, not `draft ready`; the scan is what makes the flip truthful.

### Flip scope = the 25 draft-holders only
- **Choice:** T2 draft-holders (Georgiou, Kulkarni, Ashok) keep their existing statuses; draft-less T3 rows stay `Not contacted`.
- **Rationale:** `draft ready` describes staged-and-untouched; Georgiou's `Replied - action needed` carries more signal.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/comms-log.md | Modified | 2 entries (Sanofi send verbatim, Ashok brief load) + last_contact 2026-07-17 |
| memory/project_brisken_ashok_accenture_referral.md | Modified | 07-17 state: parked note-brief, Planner 50%, Dirk's 07-13 mail had no ask |
| memory/MEMORY.md | Modified | Ashok index line updated |
| SharePoint master sheet (external) | Modified | 25 x col AA `Not contacted` -> `draft ready`; backup PRE-T3FLIP-BACKUP-2026-07-17.xlsx uploaded |
| Dirk's mailbox (external) | Modified | +1 Ashok note-brief draft; -1 Georgiou duplicate draft; 1 real send (Sanofi notification, from matthias.silva) |
| brisken-lead-desk.fly.dev (external) | State | /sync triggered; board Sheet-status now shows draft ready x25; engine state unchanged |

Scratchpad scripts (ashok_scan, followup_scan, sanofi_slide_order, send_and_draft, postrome_check, t3_flip, dedupe_and_sync) are session-ephemeral, not repo files.

---

## Current Status

- **Sanofi:** call is TODAY 16:00 with Ian Haegemans; Dirk notified with correct links; deck live-verified in `Client Deliverables/Sanofi/`. Gated leftover: Planner slide-10 tick.
- **Staged outreach:** 25 T3 + Kulkarni + Georgiou (MDH) + Ashok briefs parked in Dirk's Drafts; sheet + board truthfully read `draft ready` for the 25; everything waits on Dirk writing/sending.
- **Lead Desk:** capture live and healthy; sender DORMANT (kill_switch=1, rome-2026 done, claimed=0 on every tick). Send-gate drill still unscheduled = the single blocker on the first Graph-path campaign.
- **Stale item found:** Tejay Lokhande NOTE in Dirk's Drafts is outdated — jeff.londres already answered his OnePilot inquiry on 07-09.

---

## Next Steps

1. **Watch Dirk's sends:** when T3/T2/Ashok mails go out, cloud capture ingests them into the Lead Desk automatically, but the SHEET statuses (`draft ready` -> `Contacted - awaiting reply` + `last_outreach`) still need the mailbox-to-sheet update pass; rerun the postrome_check pattern.
2. **After today's 16:00 Sanofi call:** log the outcome in comms-log; on owner go, tick the Planner slide-10 item (task VeH5a5bwf0Ky5jns-nt8bGUAMA-a).
3. **Tejay note:** remove or rewrite the stale NOTE draft (gated mailbox write); also worth clarifying with Dirk how a 07-09 send in jeff.londres's name happened (he left the company per the domain-farm records).
4. **Lead Desk send-gate drill:** still needs an owner-present ~30-min window; unchanged single blocker.
5. **Ashok:** when Dirk sends the brief-derived mail, track the scope-confirm + customer-decision answers; Planner ticks gated.

---

## Context for Next Session

### Files to Read First
- memory/project_brisken_lead_desk.md + memory/project_lead_desk_4d_graph_send.md (engine + drill gate)
- memory/project_brisken_ashok_accenture_referral.md (parked brief state)
- workspace/clients/brisken/context/comms-log.md (last 3 entries)

### Open Questions
- Who/what sent the 07-09 "Your OnePilot inquiry" reply as jeff.londres (he left the company)? Shared mailbox, delegate, or an automation?
- When does the owner want the watched send-gate drill? (Unchanged from 07-16.)

### Working Notes
- **Delegated Files token** `.scratch/graph_token.txt` was STILL VALID this session (minted ~07-16 21:46, /me 200) — test it before re-sniffing; the planner-tab sniff was not needed at all.
- **Master contacts layout:** 300 rows x 34 cols, usedRange starts A1, `email outreach_status` = col AA. Backup convention `PRE-{OP}-BACKUP-{date}.xlsx` in the TA Cook 2026 folder works via delegated PUT :/content.
- **Lead Desk web:** login = `POST /login` field `code` (matthias code in vault/ld_secrets); `/sync` is cookie-authed with `csrf` form field parsed from any rendered page; board "Sheet status" = `outreach_status` verbatim, display-only; `suppression()` only triggers on "no consent"/"do not contact" so new status strings are engine-inert.
- **Post-Rome scan recipe:** `/users/{mbx}/messages?$filter=sentDateTime ge {cut} and isDraft eq false` spans ALL folders (Dirk's custom filing covered); local-filter from=@brisken.com for outbound; OOO-strip replies; folder-resolve hits only. 56 pages for Dirk since 06-27.
- **Live Sanofi deck:** 11 slides, SHORT VERSION at slide 2, softened close at 11; webUrls recorded in comms-log entry. Repo mirror `call-collateral/brisken-treasurycentral-sanofi.pptx` in this working tree is STALE (pre-presenter-pass).
- **Reorg residue:** two Digital Co-Worker pptx still sit in the 2026_PPTX root (were co-authoring-locked during the 07-16 reorg; that session left a background retry).
- **cp1252 guard:** every scratch Graph script needs `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` or `PYTHONIOENCODING=utf-8` — the bare first run crashed on an emoji in a 2022 mail body.

### Reference Materials
- Sanofi deck folder: https://brisken.sharepoint.com/sites/MARKETING/Shared%20Documents/20_Assets/BRISKEN%20PRESENTATIONS/OnePilot%20-%20Cloud%20Solutions%20Presentations/2026_PPTX/Client%20Deliverables/Sanofi
- Lead Desk board: https://brisken-lead-desk.fly.dev

---

## How to Continue

`/resume brisken`. If Dirk has started sending the staged drafts, run the mailbox-to-sheet update pass (postrome_check pattern -> flip sent rows to `Contacted - awaiting reply` + `last_outreach`, backup + 0-collateral diff, then `POST /sync`). If the Sanofi call happened, log the outcome. The send-gate drill remains the highest-leverage Brisken ask.

---

## Strategic Feedback

### What Worked Well This Session
- Tight yes/no directives on gated actions ("Yes to send... and yes load...") let three invasive operations execute in one pass, each with its own readiness assert and outcome verify — zero rework.

### Suggestions
- The staged-outreach batch is now four days old and fully visible to Dirk; if it stays unsent through the weekend, a one-line nudge in the next notification mail ("the 25 follow-up drafts are ready in your Drafts") would cost nothing and might unstick it.

### System Health
- Repo mirrors of SharePoint decks mislead downstream consumers within a day (the comms-critic built a HIGH finding on a stale mirror this session). The mirrors' value is questionable now that SharePoint is the declared source of truth; consider either a freshness stamp in the mirror README or dropping mirror-based verification from the critic's toolkit in favor of live Graph reads.
- Autonomy score: 0 human interventions this session (2 hook-contained regressions + 1 hook-caught phrasing, all self-corrected).
