# Agentic Ops

Automation infrastructure for client projects. Four orchestrators: **n8n**, **Make.com**, **Trigger.dev**, **FastAPI (legacy)**.

## Structure

```
workspace/
├── clients/{client}/specs/          # 1-spec → 2-build → 3-test → 4-live
├── clients/{client}/context/        # Client IDs, notes, test fixtures
├── clients/{client}/automations/    # Deployed code → git subtree
├── templates/                       # Boilerplate (Trigger.dev, FastAPI, specs, API clients)
docs/                                # Session logs, checkpoints, friction register
├── sessions/                        # Daily logs + YAML context for /resume fast-path
tools/                               # Utility scripts (make-api.py, etc.)
scripts/                             # One-off automation scripts
.claude/skills/                      # On-demand domain knowledge (via packs)
.claude/agents/                      # Multi-step orchestrators
.claude/commands/                    # User-facing entry points
.claude/rules/                       # Universal constraints (always loaded)
```

## Workflow

### Session Flow
```bash
/resume {client}             # Start: reload context from checkpoint
/build-automation {client}   # Build: plan → code → test → deploy
/test {client} {id}          # Test: local → /test-dev → /test-production
/deploy {client}             # Ship: deploy with test gates
/draft {client}              # Comms: draft client message
/checkpoint                  # End: save state + feedback
```

### System
```bash
/status-check [client]       # Overview of all automations
/review                      # Surface patterns from logs
/system-dev                  # Self-improvement cycle
/new-client {name}           # Onboard new client
/help-system                 # Full command reference card
```

### Delivery
```bash
/client-handoff {client}     # Create GitHub repo for client
/publish {client}            # Push to GitHub (auto-deploy)
/export-client-docs {client} # Consolidated docs
```

## Spec Frontmatter

Required: `id`, `name`, `type`, `stage` (spec|build|test|live), `orchestrator`, `version`, `created`, `updated`, `trigger`, `systems`, `last_changes`, `next_steps`. ID patterns: `a{N}`, `a{N}.{M}`, `app{N}`, `be{N}`, `p{N}`, `fix{N}`. Set `needs_fixes: true` when bugs found.

## Constraints

- No shared services between clients — each hands off independently
- Specs drive implementation — verify against code, not docs
- Client knowledge (IDs, mappings) → `context/` only, never in MEMORY.md or rules
- Skills load on demand via packs (make-pack, n8n-pack, trigger-pack). Run `/status-check` for full command list.

## Primitives

- **Commands** (23) — Your interface. Type `/command` to invoke.
- **Skills** (26) — Domain expertise. Auto-load by context (e.g., Make.com work loads make-pack).
- **Agents** (9) — Specialists. Spawned internally by commands. You don't invoke these directly.
- **Rules** (3) — Always-on constraints (behaviors, orchestrator detection, session start).

## Git Subtree

```bash
git subtree push --prefix="workspace/clients/{client}/automations" git@github.com:nickswagster/agentic-ops--{client}.git main
```

## End-of-Session

Update spec frontmatter → Run tests → `/checkpoint` → Note next steps

## Python

All scripts use [UV](https://github.com/astral-sh/uv): `uv run pytest tests/`, `uv run python -m app.automations.{name} --dry-run`. Scripts declare inline dependencies (PEP 723).
