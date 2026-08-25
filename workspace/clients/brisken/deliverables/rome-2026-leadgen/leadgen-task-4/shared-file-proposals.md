# Proposed changes to files outside this task directory

Per the parallel-execution isolation rules, nothing below has been applied. Each
is a proposal.

---

## 0. URGENT: the live master lost 8 rows at 18:46 today

Not caused by this session. This session never wrote to the file.

Between 18:33 and 18:46 on 2026-07-09 something regenerated
`rome2026-post-event-master-contacts.xlsx` from the raw sources. Row count went
from 298 to 290. Every dropped row is a manually-added non-attendee, so a rebuild
straight from TA Cook's export plus the token registrations would produce exactly
this loss.

Dropped:

| Person | Company | Why it matters |
|---|---|---|
| William Askew | Shell | **Has a call booked with Dirk on 27 July.** |
| Alex Kerr, Frank Appelman, Kei-Fai Liew | Shell | The cc's on Askew's thread. |
| Akash Gupta | Maersk | Emailed us; we owe him the AI-treasury docs. |
| Isabelle Badoux | Sanofi | Sales Nav research add, 2026-07-09. |
| Adela Dolezalova, Maria Moeller | Zalando | Referred by Lokesh Doggala on 2026-07-09. |

Also reverted on surviving rows: company-name casing (`Ciments de L'Atlas` back to
`Ciments De L'atlas`, `Wiener Städtische Versicherung AG` back to `... Ag`), 13
`country` values, and one `no_show` flipped from `Yes` to `No`.

`workspace/clients/*/context/` is gitignored, so **there is no git recovery.** The
complete 298-row data survives in two places, both produced by this session:

- `output/leadgen-task-4/master-snapshot-2026-07-09T1833-298rows.csv` (pinned, pre-drift)
- `output/leadgen-task-4/rome2026-post-event-master-contacts-v2.xlsx` (298 rows, repaired, classified)

`build-master-v2.py` now builds from the pinned snapshot and prints a drift report
against the live sheet on every run, so this cannot pass unnoticed again.

**Recommended:** find which session or script rewrote the workbook before anyone
restores anything, otherwise the same regeneration will drop the rows again. The
likely culprit is a re-run of `.scratch/merge_contacts.py`, whose `EXTRA_LEADS`
list carries only Akash Gupta and which has no knowledge of the Shell, Sanofi or
Zalando rows.

## 1. Promote the corrected master over the live context sheet

**File:** `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx`

The live sheet was read but never written. The corrected version is
`output/leadgen-task-4/rome2026-post-event-master-contacts-v2.xlsx`: same 298
rows, same 31 original columns, plus 15 designation columns, plus 20 verified
raw-cell repairs.

Promoting it is a copy. It is deliberately not done here because the file is
shared with other running task sessions, and because it is also mirrored on
SharePoint where Dirk co-authors it. A SharePoint push while he has it open
returns HTTP 423, or worse, his next save silently overwrites the push.

Recommended sequence, on your go:
1. Confirm nobody has the workbook open.
2. Copy v2 over the context file.
3. Push to SharePoint and verify by re-listing the file size, not by trusting the
   HTTP 200.

The 20 raw-cell repairs are listed in the build log and every new value traces to
a source file. Two candidate repairs were rejected: a fabricated email address for
Isabelle Badoux, and a merge of an anonymous Hitachi opt-out row into a named
booth registrant.

## 2. Correct the booth-network touch draft

**File:** `workspace/clients/brisken/context/drafts/rome-booth-network-touch.md`

The "Active customers" table lists Erik Snersrud, Hege Lundemo Larsen, Ian
Haegemans and asako teruki, and routes them to a different template on the basis
that `brisken_customer = Yes`. None of the four is marked `Yes` in the master;
all four are `No (Lead - ...)`. The master is correct.

Two edits:
- Remove the "Active customers" split. All 19 get the same template.
- Fix `asako teruki` to `Asako Teruki`.

Also stale in the same file: the Excluded section's counts (`Tier 2, Dirk personal (8)`,
`Stop (15)`) describe the fob subset, not the whole sheet, and read as global counts.

## 3. Correct the segmentation plan's no-show count

**File:** `workspace/clients/brisken/context/lead-generation/Rome-Event/post-event-sequences.md`

States "15 rows carry `no_show` = Yes". The sheet now has 18. The drift is three
prospect rows added after the doc was written. The doc is stale; the sheet is right.

## 4. Retire the company-substring "hot" predicate

**Files:** `.scratch/xtab.py` and any downstream copy.

`hot = company contains volkswagen|vw |jti|japan tobacco|roche|adidas|lseg|...`
matches 24 rows. Dirk's actual send pack has 11 addresses. The predicate also
carries four dead tokens that match nothing in the sheet (`vw `, `japan tobacco`,
`london stock exchange`, `refinitiv`), which reads as coverage it does not have.

H5 membership should be read from the send-pack roster. Company membership
belongs in `priority_account`, which is what it now is.
