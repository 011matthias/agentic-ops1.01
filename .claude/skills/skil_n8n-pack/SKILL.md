---
name: n8n-pack
description: Consolidated n8n skill pack. Use when building, editing, testing, or debugging n8n workflows. Replaces 8 individual n8n skills. Load modules individually per task — never load all at once.
---

# n8n Pack

Unified reference for building n8n workflows. Consolidates: n8n-mcp-tools-expert, n8n-workflow-patterns, n8n-node-configuration, n8n-expression-syntax, n8n-validation-expert, n8n-code-javascript, n8n-code-python.

---

## Build Procedure

1. **Detect** — `uv run tools/infra_yaml.py --client {client}` prints `orchestrator=n8n` (top-level `orchestrator:`, then an instance `type: n8n`). `.mcp.json` having `n8n-{client}` only means this machine has the API credentials wired
2. **Read spec** — Extract flow, systems, edge cases, acceptance criteria
3. **Choose pattern** → Load PATTERNS module for architecture
4. **Search nodes** → Use `search_nodes` + `get_node` (detail="standard")
5. **Build workflow** → `n8n_create_workflow` then iterate with `n8n_update_partial_workflow`
6. **Configure nodes** → Load NODE-CONFIG module for per-node parameters
7. **Write expressions** → Load EXPRESSIONS module for `{{}}` syntax
8. **Add Code nodes** → Load CODE-JS or CODE-PYTHON module if needed
9. **Validate** → `n8n_validate_workflow`, load VALIDATION module if errors
10. **Activate** → `activateWorkflow` operation

---

## Critical Rules (Always Apply)

- **nodeType formats differ:** `nodes-base.*` for search/validate, `n8n-nodes-base.*` for workflow create/update
- **Use detail="standard"** for get_node (not "full" — saves tokens)
- **Iterate workflows** — build incrementally (avg 56s between edits), not one-shot
- **Use smart parameters** — `branch: "true"/"false"` for IF, `case: N` for Switch
- **Include intent parameter** in every `n8n_update_partial_workflow` call
- **Auto-sanitization runs on ALL nodes** during any workflow update

---

## Module Index

Load ONE module at a time based on your current task.

### Procedure Modules (load when performing the task)

| When | Module |
|------|--------|
| Searching for nodes | [SEARCH-GUIDE](modules/SEARCH-GUIDE.md) |
| Managing workflows (create/update/activate) | [WORKFLOW-GUIDE](modules/WORKFLOW-GUIDE.md) |
| Validating node configs | [VALIDATION-GUIDE](modules/VALIDATION-GUIDE.md) |
| Choosing architecture pattern | [WEBHOOK-PROCESSING](modules/WEBHOOK-PROCESSING.md) / [SCHEDULED-TASKS](modules/SCHEDULED-TASKS.md) / [HTTP-API](modules/HTTP-API-INTEGRATION.md) / [AI-AGENT](modules/AI-AGENT-WORKFLOW.md) / [DATABASE](modules/DATABASE-OPERATIONS.md) |
| Configuring specific nodes | [OPERATION-PATTERNS](modules/OPERATION-PATTERNS.md) |
| Writing `{{}}` expressions | [EXAMPLES](modules/EXAMPLES.md) / [COMMON-MISTAKES](modules/COMMON-MISTAKES.md) |
| Writing JavaScript Code nodes | [JS-COMMON-PATTERNS](modules/JS-COMMON-PATTERNS.md) |
| Writing Python Code nodes | [PY-COMMON-PATTERNS](modules/PY-COMMON-PATTERNS.md) |
| Debugging runtime issues | [AUTONOMOUS-DIAGNOSTICS](modules/AUTONOMOUS-DIAGNOSTICS.md) |
| Verifying execution outcomes | [POST-EXECUTION-VERIFICATION](modules/POST-EXECUTION-VERIFICATION.md) |
| Pre-handover checklist | [PRE-CLIENT-REVIEW](modules/PRE-CLIENT-REVIEW.md) |
| Discovering webhook payloads | [WEBHOOK-PAYLOAD-INSPECTOR](modules/WEBHOOK-PAYLOAD-INSPECTOR.md) |
| Large workflow handling | [LARGE-WORKFLOWS](modules/LARGE-WORKFLOWS.md) |
| Project setup principles | [PROJECT-SETUP](modules/PROJECT-SETUP.md) |

### Reference Modules (load ONLY for specific lookups — never proactively)

| When | Module |
|------|--------|
| Runtime error encountered | [N8N-RUNTIME-GOTCHAS](modules/N8N-RUNTIME-GOTCHAS.md) |
| Validation error to interpret | [ERROR-CATALOG](modules/ERROR-CATALOG.md) |
| False positive validation | [FALSE-POSITIVES](modules/FALSE-POSITIVES.md) |
| Node displayOptions dependencies | [DEPENDENCIES](modules/DEPENDENCIES.md) |
| Expression common mistakes | [COMMON-MISTAKES](modules/COMMON-MISTAKES.md) |
| Expression examples | [EXAMPLES](modules/EXAMPLES.md) |
| JS builtin functions | [BUILTIN-FUNCTIONS](modules/BUILTIN-FUNCTIONS.md) |
| Python stdlib catalog | [STANDARD-LIBRARY](modules/STANDARD-LIBRARY.md) |
| JS/Python data access | [DATA-ACCESS (JS)](modules/JS-DATA-ACCESS.md) / [DATA-ACCESS (Python)](modules/PY-DATA-ACCESS.md) |
| JS/Python error patterns | [ERROR-PATTERNS (JS)](modules/JS-ERROR-PATTERNS.md) / [ERROR-PATTERNS (Python)](modules/PY-ERROR-PATTERNS.md) |
| JS/Python common patterns | [COMMON-PATTERNS (JS)](modules/JS-COMMON-PATTERNS.md) / [COMMON-PATTERNS (Python)](modules/PY-COMMON-PATTERNS.md) |

---

## Tool Availability

**Always available** (no n8n API needed): search_nodes, get_node, validate_node, validate_workflow, search_templates, get_template

**Requires n8n API** (N8N_API_URL + N8N_API_KEY): n8n_create_workflow, n8n_update_partial_workflow, n8n_validate_workflow (by ID), n8n_list_workflows, n8n_get_workflow, n8n_test_workflow, n8n_executions, n8n_deploy_template
