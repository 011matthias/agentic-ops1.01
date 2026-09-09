# Checkpoint: Meji P2 September Rework

**Date:** 2026-07-20
**Status:** P2 rework brief SENT to Gurmej; 6 shaping questions open; September build gated on his answers (occasion pick) and the reworked-copy sign-off.

---

## Summary
Worked RAD-19 (retire the 20 stranded P2B leads at reactivation), then, on the user's "what do we need to know to raise conversion" pivot, ran a 3-agent read-only evidence sweep of all four Instantly campaigns and turned it into a September P2-rework foundation brief plus a sent client message to Gurmej.

---

## What Was Done This Session

### RAD-19 (P2B stranded leads)
1. Live read-only pull confirmed the count: campaign P2B `5d677062` status=2 (paused), 20 leads at status=1 = 3 fresh (never touched) + 17 in-sequence (touch-1 on 2026-07-07, awaiting touch-2); 384 completed + 30 bounced = 434 total.
2. Added the retire step to the September pre-load checklist in `pilot-routing.md` (OPEN item 3), dedup-carry-forward preferred over blanket-retire, mark-done over delete, coupled to the geography (item 1) decision. Retire EXECUTION stays owner-gated B5 at reactivation.
3. Updated RAD-19 in `opportunity-radar.md` (state: step added; retire owner-gated).

### Reply / OOO analysis
4. Pulled the 20 leads' engagement: zero replies, zero opens/clicks (opens untracked by design). Corrected an initial mislabel of the kavita@thoughtmachine.net inbound as a "genuine reply" (it is a maternity-leave OOO auto-reply; stop-on-reply already completed the lead).
5. Enumerated + classified P2A inbound (20 rows): ~19 auto/redirect, exactly 1 genuine human (a decline). Harvested OOO successor/redirect contacts. Answered the "should we follow up on OOO replies" question with the real value (deliverability-confirmed addresses + successor contacts + return-date re-touch), gated to September/B5.

### Evidence sweep + rework foundation
6. Ran a 3-agent Workflow (read-only): Instantly corpus (63 calls, 4,595 email rows, throttled under the 20/min limit), local docs/constraints, and a copy-gap analysis with benchmarks.
7. Wrote `p2/p2-september-rework-evidence.md`: verified funnel numbers (P1 2.97% / P2A 0.17% / P2B 0.46% / P3 1.05% human-reply, auto-replies stripped), the four settled findings, remaining copy gaps on top of the approved v2, the decisive unknowns, and a September test design.
8. Added pilot-routing checklist item (4): load the approved v2 copy before reactivation (live campaigns still carry the retired June variants).

### Client message
9. Drafted the Gurmej P2 rework brief, ran the comms-critic (5 findings, all fixed), added P1/P2/P3 labels at the user's request. User sent it.
10. On-send protocol: logged the verbatim into `comms-log.md` (new 2026-07-20 entry), updated frontmatter + the P2 BUILD unresolved item, deleted the draft, moved RAD-22 to `committed 07-20`.

---

## Key Decisions Made

### Rework on evidence, not on the zero
- **Choice:** Treat the P2 zero as statistically thin (~110 new-ICP contacts, summer trough) and NOT proof of copy failure; rebuild from what P1/P3 proved.
- **Rationale:** P2 autoreply rate (3.2%) matches P3 (3.0%), so delivery is not dead; at n~110 a healthy 1% list returns zero a third of the time.

### The conversion lever is post-reply, not reply-rate
- **Choice:** Frame the daily reply-owner + SLA (RAD-22) as the highest non-copy lever; now client-committed.
- **Rationale:** Every advanced pilot deal required Gurmej personally selling; replies that sat (Anita 33d, Beki ~13d, K&M) went cold.

### Concrete-offer transplant is the top copy lever, gated on an owner decision
- **Choice:** Do not draft the reworked copy until Gurmej picks the occasion anchor (January kickoff / awards / summer parties) within his year-round constraint.
- **Rationale:** P3 won on a concrete purchasable thing; P2 sold a service category. The occasion collides with his locked "corporate stays year-round" and only he resolves it.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/pilot-routing.md | Modified | Sept pre-load checklist items 3 (retire 20) + 4 (load v2 copy) |
| workspace/clients/meji-media/context/opportunity-radar.md | Modified | RAD-19 (step added) + RAD-22 (committed 07-20) |
| workspace/clients/meji-media/context/p2/p2-september-rework-evidence.md | Created | Rework foundation brief (numbers, findings, unknowns, test design) |
| workspace/clients/meji-media/context/comms-log.md | Modified | Verbatim of the sent brief + frontmatter + P2 BUILD unresolved item |
| workspace/clients/meji-media/context/drafts/gurmej-p2-rework-brief-2026-07-20.md | Created then Deleted | Draft, deleted on send (verbatim now in comms-log) |

(All context/ paths gitignored; no PR. No Instantly mutation this session, entirely read-only.)

---

