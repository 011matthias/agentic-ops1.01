---
name: system-digest
description: Generates structured system digests (overview, changelog, client report) with internal and client-facing templates. Scans live system state and delivers via terminal, file, or email. Use when running /system-digest or when user wants a system overview, progress report, or client update.
---

# System Digest

Scans the live Agentic Ops system and generates structured digests for system awareness, client updates, or progress reporting.

## Quick Start

```bash
/system-digest --overview              # What does this system do?
/system-digest --changes --since DATE  # What changed recently?
/system-digest --client NAME           # Client-specific report
```

## Available Operations

| Operation | Description | Module |
|-----------|-------------|--------|
| System Overview | Full inventory + architecture + per-client summary | [OVERVIEW-TEMPLATE.md](modules/OVERVIEW-TEMPLATE.md) |
| Changelog | Recent changes to primitives, clients, learnings | [CHANGELOG-TEMPLATE.md](modules/CHANGELOG-TEMPLATE.md) |
| Client Report | Client-specific automations, status, configurability | [CLIENT-TEMPLATE.md](modules/CLIENT-TEMPLATE.md) |
| Email Delivery | Send digest via Resend API | [DELIVERY.md](modules/DELIVERY.md) |

## Process

### Step 1: Parse Mode

Determine mode from arguments:
- `--overview` (default): full system inventory
- `--changes [--since DATE]`: recent changes (default: 7 days)
- `--client NAME`: client-specific report

Determine template:
- Internal (default): technical, for system operator
- `--client-facing`: value-focused, for clients

### Step 2: Scan System State

Read the following to build a live inventory:

**Primitives:**
- `ls .claude/rules/*.md` → count + names
- `ls .claude/skills/*/SKILL.md` → count + read first description line from each
- `ls .claude/agents/*.md` → count + names
- `ls .claude/commands/*.md` → count + names

**Rules budget:**
- Count total lines across `.claude/rules/*.md` (budget: 250)

**Client status:**
- For each client in `workspace/clients/*/`:
  - Read `workspace/clients/{client}/specs/automation-status.yaml` if exists
  - Read `infrastructure.yaml` if exists (for orchestrator type)
  - Count specs in `specs/` subdirectories

**Skill modules:**
- For each skill, count files in `modules/` subdirectory

### Step 3: Gather Changes (if --changes mode)

- Read `docs/checkpoints/` for checkpoint files newer than `--since` date
- Read recent entries from MEMORY.md (scan for dates >= `--since`)
- Check git log: `git log --since=DATE --name-only -- .claude/` for changed primitives
- Diff automation-status.yaml against previous digest if available

### Step 4: Apply Template

Load the appropriate template module:
- `--overview` → [OVERVIEW-TEMPLATE.md](modules/OVERVIEW-TEMPLATE.md)
- `--changes` → [CHANGELOG-TEMPLATE.md](modules/CHANGELOG-TEMPLATE.md)
- `--client` → [CLIENT-TEMPLATE.md](modules/CLIENT-TEMPLATE.md)

Each template has two variants:
- **Internal**: technical details, skill names, module counts, architecture
- **Client-facing**: automation descriptions, status badges, value statements

### Step 5: Render

Generate the digest as markdown. If `--html` or `--email` is requested, convert to styled HTML.

### Step 6: Deliver

- **Terminal** (default): print the markdown output directly
- **--file**: save to `docs/digests/YYYY-MM-DD-{mode}.md`
- **--html**: save styled HTML to `docs/digests/YYYY-MM-DD-{mode}.html`
- **--email ADDRESS**: follow [DELIVERY.md](modules/DELIVERY.md) instructions

## Modules

- [OVERVIEW-TEMPLATE.md](modules/OVERVIEW-TEMPLATE.md) — System overview generation template
- [CHANGELOG-TEMPLATE.md](modules/CHANGELOG-TEMPLATE.md) — Changes digest generation template
- [CLIENT-TEMPLATE.md](modules/CLIENT-TEMPLATE.md) — Client report generation template
- [DELIVERY.md](modules/DELIVERY.md) — Email delivery via Resend API
