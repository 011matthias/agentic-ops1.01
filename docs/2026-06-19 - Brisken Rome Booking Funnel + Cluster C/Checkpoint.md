# Checkpoint: Brisken Rome Booking Funnel + Cluster C

**Date:** 2026-06-19
**Status:** Rome pre-event copy LOCKED + landing LIVE, but the booking funnel still dead-ends (Cal.com event not created; live landing still links to the dead Zoho booking). Q&A cluster C shipped.

> Distinct-folder checkpoint: an earlier same-day session already owns
> `docs/2026-06-19 - Brisken Lead-Gen Q&A Cluster + Rome Pre-Event Send/`
> (clusters A/D/G + merge pack). This session continued that thread (cluster C,
> Dirk's actual reply, the booking-funnel pivot) in its own folder to avoid
> overwriting that checkpoint (collision-zone discipline).

---

## Summary
Built AEO Q&A cluster C (Bank Fee Portal), processed Dirk's real v3 copy approval
into the locked send pack, and pivoted the Rome booking funnel from the dead Zoho
link to a Cal.com-embedded-in-landing model. The `/rome2026` landing went live at
`rome2026.brisken.com`, but its booking is still broken end to end.

---

## What Was Done This Session

### Lead-gen: Q&A cluster C
1. Built `deliverables/bankfee-qa-cluster.html` (substrate queries 13-15:
   CAMT.086 analysis, overcharge/fee-leakage, TWIST BSB / proprietary). FAQPage
   schema, 3-way comparison table, 71% stat folded in, no fabricated overcharge
   number. Validated (0 hits). Committed `5876edd`, pushed to
   `client/brisken/lead-gen-onepilot`. Q&A clusters now **4/7** (A/D/G/C);
   remaining autonomous = F (buy-vs-build), then B (Trade Automation).
2. Updated `aeo-substrate.md` §8 + `dirk-go-live-sheet.md` to mark C done.

### Rome pre-event: Dirk's reply processed
3. Logged Dirk's v3 approval verbatim to `comms-log.md` (last_contact -> 2026-06-19,
   inbound). Loaded his final copy into `rome2026-mail-merge-pack.md` (new
   subjects + preheaders, "command center" not "interface", E2 leads with the
   15-stage IC funding case, zero "running live"). Deleted the superseded v2 draft.
4. Verified deliverability live: native M365/Outlook send from
   `dirk.neumann@brisken.com` is SPF-aligned + DKIM-signed (selector1/2), clears
   `DMARC p=reject` with no DNS work. Retired the old "Zoho Campaigns DKIM" gate.

### Rome pre-event: booking funnel pivot
5. **Browser-verified the Zoho booking link is dead:** `bookings.brisken.com/#/tacrome2026`
   renders "URL doesn't exist"; the workspace only has a "Nico Test Meeting" test
   service with no slots.
6. Decisions: email CTA -> `/rome2026` landing (overrides Dirk's "booking page,
   not landing" note, flagged); tool = **Cal.com (free)**; meetings onto
   **Matthias's calendar** (per Dirk's "set it up on your calendar"). Wrote
   `rome2026-booking-setup.md` (full event config + Cal.com embed snippet for
   `011matthias/rome2026`).
7. Saved Dirk's headshot to `deliverables/dirk-neumann-profile.png` (clipboard
   capture, read-back verified). Wrote his Cal.com bio.
8. DNS guidance: subdomain `rome2026.brisken.com` (DNS at GoDaddy/domaincontrol;
   main site is Wix; subdomain isolated from the apex email records).
9. **Landing went live at `rome2026.brisken.com` (HTTP 200).** Filled the email
   CTA with that URL. BUT post-go-live check found the live landing still has 5
   "Book a meeting" buttons -> dead Zoho link, NO Cal embed, and the Cal event
   `011matthias/rome2026` itself 404s.

---

## Key Decisions Made
### Booking destination = the landing page (override)
- **Choice:** all email CTAs -> `/rome2026` landing, not the Zoho booking page.
- **Rationale:** warmer surface (proof + one-pager). Reverses Dirk's explicit
  note; flagged in comms-log + pack so he can be looped.

### Booking tool = Cal.com (free), onto Matthias's calendar
- **Choice:** standalone Cal.com event embedded in the landing, booked onto
  `Matthias.Silva@brisken.com` (he connected his Apple Calendar in Cal.com).
- **Rationale:** Zoho access uncertain; Cal.com is $0, self-serve, removes the
  Dirk dependency (his call: "set it up on your calendar").

