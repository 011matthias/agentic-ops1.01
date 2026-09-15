# Checkpoint: Meji Christmas Suppression Build

**Date:** 2026-09-15
**Status:** Tier 1 complete (25/25 blocked). Wave not built. OWNER GO #2 outstanding.

---

## Summary

Compiled the Christmas stop-list that Gurmej made the precondition of his
re-engagement go, and executed it: 25 addresses are now on the account-wide
block list, up from 1. The 3-touch wave itself does not exist yet; the audience,
the sequence and the placement test are all still to build.

---

## What Was Done This Session

### Suppression compile (read-only)

1. Pulled all 2,459 lead rows across the three Christmas campaigns and read
   every one of the 355 inbound messages, rather than classifying on flags.
2. Cross-matched the audience against the client's own `parties` booking table
   through the read-only MySQL UTIL scenario; 35 matches.
3. Split the result into two tiers and reconciled every machine flag against
   the reading: all 31 `lt_interest_status=-1` people are accounted for.

### Writes (owner-approved, both read-back verified)

4. `wilsonsvets@gmail.com` blocked on its own, ahead of the batch.
5. The remaining 23 Tier-1 entries written under OWNER GO #1 after a green
   4-point B5 readiness check. Block list 2 -> 25, added set matches intended
   exactly, zero Tier-2 addresses caught.

### Record

6. Status file updated and landed via PR #823; the stop-list itself stays in
   the gitignored `context/suppression/` because it is PII.

---

## Key Decisions Made

### Two tiers, not one combined block list
- **Choice:** 25 addresses on the permanent account-wide block list; 82 held as
  a this-wave audience filter that is never written to the block list.
