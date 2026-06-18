# File Placement Standard (W2)

**Hard constraint.** Every file the agent writes lands in the home that
matches its KIND and INTENT. Generated files never default to the repo
root, never mix ephemeral scratch into tracked directories, and never
invent a parallel structure when a home already exists. This rule is the
source of truth for *where* a file goes. Its sibling
[[rule_no_file_bloat]] (W1) governs *whether* a file should exist at all;
run W1 first (do I even create this?), then W2 (where does it land?).

## 1. Classify, then map

Before writing any file, classify it on two axes:

- **Kind** — source / test / documentation / config / data-or-fixture /
  generated-or-build-artifact / report-or-analysis / client-facing
  deliverable.
- **Intent** — durable vs ephemeral; internal vs deliverable;
  committed vs never-commit.

The same extension routes differently by intent. A deliverable `.html`
goes to a `deliverables/` or `platform/public/` home; a debug render
`.html` goes to `.scratch/`. Classify by **primary** intent for
multi-purpose files, and announce the reasoning (§4).

## 2. The home map (this repo's real directories)

| Kind + intent | Home | Committed |
|---|---|---|
| Client automation code | `workspace/clients/{client}/automations/` | yes (subtree) |
| Automation spec | `workspace/clients/{client}/specs/{1-spec…4-live}/` | yes |
| Client IDs / keys / comms / raw data | `workspace/clients/{client}/context/` | **gitignored** (except `context/portable/`) |
| Client-facing deliverable | `workspace/clients/{client}/deliverables/` | yes |
| Prospect proposal site | `platform/public/clients/{slug}/` | yes |
| Gated active-client doc site | `platform/public/docs/{client}/` | yes |
| Proposal markdown | `platform/src/content/proposals/` | yes |
| Platform app source / static | `platform/src/` · `platform/public/` | yes |
| Reusable repo tool | `tools/` (+ manifest line in `tools/INDEX.md`) | yes |
| Repo tests / fixtures | `tools/tests/` · `tools/fixtures/` | yes |
| Rule / skill / agent / hook | `.claude/rules/` · `.claude/skills/{n}/SKILL.md` · `.claude/agents/` · `.claude/hooks/` | yes |
| One-off automation script (kept) | `scripts/` (ephemeral variant: `scripts/.<name>`, gitignored) | yes / no |
| Session log / checkpoint | `docs/{YYYY-MM-DD} - Topic/` · `docs/sessions/` | yes (`*-context.yaml` gitignored) |
| Durable internal report / analysis | `docs/` (`references/`, `digests/`) | yes |
| Local prototype site | `workspace/projects/local-web/` | yes |
| Fetched API docs | `api-docs/` | **gitignored** |
| Memory fact | `~/.claude/projects/.../memory/*.md` | (separate store) |
| **Ephemeral / scratch** (debug render, temp download, one-off analysis output, API response dump, throwaway script) | **`.scratch/`** | **never** |
| **Never-commit** (secrets, tokens, raw PII export, large data) | gitignored path, or do not write | **never** |

If a kind has no row here, it has no established home: route to
`.scratch/` or ask. Do **not** silently create a new tracked top-level
directory.

## 3. The five placement rules

1. **Never default to the repo root.** Root is reserved for the existing
   config + top-level docs (`CLAUDE.md`, `README.md`, `DELIVERY-GUIDE.md`,
   `.gitignore`, `.mcp.json`, `pytest.ini`, `ruff.toml`,
   `.pre-commit-config.yaml`, `skills-lock.json`). A generated file never
   lands at root.
2. **Separate ephemeral from durable, hard.** Scratch scripts, temp
   outputs, debug renders, one-off analyses, and API response dumps go to
   the gitignored `.scratch/` — never into a tracked directory. This is
   the single biggest source of repo mess; W1 §2 already says "print the
   finding, don't save it," and when an ephemeral file genuinely must
   exist, `.scratch/` is its only home.
3. **Respect existing homes over inventing new ones.** If the repo
   already has a place for a kind, use it. No parallel structures.
4. **Don't pollute.** No generated artifacts in source dirs, no
   deliverables mixed into source, client subtree boundaries stay intact.
5. **Default-safe when uncertain.** If the correct home is genuinely
   ambiguous, prefer `.scratch/` or ask. Never guess into a tracked path.

## 4. Announce placement

When writing a file whose location is not obvious from the request, state
where it is going and why in one line (`→ workspace/clients/brisken/
deliverables/X.html (client-facing deliverable)`), so a misroute is
catchable by a human in the same turn.

## 5. The scratch home

`.scratch/` at the repo root is the one canonical ephemeral area
(gitignored). Everything that is not durable, committed content goes
there. The historical scratch conventions (`.tmp/` skill-vendoring,
`scripts/.*` dumps, the reactive `/after-*.jpeg` style root-glob ignores)
are still honored where they exist, but new ephemeral writes route to
`.scratch/`.

## 6. Scratch + never-commit name patterns (predictable, enforced)

The placement gate (§7) treats these basename patterns as ephemeral and
will deny them anywhere outside a gitignored area:

- scratch: `scratch-*`, `tmp-*`, `temp-*`, `debug-*`, `snapshot-*`,
  `state-<digits>*`, `*-dump.*`, `*-debug.*`, `*.tmp`, `*.bak`

never-commit (denied into any tracked path):

- `*.env`, `*.env.*`, `client_secrets.json`, `token.json`, `*.pem`,
  `*.key`, `*secret*.json`, `*credential*.json`

When an artifact legitimately needs one of these shapes, write it under
`.scratch/`.

## 7. Enforcement

Three layers, mirroring the repo's Tool > Rule > Memory self-anneal:

1. **This rule** (always-on) — the source of truth, auto-loaded with the
   other `.claude/rules/`.
2. **Skill `skil_file-placement`** — the classify → map → default-safe →
   announce procedure for non-obvious cases. Invoke before writing a file
   whose home is unclear.
3. **Hook `.claude/hooks/file-placement-gate.py`** (`PreToolUse(Write)`)
   — the deterministic floor. Hard-**denies**: a new file at the repo
   root not in the allowlist; a never-commit pattern into a tracked path;
   a scratch pattern into a non-gitignored path. **Advisory** warning for
   an ambiguous target (unknown top-level dir). Edits to existing files
   pass through. Wired through `tools/wire-hooks.py` `CANONICAL_HOOKS`
   (the single tracked contract) and self-healed at SessionStart.

The hook is deterministic but path-pattern blunt; the rule + skill carry
the intent nuance the hook can't read. Both fire before a misplaced file
survives.

**Self-detection.** A generated file landing at root, an ephemeral file
committed into a tracked dir, or a parallel structure invented when a
home existed is a friction event (`file-placement-drift`) — log at
`/comd_checkpoint`. The recurrence-kill is to tighten the gate or the
home map here, not to remember harder.

## Why

The `.gitignore` already carries reactive, per-pattern root-clutter
patches (`/test.pdf`, `/after-*.jpeg`, `/anchor-*.jpeg`,
`/*-live-hero.jpeg`) — each one added after a stray artifact hit the
root. That is the tell: root clutter and scratch-in-tracked-dir are
recurrent, and the only existing defense was hiding files after the fact.
This rule moves the default the other way (classify → route → deny
misplacement at write time) and gives scratch a single home instead of
the scattered `.tmp/` / `scripts/.*` / root-glob conventions.

Related: [[rule_no_file_bloat]] (whether-to-create, the W1 half),
[[rule_deliverables]] (deliverable HTML standards),
[[rule_client_page_structure]] (client-page homes under
`platform/public/`).
