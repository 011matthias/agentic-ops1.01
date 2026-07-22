# Outcome Verification

Orchestrator-agnostic procedure for verifying that execution outputs are **correct**, not just that execution **succeeded**. A successful execution status means "no unhandled errors" — it does NOT mean the right data landed in the right place.

> This module enforces **Testing Philosophy Principle #1: Outcome Verification, Not Status Checking**.

## When to Use

- **Mandatory** after every successful execution in the build-test-fix iteration loop (Step 4 of ITERATION-LOOP.md)
- **Mandatory** in build-orchestrator Phase 3.5 (Dev Test) and Phase 6 (Verify)
- After any scenario/workflow runs without errors but before reporting "success"

## Procedure

### Step 1: Extract Expected Outcomes

Before execution, read the spec's acceptance criteria and define concrete expected outcomes:

```
For each output of this automation:
  - What system receives the output? (spreadsheet, email, data store, API, notification)
  - What specific fields/values should be present?
  - What does "correct" look like for each field?
```

**Do NOT accept vague criteria.** Transform them:
- Bad: "Email is sent" → Good: "Email sent to `{{lead_email}}` with subject containing lead name, body_html > 100 chars, no `##` placeholder literals"
- Bad: "Row updated" → Good: "Row N column F = 2, column G = current date, column H = 'initial_sent'"
- Bad: "Notification posted" → Good: "Slack message in #channel contains lead name and priority level"

### Step 2: Execute

Run the scenario/workflow with realistic test data (see ITERATION-LOOP.md Step 1).

### Step 3: Verify Outcomes by Output Type

After execution succeeds (status OK), verify each output against expected outcomes.

