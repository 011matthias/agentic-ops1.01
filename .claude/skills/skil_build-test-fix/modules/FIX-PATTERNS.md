# Fix Patterns Registry

Known failure→fix mappings. Each pattern includes: trigger condition, fix procedure, and post-fix verification.

**This registry grows over time.** After every novel fix discovered during the iteration loop, add it here via the operationalization loop.

---

## EMPTY_RESULT Fixes

### ER-1: filterRows/searchRows Empty-Row Guard (Make.com)

**Trigger:** `EMPTY_RESULT` after a `google-sheets:filterRows` or `google-sheets:searchRows` module. Error: "Unable to parse range" or downstream module receives undefined `__ROW_NUMBER__`.

**Fix:**
1. Fetch current blueprint via `scenarios_get`
2. Add a filter between the filterRows module and the next downstream module
3. Filter condition: `{{N.__ROW_NUMBER__}} >= 1` (where N = filterRows module ID)
4. Alternative (safer): Use `text:isnotempty` on `{{N.__ROW_NUMBER__}}` — avoids numeric coercion edge cases
5. Update blueprint via `uv run tools/make-api.py update`

**Post-fix verification:** Run scenario with data that produces 0 filterRows matches. Expect: execution completes with 0 operations after the guard (no error).

**Source:** Meji Media A2/A3 empty-row bug (2026-02)

### ER-2: Empty Array Guard for Iterators (Make.com)

**Trigger:** `EMPTY_RESULT` when `BasicFeeder` (iterator) receives an empty array.

**Fix:**
1. Add an `ifempty()` check before the iterator
2. Or add a filter: `{{length(N.array)}} > 0` before the iterator module
3. Or restructure to avoid iterator entirely (use individual getCell modules — see EX-2)

**Source:** General Make.com pattern

### ER-3: No Results from Data Store Query (Make.com)

**Trigger:** `EMPTY_RESULT` from `datastore:GetRecord` — record doesn't exist for the given key.

**Fix:**
1. Add `builtin:Resume` error handler after the datastore module
2. In the Resume handler, set a default value or skip downstream processing
3. Alternative: Pre-check with `data-store-records_list` (API-side, before execution)

---

## EXPRESSION_ERROR Fixes

### EX-1: Numeric Key Ambiguity (Make.com)

**Trigger:** `EXPRESSION_ERROR.numeric_key` — IML expression `{{N.0}}` or `{{N.1}}` interpreted as module reference instead of field index.

**Fix:**
1. Do NOT use numeric field indices from searchRows/filterRows output
2. Replace with explicit `getCell` modules that read specific cells by column letter
3. Each getCell module gets a stable ID that can be referenced as `{{ID.value}}`
4. This requires architectural restructuring — if >3 fields needed, create N separate getCell modules

**When to escalate:** If the expression uses numeric keys in a context that can't be refactored to getCell (e.g., deeply nested array access), escalate to user.

**Source:** Meji Media A3 architecture rework (searchRows+iterator → 6× getCell)

### EX-2: Missing Module Reference (Make.com)

**Trigger:** `EXPRESSION_ERROR.missing_reference` — `{{N.field}}` where module N doesn't exist in the execution path.

**Fix:**
1. Fetch blueprint and list all module IDs
2. Check if module N exists → if not, the reference is wrong
3. Find the correct module that produces the needed field
4. Update the IML expression to reference the correct module ID
5. Common cause: module IDs shift when adding/removing modules from blueprint

### EX-3: IML Function Name Typo (Make.com)

**Trigger:** `EXPRESSION_ERROR.syntax` with error pointing to a function call.

**Fix:**
1. Check the function name against known IML functions:
   - `ifempty()`, `if()`, `length()`, `first()`, `last()`, `map()`, `get()`
   - `formatDate()`, `parseDate()`, `addDays()`, `addHours()`
   - `lower()`, `upper()`, `trim()`, `replace()`, `split()`, `join()`
   - `toNumber()`, `toString()`
2. Common mistakes: `isEmpty` (wrong) → `ifempty` (correct), `len` (wrong) → `length` (correct)
3. Replace with correct function name

---

## SCHEMA_MISMATCH Fixes

### SM-1: Missing Data Store Field (Make.com)

**Trigger:** `SCHEMA_MISMATCH.missing_field` referencing a data store field that doesn't exist.

**Fix — use Schema Evolution module:**
1. `data-stores_get(storeId)` → find `datastructureId`
2. `data-structures_get(structureId)` → current spec
3. `data-structures_update(structureId, spec: [...existing + new field])`
4. `data-store-records_update(storeId, key, {new_field: default_value})`
5. Update client context files

