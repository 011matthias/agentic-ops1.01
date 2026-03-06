---
description: "Live Production Test: Test Automation in Production"
argument-hint: <client-name> <automation-id>
---

# Live Production Test

Execute a limited production test. Delegates to the `testing-agent`.

## Prerequisites
- Client name: first argument
- Automation ID: second argument

If arguments are missing, ask the user.

## Safety

**CRITICAL:** This command tests against production. The testing-agent will:
1. Require typing "PRODUCTION" to confirm
2. Use minimal test records
3. Monitor logs during execution
4. Verify changes and update status to `tested_production`

## Execute

Invoke the `testing-agent` with:
- **Task:** `test-production`
- **Client:** parsed from arguments
- **Automation ID:** parsed from arguments