- **Rationale:** the block list is permanent and account-wide. The brief called
  for writing the combined set to it, which would have permanently blocked
  current customers from every future campaign. `paul.wilson@nsg.com` ("Already
  booked for Christmas at the ICC, looking forward to a great nights
  entertainment") is in the suppression set and must stay reachable next season.

### A new campaign, not a reused one
- **Choice:** build the wave as a new campaign and load the mailable audience
  into it.
- **Rationale:** 2,380 of 2,459 rows are `status=3`. Adding steps to a finished
  campaign is what re-triggers a completed audience en masse, and it inherits
  the suppressed people already sitting in it. The account already used this
  exact pattern once: Christmas Warm Re-engagement (2026-06-07, 907 leads) is a
  fresh-campaign re-import of Christmas Bookers (2025-11-10, 983 leads).

### Blocked the bereavement address immediately
- **Choice:** `wilsonsvets@gmail.com` written before the batch.
- **Rationale:** the practice replied 2026-06-30 that Alistair passed away in
  April, and the sequence still opened "Hey Alistair".

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/status/enquiry-automation.md` | edit (PR #823) | booked-suppression row -> done; new stop-list row |
| `workspace/clients/meji-media/context/suppression/2026-09-15-stop-list.md` | create | reviewable list, every address + verbatim reason (gitignored, PII) |
| `workspace/clients/meji-media/context/suppression/2026-09-15-stop-list.json` | create | machine-readable tiers for the wave build |
| Instantly account block list | 24 writes | 1 -> 25 entries |

---

## Current Status

Gurmej owes nothing and his stated precondition is now met. Nothing else in his
account has changed: no campaign was created, no audience loaded, no send made.

- Tier 1: **25/25 written and verified.**
- Tier 2: 82 people compiled, applied at audience-build time, not written anywhere live.
- Mailable audience: **1,445** of 1,552 distinct people.
- Senders ready: `gurmej@mejimedia.com` 90/day plus two mejixmas at 45/day, all `warmup=1`, 180/day against ~150 needed.
- meji-media has no `platform` section in `infrastructure.yaml`.

---

## Next Steps

1. Build the wave as a new campaign: load the 1,445, 3 steps, gaps on the
   **earlier** steps (the 2026-06-09 double-send came from getting this wrong).
2. Re-pull the booked set immediately before loading; `parties` grows daily and
   today's 35 will be stale.
3. Placement-test to the five seed inboxes (Gurmej's two Microsoft addresses
   plus Matthias's Brisken / iCloud / Gmail).
4. OWNER GO #2 plus a B5 readiness check, then activate.
5. Hand Gurmej the seven service complaints, separately from the build, with the
   family-exclusion results message that is already owed.
6. Deciders cold sequence on `c3daf05c` (Task 3), its own owner-go track.
7. Add a `platform` section to meji-media's `infrastructure.yaml`, or record why
   a Make.com client legitimately has none.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/suppression/2026-09-15-stop-list.md`
- `workspace/clients/meji-media/context/pilot-routing.md`
- `workspace/clients/meji-media/status/enquiry-automation.md`
- `.scratch/meji-suppression/final.json` (tiers + the 1,445 mailable set)

### Open Questions
- Which approved copy version carries the wave: B or C. Version A is the
  Deciders cold track on `c3daf05c`, a separate campaign.
- Whether the 82 Tier-2 people should be re-approached after Christmas, or
  carried into next season's suppression.
- Whether the seven complainants warrant a recovery gesture from Gurmej rather
  than silent suppression.

### Working Notes

**Four premises in the working brief were wrong, all row-vs-people confusions.**
The Bookers id was truncated; the real one is
`1f40cb36-c62c-4569-95bd-692709512c9c` and it is `status=1` active, not legacy.
"2,459 people" is 2,459 lead rows over **1,552 distinct people** (P1-Warm's 907
is a strict subset of Bookers' 983). "52 not interested" is 52 rows over **31
people**. "139 replies" is the analytics figure; **247 people** actually
replied, 355 inbound messages, and every flagged lead row has a real matching
message with zero mismatches. The 2,459 / 52 / 139 numbers were quoted to
Gurmej on 09-08 and should be corrected if they come up again.

**`parties` is this-season-only.** All 291 rows were created in 2026
(2026-01-28 to 2026-09-14 19:30). This was the load-bearing check: P1's audience
IS past attendees, so a lifetime booking history would have suppressed exactly
the people worth re-engaging. Re-verify this if the table is ever reset.

**`lt_interest_status` vocabulary, confirmed against the reading:** `0` is
out-of-office (145 of 154 independently read as auto-replies), `-1` not
interested, `-2` wrong person, `1` interested. `0` is NOT a stop signal.

**`stop_on_reply` is per-campaign.** All three campaigns have it on, but
`joanne.meadows@nhs.net` replied via P1-Warm and her Bookers row never saw it.
Low impact today because the old campaigns are finished, but it is the reason
the wave gets a fresh campaign rather than a reused one.

**Instrument findings.** `campaign_id` on `POST /leads/list` is silently ignored
and answers workspace-wide; the honoured field is `campaign`, confirmed by live
differential probe. `/emails` is capped at **20 requests/minute** and a 429
returns an empty item list that reads exactly like "this lead never replied" —
the first pull produced 43 false zeros, 17% of the replier set, all recovered by
throttling to 18/min. Only `s8974201 by_id` honours free-form SQL; the base
query has 24 columns for UNION purposes.

**Scripts** are in `.scratch/meji-suppression/`: `pull_leads.py`,
`pull_replies.py` + `repull_failed.py`, `classify.py`, `build_final.py`
(explicit per-person decisions), `verify_final.py` (adversarial re-check),
`readiness_t1.py`, `block_tier1.py` (the guarded writer).

### Reference Materials
- PR #823 (status record)
- comms-log 2026-09-14 "Gurmej completed the review page" and the 2026-09-11 finding

---

## How to Continue

Start from the stop-list file and `final.json`. The suppression half is closed;
the next real work is the wave build, and the first decision is which copy
version carries it. Do not reuse an existing campaign.

---

## Strategic Feedback

### What Worked Well This Session
- Reading all 355 replies instead of trusting the flags. The regex pass missed
  real opt-outs phrased politely ("taking us off your mailing list?"), and
  cross-checking the reading against `lt_interest_status=-1` caught five more,
  including the bereavement.
- Checking the season dimension on `parties` before trusting the booked match.
  That single query is what separated "35 people booked this Christmas" from
  "35 past customers we were about to delete from the re-engagement".
- Re-pulling the rate-limited leads rather than accepting 43 confident zeros.

### Suggestions
- The 20/min cap on `/emails` should live in a reusable client, not be
  rediscovered per script. Every future Instantly reply pull will hit it, and
  the failure mode is a silent false negative rather than an error.

### System Health
- **Autonomy: 3 human interventions.** Two were solicited decisions
  (tier split, OWNER GO #1); one was a genuine probe ("this has to be part of a
  campaign that already exists right?") that was worth answering with evidence.
- **Gates:** B1:1 B2:3 B3:0 skipped:2. The B1 skip is the fifth consecutive
  session with a closing-offer block. The primer contains it every time and has
  never prevented it; the pattern is specifically *offering a bounded invasive
  action* rather than splitting off its read-only half and putting the remainder
  as a decision.