### SM-2: Nested Payload Structure (Make.com/n8n)

**Trigger:** `SCHEMA_MISMATCH.nested` — webhook payload is nested deeper than IML expressions assume.

**Fix:**
1. Run the Webhook Payload Inspector module to discover actual structure
2. Generate correct IML expressions for the actual nesting
3. Update all module mappings in blueprint
4. Common case: Tally/Typeform/JotForm send `data.fields[]` arrays, not flat objects
5. Pattern: `{{first(map(1.data.fields; "value"; "label"; "Field Name"))}}`

### SM-3: Column Letter Mismatch (Make.com — Google Sheets)

**Trigger:** `SCHEMA_MISMATCH` in a Google Sheets module — wrong column referenced.

**Fix:**
1. Use the Sheets Column Reconciler module to map expected columns
2. If Sheet Reader utility scenario exists, read actual headers
3. Update getCell/updateRow column references in blueprint
4. Update client context `google-sheets-schema.md`

---

## API_ERROR Fixes

### AE-1: Add Resume Error Handler (Make.com)

**Trigger:** `API_ERROR` from an HTTP module or API call — any external API that might fail.

**Fix:**
1. Add `builtin:Resume` error handler to the failing module
2. In the Resume route, provide a fallback value:
   - For AI calls: empty string (then use `ifempty()` downstream for graceful degradation)
   - For data fetches: default/cached value
   - For email sends: log the failure, continue processing

**Source:** Meji Media A1 OpenAI module — Resume handler + `ifempty()` for AI-generated content

### AE-2: Rate Limit Backoff (All)

**Trigger:** `API_ERROR.rate_limit` — 429 response.

**Fix:**
1. **Make.com:** Enable built-in retry on the HTTP module (max retries: 3, interval: 60s)
2. **n8n:** Add retry on failure to the node
3. **Trigger.dev:** Use `retry.delay` in task options

---

## IMPORT_FORMAT_ERROR Fixes

### IF-1: Missing Metadata Fields for UI Import (Make.com)

**Trigger:** Blueprint rejected by Make.com UI "Import Blueprint" — "Invalid blueprint" error or silent failure when pasting JSON. Blueprint was built/deployed via API and is missing fields the UI importer requires.

**Fix:**
1. Compare blueprint metadata against a known Make.com export (A1/A2 files are reference)
2. Add `"designer": {"orphans": []}` to `metadata` if missing
3. Add `"dataloss": false` to `metadata.scenario` if missing
4. Ensure `scheduling` and `interface` top-level keys are present
5. Omit `name` key (API schema validator rejects it; UI may ignore or reject it)
6. Validate core structure with `validate_blueprint_schema` MCP tool (only checks `flow` + `metadata`)
7. Run HANDOVER-FORMAT-CHECKER reconciler module for full handover readiness

**Post-fix verification:** Paste the fixed blueprint into Make.com UI Import Blueprint dialog. Should load without errors and display the module canvas.

**Source:** Meji Media S0 handover (2026-02)

---

## OUTCOME_MISMATCH Fixes

### OM-1: Empty Email Body (Make.com)

**Trigger:** `OUTCOME_MISMATCH.EMPTY_OUTPUT` -- execution succeeds, transfer bytes are low, email module ran but body is blank. Spec requires populated HTML email body.

**Fix:**
1. Check AI/enrichment module ran: `executions_get_detail` -- compare operations count against expected. If AI module was skipped, a `builtin:Resume` error handler caught a failure silently
2. If AI output is missing: check the module's output in execution detail. If empty, the API call failed -- check Resume handler captured it
3. Add debug tap (`datastore:AddRecord`) after AI module to capture its actual output
4. If AI output exists but email body is empty: check email module mapper -- the IML reference to AI output may use wrong module ID or wrong field name
5. Confirm with: compare transfer bytes against a known-good execution with populated body

**Post-fix verification:** Re-run scenario. Transfer bytes for email module should increase by ~200-500 bytes compared to empty-body baseline.

**Source:** Meji Media A1 (2026-02)

### OM-2: Template Placeholders Not Resolved (Make.com)

**Trigger:** `OUTCOME_MISMATCH.MISSING_FIELDS` -- email body contains literal `##placeholder##` strings. Execution succeeds, email is sent, but client-specific values not injected.

