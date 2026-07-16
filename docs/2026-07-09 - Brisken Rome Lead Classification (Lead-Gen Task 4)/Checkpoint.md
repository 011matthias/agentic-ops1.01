# Checkpoint: Brisken Rome Lead Classification (Lead-Gen Task 4)

**Date:** 2026-07-09
**Status:** Classification built and committed. Two actions permission-blocked. Task 4's own LinkedIn motion paused by owner decision pending board rename.

---

## Summary

Planner Task 4 ("Rome Tier 3 booth/token-network: LinkedIn + Sales Nav") could not be executed as written: its stated cohort decomposes entirely into the cohorts the other three LinkedIn tasks already own, leaving zero residual. On owner direction the work pivoted upstream to the master contact sheet, which now carries a computed, mutually exclusive `Tier` column (H5 / T1 / T2 / T3 plus explicit non-lead labels), backed by a six-dimension adversarially-verified audit, 22 verified raw-cell repairs, and build-time assertions.

---

## What Was Done This Session

### Audit
1. Ran a 47-agent workflow across six correctness dimensions (identity, contactability, designation, tiering, flag consistency, cross-source reconciliation). Every non-trivial finding went to an independent agent instructed to refute it, defaulting to refuted when uncertain. **28 findings confirmed, 12 refuted.**
2. Discovered the structural fact behind the whole sheet: **90 rows have no name because TA Cook withheld the PII.** Every blank-name row has `sponsor_opt_in = No`, and in TA Cook's export the 90 non-opted-in attendees are exactly the 90 with blank names. Not enrichable, never contactable as individuals. Verified separately that **zero** people appear in both the token registrations and the opt-out set, so no booth tap routes around a withheld consent.
3. Rejected two proposed repairs that would have corrupted data: a fabricated email address (`isabelle.badoux@sanofi.com`, present in no source file) and a merge that would have re-identified an anonymized opt-out row into a named booth registrant.

### Classification
4. Built `Tier` as a mutually exclusive partition over all rows, grounded on how each group was actually contacted rather than on a company-name match. H5 = the 11 literal `To:`/`Cc:` addresses of Dirk's bespoke send pack. T1 = the 19 sent from Dirk's Outlook 2026-07-08. H5 and T1 disjoint, asserted.
5. Added `lead_type` (prospect / partner_si / sap_internal) orthogonally, so the 17 partners and SAP staff sitting in T2 stay visible and can never be swept into a treasury pitch.
6. Added 13 supporting columns: `Tier_reason`, `t3_branch`, `priority_account`, `canonical_account`, `contactability`, `seniority`, `salutation_first`, `booth_network_send`, `email_owner`, `linkedin_owner`, `send_hold`, `is_customer`, `duplicate_of`.

### Repairs (22, every new value traced to a source file)
7. Names: `Kiosses Christos` reversed; `asako teruki` lower-cased (she is one of the 19, so a real recipient at NYK read "Hi asako" on 8 July).
8. Titles: 4 adopted from the person's own booth self-entry, which beats TA Cook's registration value (Snersrud is Global Head of Payments, not Manager Cash Management); acronym repairs (`Gm`, `It`, `Uk&i`, `Apac`); a literal pipe removed from a title; an all-lowercase title title-cased.
9. SLB cross-wire: Galera's `alt_email` still held Morrison's address, Morrison's `alt_email` was a copy of his own, and Morrison's booth timestamp was actually Galera's.
10. Customer flags: 4 `icdportal.com` rows marked `Yes` by domain inference, corrected to Dirk's own `No (SQL)`. **`is_customer = TRUE` holds for exactly 2 rows, both at Equinor.**
11. Christian Forst: promoted his corporate address (he tapped the fob twice, once with gmail, once corporate).

### Caught before anyone was contacted
12. **Hywel Jones, the TA Cook event organiser**, tapped the fob, has no stop flag and carries a note, so the old predicates put him inside both the GDPR consent blast and the Tier-2 warm sends.
13. **"Hi Victoria" would have delivered to a different person.** Victoria Boclinca's row carries `rtsompani@bstdb.org`. The value came in from TA Cook's export and Dirk's own edit pass left it untouched.
14. **The booth-network draft called four people "active customers"** and routed them to a separate template. None is a customer.

