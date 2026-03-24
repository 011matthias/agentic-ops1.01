---
name: spec-cleanup
description: Audits a client's spec folder for misplaced files (wrong stage folder), stale frontmatter stage fields, and missing required fields. Proposes and applies moves and frontmatter updates. Use when asked to "clean up specs", "audit specs", or run "/spec-cleanup {client}".
---

# Spec Cleanup

Audits `workspace/clients/{client}/specs/` and fixes two classes of problems:

1. **Stage/folder mismatch** — a file's `stage:` frontmatter doesn't match its parent folder
2. **Missing required frontmatter** — `id`, `name`, `type`, `stage`, `orchestrator` not present

## Quick Start

When the user provides a client name (e.g. `herbox-sweden`):

1. Run the audit (steps below)
2. Present the report
3. Confirm which fixes to apply
4. Execute approved changes

## Stage → Folder Mapping

| `stage` value | Expected folder |
|---|---|
| `spec` | `1-spec/` |
| `build` | `2-build/` |
| `test` | `3-test/` |
| `live` | `4-live/` |
| `deprecated` | `_archive/` |

Files in `_archive/` or `_checklists/` are **skipped** (no stage expectations applied).
`README.md` is also skipped.

## Audit Process

### Step 1 — Scan

Use Glob to find all `.md` files:

```
workspace/clients/{client}/specs/**/*.md
```

Exclude files where the path contains `/_archive/`, `/_checklists/`, or filename is `README.md`.

### Step 2 — Parse frontmatter

For each file, Read the first 30 lines and extract:
- `stage:` value
- Whether `id`, `name`, `type`, `orchestrator` are present

### Step 3 — Check placement

Determine the file's **current folder** from its path (the segment between `specs/` and the filename).

Compare to the expected folder from the stage-to-folder table above.

A mismatch = file is in the wrong folder OR frontmatter `stage` doesn't match the folder it's sitting in.

### Step 4 — Compile report

Group findings into three sections:

**A. Stage/folder mismatches**
List each file with: current location | frontmatter stage | expected location | recommended action

**B. Missing required frontmatter**
List each file with the missing fields

**C. Clean**
Count of files that passed all checks

### Step 5 — Propose actions

For each mismatch, propose one or both of:
- **Move file** — to make location match the frontmatter stage
- **Update frontmatter** — change `stage:` to match the folder it's already in

When ambiguous (could go either way), ask the user which approach they prefer.

### Step 6 — Execute

For approved actions:
1. Update frontmatter `stage:` using Edit tool (change only that field)
2. Move file using Bash `mv`
3. Update `README.md` stage column for the affected rows

### Step 7 — Update README

After moving files, read `workspace/clients/{client}/specs/README.md` and update the Stage column for any rows referencing moved files. Update file links too if they include the folder path.

## Reference

See [AUDIT-RULES.md](modules/AUDIT-RULES.md) for the full rules reference (required fields, valid stage values, edge cases).