**Fix:**
1. Run TEMPLATE-PLACEHOLDER-CHECKER reconciler on the blueprint
2. For each unresolved placeholder, trace where the value should come from in the flow
3. Common cause: data store field is empty -- check with `data-store-records_list`
4. If field is empty: either S0 setup didn't run, or the field population step was skipped
5. Check the S0/setup scenario execution history to see if it ran and populated fields
6. If setup ran but field is blank: the setup mapper for that field has a bug -- inspect the setup blueprint

**Post-fix verification:** Re-run scenario. Inspect email module mapper input in execution detail -- all `##...##` patterns should be replaced with IML expressions returning actual values.

**Source:** Meji Media email template system (2026-02)

### OM-3: Wrong Field Values in Output (Make.com -- Data Store)

**Trigger:** `OUTCOME_MISMATCH.WRONG_VALUES` -- data store record updated but field values don't match expected (e.g., status set to wrong stage, score is 0 not calculated).

**Fix:**
1. Read the record: `data-store-records_list(storeId)` -- compare field-by-field against expected
2. Find the module that writes the wrong field: get blueprint, trace the mapper for that field
3. Check the mapper IML expression: is it referencing the right module ID and field?
4. Common cause after blueprint updates: module IDs shift when adding/removing modules. An IML like `{{14.value}}` now references a different module than intended
5. Re-validate all module ID references using IML-REFERENCE-CHECKER reconciler

**Post-fix verification:** Run scenario with known test data, read data store record immediately after, compare each field against expected values from spec acceptance criteria.

**Source:** General Make.com pattern -- module ID drift after blueprint restructuring

### OM-4: Scenario Succeeds But Target Record Not Updated (Make.com)

**Trigger:** `OUTCOME_MISMATCH.STRUCTURAL_MISMATCH` -- execution succeeds with expected operation count, but the expected data store or sheet record was not actually updated.

**Fix:**
1. Check the filter before the write module: `executions_get_detail` -- compare operations count. If write module didn't run, a filter blocked it
2. Get blueprint and inspect filter conditions on the route leading to the write module
3. Run the scenario with test data that definitely satisfies the filter, verify the filter condition evaluates correctly
4. Common cause: filter uses `text:notEqual` which is unreliable in Make.com (can silently fail comparisons). Replace with `text:equal` + router fallback route, or use `text:isnotempty`/`text:isempty` instead
5. Also check: does the write module target the correct data store ID / sheet ID? Compare against `infrastructure.yaml`

**Post-fix verification:** Run with boundary-condition test data that should trigger the write module. Confirm operation count includes the write module. Read the target record to verify values.

**Source:** IML-GOTCHAS.md -- `text:notEqual` unreliability

---

## n8n-Specific Fixes

### ER-4: Empty Result from Iteration Over Empty Array (n8n)

**Trigger:** `EMPTY_RESULT` — SplitInBatches or downstream nodes receive 0 items. Workflow appears to succeed but nothing is processed.

**Fix:**
1. Add an IF node before the SplitInBatches/loop checking `{{$json.items.length > 0}}` (adjust field name to match actual data)
2. Route the empty case to a "No items" branch (Stop and Error, or a notification)
3. If using a Code node that returns items, ensure it returns `[]` not `undefined` when empty

**Post-fix verification:** Run workflow with data that produces 0 items from the source. Expect: workflow completes, "No items" branch executes, no downstream processing errors.

### EX-4: Expression Fails Due to Wrong Node Name Casing (n8n)

**Trigger:** `EXPRESSION_ERROR` — `$('Node Name').first().json.field` returns undefined or "Referenced node does not exist" even though the node exists in the workflow.

**Fix:**
1. Run `n8n_get_workflow({id, mode: 'structure'})` to see exact node names
2. Compare the expression's node name against the actual name (case-sensitive)
3. Update the expression to match exactly: `"HTTP Request"` not `"http request"` or `"Http Request"`
4. Common pattern: n8n defaults to Title Case for node names

**Post-fix verification:** Re-run workflow. The expression should resolve to a value instead of undefined.

### EX-5: IF Node Route Not Firing (n8n)

**Trigger:** `EMPTY_RESULT` or unexpected routing — one branch of an IF node never receives items even when the condition should match.

**Fix:**
1. Check the `addConnection` calls that wired the IF node — they must use `branch: "true"` or `branch: "false"`
2. Read connections from `n8n_get_workflow({id, mode: 'structure'})` — verify `sourceIndex` maps to the correct branch (0 = true, 1 = false)
3. If connections are wrong, use `n8n_update_partial_workflow` with `removeConnection` + `addConnection` using smart parameters
4. Also check the IF condition itself — test with a hardcoded `true`/`false` to isolate condition logic vs routing

