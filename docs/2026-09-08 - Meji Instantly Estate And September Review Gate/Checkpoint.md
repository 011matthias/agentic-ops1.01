# Checkpoint: Meji Instantly Estate And September Review Gate

**Date:** 2026-09-08
**Status:** September Christmas relaunch still blocked on Gurmej; review page live and verified, link message written and UNSENT pending a redirect fix

---

## Summary

Reconstructed how every Meji campaign's audience and purpose changed since creation, corrected three factual errors in the Instantly estate reference doc, and cold-drive verified the new gated review page at `unpauseai.com/docs/meji-media/review`. The page's answer machinery works end to end, but the post-unlock redirect strands the recipient on a legacy index with no route to the review page, so the message carrying the link was deliberately not sent.

---

## What Was Done This Session

### Campaign audience-evolution history
1. Traced all four of our campaigns from creation through every audience change, from `context/pilot-routing.md` as the canonical record. P1 and P3 kept their purpose throughout and only changed by list hygiene and pacing; P2 had its audience definition replaced twice and the meaning of its A/B split changed once (role at small companies, then seniority at 201-2000 staff).
2. Added a `#evolution` section plus nav link to the estate doc carrying that per-campaign timeline.

### Corrections to the estate reference doc
1. **880-lead misattribution, three places.** The list retired 1 Jul was our own June-generation P2 list (924 loaded minus the 44 P2B bounce-fix deletions), not the inherited one. Big Companies UK coincidentally also holds exactly 880 leads and was never retired; its finish/retire/fold call is still open.
2. **Christmas capacity 210/day corrected to 180/day**, three places. `bookings@christmasofficeparty.co.uk` is reserved as the second sender for the inbound enquiry pipeline, not spare outbound capacity.

