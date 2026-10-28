# Agentic Ops

The working repo for UnpauseAI's client automation. Claude Code does most of the
building here, under rules and hooks that check its work, and every change ships
through a pull request and CI.

It holds three things: client work, a few internal projects, and the harness
itself (the rules, hooks, skills and tools that make the agent's output checkable).

> This repository is public. Anything tracked is world-readable, so client
> context, credentials and personal data live only in gitignored paths
> (`workspace/clients/*/context/`, `.env`).

## Current work

The state of each workstream lives in its status file, not in this README.

| Client or project | What | Runs on | Status |
| --- | --- | --- | --- |
| **Brisken** | Expense reconciliation (p1); lead generation for Rome 2026, the outreach engine and the Lead Desk (p2) | Python services on Fly.io, Microsoft Graph, a Lovable frontend | [`clients/brisken/status/`](workspace/clients/brisken/status/) |
| **Meji Media** | Christmas-enquiry pipeline (live), opportunity radar | Make.com | [`clients/meji-media/status/`](workspace/clients/meji-media/status/) |
| **Upwork independence** | Finding clients outside Upwork | | [`projects/upwork-independence/status/`](workspace/projects/upwork-independence/status/) |

Smaller internal projects (local-business demo sites, an AI-visibility probe,
service ideas) sit in [`workspace/projects/`](workspace/projects/), each with its
own README.

## Layout

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
  skills/ agents/ commands/
tools/                scripts and their tests, indexed in tools/INDEX.md
docs/                 checkpoints, daily session logs, friction register
platform/             legacy website source, kept for local proposal builds
```

## How a piece of work runs

```text
/comd_resume {client}              reload the last checkpoint and status files
/comd_build-automation {client}    plan, build, test and deploy against a spec
/comd_test {client} {id}           local, then dev, then production
/comd_deploy {client}              ship behind the test gates
/comd_checkpoint                   save state, log friction, update status files
```

A spec drives each build. It moves from `specs/1-spec` to `specs/4-live`, and its
frontmatter `stage` says where it stands. `/comd_help-system` lists every command.

## How changes ship

1. Every change starts on a branch (`client/{client}/...`, `docs/...`, `sys/...`).
   Nothing is committed to `main` directly.
2. Once the change is verified, commit, push and pull request run without asking.
3. CI decides the merge: type check, lint and build, the enforcement-hook test
   suite, a gitleaks secret scan, spell check and Playwright smoke tests. A green
   PR merges automatically; a red one waits.
4. Anything irreversible or outward-facing needs an explicit yes from the owner:
   deploys, force pushes, and any write to a client's live systems (sending mail,
   starting a campaign, changing records).

The full rules: [`rule_no_auto_commit.md`](.claude/rules/rule_no_auto_commit.md)
and [`rule_instantly_invasive.md`](.claude/rules/rule_instantly_invasive.md).

## The harness

The agent does most of the work, so its mistakes have to be caught by something
sturdier than its own memory. Fixes are ranked by how reliably they fire:

1. **Tools and hooks** run on every tool call and cannot be forgotten.
2. **Rules** in `.claude/rules/` are loaded into every session and apply at the
   moment of decision.
3. **Memory** depends on recall and is the last resort.

When a slip repeats, its fix moves up a rung. Every slip is logged in
[`docs/friction-register.md`](docs/friction-register.md), and `/comd_system-dev`
turns the patterns there into new hooks and rules.

## Related repositories

| Repository | What it holds | Relation to this repo |
| --- | --- | --- |
| `akkton/agentic-ops` (private) | Nico's copy of this system, with his clients, including Wärme Wimmer | This repo was copied from it on 2026-05-07; the two have not synced since |
| `011matthias/brisken-expense-review` (private) | The Lovable-built frontend of the Brisken expense app | Lovable keeps its own repo; the backend lives here |
| `akkton/unpauseai-web` (private) | unpauseai.com | Moved out of `platform/` on 2026-07-25; the site publishes from there |
| `011matthias/agentic-dev1` | Software products, and the production build for any local-web prospect who signs | Product builds kept apart from client operations |

## Working here

- Python tooling runs through [uv](https://github.com/astral-sh/uv); each script
  declares its own dependencies inline (PEP 723).
- `uv run tools/doctor.py` runs the full health-check battery.
- Before pushing a change under `tools/` or `.claude/hooks/`, run
  `uv run tools/preflight-hooks.py --full`; it reproduces the CI hook job.
- Two Claude sessions at once need two `git worktree`s. A shared checkout shares
  HEAD, index and stash, and the sessions collide.
- Further reading: [`CLAUDE.md`](CLAUDE.md) (the agent's operating manual),
  [`tools/INDEX.md`](tools/INDEX.md) (every tool, one line each),
  [`docs/INDEX.md`](docs/INDEX.md) (checkpoint index).
