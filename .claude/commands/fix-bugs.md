---
description: Fix failing tests for an automation using the bug-fixer agent
argument-hint: <client-name> <automation-id>
---

# Fix Bugs

Automatically fix failing tests for an automation using the bug-fixer agent.

## Context

- Working directory: !`pwd`
- Client argument: $ARGUMENTS

## Parse Arguments

Parse $ARGUMENTS for:
1. **Client** (required): e.g., `herbox`, `uplifted-consulting`
2. **Automation ID** (required): e.g., `a6.1`, `a6.2`, `a7`

## Step 1: Verify Location

Ensure we're in the correct location:
```
{workspace_root}/
```

If in a client automations directory, navigate up to workspace root.

## Step 2: Invoke Bug-Fixer Agent

Launch the bug-fixer agent with:
- **Client**: {client}
- **Automation ID**: {automation_id}
- **Task**: Run tests, capture failures, implement fixes

Use the Task tool:
```
Launch agent: bug-fixer

Prompt:
Fix failing tests for automation {automation_id} in client {client}.

Process:
1. Navigate to workspace/clients/{client}/automations
2. Run tests: uv run pytest tests/ -v
3. Capture test failures
4. Analyze root causes
5. Implement fixes
6. Re-run tests to verify
7. Generate fix report

After fixing:
- Call project-manager to update last_changes
- Generate fix report summary
```

## Step 3: Review Fix Report

The bug-fixer agent will output:
- Files modified
- Fixes applied
- Verification results
- Next steps

## Report Results

Output a summary:
```
✓ Bug fix complete: {automation_id}

Files modified:
  - {file_path}
  - {file_path}

Fixes applied:
  - {fix_description}
  - {fix_description}

Test results:
  Before: {X} failures
  After: {Y} failures

Status updated in automation-status.yaml
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Agent not found | Ensure bug-fixer agent exists in `.claude/agents/` |
| Tests can't run | Check for syntax errors, missing dependencies |
| No test file found | Note: No tests to fix |
| Fix doesn't work | May require manual intervention |

## Notes

- This command uses the bug-fixer agent for automated fixing
- The bug-fixer follows minimal changes principle
- Always reviews test output before applying fixes
- Re-runs tests after fixing to verify
- Calls project-manager to track changes

## Alternative Manual Workflow

If you prefer manual fixing:

1. Run tests to see failures:
```bash
cd workspace/clients/{client}/automations
uv run pytest tests/ -v
```

2. Read the failing code and test

3. Implement fix

4. Re-run tests

5. Update status manually
