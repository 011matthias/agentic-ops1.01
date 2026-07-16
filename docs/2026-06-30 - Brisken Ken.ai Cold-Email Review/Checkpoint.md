# Checkpoint: Brisken Ken.ai Cold-Email Review

**Date:** 2026-06-30
**Status:** Review complete + staged in getken; reply drafted; both held pending Dirk's go

---

## Summary
Christian Funze (founder, getken.ai) asked to launch a "new" Brisken cold-email
campaign and pushed for approval. Investigated the old getken campaigns (live
Instantly), read and reviewed the proposed "Draft 4" in the getken approval
tool, entered a full per-item review (approve / request-change / note), drafted
a reply to Cristian, and logged the hours. Cold email was retired at Brisken
2026-06-12, so the launch decision is routed to Dirk; nothing has been sent.

---

## What Was Done This Session

### Investigation (read-only)
1. Tested the supplied Instantly v2 API key: valid format but workspace has no
   API plan (402 on every endpoint). Pivoted to browser after creds supplied.
2. Logged into Instantly (browser), read the 4 substantial old getken campaigns:
   ~417K emails sent -> ~1,393 replies -> 6 opportunities -> 0 closed. All
   "Managed by: GetKen.AI". Captured full sequence copy (education-led, long,
   bare merge-tag personalization, soft/vague CTAs).
3. Confirmed getken.ai = the vendor that set up Brisken's SpaceMail mailboxes
   (Antony Ngigi, Apr 2025); Cristian Funze is getken-side.

### getken "Draft 4" review (state-changing, user-authorized)
4. Read all 3 review pages: ICP (US/CA SAP industrials, treasury titles),
   tested leads (17/20 -> Treasury Leadership), email copy (3 steps, A/B
   asset-first vs call-first, genuinely personalized + Accenture proof + SAP
   Press PS).
5. Entered the review in the tool (held until explicit "just do it yourself"):
   - Page 1: approved Search Filters + AI Segmentation; **change-requested AI
     Qualification** (drops AstraZeneca/BMS treasurers for "no SAP signal",
     contradicts its own rule; Pfizer/AbbVie kept).
   - Page 2: approved 17 Treasury Leadership leads + Alexa Moore; **change-
     requested Rob Ctp (AstraZeneca) + Keith Gaub (BMS)** (same qualifier bug).
   - Page 3: **Request-changes (all)** with two pre-send questions (FMC tenure
     mismatch 17yr-vs-5yr = QA the AI lines; confirm production sending domain).
   - Later rewrote the Page-3 note from explanation-style to plain questions
     (user request), re-applied across all 18 copy items.
   - **Did NOT click "Submit feedback"** (the send to Ken) and approved nothing
     at launch level -> campaign not greenlit.

### Comms + admin
6. Drafted the reply to Cristian (human/plain register; credits the upgrade,
   flags the 3 fixes, sets the meetings metric, routes the go to Dirk).
7. Logged the inbound + teardown to brisken comms-log (2026-06-29 entry).
8. Logged hours to the Lead Generation tab of hours-tracker.xlsx; user then
   split it to 3h (teardown, 06-29) + 4h (Draft 4 review/reply, 06-30) and I
   verified the top grand totals (89.75 h / EUR 1256.50) by independent recompute.

---

## Key Decisions Made

### Hold the launch for Dirk, not approve under vendor pressure
- **Choice:** Enter detailed review feedback (change-requests), but do NOT click
  Submit feedback and approve nothing launch-level.
- **Rationale:** Cold email was retired at Brisken 2026-06-12 (Brisken's own
  ~150-mailbox/~2M-email history = 0 leads); Instantly off-limits per
  PROJECT-BOUNDARIES. Even a better campaign reopens a channel Dirk killed for
  cause. Decision is Dirk's; he is CC'd + physically with Matthias at the SAP event.

### Reframe the verdict: channel-fit, not copy quality
- **Choice:** Tell Cristian the question is whether anything changes the 0/2M
  channel-fit outcome, and to judge the 1,000-person test on booked meetings,
  not replies.
- **Rationale:** Old reply rates were 0.85-4.34% (not catastrophic); the failure
  was reply->opportunity->meeting conversion (6 opps / 417K), so a "clearer CTA
  -> more replies" upgrade does not obviously fix the real gap.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/comms-log.md | Modified | Logged the Christian Funze inbound + old-campaign teardown (2026-06-29 entry) |