**Post-fix verification:** Run workflow with data that should trigger each branch. Verify both branches execute with correct routing.

### SM-4: Config Node Not Found (n8n)

**Trigger:** `EXPRESSION_ERROR` — "Referenced node 'Config' does not exist" from any downstream node using `$('Config').first().json`.

**Fix:**
1. `n8n_get_workflow({id, mode: 'structure'})` — check if a node named exactly `Config` exists
2. If renamed: either restore the name to `Config` or update all downstream references
3. If deleted: re-create the Config Code node per N8N-BUILD.md Step 2
4. Config node must be named exactly `Config` (capital C) — this is the workspace convention

**Post-fix verification:** Run workflow. All `$('Config').first().json.*` expressions should resolve correctly.

### AE-3: Credential Scope Insufficient (n8n)

**Trigger:** `CONNECTION_ERROR` — 403 Forbidden from a Google/Slack/OAuth-protected node even though the credential exists and the workflow previously worked.

**Fix:**
1. Read the error message — it usually specifies which OAuth scope is missing
2. **Escalate to user immediately** — credential re-authentication requires the n8n UI and cannot be done via MCP
3. Provide the user with: which node failed, which credential, what scope is needed
4. Common cause: the automation was extended to use a new operation (e.g., added "send email" to a workflow that only had "read email") requiring a broader scope

**Post-fix verification:** After user re-authenticates with expanded scope, re-run workflow. The 403 should resolve.

---

## SILENT_FAILURE Fixes

### SF-1: Data Store Module Silent Failure After API Deployment (Make.com)

**Trigger:** `OUTCOME_MISMATCH.STRUCTURAL_MISMATCH` — data store module (`datastore:UpdateRecord`, `datastore:GetRecord`) reports status 1 (success) but doesn't actually read or write data. Cursor doesn't advance, records aren't updated. No error in execution log.

**Fix:**
1. This is NOT a code/blueprint bug — it's a binding issue. Data store modules deployed via API lack an internal binding that the Make.com UI creates.
2. **User must open the scenario in Make.com UI** → click into each data store module → select the data store from the dropdown → save
3. After UI rebinding, verify the mapper uses the `"data"` collection wrapper format: `"data": {"field_name": "{{value}}"}`
4. If the UI save cleared IML expressions (common), re-deploy the blueprint via `scenarios_update` to restore them
5. Run a write-then-read verification: update a data store record, then immediately read it back and compare

**Post-fix verification:** Run scenario. Check data store record via `data-store-records_list` — values should match what the module wrote. For cursor-based polling, verify cursor value advances after processing.

**Key insight:** This applies to ALL modules referencing external resources (connections AND data stores), not just connection-dependent modules. The only modules safe for API-only deployment are: `http:ActionSendData`, built-in flow control, and `util:*` modules.

**Source:** Meji Media A0 data store binding issue (2026-03-12). 5 diagnostic scenarios required to isolate.

### SF-2: IML `emptystring` Constant Causes BlueprintValidationError (Make.com)

**Trigger:** `BlueprintValidationError` — "Scenario validation failed - 1 problem(s) found" at runtime. Blueprint deploys successfully (`isinvalid: false`) but fails when executed.

**Fix:**
1. Search blueprint for `emptystring` — this is NOT a valid Make.com IML constant
2. Replace with `""` (empty quoted string): `ifempty(field; "")` not `ifempty(field; emptystring)`
3. Other valid IML constants: `newline`, `tab`, `emptyarray` — but NOT `emptystring`

**Post-fix verification:** Run scenario. Should execute without BlueprintValidationError.

**Source:** Meji Media A0 JSON body escaping (2026-03-12)

---

## Extending This Registry

After discovering a novel fix during the iteration loop:

1. Classify the error using FAILURE-TAXONOMY.md
2. Create a new entry following this template:

```markdown
### {CATEGORY}-{N}: {Short Description} ({Orchestrator})

**Trigger:** `{CATEGORY}.{subtype}` — {specific error pattern or message}

**Fix:**
1. {Step 1}
2. {Step 2}
...

**Post-fix verification:** {How to confirm the fix works}

**Source:** {Client name + date where this was first discovered}
```

3. Add to the appropriate category section above
4. If the fix is Make.com-specific and relates to IML, also cross-reference in `.claude/skills/skil_make-mcp-tools-expert/modules/IML-GOTCHAS.md`
