---
name: build-test-fix
description: Autonomous build-test-diagnose-fix iteration loop with outcome verification. Use after initial implementation to verify both execution success AND output correctness. Classifies errors and outcome mismatches, applies known fixes, retests, and escalates only for novel problems. Works across Make.com, n8n, and Trigger.dev.
---

# Build-Test-Fix Loop

Wraps the iterative cycle that happens after every initial build: execute → check results → **verify outcomes** → classify failure → apply fix → retest. Runs autonomously for up to 3 iterations before escalating.

## When to Use

- After deploying or updating a scenario/workflow — whether it fails OR succeeds on first run
- When execution errors appear in logs (Make.com execution inspector, n8n execution history)
- When the `build` skill completes but the scenario hasn't been verified working
- **After any build where output correctness must be verified** (not just execution success)
- Invoked automatically by the build-orchestrator after implementation phase

## Quick Start

1. Identify the scenario/workflow that needs testing
2. Run it (or trigger via webhook)
3. Read execution results
4. If failure → classify → fix → retest (up to 3 iterations)
5. If success → report and move on

## Escalation Policy

| Condition | Action |
|-----------|--------|
| Iterations 1-3 | Attempt autonomous fix using FIX-PATTERNS registry |
| Same category + same fix approach repeated | Escalate early — going in circles, need different strategy |
| 3 iterations exhausted without resolution | Escalate to user with full diagnosis |
| Novel error (not in registry) | Escalate immediately with context |
| **Critical rule** | Never retry the same fix twice — each iteration must try a DIFFERENT approach |

## Orchestrator Dispatch

| Orchestrator | Execute | Read Results | Fix |
|-------------|---------|-------------|-----|
| **Make.com** | `scenarios_run` or webhook POST | `executions_list` → `executions_get_detail` | Update blueprint via `tools/make-api.py update` (NOT `scenarios_update` — returns 500 on blueprints) |
| **n8n** | MCP workflow execution | n8n execution history via MCP | Update workflow JSON via MCP |
| **Trigger.dev** | `npx trigger.dev@latest dev` + trigger | Task run logs | Edit TypeScript source |

## Modules

| Module | Purpose |
|--------|---------|
| [ITERATION-LOOP.md](modules/ITERATION-LOOP.md) | Step-by-step autonomous loop procedure |
| [OUTCOME-VERIFICATION.md](modules/OUTCOME-VERIFICATION.md) | Verify outputs are correct, not just that execution succeeded |
| [FAILURE-TAXONOMY.md](modules/FAILURE-TAXONOMY.md) | Error classification guide with detection patterns (incl. OUTCOME_MISMATCH) |
| [FIX-PATTERNS.md](modules/FIX-PATTERNS.md) | Registry of known failure→fix mappings |
| [E2E-PIPELINE-VERIFICATION.md](modules/E2E-PIPELINE-VERIFICATION.md) | Multi-scenario pipeline testing (trigger chain mapping, parallel trigger detection) |
