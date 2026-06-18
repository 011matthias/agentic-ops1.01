---
description: Review recent work, identify friction, and build system improvements. The self-annealing development loop.
argument-hint: "[project-name] [--audit-only]"
---

# System Development Loop

Structured system improvement session. Reviews recent work, identifies where human involvement was required but shouldn't have been, and builds primitives to close those gaps. It also self-anneals: it audits the toolkit for internal contradiction and bloat, and measures whether the system is converging cycle-over-cycle (sharper) rather than just accreting (bigger).

## Fixed points (never annealed away)

This loop sharpens the toolkit; it never relaxes the constraints that make the sharpening safe. Held fixed across every cycle:

- **Approval gate** — Phase 4 designs are proposed, never auto-built; the human approves the diff.
- **Reversibility** — every change ships as a reviewable PR; no auto-commit to main (`rule_no_auto_commit` B6).
- **Evidence basis** — every proposed change cites a friction-register row, a metric, or an audit finding. No speculative self-refactoring.
- **Guardrails preserved** — safety/quality gates and honesty constraints are NOT "friction to streamline"; friction that protects correctness stays.
- **No value drift** — the cycle changes tools, never purpose or character.
- **Goodhart guard** — "fewer assets" is a direction, not a number to game: a deletion still needs a cited finding + Phase-4 approval.

Annealing converges only because these are held fixed.

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
3. **`--metrics-only`** (optional): Run `tools/anneal-metrics.py` only — print the convergence row + drift, then stop. The cheap "where do we stand?" check.

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
- **Convergence + drift baseline**: run `uv run tools/anneal-metrics.py --format json` for asset counts, friction recurrence, and documented-vs-actual drift; read the latest row of `docs/anneal-ledger.md` for the prior cycle's numbers.

### Ask the user:
> "What required your involvement in recent sessions that the system should have handled autonomously? List the friction points — even small ones."

## Phase 1.5: Toolkit-Introspection Audit

Friction in the register is REACTIVE evidence (what already broke). This phase is PROACTIVE: audit the toolkit itself for defects that may never have been logged. Combine the deterministic drift from `anneal-metrics.py` with these judgment checks:

1. **Documented-vs-actual drift** (from the tool): CLAUDE.md advertised counts vs real asset counts; rules-LOC vs the stated budget. Already computed — read it off the metrics output.
2. **Rule contradictions**: scan `.claude/rules/*.md` for two rules prescribing different behavior for the same trigger (the tool can only hint via keyword overlap; this is a judgment call).
3. **Overlapping / redundant skills**: skills whose `description` WHEN-clauses overlap enough to confuse routing. The make-pack / n8n-pack consolidation is the template for the fix.
4. **Overloaded skill**: a `SKILL.md` over the ~500-line norm, or one doing three unrelated jobs → split candidate.
5. **Stale conventions**: a count, path, or budget cited in CLAUDE.md / a rule / DECISION-TREE that no longer matches reality.

Add each confirmed toolkit defect to the friction list as a synthetic entry (Client = `system`, Type = `toolkit-drift` or `toolkit-redundancy`) so Phases 2-4 treat it like any other defect. **`--audit-only` includes these and stops at Phase 3.**

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
| **Toolkit redundancy / contradiction** | Two rules conflict, two skills overlap, or a cited count/convention drifted | **Consolidate or delete** (not create) |

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

3. **Classify the direction** of each fix: `CONSOLIDATE` / `DELETE` / `EXTEND` / `CREATE`. Trend toward fewer, sharper assets — merging two overlapping skills or deleting a dead rule is as valuable as adding one. If this round only ADDS, it is accreting, not annealing: every `CREATE` must first rule out a `CONSOLIDATE` or `DELETE` that resolves the same defect.

4. Draft the specification (a primitive spec, or a consolidation/deletion plan):
   - File path(s) — created, edited, or removed
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
3. **Report rules-LOC** via `uv run tools/anneal-metrics.py` — there is no repo-wide LOC budget (the legacy "under 500" and DECISION-TREE's "250" both contradicted the ~2.2k real total and were retired 2026-06-18). The discipline is a per-file soft ceiling (~250 lines) plus "no duplicated bans across rules"; the tool surfaces per-file overages (split candidates) as an advisory, not as drift. Treat a NEW duplicated ban or a freshly oversized rule file as the finding to resolve by consolidation.

## Phase 6.5: Convergence Measurement

Record whether THIS cycle moved the system toward "sharper", not just "bigger".

1. Run `uv run tools/anneal-metrics.py --append` to append this cycle's row to `docs/anneal-ledger.md`. The tool fills every column except **Top Finding**.
2. Compare to the prior row (the tool computes `NetD`, `ChangeSet`, `Smaller?`). Apply the **convergence test**:
   - Is this cycle's change-set SMALLER than the last? (settling, not thrashing)
   - Are asset count (`NetD` ≤ 0 preferred), `Drift`, `Unres`, and recurrence stable or falling?
3. Write the verdict — **converging** (smaller changes, falling drift/asset count) or **oscillating / accreting** (growing change-set, the same defects recurring, asset count climbing) — and fill the row's `Top Finding` with the cycle's headline.
4. If a metric is rising monotonically or oscillating, NAME it and recommend pausing changes to that area next cycle rather than tweaking it again.

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

### Convergence (this cycle)
{the appended docs/anneal-ledger.md row} — verdict: {converging | oscillating | accreting}.
{one line on the trend, e.g. "net asset -2 (merged 2 skills), drift 3->1, change-set smaller than last: yes"}

### Next /system-dev session should focus on:
- [Priority items for next round — Phase 0 will surface these automatically]
```
