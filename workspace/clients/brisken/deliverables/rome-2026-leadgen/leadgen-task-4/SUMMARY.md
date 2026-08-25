# Task 4 summary

**Planner task resolved:** ID 4 = **"Rome Tier 3 booth/token-network: LinkedIn +
Sales Nav"** (4th open task, top to bottom, in the Lead Generation bucket of the
MARKETING PLAN board).

**What was actually done:** on owner direction mid-session, the work pivoted to
the upstream problem. The task's own target cohort could not be defined without
first fixing the master contact sheet, so the sheet was audited and rebuilt with a
grounded lead classification. The LinkedIn motion itself is not executed and is
now unblocked.

---

## Why the pivot

Task 4 says to run a LinkedIn motion on "the ~90 booth/token-network contacts
(`fob_encoded`)". Those 91 people decompose completely into cohorts the other
three LinkedIn tasks already own:

| Slice of the 91 token-tappers | n | Owner |
|---|---|---|
| The 19 emailed 2026-07-08 | 19 | "Rome Tier 1 leads: LinkedIn + Sales Nav" |
| Dirk's bespoke pack accounts | 12 | "Rome Tier 1 hottest-5: LinkedIn + Sales Nav" |
| Warm, personal note from Dirk | 18 | "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav" |
| Stop list | 15 | never contact |
| `dirk_notes = GA` | 26 | Dirk's hold |
| Ashok Kumar, Accenture | 1 | has its own referral task |

Residual: **zero**. Executing task 4 as written would have sent a second LinkedIn
invite to every person in H5, T1 and T2.

The cohort the tier model calls Tier 3 is a **different, disjoint** set: cold
attendees who never tapped the fob. The sheet had no column saying any of this.

## What was created

| File | What |
|---|---|
| `rome2026-post-event-master-contacts-v2.xlsx` | The corrected master. 298 rows, the 31 original columns untouched in place, 15 new designation columns, colour-coded by class, filterable. |
| `lead-classification.csv` | Flat view sorted by class. The one to open first. |
| `build-master-v2.py` | Reproducible build. Reads the live sheet read-only. Asserts the partition on every run. |
| `designation-scheme.md` | The classification rules and precedence, and why two orderings are load-bearing. |
| `AUDIT-REPORT.md` | 28 confirmed findings, 12 refuted and why. |
| `open-questions-for-dirk.md` | 12 questions, each resolving in one word. |
| `shared-file-proposals.md` | 4 changes to files outside this task dir. None applied. |
| `notes-for-other-tasks.md` | What tasks 1, 5, 7, 20, 22 and 23 need to know. |

## The classification

Grounded on how each group was actually contacted, per owner instruction:
H5 = the bespoke pack handed to Dirk; T1 = the 19 we sent from Dirk's Outlook.

```
H5   11   in Dirk's send pack (To: / Cc: of the six notes)
T1   19   emailed from Dirk's Outlook 2026-07-08
T2   25   warm: a real personal note from Dirk
T3   33   cold: reachable, no note   (29 attended, 4 no-show)
---------
     88   contactable leads

ANON 89   TA Cook withheld the PII. Never contactable.
STOP 69   competitor / SI / never contact
GA   40   Dirk's general-awareness hold
UNREACHABLE 4   named, but no channel of any kind
OWN_TEAM 4  ·  DEFERRED 1  ·  ORGANISER 1  ·  DUPLICATE 1  ·  TEST 1
```

Every row lands in exactly one class, asserted at build time. H5 and T1 are
disjoint, asserted. `lead_type` (prospect / partner_si / sap_internal) runs
orthogonally, so the 17 partners and SAP staff sitting in T2 stay visible and can
never be swept into a treasury pitch.

## The three findings that mattered most

**90 rows are legally uncontactable and nothing said so.** Every blank-name row
has `sponsor_opt_in = No`; in TA Cook's export the 90 non-opted-in attendees are
exactly the 90 with blank names. They declined to share their details with
sponsors. Any Tier-3 plan sized on 65 people was sized on 40 who cannot be
reached. Separately verified: no one appears in both the token registrations and
the opt-out set, so no booth tap is routing around a withheld consent.

**The event organiser was inside the outreach.** Hywel Jones of TA Cook tapped the
fob, has no stop flag, and carries a note, so the old predicates put him in both
the consent blast and the Tier-2 warm sends. The prose doc excluded him; the sheet
never did.

**A "Hi Victoria" would have gone to a different person.** Victoria Boclinca's row
carries `rtsompani@bstdb.org`. The defect came in from TA Cook's export and Dirk's
own copy left it untouched with an uncertainty note. She is held.

Also, already spent: `asako teruki` was stored lowercase and is one of the 19. A
real recipient at NYK read "Hi asako".

## Owner decisions taken, 2026-07-09

- **Data artifacts stay out of git.** `.gitignore` in this directory excludes the
  workbook and the CSV. The build script is committed; both artifacts regenerate
  from it. Same rule as the gitignored `workspace/clients/*/context/` tree.
- **Task 4's LinkedIn motion is paused.** The board gets fixed first, so the next
  session does not re-inherit the H5-inside-T1 and Tier-3-equals-booth-network
  confusions. See `board-rename-proposal.md`.

## Still requiring a manual step

1. **Nothing has been written to the live sheet.** `shared-file-proposals.md` §1
   has the promote sequence. It is held because the workbook is shared with other
   running sessions and co-authored on SharePoint, where a push during
   co-authoring either returns HTTP 423 or gets silently overwritten by the next save.

2. **The board renames are not applied.** `board-rename-proposal.md` carries the
   exact titles, task ids and descriptions. Applying them writes to other Planner
   tasks, which this session's isolation rules forbid, and it is an invasive write
   to a board Dirk reads.

3. **10 rows carry a `send_hold`** and are blocked from every motion until Dirk
   answers `open-questions-for-dirk.md`.

4. **Task 4's own LinkedIn motion is not executed**, by decision. When it resumes:
   the 33 cold T3 people are the only cohort not already owned by another LinkedIn
   task, and **none of the 33 has a LinkedIn URL on file**, so each needs a Sales
   Nav lookup first. Sending connects is an invasive action in a live account and
   needs an explicit go; per the standing rule the agent opens Sales Nav tabs and
   the user clicks Save, never automated connects.
