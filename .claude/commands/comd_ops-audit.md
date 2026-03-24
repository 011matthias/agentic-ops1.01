---
description: Audit operations/execution usage against plan limits using live MCP queries
argument-hint: <project-name>
---

# Operations Audit

Compare actual and estimated platform usage against plan limits for a client. Uses live MCP queries as primary data source.

## Context

- Working directory: !`pwd`
- Project: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, detect project from current path or ask.

Resolve project directory — check in order:
1. `workspace/clients/{project}/` — for `type: client` projects
2. `workspace/projects/{project}/` — for `type: internal` or `type: platform` projects

Read `{project_dir}/infrastructure.yaml`. Check `type:` field:
- If `type: internal` or `type: platform`: note "Operations audit only applies to `type: client` projects with a billing platform." Stop.
- If `type: client`: extract `platform` section (tier, ops_limit, feasibility, assessed date), orchestrator type, and MCP server name.

If no `platform` section exists:
- Warn: "No platform feasibility data found. Run the platform assessment first."
- Offer to run PLATFORM-FEASIBILITY Section A inline, then continue with audit.

## Step 1: Detect Orchestrator and Gather Live Data

### Make.com

1. **List scenarios** — `scenarios_list` via MCP (use production instance MCP server)
   - Record: scenario ID, name, scheduling interval, active/inactive status
   - Count active scenarios, total scenarios

2. **Get scenario details** — For each active scenario, `scenarios_get(scenarioId={id})`
   - Extract: scheduling interval (seconds), module count from blueprint flow
   - If blueprint not accessible via get, use `infrastructure.yaml` data as fallback

3. **Fetch execution history** — `executions_list(scenarioId={id})` for each active scenario
   - Get last 30 days of executions
   - Extract: execution count, total operations consumed, error rate
   - Calculate: avg ops per execution, executions per day

4. **Check resource usage** — `data-stores_list` to count active data stores

### n8n

1. **List workflows** — `n8n_list_workflows` via MCP
   - Record: workflow ID, name, active/inactive, trigger type
   - Count active workflows

2. **Fetch executions** — `n8n_executions` for recent history
   - Get execution counts per workflow
   - Calculate: executions per day, error rate

### Trigger.dev

1. **Check task definitions** — Read `automations/src/trigger/` directory
   - Identify scheduled tasks and their intervals
   - Estimate execution minutes based on frequency x avg duration
   - Compare against plan's execution minute allocation

## Step 2: Calculate Estimates

Load [OPERATIONS-ANALYZER](../skills/make-mcp-tools-expert/modules/OPERATIONS-ANALYZER.md) Section A formulas.

For each active scenario/workflow:

| Metric | Formula |
|--------|---------|
| **Est. monthly executions** (scheduled) | `2,592,000 / interval_seconds` |
| **Est. monthly executions** (webhook) | From actual execution history, or `events_per_month` estimate |
| **Est. monthly ops** (Make.com) | `executions x modules_in_flow` |
| **Idle poll cost** | `executions x modules_before_filter + 1` |

## Step 3: Cross-Check Estimated vs Actual

If execution history is available:

| Check | Threshold | Meaning |
|-------|-----------|---------|
| Actual < 80% of estimate | Formula may overcount (good — headroom exists) |
| Actual 80-120% of estimate | Formula is accurate |
| Actual > 120% of estimate | Formula underestimates — investigate (iterators? error retries?) |

Flag any scenario where actual significantly exceeds estimate.

## Step 4: Generate Report

Output this report to the terminal:

```
=== Ops Audit: {client} ({orchestrator}) ===
Plan: {tier} ({ops_limit} ops/month)
Last assessed: {assessed_date}

Scenario                  | Trigger      | Est. Ops/mo | Actual (30d avg)
--------------------------|--------------|-------------|------------------
{name}                    | {trigger}    | {est}       | {actual}
{name}                    | {trigger}    | {est}       | {actual}
...                       | ...          | ...         | ...
--------------------------|--------------|-------------|------------------
TOTAL                                    | {est_total} | {actual_total}
Plan limit                               | {ops_limit}
Utilization                              | {%} of limit

Resources:
  Active scenarios: {n} / {concurrent_limit or "unlimited"}
  Data stores: {n} / {limit or "unlimited"}

Verdict: {GREEN|YELLOW|ORANGE|RED} ({%} of limit)

{If not GREEN:}
Recommendations:
  1. {specific recommendation}
  2. {alternative}
```

## Step 5: Update Infrastructure

After generating the report, update `infrastructure.yaml`:
- Set `platform.feasibility` to the new verdict
- Set `platform.assessed` to today's date
- Update `platform.notes` with key findings

## Step 6: Flag Drift

If the verdict has changed since last assessment (e.g., was GREEN, now ORANGE):

> "Feasibility verdict changed: {old} -> {new} since {last_assessed}."
> "{Explain what changed — new scenarios added, interval changed, volume increased.}"

## Examples

```bash
# Audit a specific client
/ops-audit meji-media

# Audit current client (auto-detect)
/ops-audit
```

## Notes

- This command is read-heavy (MCP queries) but writes only to infrastructure.yaml
- For Make.com: uses the production MCP server (not dev instance)
- Suggested at `/comd_checkpoint` time as a one-liner in the checkpoint output
- Suggested in `/status-check` as an ops column per scenario
