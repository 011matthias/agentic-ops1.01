---
description: Show system usage guide — all commands organized by workflow phase
---

Print the following system reference card:

## Your Interface = Slash Commands

Skills and agents are internal plumbing — you interact via commands only.

### Every Session
| Phase | Command | Purpose |
|-------|---------|---------|
| Start | `/resume {client}` | Load context from last checkpoint |
| Build | `/build-automation {client}` | Full lifecycle orchestration |
| Test | `/test {client} {id}` | Local test |
| Test | `/test-dev {client} {id}` | Dev test with real APIs |
| Test | `/test-production {client} {id}` | Production test (requires confirmation) |
| Ship | `/deploy {client}` | Deploy with test gates |
| Comms | `/draft {client}` | Draft client message |
| Comms | `/comms {client} inbound` | Process client reply |
| End | `/checkpoint` | Save session state |

### Periodic
| Command | Purpose |
|---------|---------|
| `/review` | Surface patterns from logs and friction |
| `/status-check [client]` | Automation status overview |
| `/system-dev` | Self-improvement cycle |
| `/system-digest` | Generate reports |

### Client Lifecycle
| Command | Purpose |
|---------|---------|
| `/new-client {name}` | Create folder structure |
| `/client-handoff {client}` | Create GitHub repo + subtree |
| `/publish {client}` | Push to GitHub (auto-deploy) |
| `/export-client-docs {client}` | Consolidated documentation |

### Utilities
| Command | Purpose |
|---------|---------|
| `/fix-bugs {client} {id}` | Targeted bug fixing |
| `/fetch-api {name} {url}` | Import API docs + generate client |
| `/make-instances` | Manage Make.com connections |
| `/n8n-instances` | Manage n8n connections |
| `/refresh-pipeline` | Update spec dashboard |
| `/verify-live {client} {id}` | Verify production status |

### How It Works Under the Hood
- **Skills** auto-load by context (make-pack, n8n-pack, trigger-pack, spec-creator, client-comms, etc.)
- **Agents** are spawned by commands (build-orchestrator → implementation-agent, testing-agent, deployer, bug-fixer, doc-generator, project-manager)
- **Rules** are always active (behaviors.md: self-annealing, outcome verification, escalation; detection.md: orchestrator detection; session-start.md: context loading)
- **Self-annealing:** After every fix → "how do I prevent this?" → if recurrent, system creates new primitives via meta-builder
