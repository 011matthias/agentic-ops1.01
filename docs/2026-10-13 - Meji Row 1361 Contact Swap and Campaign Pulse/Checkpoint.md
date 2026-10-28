# Checkpoint: Meji Row 1361 Contact Swap and Campaign Pulse

**Date:** 2026-10-13
**Status:** Case closed; guard live on A1/A3; campaign upkeep done; two follow-ups open

---

## Summary
Nico's handover (sheet row 1361, CDS / Natalie Siret) was a source-data swap, not a mapping bug, and the automation never reached her. Row corrected, three more booked customers stopped, a contact-field guard deployed and verified on real traffic, then a campaign pulse with housekeeping on the Christmas waves and the weekly review.

---

## What Was Done This Session
### Row 1361 case (enquiry automation, Make eu2)
1. Traced the swap to source record 16627 (email/phone already swapped when A0 polled); A0/A1 copy fields 1:1. enquire@ mailbox holds no send to the phone string and no bounce; Natalie booked with Jess on 9 Oct (`parties` 2759).
2. Row 1361 corrected (D/E restored, status replied, stopped TRUE); rows 1269/1369/1379 (booked, still in A3) stopped. All read back.
3. Guard deployed: A3 filter requires `@` in column D and send error handlers Resume -> Ignore (verified on the 23:59Z real run); A1 normalises email/phone in vars 92/93 (verified on enquiry 16657 -> row 1390, score 40). Temp read UTIL 9955952 built, used, deleted.
4. PRs #1627, #1628, #1630 (status + infrastructure record).

### Campaign pulse and upkeep (Instantly)
1. Pulse over the four live campaigns; Pamela (Fenix Freight, booked) deleted from the warm wave; 7 opt-outs added to the block list; owner set on both Christmas waves (all read back).
2. Weekly engine: campaign list updated (Christmas waves + relaunched corporate), failure log added, task given network condition + 3 retries; review `2026-10-11.md` written; `pilot-routing.md` updated.

---

## Key Decisions Made
### Stop booked rows, not just fix 1361
- **Choice:** Stop rows 1269/1369/1379 (owner yes).
- **Rationale:** Bookings never flow back to the sheet, so booked customers keep receiving follow-ups.

### A3 failed sends no longer advance the step
- **Choice:** Resume -> Ignore on the three send modules.
- **Rationale:** Make logged status 1 either way, so a failed send was invisible and still moved the row.

---

## What Did NOT Work (and why)
- **Make UTIL tool returning nothing:** a ReturnData module without `metadata.expect [{tool_output, dynamicCollection}]` returns an empty result silently; found only by diffing against UTIL 8974201 after three runs.
- **Guessing the Gmail search module name (8 tries):** `google-email:searchEmails` etc. all "Module not found"; real name `executeEmailSearchQuery` came from `apps_recommend`. Its field names are unreadable (`validate_module_configuration` needs `apps:read`), so I used `makeAnApiCall` against the Gmail REST API.
- **Repeated `metadataHeaders` query keys in makeAnApiCall:** collapse to one, headers came back empty; omit the list.
- **First A1 guard deploy (vars after module 52):** accepted by Make and `live == staged`, but module 52 reads 92/93, so scores would have been 35 low. Caught by review before any A1 run; fixed in place. State equality does not prove reference order.
- **Reusing ids 57/58:** "Duplicate instance id" (taken by error handlers); the patch changed nothing.
- **Chaining CI poll + `gh pr merge`:** blocked by the repo's merge gate; merge must be its own call.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/status/enquiry-automation.md | Edited (merged) | Row 1361, booked rows, guard, verification |
| workspace/clients/meji-media/infrastructure.yaml | Edited (merged) | A1/A3 guard notes; UTIL gotchas |
| context/analysis-scripts/meji_campaign_health_check.py (gitignored) | Edited | Current campaign list, failure log |
| context/pilot-routing.md (gitignored) | Edited | Christmas wave campaign ids |
| context/weekly-reviews/2026-10-11.md (gitignored) | Written | This week's review |

---

## Current Status
- A1/A3 guard live and verified. Pre-deploy blueprints in `.scratch/meji-1361/backup-*`.
- Warm wave 774 -> 773 leads; dormant 36; corporate A at 1 clear positive of 3 (Similarweb), verdict 31 Oct.
- Ops status: no `platform` section in infrastructure.yaml (Make client, no ops-audit line).

---

## Next Steps
1. Gurmej to send Áine (Similarweb) the deck + next-year events calendar; she asked twice.
2. Decide a standing A3 booking check against `parties` (case-insensitive) and whether to tell Jess that bookings need the sheet row stopped by hand.
3. Investigate `MejiReplySLA` (0x800710E0 at 14:23 local 13 Oct).
4. Watch `MejiWeeklyReview` on Mon 19 Oct 06:17; a `FAILED-<date>.log` will appear in `weekly-reviews/` if it fails.
5. Campaign B (5d677062): retire or rebuild fresh (never patch in place).

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/status/enquiry-automation.md
- workspace/clients/meji-media/context/weekly-reviews/2026-10-11.md

### Open Questions
- Does the 0x1 Monday failure recur? Network-not-up-after-wake is a best guess, not proven.
- Case reads with raw `.scratch/meji-1361/` scripts are reusable but temporary.

### Working Notes
- Make tool scenarios: always add `metadata.expect` on ReturnData. enquire@ is readable via `google-email:makeAnApiCall` v4 (GET /v1/users/me/messages).
- Sheet email comparison to `parties` must be case-insensitive (`Joanne.hall99@` vs lowercase).

### Reference Materials
- PRs 1627/1628/1630; scratch: `.scratch/meji-1361/`, `.scratch/meji-campaigns/`

---

## How to Continue
`/resume meji-media`; start with Next Steps 1-3.

---

## Strategic Feedback

### What Worked Well This Session
- Differential probes before trusting reads (id filters, empty by_id vs known id), and reading enquire@ headers before concluding "never emailed".

### Suggestions
- Add a post-deploy check that every `{{N.var}}` reference appears after module N in flow order; `live == staged` missed the ordering bug.

### System Health
- Autonomy score: 7 human interventions, all decisions at approval gates (elevated by design; no unblocking needed). Two Stop-hook blocks (merge left pending, open offer).
