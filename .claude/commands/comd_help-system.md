---
description: Show system usage guide — all commands organized by workflow phase
---

Print the following system reference card:

## Your Interface = Slash Commands

Skills and agents are internal plumbing — you interact via commands only.

### Every Session
| Phase | Command | Purpose |
|-------|---------|---------|
| Start | `/comd_resume {project}` | Load context from last checkpoint |
| Build | `/comd_build-automation {project}` | Full lifecycle orchestration |
| Test | `/comd_test [mode] {project} {id}` | Test automation (modes: test, dev, production, verify) |
| Ship | `/comd_deploy {project}` | Deploy with test gates |
| Comms | `/comd_draft {client}` | Draft client message (`type: client` only) |
| Comms | `/comd_comms {client} inbound` | Process client reply (`type: client` only) |
| End | `/comd_checkpoint` | Save session state |

### Periodic
| Command | Purpose |
|---------|---------|
| `/comd_review` | Surface patterns from logs and friction |
| `/comd_status-check [project]` | Automation status overview |
| `/comd_ops-audit [project]` | Audit ops/execution usage vs plan limits |
| `/comd_system-dev` | Self-improvement cycle |
| `/comd_system-digest` | Generate reports |

### Project Lifecycle
| Command | Purpose |
|---------|---------|
| `/comd_new-client {name} [--type client\|internal\|platform]` | Create project folder |
| `/comd_client-handoff {client}` | Create GitHub repo + subtree (`type: client` only) |
| `/comd_publish {client}` | Push to GitHub auto-deploy (`type: client` only) |
| `/comd_export-client-docs {client}` | Consolidated docs (`type: client` only) |

### Utilities
| Command | Purpose |
|---------|---------|
| `/comd_fix-bugs {project} {id}` | Targeted bug fixing |
| `/comd_fetch-api {name} {url}` | Import API docs + generate client |
| `/comd_make-instances` | Manage Make.com connections |
| `/comd_n8n-instances` | Manage n8n connections |
| `/comd_refresh-pipeline` | Update spec dashboard |

### How It Works Under the Hood
- **Skills** auto-load by context (make-pack, n8n-pack, trigger-pack, skil_spec-creator, client-comms, etc.)
- **Agents** are spawned by commands (agnt_build-orchestrator → agnt_implementation-agent, agnt_testing-agent, agnt_deployer, agnt_bug-fixer, agnt_api-fetcher)
- **Rules** are always active (behaviors.md: self-annealing, outcome verification, escalation; session-start.md: context loading; session-pressure.md: adaptive behavior)
- **Self-annealing:** After every fix → "how do I prevent this?" → if recurrent, system creates new primitives via skil_meta-builder
