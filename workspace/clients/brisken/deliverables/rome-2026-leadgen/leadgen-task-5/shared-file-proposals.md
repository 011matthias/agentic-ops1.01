# Shared-file change proposals

Per the isolation rules, nothing below was edited. Each is a proposal.

## 1. `workspace/clients/brisken/context/lead-generation/Rome-Event/post-event-sequences.md`

Its header says "Tiers 2 to 4 planned, not written", and its Tier-2 paragraph predicts "~20" contacts grouped into "three shared spines: MDH, AI/OnePilot, connectivity".

The segmentation now exists: 18 contacts, five spines. Spines 4 (warm reconnect, no product angle) and 5 (ecosystem) were not anticipated because seven of the eighteen carry no product angle in Dirk's own note.

Proposed: replace the Tier-2 bullet under "Tiers 2 to 4 · structure (to build next)" with a pointer to `output/leadgen-task-5/segmentation.md`, and lift the five-spine table into the file once the copy is approved.

Also worth correcting in the same edit: the file's own internal contradiction. It states "leave Partners and SAP for later ... defers SAP employee (40)" and then lists "the ICD Dashboard follow-up" as a Tier-2 angle. That follow-up is three SAP employees. See `segmentation.md` for how this was resolved.

## 2. `workspace/clients/brisken/context/lead-generation/targeting/sales-nav-add-list-rome2026.md`

Generated 2026-06-29, before any adding happened. Its "Ready to add (48)" section no longer reflects list state, and it predates the Tier-1 / Tier-2 / Tier-3 split entirely.

Proposed: either regenerate it with a `status` column that survives the adds, or retire it in favour of the per-tier roster CSVs (this task ships `tier2-roster.csv` with `salesnav_add` and `linkedin_connect` columns designed to be ticked in place). Keeping both invites drift.

## 3. Planner task "Rome Tier 2 warm-engaged: LinkedIn + Sales Nav"

Its two checklist items are the whole task:

- [ ] add tier 2 leads to the 'TA Cook Rome 26' Sales Navigator list
- [ ] connect on LinkedIn + note

The sibling hottest-5 task instead carries one checklist item per contact plus the note text in the description, which is the better shape: it makes partial progress visible on the board.

Proposed, needing an explicit go-ahead because it writes to Brisken's shared board:

1. Paste the connection-note spec into the task description, mirroring the hottest-5 task.
2. Replace the second checklist item with 18 per-person items (`Connect+note: Georgiou (BSTDB)` and so on). Planner caps checklist item titles at 100 characters; all 18 fit.
3. Leave the Sales Nav item as one line, since it is a single sitting.

Not done. Adding checklist items is a state-changing write to a board Dirk reads, and the task brief limits me to a comment on my own task.
