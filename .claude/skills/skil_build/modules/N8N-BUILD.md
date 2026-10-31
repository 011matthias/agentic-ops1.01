# N8N-BUILD — n8n Implementation Workflow

Workflows are built and deployed directly in the n8n instance via MCP tools. The repo keeps a scrubbed export of each one at `workspace/clients/{client}/automations/{id}-{slug}.n8n.json` (named by the workflow's `export:` in infrastructure.yaml), written and diffed by `uv run tools/n8n_export.py --client {client} [--check]`. Client scripts go in `automations/tools/` with a `README.md` row each, tests in `automations/tests/`.

---

## The Golden Rule

**Every workflow gets a Config node immediately after the trigger.** This is the single place to switch between testing and production — no rewiring, no node toggling.

---

## Step 1: Architecture (load `n8n-pack`)

Before touching any tools, plan the workflow structure:

1. Identify which core pattern applies:
   - **Webhook Processing** — receive event → process → respond/notify
   - **HTTP API Integration** — trigger → fetch → transform → action
   - **Scheduled Polling** — schedule → query → filter → action
   - **AI Agent Workflow** — trigger → LLM agent → output
   - **Data Sync** — schedule → read source → transform → write destination

2. Map the spec's flow diagram onto the pattern
3. Identify branching points (IF nodes), loops (SplitInBatches), and error paths

Reference: load `n8n-pack` → `PROJECT-SETUP.md` module

---

## Step 2: Config Node (MANDATORY — add immediately after every trigger)

The **first node after any trigger** must always be a Code node named `"Config"`. It is the single place to switch from testing to production.

### Standard Config node template

```javascript
// ============================================================
// CONFIG — Edit this node to switch between testing and production
// ============================================================
const config = {

  // --- Mode ---
  // Set testingMode: false before activating in production
  testingMode: true,

  // --- Safety: item limit ---
  // Number of items to process per run (null = no limit, use in production)
  limitItems: 2,

  // --- Trigger window ---
  // How many days ahead to look (relevant for scheduled/polling workflows)
  triggerWindowDays: 30,

  // --- Dry run ---
  // If true: process everything but skip the final write/POST action
  dryRun: false,

};
// ============================================================
return [{ json: config }];
```

### How downstream nodes use Config

```javascript
// In any Code node downstream:
const config = $('Config').first().json;
const limit = config.limitItems;
const window = config.triggerWindowDays;
const isDryRun = config.dryRun;
```

```
// In n8n Limit nodes:
maxItems = {{ $('Config').first().json.limitItems ?? 999999 }}

// In IF nodes (dry-run gate before final write):
$('Config').first().json.dryRun === false
```

### Rules
- **Never remove Config** — only change the values inside it
- **Remove DEBUG/Limit nodes** — use `limitItems` in Config instead
- **No hardcoded test values** anywhere else in the workflow
- **Document each field** with a comment explaining what it controls

### Switching to production

Change exactly these fields in Config:
```javascript
testingMode: false,
limitItems: null,   // or remove the field
dryRun: false,
```

That is the only change needed. No node connections touched, no nodes disabled.

---

## Step 3: Node Discovery (load `n8n-pack`)

For each node needed:

```
search_nodes({query: '{service or operation}', includeExamples: true})
get_node({nodeType: 'n8n-nodes-base.{node}', detail: 'standard', includeExamples: true})
```

**Critical**: Never rely on default parameter values — they are the #1 source of runtime failures. Explicitly configure every parameter that controls behavior.

---

## Step 4: Build via MCP (load `n8n-pack`)

Use `n8n-pack` for guidance on which MCP tools to use and in what order.

### Typical build sequence:

```
# 1. Create workflow
n8n_create_workflow({name, nodes: [], connections: {}})

# 2. Validate each node before adding
validate_node({nodeType, config, mode: 'minimal'})

# 3. Add/update nodes in batches
n8n_update_partial_workflow({id, operations: [
  {type: 'updateNode', nodeId: '...', changes: {...}},
  {type: 'addConnection', source: '...', target: '...', sourcePort: 'main', targetPort: 'main'},
]})

# 4. Never make separate calls per operation — batch them
```

### Connection rules:
- IF nodes need `branch: "true"` or `branch: "false"` on connections
- Use `n8n_get_workflow({id, mode: 'structure'})` to verify topology (NOT `mode: 'full'`)

Reference: load `n8n-pack` → `LARGE-WORKFLOWS.md` module

---

## Step 5: Expressions (load `n8n-pack`)

When writing `{{ }}` expressions, load `n8n-pack` to avoid common pitfalls:

- **Iterating items**: use `$('Node').item.json.*` NOT `.first()`
- **Upstream data**: use `$('NodeName').item.json.*` NOT `$json` (which is immediate predecessor only)
- **After Slack post**: downstream nodes must reference data nodes explicitly — Slack output is the API response

---

## Step 6: Validation (load `n8n-pack`)

Run the validation loop:

```
validate_node({nodeType, config, mode: 'minimal'})        # Quick check
validate_node({nodeType, config, mode: 'full', profile: 'runtime'})  # Full check
validate_workflow(workflow)                                # Whole workflow
```

Fix ALL errors before testing. Use `n8n-pack` to interpret error messages and distinguish real errors from false positives.

---

## Step 7: Code Nodes (load `n8n-pack`)

Only if the spec requires custom logic that standard nodes can't handle.

**JavaScript** (preferred — full n8n SDK access):
- Load `n8n-pack` for syntax, `$input`/`$json`/`$node` usage, and `$helpers`

**Python** (limited — only stdlib, no n8n SDK):
- Load `n8n-pack` for Python-specific limitations and patterns

---

## Step 8: Test

```
n8n_test_workflow({workflowId})   # Execute
n8n_executions({workflowId})      # Check results
```

Verify:
- All branches execute correctly
- Data flows through the workflow as the spec describes
- Error paths are handled
- Output matches spec acceptance criteria

---

## Common Gotchas

| Problem | Fix |
|---------|-----|
| Node silently fails | Explicitly set ALL required parameters — no defaults |
| Wrong item in iteration | Use `.item.json` not `.first()` |
| Cross-branch data wrong | Reference node BEFORE the branching point |
| IF node routing | Add `branch: "true"/"false"` to connections |
| Webhook not registering | Use Manual Trigger for testing; API-created webhooks don't register |
| Upsales filter not working | Use `field=gt:value` format, not `field=value` |
| Stuck in testing mode | All test config is in Config node — just flip `testingMode: false`, `limitItems: null` |
