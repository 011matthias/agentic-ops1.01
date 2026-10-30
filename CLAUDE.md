# Agentic Ops

Automation infrastructure for client projects. Four orchestrators: **n8n**, **Make.com**, **Trigger.dev**, **FastAPI (legacy)**.

## Structure

```text
workspace/
  clients/{client}/
    specs/            1-spec -> 2-build -> 3-test -> 4-live
    automations/      the code that runs for the client
    deliverables/     what the client sees
    status/           one file per workstream, kept current
    context/          IDs, comms log, client data (gitignored)
  projects/{project}/ internal work, same shape where it applies
.claude/
  rules/              constraints loaded into every session
  hooks/              enforcement that fires on tool calls
  patterns/           regex-shaped rules read by one generic hook
  skills/ agents/ commands/ workflows/
tools/                scripts and their tests, indexed in tools/INDEX.md
docs/                 checkpoints, daily session logs, friction register
platform/             legacy website source, kept for local proposal builds
```

## Workflow

```text
/comd_resume {client}              reload the last checkpoint and status files
/comd_build-automation {client}    plan, build, test and deploy against a spec
/comd_test {client} {id}           local, then dev, then production
/comd_deploy {client}              ship behind the test gates
/comd_checkpoint                   save state, log friction, update status files
```

Spec-driven n8n/Make builds use `/comd_build-automation`, `/comd_test [mode]`, `/comd_deploy`. `/comd_help-system` lists every command.

## Spec Frontmatter

Required: `id`, `name`, `type`, `stage` (spec|build|test|live), `orchestrator`, `version`, `created`, `updated`, `trigger`, `systems`, `last_changes`, `next_steps`. ID patterns: `a{N}`, `a{N}.{M}`, `app{N}`, `be{N}`, `p{N}`, `fix{N}`. Set `needs_fixes: true` when bugs found.

## Constraints

- No shared services between clients — each hands off independently
- Specs drive implementation — verify against code, not docs
- Credentials and bulk client data live in `context/`; a rule or tool may name the stable identifiers it enforces
- Skills load on demand via packs (make-pack, n8n-pack, trigger-pack)

## Primitives

- **Commands** (32) — Your interface. Type `/comd_<name>` to invoke.
- **Skills** (26) — Domain expertise (first-party `skil_` dirs; make-pack and n8n-pack keep their modules in their own `modules/`), plus vendored plugin skills. Auto-load by context (e.g., Make.com work loads make-pack).
- **Agents** (12) — Specialists in `.claude/agents/`, spawned internally by commands (build-orchestrator, implementation-agent, testing-agent, bug-fixer, deployer, api-fetcher, and others).
- **Rules** (20) — Always-on constraints in `.claude/rules/` (behaviors, session start, session pressure, plus the hard-constraint standards).
- **Hooks** (30) — Enforcement scripts in `.claude/hooks/`, wired by `tools/wire-hooks.py` and self-healed at SessionStart.
- **Patterns** (38) — Declarative regex rules in `.claude/patterns/`, read by `pattern-rules-gate.py`.

## Platform / unpauseai.com

The live site publishes from `akkton/unpauseai-web`, never from `platform/` or `tools/vercel-force-deploy.sh`; the path and the legacy `platform/` notes are in `workspace/projects/platform/context/README.md`.

## Git Workflow

One author. Every change goes on a branch and reaches `main` by PR; direct push to `main` is prohibited. Branch families: `client/{client}/...`, `docs/...`, `sys/...`, `local-web/...`, `uwi/...`, `leadgen/...`. One worktree per concurrent session; `/comd_resume {client}` scopes each session to one client; handoffs are client-namespaced under `.claude/handoffs/{client}-{session}/`.

## End-of-Session

Update spec frontmatter → Run tests → `/comd_checkpoint` → Note next steps

## Python

uv everywhere. Scripts declare inline dependencies (PEP 723) and run as `uv run tools/x.py`; each service under `workspace/clients/{client}/automations/{service}/` is its own uv project.
