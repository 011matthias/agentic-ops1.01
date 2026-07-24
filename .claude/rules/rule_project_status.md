# Project Status Files (status-of-elements convention)

**Convention (Layer 1, non-blocking).** Every discrete workstream inside
a client carries ONE maintained status file describing the status of the
individual elements inside it, kept current as context for further work.
Shared context that belongs to a whole group (a vision, a marketing plan)
lives in a group general-reference file, never duplicated into each
workstream file. This rule is the source of truth for the convention; the
step-by-step is in [[skil_project-status]].

Two halves, kept separate on purpose: **updating** a status file is
agent discipline (fires at decision time when you start/wrap work; no
blocking hook, by design); **detecting** that one has gone stale is
automated, so currency does not depend on recall. A SessionStart sweep
(`project_status.py --sweep-stale`, wired in `wire-hooks.py`) surfaces
stale/malformed files every session, fail-open. A stale file that
misleads with confidence is the failure mode this convention most has to
avoid; the sweep is the recurrence-kill, and the right response to a
flagged file is to update it in place or delete it (W1 §4), never nurse a
rotting one.

## The home

`workspace/clients/{client}/status/` — tracked (NOT under the gitignored
`context/`), beside `infrastructure.yaml` and `PROJECT-BOUNDARIES.md`.
Internal projects carry the same convention at
`workspace/projects/{project}/status/` (first: upwork-independence,
2026-07-22); `tools/project_status.py` resolves both roots, clients first.

- One file per workstream: `{spec-id}-{slug}.md` (e.g. `p2-rome.md`,
  `p1-expense-reconciliation.md`).
- One general-reference file per group that has cross-workstream shared
  context: `{group}-general.md` (e.g. `p2-lead-gen-general.md`). A
  standalone project with no siblings gets no general ref.

This is a sanctioned client sub-home. It is documented HERE rather than in
the W2 home map ([[rule_file_placement]] §2) only because the W2 rule is
mid-flight and uncommitted at the time this convention landed; fold a
`status/` row into the W2 client-work table when W2 is committed.

## What goes where

- **Element** — a discrete part of a workstream with its own state, that
  can progress / block / ship. Lives as a row in that workstream file's
  element table.
- **Shared context** — informs the whole group, not one workstream. Lives
  in the group general reference as a pointer to the canonical doc, never
  copied. Test: if you would write it into more than one workstream file,
  it is shared context (the user's example: the OnePilot vision and the
  marketing plan belong to lead-generation in general, not to Rome or
  Outreach).

## File shape

Frontmatter: `project`, `workstream`, `group` (or ""), `spec`, `state`
(active | blocked | paused | done | live | dormant), `updated:
YYYY-MM-DD`, optional `general_ref`. Body: one-line purpose; an elements
table (`Element | State | Status | Next action | Blocker | Detail`);
optional gates; pointers to the detail docs. The file is a roll-up, not a
copy: link the detail, do not restate it.

## Discipline

- **Update during work and at `/comd_checkpoint`.** When you do material
  work on a workstream, bump its status file in the same session.
- **Update in place.** Bump `updated:`; never write a dated snapshot
  (`status-2026-06-20.md`).
- **Reflect shipped reality, not the spec's intent.** Where the build has
  moved past the spec, the status file states what actually shipped and
  links the spec as background.
- **Delete on ship/abandon** (supersession, [[rule_no_file_bloat]] W1 §4).
  No `SUPERSEDED` banners.
- **Source data values** (B4, [[rule_behaviors]]): numbers and config
  trace to a source or read TBD; never invent progress.

## Wiring

- `/comd_resume {client}` loads `status/*.md` at session start.
- `/comd_checkpoint` updates the touched workstreams' files before saving.
- `/comd_new-client` scaffolds an empty `status/` for new clients.
- `tools/project_status.py --client X --check` flags stale + malformed
  files; `--scaffold` writes a template. See `tools/INDEX.md`.
- `tools/project_status.py --sweep-stale --once-per-day` runs at
  SessionStart (wired in `wire-hooks.py`) and advises on any stale or
  malformed file across all clients, fail-open. This is what makes
  detection recall-independent.

## Relationship to existing state

- `PROJECT-BOUNDARIES.md` stays the cross-project active/paused index +
  swap history; status files are the level of detail beneath it.
- `infrastructure.yaml` (platform state), the specs (lifecycle), and
  `comms-log.md` (the client conversation) are referenced by pointer, not
  duplicated. Status files fill the gap none of those covered: the moving
  parts of a workstream and where each stands.

This is canonical operational state, an allowed file purpose under
[[rule_no_file_bloat]] W1 §1.

## Why

There was no maintained per-project file describing the status of the
elements inside a project. Picking work back up meant reassembling state
from PROJECT-BOUNDARIES.md + infrastructure.yaml + spec frontmatter +
comms-log.md, and the live drift between them (e.g. a provider pivot the
spec hasn't caught up to) had no home. Per-workstream status files give
that a single, maintained surface, with shared context lifted to the group
level so it is stated once. Introduced 2026-06-20 on user direction
(Brisken pilot + future standard via `/comd_new-client`).

Related: [[skil_project-status]] (the procedure), [[rule_no_file_bloat]]
(W1, canonical state), [[rule_file_placement]] (W2, tracked home),
[[rule_behaviors]] (B4 data sourcing, checkpoint discipline).
