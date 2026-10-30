# Sheets Column Reconciler

Validates that Google Sheets column references in a blueprint match the actual sheet structure.

## Procedure

### Step 1: Extract Blueprint Sheet References

Parse the blueprint's `flow` array. For each module where `module` starts with `google-sheets:`:

```
For google-sheets:getCell:
  - Extract column letter from mapper (e.g., "A", "M", "P")
  - Extract row reference (usually dynamic: {{N.__ROW_NUMBER__}} or static row number)
  - Note the module ID for reference tracking

For google-sheets:updateRow / google-sheets:addRow:
  - Extract all column mappings from the mapper
  - Each key is a column letter or column index
  - Note which fields are being written to which columns

For google-sheets:filterRows / google-sheets:searchRows:
  - Extract the filter/search column references
  - These are the columns used in WHERE clauses

For google-sheets:getValues (range-based):
  - Extract the range string (e.g., "A1:P100")
  - Parse column range from it
```

Build a map: `{column_letter: [module_ids_that_reference_it]}`

### Step 2: Determine Expected Column Schema

**Option A: From client context (preferred)**
Read `workspace/clients/{client}/context/google-sheets-schema.md` if it exists.
This file should contain:

```
| Column | Letter | Header | Written By | Read By |
|--------|--------|--------|-----------|---------|
| 1 | A | Name | A1 (module 3) | A3 (module 10) |
| 2 | B | Email | A1 (module 3) | A2 (module 5) |
```

**Option B: From Sheet Reader utility (if available)**
If a Sheet Reader utility scenario exists (documented in `context/test-fixtures.md`):
1. Find the utility scenario ID
2. Execute it to read the first row (headers)
3. Parse the response to build the column map

**Option C: From spec**
Read the automation spec for column definitions.

### Step 3: Compare

| Check | Severity | Issue |
|-------|----------|-------|
| Blueprint references column X, but sheet header at X is different than expected | ERROR | Column mismatch — data will be written/read from wrong column |
| Blueprint references column beyond sheet range | ERROR | Column doesn't exist |
| Scenario writes to column X, another scenario reads from column Y for the same data | ERROR | Cross-scenario column inconsistency |
| Column referenced in blueprint but not in schema doc | WARN | Undocumented column usage |
| Column in schema doc but never referenced | INFO | Unused column |

### Step 4: Cross-Scenario Consistency

When multiple scenarios (A1, A2, A3) share the same Google Sheet:

```
For each column:
  - Which scenario writes it? (addRow/updateRow)
  - Which scenario reads it? (getCell/filterRows)
  - Is the data type consistent? (writing a date, reading as text?)
  - Are column letters consistent across all scenarios?
```

**Key pattern to check:** If A1 writes to column M and A3 reads from column M, do they agree on what column M represents?

## Output

```markdown
## Sheets Column Reconciler Report

**Sheet:** {sheet name}
**Columns referenced:** {list}
**Scenarios checked:** {list}

| Severity | Column | Scenario | Issue | Suggested Fix |
|----------|--------|----------|-------|---------------|
| ERROR | M | A3 (module 14) | Reads column M expecting "lead_score" but schema shows M = "discussion_topic" | Update getCell to column L |
| WARN | G | A3 | Column G (organisation) not read by A3 but used in A3 email template | Add getCell for column G or remove ##organisation## from A3 templates |
```

## Auto-Fix

For column letter mismatches:
1. Determine the correct column letter from the schema
2. Update the blueprint's module mapper with the correct letter
3. Re-run reconciler to verify

For cross-scenario inconsistencies:
- Flag for user review (may require architectural decision about which scenario is correct)
