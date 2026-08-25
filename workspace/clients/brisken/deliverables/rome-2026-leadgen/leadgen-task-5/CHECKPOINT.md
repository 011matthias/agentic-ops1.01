# Checkpoint: leadgen task-5 (Rome Tier 2 warm-engaged: LinkedIn + Sales Nav)

**Date:** 2026-07-11 · **Branch:** `leadgen/task-5` · pushed to origin (3 commits + follow-ups).
Task-scoped checkpoint (not the shared `/comd_checkpoint`, which writes to `docs/sessions/` and would collide with the parallel task sessions).

## State: DONE, delivered, pushed

Resolved who Tier 2 is (the Planner task shipped two checklist lines and no roster): 18 contacts, five spines, from 53 candidate rows minus 35 that belong to other tasks. Then resolved direct LinkedIn profile URLs for the stragglers Sales Nav search misses.

### Deliverables in `output/leadgen-task-5/`
- `tier2-roster.csv` — 18 rows; spine, booth record, on-file LinkedIn URL, Sales Nav search URL, connect note, and `resolved_linkedin_url` / `resolve_confidence` / `resolve_note` from the lookup pass.
- `segmentation.md` — how 53 became 18.
- `runbook-linkedin-connect.md` — 18 paste-ready notes, all under 200 chars, from Dirk's account.
- `runbook-salesnav-add.md` — three batches of six Sales Nav search URLs, Matthias's seat.
- `resolved-profiles.md` — 14 of 18 resolved to a direct profile; 2 on-file URLs corrected; 4 have no public profile.
- `notes-for-other-tasks.md`, `shared-file-proposals.md`, `SUMMARY.md`.

### Profile lookup outcome (user has been saving to the list)
- 14 direct profile URLs found, verified on company + treasury/SAP role.
- Corrected: Mehlkopf `/in/thomas-mehlkopf` -> `-5231477`; Jones `/in/h-lewis-jones` -> `/in/hywel-lewis-jones-7b622a109`.
- Eyeball: Georgiou's profile is IT Director, not treasury (right person, medium confidence).
- No public profile (skip, do not guess): Victoria Boclinca, Sergey Timeshov (BSTDB), Jeffrey Lasecki (SAP), Njal Fjotland (Equinor).

## Carry-over reminders
- **Akash Gupta**: fine to add to the Sales Nav list; HOLD his connection request until the AI-in-treasury material Dirk promised him on 2026-06-24 exists (still no build evidence in repo).
- **Open questions for Dirk** (in SUMMARY.md): the 13 deferred SAP partners, is Dirk's LinkedIn Premium or free, is the ICD Dashboard one thread or two.

## Data-integrity finding (affects every downstream Rome tier)
The master sheet `rome2026-post-event-master-contacts.xlsx` was **regenerated 2026-07-10 13:42** by another process: 298 -> 290 rows, and the `post_event_outreach` column (which flagged the 19 Tier-1 "Booth follow-up sent 2026-07-08") is **gone**. Any tier that dedups against Tier-1 via that column will silently fail. Dedup by explicit name list instead. The sheet is a moving target across the parallel sessions; re-read it fresh each session.

## Next: Tier 3 LinkedIn
Continuation prompt written to `CONTINUE-T3-LINKEDIN.md` (this directory). T3 candidate pool sized at ~68 fob_encoded rows after stop + Tier-2 removal, still including the 19 Tier-1 and hottest-5 (the wiped status column blocked auto-subtracting them); true pool after dedup is roughly 45. 23 of the 68 have no LinkedIn URL on file, so a profile-lookup pass like this session's is needed.
