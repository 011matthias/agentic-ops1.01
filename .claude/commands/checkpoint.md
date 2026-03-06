---
description: Save conversation checkpoint for session continuity. Enables seamless handoff between agent sessions.
argument-hint: [topic-name]
---

Create a checkpoint that captures the current conversation state for future session continuity.

## Determine Topic

1. If `$ARGUMENTS` is provided, use it as the topic name
2. If no argument, infer the topic from what we've been working on in this conversation
3. Format topic as title case (e.g., "Fortnox API Integration")

## Check/Create Folder

1. Check if `docs/[TODAY's DATE] - [TOPIC]/` exists
   - Date format: `YYYY-MM-DD` (e.g., `2026-01-09`)
2. If folder exists: use it
3. If not: create the folder

## Gather Context

Analyze the current conversation and gather:

- **Summary**: 1-2 sentence overview of work done this session
- **What Was Done**: Categorized list of completed work
- **Key Decisions**: Important choices made with rationale
- **Files Modified**: Table of files created/modified with paths and purpose
- **Current Status**: Where things stand now
- **Next Steps**: Priority actions to continue
- **Files to Read First**: Critical files the next agent should read
- **Open Questions**: Unresolved questions needing attention
- **Reference Materials**: URLs, related docs, plan files

## Write Checkpoint

Create/update `docs/[DATE] - [TOPIC]/Checkpoint.md` using this format:

```markdown
# Checkpoint: [Topic Name]

**Date:** [TODAY's DATE]
**Status:** [Current Phase/Status]

---

## Summary
[1-2 sentence overview of work done]

---

## What Was Done This Session
### [Category]
1. Item 1
2. Item 2

---

## Key Decisions Made
### [Decision 1]
- **Choice:** What was decided
- **Rationale:** Why

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| [path] | Created/Modified | [why] |

---

## Current Status
[Where things stand now]

---

## Next Steps
1. [Priority action 1]
2. [Priority action 2]
3. [Priority action 3]

---

## Context for Next Session
### Files to Read First
- [path/to/critical/file]
- [path/to/another/file]

### Open Questions
- [Question needing resolution]

### Reference Materials
- [URL or file path]

---

## How to Continue
[Brief instructions for picking up where we left off]

---

## Strategic Feedback

### What Worked Well This Session
- [Interaction pattern or user behavior that helped efficiency]

### Suggestions
- [Specific, actionable improvement for the user's workflow]

### System Health
- [One observation about the agentic-ops architecture — e.g., skill gaps, rule coverage, documentation drift]
```

## Append Session Log

After writing the checkpoint, append a session log entry to `docs/sessions/{YYYY-MM-DD}.md`:

1. If the file doesn't exist, create it with frontmatter:
   ```yaml
   ---
   date: {TODAY}
   sessions: 0
   clients_touched: []
   friction_events: 0
   ---
   ```

2. Increment `sessions` count and merge clients into `clients_touched`
3. Append:
   ```markdown
   ### Session {N} — {TOPIC}
   **Focus:** {summary from checkpoint}
   **Clients:** {clients touched}
   **Built:** {key deliverables}
   **Friction:** {any friction events, or "None"}
   **Outcome:** {current status}
   ```
4. If friction events occurred, also append rows to `docs/friction-register.md`:
   `| {DATE} | {CLIENT} | {TYPE} | {description} | No |`

## Write Session Context YAML

After appending the session log, write a structured context file for fast session restore.

Create/update `docs/sessions/{YYYY-MM-DD}-context.yaml`:

```yaml
checkpoint_date: "{YYYY-MM-DD}"
checkpoint_topic: "{TOPIC}"
checkpoint_file: "docs/{YYYY-MM-DD} - {TOPIC}/Checkpoint.md"
clients:
  {client-id}:                        # only clients touched this session
    orchestrator: {n8n|make|trigger-dev|fastapi}
    active_specs:
      - id: {spec-id}
        stage: {spec|build|test|live}
        name: "{Automation Name}"
    comms:                             # from context/comms-log.md, omit if no log exists
      last_contact: "{YYYY-MM-DD}"
      staleness_days: {N}
      unresolved_items:
        - "{open item description}"
    next_steps:
      - "{Priority next step 1}"
      - "{Priority next step 2}"
    open_questions:
      - "{Unresolved question}"        # omit if none
```

If the file already exists for today, merge the client entries (add/update, don't overwrite unrelated clients).

## Comms Staleness Check

After writing the YAML, for each client in `clients_touched`:

1. Read `staleness_days` from the comms block computed above. Skip clients with no comms-log.
2. If any client has `staleness_days >= 4`:

> "{client} comms log is {N} days old (last contact: {date}). Any conversations to log before closing out?"

- If **yes**: use the Quick Capture procedure from COMMS-LOG.md — brief natural-language input, minimal entry, confirm before writing
- If **multiple clients** are stale: list them all, ask once ("Any of these need logging?")
- If **no**: proceed to Confirm

If all clients are under 4 days, skip this section.

## Confirm

After creating the checkpoint, confirm:
> "Checkpoint saved to `docs/[DATE] - [TOPIC]/Checkpoint.md`."
