# DOC-GENERATION — Documentation Generation Module

Generates technical and client-facing documentation for automations. Loaded by build-orchestrator during Phase 4.

---

## Input

- **Client**: Client name
- **Automation ID**: Automation identifier

## Process

### Step 1: Gather Information

Read files based on orchestrator type:

**For code-based clients (Trigger.dev, FastAPI):**
- `workspace/clients/{client}/specs/*/{id}-*.md` — Spec
- `workspace/clients/{client}/automations/app/automations/{name}.py` — Implementation
- `workspace/clients/{client}/automations/app/config.py` — Configuration
- `workspace/clients/{client}/automations/tests/test_{name}.py` — Tests

**For Make.com clients:**
- `workspace/clients/{client}/specs/*/{id}-*.md` — Spec
- `workspace/clients/{client}/automations/blueprints/{id}-*.json` — Blueprint
- `workspace/clients/{client}/context/email-templates.md` — Templates
- `workspace/clients/{client}/context/google-sheets-schema.md` — Tracking schema
- `workspace/clients/{client}/infrastructure.yaml` — Scenario IDs, connections

**For n8n clients:**
- `workspace/clients/{client}/specs/*/{id}-*.md` — Spec
- Workflow details from n8n MCP tools or context files

Extract: name, description, trigger type, systems, step-by-step flow, configuration, edge cases.

### Step 2: Generate Technical Documentation

Create `workspace/clients/{client}/automations/docs/technical/{id}.md`:

```markdown
# {Automation Name} - Technical Documentation

## Overview
{Description from spec}

| Field | Value |
|-------|-------|
| Spec | `specs/{stage}/{id}-*.md` |
| Version | {version} |
| Status | {status} |

## Architecture
{Mermaid diagram from spec}

## Dependencies / Connections
{Packages for code-based, Connections + Data Stores for Make.com/n8n}

## Configuration
{Environment variables for code-based, Data store fields for Make.com, Workflow settings for n8n}

## Implementation Details
{Step-by-step flow explanation}

## Error Handling
| Error Type | Handling | Recovery |
|------------|----------|----------|
| {error} | {how handled} | {auto/manual} |

## Testing
{How to run tests or manually verify}

## Monitoring
{Where to check logs, dashboards, run history}

## Changelog
{From spec changelog}
```

### Step 3: Generate Client Documentation

Create `workspace/clients/{client}/automations/docs/client/{id}.md`:

```markdown
# {Automation Name - Friendly Title}

## What This Does
{Plain language explanation}

**Runs:** {When - e.g., "Every day at 8:00 AM"}

## How It Works
1. **{Step 1}** - {Plain language}
2. **{Step 2}** - {Plain language}
3. **{Step 3}** - {Plain language}

## What You'll See
{Observable outputs — dashboard, emails, Slack, data changes}

## Troubleshooting
### "{Common issue 1}"
{What to do}

---
*Last updated: {date}*
```

### Step 4: Ensure Directory Structure

```bash
mkdir -p workspace/clients/{client}/automations/docs/technical
mkdir -p workspace/clients/{client}/automations/docs/client
```

## Writing Guidelines

- **Technical docs:** Precise, code-aware, assumes developer audience
- **Client docs:** Plain language, focuses on "what" not "how", scannable
- Read spec and code before writing — don't assume
- Keep both docs in sync