### Owner rulings applied (10)
15. Boclinca: not in the token CSV, so never at the booth and no self-entered fallback. Primary email cleared into `alt_email`, excluded from email outreach.
16. Dogan Yesil: the `needs_corporate_email` hold was **wrong**. He typed his hotmail into the Brisken Token himself. The free-mail rule now fires only on addresses **absent from the token CSV**. Same fix cleared Forst and Katkoria.
17. Steinar salutes as `Steinar`. GA means not a warm lead. Domenic by first name. Ashok Kumar has already responded, so he moved out of `DEFERRED` into `T2` with `email_owner = dirk_referral_thread` (`DEFERRED` is now empty). Nedhal kept as the single T3 no-show. Hywel confirmed as `ORGANISER`.
18. **Holds dropped from 7 to 3**: Boclinca (excluded), Leonid (asked Dirk), Domenic (no channel of any kind).

### Shipped
19. Planner task created, assigned to Dirk, verified by read-back: **"Run Dirk's personal outreach to the 17 Rome partner and SAP contacts"**, 17-item checklist, explaining that his personal note is what overrides his own partner-deferral rule and that these must never receive the treasury sequence.
20. Email sent from `Matthias.Silva@brisken.com` to `dirk.neumann@brisken.com` asking which address to use for Leonid Opanasyk (DSV). Verified in Sent Items; Outbox and Drafts clear.
21. `TASK-NAMING-STANDARD.md` §2/§3 rewritten to the H5/T1/T2/T3 grammar with the eight-task table. `post-event-sequences.md` segmentation and no-show sections rewritten against live data. `account-shell.md` §1a now holds Bill Askew's full contact record.

---

## Key Decisions Made

### H5 is a roster, not a company rule
- **Choice:** H5 membership = the literal `To:`/`Cc:` addresses of the six notes in `dirk-send-pack/README.md`.
- **Rationale:** A company-name match sweeps in 13 people who were never in the pack (Ana Matos, both Katkorias, Christian Forst, Miguel Carvalho, Lukas Blauth, Kenneth Bogert, five anonymized rows, Domenic). They are real leads, but T3. The `priority_account` overlay keeps the account visible without promoting the person into a send they were never part of.

### A personal note from Dirk outranks his own partner-deferral
- **Choice:** `T2` (personal note) is evaluated before `DEFERRED` (SAP partner/employee/analyst).
- **Rationale:** Dirk's own Tier-2 roster names people at Eprox, Nagarro, SAP and Zanders, all typed `SAP partner` or `SAP employee`. Deferring first collapses T2 from 24 to 8 and silently drops four people he wrote notes for. Note-first yields T2 = 24 and `DEFERRED` = 0.

### A booth self-entered address is the verified channel
- **Choice:** free-mail addresses present in `brisken-token-registrations.csv` carry no hold.
- **Rationale:** The person typed it themselves at the booth; it is the channel they chose and it carries the `direct_booth` lawful basis. Conversely, no booth registration means no fallback: an unverifiable address cannot be used and no email goes out (Boclinca).

