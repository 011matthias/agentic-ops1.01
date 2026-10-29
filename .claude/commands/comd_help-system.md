---
description: Show system usage guide — all commands organized by workflow phase
---

Print the following system reference card. The roster below is read live from
`.claude/commands/comd_*.md` frontmatter, so it never lists a command that does
not exist.

## Your Interface = Slash Commands

Skills and agents are internal plumbing — you interact via commands only.

### Every Session
| Phase | Command | Purpose |
|-------|---------|---------|
| Start | `/comd_resume {project}` | Load context from last checkpoint |
| Build | `/comd_build-automation {project}` | Spec-driven n8n/Make build: plan, code, test, deploy |
| Test | `/comd_test [mode] {project} {id}` | Modes: (default), dev, production, verify |
| Ship | `/comd_deploy {project}` | Deploy with test gates |
| End | `/comd_checkpoint` | Save session state |

### All Commands

Live roster (`file:field: value`, one or two lines per command):

!`grep -H -m2 -E '^(description|argument-hint):' .claude/commands/comd_*.md`

Render it as one table with columns Command (`/comd_` + the file stem), Arguments
(the `argument-hint`, blank when absent) and Purpose (the `description`), sorted
by command name.

### How It Works Under the Hood
- **Skills** auto-load by context (make-pack, n8n-pack, trigger-pack, skil_spec-creator, client-comms, etc.)
- **Agents** are spawned by commands (agnt_build-orchestrator → agnt_implementation-agent, agnt_testing-agent, agnt_deployer, agnt_bug-fixer, agnt_api-fetcher)
- **Rules** are always active (`rule_behaviors.md`: self-annealing, outcome verification, escalation; `rule_session-start.md`: context loading; `rule_session-pressure.md`: adaptive behavior)
- **Self-annealing:** After every fix → "how do I prevent this?" → if recurrent, system creates new primitives via skil_meta-builder
