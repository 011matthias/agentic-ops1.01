---
description: Verify Live Production Status
argument-hint: <client-name> <automation-id>
---

# Verify Live Production Status

Check that a deployed automation is running correctly in production. Delegates to the `testing-agent`.

## Prerequisites
- Client name: first argument
- Automation ID: second argument

If arguments are missing, ask the user.

## Execute

Invoke the `testing-agent` with:
- **Task:** `verify-live`
- **Client:** parsed from arguments
- **Automation ID:** parsed from arguments

The testing-agent handles: checking deployment health, verifying logs, and updating status to `tested_live`.
