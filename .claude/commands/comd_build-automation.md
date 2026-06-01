---
description: End-to-end automation building via agnt_build-orchestrator agent
argument-hint: <project-name> [--skip-spec] [--skip-test] [--skip-deploy]
---

# Build Automation

Orchestrates the complete automation development workflow from requirements to deployment using the **agnt_build-orchestrator** agent.

## Context

- Working directory: !`pwd`
- Project name: $ARGUMENTS

## Overview

This command invokes the **agnt_build-orchestrator agent** which manages the full automation lifecycle:

```
Requirements → Spec → Code → Test (Local) → Test (Dev) → Docs → Deploy → Verify
```

The orchestrator coordinates specialized agents for each phase and manages handoffs between them.

## Prerequisites

If $ARGUMENTS is empty, ask for project name.

Resolve project directory — check in order:
1. `workspace/clients/$ARGUMENTS/` — for `type: client` projects
2. `workspace/projects/$ARGUMENTS/` — for `type: internal` or `type: platform` projects

If neither exists, suggest `/new-client $ARGUMENTS --type [client|internal|platform]`

## Important: Does Not Auto-Build Everything

⚠️ **This command does NOT automatically build all automations** in the client's status file.

When you run `/build-automation herbox`, the orchestrator will:

1. **Ask what you want to build:**
   - New automation from requirements?
   - Existing automation by ID (e.g., `a6.1`, `a8`)?

2. **Check status before proceeding:**
   - If `planned`: "Are requirements ready?"
   - If `production_ready`: "What needs updating?"
   - If core business op: "Confirm client approval"

3. **Require your approval at each phase:**
   - After spec creation
   - After code generation
   - Before deployment

**Safe to run anytime** - it will not proceed without your explicit input.

## Parse Arguments

Parse $ARGUMENTS for:
1. **Project** (required): e.g., `herbox`, `uplifted-consulting`, `platform`
2. **`--skip-spec`** (optional): Use existing spec, skip to implementation
3. **`--skip-test`** (optional): Skip testing phase (not recommended)
4. **`--skip-deploy`** (optional): Stop before deployment

## Main Workflow: Invoke Build Orchestrator

Launch the **agnt_build-orchestrator** agent to manage the complete workflow:

```
Using Task tool:
  Agent: agnt_build-orchestrator

  Prompt:
    Build automation for client: {client}

    Options:
    - Skip spec: {yes|no}
    - Skip test: {yes|no}
    - Skip deploy: {yes|no}

    Process:
    1. Create session and handoff directory
    2. Phase 1: Plan (skil_spec-creator) - unless --skip-spec
    3. Phase 1.5: Intent review (agnt_intent-reviewer) — between spec creation and implementation, route the spec through intent-reviewer to catch over-literal / intent-misalignment / strategic-gap patterns BEFORE the builders spend effort. Skip ONLY if --skip-spec is also set (no spec written this session means no intent diff to audit). If reviewer returns a FAIL list, halt Phase 2 until the spec is reconciled or the user explicitly waives the findings.
    4. Phase 2: Implement — route by orchestrator (see routing table below):
       - Make.com → agnt_make-builder
       - n8n → agnt_n8n-builder
       - Trigger.dev / FastAPI → agnt_implementation-agent
    5. Phase 3: Test - Local (agnt_testing-agent) - unless --skip-test
    6. Phase 3.5: Test - Dev (agnt_testing-agent with /test dev) - unless --skip-test
    7. Phase 4: Deploy (agnt_deployer) - unless --skip-deploy
    8. Phase 5: Verify (status-check)

    After each phase:
    - Generate phase report
    - Update spec frontmatter (stage, last_changes, next_steps)
    - Get user approval at key checkpoints

    Handle errors:
    - Test failures: invoke agnt_bug-fixer, retry
    - Deploy failures: invoke agnt_bug-fixer, retry

    Generate session summary with all artifacts
```

## What the Orchestrator Does

The agnt_build-orchestrator agent will:

1. **Create a session** with handoff directory for tracking
2. **Coordinate all phases** with specialized agents
3. **Manage handoffs** between phases via reports
4. **Get user approvals** at key checkpoints (spec, code review)
5. **Handle errors** by invoking agnt_bug-fixer when needed
6. **Update spec frontmatter** after each phase (stage, last_changes, next_steps)
7. **Generate comprehensive reports** for each phase

## Phase Reports

The orchestrator generates reports in `.claude/handoffs/{session-id}/`:
- `phase1-plan-report.md`
- `phase2-implementation-report.md`
- `phase3-test-report.md` (local testing)
- `phase3.5-dev-test-report.md` (dev testing with real APIs)
- `phase4-docs-report.md`
- `phase5-deploy-report.md`
- `phase6-verify-report.md`
- `session-summary.md`

## User Interaction

The orchestrator will prompt for approval at:
- **After spec creation**: "Does this capture your requirements?"
- **After code generation**: "Does this match the spec?"
- **Before deployment**: "Ready to deploy to production?"
- **On test failures**: "Fix bugs or skip testing?"

## Skip Options

| Option | Use When |
|--------|----------|
| `--skip-spec` | Spec already exists, jump to implementation |
| `--skip-test` | Code already tested, proceed to docs (risky) |
| `--skip-deploy` | Want to review before deploying |

## Quick Reference

| Phase | Agent | Output | Status Update |
|-------|-------|--------|---------------|
| Plan | skil_spec-creator | Spec file | `planned` |
| Intent review | agnt_intent-reviewer | `OK` or intent findings list | (halts on FAIL) |
| Implement (Make.com) | agnt_make-builder | Blueprint + deploy + build report | `implemented` |
| Implement (n8n) | agnt_n8n-builder | Workflow JSON + build report | `implemented` |
| Implement (Trigger.dev / FastAPI) | agnt_implementation-agent | Code + tests | `implemented` |
| Test - Local | agnt_testing-agent | Local test report | `tested_locally` |
| Test - Dev | agnt_testing-agent + /test dev | Dev test report (real APIs) | `tested_dev` |
| Fix (if needed) | agnt_bug-fixer | Fixed code | (revert to previous) |
| Deploy | agnt_deployer | Live service | `deployed` |
| Verify | status-check | Health confirmation | `tested_live` |

**Testing Phases Explained:**
- **Local Testing (tested_locally)**: Unit tests + dry-run with mocked/stubbed data
- **Dev Testing (tested_dev)**: Live test with real APIs in dev environment (via /test-dev)
- **Production Testing (tested_production)**: Limited live test in production
- **Live Testing (tested_live)**: Verified working in production via logs

## Notes

- This command delegates all complexity to the agnt_build-orchestrator agent
- The orchestrator manages specialized agents for each phase
- Session state is saved for resumability
- All progress tracked via spec frontmatter (stage field)
- Handoff reports provide audit trail
