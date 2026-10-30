# IML Reference Checker

Validates that all `{{N.field}}` IML expressions in a blueprint reference valid, reachable modules.

## Procedure

### Step 1: Build Module Graph

Parse the blueprint's `flow` array to build a directed graph:

```
For each module in flow:
  - Record: module_id, module_type, position in flow
  - Record connections: which modules feed into this one (from routes, filters, flow order)

For routers:
  - Each route creates a separate execution path
  - Modules in route A cannot reference modules in route B (they're parallel)

For filters:
  - Filters sit between two modules
  - A filter that evaluates to false means downstream modules don't execute
```

Result: A graph where each node is a module ID and edges represent data flow.

### Step 2: Extract All IML References

Scan every module's `mapper`, `parameters`, and filter conditions for IML patterns:

```
Pattern: {{N.field}} or {{N.field.subfield}}
  - N = module ID (numeric)
  - field = field name
  - subfield = nested field (optional)

Also detect:
  - {{N}} — bare module reference (usually wrong unless N is a SetVariable)
  - {{N[index]}} — array access (valid but check N exists)
  - Function calls: {{functionName(N.field; ...)}} — N.field is still a reference
```

Build a list: `{referencing_module_id, referenced_module_id, field_name, full_expression}`

### Step 3: Validate References

For each IML reference:

| Check | Severity | Issue |
|-------|----------|-------|
| Module N doesn't exist in the flow | ERROR | Reference to non-existent module |
| Module N exists but is not upstream (not reachable via graph edges) | ERROR | Reference to unreachable module — data won't be available |
| Module N is in a different router branch | ERROR | Cross-branch reference — module N may not have executed |
| Module N is a number < 10 and field is also numeric | WARN | Numeric key ambiguity — `{{1.0}}` may be interpreted as module 1, field "0" or as a decimal number. See IML-GOTCHAS.md. |
| Module N is downstream (comes after the referencing module) | ERROR | Forward reference — data doesn't exist yet |
| Reference uses `{{N.__ROW_NUMBER__}}` without guard filter | WARN | If N is filterRows/searchRows, empty results will make this undefined |

### Step 4: Detect Common Anti-Patterns

**Numeric key ambiguity (CRITICAL for Make.com):**
```
If any reference matches: {{N.DIGIT}} where DIGIT is 0-9
  → FLAG as WARN: "Numeric key ambiguity — consider using getCell pattern instead"
  → See FIX-PATTERNS.md EX-1
```

**Orphaned SetVariable references:**
```
If a SetVariable2 module (util:SetVariable2) exists:
  - Check that at least one downstream module references it
  - If not → WARN: "SetVariable has no consumers"
```

**Missing scope on SetVariable:**
```
If util:SetVariable2 lacks scope: "roundtrip":
  → WARN: "SetVariable may not persist. Add scope: roundtrip"
  → See IML-GOTCHAS.md
```

## Output

```markdown
## IML Reference Checker Report

**Scenario:** {name} (ID: {id})
**Modules:** {count}
**IML References:** {count}

| Severity | Module | Expression | Issue |
|----------|--------|-----------|-------|
| ERROR | 14 (getCell) | `{{2.__ROW_NUMBER__}}` | Module 2 (filterRows) may return empty — no guard filter detected |
| WARN | 7 (HTTP) | `{{1.0}}` | Numeric key ambiguity — field "0" may be interpreted as module reference |
| ERROR | 52 (SetVariable) | `{{99.value}}` | Module 99 does not exist in flow |
```

## Limitations

- This checker validates structural correctness (do the references point to valid modules?), not semantic correctness (is the right field being used for the right purpose?)
- Nested IML functions (e.g., `{{if(length(get(52.config; "ai_enabled")); ...)}}`) are parsed for module references but the function logic is not validated
- Filter conditions are checked for references but not for logical correctness
