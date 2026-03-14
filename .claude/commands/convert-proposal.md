---
description: Convert a won proposal into a client folder with pre-filled context
argument-hint: <proposal-slug>
---

# Convert Proposal to Client

Reads a won proposal's frontmatter and scaffolds a complete client folder with pre-populated context from the proposal.

## Context

- Working directory: !`pwd`
- Proposal slug: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, list all proposals in `platform/src/content/proposals/` (excluding p000 sample) and ask which one to convert.

## Step 1: Read Proposal

Read `platform/src/content/proposals/$ARGUMENTS.md` and extract frontmatter:
- `prospect` — becomes the client display name
- `contact` — primary contact name
- `source` — acquisition channel (upwork|direct|linkedin|referral)
- `source_url` — original listing/conversation URL
- `project_title` — initial project description
- `value_estimate` — contract value range
- `timeline` — estimated delivery timeline
- `tags` — hints for orchestrator selection
- `status` — current proposal status

If the file doesn't exist, report error and stop.

## Step 2: Check Status

If `status` is not `won`:
- Show current status
- Ask: "This proposal is currently `{status}`. Mark as won and proceed?"
- If no, stop

## Step 3: Derive Client Name

Convert `prospect` to kebab-case for the folder name:
- "Acme Corp" → `acme-corp`
- "Beta Inc" → `beta-inc`

Show the derived name and ask user to confirm or override.

## Step 4: Check Existing Client

If `workspace/clients/{client-name}/` exists:
1. Warn the user
2. Ask: abort or continue (partial setup)?

## Step 5: Choose Orchestrator

Pre-suggest based on proposal `tags`:
- Tags include "make.com" or "make" → suggest Make.com
- Tags include "trigger" or "trigger.dev" → suggest Trigger.dev
- Tags include "n8n" → suggest n8n
- Otherwise → default to Trigger.dev

Show the suggestion and let user confirm or change. Use the same orchestrator options as `/new-client`:

| Option | Description |
|--------|-------------|
| **Trigger.dev** (Default) | Scheduling, webhooks, retries, monitoring. Python via `pythonExtension`. |
| **n8n** | Visual workflow builder via n8n UI or n8n-mcp tools. |
| **Make.com** | Visual scenario builder via Make.com UI. |
| **Plain FastAPI** (Legacy) | NOT recommended for new clients. |

## Step 6: Create Folder Structure

Create the same structure as `/new-client` Step 3:

```
workspace/clients/{client-name}/
├── specs/
│   ├── 1-spec/
│   ├── 2-build/
│   ├── 3-test/
│   ├── 4-live/
│   ├── _archive/
│   ├── _checklists/
│   └── README.md
├── context/
│   ├── README.md
│   ├── comms-log.md
│   ├── comms-profile.md
│   └── acquisition.md        # NEW — proposal source data
├── reference/
├── automations/
├── docs/
│   └── client/
└── infrastructure.yaml
```

## Step 7: Copy Automation Template

Follow the same logic as `/new-client` Step 4 based on the chosen orchestrator (Trigger.dev template copy, n8n/Make.com minimal setup, etc.).

## Step 8: Create Pre-filled Files

### Specs README

Same as `/new-client` Step 5.

### Context README

Create `workspace/clients/{client-name}/context/README.md` with proposal data pre-filled:

```markdown
# {prospect} Context

## Client Overview

**Contact:** {contact}
**Source:** {source}
**Primary Systems:** (from proposal tags: {tags})
**Timezone:** TBD

## Notes

Converted from proposal {id} ({project_title}).
Original value estimate: ${value_estimate}.

## Integration Details

Document API credentials, webhooks, and integration setup here.
```

### Acquisition Context (NEW)

Create `workspace/clients/{client-name}/context/acquisition.md`:

```markdown
# Acquisition Context — {prospect}

| Field | Value |
|-------|-------|
| Source | {source} |
| Source URL | {source_url} |
| Proposal | platform/src/content/proposals/{slug}.md |
| Proposal ID | {id} |
| Won date | {today YYYY-MM-DD} |
| Value estimate | ${value_estimate} |
| Project title | {project_title} |
| Contact | {contact} |
| Timeline | {timeline} |
```

### Comms Profile (pre-filled)

Copy `.claude/skills/client-comms/templates/comms-profile-template.md` to `context/comms-profile.md`.

Replace template variables:
- `{CLIENT_NAME}` → prospect name
- `{CONTACT_1_NAME}` → contact name from proposal
- `{PLATFORM}` → source (upwork, direct, linkedin, referral)
- Leave other fields as template placeholders for user to fill

### Comms Log

Copy `.claude/skills/client-comms/templates/comms-log-template.md` to `context/comms-log.md`.

## Step 9: Update Proposal Status

Edit `platform/src/content/proposals/{slug}.md` frontmatter:
- Set `status: won`

## Step 10: Create Reference Symlink

Same logic as `/new-client` Step 8 — check The Crucible for matching folder.

## Step 11: Offer First Spec Stub

Ask: "Create an initial spec stub from the proposal?"

If yes, create `workspace/clients/{client-name}/specs/1-spec/a1-{project-keyword}.md` with:

```yaml
---
id: a1
name: "{project_title}"
type: automation
stage: spec
orchestrator: {orchestrator}
version: "0.1"
created: "{today}"
updated: "{today}"
trigger: TBD
systems: [{from tags}]
last_changes:
  - "Initial spec from proposal {id}"
next_steps:
  - "Refine requirements with client"
  - "Map data fields and integrations"
---
```

And a body section extracted from the proposal's "Our Proposed Solution" section.

## Output Summary

```
Proposal {slug} converted to client: {client-name}

  Client folder:  workspace/clients/{client-name}/
  Orchestrator:   {orchestrator}
  Comms profile:  context/comms-profile.md  (fill in tone + style)
  Acquisition:    context/acquisition.md
  First spec:     specs/1-spec/a1-*.md  (if created)
  Proposal:       status updated to "won"

Next steps:
  1. Fill in comms-profile.md (contact details, tone, style)
  2. Refine first spec: /spec-creator {client-name}
  3. Run /resume {client-name} to start the build session
  4. When ready for GitHub: /client-handoff {client-name}
```

## Notes

- This command replicates `/new-client` logic with pre-filled values from the proposal
- The `acquisition.md` file preserves the full proposal context for future reference
- Run `/proposal-status` after conversion to verify the pipeline updated
