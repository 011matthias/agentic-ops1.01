# Checkpoint: Brisken Rome Booth Pack + Landing Publish

**Date:** 2026-06-19
**Status:** Rome in-person + publish assets shipped; landing live; deployed-booking publish gap flagged

---

## Summary
Resumed Brisken p2 Rome prep and built the in-person/booth-and-app pack, the branded one-pager PDF, the real Brisken logo as JPGs, and the OG social card + icon for the Lovable landing publish; verified the landing live at `rome2026.brisken.com`; confirmed the emails already point there and reconciled the booking-funnel state (deployed origin still on the dead Zoho link, an unpublished-edit gap).

---

## What Was Done This Session
### Booth + event-app pack (user-selected)
1. `Rome-Event/booth-playbook.md` — paste-ready event-app bio (Dirk's spine), badge-share guidance, the 15-min demo talk track, the 3 live-proof stories, BANT-lite booth qualifiers, EventsAir Scanner capture, during/post follow-up cadence, logistics.

### Deliverables
2. `deliverables/brisken-rome-2026-onepager.pdf` — branded dark/cyan one-pager for the EventsAir content gallery. Rendered the landing's `#onepager` section standalone via Chrome headless (the landing's own `@media print` whitens + prints the whole page, so a browser-print was wrong); verified 1 page A4, all claims present, zero em-dashes.
3. `context/brisken-logo.jpg` + `context/brisken-logo-on-navy.jpg` — the REAL Brisken logo (charcoal wordmark + two-tone hexagon), dark-on-white (cropped from the official TA Cook banner) and white-on-navy (from the live-site asset). Replaced the prototype's cube stand-in.
4. `deliverables/brisken-rome-2026-og.png` (1200x630 @2x) + `deliverables/brisken-rome-icon.png` (512 hexagon) — branded social card + favicon for the Lovable Publish dialog, instead of the generic "Generate" default. Plus paste-ready title/description.

