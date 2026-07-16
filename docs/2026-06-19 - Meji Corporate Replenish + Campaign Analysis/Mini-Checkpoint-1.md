# Mini-Checkpoint: P2B Bounce Remediation + NeverBounce Gate

**Date:** 2026-06-19
**Status:** P2B recovered (live, cleaned, throttled); NeverBounce wired + standing gate added
**Type:** mini (continues the full Checkpoint.md this folder)

---

## Summary
After the full pull, P2B (Organisers) auto-paused on a bounce spike. Root-caused it to my bulk organiser load, set up NeverBounce, cleaned + relaunched P2B at reduced pace, verified P2A too, and built a standing no-bulk-load gate so it can't recur.

## What Was Done
- **Diagnosed the P2B pause:** Instantly bounce-protection auto-paused P2B (status -2) at 5.2% (22/422). Of 22 bounces, 15 old-list + 7 from my new batch; the new sends tipped an already-3.7% campaign over the ~5% line. P2A unaffected (0.9%). I did not pause it.
- **NeverBounce set up:** `NEVERBOUNCE_API_KEY` (private_...) added to `context/.env` (gitignored); user added credits. Built reusable `analysis-scripts/meji_nb_verify.py` (pulls a campaign's leads at a status, verifies, buckets valid/catchall/unknown/invalid, writes keep/drop).
- **P2B cleaned + relaunched:** verified 193 unsent -> kept 149 (120 valid + 29 catch-all), removed 44 (43 unknown + 1 invalid); reduced `daily_limit` 90 -> 25; re-activated (status 1). Now 369 leads, verified via leads/list (analytics count lagged). Process miss: activated before the lead-delete confirmed (delete 400'd on empty-body DELETE; ~1 min live with the 44 in, no bad sends at 25/day); re-ran delete without Content-Type header (44/44) and verified.
- **P2A verified:** 307 unsent -> 233 valid + 48 catch-all + 26 unknown, **0 invalid**. Kept the 26 unknowns (P2A is at 0.9% with headroom; removing would discard deliverable leads to avoid a risk it can absorb). No pace change.
- **Standing gate added (owner directive):** P2B is NO-BULK-LOAD. Enforced two ways: pilot-routing Hard rule #6 (decision-time) + an automatic guard in `meji_p2_instantly_load.py` (`P2B_MAX_LOAD = 50`, blocks >50 new leads into P2B, points to the verify step). P2A loads normally.
- **Comms reworded:** Make-credit reply tightened to seasonal framing (drafted, user to send); the client-facing pause explanation reworded compact + neutral.

## Current Status
- **P2B:** live, 25/day, 149 NeverBounce-clean leads queued, no-bulk-load gated.
- **P2A:** live, full pace, verified (26 unknowns intentionally kept).
- **NeverBounce:** key + credits in; `meji_nb_verify.py` reusable for P3 + future loads.

## Next Steps
1. Watch P2B + P2A day-one bounce as the verified leads send (the signal the fix held).
2. User sends the drafted Make-credit reply; route the Anita Patel / CLC hot lead to Jessica.
3. P3 build via `context/piece3-build-prompt.md` (fresh chat) — apply the same NeverBounce-verify step before any P3 load.
4. Inbound-enquiry-automation scope still owed (since 2026-06-08).

## Files to Read First
- workspace/clients/meji-media/context/pilot-routing.md (P2A/P2B live state + Hard rule #6 no-bulk-load gate)
- workspace/clients/meji-media/context/p2b-nb-results.json + p2a-nb-results.json (verification verdicts, keep/drop lists)
- workspace/clients/meji-media/context/analysis-scripts/meji_nb_verify.py (reusable verifier) + meji_p2_instantly_load.py (the gate)
- workspace/clients/meji-media/context/piece3-build-prompt.md (P3 fresh-session build)
