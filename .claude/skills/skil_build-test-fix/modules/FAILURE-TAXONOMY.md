# Failure Taxonomy

Classification guide for execution errors across orchestrators. Used by the iteration loop to route failures to the correct fix pattern.

## Categories

### EXPRESSION_ERROR
**What:** IML/expression syntax or reference failure.

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | "Unable to parse", "Invalid expression", "syntax error in IML", "Unexpected token", module returns null when value expected |
| **n8n** | "Expression error", "Cannot read property", "is not a function", `{{ }}` evaluation failure |
| **Trigger.dev** | TypeScript compile error, runtime TypeError, undefined variable |

**Common subtypes:**
- `EXPRESSION_ERROR.numeric_key` — `{{1.0}}` interpreted as module ID instead of field index (Make.com specific)
- `EXPRESSION_ERROR.missing_reference` — `{{N.field}}` where module N doesn't exist or isn't upstream
- `EXPRESSION_ERROR.type_mismatch` — String used where number expected (or vice versa)
- `EXPRESSION_ERROR.syntax` — Malformed expression, unclosed brackets, wrong function name

### CONNECTION_ERROR
**What:** Authentication or credential failure.

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | "Authorization failed", "Invalid credentials", "Connection expired", "The connection is not authorized" |
| **n8n** | "AUTHENTICATION_FAILED", "401 Unauthorized", "credential" |
| **Trigger.dev** | "UNAUTHORIZED", "Invalid API key", env var missing |

**Subtypes:**
- `CONNECTION_ERROR.expired` — Token/session expired (re-auth needed)
- `CONNECTION_ERROR.missing` — No connection configured for this module
- `CONNECTION_ERROR.scope` — Connection exists but lacks required permissions

**Note:** CONNECTION_ERROR usually requires human intervention (re-authenticate in UI). Escalate immediately unless it's a missing connection that can be set programmatically.

### SCHEMA_MISMATCH
**What:** Data shape doesn't match what the module expects.

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | "field not found", "property does not exist", "The value is required", data store key mismatch, unexpected null |
| **n8n** | "Property does not exist", "Cannot read properties of undefined", missing required field |
| **Trigger.dev** | TypeScript type error, Zod validation failure, missing field in API response |

**Subtypes:**
- `SCHEMA_MISMATCH.missing_field` — Field referenced but doesn't exist in source
- `SCHEMA_MISMATCH.renamed_field` — Field was renamed but references weren't updated
- `SCHEMA_MISMATCH.type` — Field exists but wrong type (string vs number vs array)
- `SCHEMA_MISMATCH.nested` — Field is nested deeper than expected (e.g., Tally `data.fields[]` vs flat `data`)

### EMPTY_RESULT
**What:** Query/filter returned 0 results, downstream modules fail on empty data.

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | "Unable to parse range" (Sheets), empty array from filterRows/searchRows, `__ROW_NUMBER__` undefined, "No items" |
| **n8n** | "No items" returned, empty array from query, downstream node receives 0 items |
| **Trigger.dev** | Empty array, null result from database query, API returns empty collection |

**This is the #1 most common Make.com failure.** The filterRows → getCell pattern without an empty-row guard always fails on 0 results.

### API_ERROR
**What:** External API returned an error (not auth — see CONNECTION_ERROR).

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | HTTP status 4xx/5xx from HTTP module, "rate limit", "quota exceeded", "Recipient address required" (Gmail), OpenAI "content_filter" |
| **n8n** | HTTP response code error, API-specific error messages |
| **Trigger.dev** | Thrown errors from API calls, rate limit responses |

**Subtypes:**
- `API_ERROR.rate_limit` — 429 / quota exceeded (retry with backoff)
- `API_ERROR.server` — 500 / 502 / 503 (transient — retry)
- `API_ERROR.client` — 400 / 422 (bad request — fix the payload)
- `API_ERROR.not_found` — 404 (wrong endpoint or resource ID)

### TIMEOUT
**What:** Operation exceeded time limit.

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | "Operation timeout", execution time exceeded, "ETIMEDOUT" |
| **n8n** | "Execution timed out", node timeout |
| **Trigger.dev** | Task timeout, function timeout |

**Usually caused by:** Large data sets, slow external APIs, infinite loops. Fix by adding pagination, increasing timeout, or optimizing query.

### OUTCOME_MISMATCH
**What:** Execution succeeded (no errors) but output is incorrect. Detected during outcome verification (see [OUTCOME-VERIFICATION.md](OUTCOME-VERIFICATION.md)).

| Orchestrator | Detection Patterns |
|-------------|-------------------|
| **Make.com** | Transfer bytes suspiciously low, data store record has empty/wrong fields, operations count lower than expected modules |
| **n8n** | Node output empty or wrong values, execution data doesn't match expected |
| **Trigger.dev** | Task returned successfully but output values incorrect, partial data returned |

**Subtypes:**
- `OUTCOME_MISMATCH.EMPTY_OUTPUT` — Execution succeeded but produced no/empty output (e.g., email sent with empty body, spreadsheet row with blank cells). Key signal: transfer bytes much lower than expected.
- `OUTCOME_MISMATCH.WRONG_VALUES` — Output exists but field values don't match expected. Requires field-by-field comparison against spec acceptance criteria.
- `OUTCOME_MISMATCH.MISSING_FIELDS` — Some expected fields populated, others null/empty. Often caused by partial placeholder resolution or conditional logic skipping branches.
- `OUTCOME_MISMATCH.STRUCTURAL_MISMATCH` — Output shape differs from expected (e.g., single value vs array, flat vs nested). Often caused by upstream module returning different structure than assumed.

**Key distinction from other categories:** No error message exists. The execution log shows all green/success. Only detectable by comparing actual output against expected outcomes defined before execution.

## Priority for Autonomous Fix

| Category | Autonomous Fix Likelihood | Notes |
|----------|--------------------------|-------|
| EMPTY_RESULT | **HIGH** — well-known guard patterns | Always try first |
| EXPRESSION_ERROR | **MEDIUM** — depends on subtype | numeric_key and missing_reference are fixable; syntax may need human |
| SCHEMA_MISMATCH | **MEDIUM** — can reconcile against actual schema | nested subtype often needs architectural rethink |
| OUTCOME_MISMATCH | **MEDIUM** — depends on subtype | EMPTY_OUTPUT often fixable (missing mapping); WRONG_VALUES may need spec clarification |
| API_ERROR | **LOW-MEDIUM** — rate_limit/server are retryable, client needs payload fix | |
| TIMEOUT | **LOW** — may need architectural change | |
| CONNECTION_ERROR | **VERY LOW** — usually requires human re-auth | Escalate immediately |
