# Mini-Checkpoint: KIT CDS Tutorien und Anmeldungen

**Date:** 2026-10-27
**Status:** Alle Tutorien-Anmeldungen der ersten Woche erledigt; Einteilung kommt Fr 30.10.
**Type:** mini

---

## Summary
Second week of the personal KIT study-start support (owner's own studies, no client). This stretch covered the HoC lottery results, the welcome-event registration, the IAM lab instructions sent to the owner, the GTI ILIAS join, and calendar-fit star ratings for the Analysis, LA I and GTI tutorials. Each registration had an explicit per-action owner OK and was verified three ways.

## What Was Done
- HoC lottery read out (2 accepted, 2 declined, no waitlist). Accepted course dates entered in the iCloud KIT calendar with alarms. Overfachliche-Qualifikationen options sourced from SPO § 16 and the module handbook ("Einführung in Python" also counts).
- BAföG deadline (31.10.) added. Spring-semester reminder extended with the remaining credit options.
- Welcome-event registration done (owner OK). The QR code was extracted from the confirmation mail, upscaled, verified by decoding, and saved to the owner's cloud drive because the phone is locked out of KIT Exchange.
- IAM lab: the deadline is Thu 29.10. 23:59, not Wed 16:00 (live API). The star rules were read from the frontend bundle (average ≥ 2.5, at least one 5 and one 4, ≤ 50 % equal). The owner rates on the go, from a self-mail sent on the owner's explicit order.
- GTI ILIAS joined (owner OK). Lecture-free GTI dates were excluded via EXDATE and verified against control days.
- Tutorials found to run on the legacy SignMeUp, one event per lecture, all closing Fri 30.10. 10:00. Analysis, LA I and GTI were rated by calendar fit: no lecture clashes, top choices on disjoint times, IAM wish slots kept low. Each one is verified by "Meine Anmeldungen" plus a confirmation mail.
- The first Analysis Übung (30.10.) was added as a single event. The series already carried the three test dates as overrides.

## What Did NOT Work (and why)
- **Finding star buttons by `inner_text()` (tut_rate.py):** the star buttons are `[role=radio]` elements with an empty innerText; the digit lives in `value`. Fixed by reading `value`, on the third run.
- **Moving the Analysis Übung series DTSTART:** the series has RECURRENCE-ID overrides (the test dates), so the guard aborted before any write. A single event for 30.10. was added instead.
- **Reading GTI Übung times from the VVZ / infotut:** infotut still redirects to SS2026 and the WS overview was empty. The times came from the ILIAS course page after joining.

## Current Status
The four first-semester tutorial and lab registrations are submitted, except the IAM lab, which the owner rates personally by Thu 23:59. The calendar reflects every known date. Pending owner decisions: the Programmieren module choice in Campus, the remaining 2 ÜQ credits, LA homework partners, and the BAföG application by Sat 31.10.

## Next Steps
1. Fri 30.10.: read the tutorial assignment mails and enter the three weekly tutorial slots in the calendar.
2. After Fri 30.10. 16:00: check the IAM lab assignment and enter that slot.
3. Programmieren module choice in Campus (IAM vs Programmieren 1), only with the owner's OK.
4. Remind about the BAföG application (Sat 31.10.) and the LA Übungsschein registration once Campus offers it.

## Files to Read First
- Memory `project_kit_studiengangwechsel.md` (sections 23.10. to 27.10.)
- Memory `reference_kit_two_signmeup_instances.md`
