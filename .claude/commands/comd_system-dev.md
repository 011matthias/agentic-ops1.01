---
description: Review recent work, identify friction, and build system improvements. The self-annealing development loop.
argument-hint: "[project-name] [--audit-only]"
---

# System Development Loop

Structured system improvement session. Reviews recent work, identifies where human involvement was required but shouldn't have been, and builds primitives to close those gaps.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Session Header + Auto-Rename

Before anything else, output the session header and rename this chat:

```
---
**[SYS] system-dev**
Scope: system · cross-client
Skills: none auto-loaded
Open: see friction register | Comms: n/a
Memories: (list any loaded below)
---
```

Then call: `python tools/rename-chat.py "sys--system-dev"` (or `sys--system-dev-{client}` if a client arg is present, e.g. `sys--system-dev-meji`).

## Parse Arguments

1. **Client name** (optional): If provided, focus analysis on that client's recent work
2. **`--audit-only`** (optional): Stop after friction analysis — report findings without implementing fixes

## Phase 0: Backlog Triage

Before analyzing new friction, review what was deferred from previous sessions. This prevents items from aging silently in the backlog.

1. Read `docs/friction-register.md` — extract all items where Resolved = "No", "Partially", or contains "Agentic Backlog". Also flag items where Fix = `memory` (these rely on agent recall and are fragile — consider upgrading to structural)
2. For each unresolved item, note date first logged and calculate age in days
3. Present the backlog using the manifest format:
   ```
   BACKLOG (carried forward):
   - [ ] {description} — first logged {date} ({N days ago}) — {status}
   Total: N unresolved items
   ```
4. If any item is >7 days old, flag it: "This item has been deferred for {N} days across ~{M} system-dev sessions."
5. Ask the user: "Which backlog items should we close this session? (Pick 1-2, or explicitly defer with a reason)"

Items deferred here MUST include a reason in the Phase 7 output. "Medium priority" is not a reason — state what blocks resolution or why it's lower priority than the new friction being addressed.

## Phase 1: Gather Friction Signals

Read the following to understand recent work and where friction occurred:

### If project name provided:
- Latest checkpoint: `docs/` folder — find most recent dated folder for this project
- Project specs: `{project_dir}/specs/` — any with `needs_fixes: true` (resolve dir: check `workspace/clients/{project}/` first, then `workspace/projects/{project}/`)
- Project context: `{project_dir}/context/` — infrastructure IDs, test fixtures
- `infrastructure.yaml` if it exists

### Always:
- Recent checkpoints in `docs/` — scan for patterns across sessions
- `MEMORY.md` (auto memory) — scan for already-canonicalized patterns. Prevents proposing duplicates and builds on existing knowledge. Pay attention to: "Key Learnings" sections (patterns already extracted from failures), client-specific notes, and "System Development Infrastructure" entries (what was built in previous sessions)
- `docs/friction-register.md` — structured friction data with types and resolution status. Use as PRIMARY friction source when available (faster and more accurate than scanning all checkpoints).
- `docs/sessions/*.md` — session logs for recent activity patterns and friction events
- `workspace/clients/*/context/build-log.md` and `workspace/projects/*/context/build-log.md` — per-project build iteration history and error patterns
- `.claude/rules/rule_behaviors.md` — refresh the self-annealing framework and behavioral constraints
- Current CLAUDE.md — understand existing primitives

### Ask the user:
> "What required your involvement in recent sessions that the system should have handled autonomously? List the friction points — even small ones."

## Phase 2: Categorize Friction

For each friction point identified (from checkpoints + user input), classify:

| Category | Indicator | Primitive to Create |
|----------|-----------|-------------------|
| **Knowledge gap** | Agent didn't know how to do X | Skill module update or new module |
| **Missing verification** | Bug found only through manual testing | Validator tool (reconciler, linter, checker) |
| **Manual repetitive task** | Same manual steps done 3+ times | Command or skill automation |
| **Behavioral constraint** | Agent did something it shouldn't (or didn't do something it should) | Rule update |
| **Cross-artifact inconsistency** | Blueprint ↔ data store ↔ sheet ↔ template drift | Reconciliation tool |
| **Missing diagnostic** | User had to investigate what agent could have checked | Diagnostic module in relevant skill |

## Phase 3: Prioritize by ROI

Score each friction point:

```
ROI = (frequency × manual_effort_minutes) / estimated_implementation_hours

- frequency: 1 (one-off) → 5 (every session)
- manual_effort: minutes spent each time
- implementation: hours to build the fix
```

Present the ranked list to the user as a table:

| # | Friction Point | Category | Freq | Effort | Impl | ROI | Proposed Fix |
|---|---------------|----------|------|--------|------|-----|-------------|

**If `--audit-only` flag is set: STOP HERE.** Present the table and exit.

## Phase 4: Design Improvements

For each friction point with ROI > 5 (or top 3 if all are low-ROI):

1. Determine the right primitive type:
   - Read `.claude/skills/skil_meta-builder/modules/DECISION-TREE.md` — "Agentic Ops Decision Criteria" section
   - Use the friction category (from Phase 2) as input to the decision tree

2. Check for existing primitives that could be extended instead of creating new ones:
   - Search CLAUDE.md skills/commands/agents lists
   - Search existing skill modules for partial coverage
   - **Always prefer extending over creating**

3. Draft the primitive specification:
   - File path
   - Purpose (1 sentence)
   - Key content/steps
   - How it integrates with existing infrastructure

Present the design to the user for approval before implementing.

## Phase 5: Implement

For each approved improvement:

1. **Read the skil_meta-builder skill** — `.claude/skills/skil_meta-builder/SKILL.md`
2. **Read the appropriate template** — from `skil_meta-builder/templates/`
3. **Read the appropriate guide** — SKILL-GUIDE.md, COMMAND-GUIDE.md, or AGENT-GUIDE.md
4. **Create the primitive** following conventions exactly
5. **Verify** the primitive works against the original friction scenario

## Phase 6: Register

After all primitives are created:

1. **Update CLAUDE.md** — Add new skills/commands/agents to the appropriate sections
2. **Update MEMORY.md** — If any critical patterns were discovered, add them (with dedup check)
3. **Check rules budget** — `wc -l .claude/rules/*.md` — must stay under 500 total

## Phase 7: Checkpoint

Run `/comd_checkpoint System Development` to save the session state.

## Output Format

At the end of the session, summarize:

```
## System Development Summary

### Friction Points Identified: N
### Primitives Created: N
### Primitives Updated: N

| Primitive | Type | Purpose | Friction Resolved |
|-----------|------|---------|-------------------|

### Remaining Friction (deferred)
| Item | First Logged | Age | Reason for Deferral |
|------|-------------|-----|---------------------|
| {description} | {date} | {N days} | {specific reason — not "medium priority"} |

### Next /system-dev session should focus on:
- [Priority items for next round — Phase 0 will surface these automatically]
```
