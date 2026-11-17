# Checkpoint: Meji Campaign Check-up and Block List

**Date:** 2026-10-29
**Status:** November corporate wave running clean; five removals blocked; October trial deadline Sat 31 Oct

---

## Summary
Checked the Meji campaigns on 10-28 and 10-29, blocked the five removals promised in the weekly report (block list 39 to 44), and confirmed the November copy needs no timing edit.

---

## What Was Done This Session
### Campaign checks (read-only)
1. 10-28: November wave (P2N) day one: 90 sent, 0 bounced, 0 unsubscribed, 6 out-of-office, 0 real replies. Warm list quiet because third emails batch from ~31 Oct.
2. 10-29: 51 more sent so far (141 lifetime), 0 bounces, only the same 6 out-of-office replies. October A trial: 12 replies, 1 opportunity, no new inbound. Organisers B: paused, nothing new.

### Invasive action (owner yes 10-28)
1. Readiness check green, then added reception@vcdp.co.uk, natalie.bennett@bespokeconstruction.co.uk, javed.ali@dpd.uk, kellyx03@hotmail.co.uk, lisa@visioncareathome.co.uk to the Instantly block list. Re-read: 44 entries, all five present, enquiries@vcdp.co.uk and vcdp.co.uk not blocked.

### Records
1. comms-log.md and pilot-routing.md updated; status/enquiry-automation.md corrected (activation 21:50Z) and merged (PR #1658).

---

## Key Decisions Made
### Keep stop-on-auto-reply as is
- **Choice:** Leave `stop_on_auto_reply` null (acts as stop); review November copy for stale timing instead.
- **Rationale:** Owner call 10-28. Copy has no dated wording, so no edit.

### Block all five removals
- **Choice:** Block by full address, not domain.
- **Rationale:** Owner call; VCDP's booking address must stay reachable.

---

## What Did NOT Work (and why)
- **`grep --no-ignore`:** rg-only flag; errored silently under 2>/dev/null. Plain `grep -rn` worked.
- **WebFetch of the Instantly createcampaign doc URL:** 404; the schema page via WebSearch had the answer.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/status/enquiry-automation.md | Edit (PR #1658) | Day-one numbers, activation time, block list note |
| workspace/clients/meji-media/context/comms-log.md | Edit (gitignored) | 10-28 check-up section |
| workspace/clients/meji-media/context/pilot-routing.md | Edit (gitignored) | stop_on_auto_reply note, block list 44 |
| .scratch/meji-campaigns/*_1028.py, corp_replies_1029.py | New (gitignored) | Read-only probes and the guarded block script |

---

## Current Status
Nov wave: 141 of 235 first emails sent; last 94 go Thu 29 (90) and Fri 30 (4); second emails from Mon 2 Nov. October trial at 1 of 3 positives. Ops status: no `platform` section in infrastructure.yaml for meji-media.

---

## Next Steps
1. ~31 Oct to 2 Nov: confirm reception@vcdp.co.uk got no third warm email (first test of a block on a lead mid-sequence).
2. Fri 30: confirm the last 4 November first emails went.
3. From 2 Nov: count November replies separately from the October trial.

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/status/enquiry-automation.md
- workspace/clients/meji-media/context/pilot-routing.md

### Open Questions
- Does the owner tell Gurmej about the November wave before the 31 Oct verdict?
- Weekly report edition 3 still awaits approval; its "removals for Monday" wording is now out of date.
- Make auto top-up and the 71 catch-alls (not loaded) remain owner-pending.

### Working Notes
Probe scripts space calls 3.2 s apart (20 req/min limit). Lead status 1 includes never-emailed leads; derive "emailed" from timestamp_last_contact. Health-check windows end yesterday.

---

## How to Continue
Re-run `.scratch/meji-campaigns/corp_replies_1029.py <since-iso>` for replies and today's counts.

---

## Strategic Feedback

### What Worked Well This Session
- Readiness audit before the block write (39 entries, full addresses, no domain blocked) and a re-read after; the filter probe confirmed per-campaign inbound was real.

### Suggestions
- Move the corporate replies script under tools/ if checks stay daily.

### System Health
- 12 friction candidates, all the Instantly tripwire firing on read-only calls or approved writes; discarded. Autonomy score: 2 human interventions (both requested decisions), otherwise fully autonomous.
