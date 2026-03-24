# n8n Runtime Gotchas

Production-discovered quirks that silently break at runtime but pass validation. Check here first when debugging.

Format: **Symptom** → **Cause** → **Fix**

---

## G1: Webhook Data Returns Undefined

**Symptom:** `{{$json.name}}` returns undefined even though the webhook receives data.

**Cause:** Webhook node wraps incoming data under `.body`. The root `$json` contains `{headers, params, query, body}`.

**Fix:** Use `{{$json.body.name}}` not `{{$json.name}}`. All user-submitted data is under `.body`.

---

## G2: Wrong Item in Iteration

**Symptom:** All items in a loop get the same value, or data doesn't match expected item.

**Cause:** `.first()` always returns the first item. In iteration context (after SplitInBatches, or when processing multiple items), you need `.item`.

**Fix:**
- Iteration: `$('NodeName').item.json.field`
- Single value (Config, first result): `$('NodeName').first().json.field`

Rule of thumb: if data should change per item, use `.item`. If it's a constant (Config node), use `.first()`.

---

## G3: IF Node Route Never Fires

**Symptom:** One branch of an IF node never receives items, even when the condition should match.

**Cause:** The `addConnection` call didn't specify `branch: "true"` or `branch: "false"`. Without it, the connection may wire to the wrong output.

**Fix:** Always use smart parameters when connecting IF nodes:
```
{type: "addConnection", source: "IF", target: "Handler", branch: "true"}
{type: "addConnection", source: "IF", target: "Other", branch: "false"}
```

Same pattern for Switch nodes: use `case: 0`, `case: 1`, etc.

---

## G4: API-Created Webhooks Don't Trigger

**Symptom:** Workflow created via MCP with a Webhook node, but sending requests to the webhook URL produces no execution.

**Cause:** Webhooks created via API don't register in n8n's webhook listener until the workflow is activated through the UI or the webhook is explicitly registered. Test mode webhooks require the UI "Listen for test event" button.

**Fix:** For testing: add a Manual Trigger node alongside the Webhook node. Test with Manual Trigger first, then activate the workflow for production webhook use. Alternatively, use `n8n_test_workflow` which handles test execution.

---

## G5: nodeType Format Mismatch

**Symptom:** "Node not found" error when creating a workflow, or "Unknown node type" from search/validate tools.

**Cause:** Two different formats exist:
- Search/validate tools: `nodes-base.slack` (short prefix)
- Workflow tools: `n8n-nodes-base.slack` (full prefix)

**Fix:** Use `search_nodes` which returns both formats:
```json
{
  "nodeType": "nodes-base.slack",           // For search/validate
  "workflowNodeType": "n8n-nodes-base.slack" // For workflow creation
}
```

Never manually guess the prefix — always get it from `search_nodes`.

---

## G6: Validation Passes But Logic Is Wrong

**Symptom:** `validate_workflow` reports no errors, but the workflow produces wrong results.

**Cause:** Validation checks structure (required fields, types, connections) not logic (correct expressions, right data flow, business rules).

**Fix:** Validation is necessary but not sufficient. After validation passes:
1. Run `n8n_test_workflow` with real or realistic data
2. Read execution results via `n8n_executions` to verify actual output
3. Check each node's output matches expectations (see POST-EXECUTION-VERIFICATION module)

---

## G7: Auto-Sanitization Modifies Unrelated Nodes

**Symptom:** After updating one node, other nodes (especially IF/Switch) have changed operator metadata.

**Cause:** Every `n8n_update_partial_workflow` call triggers auto-sanitization on ALL nodes in the workflow. This fixes operator structures (adds `singleValue: true` to unary operators, removes it from binary ones).

**Fix:** This is expected behavior and generally beneficial. Be aware that:
- Binary operators (equals, contains): `singleValue` is removed
- Unary operators (isEmpty, isNotEmpty): `singleValue: true` is added
- IF/Switch metadata is normalized

If you see unexpected changes, re-validate the workflow — auto-sanitization fixes are almost always correct.

---

## G8: Config Node Not Found in Expressions

**Symptom:** `$('Config').first().json.field` returns "Referenced node 'Config' does not exist."

**Cause:** The Config Code node was renamed, deleted, or the name doesn't match exactly (case-sensitive).

**Fix:** Config node must be named exactly `Config` (capital C). Verify with `n8n_get_workflow({id, mode: 'structure'})` — check that a node named "Config" exists. If renamed, either restore the name or update all downstream references.

---

