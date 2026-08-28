# Checkpoint: Meji September Readiness + Make Credit Cliff

**Date:** 2026-08-27
**Status:** Credit fix approved by client, UNEXECUTED. Corporate-wave blocker found.

---

## Summary

Reopened Meji after a 26-day silence to prepare for the September peak. Found the Make
credit allowance burning ~3x its July rate and due to exhaust before the season's busiest
fortnight; got the tier move and auto-purchase approved by Gurmej. A live-inventory audit
then surfaced a bigger problem than the credits: an untracked campaign holding 267
in-sequence leads on the exact mailboxes the September corporate wave launches from.

---

## What Was Done This Session

### Make capacity diagnosis
1. Measured the live meter across four pulls (08-24, 08-26, 08-27) rather than trusting one
   sample. Cycle opened 20 Aug; 12,529 of 20,000 spent by 08-27 18:54 UTC.
2. Derived cost per enquiry from a full day of execution logs (08-23): A3 819 ops draining
   53 rows, A1 182 ops for 14 enquiries, 71.5 ops/enquiry combined. The op formula
   `1 + 15n` reproduces the logged totals exactly.
3. Forecast against the 11-year seasonal curve: Sep ~60k, Oct ~42k, Nov ~28k credits
   against a 20k plan, ~70k beyond plan across three months, back under in December.
4. Verified Make's billing mechanics from their docs: neither plan credits nor purchased
   extras roll over; on Core annual, extras still expire at each monthly reset. Extras
   carry a 25% markup off the current tier's rate, so the tier crossover sits at ~33k credits.

### Client comms
5. Sent the credit-cliff message (the report-back owed since the 2026-07-13 "keep me posted"
   exchange). Gurmej approved both changes outright on 08-25: "Thanks happy for you to do this."
6. Logged the exchange verbatim as comms-log Block 31 with the evidence and a forecast
   correction; `last_contact` moved to 2026-08-25.

### Live inventory audit
7. Enumerated all 9 Instantly campaigns. Our reporting covers 4. Two of the untracked five
   are Meji Media campaigns on our sending infrastructure.
8. Counted leads per campaign against the verified `campaign` scoping field. Cross-checked
   against two independently-recorded prior audits (RAD-19's P2B breakdown, RAD-14's P1 907)
   before trusting the numbers.

### Ledger + memory
9. RAD-29 opened for the A3 redundant-lookup finding, recording why it was NOT proposed.
10. New memory `feedback_client_message_human_register.md` from the owner's rewrite of the
    Gurmej draft.

---

## Key Decisions Made

### A3 redundant-lookup rewrite: deferred, not proposed
- **Choice:** Kept it out of the client message entirely and parked it as RAD-29 for October.
- **Rationale:** Owner directive not to propose a change we are not 100% sure is safe. The
  saving is real on paper (9 of every 15 credits per follow-up email go on getCell calls
  re-fetching columns `filterRows` already returned), but `executions_get-detail` returns
  status only for this scenario, so the filterRows output field names were never confirmed
  against a live bundle. A3 is also `sequential: true` and rewrites columns L and M mid-run,
  which a snapshot read would not see. This exact scenario already failed silently for two
  weeks in April 2026 on a column-handling change whose "verified fix" was a false positive
  read off an ops drop.

### Tier move over buying extras
- **Choice:** 20k -> 40k tier plus auto-purchase, monthly billing, stepping back down after November.
- **Rationale:** Extras cost 25% more per credit than in-plan credits, so the tier wins above
  ~33k. Annual billing would lock a peak-sized tier across a year whose Jan-Apr runs 2-14
  enquiries/month. Auto-purchase matters more than the tier choice: it makes a silent stop
  structurally impossible and removes the unresolved question of whether a mid-cycle upgrade
  grants its allowance immediately or only at reset.

### Do not re-open the 29 August date with the client
- **Choice:** Logged the forecast correction internally; sent nothing.
- **Rationale:** He has approved and the action is identical either way. Re-opening is noise.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/comms-log.md` | edit | Block 31: message verbatim, Gurmej's approval, forecast correction; frontmatter to 2026-08-25 / 67 entries |
| `workspace/clients/meji-media/context/opportunity-radar.md` | edit | RAD-29 added (A3 redundant-lookup, deferred with reasons) |
| `workspace/clients/meji-media/status/ops-radar.md` | edit | Brought current; live state, Instantly inventory table, the `campaign` API gotcha |
| `~/.claude/.../memory/feedback_client_message_human_register.md` | create | Six moves that separate a human client message from a correct one |
| `~/.claude/.../memory/MEMORY.md` | edit | Index row for the above |

---

## Current Status

**Make (production org 5473701, Core 20k, eu2):** all four scenarios active, zero errors,
next executions scheduled. 12,529 of 20,000 credits spent as of 08-27 18:54 UTC, 7,471 left.
Settled burn 1,045-1,185/day (the 2,162/day cycle average was inflated by a post-reset
backlog drain). Exhausts ~3 Sep, 7-day grace to ~10 Sep, reset 20 Sep.

**Approved and unexecuted:** `autoPurchasingActivated: false`, `operations: 20000` confirmed
at the last pull. Both changes are dashboard actions on the owner's side; there is no billing
endpoint in the Make MCP.

**Instantly inventory (verified 08-27):** P1, P2A and P3 are spent. P2B holds the 20 stranded
leads from the July pause. `Big Companies UK` holds 267 in sequence and 258 never contacted.

**infrastructure.yaml:** no `platform` section for meji-media; the client runs on Make.

---

## Next Steps

1. **Execute the tier move to 40,000 and enable auto-purchase in the Make dashboard.**
   Auto-purchase first, since it covers the gap regardless of how a mid-cycle upgrade prorates.
   Then the one-line confirmation to Gurmej. Runway to ~3 Sep.
2. **Resolve `Big Companies UK` (245913f7) before the corporate wave loads.** 267 in-sequence
   leads on the same three mejievent mailboxes as the September launch, in no routing doc.
   Decide what status -2 means operationally and whether the campaign is retired, resumed, or
   its 258 never-contacted leads are folded into the September wave.
3. **P1 warm list refill decision.** 1 fresh lead of 907 going into the peak month; refilling
   spends Apollo credits, so it needs an explicit call.
4. **mejievent.com DMARC ladder.** Still `p=none`; both the 10 Aug and 24 Aug steps lapsed.
   Needs the Porkbun dashboard API toggle before the `_dmarc` edit, and it changes live mail
   authentication on the September sending domain.
5. **Second sending domain:** decided by lapse. September runs at reduced volume on the three
   mejievent mailboxes. Worth stating explicitly rather than leaving on a list.
6. **RAD-29 (A3 rewrite):** October, after the peak, blocked on RAD-08 (no working prod-sheet
   read path).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/status/ops-radar.md` (live state + the inventory table)
