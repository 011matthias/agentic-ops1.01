---
description: Save conversation checkpoint for session continuity. Enables seamless handoff between agent sessions.
argument-hint: [topic-name]
---

Create a checkpoint that captures the current conversation state for future session continuity.

## Determine Topic

1. If `$ARGUMENTS` is provided, use it as the topic name
2. If no argument, infer the topic from what we've been working on in this conversation
3. Format topic as title case (e.g., "Fortnox API Integration")

## Check for Mini Mode

If `$ARGUMENTS` contains `--mini`:
1. Strip `--mini` from arguments; remainder is the topic
2. Use **MINI mode** — a lightweight checkpoint that preserves essential state without full analysis
3. Skip: Friction Self-Audit, Comms Staleness Check, Strategic Feedback sections
4. Write a shorter checkpoint (see Mini-Checkpoint Template below)
5. Use filename: `Mini-Checkpoint-{N}.md` where N = count of existing `Mini-Checkpoint-*.md` files in the folder + 1
6. Session log entry includes `(mini)` suffix: `### Session {N} — {TOPIC} (mini)`
7. Still write/update the context YAML (critical for /resume)
8. Skip directly to Confirm after writing

## Check/Create Folder

1. Check if `docs/[TODAY's DATE] - [TOPIC]/` exists
   - Date format: `YYYY-MM-DD` (e.g., `2026-01-09`)
2. If folder exists: use it
3. If not: create the folder

## Gather Context

Analyze the current conversation and gather:

- **Work Type**: Classify the primary work done this session:
  - `client-dev` — building/testing/deploying/fixing client automations
  - `system-infra` — improving the agentic-ops system itself
  - `comms` — client communication, drafting, comms catch-up
  - `misc` — one-off tasks, research, exploration
- **Summary**: 1-2 sentence overview of work done this session
- **What Was Done**: Categorized list of completed work
- **Key Decisions**: Important choices made with rationale
- **Files Modified**: Table of files created/modified with paths and purpose
- **Current Status**: Where things stand now
- **Next Steps**: Priority actions to continue
- **Files to Read First**: Critical files the next agent should read
- **Open Questions**: Unresolved questions needing attention
- **Reference Materials**: URLs, related docs, plan files

## Friction Self-Audit

Before writing the checkpoint, review the conversation for friction events. Include any events already noted mid-session (per the friction logging rule in rule_behaviors.md) plus any newly discovered ones.

1. **Scan for user corrections:** Did the user redirect your approach? ("No, use X instead", "You can just...", "Try Y", "Figure it out")
2. **Scan for user-performed tasks:** Did the user check something you could have checked via fixtures/tools? ("I checked the sheet and...", "The email looks like...")
3. **Scan for missed tools:** Did you ask the user to do something that `tools/make-api.py`, test fixtures, or MCP tools could have done?
4. **Scan for invisible friction:** Slow paths taken, scope creep, verification theater, skipped gates (see friction types in rule_behaviors.md)
5. **Scan for intent misalignment:** Did the user redirect the goal (not just the method)? Did I take exploratory input literally?
6. **Scan for strategic gaps:** Did I start building before questioning whether the approach was right?
7. **Scan for infrastructure deferral:** Did I solve something manually that a tool/script/hook could prevent permanently? Check if similar friction was logged before — if the same manual fix appears 2+ times, it's `infrastructure-deferred`.

For each event found, record:
- **Type:** `agent-deferred`, `missed-tool`, `redundant-escalation`, `slow-path`, `scope-creep`, `verification-theater`, `skipped-gate`, `intent-misalignment`, `over-literal`, `strategic-gap`, `missed-memory-recall`, `infrastructure-deferred`
- **Detected by:** `user` or `agent` (who caught it first)
- **Gate:** Which decision boundary (B1/B2/B3/B4) should have prevented it, or `none`
- **Fix:** `structural` (gate/rule/code), `memory` (feedback file), `documented` (noted), `ext-limit` (platform limitation)

**Regression check:** Before logging, grep `docs/friction-register.md` for previous entries of the same type with Resolved=Yes. If found, mark new entry with `Regression?` = `Yes ({date} fix, {fix type} didn't hold)`.

Include in session log `**Friction:**` line and increment `friction_events`. Append rows to `docs/friction-register.md`:
`| {DATE} | {CLIENT} | {TYPE} | {description} | No | {fix} | {Yes/No (date)} |`
If fix = `memory`, note: "Fragile fix — consider structural alternative."

## Gate Compliance Audit

Review the session for decision boundary application:

1. List each instance where B1 fired (about to ask user → checked tools first)
2. List each instance where B2 fired (about to mark done → verified behavior)
3. List each instance where B3 fired (about to diagnose → read full error)
4. List any instance where a gate SHOULD have fired but didn't

Include in session log: `**Gates:** B1:{N} B2:{N} B3:{N} skipped:{N}`
If skipped > 0, log each as friction type `skipped-gate` with fix type `structural` (this audit is the fix).

After the friction scan and gate audit, compute the **Autonomy Score** for this session:
- Count total human interventions required (friction events above)
- Add one line to the checkpoint's **System Health** section: `Autonomy score: {N} human interventions this session.`
- If N = 0: `Autonomy score: 0 — fully autonomous session.`
- If N > 3: note `(elevated — run /system-dev to close gaps)`

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

### Working Notes
Key findings, investigation results, and intermediate state that would be expensive to re-derive in the next session. Include: failed approaches (and why), partial results, open questions with current best hypothesis.

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
   projects_touched: []
   friction_events: 0
   work_types: []
   ---
   ```

2. Increment `sessions` count, merge projects into `projects_touched`, merge work type into `work_types` (deduplicated)
3. Append:
   ```markdown
   ### Session {N} — {TOPIC}
   **Type:** {work_type}
   **Focus:** {summary from checkpoint}
   **Projects:** {projects touched}
   **Built:** {key deliverables}
   **Friction:** {any friction events, or "None"}
   **Autonomy:** {N} human interventions
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
work_type: "{client-dev|system-infra|comms|misc}"
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

