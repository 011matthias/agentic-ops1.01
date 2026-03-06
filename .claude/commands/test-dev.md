---
description: "Live Dev Test: Test Automation with Real APIs"
argument-hint: <client-name> <automation-id>
---

# Live Dev Test

Execute a live development test with real APIs. Delegates to the `testing-agent`.

## Prerequisites
- Client name: first argument
- Automation ID: second argument

If arguments are missing, ask the user.

## Execute

Invoke the `testing-agent` with:
- **Task:** `test-dev`
- **Client:** parsed from arguments
- **Automation ID:** parsed from arguments

The testing-agent handles: parsing test records, showing confirmation preview, executing the automation, verifying results, and updating status to `tested_dev`.
