---
description: "Test or verify automation"
argument-hint: "[mode] <project-name> <automation-id>"
---

# Test Automation

Run tests or verify an automation. Delegates to the `agnt_testing-agent`.

## Modes

| Mode | What it does |
|------|-------------|
| (default) | Run local unit tests and dry-run |
| `dev` | Live test with real APIs (dev environment) |
| `production` | Limited production test (requires PRODUCTION confirmation) |
| `verify` | Check production deployment health |

## Argument Parsing

Parse the arguments in order. If the first argument matches a mode keyword (`dev`, `production`, `verify`), use it as the mode and shift. Otherwise default to `test`.

Examples:
- `/test meji-media a1` → mode=test, client=meji-media, id=a1
- `/test dev meji-media a1` → mode=test-dev, client=meji-media, id=a1
- `/test production meji-media a1` → mode=test-production, client=meji-media, id=a1
- `/test verify meji-media a1` → mode=verify-live, client=meji-media, id=a1

If arguments are missing, ask the user.

## Execute

Map mode to agnt_testing-agent task:
- (default) → `test`
- `dev` → `test-dev`
- `production` → `test-production`
- `verify` → `verify-live`

Invoke the `agnt_testing-agent` with:
- **Task:** mapped mode
- **Client:** parsed from arguments
- **Automation ID:** parsed from arguments

The agnt_testing-agent handles all test execution, result interpretation, and status updates.
