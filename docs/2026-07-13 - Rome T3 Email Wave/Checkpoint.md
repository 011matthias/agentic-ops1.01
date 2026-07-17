# Checkpoint: Rome T3 Email Wave

**Date:** 2026-07-13
**Status:** T3 pack drafted + critic-audited + roster approved-for-review; LOAD GATE CLOSED (14 of 16 T2 drafts still in Dirk's mailbox). Notify-Dirk email already sent 07-11. Portable prompt handed to user for the gated load in another session.

---

## Summary
Built the Rome Tier-3 cold-reconnect email wave (30 T3 contacts → 3 variants, 27 sendable / 2 held / 1 excluded), critic-audited it, and notified Dirk it is ready. The actual load into Dirk's Drafts is gated on his clearing the 16 Tier-2 drafts from 07-10; as of 07-13 he has cleared only 2, so nothing loaded.

---

## What Was Done This Session
### T3 wave build
1. Pulled the T3 task from Planner ("Rome Tier 3 booth/token-network: email outreach", id `NmYYXMHlfE6U`, 0% complete, no checklist). Its description still carries the stale ~90-contact/token-network/consent framing; followed the settled Tier-column authority + owner's no-consent-notice correction instead.
2. Extracted all 30 `Tier = T3` rows from the master sheet (counts matched settled context exactly: 30 T3, 29 attended + 1 no-show). Verified zero cross-tier address clashes (no T3 address appears on any H5/T1/T2/ANON/STOP/GA row).
3. Ran a read-only dual-mailbox dedupe scan (`.scratch/t3_dedupe_scan.py`): both Matthias + Dirk Sent Items since 2026-06-26 (SMTP-resolved recipients), both Drafts, both calendars. One raw hit ("malak" substring inside a Nestlé contact name) correctly identified as a false positive. No live thread with any T3 address.
4. Wrote the 3-variant pack: A/booth (verbatim T1 template), B/attended-no-booth (only the opener changed), C/no-show (verbatim from post-event-sequences.md). Split source = `in_our_booth` (4 → A) + `no_show` (1 → C) + remainder (22 → B), named in the file after the critic flagged it.
5. agnt_comms-critic audit → 1 HIGH (variant-split source unnamed) → fixed. Everything else passed.

### Notify Dirk
6. Drafted, critic-audited (1 HIGH: readiness overstated → fixed by naming the 3 open owner calls), and SENT the "T3 ready" email from Matthias.Silva@brisken.com; verified in Sent Items 2026-07-11 20:08:38 UTC; logged verbatim to comms-log.md.

### T2 gate checks
7. Checked Dirk's Drafts on 07-11 (all 16 T2 present) and again on 07-13 (`.scratch/check_dirk_t2_drafts.py`): 14 of 16 still present. Holcim Vergel + Partners Group Jellonek are gone (sent/cleared); none of the 16 appears in Sent since 07-09.
8. Handed the user a self-contained portable prompt to run the gated load (re-check T2 → if clear, load T3 + draft notify) in another session.

---

## Key Decisions Made
### Three copy variants, not one
- **Choice:** A/booth verbatim, B/attended-no-booth (new opener only), C/no-show verbatim.
- **Rationale:** only 4 of 30 T3 visited the booth; the T1 "thanks for coming by our booth" opener is factually false for the other 26. Variant B claims only what the sheet supports (both attended, did not talk).

### Load stays gated on T2 clearing
- **Choice:** Do not load T3 until Dirk's Drafts are clear of the T2 wave; hold Opanasyk + Stuart Graham pending his yes/no; surface the Boclinca cc question.
- **Rationale:** keeps the waves visually separate in his Drafts, and the two flagged contacts have real downside (personal Gmail; live Shell/Askew thread).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/drafts/rome-t3-cold-reconnect.md | Created | The T3 deliverable: 3 variants + full send roster + exclusions + pre-load checklist |
| workspace/clients/brisken/context/comms-log.md | Modified | Appended the 07-11 sent notify email verbatim; bumped last_contact to 2026-07-11 |
| .scratch/t3_dedupe_scan.py | Created | Read-only dual-mailbox dedupe scan (Sent/Drafts/Calendar, SMTP-resolved) |
| .scratch/send_t3_notify.py | Created | Sent the notify email from Matthias, duplicate-guarded + readback |
| .scratch/check_dirk_t2_drafts.py | Created | Read-only enumeration of Dirk's Drafts + Sent, classifies each against the T2 wave |

---

## Current Status
- **T3 pack:** written, critic-clean, roster approved-for-review. Nothing loaded to Outlook.
- **Notify email:** sent to Dirk 07-11, verified, logged.
- **Load gate:** CLOSED. 14 of 16 T2 drafts still sit in Dirk's Drafts (created 07-10 14:10-14:12 UTC). He has sent/cleared only Holcim Vergel + Partners Group Jellonek.
- **Platform (expense-recon p1):** unrelated to this session; tier unknown, build paused on §38 stack pick. Not touched.

---

## Next Steps
1. When Dirk's Drafts are clear of ALL 16 T2 drafts: load T3 as drafts into `\\dirk.neumann@brisken.com\Drafts` via `dirkDrafts.Items.Add` (never CreateItem+SendUsingAccount+Save), duplicate guard + readback, force SyncObjects + SendAndReceive, re-verify sync.
2. Get Dirk's yes/no on the 3 open calls: Opanasyk (personal Gmail), Stuart Graham (Shell/Askew live), Boclinca cc (rtsompani@bstdb.org on Timeshov's email?). Default: load the 25 clear ones, hold the 2 flagged.
3. After load: draft (do not auto-send) a notify email to Dirk for user review; log the load to comms-log.md.
4. Reconcile the T3 roster against Dirk's SharePoint DN-Edits master if he has edited it since 07-01 (the two "see comment" cells — Opanasyk, Ehlers — resolve only there).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/context/drafts/rome-t3-cold-reconnect.md (the deliverable + roster + pre-load checklist)
- workspace/clients/brisken/context/lead-generation/Rome-Event/post-event-sequences.md (tier segmentation, Variant C source, no-show routing)
- workspace/clients/brisken/context/comms-log.md (07-11 notify email verbatim; the outbound thread with Dirk)
- .scratch/check_dirk_t2_drafts.py (the gate check — re-run first, read-only)

