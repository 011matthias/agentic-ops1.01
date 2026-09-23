---
project: meji-media
workstream: enquiry-automation
group: ""
spec: a0, a1, a2, a3
state: live
updated: 2026-09-23
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
| Booked-lead suppression off the client's own database | done | Compiled 2026-09-15. No client ask was needed: `enquiry_status` has no booked value, bookings live in `parties`, joined to the campaign audience on `leader_email`. 35 of the 1,552 campaign people match. All 291 `parties` rows were created in 2026, so the table is this-season-only and a match means "booked for this Christmas", not a historic booking. | Re-pulled 2026-09-23 immediately before the wave went live: 318 rows / 291 valid emails, **28 new bookings since 09-14**, one of them in the send audience and dropped. Read path had to be rebuilt first (see `infrastructure.yaml` 8974201) because the old one rode the injection hole closed on 09-21. | - | `context/suppression/2026-09-15-stop-list.md` |
| Christmas stop-list (the gate on Gurmej's re-engagement go) | ready | Compiled 2026-09-15 from a live pull of the three Christmas campaigns and a read of all 355 inbound messages. Two tiers on owner direction: 25 for the account-wide block list (asked out, or dead address), 82 excluded from this wave only (booked, sorted elsewhere, complained, live deals) and deliberately NOT blocked, since blocking a booked customer would kill next season's re-engagement. Net mailable 1,445. | Done. All 25 tier-1 writes confirmed live on the account block list (read back 09-23, 25 of 25 present). The 82 held remain deliberately unblocked. | - | `context/suppression/2026-09-15-stop-list.md` |
| Christmas re-engagement wave, segment A (warm) | live | **ACTIVATED 2026-09-23** after a 15/15 B5 readiness check. Campaign `62fc56ff`, 775 people, 3 touches (delays 5 / 8 / 0), sender `gurmej@mejimedia.com` only at 75/day, stop-on-reply on. Copy approved by Gurmej 09-22 16:38 unedited. Single sender is deliberate: 774 of 775 were last emailed from that address (to 2026-08-27) and the copy resumes that thread, so a domain switch would break it. Costs capacity, 90/day not 180. | Read back the first real sends for rendering and bounce rate; touch 1 completes ~10-07 | - | comms-log 2026-09-23 |
| Christmas re-engagement wave, segment B (dormant) | paused | Built and loaded (`26a0d9eb`, 37 people) but HELD IN DRAFT on owner decision 09-23. Its source cohort bounced **50.0%** (38 of 76) on the real Nov-2025 send and is 10 months stale, with 29 of the surviving 37 unverifiable by NeverBounce, so it carries most of the bounce risk for 4.5% of the audience. | Decide after warm's real bounce rate is visible | owner call | comms-log 2026-09-23 |
| Corporate / Deciders cold track (P2) | idle | Gurmej chased this 09-22. Nothing has sent since **2026-07-06** (A) / **07-07** (B); Big Companies stopped on bounce rate in January. He cleared every gate himself (version-b + c 09-09, version-a 09-14, `big-companies-uk=retire`). Lifetime 3,906 sent, 9 replies, 0 opportunities. Mailboxes are healthy (3x mejievent.com, warmup 100, 90/day) and are a different domain from the wave, so the tracks do not compete. | Source fresh lists for A and B, swap in approved copy; C needs his dream-account list | NeverBounce down to 118 credits; B is the bounce-prone segment | comms-log 2026-09-23 |

## Open decisions / gates

- Live edits to A0-A3 are invasive (real enquirers, peak season): owner per-action go + readiness check, every time.
- The family rows written to the tracking sheet before 2026-09-10 stay as history; the A3 condition makes them inert. Removal is Jess's call, and her stated reason for the exclusion was to keep the sheet clean, so it is worth putting to her.
- Excluding by enquiry type does not fully cover the 13 December date Jess originally named: enquiry 15592 is for that event but typed as office and was automated in August. Closing it needs either a hardcoded event id (the rot the deferred rebuild exists to remove) or the live events read.

## Pointers

- Specs: `specs/4-live/a0-mysql-enquiry-poller.md`, `a1-enquiry-follow-up-sequence.md`, `a2-reply-detection-stop.md`, `a3-scheduled-follow-up-steps.md`
- Platform state: `infrastructure.yaml` (production org block)
- Context: `context/comms-log.md` (Block 32 + the 2026-09-09 entry), `context/inbound-enquiry-multiinbox-scope.md`
