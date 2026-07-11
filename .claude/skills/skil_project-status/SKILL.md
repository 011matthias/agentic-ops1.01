---
name: project-status
description: Maintain the per-project status-of-elements files for a client. Use when starting or wrapping work on a client workstream (Brisken Rome, the outreach engine, expense-recon, etc.), when a new workstream begins, or when asked to bring a project's status current. Defines what a workstream is, the element-vs-shared-context test, the file templates, the tracked home, and supersession discipline. Backs rule_project_status.md.
---

# Project Status

Each discrete workstream inside a client gets ONE maintained status file: a
roll-up of the important elements inside it and where each stands, kept as
context for picking the work back up. Shared context that belongs to a whole
group (a vision, a marketing plan) lives in a group general-reference file, never
duplicated into each workstream file.

The policy lives in `.claude/rules/rule_project_status.md` (always loaded). This
skill is the procedure for the non-obvious parts: deciding the workstream
boundaries, classifying elements vs shared context, and writing the files.

## When to run

- Beginning or wrapping material work on a client workstream.
- A new workstream starts (scaffold its file).
- Asked to "bring the status current" / before `/comd_resume` is useful again.
- A workstream ships or is abandoned (delete its file, per supersession).

For a one-line state edit to an existing file, just edit it; you do not need this
skill.

## The home

`workspace/clients/{client}/status/` — tracked (NOT under the gitignored
`context/`), beside `infrastructure.yaml` and `PROJECT-BOUNDARIES.md`. One file
per workstream; one general-reference file per group that has shared context.
Naming: `{spec-id}-{slug}.md` (e.g. `p2-rome.md`, `p1-expense-reconciliation.md`,
`p2-lead-gen-general.md`).

## Step 1 — Find the workstream boundaries

A **workstream** is a unit of work with its own moving parts that can progress,
block, or ship somewhat independently of the others. It usually maps to a
folder under the client's `context/` or `deliverables/`, or to a spec.

Test: would a status update on this unit be mostly irrelevant to the others? If
yes, it is its own workstream. If two candidate units rise and fall together,
they are one workstream with two elements.

A **group** is a parent that several workstreams share (e.g. `lead-generation`
holding Rome, Outreach, OnePilot-site, Targeting). A group earns a
general-reference file only when it has cross-workstream shared context. A
standalone project with no siblings (e.g. expense-recon) has no group and no
general ref.

## Step 2 — Classify each item: element vs shared context

For everything inside the workstream, decide:

- **Element** — a discrete part of THIS workstream that has its own state and
  can be worked on / blocked / shipped. Goes in the workstream file's element
  table. (Rome's one-pager; the cold-sending domain farm; the deterministic
  matcher.)
- **Shared context** — informs the whole GROUP, not one workstream. Goes in the
  group general reference as a pointer, never copied. (The OnePilot vision; the
  marketing/strategy plan; the product catalog.)

The test the user gave: "OnePilot vision is for lead generation in general, not
for a certain project, so it goes into the general reference, not inside a
workstream." Apply it to anything that would otherwise be duplicated across
workstream files: if you would write it twice, it is shared context.

## Step 3 — Write the file (roll-up, not a copy)

Scaffold with the tool, then fill it in:

```
uv run tools/project_status.py --client {client} --scaffold {slug} \
    --group {group} --spec {id} --general-ref status/{group}-general.md
```

Workstream file:

```yaml
---
project: {client}
workstream: {slug}
group: {group}        # "" if standalone
spec: {id}            # related spec id(s)
state: active         # active | blocked | paused | done | live | dormant
updated: YYYY-MM-DD
general_ref: status/{group}-general.md   # omit if no group
---
```
Body:
- One-line purpose.
- **Elements** table: `Element | State | Status | Next action | Blocker | Detail`.
  Element states: not-started · in-progress · blocked · done · live · paused.
- **Open decisions / gates** (optional): link the source doc, do not restate it.
- **Pointers**: links to the spec / deliverables / context that hold the detail.

The file is a roll-up. If you are pasting paragraphs from another doc, link the
doc instead. Each element row points to where its detail lives.

Group general-reference file: same frontmatter shape (use the group slug as
`workstream`, state = the group's overall state); body holds the shared-context
pointers, the group-level gates, and an index of the workstream files beneath it.

## Step 4 — Keep it honest

- **Update in place** when an element moves. Never date-stamp a new copy
  (`status-2026-06-20.md`); bump the `updated:` field instead.
- **Reflect shipped reality, not the spec's intent.** Where the build has moved
  past the spec (e.g. a provider pivot the spec hasn't caught up to), the status
  file states what actually shipped and links the spec as background.
- **Delete on ship/abandon.** When a workstream ships or is dropped, delete its
  file (supersession discipline, rule_no_file_bloat W1 §4). Do not leave a
  `SUPERSEDED` banner.
- **Source data values.** Numbers, counts, and config in a status file follow the
  B4 gate: trace to a source or mark TBD. Do not invent progress.

## Step 5 — Verify

```
uv run tools/project_status.py --client {client} --check
```
Flags stale files (active/blocked/live not touched within the threshold) and
malformed frontmatter. Green before you consider the status current.

## How this connects

- `/comd_resume {client}` loads `status/*.md` at session start — these files are
  the at-a-glance state it reads.
- `/comd_checkpoint` updates the touched workstreams' files before saving.
- `/comd_new-client` scaffolds an empty `status/` so a new client starts here.
- A SessionStart sweep (`project_status.py --sweep-stale`, wired in
  `wire-hooks.py`) auto-surfaces stale/malformed files every session, fail-open,
  so you do not have to remember to run `--check`. When it flags one, update it in
  place or delete it (W1 §4); do not nurse a rotting file.
- `PROJECT-BOUNDARIES.md` stays the cross-project active/paused index; status
  files are the level of detail beneath it. `infrastructure.yaml`, the specs, and
  `comms-log.md` are referenced by pointer, never duplicated.
