# Data Store Reconciler

Compares data store field references in a blueprint against the actual data store schema.

## Procedure

### Step 1: Extract Blueprint Data Store References

Parse the blueprint's `flow` array. For each module where `module` starts with `datastore:`:

```
For datastore:GetRecord modules:
  - Extract the `store` parameter (data store ID)
  - Extract referenced fields from the mapper and downstream IML expressions
  - Note: downstream modules reference GetRecord output as {{N.field_name}}

For datastore:AddRecord / datastore:UpdateRecord modules:
  - Extract the `store` parameter (data store ID)
  - Extract all field names from the mapper (input fields being written)
```

Also scan ALL modules for IML expressions referencing data store output:
- Pattern: `{{N.field_name}}` where N is a data store module ID

### Step 2: Fetch Actual Schema

```
1. data-stores_get(storeId) → extract datastructureId
2. data-structures_get(datastructureId) → extract spec array
3. Build a set of valid field names from the spec
```

### Step 3: Compare

For each field referenced in the blueprint:

| Check | Severity | Issue |
|-------|----------|-------|
| Field referenced but not in schema | ERROR | Missing field — will fail at runtime |
| Field in schema but never referenced | INFO | Unused field — no action needed unless it should be used |
| Field type mismatch (e.g., reading number as text) | WARN | May cause unexpected behavior |
| Data store ID in blueprint doesn't match any existing store | ERROR | Wrong store ID |

### Step 4: Cross-Scenario Check (Optional)

If multiple scenarios use the same data store, compare their field references:

```
For each data store used across scenarios:
  - Collect all field references from all scenarios
  - Flag fields referenced in one scenario but not others (may indicate incomplete migration)
  - Flag fields written in one scenario but never read (may be dead code)
```

## Output

```markdown
## Data Store Reconciler Report

**Data Store:** {name} (ID: {id})
**Schema Fields:** {count}
**Blueprint References:** {count unique fields}

| Severity | Field | Issue | Blueprint Module |
|----------|-------|-------|-----------------|
| ERROR | `new_config_field` | Referenced in module 52 but not in schema | 52 (SetVariable) |
| WARN | `legacy_field` | In schema but never referenced | — |
```

## Auto-Fix

For ERROR findings (missing field), automatically invoke the Schema Evolution module:
1. Add the missing field to the data structure
2. Set a sensible default value based on context
3. Re-run this reconciler to verify the fix