### Review page verification (cold drive)
1. Drove the gate with no session, from the URL onward, using curl rather than the CDP-bound Playwright (which would have carried the owner's Edge session and defeated the point).
2. Confirmed working: cold GET returns the gate not the content; code `mn040307` accepted with the form's hidden `site=meji`; HttpOnly+Secure `meji-auth` cookie; `/review` renders; answers POST to `/api/meji-review` and are gated (`401 passcode_required` without cookie, `400 unknown_item` for junk).
3. Found the blocker and two lesser defects (see Key Decisions).

### Comms + status
1. Logged the 2026-09-08 19:35 outbound to Gurmej verbatim into `comms-log.md`; the September thread had only ever lived in `ops-radar.md`.
2. Recorded the commercial change: the rest of September on corporate is offered free, narrowing paid scope to the suppression build, list rebuild and weekly maintenance retainer.

---

## Key Decisions Made

### Hold the review-link message rather than send it
- **Choice:** Message drafted and left unsent until the post-unlock redirect lands the recipient on `/review`.
- **Rationale:** The unlock discards the posted `from=/docs/meji-media/review` and clamps to `/docs/meji-media`, whose index links only to ab-testing, guide, lead-scoring, scaling and system-overview. Gurmej would enter the code and dead-end. Re-clicking the original link works once the cookie is set, but he has no way to know that. Same failure class as the 2026-09-07 Brisken packet.

### Do not send a correction for the 210/day figure
- **Choice:** Fix the internal doc, leave the client message alone, never wire `bookings@` into a Christmas campaign.
- **Rationale:** 180/day still clears the ~150/day the seven-week plan needs, so no operational promise is broken. A correction message would spend credibility on a number that does not change the plan.

### Recommend retiring Big Companies UK rather than asking again
- **Choice:** Fold it into the question set as a recommendation with a stated reason, not a fourth open question.
- **Rationale:** Asked twice already and unanswered. It stopped itself on 5.9% bounce, its 258 unreached leads sit on old big-company targeting rather than the approved 50-2000 band, and any that still fit get picked up by fresh sourcing.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `docs/references/meji-instantly-estate-2026-09-08.html` | Edit | 880 misattribution fixed x3; capacity 210 to 180 x3; new `#evolution` section + nav link |
| `workspace/clients/meji-media/context/comms-log.md` | Edit | 2026-09-08 outbound logged verbatim with flags and still-unsent list (gitignored) |
| `workspace/clients/meji-media/status/ops-radar.md` | Edit | 09-08 evening section: free-September decision, capacity correction, review-page verification and blocker |

---

## Current Status

Christmas relaunch is blocked on Gurmej and has been since the 09-05 launch message. He replied 09-07 with three items (suppression, volume, corporate timing), all answered in the 09-08 19:35 outbound, but he has still not answered either of the two things the launch message said it needed. Corporate A and B are being upgraded in place with the approved 29 July copy; the owner has offered the rest of September on it free.

The review page is the intended fix for the answer backlog and is technically sound; only its entry path is broken. `platform:` has no section in `infrastructure.yaml` for meji-media, which is expected since the client runs on Make.com and the review page lives on the separate `akkton/unpauseai-web` deployment.

---

## Next Steps

1. **Fix the post-unlock redirect** so a same-site `from` is honoured, or add a `/review` link to the `/docs/meji-media` index. Then re-run the cold drive before sending.
2. **Remove the client-side gate literal** `var MEJI_CODE = 'meji2026'` from the legacy `/docs/meji-media` index; it violates rule_gated_access and is live.
3. **Send the review-link message** (text in the session transcript) once 1 is verified.
4. Fix the German gate copy ("Bitte Zugangscode eingeben") on the Meji gate screen.
5. When Gurmej answers: the past-customer export and the cold geography pick are the two that actually release the Christmas send.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/status/ops-radar.md` (09-08 evening section is the live state)
- `workspace/clients/meji-media/context/pilot-routing.md` (canonical campaign/audience record)
- `docs/references/meji-instantly-estate-2026-09-08.html` (corrected estate reference)

### Open Questions
- Is the `from` clamp in the unlock route deliberate open-redirect protection, or an oversight? Determines whether the fix is in the route or in the index page.
- Which `enquiry_status` value means booked, and does `reference` fill on booking? One line from Jess, gates the booked-suppression build.
- Does the opt-out/suppression build get priced per-project or folded into the weekly maintenance retainer?

### Working Notes

**Grepping server-rendered HTML cannot prove absence of client behaviour in a React app.** I searched `review.html` for `onclick`, `addEventListener`, `fetch(`, `setItem` and found zero of each, and nearly concluded the Save and Approve buttons were inert markup with no transport. That would have been a serious wrong call in a client-facing report. Next.js compiles JSX handlers into `/_next/static/chunks/*.js`, so the served HTML legitimately shows nothing. Downloading the ten chunks and grepping for the button labels found the client component immediately (`ac4cf3a78628f2a9.js`), which contained the real `fetch("/api/meji-review", {method:"POST"})`. Transferable rule: to test client behaviour, drive the client or read its bundle; the HTML is not the program.

**The unlock form posts a hidden `site` field.** My first POST sent only `code` and `from`, got `err=1`, and redirected to the Wärme Wimmer login with `from=/docs/warme-wimmer/`. That looked exactly like a cross-client routing bug in the page. It was my omission. Checking my own request before blaming the system is what kept a false defect out of the report. The correct payload is `code`, `site=meji`, `from`.

**Playwright MCP is CDP-bound to localhost:9222** and fails with ECONNREFUSED when Edge is not running with the debug port. For a cold drive this is a feature, not a limitation: driving the owner's Edge would carry their session and prove the wrong thing. curl with a fresh cookie jar is the more correct instrument for verifying a server-side gate.

**Verified live numbers (2026-09-08 Instantly pull):** 2,459 Christmas leads across three campaigns, 5,497 sent, 139 replies, 52 tagged not interested, 1 address on the account block list, 0 unsubscribes. Every figure in the 19:35 outbound checks out against this.

### Reference Materials
- `https://unpauseai.com/docs/meji-media/review` (code `mn040307`)
- `.claude/rules/rule_gated_access.md` (server-side gate model, the violated rule)
- `workspace/clients/meji-media/context/inbound-enquiry-multiinbox-scope.md` (why `bookings@` is reserved)

---

## How to Continue

Fix the redirect first; nothing else matters until the recipient can reach the page he is being sent to. Re-run the cold drive (curl, fresh jar, POST `code`+`site=meji`+`from`, then GET `/review`) and confirm the 303 lands on `/review`. Then send the drafted message. The five open Gurmej items are already written up at the end of the `ops-radar.md` 09-08 section and are the page's content.

---

## Strategic Feedback

### What Worked Well This Session
- The cold drive caught a real dead-end that every server-side check would have passed. The cold-drive sub-clause earned its place: the gate returned 200, the API authenticated, the page rendered, and the recipient still could not get there.
- Checking my own request before reporting a cross-client routing bug, and checking the JS chunks before reporting inert buttons, each stopped a confident wrong finding from reaching the user.

### Suggestions
- The estate doc carried two independent factual errors that had already been through a client-facing draft. Reference docs assembled from multiple sources deserve a numbers-traceability pass against the canonical record before they inform any outbound message, not after.

### System Health
- **Autonomy: 1 human intervention.** The one redirect was the owner having already sent their own answer to Gurmej, which made the staged question set moot. Not a correction of a mistake, but it did mean a drafted deliverable went unused; asking earlier whether a reply was already in flight would have avoided the wasted draft.
- `stop-b1-gate.py` fired once on a closing offer ("If you want, I can correct that row"), the fourth-plus B1 block in the recent register. The B1 primer is containing these but not preventing them.
