# Checkpoint: Brisken Rome Deliverables + Hours Tracker Rebuild

**Date:** 2026-06-18
**Status:** Rachel list SENT; one-pager / emails / landing drafted (Dirk-gated); hours tracker rebuilt + fixed

---

## Summary
Reconciled the Brisken Rome pre-event work against Dirk's authoritative TA Cook
2026 event pack, sent the consolidated company invite list to Rachel, and drafted
the one-pager, the E1/E2/E3 email sequence, and the Lovable landing prompt. A long
second half was spent rebuilding `hours-tracker.xlsx` after an Excel/openpyxl
collision corrupted it.

---

## What Was Done This Session

### Rome pre-event (Brisken p2)
1. Read Dirk's `TA Cook 2026/` pack (Event Execution Plan + 77-task Master Task
   Plan + intro call). Reconciled it into `conference-rome-2026-plan.md`: the
   Rachel list already half-existed (Dirk sent ~25 on 17 Jun), booking link
   `bookings.brisken.com/#/tacrome2026`, landing `/rome2026`, sending = brisken.com
   as Dirk, audience = past-event Ambi list.
2. **Rachel deliverable SENT.** Consolidated 47-company list (Dirk's 25 batch-2 +
   our 22 net-new, France-gap filled, 8 TA-Cook-warm), saved as clean single-sheet
   `deliverables/brisken-rome-2026-invite-companies.xlsx`, drafted + sent the email
   to rachel.dyke@tac-insights.com (logged in comms-log).
3. **TreasuryCentral/OnePilot one-pager** drafted (`deliverables/brisken-rome-2026-onepager.md`),
   sourced from the prototype, on the corrected hierarchy (TreasuryCentral = the
   universal interface, OnePilot = the AI layer under it, the applications on SAP).
