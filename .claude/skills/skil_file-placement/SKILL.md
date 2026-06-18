---
name: file-placement
description: Decide where a generated file belongs in this repo by classifying its kind and intent, then mapping to the repo's real home. Use before writing any file whose location is not obvious — a new file kind, a deliverable-vs-scratch judgement, a never-commit artifact, or a multi-purpose file. Routes ephemeral work to the gitignored .scratch/ and never defaults to the repo root. Backs rule_file_placement.md (W2).
---

# File Placement

The procedure for routing a file to the correct home. The policy and the
home map live in `.claude/rules/rule_file_placement.md` (W2, always
loaded); this skill is the step-by-step for the non-obvious cases the
always-on rule doesn't resolve at a glance. For an obvious write (editing
a file in its existing home, a deliverable into `deliverables/`) you do
not need this skill — just write and announce.

## When to run

- The file is a new KIND with no obvious home.
- The same extension could be a deliverable OR a scratch artifact and you
  must pick (a `.html` report vs a debug render; a `.json` fixture vs an
  API response dump).
- The content is never-commit (a secret, a token, a raw lead export).
- A multi-purpose file where the home depends on primary intent.
- You are about to write to the repo root, or to a top-level directory
  the home map doesn't list.

## Procedure: classify → map → default-safe → announce

### 1. Classify on two axes

- **Kind:** source · test · documentation · config · data/fixture ·
  generated/build artifact · report/analysis · client-facing deliverable.
- **Intent:** durable or ephemeral · internal or deliverable · committed
  or never-commit.

For a multi-purpose file, pick the **primary** intent. A script that
generates a deliverable is still a script (durable tool → `tools/`, or
throwaway → `.scratch/`); its output is the deliverable.

### 2. Map to the home (from W2 §2)

Walk the kind+intent to its row:

- Client work → `workspace/clients/{client}/{automations,specs,context,deliverables}/`
  (context is gitignored — IDs, keys, comms, raw data go there).
- Platform → `platform/src/` (app), `platform/public/` (static +
  client/prospect sites), `platform/src/content/proposals/` (proposal md).
- Repo capability → `tools/` (+ a line in `tools/INDEX.md`), tests →
  `tools/tests/`, fixtures → `tools/fixtures/`.
- Claude primitives → `.claude/{rules,skills,agents,hooks}/`.
- Internal durable record → `docs/` (session folders, `references/`,
  `digests/`).
- Fetched API docs → `api-docs/` (gitignored).

### 3. Ephemeral and never-commit → out of tracked space

- **Ephemeral** (debug render, temp download, one-off analysis output,
  API response dump, throwaway script): route to **`.scratch/`**. First
  apply W1 — if the finding can be printed to stdout or distilled into one
  sentence in an existing doc, do that and write nothing.
- **Never-commit** (secret, token, raw PII export, large binary): a
  gitignored path only, or do not write it. Never into a tracked dir.
- Use a name the gate recognizes as scratch when appropriate
  (`scratch-*`, `tmp-*`, `state-<date>.json`), or just put it under
  `.scratch/`.

### 4. Default-safe when uncertain

If two homes are plausible and the choice is genuinely unclear, prefer
`.scratch/` (reversible, gitignored, no pollution) or ask. Never guess
into a tracked path and never create a new tracked top-level directory to
hold an orphan kind.

### 5. Announce

State the destination and the reason in one line before/at the write:
`→ .scratch/recon-dump.json (ephemeral API response, not committed)` or
`→ workspace/clients/brisken/deliverables/statement.html (client-facing
deliverable)`. One line is enough; it makes a misroute catchable in the
same turn.

## Edge cases

- **New kind, no home in W2 §2** → `.scratch/` or ask; never invent a
  tracked directory silently.
- **Deliverable vs intermediate output** → deliverables go to a
  `deliverables/` or `platform/public/` home; the intermediate render
  that produced it goes to `.scratch/`. They are different files with
  different homes.
- **Multi-purpose** → classify by primary intent, announce the call.
- **Root** → only the W2 §3 allowlist lives at root; everything else gets
  a home or `.scratch/`.

The gate (`.claude/hooks/file-placement-gate.py`) is the backstop: it
denies a root-write, a never-commit-into-tracked, or a scratch-pattern
into a non-gitignored path, and warns on an unknown top-level dir. This
skill is how you get it right before the gate has to.
