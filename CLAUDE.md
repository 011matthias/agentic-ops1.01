# Agentic Ops

Automation infrastructure for client projects. Four orchestrators: **n8n**, **Make.com**, **Trigger.dev**, **FastAPI (legacy)**.

## Structure

```
workspace/
├── clients/{client}/specs/          # 1-spec → 2-build → 3-test → 4-live
├── clients/{client}/context/        # Client IDs, notes, test fixtures
├── clients/{client}/automations/    # Deployed code → git subtree
├── templates/                       # Boilerplate (Trigger.dev, FastAPI, specs, API clients)
platform/                            # Website — proposals + automation modules + client portal
├── src/content/proposals/           # Proposal markdown files (frontmatter + MDX)
├── src/app/proposals/               # Public proposal landing pages
├── src/app/api/modules/             # Automation module webhook endpoints
├── src/modules/                     # Module registry and type definitions
docs/                                # Session logs, checkpoints, friction register
├── sessions/                        # Daily logs + YAML context for /resume fast-path
tools/                               # Utility scripts (see tools/INDEX.md for manifest)
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

### Proposals
```bash
/new-proposal {prospect}     # Generate proposal landing page
/proposal-status             # Track all proposals (pipeline view)
/publish-proposal {slug}     # Deploy proposal to production
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

- **Commands** (27) — Your interface. Type `/command` to invoke.
- **Skills** (26) — Domain expertise. Auto-load by context (e.g., Make.com work loads make-pack).
- **Agents** (6) — Specialists. Spawned internally by commands: build-orchestrator, implementation-agent, testing-agent, bug-fixer, deployer, api-fetcher.
- **Rules** (3) — Always-on constraints (behaviors, session start, session pressure). Orchestrator detection deferred to build-time.

## Parallel Sessions

For parallel work across clients, open separate terminal sessions and `/resume {client}` in each. Each session is scoped to one client — no cross-contamination. Handoff directories are client-namespaced: `.claude/handoffs/{client}/`.

## Git Subtree

```bash
git subtree push --prefix="workspace/clients/{client}/automations" git@github.com:akkton/agentic-ops--{client}.git main
```

## Platform (unpauseai.com)

Next.js 15 + Tailwind + TypeScript in `platform/`. Deployed to Vercel (Root Directory: `platform/`).

- **Proposals:** Markdown files in `platform/src/content/proposals/` with YAML frontmatter. Statically generated at build time.
- **Modules:** Automation modules push data via `/api/modules/{name}`. Registry in `src/modules/registry.ts`.
- **Dev:** `cd platform && npm run dev`
- **Build:** `cd platform && npm run build`

## Git Workflow (Multi-Developer)

Both developers use feature branches. Direct push to `main` is prohibited.

```
Branch naming:
  proposal/{slug}              # One proposal per branch
  platform/{feature}           # Platform code changes
  client/{client}/{description} # Client automation work
```

Merge via PR. Vercel creates preview deployments per PR automatically.

## End-of-Session

Update spec frontmatter → Run tests → `/checkpoint` → Note next steps

## Python

All scripts use [UV](https://github.com/astral-sh/uv): `uv run pytest tests/`, `uv run python -m app.automations.{name} --dry-run`. Scripts declare inline dependencies (PEP 723).
