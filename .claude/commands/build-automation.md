---
description: End-to-end automation building via build-orchestrator agent
argument-hint: <client-name> [--skip-spec] [--skip-test] [--skip-deploy]
---

# Build Automation

Orchestrates the complete automation development workflow from requirements to deployment using the **build-orchestrator** agent.

## Context

- Working directory: !`pwd`
- Client name: $ARGUMENTS

## Overview

This command invokes the **build-orchestrator agent** which manages the full automation lifecycle:

```
Requirements → Spec → Code → Test (Local) → Test (Dev) → Docs → Deploy → Verify
```

The orchestrator coordinates specialized agents for each phase and manages handoffs between them.

## Prerequisites

If $ARGUMENTS is empty, ask for client name.

Verify client exists:
- `workspace/clients/$ARGUMENTS/` should exist
- If not, suggest `/new-client $ARGUMENTS` first

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
1. **Client** (required): e.g., `herbox`, `uplifted-consulting`
2. **`--skip-spec`** (optional): Use existing spec, skip to implementation
3. **`--skip-test`** (optional): Skip testing phase (not recommended)
4. **`--skip-deploy`** (optional): Stop before deployment

## Main Workflow: Invoke Build Orchestrator

Launch the **build-orchestrator** agent to manage the complete workflow:

```
Using Task tool:
  Agent: build-orchestrator

  Prompt:
    Build automation for client: {client}

    Options:
    - Skip spec: {yes|no}
    - Skip test: {yes|no}
    - Skip deploy: {yes|no}

    Process:
    1. Create session and handoff directory
    2. Phase 1: Plan (spec-creator) - unless --skip-spec
    3. Phase 2: Implement (implementation-agent)
    4. Phase 3: Test - Local (testing-agent) - unless --skip-test
    5. Phase 3.5: Test - Dev (testing-agent with /test-dev) - unless --skip-test
    6. Phase 4: Document (doc-generator)
    7. Phase 5: Deploy (deployer) - unless --skip-deploy
    8. Phase 6: Verify (status-check)

    After each phase:
    - Generate phase report
    - Call project-manager to update status
    - Get user approval at key checkpoints

    Handle errors:
    - Test failures: invoke bug-fixer, retry
    - Deploy failures: invoke bug-fixer, retry

    Generate session summary with all artifacts
```

## What the Orchestrator Does

The build-orchestrator agent will:

1. **Create a session** with handoff directory for tracking
2. **Coordinate all phases** with specialized agents
3. **Manage handoffs** between phases via reports
4. **Get user approvals** at key checkpoints (spec, code review)
5. **Handle errors** by invoking bug-fixer when needed
6. **Call project-manager** after each phase to update status
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
| Plan | spec-creator | Spec file | `planned` |
| Implement | implementation-agent | Code + tests | `implemented` |
| Test - Local | testing-agent | Local test report | `tested_locally` |
| Test - Dev | testing-agent + /test-dev | Dev test report (real APIs) | `tested_dev` |
| Fix (if needed) | bug-fixer | Fixed code | (revert to previous) |
| Document | doc-generator | Technical + client docs | `documentation_created` |
| Deploy | deployer | Live service | `deployed` |
| Verify | status-check | Health confirmation | `tested_live` |

**Testing Phases Explained:**
- **Local Testing (tested_locally)**: Unit tests + dry-run with mocked/stubbed data
- **Dev Testing (tested_dev)**: Live test with real APIs in dev environment (via /test-dev)
- **Production Testing (tested_production)**: Limited live test in production
- **Live Testing (tested_live)**: Verified working in production via logs

## Notes

- This command delegates all complexity to the build-orchestrator agent
- The orchestrator manages specialized agents for each phase
- Session state is saved for resumability
- All progress tracked via project-manager
- Handoff reports provide audit trail
