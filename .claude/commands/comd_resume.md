---
description: Resume work on a project or client by loading context from latest checkpoint and project files
argument-hint: <project-or-client-name>
---

# Resume Work

Reloads context for a project or client so work can continue from where it left off. Eliminates the cold-start problem at the beginning of sessions. **This command scopes the session to a single project** — all subsequent operations target only this project's directory. For parallel work, open separate sessions and `/resume` in each.

## Context

- Working directory: !`pwd`
- Project name: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, ask the user for the project name.

Resolve the project directory — check in this order:
1. `workspace/clients/$ARGUMENTS/` — client projects (`type: client`)
2. `workspace/projects/$ARGUMENTS/` — internal/platform projects

If found, note the resolved path and `type` from `infrastructure.yaml`.
If neither exists, list both `workspace/clients/` and `workspace/projects/` and ask the user to pick one.

## Scope Codes

Use these when building the session header slug and title:

| Code | Project |
|------|---------|
| `meji` | meji-media |
| `plat` | platform (unpauseai.com) |
| `sys` | system-dev / cross-client |
| `auto` | autopilot |
| `hie` | hideit-equorperated |
| `bris` | brisken |
| `peak` | peakora |
| `{3-4 char initials}` | any new client/project |

## Step 0: Try YAML Fast-Path

Check for a session context YAML:

```bash
ls docs/sessions/*-context.yaml 2>/dev/null | sort -r | head -3
```

If a recent `docs/sessions/{date}-context.yaml` exists and contains an entry for `$ARGUMENTS`:

1. Read the YAML file
2. Extract the project's entry (`orchestrator`, `active_specs`, `next_steps`, `open_questions`, `comms`)
3. Also read `{resolved_path}/infrastructure.yaml` for instance IDs and `type` (1 file, fast)
4. Also read `{resolved_path}/context/comms-log.md` if it exists — extract `last_contact`, count unresolved open items
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

## Step 2: Read Spec Status

If `{resolved_path}/specs/README.md` exists, read it to understand:
- Which automations exist
- What stage each is in (spec → build → test → live)
- Any open bug fixes

(Non-client projects may not have a specs/ directory — skip silently if absent.)

## Step 3: Read Context

Read all files in `{resolved_path}/context/`:
- Project-specific notes, integration details
- Google Sheet schemas, email templates, etc.
- **Test fixtures registry** (if it exists: `context/test-fixtures.md`)
- **Roadmap** (if it exists: `context/roadmap.md`)

## Step 4: Read Infrastructure

Read `{resolved_path}/infrastructure.yaml` (if it exists) to identify:
- Project `type` (client | internal | platform)
- Orchestrator type (make, n8n, trigger-dev, fastapi, vercel, etc.)
- Instance details (org IDs, URLs, team IDs)

## Step 4.5: Read Comms Context

If `{resolved_path}/context/comms-log.md` exists:

1. Read the file
2. Extract `last_contact` date from frontmatter, calculate days since today
3. Count unresolved open items (entries with `Open items:` that have no matching `Resolved:`)
4. List unresolved items briefly (one-liner each, with assigned contact and age in days)
5. If unresolved comms items exist, flag them as **task inputs** in the Step 6 summary — not just status. Present as: "Pending comms decisions that may affect this session: {list}". These are inputs to planning, not background context.

If no comms-log exists, skip this step silently.

## Step 5: Orchestrator-Specific Context

**If Make.com:**
- Note scenario IDs, webhook URLs, connection IDs from checkpoint
- Check if test fixtures (Sheet Reader, Cell Writer) are documented
- **Resolve active instance:** If `infrastructure.yaml` lists multiple Make.com instances:
  1. Identify which instance has `mcp_server` field — that is the MCP-accessible instance
  2. Cross-reference with `.mcp.json` to confirm MCP server name and zone (eu1/eu2)
  3. Note both instances with their zones and purposes (dev vs production)
  4. Default targeting: production instance (`mcp_server` present) for live work; dev instance for building/testing `ship: false` scenarios