## Update INDEX.md

After writing the session log, maintain `docs/INDEX.md` — a running index of all sessions organized by client/project, kept in descending date order within each section.

1. **Determine section** for this checkpoint:
   - If `work_type = client-dev` and a single client was touched → use that client's name as the section heading
   - If `work_type = system-infra` or multiple clients touched → section heading = `system`
   - If `work_type = comms` for a single client → use that client's name
   - For platform work → section heading = `platform`

2. **Build the row** to insert:
   ```
   | {YYYY-MM-DD} | {Topic} | {work_type} | [→](docs/{DATE}%20-%20{TOPIC}/Checkpoint.md) |
   ```
   URL-encode spaces as `%20` in the link.

3. **Read `docs/INDEX.md`** if it exists. If not, initialize it:
   ```markdown
   # Session Index

   _Auto-updated by /comd_checkpoint. Most recent first within each section._

   ```

4. **Insert the row** at the TOP of the matching section (after the section's table header). If the section doesn't exist yet, add it before the next section (alphabetical order is fine).

5. **Write back** to `docs/INDEX.md`.

**On first run only (INDEX.md doesn't exist yet):** Before inserting the current checkpoint row, do a one-time backfill: scan all `docs/*/Checkpoint.md` files, extract date and topic from each folder name (`YYYY-MM-DD - Topic`), and populate all sections from the existing history. Infer the section from the topic text (client name, "Platform", "System Dev", etc.). Then insert the current row at the top of its section.

## Ops Status Line

After writing the YAML, for each client in `clients_touched`:

1. Read `infrastructure.yaml` — check for `platform` section
2. If `platform` section exists, include a one-line ops status in the checkpoint's **Current Status** section:

> "Platform: {tier} plan, ~{estimated_ops}/{ops_limit} ops/mo ({%}, {GREEN|YELLOW|ORANGE|RED}). Last assessed: {date}."

3. If the verdict is ORANGE or RED, also add to **Next Steps**:

> "Run `/ops-audit {client}` — platform usage is at {%} of limit."

4. If no `platform` section exists but the client uses Make.com/n8n/Trigger.dev, add to **Next Steps**:

> "Run platform feasibility assessment for {client} (no `platform` section in infrastructure.yaml)."

This is a lightweight check — no MCP queries, just reading infrastructure.yaml. For a full audit, use `/ops-audit`.

## Infrastructure Reconciliation

After the ops status line, for each client in `clients_touched` that uses Make.com:

1. Check if MCP server is connected (one ToolSearch check — if not connected, skip silently)
2. Call `scenarios_list` for the client's team ID
3. For each `ship: true` scenario in `infrastructure.yaml`, compare live vs recorded:
   - **Interval:** `scheduling.interval` (live) vs `trigger: scheduled (Ns)` (recorded)
   - **Status:** `isActive` (live) vs `status:` field (recorded)
4. If mismatches found:
   - List them: `"Infrastructure drift: A0 interval is 1800s live but 900s in YAML"`
   - Update `infrastructure.yaml` inline (fix `trigger:`, `status:`, append change to `note:`)
   - Include in checkpoint under **Files Modified**
5. If no mismatches: skip silently (no output needed)
6. If MCP not connected: skip entirely — no spiral, no friction event

This is a lightweight reconciliation. It only checks `ship: true` scenarios (not UTIL/test).

## Comms Staleness Check

After writing the YAML, for each client in `clients_touched`:

1. Read `staleness_days` from the comms block computed above. Skip clients with no comms-log.
2. If any client has `staleness_days >= 4`:

> "{client} comms log is {N} days old (last contact: {date}). Any conversations to log before closing out?"

- If **yes**: use the Quick Capture procedure from COMMS-LOG.md — brief natural-language input, minimal entry, confirm before writing
- If **multiple clients** are stale: list them all, ask once ("Any of these need logging?")
- If **no**: proceed to Confirm

If all clients are under 4 days, skip this section.

## Mini-Checkpoint Template

When in MINI mode, use this shorter format instead of the full checkpoint template:

```markdown
# Mini-Checkpoint: [Topic Name]

**Date:** [TODAY's DATE]
**Status:** [Current Phase/Status]
**Type:** mini

---

## Summary
[1-2 sentence overview]

## What Was Done
- [Item 1]
- [Item 2]
- [Item 3]

## Current Status
[Where things stand]

## Next Steps
1. [Priority 1]
2. [Priority 2]

## Files to Read First
- [path/to/critical/file]
```

## Confirm

After creating the checkpoint, output ONE confirmation line as a VSCode-clickable markdown link (substitute actual date and topic values).

**IMPORTANT:** URL-encode spaces as `%20` in the link URL. Spaces in paths break markdown link rendering in VSCode.

- Full mode: `Checkpoint saved → [Checkpoint.md](docs/{DATE}%20-%20{TOPIC}/Checkpoint.md)` (replace spaces in TOPIC with `%20` too)
- Mini mode: `Mini-checkpoint saved → [Mini-Checkpoint-{N}.md](docs/{DATE}%20-%20{TOPIC}/Mini-Checkpoint-{N}.md)`

Where `{DATE}` = resolved date (e.g. `2026-03-15`) and `{TOPIC}` = resolved topic title. Example: `[Checkpoint.md](docs/2026-03-15%20-%20Meji%20Media%20Build/Checkpoint.md)`
