# Task 7 · Rome Tier 3 booth/token-network: LinkedIn + Sales Nav

**Planner task:** "Rome Tier 3 booth/token-network: LinkedIn + Sales Nav" (id `a7c6yU3_DEOjqnG08LBR22UAL5yv`), Lead Generation bucket. Resolved by id; on the live board it sits 5th among open tasks, not 4th as the brief expected.
**Branch:** `leadgen/task-7` · **Worktree:** `../agentic-ops1-leadgen-task-7` · **Date:** 2026-07-11

**Why task-7, not the briefed task-4:** the brief said `leadgen/task-4` with "confirm before naming". Confirmation failed twice: the board position drifted from 4 to 5, and both `leadgen/task-4` (tier-classification session, committed 2026-07-09/10) and `leadgen/task-5` (Tier-2 session) already hold other tasks' outputs, including files with the same names this task produces. Task numbers here are session identifiers, not live board positions; 7 was the next free one.

## What was created (all in `output/leadgen-task-7/`)

| File | What it is |
|---|---|
| `tier3-roster.csv` | 29 contacts: segment, booth record, verified LinkedIn URL or Sales Nav search URL, rotating connect note, `salesnav_add` / `linkedin_connect` columns to tick in place |
| `segmentation.md` | How 91 fob-encoded rows became 29 templated connects + 11 routed + 51 removed, name-matched against every prior tier |
| `runbook-linkedin-connect.md` | 29 paste-ready notes from Dirk's account, all 160 characters or fewer, booth opener, no pitch |
| `runbook-salesnav-add.md` | Five paced batches of Sales Nav search URLs for Matthias's seat |
| `resolved-profiles.md` | 24 of 29 resolved to a verified direct profile (2 new finds); 5 with no verifiable public profile; 1 suspect on-file URL |
| `notes-for-other-tasks.md` | Six findings belonging to other Planner tasks |
| `shared-file-proposals.md` | Three proposed edits to shared files, none applied |

## The one judgement call: 29, not ~45

The brief estimated ~45 after name-dedup. The name-dedup itself reproduces the brief's arithmetic (69 fob survivors of stop, minus 19 Tier-1, 8 Tier-2, 8 hottest-5, 1 duplicate = 40-ish). This session then routed 11 more out: Ashok Kumar (live Accenture referral, own task) and 10 partners carrying Dirk's `personal outreach DN` note, whose emails are already in his personal send pack. Both Planner siblings define the segment as "no specific note", and a templated token note landing next to Dirk's personal email would read as a colder duplicate. If Dirk wants the 10 partners connected on LinkedIn anyway, they are enumerated in `notes-for-other-tasks.md` §1 and the note template applies unchanged.

## What still needs a human

Both motions are manual by design (LinkedIn bans scripted connecting; the owner ruled out driving the Sales Nav seat aggressively). Nothing was executed: no invite sent, no lead saved, no tab opened, no Planner change.

1. **Send with notes.** Resolved 2026-07-11: Dirk's LinkedIn is Premium per Matthias, so 29 noted invites at ~20/day is the plan. The runbook keeps a ten-second counter check (300-character note box = Premium) before the first batch as the safety net. This also unblocks the Tier-2 runbook, which was written to the same question.
2. **Sales Nav adds (Matthias's seat, ~25 min).** Five batches in `runbook-salesnav-add.md`; save each to "TA Cook Rome 26". `.scratch/open_tabs.py` opens a batch of tabs over CDP if wanted; one batch at a time, six parallel search tabs tripped the throttle once before.
3. **LinkedIn connects (Dirk's account, ~2 days at 20/day).** 29 invites in `runbook-linkedin-connect.md`. Five contacts have no verified profile and must be identity-checked in Sales Nav first; five more are marked eyeball-first.

## Open questions for Dirk

1. **The 10 `personal outreach DN` partners** in the fob set: after his personal emails land, do they also get a LinkedIn connect, and from which motion? (Same open question the Tier-2 session filed; it now blocks two rosters.)
2. **Lukas Blauth (Roche)**: the on-file LinkedIn URL looks wrong (see `resolved-profiles.md`). Worth confirming who captured it, since the same row sits on a hottest-5 account.

## Verification

- Task resolved by exact id from the brief; description and both checklist items read via Graph; siblings (T3 email, GDPR consent) read for segment definition and separation of concerns.
- Master sheet read fresh 2026-07-11 (290 rows, the 2026-07-10 regeneration). Dedup by explicit name lists only; the `Tier` column was used as a cross-check and agreed: the 29 survivors are exactly the sheet's GA (26) + T3 (3) fob rows, zero prior-tier rows slipped through.
- Segment arithmetic: 15 stop + 8 hottest-5 + 19 Tier-1 + 8 Tier-2 + 1 duplicate + 11 routed + 29 connects = 91 fob rows.
- All 29 notes measured at 160 characters or fewer; zero em-dashes anywhere in the deliverables; no consent framing in any note.
- Every profile URL in `resolved-profiles.md` traces to a named search corroboration (company + role), or the contact is explicitly marked unverifiable; no invented URLs.
- Nothing sent, saved, added, or marked complete; no shared file edited; no other Planner task touched.

## Paste-ready Planner status comment

> Prep complete, nothing sent yet. Roster: 29 booth/token-network contacts after name-dedup against hottest-5 / Tier-1 / Tier-2 (the sheet's status column is gone, so dedup ran on explicit name lists) and after routing 11 personal-note holders (10 partners + Ashok) to their own motions. 24 of 29 have verified LinkedIn profile URLs, 5 are Sales Nav search only. Runbooks ready on branch leadgen/task-7, folder output/leadgen-task-7/: Sales Nav adds in five batches (Matthias seat, ~25 min), LinkedIn connects from Dirk's account paced 20/day (~2 days), notes under 200 chars, booth opener, relationship only, no pitch, no consent language. Dirk's account being Premium (confirmed by Matthias 2026-07-11), the invites go out with notes; the runbook keeps a ten-second Premium counter check before the first batch.