#### Email Outputs
| Check | How to Verify | Autonomous? |
|-------|--------------|-------------|
| Email sent | Operations count includes email module | Yes |
| Recipient correct | Check email module input mapping in execution detail | Partial (Make: check mapping, can't read Gmail) |
| Subject populated | Check email module input — subject field non-empty | Partial |
| Body non-empty | Transfer bytes for email module > threshold (~500 bytes min for HTML) | Yes (proxy) |
| Placeholders resolved | No `##placeholder##` literals in subject/body | No (requires reading sent email) |
| AI content injected | If AI module ran (ops count), check its output length > 0 | Yes (check AI module output) |

**Mostly verifiable via proxies:** Before asking the user to check email content:
1. Check `context/test-fixtures.md` for an Email Reader fixture
2. Check email module input mapping — populated subject + body_html with non-placeholder values = strong proxy
3. Check AI module output (non-empty) + email module transfer bytes > 500 = high confidence
4. Only ask user if ALL proxy indicators are inconclusive

#### Spreadsheet Outputs
| Check | How to Verify | Autonomous? |
|-------|--------------|-------------|
| Row written/updated | Operations count includes sheets module | Yes |
| Correct columns | Check module input mapping for column references | Partial |
| Values correct | **Check `context/test-fixtures.md` for Sheet Reader fixture.** If exists: curl the webhook URL, parse pipe-separated response, compare field-by-field against expected. If no fixture exists: create one using `make-api.py`. | **Yes (with fixtures)** |

#### Data Store Outputs
| Check | How to Verify | Autonomous? |
|-------|--------------|-------------|
| Record created/updated | `data-store-records_list(dataStoreId)` | Yes |
| All fields populated | Read record, check each field is non-null/non-empty | Yes |
| Values correct | Compare field values against expected | Yes |

#### API Call Outputs
| Check | How to Verify | Autonomous? |
|-------|--------------|-------------|
| Response status | Execution detail shows HTTP module status | Yes |
| Response body | Execution detail shows HTTP module output | Yes |
| Side effect in target system | Call target API to read the result | Depends |

#### Notification Outputs (Slack, etc.)
| Check | How to Verify | Autonomous? |
|-------|--------------|-------------|
| Message sent | Operations count includes notification module | Yes |
| Content correct | Check module input mapping | Partial |

### Fixture-Based Verification (Make.com)

Before falling back to proxy indicators or user verification, check for persistent test fixtures:

1. **Read `workspace/clients/{client}/context/test-fixtures.md`** for available fixtures
2. **Sheet Reader pattern:** `curl -s "{WEBHOOK_URL}"` returns pipe-separated `key=value` pairs. Parse and compare field-by-field against expected values.
3. **Cell Writer pattern:** `uv run tools/make-api.py scenario-run --zone {ZONE} --scenario-id {WRITER_ID} --data '{"cell":"{CELL}","value":"{VALUE}"}'` to set preconditions before test runs.
4. **Full autonomous test cycle:**
   ```
   READ  -> curl Sheet Reader -> baseline state
   SET   -> Cell Writer -> set preconditions (timestamps, flags, step values)
   RUN   -> trigger scenario under test (webhook POST or scenarios_run)
   READ  -> curl Sheet Reader -> new state
   COMPARE -> expected vs actual, field by field
   ```

This converts "unverifiable" spreadsheet outputs into fully autonomous verification. Use it instead of asking the user.

### Step 4: Classify Results

After checking all outputs:

**All outcomes match** → Report success with verification table (see report format below).

**Any outcome mismatches** → Classify as `OUTCOME_MISMATCH` with sub-type:

| Sub-type | Detection Pattern |
|----------|------------------|
| `EMPTY_OUTPUT` | Transfer bytes suspiciously low; data store field empty; operations count lower than expected |
| `WRONG_VALUES` | Field-by-field comparison fails; values present but incorrect |
| `MISSING_FIELDS` | Expected fields not populated; nulls where values expected |
| `STRUCTURAL_MISMATCH` | Output shape differs from expected (array vs object, nested vs flat) |

→ Return to ITERATION-LOOP.md Step 6 (LOOKUP fix) with the `OUTCOME_MISMATCH` category.

**Some outcomes unverifiable** → Document them explicitly (see report format). These represent verification debt.

### Step 5: Document Unverifiable Outputs

For every output that cannot be verified autonomously:

```markdown
### Unverifiable Outputs (Verification Debt)

| Output | Why Unverifiable | Mitigation |
|--------|-----------------|------------|
| Email body content | No Gmail read via MCP | Ask user to check 1 email; consider UTIL - Email Reader fixture |
| Sheet cell values | No Sheets read via MCP | Use Sheet Reader fixture (scenario ID: {X}) if available |
```

Each unverifiable item is a candidate for a persistent test fixture. If the same output is unverifiable across 2+ builds, create the fixture.

---

## Orchestrator-Specific Verification

### Make.com

Uses `executions_list` → `executions_get_detail` for execution metadata. Integrates with the [POST-EXECUTION-VERIFICATION](../../skil_make-mcp-tools-expert/modules/POST-EXECUTION-VERIFICATION.md) module for Make.com-specific patterns.

Key proxies:
- **Operations count:** Compare expected module count vs actual. Fewer ops = something was skipped (filter blocked, error handler caught).
- **Transfer bytes:** Compare against known-good baseline. Suspiciously low = empty payload/body.
- **Data stores:** Fully readable via `data-store-records_list`. Always verify data store outputs directly.

### n8n

Uses execution history via MCP. Each node's output is visible in execution data.
- Read node output directly from execution history
- Compare output fields against expected values
- Check for empty arrays or null values in node outputs

### Trigger.dev

Uses task run logs. Output is returned from the task function.
- Read task run output from logs/dashboard
- Compare returned values against expected
- Check for partial outputs (task completed but returned incomplete data)

---

## Success Report Format

Include in the build-test-fix success report:

```markdown
### Outcome Verification
| Output | Expected | Actual | Match? |
|--------|----------|--------|--------|
| {system: field} | {expected value/condition} | {actual value/condition} | Yes/No |

### Unverifiable Outputs
| Output | Why | Suggested Fixture |
|--------|-----|-------------------|
| {output} | {reason} | {fixture suggestion or "N/A"} |
```

---

## Integration Points

- **ITERATION-LOOP.md** — Called at Step 4 (after execution success, before reporting)
- **FAILURE-TAXONOMY.md** — Adds `OUTCOME_MISMATCH` category with 4 sub-types
- **FIX-PATTERNS.md** — Outcome mismatch fixes added as `OM-*` patterns
- **POST-EXECUTION-VERIFICATION.md** (Make.com) — Referenced for Make-specific verification; this module is the orchestrator-agnostic wrapper
- **build-orchestrator.md** — Mandatory gate in Phase 3.5 and Phase 6
