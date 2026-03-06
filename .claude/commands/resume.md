---
description: Resume work on a client by loading context from latest checkpoint and client files
argument-hint: <client-name>
---

# Resume Client Work

Reloads context for a client so work can continue from where it left off. Eliminates the cold-start problem at the beginning of sessions.

## Context

- Working directory: !`pwd`
- Client name: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, ask the user for the client name.

Verify `workspace/clients/$ARGUMENTS/` exists. If not, list available clients from `workspace/clients/` and ask the user to pick one.

## Step 0: Try YAML Fast-Path

Check for a session context YAML:

```bash
ls docs/sessions/*-context.yaml 2>/dev/null | sort -r | head -3
```

If a recent `docs/sessions/{date}-context.yaml` exists and contains an entry for `$ARGUMENTS`:

1. Read the YAML file
2. Extract the client's entry (`orchestrator`, `active_specs`, `next_steps`, `open_questions`, `comms`)
3. Also read `workspace/clients/$ARGUMENTS/infrastructure.yaml` for instance IDs (1 file, fast)
4. Also read `workspace/clients/$ARGUMENTS/context/comms-log.md` if it exists — extract `last_contact`, count unresolved open items
5. Jump directly to **Step 6: Summarize** using the YAML data + live comms state — skip Steps 1-5

If no YAML exists or the client isn't in it, proceed with Steps 1-5 below (full context load).

## Step 1: Find Latest Checkpoint

Search `docs/` for the most recent dated folder that relates to this client:

```bash
ls -d docs/*/ | sort -r | head -5
```

Read the latest `Checkpoint.md` that mentions the client. Focus on:
- **Current Status** — what's working, what's not
- **Next Steps** — what was planned next
- **Context for Next Session** — files to read, account references, open questions

## Step 2: Read Client Spec Status

Read `workspace/clients/$ARGUMENTS/specs/README.md` to understand:
- Which automations exist
- What stage each is in (spec → build → test → live)
- Any open bug fixes

## Step 3: Read Client Context

Read all files in `workspace/clients/$ARGUMENTS/context/`:
- Client-specific notes, integration details
- Google Sheet schemas, email templates, etc.
- **Test fixtures registry** (if it exists: `context/test-fixtures.md`)
- **Roadmap** (if it exists: `context/roadmap.md`)

## Step 4: Read Infrastructure

Read `workspace/clients/$ARGUMENTS/infrastructure.yaml` (if it exists) to identify:
- Orchestrator type (make, n8n, trigger-dev, fastapi)
- Instance details (org IDs, URLs, team IDs)

## Step 4.5: Read Comms Context

If `workspace/clients/$ARGUMENTS/context/comms-log.md` exists:

1. Read the file
2. Extract `last_contact` date from frontmatter, calculate days since today
3. Count unresolved open items (entries with `Open items:` that have no matching `Resolved:`)
4. List unresolved items briefly (one-liner each, with assigned contact and age in days)

If no comms-log exists, skip this step silently.

## Step 5: Orchestrator-Specific Context

**If Make.com:**
- Note scenario IDs, webhook URLs, connection IDs from checkpoint
- Check if test fixtures (Sheet Reader, Cell Writer) are documented
- Note the Make.com zone and MCP token availability

**If n8n:**
- Check `.mcp.json` for n8n MCP server entry
- Note workflow IDs from checkpoint

**If Trigger.dev:**
- Check `trigger.config.ts` for registered tasks
- Note deployment status

## Step 6: Summarize

Present a concise summary to the user:

```
## $ARGUMENTS — Session Context

**Orchestrator:** {type}
**Last checkpoint:** {date} — {topic}

### Current Status
- {automation}: {stage} — {one-liner}
- ...

### What's Next
1. {next step from checkpoint}
2. ...

### Available Test Fixtures
- {fixture name}: {ID / URL}
- ...

### Build History
If `workspace/clients/$ARGUMENTS/context/build-log.md` exists, include:
- Total builds: {from frontmatter}
- Latest build: {date, automation, outcome}
- Most common errors: {from build log entries}

### Client Communication
- **Last contact:** {date} ({N} days ago) — {direction} — {who}
- **Status:** {OK (0-3d) | NOTICE (4-7d) | STALE (8-14d) | URGENT (15+d)}
- **Open items ({M}):**
  - {item} — assigned to {contact} — {age} days

### Open Questions
- {from checkpoint}
```

If comms status is STALE or URGENT:

> "Comms log is {N} days old. Want to catch it up before we start?
> - **a)** Log missed conversations now (quick capture)
> - **b)** Draft an outbound follow-up (`/draft {client}`)
> - **c)** Skip for now"

Wait for the user's response before asking "What would you like to work on?"

If comms status is NOTICE (4-7d), keep the current passive note: "Last contact was {N} days ago."

If no comms-log exists, omit the Client Communication section.

Then ask: "What would you like to work on?"

## Notes

- This command is READ-ONLY — it gathers context but makes no changes
- If no checkpoint exists for this client, report that and suggest starting with `/status-check`
- For new clients with no history, suggest `/new-client` instead
