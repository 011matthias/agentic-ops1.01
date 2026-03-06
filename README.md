# Agentic Ops

**Code-based automation infrastructure for client projects.**

Build, test, and deploy Python automations with AI-powered self-healing capabilities.

```
     ___                    __  _         ____
    /   | ____ ____  ____  / /_(_)____   / __ \____  _____
   / /| |/ __ `/ _ \/ __ \/ __/ / ___/  / / / / __ \/ ___/
  / ___ / /_/ /  __/ / / / /_/ / /__   / /_/ / /_/ (__  )
 /_/  |_\__, /\___/_/ /_/\__/_/\___/   \____/ .___/____/
       /____/                              /_/
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENTIC OPS                                    │
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │  N8N JSON   │    │  NATURAL    │    │   MANUAL    │    │  EXISTING   │  │
│   │   EXPORT    │    │  LANGUAGE   │    │    SPEC     │    │    CODE     │  │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│          │                  │                  │                  │         │
│          ▼                  ▼                  ▼                  ▼         │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                        SPEC GENERATION                               │  │
│   │                                                                      │  │
│   │   /n8n-converter  │  /spec-creator  │  /spec-updater                 │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                     AUTOMATION SPEC (.md)                            │  │
│   │  ┌──────────────────────────────────────────────────────────────┐    │  │
│   │  │  - Mermaid flow diagram                                      │    │  │
│   │  │  - API references                                            │    │  │
│   │  │  - Edge cases & error handling                               │    │  │
│   │  │  - Testing criteria                                          │    │  │
│   │  └──────────────────────────────────────────────────────────────┘    │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                       IMPLEMENTATION                                 │  │
│   │                                                                      │  │
│   │   Claude Code implements automation from spec                        │  │
│   │   ├── app/automations/{name}.py                                      │  │
│   │   ├── app/routers/{webhooks}.py                                      │  │
│   │   └── tests/test_{name}.py                                           │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         VALIDATION                                   │  │
│   │                                                                      │  │
│   │   testing-agent validates against spec                               │  │
│   │   ├── Unit tests                                                     │  │
│   │   ├── Dry-run execution                                              │  │
│   │   └── Acceptance criteria check                                      │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                          DEPLOY                                      │  │
│   │                                                                      │  │
│   │   deployer pushes to Railway                                         │  │
│   │   ├── GitHub repo (git subtree)                                      │  │
│   │   ├── Railway deployment                                             │  │
│   │   └── Environment configuration                                      │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Multi-Client Isolation

Each client gets their own isolated infrastructure:

```
                    ┌───────────────────────────────────────┐
                    │           AGENTIC OPS REPO            │
                    │                                       │
                    │  ┌─────────────────────────────────┐  │
                    │  │           api-docs/             │  │
                    │  │   (shared API documentation)    │  │
                    │  └─────────────────────────────────┘  │
                    │                                       │
                    │  ┌─────────────────────────────────┐  │
                    │  │           templates/            │  │
                    │  │   (boilerplate for new clients) │  │
                    │  └─────────────────────────────────┘  │
                    │                                       │
                    │  ┌────────────────────────────────┐  │
                    │  │            clients/            │  │
                    │  │                                │  │
┌───────────────────┼──┼─── client-a/ ──────────────────┼──┼───────────────────┐
│                   │  │    │                           │  │                   │
│                   │  │    ├── specs/                  │  │                   │
│  GIT SUBTREE      │  │    │   └── automations/        │  │    RAILWAY        │
│  ────────────►    │  │    │       ├── a1-xxx.md       │  │    ────────►      │
│                   │  │    │       └── a2-xxx.md       │  │                   │
│  akkton/  │  │    │                           │  │   herbox-sweden   │
│  agentic-ops--    │  │    └── automations/ ──────────►│──┼──► Railway App    │
│  herbox-sweden    │  │        └── (FastAPI app)       │  │                   │
│                   │  │                                │  │                   │
└───────────────────┼──┼────────────────────────────────┼──┼───────────────────┘
                    │  │                                │  │
┌───────────────────┼──┼─── uplifted-consulting/ ───────┼──┼───────────────────┐
│                   │  │    │                           │  │                   │
│  GIT SUBTREE      │  │    ├── specs/                  │  │    RAILWAY        │
│  ────────────►    │  │    │   └── automations/        │  │    ────────►      │
│                   │  │    │                           │  │                   │
│  akkton/  │  │    └── automations/ ──────────►│──┼──► uplifted       │
│  agentic-ops--    │  │        └── (FastAPI app)       │  │    Railway App    │
│  uplifted-...     │  │                                 │  │                   │
│                   │  │                                 │  │                   │
└───────────────────┼──┼─────────────────────────────────┼──┼───────────────────┘
                    │  │                                 │  │
                    │  └─────────────────────────────────┘  │
                    │                                       │
                    └───────────────────────────────────────┘
```

### Self-Healing Loop

When automations fail, they can self-heal:

```
     ┌─────────────────────────────────────────────────────────────┐
     │                   AUTOMATION RUNNING                        │
     └─────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
                          ┌───────────────┐
                          │  Error occurs │
                          └───────┬───────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │        Log error + step history       │
              │          to client database           │
              └───────────────────┬───────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │     Trigger self-healing webhook      │
              │         (if configured)               │
              └───────────────────┬───────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │    Claude agent receives context:     │
              │    - Error message                    │
              │    - Step history                     │
              │    - Automation code                  │
              └───────────────────┬───────────────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  Analyze & attempt  │
                       │       fix           │
                       └──────────┬──────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
          ┌─────────────────┐         ┌─────────────────┐
          │     SUCCESS     │         │     FAILURE     │
          │  auto_resolved  │         │  notify user    │
          └─────────────────┘         └─────────────────┘
```

