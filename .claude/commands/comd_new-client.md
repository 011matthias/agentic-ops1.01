---
description: Initialize a new project folder (client, internal, or platform)
argument-hint: <project-name> [--type client|internal|platform]
---

# New Project Setup

Creates the complete folder structure for a new project within the Agentic Ops workspace. Projects have a type: `client` (default), `internal`, or `platform`.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Prerequisites

Parse $ARGUMENTS:
- **Project name** (required): the slug, e.g. `acme-corp`, `my-tool`
- **`--type`** (optional): `client` | `internal` | `platform`. Default: `client`

If project name is empty, ask the user for it. Name should be lowercase, kebab-case.

**Resolve base directory based on type:**
- `type: client` → `workspace/clients/{name}/`
- `type: internal` → `workspace/projects/{name}/`
- `type: platform` → `workspace/projects/{name}/`

For `type: internal` or `type: platform`, skip Step 2 (orchestrator selection) and Step 2.5 (feasibility assessment) — proceed directly to Step 3 with a lightweight structure (context/ and scripts/ only). Generate a minimal `infrastructure.yaml` with just `type:` and `notes:` fields. Skip Steps 4–8 that are client-specific (template copy, comms, symlink).

## Step 1: Verify Project Doesn't Exist

Check if the resolved directory already exists.

If it exists, ask the user if they want to:
1. Abort (default)
2. Continue anyway (for partial setups)

## Step 2: Choose Orchestrator

Ask the user which orchestrator to use:

| Option | Description |
|--------|-------------|
| **Trigger.dev** (Recommended) | Trigger.dev handles scheduling, webhooks, retries, and monitoring. Python automations run via `pythonExtension`. |
| **n8n** | Visual workflow builder. Workflows built in n8n UI or via n8n-mcp tools. For non-developer teams with an n8n instance. |
| **Make.com** | Visual scenario builder. Scenarios built in Make.com UI, specs guide the design. For non-developer teams or clients already using Make.com. |
| **Plain FastAPI** (Legacy) | FastAPI service on Railway with custom dashboard, cron scripts, and webhook routes. NOT recommended for new clients. |

Default to **Trigger.dev** unless the user chooses otherwise.

## Step 2.5: Platform Feasibility Assessment

Before creating any files, investigate the client's platform subscription to catch mismatches early. Load [PLATFORM-FEASIBILITY](../skills/make-mcp-tools-expert/modules/PLATFORM-FEASIBILITY.md) and run Section A (Full Platform Capability Audit) for the chosen orchestrator.

**Minimum questions to ask:**

| Orchestrator | Questions |
|-------------|-----------|
| **Make.com** | Plan tier? (free/core/pro/teams/enterprise). Do they have API/MCP access? Any modules they know they need? |
| **n8n** | Cloud or self-hosted? If cloud: plan tier? Workflow count limit? |
| **Trigger.dev** | Plan tier? (hobby/pro/enterprise). Expected execution volume? |

**Record the answers** — they'll go into `infrastructure.yaml` under a `platform` section in Step 4.

**If the client doesn't know their plan details yet:**
- Record `platform.tier: "unknown"` and `platform.feasibility: "unassessed"`
- Add a note: "Feasibility assessment pending — must complete before first spec build"
- This is acceptable at onboarding; the assessment MUST be completed before `/build-automation`

**If answers reveal a RED verdict** (plan clearly insufficient for discussed scope):
- Warn: "The {plan} plan may not support the planned workload. Recommend upgrading to {tier} or reducing scope."
- Ask: "Proceed with setup anyway, or pause until subscription is confirmed?"

## Step 3: Create Folder Structure

Create the following directories:

```
workspace/clients/$ARGUMENTS/
├── specs/
│   ├── 1-spec/           # Planned, not started
│   ├── 2-build/          # Actively being implemented
│   ├── 3-test/           # Testing in progress
│   ├── 4-live/           # Deployed and working
│   ├── _archive/         # Deprecated/superseded specs
│   ├── _checklists/      # Testing checklists (per work item)
│   └── README.md         # Index of all work items
├── context/
│   └── README.md         # Client-specific notes
├── reference/            # Will link to The Crucible
└── automations/          # Copy from template
```

## Step 4: Copy Automation Template

Based on the chosen orchestrator:

**If Trigger.dev:**
```bash
cp -r workspace/templates/client-trigger-dev/* workspace/clients/$ARGUMENTS/automations/
cp -r workspace/templates/client-trigger-dev/.github workspace/clients/$ARGUMENTS/automations/
cp workspace/templates/client-trigger-dev/.gitignore workspace/clients/$ARGUMENTS/automations/
```

**If n8n:**

No template to copy. Workflows live in the n8n instance. Create a minimal automations folder:

