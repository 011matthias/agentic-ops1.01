# Post-Deployment Verification (Make.com)

> Run IMMEDIATELY after deploying a blueprint via API. Catches silent binding failures before they waste testing cycles.

## When to Use

- After every `uv run tools/make-api.py update` or `deploy`
- After every `scenarios_update` or `scenarios_create` via MCP
- NOT needed after UI-based edits (UI handles binding automatically)

---

## Step 1: Identify Binding-Dependent Modules

Read the deployed blueprint and list all modules that reference external resources:

| Module Type Pattern | Needs UI Rebinding? |
|---------------------|---------------------|
| `datastore:*` | **YES** — always |
| Any module with `connection` param | **YES** — always |
| `google-sheets:*` | **YES** — connection-dependent |
| `gmail:*` | **YES** — connection-dependent |
| `scenario-service:StartSubscenario` | **YES** — tool scenario binding |
| `http:ActionSendData` | NO — URL-based, no binding |
| `builtin:*` (Router, Resume, Sleep) | NO — no external resources |
| `util:*` | NO — no external resources |
| `flow:*` (SetVariable, GetVariable) | NO — scenario-internal |

## Step 2: Generate Rebinding Checklist

For each binding-dependent module found:

```
[ ] Module {id} ({type}): Open in UI → select {resource} from dropdown → Save
```

## Step 3: Alert User

If ANY binding-dependent modules exist:

```
POST-DEPLOYMENT BINDING REQUIRED

This blueprint was deployed via API. The following modules need
UI rebinding before they will function correctly:

{checklist from Step 2}

After rebinding in UI, the scenario is ready for testing.
```

If NO binding-dependent modules exist (rare — e.g., pure HTTP + router scenarios), skip to Step 4.

## Step 4: Post-Rebinding Verification

After user confirms rebinding:

1. Run scenario with test data (`scenarios_run` or webhook POST)
2. For data store modules: read record via `data-store-records_list` — verify values changed
3. For Google Sheets: use Sheet Reader fixture (see `context/test-fixtures.md`) — verify cells updated
4. For cursor-based polling: verify cursor value advanced
5. For tool scenarios: verify `scenarios_interface` returns expected input parameters

## Integration

- **SF-1 in FIX-PATTERNS.md** handles the case where this check was skipped and silent failure is discovered later
- **AUTONOMOUS-DIAGNOSTICS Level 1** should include binding check when diagnosing unexpected empty results after a recent deployment
- Run this check BEFORE entering the build-test-fix loop to avoid wasting iterations on binding issues
