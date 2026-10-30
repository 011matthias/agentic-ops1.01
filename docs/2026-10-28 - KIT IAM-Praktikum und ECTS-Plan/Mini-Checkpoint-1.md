# Mini-Checkpoint: KIT IAM-Praktikum und ECTS-Plan

**Date:** 2026-10-28
**Status:** IAM-Praktikum registered; Friday tutorial/IAM calendar entries pending
**Type:** mini

---

## Summary
Registered the owner for the IAM Rechnerpraktikum (Campus+ SignMeUp) on his order and answered three planning questions (ECTS progress, SEE-profile timing, Analysis 3 vs Analytische Methoden, open ÜQ options) from the live Campus plan, SPO and MHB.

## What Was Done
- IAM Rechnerpraktikum: star ratings from the owner's 26.10. plan submitted, read back via "Bearbeiten" (all six match), confirmation mail received, status "Offen" until the 29.10. 23:59 close. All six groups dry-run against the calendar first (no real clash).
- Calendar: both IAM reminders rewritten to done, alarms removed (owner OK), read back.
- ECTS: semester 1 = 30 LP (Ana 1 9, LA I 9, IAM 6, GTI 6) + 4 HoC ÜQ LP; 109 of 180 LP fixed in the plan, 71 open (SEE+Vertiefung 60, Ana 3/Analytische Methoden 9, ÜQ 2). Orientierungsprüfung (SPO § 8) = Ana 1 + LA I by end of FS 2, passed by end of FS 3.
- SEE: profile fixes with the first module chosen (MHB); three profiles start in WS (now), five in SoSe 2027.
- Analysis 3 / Analytische Methoden: not this semester (MHB recommends Ana 1+2 and LA first; all sample plans put it in FS 3).
- ÜQ: live list of HoC/FORUM offers with free places and no calendar clash; recommended a March HoC block course.

## What Did NOT Work (and why)
- **Campus+ login via the "ANMELDEN" button:** the button only opens a menu; login works by GET `/api/user/oidc-login` then the KIT IdP form.
- **Campus+ FORUM API at `/api/signmeup/procedures/WS2627/FORUM`:** 404; the full list `/api/signmeup/procedures` is public and carries the FORUM groups.
- **FORUM clash check on raw appointments:** a weekly series comes back as ONE appointment spanning the semester, so every course looked like 100+ clashes until the span was expanded into weekly instances.

## Current Status
Personal study organisation (personal-kit, no orchestrator, no infrastructure.yaml). Tutorial assignment for Analysis/LA/GTI arrives Fri 30.10. by mail; IAM group allocation after the 29.10. close. Session-only cron jobs for Friday (11:07, 12:13, 16:23) die with the session.

## Next Steps
1. Fri 30.10.: read the assignment mails, create the weekly series with `cal_series.py` (dry run, `--go`, read back), IAM room from the allocation into LOCATION, report overlaps.
2. LA Übungsschein (T-MATH-102238): register once Campus offers it, only with owner OK.
3. ÜQ 2 LP: owner picks a course (March HoC block recommended); register only with owner OK.
4. Owner: LA homework partners; KIT password rotation.

## Files to Read First
- Memory `project_kit_studiengangwechsel.md` (bullets 26.10. to 28.10.)
- Session scratchpad helpers (outside the repo): `cplus.py` (Campus+ register/readback), `cal_series.py`, `cal_update.py`, `fit_uq.py` in `%TEMP%\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\54274f38-3f22-4f6c-94da-20a15e9623eb\scratchpad\`
