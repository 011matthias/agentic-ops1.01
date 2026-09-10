# Mini-Checkpoint: Meji Family Exclusion Deployed

**Date:** 2026-09-10
**Status:** Family exclusion LIVE in the client's Make org and verified; venue live-read rebuild deferred to end of year; confirmation message to the room still owed
**Type:** mini

---

## Summary

Logged the 08-09 September room thread (Gurmej priced the fix, Jess corrected the frame, Gurmej approved ~3 h of family exclusion and deferred the venue rebuild), then deployed the exclusion to the live A1 and A3 scenarios with an owner go and verified it against real traffic.

## What Was Done

- Comms log: 2026-09-09 entry with both screenshots verbatim, decisions captured, frontmatter bumped (last_contact 09-09, unresolved item added).
- Live read of A1/A2/A3 blueprints and the client's events + enquiries tables. The only unmapped event id (151, 13 Dec) is the family event at Wolverhampton; all 26 family enquiries since mid-August carry it, so they were all getting Birmingham office-party content. The office/family split is clean (0 rows with any other value since id 14200).
- A1 8804011: filter on module 50 (enquiry_type = 0) ahead of the sheet write; event 151 added to the Wolverhampton list in module 80. A3 8804014: fourth filterRows condition, column F != Family Party. Deployed via `tools/make-api.py update` (the MCP has no scenario-update tool); pre-change pulls + rollback files in `.scratch/meji-family-exclusion/`.
- Verified: live blueprints diff equal to staged (the diff instrument was proven on the pre-deploy mismatch first); synthetic family POST ran 1 op status 1; the next real office enquiry (id 16043) ran 13 ops status 1; the first A3 run under the new query ran 16 ops status 1. Both scenarios active and valid after the PATCH.
- Docs on `client/meji-media/family-exclusion` (PR #789): infrastructure notes, both spec frontmatters (v3.2.0), new `status/enquiry-automation.md`.

## Current Status

Family enquiries no longer enter the pipeline; family rows already in the sheet are inert. Office traffic unaffected (peak season, ~20 enquiries per working morning). Hours: ~3 h agreed with Gurmej, not yet logged. The venue rebuild waits for Gurmej's end-of-year call; the September Christmas launch is still blocked on the same five unanswered items as 09-08.

## Next Steps

1. Send the confirmation to the room (draft in the session transcript): done, what changed, family rows already in the sheet stay as history, the venue rebuild parked until they add next season's dates.
2. Merge PR #789 on CI green (Band 2), then this docs PR.
3. Log the ~3 h against the family exclusion in the hours tracker.
4. Fix `tools/make-api.py get` to save the inner blueprint so a get -> update roundtrip works (the wrapper it saves today is rejected by `update`; cost one failed script run this session).
5. Unchanged from 09-08: redirect fix + review-link message, the five Gurmej launch blockers, auto top-up in Make.

## Files to Read First

- `workspace/clients/meji-media/status/enquiry-automation.md` (new workstream file)
- `workspace/clients/meji-media/context/comms-log.md` (2026-09-09 entry at the top, Block 32 at the bottom)
- `.scratch/meji-family-exclusion/` (live pulls, staged blueprints, rollback, verify.py)
