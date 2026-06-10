# Checkpoint: Meji Piece 1 Christmas Warm Live

**Date:** 2026-06-08
**Status:** Piece 1 LIVE. Christmas warm re-engagement campaign activated; first sends Monday 2026-06-09. All three pilot pieces now in motion.

---

## Summary
Built, audited, wording-confirmed, and activated the Piece 1 Christmas warm re-engagement campaign (945 past Moonlight & Mistletoe guests, venue-personalised Touch 1 in Gurmej's confirmed voice). Also answered Gurmej's two service questions (inbound automation, lead scoring) and closed the original two-piece scope loop, seeding the retainer conversation.

---

## What Was Done This Session
### Piece 1 build (Christmas warm)
1. **Venue enrichment** (read-only SQL via UTIL 8974201): mapped all 983 warm leads to venue via `full_data_parties.event_id -> full_data_events.id -> LEFT(event_id,1)` (most-recent booking). Wrote `d1-venue-map.json`. Coverage 819/983 specific, 164 generic.
2. **Bounce analysis**: the 38 status=-1 bounces are well-formed, corporate-skewed addresses, not bad data. Root cause = the old send used the dead `.co` domain (NXDOMAIN, fails SPF/DKIM/DMARC), which strict corporate receivers hard-reject. New campaign sends from the authenticated `.com`, removing the cause.
3. **Cohort** (`d1-final-cohort.json`): 945 = 983 - 38 bounces. No business exclusions (per owner direction; repliers/in-convo/booked all kept). 3 no-company leads get a "your team" `{{companyName}}` fallback.
4. **Loader** (`meji_p1_instantly_load.py`): preview/create/load/refresh/audit/activate/verify. Single campaign, sender `gurmej@mejimedia.com`, 3-touch, Touch 1 venue-branched via per-lead `venue_line`.
5. **Created + loaded** campaign `00fc708d` (paused), 945 leads, probe-verified `venue_line` attaches. Audit 17/17 GO (provenance clean, 0 overlap with live Piece 2).
6. **Refreshed to Gurmej's confirmed wording** (he returned his own voice 2026-06-08): "good night"/"the food", venue lines "at the ICC" / "at the Empire Leicester" / "at the ICB" / "at the last Moonlight & Mistletoe". PATCHed the sequence + 797 leads (148 already correct). Re-audit 17/17 GO; per-city spot-check confirmed values.
7. **ACTIVATED** (status 1, daily_limit 40). Verified independently: sender warm (100), schedule Mon-Sat 07:00-18:00 UK, no mailbox collision. First sends Monday 2026-06-09.

### Comms
8. Logged Gurmej's 2026-06-08 reply verbatim (comms-log Block 20). Drafted + (user sent) the answers to his two service questions and the "anything else" loop-close referencing his original two-piece scope.

---

## Key Decisions Made
### Fresh campaign, not reuse of dormant Christmas Bookers
- **Choice:** new campaign `00fc708d`, not editing `1f40cb36`.
- **Rationale:** the dormant campaign's 944 "Completed" leads would not reliably re-enter a replaced sequence (silent-failure risk). Fresh campaign guarantees all 945 enter Touch 1 cleanly. Owner confirmed this approach after first exploring reuse.

### No business exclusions
- **Choice:** keep all existing clients (drop only the 38 dead-address bounces).
- **Rationale:** owner direction; it's a warm re-engagement of existing clients, so in-convo/booked/replier filtering is unwanted. The 38 bounces are dropped purely to avoid re-bouncing on the new mailbox; recoverable later via verification.

### Venue wording anchored on Gurmej's own words
- **Choice:** Birmingham "at the ICC", Leicester "at the Empire Leicester", Wolverhampton "at the ICB" (his confirmed phrasing, em-dash -> comma per our copy handling).
- **Rationale:** he returned the copy in his voice; anchor-on-clients-words. The website (his source) settled Wolverhampton = "the ICB".

### Retainer framing held for step two
- **Choice:** answer his service questions now; do NOT pitch the retainer in the same message.
- **Rationale:** he fired the prior contractor for pushiness. The retainer ($1,000-1,500/mo dynamic/seasonal, already on the table) lands once the warm send is live and the first weekly report is in his hands, framed as formalising what he's already pulling toward.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/analysis-scripts/meji_p1_instantly_load.py | Created | Piece 1 loader (7 stages) |
| workspace/clients/meji-media/context/d1-venue-map.json | Created | email -> venue map (all 983) |
| workspace/clients/meji-media/context/d1-final-cohort.json | Created | 945 sendable cohort, venue + fallback |
| workspace/clients/meji-media/context/comms-log.md | Modified | Block 20 (Gurmej 2026-06-08 verbatim) + frontmatter |
| workspace/clients/meji-media/context/pilot-routing.md | Modified | Piece 1 -> campaign 00fc708d, LIVE |

Instantly state (not files): campaign `00fc708d` created, 945 loaded, refreshed to confirmed wording, ACTIVATED (status 1, daily_limit 40).

---

## Current Status
- **Piece 1 Christmas warm:** LIVE. Campaign `00fc708d-c17c-4b4f-bafb-9248bdd1e8b9`, sender `gurmej@mejimedia.com`, 945 leads, ~40/day over ~24 days. First sends Monday 2026-06-09 (UK Mon-Sat window). Touch 2 +18d, Touch 3 +28d, stop-on-reply + bounce-protect on.
- **Piece 2 corporate cold:** LIVE (A `c3daf05c` + B `5d677062`), sending.
- **Piece 3 Christmas cold:** not built. `mejixmas.com` mailboxes warming (read 100 at ~6 days old on a new domain; scrutinise before go-live). 3 venue cities only.
- Make side (A0-A3 inbound) untouched this session.

---

## Next Steps
1. **Monday 2026-06-09: verify first sends.** Once the first batch goes out, pull a few sent emails and confirm `{{firstName}}`/`{{companyName}}`/`{{venue_line}}` render and deliverability/bounce looks clean. This is the one open verification on Piece 1 (today's checks were on stored data, not the send itself).
2. **Retainer (step two):** once first sends + first weekly report land, frame the ongoing management (outbound week-to-week + inbound system care + weekly report) as the monthly arrangement. $1,000-1,500/mo dynamic/seasonal, soft on timing. Do not pitch before the proof is in his hands.
3. **Piece 3 Christmas cold:** scrutinise mejixmas.com warmup robustness (new domain), source the 3-city audience (geo-filtered subset of the corporate cold DB), venue-specific copy, build. After Piece 1 proven.
4. **Gurmej's "inbound email address first" priority:** he wants the inbound enquiry sending mailbox looked at first (the multi-inbox deliverability item before the Sept peak).

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/context/pilot-routing.md (CANONICAL routing; Piece 1 now LIVE on 00fc708d)
- workspace/clients/meji-media/context/comms-log.md (Block 20 = latest Gurmej state; service questions answered)
- workspace/clients/meji-media/context/analysis-scripts/meji_p1_instantly_load.py (loader; `--stage verify` to check live state)
- Memories: project_meji_commercial_model (retainer framing), project_meji_pilot_routing, feedback_anchor_on_clients_words

### Open Questions
- Does the warm send render + deliver cleanly on the first real Monday batch? (verify Monday)
- Are the mejixmas.com mailboxes genuinely send-ready, or is the 100 score misleading on a 6-day-old domain? (scrutinise before Piece 3)

### Working Notes
- **Instantly custom vars live in the lead `payload`, NOT top-level `custom_variables`** (which stays None). `{{merge}}` renders from payload. The audit must read `payload.venue_line` (fixed this session after a false-negative).
- **POST /leads does NOT update an existing lead** (returns it unchanged, no dup). Use **PATCH /leads/{id}** with `{custom_variables:{...}}` to update; it writes to payload. The loader's `refresh` stage does this.
- **owned_by must be set explicitly** on API-created campaigns (clone source GET returns it as None, so the keep-list clone fails). Loader now hardcodes OWNER `9b6145de-77fb-45f3-8584-84f786bcf32e`.
- **The instantly-invasive-gate hook does NOT fire on `python loader.py --stage create|load|activate`** (no api.instantly.ai in the command string; the calls are inside the script). B5 protocol held only via explicit owner orders. See friction.
- Venue split of the 945: Birmingham 430, Leicester 199, Wolverhampton 169, generic 147.

### Reference Materials
- Prior: docs/2026-06-07 - Meji Piece 2 Corporate Cold Live/Checkpoint.md
- Campaign IDs: Piece 1 `00fc708d-c17c-4b4f-bafb-9248bdd1e8b9`; Piece 2 A `c3daf05c-1395-43fb-8154-cc4643290859`, B `5d677062-adc0-4492-a4e3-3ffe8507ba88`; dormant `1f40cb36-c62c-4569-95bd-692709512c9c`.

---

## How to Continue
Piece 1 is live and verified at the data level; the only open Piece-1 item is confirming the first real sends Monday render + deliver. The natural next moves are the retainer conversation (once the first report lands) and the Piece 3 build (after warmup scrutiny). Start with `--stage verify` on the loader to re-confirm live state.

---

## Strategic Feedback

### What Worked Well This Session
- The owner's tight step-by-step direction (reuse-vs-fresh, no-exclusions, find the bounce cause) kept the build aligned and surfaced the right simplifications. The venue-wording loop (propose -> Gurmej returns his voice -> refresh in place) is a clean pattern: build with a sensible default, let the client confirm, PATCH to match, no rebuild.

### Suggestions
- The retainer is now one weekly-report away from its natural pitch moment. Worth pre-drafting the cost-benefit framing so it's ready the day the first report goes out, rather than composed under time pressure.

### System Health
- **B5 gap (important):** the instantly-invasive-gate is keyed on api.instantly.ai appearing in the Bash command string, so script-wrapped invasive calls (`python loader.py --stage activate`) bypass it entirely. The protocol held via explicit owner orders, but the structural backstop did not fire on the actual create/load/activate. Candidate fix: have the gate also flag invocations of known invasive loader scripts, or have the loader self-gate on its mutating stages.
- The cd-guard now catches `cd ... &&` compounds before they wedge the shell (it fired correctly this session) — improvement over 06-06/06-07 where newline-`cd` variants slipped through.
- Autonomy score: 3 friction events, all self- or hook-caught; 0 user-detected error corrections. Not elevated in the user-intervention sense; the user's messages were forward directions, not error fixes.
