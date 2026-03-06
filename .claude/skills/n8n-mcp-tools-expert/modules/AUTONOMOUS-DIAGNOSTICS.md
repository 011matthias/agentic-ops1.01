# Autonomous Diagnostic Ladder (n8n)

> n8n implementation of observable state diagnostics. See `.claude/rules/behaviors.md` for outcome verification principles.

**When something doesn't work as expected, exhaust these levels IN ORDER before asking the user.**

n8n's execution history exposes full node I/O — this eliminates most of Make.com's 16-level diagnostic chain. 6 levels are sufficient.

---

## Level 1: Check Execution Status

```
n8n_executions({action: "list", workflowId: "{id}", limit: 5})
```

What to read:
- `status` — success, error, waiting, canceled
- `startedAt` / `stoppedAt` — did it run at all?
- `mode` — manual, webhook, trigger (confirms how it was triggered)

**If no executions exist:** The workflow never ran. Check: is it activated? Is the webhook URL correct? Is the trigger configured?

---

## Level 2: Get Execution Detail — Find First Failing Node

```
n8n_executions({action: "get", id: "{executionId}", mode: "error"})
```

What to read:
- Which node errored first
- Error message and stack trace
- Whether the error is in a Code node (syntax), HTTP node (API), or expression (reference)

**If status is success but output is wrong:** This is an OUTCOME_MISMATCH, not an error. Proceed to Level 3.

---

## Level 3: Read Node-by-Node Output

```
n8n_executions({action: "get", id: "{executionId}", mode: "filtered"})
```

What to look for:
- **Empty arrays** — node received no items (upstream filter or empty source)
- **Null/undefined values** — expression resolved but field doesn't exist in source data
- **Wrong types** — string where number expected, object where string expected
- **Missing nodes** — node didn't execute (branch not taken, or disconnected)

Walk the execution from trigger → final node, checking each node's output matches expectations.

---

## Level 4: Cross-Reference Expressions

When a node's output has wrong data, check its expressions against the actual data from the previous node:

1. Read the workflow structure: `n8n_get_workflow({id, mode: 'structure'})`
2. Find the failing node's expression (e.g., `{{$json.body.name}}`)
3. Look at the upstream node's actual output (from Level 3)
4. Compare: does `body.name` actually exist in that output?

**Common causes:**
- Wrong node name casing (see N8N-RUNTIME-GOTCHAS G9)
- Missing `.body` for webhooks (G1)
- `.first()` instead of `.item` in iteration (G2)
- Referencing a node from the wrong branch

---

## Level 5: Isolate Logic vs Reference

When expressions look correct but produce wrong results:

1. Temporarily replace the expression with a hardcoded value
2. Re-run the workflow via `n8n_test_workflow`
3. If the workflow works with hardcoded values → the expression reference is wrong (go back to Level 4 with fresh eyes)
4. If it still fails → the node's logic or configuration is wrong (check node config via `get_node`)

Use `n8n_update_partial_workflow` to swap in hardcoded values, test, then restore the expression.

---

## Level 6: Check Credentials and Environment

```
n8n_health_check({mode: "diagnostic"})
```

Check:
- Is the n8n instance reachable?
- Are credentials valid? (403 = scope issue, 401 = expired token)
- Is the workflow activated? (webhook-triggered workflows must be active)
- Are environment variables set? (`$env` references return undefined if not configured)

**If credentials are the issue:** Escalate to user immediately — credential refresh requires UI access and cannot be done via MCP.

---

## After Level 6: Escalate

If all 6 levels exhausted without finding the root cause, escalate to user with:
1. What was tried at each level
2. What the execution data showed
3. The specific node and expression that's failing
4. A hypothesis for the root cause

---

## Anti-Pattern: Execution Succeeded != Correct Output

A successful execution status means "no unhandled errors." It does NOT mean:
- The right data was written to the right place
- Emails contain the right content
- API calls sent the right payload
- All branches executed as expected

**After every successful execution, verify outcomes.** See [POST-EXECUTION-VERIFICATION.md](POST-EXECUTION-VERIFICATION.md) for the verification procedure.