### Open Questions
- Opanasyk: send to his personal Gmail (only address he left at the booth) or drop?
- Stuart Graham: include while the 27 Jul Askew Shell call is live? (precedent: Bunmi went into the T1 wave despite that thread)
- Boclinca: cc rtsompani@bstdb.org on Timeshov's email, or drop her? (her own row has no address; the alt belongs to a third person)

### Working Notes
- **The load requires the local Windows Outlook profile** with BOTH dirk.neumann + Matthias.Silva stores attached. A cloud/remote session cannot do it.
- **Count correction that reached Dirk:** the 07-11 notify email said "19 Tier 2 notes (6 prospect, 13 partner and SAP)." Accurate staged count is 16 (6 prospect + 10 partner/SAP). The gap is the 3 ICD-cluster drafts (Brueckner/Lasecki/Hamid) pulled from Dirk's Outlook on 07-11; the "13/19" came from the earlier restricted dedupe folder-count, not a per-item T2 classification. If Dirk counts his Rome drafts he finds 16, not 19. Nothing about the plan changes.
- **T2 attrition tracking:** 07-11 = 16 present; 07-13 = 14 present (Vergel Holcim + Jellonek Partners Group gone). This is the live gate signal — the load only fires at 0 remaining.
- **Variant A/C are verbatim** from approved/sent sources; do not reword them. Only Variant B's opener is new.

### Reference Materials
- Planner task id: `NmYYXMHlfE6UDj1aS8PcOmUANkgn` (Lead Generation bucket, plan `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`)
- Graph token: `.scratch/grabtoken.py` off CDP :9222 Edge planner tab → `.scratch/graph_token.txt`

---

## How to Continue
Re-run `.scratch/check_dirk_t2_drafts.py`. If any T2 draft remains, report and stop (gate closed). If zero remain, load the T3 pack (drafts only, dirkDrafts.Items.Add, hold the 2 flagged unless Dirk answered), then draft the notify email for review and log to comms-log.md. The portable prompt handed to the user this session carries all of this if they run it elsewhere.

---

## Strategic Feedback

### What Worked Well This Session
- The conditional gate ("check T2, load only if clear") kept an irreversible-ish mailbox write behind an objective, machine-checkable signal (drafts-remaining count) instead of a judgment call. Re-running one read-only script answers "load or not" definitively.

### Suggestions
- The T2 draft count is now the live gate. Rather than re-checking manually each session, this could become a tiny scheduled read (or a one-line status in /resume brisken) so the moment Dirk hits zero is visible without a prompt.

### System Health
- Data-accuracy on outbound owner-facing counts: the "19 vs 16" slip came from reusing a restricted folder-count as if it were a classified T2 count. The classifying enumeration (`check_dirk_t2_drafts.py`) existed one turn later and would have given 16. Lesson: an outbound count should trace to the per-item classification, not a folder Restrict total (B4).
- Autonomy score: 1 human intervention this session (self-detected count slip; no user work-quality corrections). The one user interrupt was a venue change ("do it in another chat"), not a correction.

---

## Friction Events
1. **verification-theater / B4** — the 07-11 notify email to Dirk carried "19 Tier 2 notes (6 prospect, 13 partner and SAP)"; accurate staged count is 16 (6 + 10). The count came from an earlier restricted dedupe folder-total, not a per-item T2 classification. Self-detected the next turn via full enumeration. Fix: documented (outbound counts trace to the classifying query, not a folder Restrict).
2. **agent-deferred / B1 (regression)** — stop-b1-gate caught a closing-offer/deferral in the T2-check turn ("When you next want me to check, I can re-run"). Hook-caught, self-reframed to a held-pending statement. Same most-logged class as the 07-12 entries; hook holds, generation reflex persists.
