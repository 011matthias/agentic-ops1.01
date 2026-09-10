---
project: meji-media
workstream: enquiry-automation
group: ""
spec: a0, a1, a2, a3
state: live
updated: 2026-09-10
---

# meji-media / enquiry-automation

The inbound Christmas-enquiry pipeline on the client's Make.com org: A0 polls
the website database, A1 sends the venue-specific first reply and logs the
lead, A2 stops a lead on reply, A3 sends the three timed follow-ups. Specs in
`specs/4-live/`, scenario ids in `infrastructure.yaml`, client data in the
gitignored `context/`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Family-party exclusion | live | Deployed 2026-09-10 (A1 filter ahead of the sheet write, A3 query condition on the topic column). Synthetic family enquiry ran 1 op and stopped at the filter. | Confirm the next real office enquiry runs full length and the next A3 run picks office rows only, then confirm in the room | - | comms-log 2026-09-09 entry; `.scratch/meji-family-exclusion/` (blueprints + rollback) |
| Venue lookup rebuild (live read of the events table instead of the hardcoded id list) | paused | Approved in principle by Jess 09-01; DEFERRED by Gurmej 09-09 to the end of the year. One new id (151) added to the hardcoded list meanwhile. | Re-raise before next season's dates are entered | Gurmej's call | comms-log 2026-09-09 + Block 32 |
| Second inbound sender (bookings@ router + dual-inbox reply detection) | paused | Mailbox warmed since July; router and A2 dual-inbox work not started. bookings@ must not carry cold campaigns until this ships. | Scope with the owner once the Christmas launch questions are answered | owner priority | `context/inbound-enquiry-multiinbox-scope.md` |
| Booked-lead suppression off the client's own database | blocked | Needs the enquiry_status value that means booked | Ask Jess in the next room message | One line from Jess | comms-log 2026-09-08 "Still unsent" |

## Open decisions / gates

- Live edits to A0-A3 are invasive (real enquirers, peak season): owner per-action go + readiness check, every time.
- The family rows written to the tracking sheet before 2026-09-10 stay as history; the A3 condition makes them inert. Removal is Jess's call.

## Pointers

- Specs: `specs/4-live/a0-mysql-enquiry-poller.md`, `a1-enquiry-follow-up-sequence.md`, `a2-reply-detection-stop.md`, `a3-scheduled-follow-up-steps.md`
- Platform state: `infrastructure.yaml` (production org block)
- Context: `context/comms-log.md` (Block 32 + the 2026-09-09 entry), `context/inbound-enquiry-multiinbox-scope.md`
