# Mini-Checkpoint: Meji Banter Origin and Christmas Variant Verification

**Date:** 2026-05-18
**Status:** Banter origin question drafted (held, B5); Christmas C/D claim verified against live data and downgraded
**Type:** mini

---

## Summary
Drafted the Banter list-origin question to Gurmej; investigated the A/B/C/D first-email variants on the live Christmas Bookers and Banter Instantly campaigns; raised a C/D relationship-overclaim concern, then verified it against live analytics and correctly downgraded it from "active problem" to "low-urgency quality refinement".

## What Was Done
- Resumed meji-media (fast-path YAML + memory + comms + infra). Chat renamed `meji--d1-voice-review`.
- Drafted `ask-gurmej-banter-origin-2026-05-17.md` (Thread 2, one ask: where did the 4,362 come from). User edited; fixed broken sentence, reordered logic, restored direct question. Lint clean. NOT sent (B5).
- Pulled both live Instantly sequences. Both = 2-step (4-variant first email A/B/C/D + single bump). Christmas C/D overclaim a personal working relationship for a mostly party-night-attendee audience. Defects found: `�` encoding char in Christmas C/D bodies; hardcoded "Gurmej"/"Sent from my iPhone". Banter sends from banterexp.com + mejiai.com, every variant assumes "you booked before".
- Wrote a Gurmej-readable copy-hold explainer; user challenged whether the complication is real.
- Pulled live campaign analytics. Distribution confirmed even (246/246/245/245). Per-variant replies A1 / B3 / C0 / D1 over ~245 each = statistical noise. Campaign dormant, ran on 982/983, ~1.9% reply, 38 bounces, 4 opps / GBP 4,000. Conclusion: explainer overstated the evidence. Flagged it `do-not-send` (preserved, not deleted).
- Produced 2-part work summary and a concrete Banter-origin impact breakdown (copy truth, deliverability blast radius into Sept peak, list-verification scope, ramp/domain).

## Current Status
- Banter origin message: ready, not sent (gated on user, external + B5).
- Christmas-copy-hold explainer: `status: do-not-send`, kept as base for a future toned-down line.
- Christmas C/D rewrite + `�` bug: identified, genuine but low-urgency, only matters before a re-run. Campaign is dormant/completed.
- Christmas Bookers verified outcome: ~1.9% reply, 38 bounces (~3.9%), 4 opportunities / GBP 4,000, open tracking off.

## Next Steps
1. Send the Banter origin question to Gurmej (user action, external + B5), then branch: warm = hygiene + go; cold/enquiry = rewrite as cold, reconsider mejiai.com in rotation.
2. Before any Christmas re-run: rewrite C/D to attendee-true premise and fix the `�` encoding bug. Quiet quality work, not a client message.
3. Pre-send hygiene for any Christmas re-run: verify all 983, exclude the 38 known bounces.

## Files to Read First
- workspace/clients/meji-media/context/drafts/ask-gurmej-banter-origin-2026-05-17.md
- workspace/clients/meji-media/context/drafts/christmas-copy-hold-explainer-gurmej-2026-05-18.md (do-not-send, has the evidence reason)
- workspace/clients/meji-media/context/banter-source-inspection.json (4,362 all verification_status none, single batch upload)