---

## Automation Status Legend

Each automation progresses through a well-defined lifecycle:

| Status | Description | What Happens |
|--------|-------------|--------------|
| `planned` | Automation is planned but no spec exists | Requirements gathering |
| `spec_created` | Spec document exists, implementation not started | Spec review |
| `implemented` | Code written, not tested | Ready for testing |
| `tested_locally` | Local tests pass (unit + dry-run) | Ready for dev testing |
| `tested_dev` | Live dev test passed with real APIs | Ready for deployment |
| `deployed` | Deployed to Railway | Ready for production testing |
| `tested_production` | Limited production test passed | Monitoring live execution |
| `tested_live` | Working in production (verified via logs) | Ready for documentation |
| `documentation_created` | Technical + client docs generated | Complete |
| `completed` | Fully live and documented | Maintenance mode |
| `needs_fixes` | Requires bug fixes or maintenance | Fix required |

**Status Flow:**
```
planned → spec_created → implemented → tested_locally → tested_dev → deployed → tested_production → tested_live → documentation_created → completed
                                        ↑                                                    ↑
                                        └── Any status can revert to needs_fixes ──────────┘
```

---

## Quick Start

### 1\. New Client Setup

```bash
# Initialize folder structure
/new-client acme-corp

# Creates:
# clients/acme-corp/
# ├── specs/
# │   └── automations/
# ├── context/
# └── automations/   (from template)
```

### 2\. Build an Automation

```bash
# End-to-end automation building
/build-automation acme-corp
```

This orchestrates the full pipeline:

```
  /build-automation
         │
         ├──► 1. PLAN      ─► spec-creator skill
         │                    generates spec with Mermaid diagram
         │
         ├──► 2. CODE      ─► implement automation from spec
         │                    extends BaseAutomation class
         │
         ├──► 3. TEST      ─► testing-agent validates
         │                    runs tests, dry-run, checks criteria
         │
         ├──► 4. DOCS      ─► doc-generator creates
         │                    technical + client-facing docs
         │
         └──► 5. DEPLOY    ─► deployer pushes
                              GitHub + Railway deployment
```

### 3\. Client Handoff

When ready to give client their own repo:

```bash
/client-handoff acme-corp

# Creates:
# - GitHub repo: akkton/agentic-ops--acme-corp
# - Git subtree connection for future syncs
```

---

## Skills, Agents & Commands

### Skills (Specialized Workflows)

| Skill | Command | Purpose |
| --- | --- | --- |
| spec-creator | /spec-creator | Create automation specs from requirements |
| spec-updater | /spec-updater | Add features to existing specs |
| n8n-converter | /n8n-converter | Convert N8N workflows to Python specs |
| api-docs-fetcher | /fetch-api | Download API documentation |
| api-boilerplate | /api-boilerplate | Generate Python API clients |
| meta-builder | /meta-builder | Create new skills, commands, agents |

### Agents (Autonomous Workers)

| Agent | Purpose |
| --- | --- |
| testing-agent | Validate implementations against specs |
| doc-generator | Generate technical + client documentation |
| deployer | Deploy to Railway with test gates |

### Commands (User Actions)

| Command | Purpose |
| --- | --- |
| /new-client {name} | Initialize client folder structure |
| /client-handoff {name} | Create GitHub repo + git subtree |
| /build-automation {name} | End-to-end automation building |
| /deploy {name} | Deploy to Railway |
| /checkpoint | Save conversation state |

---

## Folder Structure

```
Agentic Ops/
│
├── api-docs/                    # Shared API documentation
│   ├── fortnox/
│   └── upsales/
│
├── clients/                     # Per-client isolation
│   └── {client-name}/
│       ├── reference/           # Symlink to client data
│       ├── specs/
│       │   ├── README.md        # Index of automations
│       │   └── automations/     # Individual spec files
│       │       ├── a1-xxx.md
│       │       └── a2-xxx.md
│       ├── context/             # Client notes
│       └── automations/         # Deployable app (git subtree)
│           ├── app/
│           │   ├── automations/ # Automation classes
│           │   ├── routers/     # Webhooks, dashboard
│           │   └── templates/   # Dashboard UI
│           ├── docs/
│           │   ├── technical/   # Developer docs
│           │   └── client/      # End-user docs
│           └── tests/
│
├── templates/
│   ├── client-automation/       # Boilerplate for new clients
│   ├── api-clients/             # Generated API client templates
│   └── specs/                   # Spec templates
│
└── .claude/
    ├── skills/                  # AI skills
    ├── agents/                  # Specialized agents
    └── commands/                # User commands
```

---

## Tech Stack

| Component | Technology |
| --- | --- |
| Runtime | Python 3.11+ with UV |
| Framework | FastAPI |
| AI | Claude Code (Anthropic) |
| Deployment | Railway |
| Version Control | Git subtrees for client isolation |
| Database | SQLite (per-client) |

---

## Running Locally

```bash
# Navigate to client automations
cd clients/{client-name}/automations

# Install dependencies
uv sync

# Run tests
uv run pytest tests/

# Run specific automation (dry-run)
uv run python -m app.automations.{name} --dry-run

# Start development server
uv run uvicorn app.main:app --reload
```

---

## License

Private repository. All rights reserved.