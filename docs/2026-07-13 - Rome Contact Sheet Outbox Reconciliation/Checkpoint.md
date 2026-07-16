# Checkpoint: Rome Contact Sheet Outbox Reconciliation

**Date:** 2026-07-13
**Status:** Complete — reconciliation delivered, SharePoint comparison done, Dirk notified (corrected send)

---

## Summary
Reconciled the Rome post-event master contact sheet's outreach status against the actual Outlook Sent Items of both Matthias's and Dirk's mailboxes, compared the local canonical sheet to Dirk's live SharePoint version (different schema, 2 days newer), and notified Dirk of the one real discrepancy (an LSEG send logged on the sheet that isn't in either outbox).

---

## What Was Done This Session

### Outbox reconciliation (local canonical sheet)
1. Read the canonical `rome2026-post-event-master-contacts.xlsx` (event-admin, Jul 10): 290 rows, 24 flagged email-contacted.
2. Scanned both Sent Items via Outlook COM (Matthias 477, Dirk 2,477) for June–July; matched recipient SMTP against the sheet.
3. Result: **23/24 flagged leads trace to a real sent email.** The post-event campaign "Following up from the SAP conference in Rome" (Dirk, 07-08) = exactly 19 recipients, all 19 flagged, zero un-flagged. Clean 3-way match.
4. One exception: **Rohit Bali (Deloitte)** flagged "Contacted – awaiting reply" with NO email in either outbox (his touch was a SharePoint brochure note, not an email).
5. Pre-event blast context: E1 "Worth fifteen minutes at Booth #2" reached 243, E2 88, E3 86; only 34 survived into the current sheet, mostly marked "Not contacted" — the status column tracks post-event only.

### SharePoint comparison
6. Located Dirk's live copy via the authenticated Edge session (raw-CDP + SharePoint Search REST): `30_Events/TA Cook/TA Cook 2026/TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx`, modified **2026-07-12** (2 days newer than our local pull).
7. Downloaded it (71KB) and diffed: **different schema** — SharePoint uses `emails_sent` / `E1-E3_response` / `post_event_outreach`; ours uses `Tier` / `email outreach_status`. Shared base columns identical.
8. Three-way reconcile (SharePoint vs local vs outbox): the 19 booth follow-ups agree everywhere. SharePoint has `post_event_outreach` on 36 rows vs our 24; 14 are Dirk's notes/plans (personal-note queue, REMOVE flags, "send MDH") not sends. **Marco Favalli (LSEG)** marked "1st email sent 7/10" but no email to any @lseg.com address in either outbox all year. 5 contacts in SharePoint not in ours (Maersk + 4 Shell International, pre-event-blast recipients).

### Comms — notify Dirk
9. Drafted an LSEG-discrepancy notification in Dirk's notification style; ran agnt_comms-critic (5 fixes: hyperlink the sheet, core finding as a bullet, add sign-off, trim audit-method narration, quote the flag in full); applied all.
10. Sent from Matthias's mailbox with a folder-ownership readiness check; verified it landed in Sent Items.
11. First send over-included two padding bullets (Bonizzoni OOO, Hetesi/Jaszczak MDH) — Dirk's own notes, not the fact. User caught it. Sent a trimmed correction (Favalli only), threaded on the original, verified delivered.

---

## Key Decisions Made

### Reconcile against the outbox by recipient SMTP, both mailboxes
- **Choice:** Read Sent Items via Outlook COM, match `PR_SMTP` per recipient, classify by campaign subject.
- **Rationale:** The sheet's "contacted" claim is only trustworthy if it maps to a real send; the booth follow-up ("Following up from the SAP conference in Rome") is the definitive who-did-Dirk-email list.

### Treat the two sheets as separate documents, not stale copies
- **Choice:** Report the schema divergence rather than assuming SharePoint == local + edits.
- **Rationale:** SharePoint is Dirk's live tracker (E1-E3 + free-text notes); ours is the structured Tier partition the lead-desk migrate reads. They track the same reality differently; a naive diff would misread it.

### Notify Dirk of the Favalli discrepancy only; second (corrected) send
- **Choice:** After the user flagged over-inclusion, send a trimmed correction instead of leaving the padded one as the record.
- **Rationale:** The one thing that needs Dirk is the Favalli send he believes went out but isn't in Outlook; the other two LSEG lines are his own open notes.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/sp-master-contacts.xlsx` | Created (ephemeral) | Downloaded SharePoint copy for the diff; gitignored scratch |
| `~/.claude/.../memory/reference_user_edge_cdp_9222.md` | Modified | Added: when `tools/edge_cdp.py` is absent on a feature branch, skip `connect_over_cdp`, go straight to inline raw-CDP + `suppress_origin` |
| Matthias Outlook → Sent Items | Sent | 2 emails to Dirk (original + trimmed LSEG-discrepancy correction) |

No repo source files changed. Neither master sheet was edited (both are live/tracked; edits gated on user direction).

---

## Current Status
Reconciliation and SharePoint comparison complete and delivered. Dirk has the corrected LSEG notification (Sent 2026-07-13 22:33 UTC). Two open items are the user's/Dirk's to decide (below); nothing is mid-flight on the agent side.

---

## Next Steps
1. **Dirk to answer the Favalli question** — did the 7/10 LSEG email go out another way, or does it still need sending? (Neither Outlook has it.)
2. **Decide sheet-sync direction** — SharePoint is ahead (14 note entries + 5 dropped contacts + the Rohit Bali correction). Pull those into our canonical sheet, or keep the two intentionally separate. Merge is gated on this call (both files are live/tracked).
3. **Rohit Bali reclassify** — either send him a real email (makes "awaiting reply" true) or change his status to reflect the SharePoint-note channel.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx` — our canonical sheet
- `workspace/clients/brisken/TASK-NAMING-STANDARD.md` §3 — Rome tier canon (H5/T1/T2/T3); confirms T1 = the 19 emailed from Dirk's Outlook 07-08
- SharePoint: `.../30_Events/TA Cook/TA Cook 2026/TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx` (Dirk's live copy)

### Open Questions
- Marco Favalli / LSEG: did the "1st email sent 7/10" actually go out, and via what channel? Only Dirk knows.
- Should our canonical sheet absorb Dirk's post-07-10 personal-note queue and the 5 dropped rows, or stay a pure post-event tracker?

### Working Notes
- **Outbox access is Outlook COM** (`win32com`), both stores reachable: `Matthias.Silva@brisken.com` (477 sent) and `dirk.neumann@brisken.com` (2,477). Recipient SMTP via PropertyAccessor `0x39FE001E`.
- **Sheet vs sheet:** local canonical = Tier + `email outreach_status` (290 rows); SharePoint = `emails_sent`/`E1-E3_response`/`post_event_outreach` (295 rows). The 19 "Booth follow-up sent 2026-07-08" match across both + outbox.
- **The 36 SharePoint post_event_outreach entries:** 22 map to a real send (19 booth + Andriy 07-06 + Dan Staniford/Sebastian 07-01); 14 are notes/plans (Rohit Bali, Lars Richter, Michael Diet, Jean-Michele Szczecina, Kiosses Christos, Aniket Kulkarni, Marcus Reinsfelder, Laura Koekkoek; LSEG Bonizzoni/Hetesi/Jaszczak/Favalli; REMOVE: Stephan Meyerhoff, Jochen Stiebe).
- **CDP:** `connect_over_cdp` hung the full 2-min timeout on this Edge (149) build; the working path was inline raw-CDP websocket with `suppress_origin=True` driving `Runtime.evaluate` on the open SharePoint tab. `tools/edge_cdp.py` is NOT on this branch.
- The downloaded SharePoint copy is at `.scratch/sp-master-contacts.xlsx` if the diff needs re-running.

### Reference Materials
- Memory: `project_brisken_rome_tier_classification`, `project_brisken_rome_salesnav_list`, `reference_dirk_outlook_com_drafts`, `feedback_dirk_email_notification_style`, `reference_user_edge_cdp_9222`

---

## How to Continue
The analysis is done and Dirk is notified. To act on it, get the user's call on sheet-sync direction (next step 2) and Dirk's answer on Favalli, then the merge into `rome2026-post-event-master-contacts.xlsx` can proceed (with a backup first, since the lead-desk migrate reads it).

---

## Strategic Feedback

### What Worked Well This Session
- The three-way reconcile (sheet ↔ outbox ↔ SharePoint) surfaced a real, actionable gap (Favalli claimed-sent, not in Outlook) that neither sheet alone would show. Behavior-verified sends (folder-count checks after each email) rather than trusting "issued".

### Suggestions
- When a notification's job is "flag one discrepancy", the message should carry only that discrepancy. Two of the three LSEG bullets in the first send were Dirk's own notes — padding that diluted the ask and forced a correction email. Keep flags to the finding + one ask.

### System Health
- The comms-critic is a **style** critic; it passed the over-scoped notification because every line was individually well-formed. There's no gate that checks "does this notification's content match the one fact I was asked to convey" — that scope check stayed manual (and got caught by the user, not a gate). Candidate: a scope/brief-match pass in the comms path.
- Autonomy score: 3 interventions this session (1 user-caught scope-creep that reached the client as a double-send, 2 hook-caught B1 closing-deferrals). `agent-deferred` (B1 closing-deferral) remains the most-logged class; the stop-gate holds each time but the generation reflex persists.
