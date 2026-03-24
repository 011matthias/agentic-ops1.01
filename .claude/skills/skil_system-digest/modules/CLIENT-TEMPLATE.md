# Client Template

Template for generating a client-specific digest. Shows automations, status, configurability, and recent changes for one client.

## Data Collection

```bash
# Client folder
CLIENT_DIR="workspace/clients/{CLIENT_NAME}"

# Required reads:
# 1. infrastructure.yaml — orchestrator, resources, connections
# 2. specs/automation-status.yaml — automation inventory + status
# 3. specs/ subdirectories — count specs per stage
# 4. context/ — client-specific notes, test fixtures, IDs
# 5. docs/client/ — if exists, client-facing documentation

# Optional reads:
# 6. context/comms-log.md — conversation history, open items
# 7. automations/ — implementation files
```

---

## Internal Template

```markdown
# {CLIENT_NAME} — Client Report
Generated: {DATE}

## Client Overview

- **Orchestrator:** {type from infrastructure.yaml or detection}
- **Total Automations:** {count from automation-status.yaml}
- **Stage Distribution:** {count per stage: spec/build/test/live}

## Automations

| ID | Name | Status | Trigger | Systems | Last Updated |
|----|------|--------|---------|---------|-------------|
{rows from automation-status.yaml}

### Automation Details

{For each automation:}
#### {ID}: {Name}
- **Status:** {status}
- **Trigger:** {trigger type}
- **Systems:** {systems list}
- **Spec:** `specs/{stage_folder}/{id}.md`
- **Last Changes:**
{bullet list from last_changes}
- **Next Steps:**
{bullet list from next_steps}

## Infrastructure

{From infrastructure.yaml:}
- **Resources:** {list resources with ship: true/false flags}
- **Connections:** {list configured connections/credentials}
- **Data Stores / Databases:** {list if applicable}

## Context Files

{List files in context/ directory:}
- {filename} — {first line or purpose}

## Open Items

{From context/comms-log.md if exists:}
- {Unresolved items from comms log}

## Test Fixtures

{From context/test-fixtures.md if exists:}
- {List of persistent test fixtures}
```

---

## Client-Facing Template

```markdown
# {CLIENT_NAME} — Automation Report
Generated: {DATE}

## Your Automations

{For each automation:}
### {Name}

**Status:** {human-readable status badge}

**What it does:**
{Plain-language description from spec overview section}

**Triggered by:** {trigger in plain language}
**Connected systems:** {systems list}

{If status is "live":}
> This automation is live and running in production.

{If status is "testing":}
> This automation is being tested with real data to ensure accuracy.

{If status is "building":}
> This automation is currently being built.

## What's Configurable

{For each configurable item:}
| Setting | Current Value | Where to Change |
|---------|--------------|-----------------|
{rows from spec configurability section or infrastructure.yaml}

## Status Summary

| Automation | Status |
|------------|--------|
{simplified status table with emoji badges:}
{live = "Live", tested = "Testing Complete", building = "In Progress", spec = "Planned"}

## Questions or Changes?

If you'd like to adjust any settings or have questions about your automations,
just let us know and we'll update the configuration.
```
