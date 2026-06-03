# Mini-Checkpoint: Meji Pieces Build Prep

**Date:** 2026-06-03
**Status:** Piece 1 data-prep complete (logic); Piece 2 staged to enrich; Piece 3 warmup running
**Type:** mini

---

## Summary
Logged Gurmej's 2026-06-02 reply (Piece 2 sample APPROVED + CEO-vs-PA ask + "which campaigns go out"), then staged all three pilot pieces toward launch. Resolved two Option-A decisions: Piece 1 venue source and Piece 2 AI icebreakers.

## What Was Done
- **Comms:** transcribed the Jun 02 Upwork thread verbatim into comms-log (Block 16 Gurmej approval/questions, Block 17 hours-tracker resolved 4→6 hr/wk). Frontmatter updated (32 entries).
- **Piece 2 copy:** wrote `piece2-cold-copy.md` — 2A decision-maker (CEO/MD, kept verbatim from live campaign 245913f7) + 2B gatekeeper (PA/EA/OM/HR, NEW, needs Gurmej OK). Maps to the 4 approved sample segments.
- **Piece 2 exclusion:** verified live — M&M past customers = **1,197 distinct domains** (delegates 890 + full_data_parties 871, deduped, free-email stripped).
- **Piece 2 enrich:** built `analysis-scripts/meji_p2_enrich.py` (Apollo search+bulk_match, credit-guarded dry-run; now also pulls industry/city/blurb for AI icebreakers). Compiles clean.
- **Piece 1 data-prep (steps 1-3, stopped before fresh campaign):** decoded booking schema; **venue RESOLVED** via `full_data_parties.event_id → full_data_events.id → LEFT(event_id,1)` (B 931 / L 348 / W 300 leaders); active-conv exclusion = enquiries in_contact/new/hot (83 now); booked-2026 = 6; cohort recipe locked (983 − 38 bounce − active − booked, re-pulled live at build).
- **Live mailbox state** (re-pulled): mejimedia.com + 2× mejixmas.com warmup ON (status=1, score maturing, daily_limit null); 3× mejievent.com send-ready (limit 30). pilot-routing.md updated.

## Current Status
- **Piece 1:** build-ready pending the gated fresh-campaign step; venue + exclusions solved.
- **Piece 2:** sending mailboxes ready, sample approved, copy + exclusion + enrich script staged. Decisions locked: 2 sub-campaigns (decision-maker/gatekeeper), AI icebreakers (Option A, generated agent-side, no LLM key needed).
- **Piece 3:** infra done, 2 mailboxes warming (~late June ready); venue-branched Christmas-cold copy not yet drafted.

## Next Steps
1. **P2 (first action next session):** run `meji_p2_enrich.py --search` then `--enrich --execute` on the approved 200 (≈200 Apollo credits), apply the 1,197-domain exclusion, generate AI icebreakers agent-side. STOP before Instantly load (B5).
2. **P1:** on user go, materialise the upload CSV (venue join + live exclusions) and build the fresh campaign (B5 gated).
3. **2B copy** to Gurmej for sign-off; reply to his 2 Jun-02 questions (held per no-unrequested-drafts until asked).

## Files to Read First
- workspace/clients/meji-media/context/pilot-routing.md
- workspace/clients/meji-media/context/piece1-warm-followup-status-2026-05-22.md (venue resolution at bottom)
- workspace/clients/meji-media/context/piece2-apollo-filter-spec-2026-05-24.md (activation status)
- workspace/clients/meji-media/context/piece2-cold-copy.md
- workspace/clients/meji-media/context/analysis-scripts/meji_p2_enrich.py
