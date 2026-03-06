---
description: Test Automation
argument-hint: <client-name> <automation-id>
---

# Test Automation

Run local tests for an automation. Delegates to the `testing-agent`.

## Prerequisites
- Client name: first argument (e.g., `herbox-sweden`)
- Automation ID: second argument (e.g., `a1`)

If arguments are missing, ask the user.

## Execute

Invoke the `testing-agent` with:
- **Task:** `test`
- **Client:** parsed from arguments
- **Automation ID:** parsed from arguments

The testing-agent handles: finding tests, running pytest, interpreting results, and updating status.