- `workspace/clients/meji-media/context/comms-log.md` Block 31 (the credit thread, verbatim)
- `workspace/clients/meji-media/context/opportunity-radar.md` RAD-29, RAD-19, RAD-08
- `workspace/clients/meji-media/context/p2/september-prep-2026-07-29.md` (the go checklist)

### Open Questions
- What does Instantly campaign status `-2` mean operationally? Both `Big Companies UK` and
  `MejiAI Construction/HVAC` sit at it. It is not in the 0/1/2/3/4 set.
- Do the 258 never-contacted `Big Companies UK` leads survive the current ICP filter
  (50-2,000 staff, 17 sector tags)? They are already in the account at zero Apollo cost.
- Does a mid-cycle Make tier upgrade grant the new allowance immediately or at the 20 Sep reset?

### Working Notes
**Instantly `/leads/list` silently ignores unrecognised filter fields.** `campaign_id` returns
the entire workspace with no error; the correct field is `campaign`. Six campaigns returned
identical counts (8000/503/8000/410) before this was caught. This is the SECOND documented
instance of this API silently dropping a filter: the September prep pack already records
`?thread_id=` being ignored on `/emails`. Treat any Instantly filter as unverified until a
differential probe proves it scopes (send two different ids, confirm different results).

**Do not project a Make burn rate from the opening days of a billing cycle that followed an
exhausted one.** The catch-up drain is not the steady state; it read 2,162/day against a real
1,045-1,185/day and put a five-day-early date into a sent client message.

**Three mejimedia.co mailboxes show `warmup_status: -1`** (gurmej@, gurmej.p@, gurmej.pawar@)
while every other mailbox reads 1. They serve `Christmas Bookers`, which is ACTIVE but
effectively spent (2 of 983 still in sequence), so exposure is small. Hygiene, not urgent.

**`Christmas Bookers` = 983 leads = the past-attendee cohort** from the D1 warm rebuild.

**Shared working tree cost an edit this session.** `status/ops-radar.md` was written on 08-25,
verified at 0d, then reverted to its committed state by a sibling session and showed clean in
git. Gitignored `context/` files were untouched. Use a worktree next session.

### Reference Materials
- `https://help.make.com/extra-credits` (25% markup, expiry rules)
- `platform/public/docs/meji-media/volume-forecast.html` (the 11-year seasonal curve)
- Core pricing, from owner screenshots of the live account: 10k $10.59 / 20k $18.82 /
  40k $34.12 / 80k $64.71, billed monthly; extras $11.75 per 10,000

---

## How to Continue

Open in a worktree, not this shared clone. Check the meter first
(`organizations_get 5473701`): if `operations` still reads 20000 and
`autoPurchasingActivated` is false, the approved change has not been made and the runway is
the first thing to state. Then pick up `Big Companies UK`, which is the real blocker on the
September corporate wave.

---

## Strategic Feedback

### What Worked Well This Session
- Cross-checking the lead counts against two independently-recorded prior audits (RAD-19's
  P2B breakdown, RAD-14's 907) before trusting them. That is what turned a plausible table
  into a verified one, and it is the check that would have caught the bad table earlier had
  it been run first.
- Refusing to put a Make price in front of the client until the owner supplied screenshots
  of the actual account. The list price and his price were different tiers entirely.

### Suggestions
- Run the differential probe BEFORE building on any external filter parameter, not after the
  output looks wrong. One two-call probe (two different ids, confirm different results) would
  have cost 10 seconds and saved a 300s timeout plus a full re-run. This is B7/E2 applied to
  query parameters rather than to capabilities.

### System Health
- The `stop-b1-gate.py` hook caught a deferral again this session, the fifth agent-deferred
  event in five days. The `[B1 PRIMER]` path exists and still did not prevent the offer.
- The shared-working-tree clobber is the second cost of ignoring the SessionStart worktree
  advisory. The advisory is correct and was not acted on.
- Autonomy: 5 human interventions (elevated). All five were voice and framing corrections on
  client-facing text, none on the analysis. The technical findings held; the writing needed
  five passes.