### Verification + reconciliation
5. Verified the live landing (`tacrome-treasurycentral.lovable.app`, then `rome2026.brisken.com`): 200, full Brisken page renders, metadata on-brand, og:image = our card resolves 200.
6. Confirmed the canonical send pack already points all 3 emails to `rome2026.brisken.com` (a concurrent session's change); fixed its stale "placeholder" note; reconciled the booking line to the verified deployed state.

### Files touched in the shared plan
7. `Rome-Event/conference-rome-2026-plan.md` — confirmed-live DNS auth block (Zoho Campaigns DKIM `zcsend` NXDOMAIN), landing-published note, date roll.

---

## Key Decisions Made
### Use the real logo, not the prototype glyph
- **Choice:** Pulled Brisken's actual mark (live site `Logo_Brisken_Light.png` + the official banner) instead of the prototype's cyan-cube outline.
- **Rationale:** "Brisken's logo" means the real one; the cube was our stand-in. Verified against two official sources.

### Render the one-pager standalone, not browser-print the landing
- **Choice:** Chrome-headless render of the isolated `#onepager` section in dark styling; source in `.scratch/`, PDF to `deliverables/`.
- **Rationale:** The landing's `@media print` forces white + prints all sections; a naive print would have produced a white multi-page document, the opposite of the branded one-pager requested.

### Record the booking funnel as deployed-broken, not "owner says fine"
- **Choice:** After the user said the buttons are Cal.com and nothing was needed, I re-fetched the deployed origin: it still serves the dead Zoho link (no `cal.com` in live source), matching the concurrent session's browser check. Wrote that verified state into the pack rather than "works end to end."
- **Rationale:** "Live" means the deployed origin, not the editor. An unpublished editor change isn't a working funnel for a 252-person send.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `Rome-Event/booth-playbook.md` | Created | Booth + event-app runbook (gitignored context) |
| `deliverables/brisken-rome-2026-onepager.pdf` | Created | Branded one-pager for EventsAir gallery |
| `context/brisken-logo.jpg` · `context/brisken-logo-on-navy.jpg` | Created | Real Brisken logo, two lockups (gitignored) |
| `deliverables/brisken-rome-2026-og.png` · `brisken-rome-icon.png` | Created | OG social card + favicon for Lovable publish |
| `Rome-Event/rome2026-mail-merge-pack.md` | Modified | CTA-target confirmed; booking line reconciled to deployed state |
| `Rome-Event/conference-rome-2026-plan.md` | Modified | DKIM finding, landing-live note, date roll |

(Deliverables are uncommitted in the working tree; checkpoint did not commit.)

---

## Current Status
Brisken p2, manual-first (no orchestrator); comms current (0 days). Rome assets shipped. Landing LIVE at `rome2026.brisken.com` (200) with our branded OG card; all 3 emails already point there. **Open blocker (verified, shared with the concurrent session): the deployed landing still serves the dead Zoho booking** (`bookings.brisken.com/#/tacrome2026`, no `cal.com` in live source) despite the editor being switched to Cal.com, an unpublished-edit / CDN gap. E1 (dated Fri 19) holds until the deploy carries the Cal.com booking.

---

## Next Steps
1. Publish the landing so the deployed `rome2026.brisken.com` serves the Cal.com booking (live origin still on dead Zoho); re-fetch to confirm before E1.
2. Create + publish the Cal.com event `011matthias/rome2026` (404s) per `rome2026-booking-setup.md`.
3. Cut Dirk's personal-contact exclusions from the 252 list, then run E1/E2/E3 paced from his Outlook.
4. Upload the one-pager PDF + OG card + icon where Dirk wants them (EventsAir gallery / publish dialog).

---

## Context for Next Session
### Files to Read First
- `Rome-Event/rome2026-mail-merge-pack.md` (send copy + the booking-confirm checklist)
- `Rome-Event/booth-playbook.md`
- `Rome-Event/rome2026-booking-setup.md` (Cal.com config + embed)

### Open Questions
- Why does the deployed landing still serve Zoho when the editor is Cal.com? (Lovable publish step not run, or CDN cache.) "Live" = re-fetch the origin, not the editor.
- TreasuryCentral / OnePilot hierarchy + blended-71%-vs-in-house-sub-rate (gates copy; for Dirk).

### Working Notes
- One-pager render: source `.scratch/brisken-rome-2026-onepager-print.html` (ephemeral); re-render via Chrome headless to `deliverables/...onepager.pdf`. Edge headless collides (Edge is the open viewer) — use Chrome.
- Logo: dark-on-white cropped from `TA Cook 2026/.../Personalised Banner_Brisken.png`; navy from live-site `Logo_Brisken_Light.png`. The site's "Light" logo is white-text (hides on white) — flatten on navy, or crop the banner for white-bg.
- Three concurrent Brisken sessions ran today (collision zone): this one, "Booking Funnel + Cluster C", "Q&A Cluster + Pre-Event Send". Booking-funnel state is shared across the last two.

### Reference Materials
- Live: `https://rome2026.brisken.com` (200) · OG card serves as webp
- `dirk-go-live-sheet.md` (single Dirk conversation)

---

## How to Continue
The Rome in-person + publish assets are done and on disk. The one gating item for E1 is the booking deploy: publish the landing so the live origin serves Cal.com, verify by re-fetching the URL, then run the paced send from Dirk's mailbox after his exclusions.

---

## Strategic Feedback

### What Worked Well This Session
- Verifying the deployed origin (not the editor or the doc) before writing "fixed" caught a false "booking works" the user's report would have locked in; the same gap independently bit the concurrent session.

### Suggestions
- The one-pager render is now a repeatable pattern (isolate a section, Chrome-headless to PDF/PNG, pypdf-verify). A tiny `tools/html-section-to-pdf.py` would remove the per-use `.scratch` scaffolding and the Edge-vs-Chrome gotcha.

### System Health
- The editor-vs-deployed gap is a recurring class (this session + the Booking Funnel session, same day; `feedback_live_means_deployed_origin`). A `tools/` check that fetches a deployed URL and asserts an expected/forbidden string would make "is the change actually live" a one-command gate.
- Autonomy score: 3 human/guardrail interventions this session (1 stop-b1-gate deferral catch, 1 logo crop iteration-3x, 1 user correction on the booking that re-verification then reconciled).
