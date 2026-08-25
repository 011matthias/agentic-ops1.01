# Task 5 · Rome Tier 2 warm-engaged: LinkedIn + Sales Nav

**Planner task:** "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav" (id `E3KqsA7guEKQW5vAk7MQKWUAK5ue`), Lead Generation bucket, 5th open task from the top of the Board view.
**Branch:** `leadgen/task-5` · **Worktree:** `../agentic-ops1-leadgen-task-5`
**Date:** 2026-07-09

The task was a two-line checklist with no roster behind it: "add tier 2 leads to the 'TA Cook Rome 26' Sales Navigator list" and "connect on LinkedIn + note". Nobody had ever resolved who Tier 2 actually is. That is now done, and both motions are packaged to run.

## What was created

| File | What it is |
|---|---|
| `tier2-roster.csv` | The 18 contacts, with spine, booth record, prior relationship, LinkedIn URL or Sales Nav search URL, the connection note, and `salesnav_add` / `linkedin_connect` columns to tick in place |
| `segmentation.md` | How 53 candidate rows became 18, what was removed and to which task it belongs, and the five spines |
| `runbook-linkedin-connect.md` | Paste-ready, from Dirk's LinkedIn account. 18 notes, all 198 characters or fewer |
| `runbook-salesnav-add.md` | Three paced batches of six pre-built Sales Nav search URLs, for Matthias's seat |
| `notes-for-other-tasks.md` | Five findings belonging to other Planner tasks |
| `shared-file-proposals.md` | Three proposed edits to shared files, none applied |

## What still needs a human

Both motions are manual by design. LinkedIn bans scripted connecting, and the owner has ruled out driving Brisken's Sales Nav seat aggressively, so nothing was executed.

1. **Sales Nav (Matthias's seat, ~15 min).** Three batches of six search URLs in `runbook-salesnav-add.md`. Open a batch, save each to "TA Cook Rome 26", move on. `.scratch/open_tabs.py` opens the tabs over CDP if you want them opened for you; it only opens tabs.
2. **LinkedIn connects (Dirk's account, ~25 min).** Eighteen invites in `runbook-linkedin-connect.md`. Open profile, Connect, Add a note, paste, Send.
3. **Resolve 14 profiles.** Only four of the eighteen carry a LinkedIn URL on the master sheet (Jellonek, Brueckner, Mehlkopf, Jones). I did not guess the other fourteen. A wrong-person URL here means a connection request with Dirk's name on it landing on a stranger, and web search cannot verify identity on LinkedIn. The Sales Nav search URLs put the operator one click from a visual confirmation against the `job_title` column instead.

## One blocker

**Hold Akash Gupta's invite (#6).** He asked for AI-in-treasury use case documentation on 2026-06-24 and Dirk replied that he would put something together. It does not exist anywhere in the repo two weeks later. His connection note references that material, so sending it now repeats a promise nobody has kept. Everyone else is clear.

## Open questions for Dirk

1. **The 13 SAP partners and consultancies** (Deloitte, KPMG, PwC, Nagarro, Zanders, Tradeweb, LeverX, Eprox, INTENSUM, SINVA, Target Networks) each carry a bare `personal outreach DN` stamp with no substance behind it, and his standing rule defers partners. They are excluded from the 18. Add them to the Sales Nav watch list anyway, since it only tracks? Give them a generic connection note? Or hold them for a separate partner motion?
2. **Is Dirk's LinkedIn on Premium?** Every note is written to 198 characters so it fits the 200-character free-account cap. If he is on free, LinkedIn also caps note-invites at roughly five a month, and the batch will need spreading out or sending without notes.
3. **The ICD Dashboard.** Four SAP people (Lasecki, Hamid, Brueckner, plus Mehlkopf on a general note) hang off Dirk's `DN follow up on ICD Dashboard`. Sebastian Ramos at Tradeweb is Head of ICD and sits in the deferred partner group. Whether these are one thread or two changes who gets connected to whom.

## Judgement calls worth flagging

**18, not "~20".** The task description estimated ~20. Fifty-three rows carry a non-GA, non-stop `dirk_notes`. Thirty-five belong to other tasks: 10 are hottest-5 accounts, 3 were already emailed on 2026-07-08, 7 are no-shows, 2 Dirk himself redirected to GA, and 13 are the deferred partners. The arithmetic is in `segmentation.md`.

**Five spines, not three.** The task anticipated MDH / AI-OnePilot / connectivity. Those cover 11 of the 18. The remaining 7 have no product angle anywhere in Dirk's note: four are warm reconnects (two of them live Equinor customers he just wanted thanked) and three are ecosystem contacts, including a partnership ask to TAC Insights about the Brisken Token. Writing those seven a product note would invent a conversation that did not happen.

**Eight say "at our booth", ten do not.** The `in_our_booth` column decides the opener. Ten of the eighteen attended the conference but never registered at Booth #2. Akash Gupta did not attend at all, so his note opens "sorry we missed each other around Rome". Uffe Teisner-Kjaer already has a call agreed with Dirk for after the summer, so his note points at that call rather than proposing a new one.

**The source doc contradicts itself on SAP employees.** `post-event-sequences.md` defers "Partners and SAP", then names "the ICD Dashboard follow-up" as a Tier-2 angle, which is three SAP employees. I included them: Dirk wrote a specific note against each of those four names, and a named note outranks a blanket category defer. The 13 partners have no such note, which is where I drew the line.

## Verification

- Task ID resolved two independent ways: Microsoft Graph `orderHint` sort over the Lead Generation bucket, and a live DOM read of the Planner Board column. Both put "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav" 5th among open tasks.
- All 18 notes measured: longest is 198 characters, none contains an em-dash or a double-hyphen substitute.
- Segment arithmetic checked: 18 core + 13 partners + 2 GA-redirected + 10 hottest-5 + 3 already-emailed + 7 no-shows = 53, the full non-GA non-stop `dirk_notes` pool.
- Every fact in every note traces to a column in the master sheet or to a logged E-wave reply. No invented values, no invented LinkedIn URLs.
- Nothing was sent, saved, added, or marked complete. No Planner task was modified. No shared file was edited.
