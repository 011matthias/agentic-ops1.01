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

Grouped by parent home so each path-thread is stated once. **gi** =
gitignored.

**Client work — `workspace/clients/{client}/`**

| Sub-home | What | Committed |
|---|---|---|
| `automations/` | automation code | yes (git subtree) |
| `specs/{1-spec…4-live}/` | specs, by stage | yes |
| `context/` | IDs / keys / comms / raw client data | **gi** (except `context/portable/`) |
| `deliverables/` | client-facing deliverables | yes |

**Platform — `platform/`**

| Sub-home | What |
|---|---|
| `src/` | Next.js app source |
| `public/clients/{slug}/` · `public/docs/{client}/` | prospect proposal sites · gated active-client doc sites |
| `src/content/proposals/` | proposal markdown |

**Repo infrastructure**

| Home | What |
|---|---|
| `tools/` (+ a row in `tools/INDEX.md`) · `tools/tests/` · `tools/fixtures/` | reusable tools · tests · fixtures |
| `.claude/{rules, skills/{n}/SKILL.md, agents, hooks}/` | Claude primitives |
| `scripts/` (`.<name>` → **gi**) | one-off automation scripts |
| `docs/{YYYY-MM-DD} - Topic/` · `docs/sessions/` · `docs/references/` · `docs/digests/` | session logs · checkpoints · internal reports (`sessions/*-context.yaml` → **gi**) |
| `.github/` · `.agents/` | CI workflows · vendored skill assets (NOT `.claude/agents/`) |
| `api-docs/` | fetched API docs (**gi**) |
| `workspace/projects/local-web/` | local prototype sites |
| `workspace/projects/upwork-independence/` | owned-acquisition program: optimize assets (root, byte-stable) · `status/` workstream files · tracked `context/` (`.env` → **gi**) |

**Ephemeral / never-commit**

| Home | What |
|---|---|
| **`.scratch/`** | ALL ephemeral output (debug renders, temp downloads, one-off analysis, API dumps, throwaway scripts) — **never** committed |
| a gitignored path, or don't write | secrets, tokens, raw PII export, large data — **never** committed |
| `~/.claude/.../memory/*.md` | memory facts (separate store) |

If a kind has no row here, it has no established home: route to `.scratch/`
or ask. Do **not** silently create a new tracked top-level directory. (The
gate also recognizes the gitignored tooling dirs `.vscode/`, `.serena/`,
`.playwright-mcp/`, `.tmp/`, `internal/`, `node_modules/` and never advises
on a write there.)

## 3. The five placement rules

1. **Never default to the repo root.** Root is reserved for config + top-level
   docs: the existing set (`CLAUDE.md`, `README.md`, `DELIVERY-GUIDE.md`,
   `.gitignore`, `.mcp.json`, `pytest.ini`, `ruff.toml`,
   `.pre-commit-config.yaml`, `skills-lock.json`) plus conventional
   root-only build/tooling config that has no other home (`Makefile`,
   `Dockerfile`, `package.json`, `tsconfig.json`, `vercel.json`,
   `pyproject.toml`, `uv.lock`, `.nvmrc`, `CHANGELOG.md`, `CONTRIBUTING.md`,
   `SECURITY.md`, and the like; see the gate's `ROOT_ALLOWLIST`). A generated
   artifact (a report, a data dump, an image) never lands at root.
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

The placement gate (§7) keys on basename patterns. These lists are a
**non-exhaustive deny floor**, not complete coverage: the rule + skill still
govern any credential- or scratch-shaped file the patterns don't name. And
because the gate sees only the path, an innocuously-named dump
(`analysis-results.json`) or a raw export into a tracked dir passes the hook
silently; not creating those is the agent's W1 responsibility.

**Scratch** (denied outside a gitignored area):

- Hard (always ephemeral): `*-dump.*`, `*-debug.*`, `*.tmp`, `*.bak`,
  `state-<digits>*`.
- Prefix (`scratch-*`, `tmp-*`, `temp-*`, `debug-*`, `snapshot-*`): denied
  ONLY for non-durable files. A committed source/test/doc with a durable
  extension (`.py`, `.ts/.tsx`, `.js`, `.md`, `.go`, `.rs`, a `.spec.`/`.test.`
  file, ...) that merely starts with one of these words is NOT scratch and
  passes (a real `debug-helper.py` or `snapshot-utils.ts` is source).

**Never-commit** (denied into any tracked path; passes only when the path is
already gitignored):

- env: `.env`, `.env.<anything>` (e.g. `.env.local`, `.env.production`) —
  EXCEPT the secret-free templates `.env.example` / `.env.sample` /
  `.env.template` / `.env.dist`, which are committable and pass.
- keys/certs: `*.pem`, `*.key`, `*.key.json`, `*.p12`, `*.pfx`, `*.jks`,
  `*.keystore`, the SSH private-key names `id_rsa` / `id_dsa` / `id_ecdsa` /
  `id_ed25519`, and extension-less `*_key` (`id_rsa.pub` and `*_key.py`
  stay committable).
- secret/credential payloads (word-boundary, not descriptive substring):
  `secrets?.{json,yaml,yml,toml,ini,conf,cfg}` and
  `credentials?.{...}` (so `api-credentials.json` denies but
  `secrets-rotation-guide.json` passes), `client_secrets.json`,
  `token.json` / `*_token.json`, `service-account*.json`, `sa-key.json`,
  `firebase-adminsdk*.json`.

**Token-bearing dotfiles** (`.npmrc`, `.pypirc`, `.netrc`, `.dockercfg`) and
**data/PII exports** (`*-export.csv`, `leads*.csv`, `*-pii-*`) into a tracked
path get an **advisory** (a name-only gate can't see an inline token or raw
PII), not a hard deny.

When an artifact legitimately needs a scratch/never-commit shape, write it
under `.scratch/` (or the client's gitignored `context/`).

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
