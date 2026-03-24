# Post-Execution Outcome Verification (n8n)

> n8n implementation of outcome verification. See `.claude/rules/rule_behaviors.md` for orchestrator-agnostic principles.

**Always verify OUTCOMES, not just STATUS.** A successful execution means "no unhandled errors" — it does NOT mean the right data landed in the right place.

---

## What IS Directly Verifiable via MCP

n8n's execution history exposes full node I/O. These outputs can be verified autonomously:

| Output Type | How to Verify | MCP Call |
|-------------|--------------|----------|
| Node output data | Read from execution history | `n8n_executions({action: "get", id, mode: "filtered"})` |
| HTTP response body | Read HTTP Request node output | Same — check the HTTP node's output in execution |
| API call payload | Read what was sent | Check HTTP node's input in execution |
| Database query results | Read query node output | Check Postgres/MySQL node output |
| Slack message delivery | Read Slack node output (contains ts, channel) | Check Slack node output |
| Code node results | Read Code node output | Check Code node output |
| IF/Switch routing | Check which branch executed | See which downstream nodes have execution data |

---

## What is NOT Directly Verifiable

| Output Type | Why Not | Mitigation |
|-------------|---------|-----------|
| Gmail sent content | n8n MCP can't read Gmail inbox | Ask user to verify, or add a read-back workflow |
| Google Sheets cell values | No Sheets read via MCP | Add an HTTP Request verification node (Sheets API) at workflow end |
| External system state | Depends on the system's API | Add a verification HTTP Request node that reads back |
| Webhook response received by caller | Caller is external | Check Respond to Webhook node output in execution |
| File contents written | File system not accessible | Add a read-back step or verify file size |

---

## Verification Procedure

### 1. Define Expected Outcomes (BEFORE running)

Before executing, state what SHOULD happen for each acceptance criterion:
- What data should appear in the final node's output?
- What API calls should be made with what payloads?
- What records should be created/updated?
- What messages should be sent?

### 2. Execute and Read

```
n8n_test_workflow({workflowId: "{id}"})
n8n_executions({action: "list", workflowId: "{id}", limit: 1})
n8n_executions({action: "get", id: "{executionId}", mode: "filtered"})
```

### 3. Verify Node-by-Node

Map each spec acceptance criterion to a node name, then check that node's output:

| Acceptance Criterion | Node to Check | Expected Output | Actual Output | Match? |
|---------------------|---------------|-----------------|---------------|--------|
| Lead logged in sheet | Google Sheets node | Row with name, email | (from execution) | Y/N |
| Email sent | Gmail node | Status: sent | (from execution) | Y/N |
| Slack notified | Slack node | Message posted | (from execution) | Y/N |

### 4. If Mismatch

When actual doesn't match expected:
1. Identify the first node where data diverges from expectations
2. Check that node's input — is it receiving the right data?
3. If input is wrong → trace upstream (the problem is before this node)
4. If input is right but output is wrong → the node's configuration is wrong
5. Use the [AUTONOMOUS-DIAGNOSTICS](AUTONOMOUS-DIAGNOSTICS.md) ladder for systematic debugging

### 5. After Fix, Verify Again

Re-run and re-verify. Don't assume the fix worked.

---

## Verification Fixture Pattern

For outputs that are repeatedly unverifiable (e.g., Google Sheets values), add a **verification node** at the end of the workflow:

```
... → Google Sheets (write) → HTTP Request (Sheets API GET) → Set (format result)
```

This read-back node makes the written data appear in the execution history, making it autonomously verifiable. The pattern:

1. After the write node, add an HTTP Request node
2. Configure it to read back the data just written (e.g., Sheets API `GET` on the row)
3. The response appears in execution history
4. Now the agent can verify the write autonomously

**When to add verification fixtures:**
- The workflow writes to a system we can't read via MCP
- The same workflow will be tested repeatedly (not a one-off)
- Add as a permanent part of the workflow with a Config flag: `config.enableVerification`

**In production:** Set `enableVerification: false` to skip the read-back (saves API calls). Keep it enabled during testing.

---

## Proxy Indicators

When direct verification and fixtures aren't available:

| Indicator | What It Tells You |
|-----------|-------------------|
| Node executed at all | It appears in execution data with output |
| Output array length > 0 | Node processed at least one item |
| HTTP status 200/201 | API accepted the request (but didn't necessarily process it correctly) |
| Execution node count | If fewer nodes executed than expected, a branch was skipped |
| Code node output shape | Confirms transformation logic produced the right structure |