- If only one instance exists, note its zone and MCP availability
- Include in Step 6 summary:
  ```
  ### Active Instance
  - **MCP target:** {mcp_server_name} → {zone} (org {org_id}, team {team_id})
  - **Dev instance:** {name} → {zone} (org {org_id}) — no MCP, API-only (if applicable)
  - **Rule:** Production for live ops, dev for UTIL/test scenarios
  ```

**If n8n:**
- Check `.mcp.json` for n8n MCP server entry
- Note workflow IDs from checkpoint

**If Trigger.dev:**
- Check `trigger.config.ts` for registered tasks
- Note deployment status

## Step 5.5: Load ALL Memory Files (Bulk Context Load)

With 1M token context, memory files cost ~1,800 tokens total (~0.2% of budget). Load ALL of them to eliminate recall failures.

**Mandatory:** Read every `.md` file in the memory directory. This includes trigger files, feedback files, reference files, and project files. The cost is negligible; the benefit is that every learned pattern is available at decision time without requiring recall.

```bash
ls -1 {memory_directory}/*.md
```

Read each file. This replaces the previous selective loading approach.

**Domain-specific extras (load when applicable):**

| File | When |
|---|---|
| `workspace/projects/platform/context/brand.md` | Platform work: canonical company/domain/contact names |

### Platform Brand Verification (when type = platform)

After reading `brand.md`, include this block in the Step 6 summary:

```
### Brand Constants (verified)
- Company: {from brand.md}
- Domain: {from brand.md}
- Contact: {from infrastructure.yaml or brand.md}
```

Do not proceed with platform work if brand.md cannot be read.

## Step 5.6: Load Recent Session History

Load the most recent session context for continuity. Cost: ~1-2K tokens (~0.2% of budget).

1. Read the most recent session log from `docs/sessions/` that mentions this project:
   ```bash
   ls docs/sessions/*.md | sort -r | head -3
   ```
   Scan the most recent 3 for entries mentioning this project. Read the relevant entry.

2. Read the most recent full checkpoint for this project (from Step 1, but read the FULL file, not just next_steps).

3. Cross-reference the project's `open_questions` from the checkpoint with `docs/friction-register.md`. If any open question matches a previously-resolved friction entry, surface it: "Note: '{question}' was resolved on {date} via {fix}. Applying known solution."

This gives the agent continuity with the previous session's work, decisions, and friction events without depending on checkpoint quality alone.

## Step 5.7: Pre-Load Orchestrator Skill Pack Overview

Based on the `orchestrator:` field in `infrastructure.yaml`, pre-load the relevant skill pack's SKILL.md overview. This tells the agent what modules and capabilities are available without requiring a manual read later.

| Orchestrator | File to Read |
|---|---|
| `make` | `.claude/skills/skil_make-pack/SKILL.md` |
| `n8n` | `.claude/skills/skil_n8n-pack/SKILL.md` |
| `trigger-dev` | `.claude/skills/skil_trigger-pack/SKILL.md` |

Only read the SKILL.md overview (~100-350 tokens), not all modules. Modules still load on demand when needed for specific tasks.

Include a **Loaded feedback memories: {list}** line in Step 6 summary.

## Step 6: Summarize

### 6a — Session Header (output this FIRST)

Before the detailed summary, output the compact session header and auto-rename the chat.

1. Determine scope code from the project name (see Scope Codes table above)
2. Derive a 2-4 word task slug from: `next_steps[0]` in the YAML/checkpoint, or the checkpoint topic if no next steps exist. Use lowercase hyphenated words (e.g., `a3-wrap-up`, `client-portal`, `trigger-build`)
3. Output the header block:

```
---
**[{SCOPE}] {task-desc}**
Scope: {project-name} · {orchestrator}
Skills: {skills auto-loaded by name, e.g. skil_make-pack | none}
Open: {N spec(s) in build/test, or "none"} | Comms: {N days stale or "current"}
Memories: {list of applied feedback memory file names}
---
```

4. Call the rename script to retitle this chat:

```bash
python tools/rename-chat.py "{scope}--{task-desc}"
```

Example for meji-media with A3 work next: header shows `[MEJI] a3-wrap-up` and script runs `python tools/rename-chat.py "meji--a3-wrap-up"`.

### 6b — Full Context Summary

Present the detailed context summary to the user:

```
## $ARGUMENTS — Session Context

**Project type:** {client | internal | platform}
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
