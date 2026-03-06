# Schema Evolution

Handles the full chain for adding, modifying, or removing data store fields. Eliminates the manual multi-step dance required every time a new field is needed during build.

## When to Use

- During build when a new config field, template field, or tracking field is needed
- When a spec calls for a field that doesn't exist in the data store yet
- When the build-test-fix loop identifies a `SCHEMA_MISMATCH.missing_field` error
- When migrating a data store schema between versions

## Prerequisites

- Data store exists (know the `dataStoreId`)
- MCP tools available for the client's Make.com org

## Procedure: Add New Field(s)

### Step 1: Get Current Schema

```
1. data-stores_get(dataStoreId) → extract `datastructureId`
2. data-structures_get(datastructureId) → extract current `spec` array
```

The `spec` is an array of field definitions:
```json
[
  { "name": "field_name", "type": "text", "label": "Field Label" },
  { "name": "score_weight_budget", "type": "number", "label": "Score Weight: Budget" },
  { "name": "ai_enabled", "type": "boolean", "label": "AI Enabled" }
]
```

### Step 2: Define New Field(s)

Add to the `spec` array. Supported types:

| Type | Make.com Type | Default Value | Notes |
|------|--------------|---------------|-------|
| `text` | String | `""` | General purpose |
| `number` | Number | `0` | Integers and floats |
| `boolean` | Boolean | `false` | Checkboxes, toggles |
| `date` | Date | `null` | ISO 8601 format |
| `email` | Email | `""` | Validated email |
| `url` | URL | `""` | Validated URL |
| `select` | Enum | first option | Requires `options` array |
| `collection` | Object | `{}` | Nested structure |
| `array` | Array | `[]` | List of items |

**Naming convention:** Use snake_case for field names. Group related fields with a prefix:
- Scoring: `score_weight_*`
- Cadence: `cadence_*`
- AI: `ai_*`
- Handoff: `handoff_*`

### Step 3: Update Data Structure

```
data-structures_update(datastructureId, spec: [...existing_fields, ...new_fields])
```

**CRITICAL:** You must include ALL existing fields in the `spec` array, not just the new ones. The API replaces the entire spec.

### Step 4: Populate Records

For each record that needs the new field:

```
data-store-records_update(dataStoreId, key: "record_key", data: { new_field: default_value })
```

**Common patterns:**
- Pipeline Config: usually 1 record (key = "config" or "default")
- Email Templates: multiple records (one per template)
- Lookup tables: multiple records (one per entry)

### Step 5: Update Client Context

Update the relevant context file in `workspace/clients/{client}/context/`:
- If it's a config data store → update the config field reference doc
- If it's a template store → update the template reference doc
- If it's a new data store → create a new context doc

Include: field name, type, default value, which scenario(s) use it.

## Procedure: Modify Existing Field

1. Get current schema (Steps 1-2 above)
2. Find the field in the `spec` array
3. Modify its properties (type, label, etc.)
4. Update via `data-structures_update` with the full modified spec
5. **Warning:** Changing a field's type may break existing records. Check records first.

## Procedure: Remove Field

1. Get current schema
2. Remove the field from the `spec` array
3. Update via `data-structures_update`
4. Note: Existing records may still contain the old field data (Make.com doesn't clean up)
5. Update context docs to remove references

## Bulk Schema Setup (for S0 / Setup Scenarios)

When creating a data store from scratch (e.g., during initial client setup):

```
1. data-structures_create(name: "Pipeline Config", teamId: teamId, spec: [full_spec_array])
2. data-stores_create(name: "Pipeline Config", teamId: teamId, datastructureId: new_structure_id, maxRecords: 1)
3. data-store-records_create(dataStoreId: new_store_id, key: "config", data: {all_fields_with_defaults})
```

## Integration with build-test-fix

When the iteration loop detects `SCHEMA_MISMATCH.missing_field`:
1. Extract the missing field name from the error
2. Determine the appropriate type and default value
3. Run this procedure automatically
4. Continue the iteration loop (retest)

This should be a fully autonomous fix — no user involvement needed.
