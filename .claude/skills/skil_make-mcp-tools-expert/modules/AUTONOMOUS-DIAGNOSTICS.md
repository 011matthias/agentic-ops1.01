# Autonomous Diagnostic Fallback Chain

> Make.com implementation of observable state diagnostics. See `.claude/rules/rule_behaviors.md` for outcome verification principles.

**When something doesn't work as expected in a Make.com integration, exhaust these diagnostic approaches IN ORDER before asking the user for help.**

The user should not need to provide raw payloads, field names, or API responses unless all autonomous approaches have been tried and failed.

---

## Fallback Chain (try in order)

### Level 1: Available Data (no side effects)

1. **Check execution metadata:** `executions_list(scenarioId)` — compare operations count, transfer bytes, status, and duration against known-good executions
2. **Check webhook configuration:** `hooks_get(hookId)` — inspect `udt` (user data type), `ip`, `data` fields for clues about payload structure
3. **Check scenario blueprint:** `scenarios_get(scenarioId)` — review mapper expressions for obvious errors (wrong paths, typos, function errors)
4. **Compare transfer bytes:** A successful execution with lower-than-expected transfer bytes means data is empty/missing even though status is success
5. **Check execution detail:** `executions_get_detail(scenarioId, executionId)` — returns status, operations count, and transfer bytes ONLY. Does NOT return module output data. Use for counting operations and comparing transfer bytes, NOT for reading actual values.
6. **Check entry point binding:** If the pipeline starts from an external source (website form, CRM, third-party), verify the source actually posts to the correct scenario. Use `WebFetch` for website forms. See [E2E-PIPELINE-VERIFICATION](../../skil_build-test-fix/modules/E2E-PIPELINE-VERIFICATION.md) Step 0.
7. **Check ops feasibility:** If the symptom is "account paused" or "ops limit reached", load [OPERATIONS-ANALYZER](./OPERATIONS-ANALYZER.md) Section B for post-hoc analysis.

### Level 2: Research (no side effects)

6. **Search KNOWN-PROVIDERS.md:** Check `webhook-inspector` skill for pre-documented payload formats
7. **Web search:** Search for "[provider name] webhook payload format" or "[provider name] Make.com integration"
8. **Make community search:** Search Make Community forum for the provider + module combination
9. **Check provider's official docs:** WebFetch the provider's webhook documentation
10. **Check Make module documentation:** `app-module_get` or `app-modules_list` for the module in question to understand its output schema

### Level 3: Active Probing (side effects, but reversible)

11. **Curl test with known data:** Send a curl request with known values → check execution → compare transfer bytes against empty-data executions
12. **Vary the test payload:** Send multiple curl tests with different structures (flat vs nested) to see which produces higher transfer bytes
13. **Webhook data structure redetermination:** If `hooks_get` shows `udt: null`, the webhook hasn't learned the data structure. Send a test payload, then re-check `hooks_get` to see if `udt` populated
14. **Data store diagnostic tap:** Add a temporary `datastore:AddRecord` module to the scenario to capture intermediate data (see webhook-inspector skill)
15. **Create a minimal inspector scenario:** Webhook → DataStore (captures raw payload for reading via MCP)

### Level 3.5: Database State (before escalating to user)

Before asking the user to check a database or explore phpMyAdmin:

15a. **Attempt direct DB connection:** Try `uv run python -c "import pymysql; conn = pymysql.connect(host=HOST, port=3306, user=USER, password=PASS, database=DB); ..."` or use the `s8842538_util_my_sql_test_query` / `s8842540_util_my_sql_count_query` MCP fixtures if available.
15b. **Check for firewall:** A `Connection refused` or timeout on port 3306 is a legitimate blocker — document the error, then escalate. Never escalate *before* attempting.
15c. **Use count query as proxy:** If direct read fails, `SELECT COUNT(*) FROM table WHERE condition` via the MySQL UTIL scenario is lower-privilege and more likely to succeed.

**Key rule:** "Can you check in phpMyAdmin?" is only valid AFTER steps 15a–15c have been tried and documented.

### Level 4: User Assistance (last resort)

16. **Ask user to verify output:** "Can you check if row X in the spreadsheet has data in columns A-F?"
17. **Ask user for raw payload:** Only after all autonomous methods have failed

---

## Key Heuristic: Transfer Bytes as a Proxy

When you can't directly read the output (e.g., Google Sheets cells), use transfer byte comparison:

- Send a curl with **empty** values → note transfer bytes (baseline)
- Send a curl with **populated** values → note transfer bytes
- If the difference is proportional to the data size, the mapper is working
- If both produce the same bytes, the mapper is NOT resolving values

This works because more resolved data = more bytes written to target systems.

---

## Make CustomWebHook Output Path

The path to access webhook data depends on whether the webhook has a learned data structure:

| Webhook `udt` value | Access path | Notes |
|---------------------|-------------|-------|
| `null` (no learned structure) | `1.data.*` or `1.*` | Raw parsed JSON at top level |
| Set (has data structure) | `1.body.*` | Structured access through body |

**Critical:** When `udt` is null, `1.body.*` will NOT work. Always check `hooks_get(hookId)` for the `udt` value before building mappers.

This was the root cause of the Tally mapping failure — the webhook had `udt: null` but mappers referenced `1.body.data.fields`.

---

## Anti-Pattern: "It Succeeded So It Must Be Right"

A Make execution with status: 1 (success) only means no module threw an unhandled error. It does NOT mean:
- Data was correctly mapped (could all be empty strings)
- Emails were sent to the right person (Resume error handler masks send failures)
- The right number of records were created

Always verify OUTCOMES through the fallback chain above, not just STATUS.
