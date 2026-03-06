# Handover Format Checker

Validates that a Make.com blueprint is structurally correct for UI import (client handover). Catches format issues that only surface when a client tries to paste the blueprint into Make.com's "Import Blueprint" dialog.

## When to Use

- Before any client handover (mandatory)
- After building a blueprint via API deployment that will also ship as a handover file
- As part of pre-client-review checklist

## Procedure

### Step 1: Check Top-Level Keys

Parse the blueprint JSON and verify:

| Key | Required | Valid Values |
|-----|----------|-------------|
| `flow` | Yes | Non-empty array of modules |
| `metadata` | Yes | Object with `instant`, `version`, `designer`, `scenario` |
| `scheduling` | Yes (UI import) | `{"type": "immediately"}` for webhook, `{"type": "indefinitely", "interval": N}` for polling |
| `interface` | Yes (UI import) | `{"input": [], "output": []}` |
| `name` | No | Omit — not required for import and flagged as invalid by API schema validator |

Any other top-level key = ERROR.

### Step 2: Check Metadata Structure

```
metadata.version        → must be 1
metadata.instant        → must be boolean
metadata.designer       → must exist with "orphans": []
metadata.scenario       → must exist with at minimum:
  - dataloss (boolean)
  - maxErrors (number)
  - autoCommit (boolean)
  - roundtrips (number)
  - sequential (boolean)
  - confidential (boolean)
  - autoCommitTriggerLast (boolean)
```

| Check | Severity | Issue |
|-------|----------|-------|
| `metadata.designer` missing | ERROR | UI import will fail — cannot render canvas |
| `metadata.designer.orphans` missing | ERROR | UI import may fail |
| `metadata.scenario.dataloss` missing | WARN | May cause validation error on import |
| `metadata.instant` doesn't match trigger type | WARN | Webhook trigger should have `instant: true`, scheduler should have `instant: false` |

### Step 3: Check Scheduling Consistency

```
If flow[0].module starts with "gateway:" → scheduling.type must be "immediately"
If flow[0].module is a polling trigger   → scheduling.type must be "indefinitely" with interval > 0
```

| Check | Severity | Issue |
|-------|----------|-------|
| `scheduling` missing | ERROR | Required for UI import |
| `scheduling.type` mismatches trigger | WARN | Scenario may behave unexpectedly |

### Step 4: Check Module Handover Readiness

For each module in the `flow` array:

**Webhook modules** (`gateway:CustomWebHook`):

| Check | Severity | Issue |
|-------|----------|-------|
| `parameters.hook` is not `null` | ERROR | Hardcoded dev webhook ID — client can't use this |
| `metadata.restore.parameters.hook.label` missing | WARN | No friendly label — client sees blank webhook prompt |

**Connection modules** (any module with `parameters.__IMTCONN__`):

| Check | Severity | Issue |
|-------|----------|-------|
| `metadata.restore.parameters.__IMTCONN__` missing | WARN | No connection prompt label — client may not know which account to connect |

**Data store modules** (`datastore:*`):

| Check | Severity | Issue |
|-------|----------|-------|
| `parameters.datastore` is a hardcoded integer | WARN | Dev data store ID — client will need to select their own |

### Step 5: Check Module ID Uniqueness

Collect all module IDs from `flow` (including `onerror` handlers). Flag duplicates.

| Check | Severity | Issue |
|-------|----------|-------|
| Duplicate module ID found | ERROR | Will silently break module references |

## Output

```markdown
## Handover Format Checker Report

**Blueprint:** {filename}
**Status:** {PASS | WARN | FAIL}
**Modules:** {count} main + {count} error handlers

### Top-Level Structure
| Check | Status |
|-------|--------|
| `flow` present | PASS/FAIL |
| `metadata` complete | PASS/FAIL |
| `scheduling` present | PASS/FAIL |
| `interface` present | PASS/FAIL |

### Metadata
| Check | Status |
|-------|--------|
| `designer.orphans` | PASS/FAIL |
| `scenario.dataloss` | PASS/WARN |
| `instant` matches trigger | PASS/WARN |

### Handover Readiness
| Severity | Module ID | Issue | Suggested Fix |
|----------|-----------|-------|---------------|
| ERROR | 1 | hook is hardcoded (2515332) | Set to null, add restore label |
| WARN | 14 | No restore label for __IMTCONN__ | Add restore.parameters.__IMTCONN__.label |
```

## Common Fixes

| Issue | Fix |
|-------|-----|
| Missing `designer.orphans` | Add `"designer": {"orphans": []}` to `metadata` |
| Missing `dataloss` | Add `"dataloss": false` to `metadata.scenario` |
| Missing `scheduling` | Add `"scheduling": {"type": "immediately"}` (webhook) or `{"type": "indefinitely", "interval": N}` (polling) |
| Missing `interface` | Add `"interface": {"input": [], "output": []}` |
| Hardcoded webhook ID | Set `parameters.hook` to `null`, add `metadata.restore.parameters.hook.label` |
| No connection restore label | Add `metadata.restore.parameters.__IMTCONN__` with `label` |
