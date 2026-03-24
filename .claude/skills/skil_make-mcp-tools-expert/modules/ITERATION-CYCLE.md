# Make.com Scenario Iteration Cycle

Standard diagnose-fix-test pattern for iterating on Make.com scenarios autonomously.

---

## The Loop

```
1. SEND    → curl test data to webhook (or run scheduled scenario)
2. CHECK   → executions_list → find latest execution, check status
3. DIAGNOSE → if error: read error message
              if success but wrong output: inspect sheet data / email
4. FIX     → update blueprint via make-api.py update (scenarios_update 500s on blueprints)
5. VERIFY  → re-send test data, check execution again
6. REPEAT  → until clean execution with correct output
```

---

## Tools Available

### What we CAN do via MCP:
- `executions_list(scenarioId)` → list executions with status and error messages
- `executions_get(scenarioId, executionId)` → execution metadata
- `scenarios_get(scenarioId)` → current blueprint (to identify the failing module)
- `uv run tools/make-api.py update --zone {ZONE} --scenario-id {ID} --blueprint {PATH}` → deploy fixes (NOT `scenarios_update` — returns 500 on blueprint param)
- `scenarios_activate/deactivate(scenarioId)` → control scenario state
- `scenarios_run(scenarioId)` → trigger scheduled scenarios on demand
- `hooks_list(teamId)` → find webhook URLs
- `connections_list(teamId)` → verify auth connections exist
- `rpc_execute(google-sheets, listSpreadsheets)` → list available spreadsheets

### What we CAN do locally:
- `curl` → send test webhook payloads (see WEBHOOK-TESTING.md)
- `uv run tools/make-api.py` → REST API for blueprint deploy/update, data store CRUD, scenario run (bypasses MCP 500 errors on blueprint params)
- Bash scripts → automate multi-step test sequences

### What we CANNOT do directly (Make API limitation):
- **Read module-level I/O from successful executions** — Make's public API only returns SUCCESS/ERROR status, not the data that flowed through each module. The data visible in Make's UI uses internal endpoints not in the public API.

### What we CAN do via Persistent Test Fixtures:
- **Read Google Sheet cell data** — via UTIL - Sheet Reader (webhook → getCells → WebhookRespond). Returns pipe-separated key=value pairs. See the client's `context/test-fixtures.md` for fixture IDs and URLs.
- **Write Google Sheet cell data** — via UTIL - Cell Writer (Tool type, callable via `scenarios_run`). Used to set preconditions: backdate timestamps, toggle flags, set step values.

> See `.claude/rules/rule_behaviors.md` — "Test fixtures persist" behavior.

### Workaround: Module I/O Inspection via Data Store "Debug Taps"

When you need to see what data flows between modules:

1. Create or reuse a diagnostic data store: `data-stores_create` or `data-stores_list`
2. Get the current blueprint: `scenarios_get(scenarioId)`
3. Insert a `datastore:addRecord` module AFTER the module you want to inspect
4. Map the module's output variables into the data store record (use `toString()` to capture complex objects)
5. Deploy the modified blueprint: `uv run tools/make-api.py update`
6. Run the scenario (curl or trigger)
7. Read the captured data: `data-store-records_list(dataStoreId)`
8. **Remove the debug tap** and redeploy the clean blueprint

This is particularly useful for:
- Verifying what a webhook actually received (tap after the webhook module)
- Checking what a mapper produced (tap after the mapper module)
- Debugging router filter inputs (tap before the router)

See also: `webhook-inspector` skill for a dedicated webhook payload capture workflow.

---

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `Function 'X' not found` | Wrong function name for Make's IML | Check Make.com function reference. Common: `toNumber` → `parseNumber`, `toString` → `toString` (may not exist) |
| `Failed to evaluate filter` | Filter expression has IML error | Check the filter's `conditions` array for invalid functions or references |
| `Connection not found` | Connection ID invalid or expired | `connections_list` to find valid IDs, update blueprint |
| `PERMISSION_DENIED` | Google connection missing scopes | User needs to re-auth the connection in Make UI |
| Status 1 but wrong output | Field mapping mismatch | Test with clean curl JSON first to isolate: blueprint issue vs form naming issue |

---

## Workflow: New Scenario Integration

1. **Deploy blueprint** via `uv run tools/make-api.py update`
2. **Activate** via `scenarios_activate`
3. **Test with clean JSON** via curl (see WEBHOOK-TESTING.md)
4. **Check execution** via `executions_list`
5. **If error** → read error, fix blueprint, go to step 1
6. **If success** → verify output (sheet data, email, etc.)
7. **If output wrong** → fix mapper/filter, go to step 1
8. **Source schema verification** (BEFORE testing with real data):
   - If the scenario has an external trigger (form, API, webhook sender):
   - Check `webhook-inspector` skill → KNOWN-PROVIDERS.md for the source system's payload format
   - If not listed → use the capture pattern to discover the format
   - Compare the source schema against the blueprint's mapper references
   - If structural mismatch (nested vs flat, different field names) → fix mapper FIRST
9. **Test with real source data** (form submission, API event, etc.)
10. **Post-execution outcome verification** (see `.claude/rules/make/post-execution-verification.md`):
    - Don't stop at "status: success" — verify the actual data in target systems
    - Check expected vs actual output field by field
    - If mismatch → diagnose where data was lost/transformed incorrectly
11. **If real data fails but clean JSON worked** → structural/naming mismatch between source and mapper
12. **After fixing** → apply operationalization loop (see `.claude/rules/operationalization-loop.md`)

---

## Workflow: Debugging an Existing Scenario

1. **Check executions** → `executions_list(scenarioId)` → look for status 3 (error)
2. **Read error message** → tells you which module/filter failed
3. **Get current blueprint** → `scenarios_get(scenarioId)` → find the failing module
4. **Fix the blueprint** → modify the relevant module/filter/mapper
5. **Deploy** → `uv run tools/make-api.py update`
6. **Re-test** → curl or run

---

## Key Principles

- **Test with clean JSON first** before blaming external integrations
- **One change at a time** when fixing — don't change multiple things between tests
- **Check the blueprint matches the sheet structure** — column indices in the mapper must align with actual sheet headers
- **Connection IDs are instance-specific** — always verify via `connections_list` when deploying to a new account
- **`parseNumber(value; ".")` not `toNumber(value)`** — Make's IML uses `parseNumber` with a decimal separator argument