## G9: Node Name Case Mismatch in Expressions

**Symptom:** `$node["http request"].json` returns undefined even though the node exists.

**Cause:** Node names are case-sensitive. `"http request"` != `"HTTP Request"`.

**Fix:** Match the exact node name as shown in the workflow. Use `n8n_get_workflow({id, mode: 'structure'})` to see exact names. Common mistake: lowercase when n8n defaults to Title Case.

---

## G10: Expression Works in Editor But Fails at Runtime

**Symptom:** Expression preview in the UI shows correct value, but execution produces undefined or error.

**Cause:** The expression editor uses test data from the last execution. If the actual execution data has a different structure (e.g., missing fields, different nesting), the expression fails.

**Fix:** Don't rely solely on the expression editor preview. Test with actual production-like data via `n8n_test_workflow`, then inspect the execution to see what data each node actually received.

---

---

## G11: n8n Cloud Code Node Cannot Make External HTTP Calls

**Symptom:** `fetch()` or `$helpers.httpRequest()` calls in Code nodes return errors or fail silently. All external API calls produce 0 results.

**Cause:** n8n Cloud Code node sandbox blocks ALL external HTTP — both the browser-native `fetch()` and n8n's `$helpers.httpRequest()`. This applies to Code nodes only.

**Fix:** Use HTTP Request nodes (type: `n8n-nodes-base.httpRequest`) for all external API calls. Code nodes can only process data that's already been fetched by preceding HTTP Request nodes.

---

## G12: Python f-strings Collapse n8n Expression Braces

**Symptom:** n8n expression like `{{ $json.id }}` gets deployed as `{ $json.id }` (single braces) and fails at runtime — "Invalid expression" or treats the value as a literal string.

**Cause:** Python f-strings treat `{{` as an escaped `{` and output a single `{`. So `f"={{ $json.id }}"` becomes `={ $json.id }` in the deployed workflow.

**Fix:** Build n8n expressions using string concatenation, not f-strings:
```python
# WRONG: f"={{ 'https://api.com/' + $json.id }}"
# CORRECT:
url_expr = "={{ 'https://api.com/' + $json.id + '/analytics' }}"
```
Or use `{{` only if you want a literal `{` in your Python string.

---

## G13: Split In Batches typeVersion 1 Has No Done Output

**Symptom:** Downstream nodes connected to Split In Batches output[1] ("done") never execute. The loop runs all batches but the chain after the loop is skipped.

**Cause:** Split In Batches typeVersion 1 only has output[0] (current batch). The done output[1] was added in typeVersion 3. With typeVersion 1, the done connection fires 0 items.

**Fix:** Use `typeVersion: 3` for Split In Batches when you need the done output to trigger downstream nodes after all batches complete.

---

## G14: HTTP Request Node Runs Once Per Input Item

**Symptom:** A Clear/Setup node (meant to run once) runs N times when it receives N items from a previous node, causing rate limit errors (429) or unexpected multiple writes.

**Cause:** HTTP Request nodes process every input item independently — one HTTP call per item. If the preceding node returns 1000 items, the HTTP node makes 1000 requests.

**Fix:** Place setup/cleanup nodes BEFORE nodes that fan out to many items:
```
Trigger (1 item) → Clear Sheet (1 call) → Read All Data (returns N items) → Process N items
```
NOT:
```
Trigger → Read All Data (N items) → Clear Sheet (N calls!) → Process
```

---

## Quick Lookup Table

| Symptom | Gotcha | Fix |
|---------|--------|-----|
| Webhook fields undefined | G1 | Add `.body` to path |
| Same value for all items | G2 | Use `.item` not `.first()` |
| IF branch never fires | G3 | Add `branch: "true"/"false"` |
| Webhook doesn't trigger | G4 | Use Manual Trigger for testing |
| "Node not found" on create | G5 | Check nodeType prefix format |
| Validation passes, wrong output | G6 | Test with real data + verify |
| Unrelated nodes changed | G7 | Expected auto-sanitization |
| "Config does not exist" | G8 | Name must be exactly "Config" |
| Node ref returns undefined | G9 | Match exact case |
| Works in editor, fails at runtime | G10 | Test with production data |
| fetch()/httpRequest() returns nothing | G11 | Use HTTP Request nodes instead |
| n8n expressions have single braces | G12 | Use string concatenation, not f-strings |
| Loop done-output never fires | G13 | Use Split In Batches typeVersion 3 |
| Clear/setup node runs N times | G14 | Place setup before fan-out nodes |
