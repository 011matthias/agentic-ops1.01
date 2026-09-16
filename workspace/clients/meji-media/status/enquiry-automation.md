---
project: meji-media
workstream: enquiry-automation
group: ""
spec: a0, a1, a2, a3
state: live
updated: 2026-09-15
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
| Family-party exclusion | live | Settled 2026-09-11. A1 module 50 blocks only enquiry_type 1 (fail-open); A3 skips rows whose topic is Family Party. Verified on 25 h of real traffic: 26 rows forwarded, 26 runs, 25 full-path, and the one filtered run is a real family enquiry (16076). | Confirm in the room; decide whether enquiry 16046 needs a manual sheet row | - | comms-log 2026-09-09 entry |
| Fail-closed filter defect (2026-09-10) | done | The first filter passed only enquiry_type 0 and silently dropped office enquiry 16046. Corrected the same day at 12:02Z. Root-cause candidate: A0 hand-builds its JSON body with unescaped customer free-text immediately before enquiry_type. | Harden A0's payload construction (escape notes, or send a structured body) | not scheduled | comms-log 2026-09-09 entry |
| Venue lookup rebuild (live read of the events table instead of the hardcoded id list) | paused | DEFERRED by Gurmej 09-09 to the end of the year. An event-151 line was added 09-10 and REVERTED 09-11: the venue list sits inside the deferred scope and is not to be touched. | Re-raise before next season's dates are entered | Gurmej's call | comms-log 2026-09-09 + Block 32 |
| Second inbound sender (bookings@ router + dual-inbox reply detection) | paused | Mailbox warmed since July; router and A2 dual-inbox work not started. bookings@ must not carry cold campaigns until this ships. | Scope with the owner once the Christmas launch questions are answered | owner priority | `context/inbound-enquiry-multiinbox-scope.md` |
| Booked-lead suppression off the client's own database | done | Compiled 2026-09-15. No client ask was needed: `enquiry_status` has no booked value, bookings live in `parties`, joined to the campaign audience on `leader_email`. 35 of the 1,552 campaign people match. All 291 `parties` rows were created in 2026, so the table is this-season-only and a match means "booked for this Christmas", not a historic booking. | Re-pull immediately before any send; the table grew to 291 rows by 09-14 19:30 | - | `context/suppression/2026-09-15-stop-list.md` |
| Christmas stop-list (the gate on Gurmej's re-engagement go) | ready | Compiled 2026-09-15 from a live pull of the three Christmas campaigns and a read of all 355 inbound messages. Two tiers on owner direction: 25 for the account-wide block list (asked out, or dead address), 82 excluded from this wave only (booked, sorted elsewhere, complained, live deals) and deliberately NOT blocked, since blocking a booked customer would kill next season's re-engagement. Net mailable 1,445. | OWNER GO #1 for the remaining 24 block-list writes | owner go | `context/suppression/2026-09-15-stop-list.md` |

## Open decisions / gates

- Live edits to A0-A3 are invasive (real enquirers, peak season): owner per-action go + readiness check, every time.
- The family rows written to the tracking sheet before 2026-09-10 stay as history; the A3 condition makes them inert. Removal is Jess's call, and her stated reason for the exclusion was to keep the sheet clean, so it is worth putting to her.
- Excluding by enquiry type does not fully cover the 13 December date Jess originally named: enquiry 15592 is for that event but typed as office and was automated in August. Closing it needs either a hardcoded event id (the rot the deferred rebuild exists to remove) or the live events read.

## Pointers

- Specs: `specs/4-live/a0-mysql-enquiry-poller.md`, `a1-enquiry-follow-up-sequence.md`, `a2-reply-detection-stop.md`, `a3-scheduled-follow-up-steps.md`
- Platform state: `infrastructure.yaml` (production org block)
- Context: `context/comms-log.md` (Block 32 + the 2026-09-09 entry), `context/inbound-enquiry-multiinbox-scope.md`