## Current Status
The P2 rework brief is sent. Six questions are open with Gurmej; two are load-bearing: the occasion pick (unblocks the copy draft) and September seasonality (validates the whole August-unbilled / September-window premise, currently unsourced because our data is Christmas-only). P2B stays paused; the 20 stranded leads are untouched (retire is a September B5 action). Nothing sends until Gurmej approves the reworked pack.

Make platform: A0 poller + A1/A2/A3 live (not touched this session; no reconciliation run, no Make work done). Make credit line watched separately (07-20 reset).

---

## Next Steps
1. Await Gurmej's answers to the 6 questions; the occasion pick unblocks the reworked copy pack, then send for his sign-off (same review gate as P3).
2. Build the RAD-22 daily reply-check for September (now client-committed).
3. Fri 2026-07-25: generate the weekly report from the staged block + fresh health-check numbers.
4. At September reactivation (B5-gated, all owner-go): retire the 20 stranded P2B leads (dedup-carry-forward), load the approved v2 copy, widen geography UK-wide, fresh M&M exclusion, MX-filter + NeverBounce just before load.

---

## Context for Next Session

### Files to Read First
- workspace/clients/meji-media/context/p2/p2-september-rework-evidence.md (the whole rework basis)
- workspace/clients/meji-media/context/pilot-routing.md (September pre-load checklist, items 1-4)
- workspace/clients/meji-media/context/comms-log.md (2026-07-20 entry: the sent brief + the 6 open questions)
- workspace/clients/meji-media/context/opportunity-radar.md (RAD-19, RAD-22)

### Open Questions
- Which occasion anchors the corporate copy within the year-round constraint (January kickoff / awards / summer parties)?
- Does corporate booking actually peak in September in Gurmej's data? (ours is Christmas-only; premise unsourced, B4)
- How were Polestar / SJA / the top-5 accountancy firm actually won (channel steer for broadcast-vs-named-accounts)?

### Working Notes
- Verified funnel (human-verified, auto stripped): P1 26 unique repliers / 875 = 2.97%, 8 opps; P2A 1/589 = 0.17% (decline); P2B 2/431 = 0.46% (both declines); P3 6/569 = 1.05%, 2 opps. P2 combined = 3 human replies, all declines/wrong-fit.
- The three campaigns send from THREE different domains (mejimedia / mejievent / mejixmas); no cross-campaign "domain cleared" inference is valid.
- The approved v2 copy is NOT live: campaigns still carry the six retired June variants (verified live 07-20). Loading v2 is a September B5 action.
- Statistical bound: September volume supports ONE variant per arm + at most one structural A/B (detecting 1% vs 2% needs ~2,300/arm). Six variants x 30 leads was noise.
- Capacity: 3 mejievent mailboxes ~90/day shared ~= 1,980/mo before follow-ups; the 1,500-2,000/mo target needs a second domain (decision by early August for the warmup).
- OOO harvest is real but modest: deliverability-confirmed addresses + named successor contacts (Zoopla, Zenitech, Epsoms, HLD, Amvoc->BigWolf, etc.) + return-date re-touch; all September/B5-gated, feeds RAD-04.
- Raw evidence: workflow wz96k1r5o output; full email-page JSON cached under .scratch/meji-pull/pages/ (gitignored).

### Reference Materials
- Workflow run: wf_fd1146f0-f2d (task wz96k1r5o); 3 agents, 512k tokens.

---

## How to Continue
When Gurmej replies: capture his answers into comms-log, resolve the open items, and (if he picks an occasion) draft the reworked copy pack from p2-september-rework-evidence.md section 3 + the approved v2 baseline, then send for sign-off. Do not send any P2 copy or retire any leads without his go; September load stays B5-gated.

---

## Strategic Feedback

### What Worked Well This Session
- The user's "what do we need to know" pivot reframed a copy task into an evidence question; the 3-agent read-only sweep answered it in one pass and caught three false assumptions (dead deliverability, shared domain, the zero as proof) before any rework spend.
- Staging the client message through drafts/ + the comms-critic caught two B4 overstatements ("reaching inboxes", "8 live opportunities") and a re-ask of a settled item before the user saw the send.

### Suggestions
- The September build has one true blocker (the occasion pick). Batch the 6 questions as sent, but treat the occasion + seasonality answers as the two that gate work; the rest can trail without stalling.

### System Health
- **stop-b1-gate false-positive on quoted client copy (actionable).** The B1 deferral-scan fired twice on Register-A phrasing INSIDE the drafted client message ("If you want to go that way I will set it all up"), not an agent turn-action, costing 2 turns. Structural fix: exclude `> ` blockquote and fenced verbatim lines from the deferral-pattern scan so presented drafts are not read as agent deferrals. Highest-leverage system finding this session.
- **Transferable principle (from the OOO mislabel):** characterize inbound data after reading the full record (body + direction), not from a filter heuristic; a "Re:" threaded row can be an OOO or our own follow-up.
- Autonomy score: 2 human interventions this session (the OOO mischaracterization surfaced by the user's "where is that from?", and the P2-label refinement request).
