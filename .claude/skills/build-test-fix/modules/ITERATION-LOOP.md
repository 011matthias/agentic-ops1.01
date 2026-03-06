# Iteration Loop

The autonomous build→test→classify→fix→retest procedure.

## Prerequisites

- A scenario/workflow ID that has been deployed (at least blueprint exists)
- For Make.com: active scenario with valid connections
- For n8n: workflow exists in the instance
- Test data available (webhook payload, sample input, or cron trigger)

## The Loop

```
iteration = 0
max_iterations = 3
fix_history = []

while iteration < max_iterations:
    1. EXECUTE
    2. READ RESULTS
    3. if EXECUTION ERROR → go to step 5 (CLASSIFY)
    4. if EXECUTION SUCCESS → VERIFY OUTCOMES (see OUTCOME-VERIFICATION.md)
       - if OUTCOMES MATCH → break (report success with verification table)
       - if OUTCOMES MISMATCH → classify as OUTCOME_MISMATCH (go to step 5)
       - if UNVERIFIABLE OUTPUTS → document them, continue to step 4b
       4b. If all verifiable outcomes match → break (report success + verification debt)
           If any verifiable outcome mismatches → go to step 5
    5. CLASSIFY failure (see FAILURE-TAXONOMY.md)
       - Execution errors: EXPRESSION_ERROR, CONNECTION_ERROR, SCHEMA_MISMATCH, etc.
       - Outcome mismatches: OUTCOME_MISMATCH.EMPTY_OUTPUT, .WRONG_VALUES, etc.
    6. CHECK fix_history — is this the same error category as a previous iteration?
       - If yes AND same fix approach → escalate (we're going in circles)
    7. LOOKUP fix in FIX-PATTERNS.md
       - If found → apply fix, record in fix_history
       - If not found → escalate (novel error)
    8. iteration += 1

if iteration == max_iterations:
    ESCALATE with full diagnosis
```

## Step 1: Execute

### Make.com
```
1. Fetch scenario state: scenarios_get(scenarioId)
2. If scenario is inactive: scenarios_activate(scenarioId)
3. Execute: scenarios_run(scenarioId)
   - OR: POST to webhook URL with test payload
4. Wait 5-10 seconds for execution to complete
```

### n8n
```
1. Trigger workflow execution via MCP
2. Or POST to webhook URL with test payload
3. Wait for execution to complete
```

### Trigger.dev
```
1. Trigger task via API or CLI
2. Wait for task run to complete
```

## Step 2: Read Results

### Make.com
```
1. executions_list(scenarioId, limit: 1) → get latest execution ID
2. executions_get_detail(executionId) → full module-by-module results
3. For each module in execution:
   - Check status (success/error/skipped)
   - If error: capture error message, module ID, module type
   - If success: note output shape (for downstream validation)
```

### n8n
```
1. Read execution history via MCP
2. Check each node's output/error status
```

### Trigger.dev
```
1. Read task run output from logs
2. Check for error/exception traces
```

## Step 3: Verify Outcomes (NEW — after execution success)

If all modules executed without errors, do NOT report success yet. Load [OUTCOME-VERIFICATION.md](OUTCOME-VERIFICATION.md) and:

1. **Extract expected outcomes** from the spec's acceptance criteria
2. **Verify each output** using the orchestrator-specific checks in OUTCOME-VERIFICATION.md
3. **Build verification table:**
   ```
   | Output | Expected | Actual | Match? |
   |--------|----------|--------|--------|
   ```
4. **If any mismatch** → classify as `OUTCOME_MISMATCH` (see FAILURE-TAXONOMY.md) → proceed to Step 4
5. **If all match** → report success (include verification table in report)
6. **Document unverifiable outputs** — any output that couldn't be checked autonomously

## Step 4: Classify

Map the error to the taxonomy in FAILURE-TAXONOMY.md. Key signals:

| Signal in Error Message | Category |
|------------------------|----------|
| "Unable to parse" / "Invalid expression" / "syntax error" | `EXPRESSION_ERROR` |
| "Authorization" / "Invalid credentials" / "token expired" | `CONNECTION_ERROR` |
| "field not found" / "property does not exist" / "undefined" | `SCHEMA_MISMATCH` |
| "Unable to parse range" / "No items" / empty array | `EMPTY_RESULT` |
| "429" / "500" / "rate limit" / "quota exceeded" | `API_ERROR` |
| "timeout" / "ETIMEDOUT" / "exceeded time limit" | `TIMEOUT` |

## Step 5: Fix

1. Look up the error category + context in FIX-PATTERNS.md
   - For `OUTCOME_MISMATCH` categories, also check OUTCOME-VERIFICATION.md for output-specific guidance
2. Choose the most specific matching pattern
3. Apply the fix:
   - **Make.com**: Fetch current blueprint → modify → `scenarios_update`
   - **n8n**: Fetch workflow → modify → update via MCP
   - **Trigger.dev**: Edit source file directly
4. Record the fix in `fix_history`:
   ```
   { iteration: N, category: "...", fix_applied: "...", module_id: N }
   ```

## Step 6: Retest

Go back to Step 1. The loop continues.

## Escalation Format

When escalating to the user, provide:

```markdown
## Build-Test-Fix Escalation

**Scenario:** {name} (ID: {id})
**Iterations attempted:** {N}
**Error category:** {category}

### What failed
- Module: {module_id} ({module_type})
- Error: {exact error message}

### What I tried
| Iteration | Fix Applied | Result |
|-----------|------------|--------|
| 1 | {fix description} | {still failed because...} |
| 2 | {different fix} | {still failed because...} |

### My diagnosis
{What I think the root cause is, based on execution data}

### Suggested next steps
1. {Most likely fix that requires human judgment}
2. {Alternative approach}
```

## Log Friction Event

When escalating (any trigger — max iterations, repeated category, or novel error), append a row to `docs/friction-register.md`:

```
| {DATE} | {CLIENT} | ESCALATION | {Category}: {1-line description} | No |
```

For novel errors (not in FIX-PATTERNS.md), also log even if the loop hasn't exhausted iterations:

```
| {DATE} | {CLIENT} | KNOWLEDGE_GAP | Novel error: {category} — {description} | No |
```

---

## Success Report

When the loop succeeds:

```markdown
## Build-Test-Fix: SUCCESS

**Scenario:** {name} (ID: {id})
**Iterations:** {N} (1 = first try, 2+ = required fixes)

### Fixes Applied
| Iteration | Category | Fix |
|-----------|----------|-----|
| {N} | {category} | {description} |

### Outcome Verification
| Output | Expected | Actual | Match? |
|--------|----------|--------|--------|
| {system: field} | {expected} | {actual} | Yes/No |

### Unverifiable Outputs (Verification Debt)
| Output | Why Unverifiable | Suggested Fixture |
|--------|-----------------|-------------------|
| {output} | {reason} | {fixture or "N/A"} |

### Operationalization
{If a fix was novel (not in FIX-PATTERNS.md), note it for addition to the registry}
{If unverifiable outputs recur across 2+ builds, recommend creating a persistent test fixture}
```