### The live sheet is truth; the snapshot proves intent
- **Choice:** build reads the live workbook; a pinned pre-drift snapshot exists only so `report_drift` can diff and fail on any removal not in `INTENTIONALLY_REMOVED`.
- **Rationale:** 8 rows were deliberately removed by a parallel session (non-attendees: Askew + 3 Shell cc's, Akash Gupta, Isabelle Badoux, Adela Dolezalova, Maria Moeller). I initially misread this as a regression. The allowlist makes intent explicit and still catches a real one.

### PII stays out of git
- **Choice:** commit the build script and the docs; gitignore the workbook, the CSV and the snapshot.
- **Rationale:** 298 contacts' names, emails and LinkedIn URLs. Git history is durable. Both artifacts regenerate from the committed script.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `output/leadgen-task-4/build-master-v2.py` | Created | Reproducible build. Partition + dead-key + drift assertions. **(branch `leadgen/task-4`)** |
| `output/leadgen-task-4/designation-scheme.md` | Created | Tier rules, precedence, and why two orderings are load-bearing |
| `output/leadgen-task-4/AUDIT-REPORT.md` | Created | 28 confirmed findings, 12 refuted and why |
| `output/leadgen-task-4/open-questions-for-dirk.md` | Created | The questions that gate the held rows |
| `output/leadgen-task-4/board-rename-proposal.md` | Created | Exact Planner titles, ids, descriptions (unapplied) |
| `output/leadgen-task-4/shared-file-proposals.md` | Created | 4 changes outside the task dir |
| `output/leadgen-task-4/notes-for-other-tasks.md` | Created | What tasks 1, 5, 7, 20, 22, 23 need to know |
| `output/leadgen-task-4/SUMMARY.md` | Created | Task-4 summary |
| `output/leadgen-task-4/.gitignore` | Created | Keeps the workbook / CSV / snapshot out of git |
| `workspace/clients/brisken/TASK-NAMING-STANDARD.md` | Modified | §2/§3 rewritten to H5/T1/T2/T3; eight-task table (untracked file) |
| `.../Rome-Event/post-event-sequences.md` | Modified | Segmentation + no-show sections rewritten against live data |
| `.../accounts/account-shell.md` | Modified | §1a: Bill Askew's contact record after his row left the sheet |
| `.../drafts/rome-booth-network-touch.md` | Modified | Removed the false "active customers" split; corrected names/titles |
| `.../drafts/ask-dirk-leonid-dsv-address.md` | Created | The ask, now SENT |
| `~/.claude/.../memory/project_brisken_rome_tier_classification.md` | Created | Tier grounding + the two traps |
| `~/.claude/.../memory/reference_booth_self_entered_email_is_verified.md` | Created | Booth address rule |
| `~/.claude/.../memory/reference_brisken_microsoft_planner.md` | Modified | Marked tier model superseded; board still carries old titles |

---

## Current Status

Branch `leadgen/task-4`, worktree `agentic-ops1-leadgen-task-4`, **5 commits, working tree clean**. Build passes all assertions against the live 290-row sheet.

Final counts: **H5 11, T1 19, T2 24, T3 30 = 84 leads.** Non-lead: `ANON` 89, `STOP` 69, `GA` 40, `OWN_TEAM` 4, `UNREACHABLE` 1, `ORGANISER` 1, `DUPLICATE` 1, `TEST` 1. `booth_network_send` = 74.

All 84 leads are emailable today (28 of 30 in T3). LinkedIn is the bottleneck: **55 Sales Nav lookups needed** (H5 4, T1 9, T2 14, T3 28).

Platform: no `platform` section in `infrastructure.yaml` for brisken; p2 lead-gen is manual-first (1:1 from Dirk's Outlook), so no ops-limit check applies.

---

## Next Steps

1. **Retire or fix `.scratch/merge_contacts.py`.** It rebuilds the workbook from raw sources, knows nothing about the `Tier` column, and drops every manually-added row. Whoever runs it next wipes this work. This is the single highest-risk open item.
2. **Grant permission and promote the workbook** over `.../event-admin/rome2026-post-event-master-contacts.xlsx` (blocked: irreversible, gitignored, SharePoint co-authored). Backup of the current 290-row file is in `.scratch/task4/`.
3. **Grant permission and apply the 8 Planner renames** from `.scratch/task4/renames.json` (blocked: external-system write to tasks this session did not create). The board still says "Rome Tier 1 hottest-5" and "Rome Tier 3 booth/token-network", the two phrases that caused this detour.
4. **Run the 55 Sales Nav lookups.** Agent opens the Sales Nav people-search tab per lead; user clicks Save to "TA Cook Rome 26". Never automate connects.
5. **Await Dirk's reply on Leonid Opanasyk's DSV address** (sent 21:18). On his answer, clear the `owner_decision` hold.
6. **Resume Task 4's LinkedIn motion** once the board is renamed (paused by owner decision).
7. Domenic (JTI) has no email, phone or LinkedIn. Either enrich or drop the row.

---

## Context for Next Session

### Files to Read First
- `output/leadgen-task-4/designation-scheme.md` (branch `leadgen/task-4`) — the rules
- `output/leadgen-task-4/lead-classification.csv` — the flat view, sorted by Tier (gitignored; regenerate with `uv run output/leadgen-task-4/build-master-v2.py`)
- `output/leadgen-task-4/open-questions-for-dirk.md`
- `workspace/clients/brisken/TASK-NAMING-STANDARD.md` §2/§3
- `workspace/clients/brisken/context/lead-generation/accounts/account-shell.md` §1a

### Open Questions
- Leonid Opanasyk (DSV): corporate address, or send to the personal one he gave at the booth, or skip? **Asked Dirk 2026-07-09 21:18.**
- Domenic (JTI): surname and address? Currently `UNREACHABLE`.
- Asako Teruki: is her surname `Teruki` or `Tateno-Teruki` (her LinkedIn slug says the latter)?
- Should `merge_contacts.py` be retired outright, or taught the `Tier` column?

### Working Notes
- **The 8 removed rows were intentional**, not a regression. I initially wrote alarmist commit messages and a shared-file proposal claiming data loss. A parallel session (S9) had added Badoux + the two Zalando referrals as non-attendees; those and the Shell/Maersk inbounds were then correctly purged because they never attended Rome. Their details are preserved in `account-shell.md` §1a and the account notes.
- **Failed approach:** classifying against the pinned 298-row snapshot. Correct approach: build from the live sheet, keep the snapshot only to prove every departure was deliberate (`INTENTIONALLY_REMOVED`).
- **Two of my findings were wrong and the owner caught both**: I claimed the H5 Roche note carries an attached deck (it has `Attach: none`), and I flagged Dogan Yesil's hotmail as needing a corporate address when he had self-entered it at the booth.
- The audit's synthesis agent proposed a **fabricated** email (`isabelle.badoux@sanofi.com`). It was rejected only because every new value was checked against a source file before being applied. A neighbouring value that looked equally invented (`christian.forst@adidas-group.com`) turned out to be real.
- The old `hot` predicate carries four dead tokens that match nothing in the sheet (`vw `, `japan tobacco`, `london stock exchange`, `refinitiv`), reading as coverage it does not have.
- Row citations by line number are unsafe: ~27 cells contain embedded newlines, so a line-based grep miscounts. Every fix keys on `email`.

### Reference Materials
- Planner: plan `MARKETING PLAN` `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, bucket `Lead Generation` `gyfptEwAwUiJLXfd6aMrYWUABZRr`
- New task created: `S-t9htVQa0WgWqw5zGW0j2UALkug` (assigned to Dirk `3f083bcb-a186-44d0-81a0-918c73b145d9`)
- Rename payload: `.scratch/task4/renames.json`
- Task-4 payload: `.scratch/task4/dirk_t2_partners_task.json`
- Pre-drift snapshot: `.scratch/task4/master-PRE-DRIFT-298rows.csv`

---

## How to Continue

`git worktree list` already has `agentic-ops1-leadgen-task-4` on branch `leadgen/task-4`. Run `uv run output/leadgen-task-4/build-master-v2.py` from the repo root; it reads the live sheet, prints a drift report, and regenerates the workbook and CSV. Read `designation-scheme.md`, then `lead-classification.csv`. The two blocked actions need an explicit permission grant.

---

## Strategic Feedback

### What Worked Well This Session
- The owner interrupting mid-turn with corrections ("the contacts were purposefully removed", "what is the H5 Roche note? Did dirk say that?") caught two wrong findings before either reached a client-facing artifact. Short, specific challenges to a claim are worth more than a long review pass.
- Answering ten open questions in one message let the whole hold list clear in a single rebuild.

### Suggestions
- The eight-task structure (four tiers x two channels) only became legible once the tiers were named on the board. Renaming the Planner tasks is cheap and prevents the next session inheriting the same "Tier 1 hottest-5" contradiction. It is currently the only thing gating Task 4.

### System Health
- Build-time assertions caught what review would not: the partition assert caught the live sheet moving mid-build, and the dead-lookup-key assert caught a fix silently doing nothing (`sultan.alqahtani@mobily.com.sa`, wrong address, repaired by the acronym pass anyway). A named assertion is cheaper than a paragraph of prose claiming correctness.
- Autonomy score: 5 human interventions this session (elevated — run `/system-dev` to close gaps). Three became friction rows; two were healthy direction-setting.
- The permission classifier blocked two irreversible actions that the agent had itself flagged as needing an explicit go. Defence in depth worked.
