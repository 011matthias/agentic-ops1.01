# Post-Execution Outcome Verification

> Make.com implementation of outcome verification. See `.claude/rules/rule_behaviors.md` for orchestrator-agnostic principles.

**Always verify OUTCOMES, not just STATUS.**

After any Make.com scenario execution — whether test or production — do not stop at "status: 1 (success)". A successful execution only means the modules ran without errors. It does NOT mean the right data landed in the right place.

---

## Critical: `executions_get_detail` Does NOT Return Module Output Data

The `executions_get_detail` API returns ONLY metadata:
- Execution status (success/error), operations count per module, transfer bytes, duration, error messages

It does **NOT** return: actual data values between modules, resolved IML expressions, email bodies, sheet values, or API response payloads. Do not call it expecting to read what a module produced.

| To verify... | Use instead |
|--------------|-------------|
| Data store values | `data-store-records_list(storeId)` |
| Sheet cell values | Sheet Reader fixture (see `context/test-fixtures.md`) |
| Intermediate module output | Add temporary `datastore:AddRecord` debug tap |
| Whether a module ran | Operations count from `executions_get_detail` (this IS available) |
| Relative data volume | Transfer bytes comparison (this IS available) |

---

## Mandatory Steps After Every Execution

### 1. Define Expected Outcomes

Before running a scenario, state what SHOULD happen:
- What data should appear in the spreadsheet (which columns, what values)?
- What email should be sent (to whom, with what subject/body)?
- What records should be created/updated in target systems?

### 2. Verify Actual Outcomes

After execution completes (status: 1):
- **Check execution metadata:** `executions_list(scenarioId)` — operations count, transfer bytes, duration
- **Check data store records:** If debug taps are in place, read `data-store-records_list(dataStoreId)`
- **Ask user to verify:** For systems we can't read via MCP (Google Sheets cell data, Gmail sent folder), ask the user to confirm the output matches expectations
- **Compare expected vs actual:** Field by field, not just "it worked"

### 3. If Mismatch Detected

When the outcome doesn't match expectations:

1. **Isolate the failure stage:**
   - Did the trigger receive the correct data? (Check webhook payload)
   - Did the mapper transform it correctly? (Add debug tap after mapper)
   - Did the target system receive the right input? (Check target system directly)

2. **Common root causes:**
   - **Structural mismatch:** Source sends nested data, mapper expects flat (e.g., form providers)
   - **Field name mismatch:** Source uses different field names than mapper references
   - **Type mismatch:** Source sends string, target expects number (or vice versa)
   - **Missing fields:** Source doesn't include expected fields, mapper defaults kick in
   - **Empty values:** Field exists but is empty, `ifempty` fallback used

3. **Use the webhook-inspector skill** to capture and analyze the actual payload if the issue is at the webhook stage.

4. **Use the debug tap pattern** (data store module after suspect module) to inspect intermediate data if the issue is mid-scenario.

### 4. After Fix → Verify Again

After applying any fix, re-run the scenario and repeat verification. Don't assume the fix worked — confirm it.

---

## Proxy Indicators

When direct verification isn't possible, use proxy indicators:

| System | Direct Read Available? | Proxy Indicator |
|--------|----------------------|-----------------|
| Make execution | Yes (status, operations) | `executions_list` |
| Make data store | Yes (records) | `data-store-records_list` |
| Google Sheets | No (MCP can't read cells) | Ask user, or check row count via execution operations |
| Gmail sent | No | Ask user, or check execution status + operations count |
| External API | Depends | Check execution status, or call the API directly |

---

## Key Heuristic

**If the execution used fewer operations than expected, something was skipped.** A 4-operation execution on a 5-module scenario means one module didn't fire (likely a filter blocked it). Check router filters and conditional logic.

**If transfer bytes are suspiciously low, the payload may be empty.** Compare transfer bytes between a known-good execution and the suspect one.