### Distinct checkpoint folder
- **Choice:** new folder, not the existing 2026-06-19 brisken folder.
- **Rationale:** avoid overwriting the earlier same-day session's checkpoint.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `deliverables/bankfee-qa-cluster.html` | Created | Cluster C Q&A page (committed 5876edd) |
| `deliverables/dirk-neumann-profile.png` | Created | Dirk headshot for Cal.com avatar |
| `context/comms-log.md` | Modified | Dirk's v3 approval logged verbatim + booking finding |
| `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` | Modified | v3 copy loaded; CTA -> landing; status |
| `context/lead-generation/Rome-Event/rome2026-booking-setup.md` | Created | Cal.com event config + embed snippet |
| `context/lead-generation/Rome-Event/pre-event-email-sequence-DRAFT.md` | Deleted | superseded by Dirk's v3 |
| `context/lead-generation/outreach-assets/aeo-substrate.md` | Modified | §8 cluster C done |
| `context/lead-generation/dirk-go-live-sheet.md` | Modified | Q&A row updated |

(Only `bankfee-qa-cluster.html` is committed; the rest are gitignored context.)

---

## Current Status
- **Q&A:** 4/7 clusters built + validated + committed (A/D/G/C). Publish Dirk-gated.
- **Rome copy:** v3 locked, Dirk-approved. Email CTA -> `https://rome2026.brisken.com`.
- **Deliverability:** native Outlook send clears `p=reject`, no DNS work.
- **Landing:** LIVE at `rome2026.brisken.com` (200).
- **Booking: BROKEN.** Cal event `011matthias/rome2026` 404s; live landing still
  links 5 buttons to the dead Zoho `tacrome2026`; no Cal embed on the landing.
- **Date pressure:** today IS Fri 19 = E1's own send date. E1 cannot go with a
  dead booking, so the Friday send slips until the booking funnel is fixed.

---

## Next Steps
1. **Create + publish the Cal.com event** (`011matthias/rome2026`, currently 404)
   per `rome2026-booking-setup.md`: title/desc/15-min/two locations/availability
   24-25 Jun + virtual/one question. USER ACTION (no access to the Cal account).
2. **Replace the 5 Zoho links on the live landing with the Cal embed** (snippet
   in the booking-setup file). USER ACTION (no access to the Lovable project).
3. Get **Dirk's personal-contact exclusions**; cut them from the 252 list.
4. Then E1 can send (paced; cadence E1/E2/E3, now slipped from Fri 19).
5. Lead-gen autonomous: cluster F (buy-vs-build), then B (Trade Automation).
6. Take `dirk-go-live-sheet.md` to Dirk (identity, publish, cockpit access, the
   2 product-shape calls).

---

## Context for Next Session
### Files to Read First
- `context/lead-generation/Rome-Event/rome2026-booking-setup.md` (Cal config + embed)
- `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` (locked v3 copy + status)
- `context/comms-log.md` (Dirk's 2026-06-19 reply)

### Open Questions
- Booking: keep Cal.com-embed (chosen), and is the landing edit done in Lovable
  or by hosting an exported static landing on Fly?
- Dirk go-live-sheet items: blended 71% vs in-house sub-rate; TreasuryCentral /
  OnePilot hierarchy.

### Working Notes
- **Verified live 2026-06-19:** brisken.com MX=Outlook, SPF includes Outlook+Zoho,
  DMARC `p=reject`, M365 DKIM selector1/2 published. NS = domaincontrol (GoDaddy).
  Apex + www = Wix. `rome2026.brisken.com` = 200.
- The booking has now broken TWICE the same way (Zoho dead, then live landing
  still pointing at it): a live page with a dead booking is the recurring trap.
  Verify the *terminal* booking action, not just that the page loads.
- Cal embed snippet (011matthias/rome2026, brand cyan) is in the booking-setup file.

### Reference Materials
- Live landing: https://rome2026.brisken.com
- Cal event (currently 404): https://cal.com/011matthias/rome2026
- Booking screenshot trail: Zoho `bookings.brisken.com` (dead), GoDaddy Airo, Cal.com setup

---

## How to Continue
The Rome funnel is one fix away from working: stand up the Cal.com event and swap
the landing's booking buttons to the Cal embed. Both need account/project access
the agent doesn't have, so they're user actions; everything else (copy,
deliverability, DNS, event config, embed snippet, exclusion-list step) is ready.

---

## Strategic Feedback

### What Worked Well This Session
- Verifying the *terminal* booking action in a real browser (not just that pages
  return 200) caught two dead-booking states the user would otherwise have shipped
  to 252 prospects: the original Zoho link, and the live landing still pointing at
  it. B2 (test behavior, not state) paid off twice.

### Suggestions
- The Rome funnel has many moving externally-owned parts (Wix landing, Lovable,
  Zoho, Cal.com, GoDaddy DNS, M365). A one-line "funnel health" check
  (curl the landing + assert the booking destination resolves) would catch the
  dead-booking trap automatically before each send, instead of by manual browser
  poke. Worth a small `tools/check-rome-funnel.py`.

### System Health
- Autonomy score: 3 human interventions (all stop-b1-gate catches on turn-end
  deferral phrasing; self-corrected each). Same long-running B1 phrasing-reflex
  cluster; the hook is holding. The genuine forks this session (booking tool +
  calendar) were correctly routed to AskUserQuestion rather than deferral.
- Collision-zone recurs: 3rd+ same-day brisken/meji session sharing the session
  log / context YAML / docs folder; handled by distinct-folder + merge.