| workspace/hours-tracker.xlsx | Modified | Logged ken.ai hours into Lead Generation tab (user then split 6.5 -> 3+4) |
| getken.ai approval page (external) | State-change (staged) | Full Draft-4 review entered; NOT submitted to Ken |

---

## Current Status
- getken Draft 4: "Review complete" in-tool, 41/41 items actioned, but **un-
  submitted** (Submit feedback not clicked). Change-requests on AI Qualification,
  2 leads, and all 18 copy items. Approved: Search Filters, Segmentation, 18 leads.
- Reply to Cristian: **drafted, not sent**.
- Both outward sends (Submit feedback + the email) are held for Dirk's go.
- Brisken p2 lead-gen: cold email remains retired; this is a vendor-pushed
  relaunch request, not an owned channel.
- hours-tracker Lead Generation grand total verified: 89.75 h / EUR 1256.50.

---

## Next Steps
1. Get Dirk's explicit yes/no on reopening cold email for the 1,000-person test
   (he is on the thread + at the event with Matthias).
2. On a yes: submit the getken feedback + send the reply to Cristian together,
   with the meetings-booked success metric agreed up front.
3. On a no / no-response: hold; the reply already routes politely to Dirk.
4. If launched, watch the 3 fixes land before send: qualifier loosened, AI tenure
   lines QA'd, production sending domain confirmed (protect brisken.com).

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/context/comms-log.md (2026-06-29 Christian entry)
- workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md (cold-email-retired decision, 2026-06-12)
- workspace/clients/brisken/PROJECT-BOUNDARIES.md (Instantly off-limits)
- This checkpoint

### Open Questions
- Will Dirk reopen the channel for a bounded test, or keep it closed?
- What does getken's production send actually send from (domain)? Unconfirmed.

### Working Notes
- getken approval link (Cristian's): app.getken.ai/approvals/4VdRzQgvFxQZ1Hdnd-UqoJuWB-r1J0FiP1Zre5a-svU
  (shared link, no login; review state persists server-side on the link).
- Instantly creds were supplied for read-only campaign review (admin.app.instantly.ai@brisken.com).
  Treat Instantly as read-only (B5 / no-invasive-action). API key is plan-gated (402).
- Old campaigns (all-time): V1.2 203,884 sent / 623 rep / 5 opp; C3 [Cash Mgmt]
  142,671 / 497 / 1; GKA_FD 37,930 / 181 / 0; 2.2v2 32,206 / 92 / 0.
- New Draft 4 is materially better and on-strategy (maps to the MDH teardown-
  asset motion); the only real objection left is the channel + deliverability.
- Submit feedback on getken is the irreversible outward send; left un-clicked.

### Reference Materials
- getken approval: https://app.getken.ai/approvals/4VdRzQgvFxQZ1Hdnd-UqoJuWB-r1J0FiP1Zre5a-svU
- Instantly: https://app.instantly.ai/app/campaigns

---

## How to Continue
Wait for Dirk's call on the channel. If yes: agree the meetings metric, submit the
getken feedback, send the Cristian reply (in the comms draft / this checkpoint).
If no: hold; nothing is sent. Keep treating Instantly/getken as read-only unless
an invasive action is explicitly authorized per-action.

---

## Strategic Feedback

### What Worked Well This Session
- "Just do it yourself" after a clear scope-of-effects + per-page plan was the
  right unblock: the invasive-action gate held until explicit authorization, then
  execution was clean. The gate did its job without over-blocking once authorized.

### Suggestions
- For vendor-tool reviews like getken, decide up front whether the in-tool
  feedback and the cover email are a package (they are) so the outward sends are
  sequenced together rather than re-litigated.

### System Health
- The stop-b1-gate produced false positives on phrases INSIDE quoted email
  drafts (e.g. "could you confirm what domain...", "if you want") that were
  legitimate draft content, not turn-end deferrals. The B1 gate cannot tell a
  drafted-comms block from the agent's own closing. Candidate refinement:
  exempt fenced/quoted draft blocks from the deferral scan.
- agent-browser on a React SPA (getken) is fragile: refs renumber between
  snapshot and click, off-screen clicks silently no-op (inner scroll container;
  `scroll down` did nothing, `scrollintoview` was required), and modal Save
  buttons must be re-found by name after fill. ~15-20 extra calls. Worth a memory.
- Autonomy score: 2 human interventions this session (1 B1-deferral cluster, 1
  browser slow-path; plus the user supplied the correct getken safelink after a
  bad token guess). Not elevated.