4. **Pre-event emails E1/E2/E3** (`pre-event-email-sequence-DRAFT.md`) — our own
   draft (Dirk's HTML drafts treated as suggestions per user), hook/proof/nudge,
   Dirk's voice, booking CTA, corrected hierarchy.
5. **Lovable prompt** for the `/rome2026` landing (`rome2026-landing-lovable-prompt.md`);
   landing now being built in Lovable by the user. Logo fixed to the real asset
   (`static.wixstatic.com/.../Logo_Brisken_Light_edited.png`).
6. Verified brisken.com sending: M365 MX, SPF already includes Zoho, DMARC
   `p=reject` -> the one gap is Zoho Campaigns DKIM for brisken.com before E1.

### Hours tracker (system/tooling)
7. Logged this session's Rome hours to the Lead Generation tab; fixed the
   currency format; shortened the Lead Generation descriptions to the compact
   rule (reinstated for both tabs).
8. **Rebuilt the corrupted file.** Repeated COM close/reopen + force-kill cycling
   let Excel and openpyxl write concurrently and corrupted the workbook (openpyxl
   read it, Excel opened blank). Isolated it (test xlsx opened -> Excel fine, file
   bad), cloned all cells/formulas/formats into a fresh container, removed 3
   duplicate rows (were double-counting 4.5 h), fixed the rows-19-21 formats, and
   injected `ignoredErrors` to clear the green triangles. CSV backups exported.

---

## Key Decisions Made
- **Rachel deliverable = company names only** (user), and align to Dirk's actual
  list rather than ship the independent 40 I'd built.
- **Product hierarchy:** TreasuryCentral is the product / universal interface;
  OnePilot is the AI layer underneath; MDH / Smart Trading / Remittance Advice
  Gate are applications it runs; SAP is the foundation. Applied to one-pager +
  emails + landing prompt.
- **We draft the email sequences** (Dirk's drafts are input, not final copy).
- **Hours tracker corruption -> full rebuild into a fresh container** (not a
  repair of the damaged file).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/lead-generation/Rome-Event/conference-rome-2026-plan.md` | Modified | TA Cook reconciliation, sending readiness, open decisions |
| `context/comms-log.md` | Modified | Dirk batch-2 email transcribed; Rachel email logged as SENT |
| `deliverables/brisken-rome-2026-invite-companies.xlsx` | Created | The Rachel deliverable (47 companies) |
| `deliverables/brisken-rome-2026-onepager.md` | Created | TreasuryCentral/OnePilot one-pager draft |
| `context/lead-generation/Rome-Event/pre-event-email-sequence-DRAFT.md` | Rewritten | E1/E2/E3 our draft |
| `context/lead-generation/Rome-Event/rome2026-landing-lovable-prompt.md` | Created | Lovable prompt for the landing |
| `workspace/hours-tracker.xlsx` | Rebuilt | Rebuilt clean after corruption; Rome hours logged; descriptions compacted |
| `memory/project_brisken_outreach_domains.md` | Modified | Jeff Londres abandoned-domain reconciliation |
| `memory/feedback_hours_tracker_format.md` | Modified | reopen gotcha + format-copy gotcha + both-tabs rule |

---

## Current Status
- **Track 1 (Rachel list): DONE + SENT.** TAC invites with free-pass codes.
- **Track 2 (Dirk-gated):** one-pager, E1/E2/E3, landing prompt all drafted;
  await Dirk approval + Zoho Campaigns DKIM + landing publish.
- **Hours tracker:** rebuilt and fixed; awaiting user confirmation it opens clean,
  then remove `hours-tracker.broken-bak.xlsx` + the two CSV backups.

---

## Next Steps
1. Dirk approval on the emails + one-pager; **Zoho Campaigns DKIM for brisken.com
   before E1 (Fri 19)** — the `p=reject` trap that bounces the whole send.
2. Generate the one-pager PDF (PDF protocol) and host at
   `/brisken-rome-2026-onepager.pdf` for the landing download.
3. Finish + publish the Lovable `/rome2026` landing; wire the booking link + PDF
   download; put the URL on the booth NFC tags.
4. APP-6: ask Rachel to fix the sponsor-profile URL (`/sap-consulting` ->
   `www.brisken.com`).
5. After user confirms the rebuilt tracker, delete the broken backup + CSVs.

---

## Context for Next Session
### Files to Read First
- `context/lead-generation/Rome-Event/conference-rome-2026-plan.md` (the reconciled plan)
- `context/lead-generation/TA Cook 2026/TAC26 Rome - Master Task Plan.xlsx` (Dirk's task board)
- `context/comms-log.md` (Rachel thread + Dirk's positioning)

### Open Questions
- Does Dirk approve the E1/E2/E3 copy as-is, and is Zoho Campaigns access in hand?
- Landing: primary CTA booking-only, or booking + Booth #2?

### Working Notes
- brisken.com is on **Microsoft 365** (not Zoho); SPF already authorizes Zoho
  sending; DMARC `p=reject`; only Zoho Campaigns DKIM is missing.
- The Spaceship `brisken-*` farm: the 3 Zoho-auth domains are Jeff Londres's
  ABANDONED campaign domains (migrate to GoDaddy post-event, not warmable).
- Hours-tracker lesson: never bounce the same workbook between Excel and openpyxl;
  close fully (or never open in Excel mid-edit), and reopen via
  `GetActiveObject('Excel.Application')`, not Start-Process after a COM close.

### Reference Materials
- Booking: `bookings.brisken.com/#/tacrome2026` · Landing: `/rome2026`
- Real logo: `static.wixstatic.com/media/88b747_fe65b933129c489393c9c53445b9d010~mv2.png`

---

## How to Continue
Track 1 is closed. The Friday email chain is the live deadline and is gated on
Dirk's approval + Zoho DKIM, not on more drafting. The one-pager PDF + the Lovable
landing are the remaining build pieces.

---

## Strategic Feedback

### What Worked Well This Session
- Surfacing the named-contacts-vs-company-names conflict (Dirk's task plan said
  named contacts; user said company-only) as an explicit decision rather than
  silently picking. Same for the Dirk-versions alignment.

### Suggestions
- The hours-tracker is the third session this week to hit the Excel/openpyxl
  open-file hazard. It now escalated from a blocked save to a full corruption +
  long recovery. Worth a tiny helper (`tools/hours-log.py`) that fully closes
  Excel, edits via openpyxl, and reopens via GetActiveObject, so the cadence is
  never hand-rolled with COM again.

### System Health
- Autonomy score: ~3 human interventions (file-corruption discovery, format catch,
  description-length re-flag) plus 2 stop-b1-gate deferral catches. Elevated; the
  hours-tracker COM hazard is the recurring drag, and it is tooling-shaped, not a
  rule gap.