```bash
mkdir -p workspace/clients/$ARGUMENTS/automations
```

Create `workspace/clients/$ARGUMENTS/automations/README.md`:

```markdown
# $ARGUMENTS — n8n Workflows

Workflows are built and managed in the n8n UI and via n8n-mcp tools.

| Workflow ID | Name | Status | Active |
|-------------|------|--------|--------|
| — | — | — | — |
```

Create `workspace/clients/$ARGUMENTS/infrastructure.yaml`:

```yaml
type: client

instances:
  - type: n8n
    name: n8n-$ARGUMENTS
    api_url: "https://<n8n-instance-url>"
    api_key_env: "N8N_API_KEY_$ARGUMENTS"
```

Ask the user for the n8n instance URL and API key.

Add MCP server entry to `.mcp.json` (create file if it doesn't exist):

```json
{
  "mcpServers": {
    "n8n-$ARGUMENTS": {
      "command": "npx",
      "args": ["-y", "n8n-mcp", "--apiKey=<API_KEY>", "--baseUrl=<INSTANCE_URL>"]
    }
  }
}
```

Tell the user to restart Claude Code for MCP tools to be available.

**If Make.com:**

No template to copy. Create a minimal automations folder:

```bash
mkdir -p workspace/clients/$ARGUMENTS/automations/blueprints
```

Create `workspace/clients/$ARGUMENTS/automations/README.md`:

```markdown
# $ARGUMENTS — Make.com Scenarios

Scenarios are built and managed in the Make.com UI and via MCP tools.
Exported blueprints are stored in `blueprints/` for version control.

| Scenario ID | Name | Status | Make.com URL |
|-------------|------|--------|--------------|
| — | — | — | — |
```

Create `workspace/clients/$ARGUMENTS/automations/blueprints/.gitkeep` (empty file).

Create `workspace/clients/$ARGUMENTS/infrastructure.yaml`:

```yaml
type: client

platform:
  tier: "<from Step 2.5>"       # free|core|pro|teams|enterprise
  ops_limit: <from plan tier>   # monthly operations cap
  api_access: <true|false>      # MCP/API available (Pro+ only)
  concurrent_limit: null        # null = unlimited on paid plans
  feasibility: "<from Step 2.5>" # green|yellow|orange|red|unassessed
  blockers: []                  # capability blockers found in Step 2.5
  assessed: "<today YYYY-MM-DD>"
  notes: "<any notes from Step 2.5>"

instances:
  - type: make
    name: make-$ARGUMENTS
    org_url: "https://us1.make.com/organization/<org-id>"
    team: "$ARGUMENTS"
```

Create `workspace/clients/$ARGUMENTS/context/test-fixtures.md`:

```markdown
# Test Fixtures — $ARGUMENTS

No fixtures created yet. After building the first automation, create
observability (Sheet Reader) and control (Cell Writer) fixtures.

See `.claude/rules/rule_behaviors.md` for outcome verification and test fixture conventions.

---

## Spreadsheet Reference

| Property | Value |
|----------|-------|
| Spreadsheet ID | TBD |
| Sheet name | TBD |
| Google connection | TBD |
```

Ask the user for the Make.com organization URL and team name to fill in real values.

If the client has a Make.com paid plan with API/MCP access, also add MCP server entry to `.mcp.json` (create file if it doesn't exist):

```json
{
  "mcpServers": {
    "make-$ARGUMENTS": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<MAKE_ZONE>/mcp/u/<MCP_TOKEN>/sse"]
    }
  }
}
```

Ask for the MCP token (from Make.com Profile → API/MCP access) and zone.
Tell the user to restart Claude Code for MCP tools to be available.

**If Plain FastAPI:**
```bash
cp -r workspace/templates/client-automation/* workspace/clients/$ARGUMENTS/automations/
```

## Step 5: Create Specs README

Create `workspace/clients/$ARGUMENTS/specs/README.md`:

```markdown
# $ARGUMENTS — Work Items

## Overview

| ID | Name | Type | Stage | Trigger | Orchestrator |
|----|------|------|-------|---------|--------------|
| — | — | — | — | — | — |

## Open Bug Fixes

| Fix ID | Parent | Description | Stage |
|--------|--------|-------------|-------|
| — | — | — | — |

## Pipeline Stages

- **1-spec/** — Specifications, no implementation yet
- **2-build/** — Actively being implemented
- **3-test/** — Testing in progress
- **4-live/** — Deployed and working in production
- **_archive/** — Deprecated or superseded specs
- **_checklists/** — Testing checklists (per work item)

## Work Item Types

- `a{N}` — Automation (background job, n8n workflow, cron task)
- `a{N}.{M}` — Sub-automation (child of parent automation)
- `app{N}` — App/frontend (dashboard, web UI)
- `be{N}` — Backend service (API, DB migration, infra)
- `p{N}` — Project container (multi-phase)
- `p{N}.{M}` — Project phase
- `fix{N}` — Bug fix (tracked against a parent automation via `fix{N}-{parentId}-{description}.md`)

Use `/skil_spec-creator` to add new work items.

## Quick Links

- [Context Notes](../context/README.md)
- [Reference Materials](../reference/)
```

## Step 6: Create Context README

Create `workspace/clients/$ARGUMENTS/context/README.md`:

```markdown
# $ARGUMENTS Context

## Client Overview

**Contact:** TBD
**Primary Systems:** TBD
**Timezone:** TBD

## Notes

Add client-specific notes, meeting summaries, and decisions here.

## Integration Details

Document API credentials, webhooks, and integration setup here.
```

## Step 6.5: Create Comms Infrastructure

Create communication tracking files for the new client:

1. Copy `.claude/skills/client-comms/templates/comms-log-template.md` → `workspace/clients/$ARGUMENTS/context/comms-log.md`
2. Copy `.claude/skills/client-comms/templates/comms-profile-template.md` → `workspace/clients/$ARGUMENTS/context/comms-profile.md`
3. Tell user: "Comms log and profile created. Fill in contact details in `context/comms-profile.md` when available."

## Step 7: Configure Environment

**If Trigger.dev:**

Copy `.env.example` to `.env` and fill in API keys. Environment variables are set in the Trigger.dev dashboard for production.

**If Make.com:**

No local `.env` needed. All credentials are managed as Connections in the Make.com UI. Remind the user to set up connections in their Make.com organization.

**If Plain FastAPI:**

Create `workspace/clients/$ARGUMENTS/automations/.env` with placeholders:

```env
# Dashboard Authentication
DASHBOARD_PASSWORD=<generate-secure-password>

# Internal API Key (for cron jobs)
INTERNAL_API_KEY=<generate-uuid>

# Database
DATABASE_URL=sqlite:///./data/automation.db

# Self-healing (optional)
SELF_HEALING_WEBHOOK=

# Client-specific credentials (add as needed)
# FORTNOX_CLIENT_ID=
# FORTNOX_CLIENT_SECRET=
# UPSALES_API_KEY=
```

Generate secure values:
- DASHBOARD_PASSWORD: `openssl rand -base64 16`
- INTERNAL_API_KEY: `uuidgen` or `python -c "import uuid; print(uuid.uuid4())"`

## Step 8: Create Reference Symlink

Check The Crucible's client_work folder for a matching client folder:

```bash
ls "/c/Users/neuma/Coding/1. General Work/The Crucible/workspace/client_work/"
```

Look for a folder name that matches `$ARGUMENTS` (case-insensitive, partial match OK — e.g., client name `herbox` should match `Herbox Sweden`).

**If exactly one match is found**, create the symlink automatically:
```bash
ln -s "/c/Users/neuma/Coding/1. General Work/The Crucible/workspace/client_work/<matched-folder>" workspace/clients/$ARGUMENTS/reference
```

**If multiple matches are found**, show the options and ask the user to pick one.

**If no match is found**, inform the user and create an empty placeholder:
```markdown
# workspace/clients/$ARGUMENTS/reference/README.md

No matching folder found in The Crucible. Link manually when available:
ln -s "/path/to/The Crucible/workspace/client_work/<folder>" workspace/clients/$ARGUMENTS/reference
```

## Step 9: Initialize Git Tracking

The client folder is tracked in the main Agentic Ops repo.

Run `git status` to show new untracked files.

Do NOT commit yet - let the user decide when to commit.

## Output Summary

Report to user:

```
✓ Client folder created: workspace/clients/$ARGUMENTS/

Structure:
├── specs/
│   ├── 1-spec/        # New work item specs go here
│   ├── 2-build/
│   ├── 3-test/
│   ├── 4-live/
│   ├── _archive/
│   └── _checklists/
├── context/           # Client notes + comms
│   ├── comms-log.md        # Conversation record
│   └── comms-profile.md    # Contact details & tone
├── reference/         # The Crucible link (if set)
└── automations/       # {Trigger.dev project | Make.com scenarios | FastAPI service}

Orchestrator: {Trigger.dev | Make.com | Plain FastAPI}

Next steps:
1. Review and update .env file with real credentials (Trigger.dev/FastAPI) or set up Make.com connections
2. Create first work item spec: /skil_spec-creator
3. When ready for deployment: /comd_client-handoff
```

## Notes

- This command does NOT create a GitHub repository
- The client folder lives in the main Agentic Ops repo initially
- Use `/comd_client-handoff` when client needs their own repository
- Specs should be created before implementing automations
