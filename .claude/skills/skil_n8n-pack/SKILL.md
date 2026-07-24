---
name: n8n-pack
description: Consolidated n8n skill pack. Use when building, editing, testing, or debugging n8n workflows. Replaces 8 individual n8n skills. Load modules individually per task — never load all at once.
---

# n8n Pack

Unified reference for building n8n workflows. Consolidates: n8n-mcp-tools-expert, n8n-workflow-patterns, n8n-node-configuration, n8n-expression-syntax, n8n-validation-expert, n8n-code-javascript, n8n-code-python.

---

## Build Procedure

1. **Detect** — Confirm n8n orchestrator (`.mcp.json` has `n8n-{client}`)
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

| When | Module | Source |
|------|--------|--------|
| Searching for nodes | [SEARCH-GUIDE](../skil_n8n-mcp-tools-expert/modules/SEARCH-GUIDE.md) | n8n-mcp-tools-expert |
| Managing workflows (create/update/activate) | [WORKFLOW-GUIDE](../skil_n8n-mcp-tools-expert/modules/WORKFLOW-GUIDE.md) | n8n-mcp-tools-expert |
| Validating node configs | [VALIDATION-GUIDE](../skil_n8n-mcp-tools-expert/modules/VALIDATION-GUIDE.md) | n8n-mcp-tools-expert |
| Choosing architecture pattern | [WEBHOOK-PROCESSING](../skil_n8n-workflow-patterns/modules/WEBHOOK-PROCESSING.md) / [SCHEDULED-TASKS](../skil_n8n-workflow-patterns/modules/SCHEDULED-TASKS.md) / [HTTP-API](../skil_n8n-workflow-patterns/modules/HTTP-API-INTEGRATION.md) / [AI-AGENT](../skil_n8n-workflow-patterns/modules/AI-AGENT-WORKFLOW.md) / [DATABASE](../skil_n8n-workflow-patterns/modules/DATABASE-OPERATIONS.md) | n8n-workflow-patterns |
| Configuring specific nodes | [OPERATION-PATTERNS](../skil_n8n-node-configuration/modules/OPERATION-PATTERNS.md) | n8n-node-configuration |
| Writing `{{}}` expressions | [n8n-expression-syntax SKILL](../skil_n8n-expression-syntax/SKILL.md) | n8n-expression-syntax |
| Writing JavaScript Code nodes | [n8n-code-javascript SKILL](../skil_n8n-code-javascript/SKILL.md) | n8n-code-javascript |
| Writing Python Code nodes | [n8n-code-python SKILL](../skil_n8n-code-python/SKILL.md) | n8n-code-python |
| Debugging runtime issues | [AUTONOMOUS-DIAGNOSTICS](../skil_n8n-mcp-tools-expert/modules/AUTONOMOUS-DIAGNOSTICS.md) | n8n-mcp-tools-expert |
| Verifying execution outcomes | [POST-EXECUTION-VERIFICATION](../skil_n8n-mcp-tools-expert/modules/POST-EXECUTION-VERIFICATION.md) | n8n-mcp-tools-expert |
| Pre-handover checklist | [PRE-CLIENT-REVIEW](../skil_n8n-mcp-tools-expert/modules/PRE-CLIENT-REVIEW.md) | n8n-mcp-tools-expert |
| Discovering webhook payloads | [WEBHOOK-PAYLOAD-INSPECTOR](../skil_n8n-workflow-patterns/modules/WEBHOOK-PAYLOAD-INSPECTOR.md) | n8n-workflow-patterns |
| Large workflow handling | [LARGE-WORKFLOWS](../skil_n8n-mcp-tools-expert/modules/LARGE-WORKFLOWS.md) | n8n-mcp-tools-expert |
| Project setup principles | [PROJECT-SETUP](../skil_n8n-mcp-tools-expert/modules/PROJECT-SETUP.md) | n8n-mcp-tools-expert |

### Reference Modules (load ONLY for specific lookups — never proactively)

| When | Module | Source |
|------|--------|--------|
| Runtime error encountered | [N8N-RUNTIME-GOTCHAS](../skil_n8n-mcp-tools-expert/modules/N8N-RUNTIME-GOTCHAS.md) | n8n-mcp-tools-expert |
| Validation error to interpret | [ERROR-CATALOG](../skil_n8n-validation-expert/modules/ERROR-CATALOG.md) | n8n-validation-expert |
| False positive validation | [FALSE-POSITIVES](../skil_n8n-validation-expert/modules/FALSE-POSITIVES.md) | n8n-validation-expert |
| Node displayOptions dependencies | [DEPENDENCIES](../skil_n8n-node-configuration/modules/DEPENDENCIES.md) | n8n-node-configuration |
| Expression common mistakes | [COMMON-MISTAKES](../skil_n8n-expression-syntax/modules/COMMON-MISTAKES.md) | n8n-expression-syntax |
| Expression examples | [EXAMPLES](../skil_n8n-expression-syntax/modules/EXAMPLES.md) | n8n-expression-syntax |
| JS builtin functions | [BUILTIN-FUNCTIONS](../skil_n8n-code-javascript/modules/BUILTIN-FUNCTIONS.md) | n8n-code-javascript |
| Python stdlib catalog | [STANDARD-LIBRARY](../skil_n8n-code-python/modules/STANDARD-LIBRARY.md) | n8n-code-python |
| JS/Python data access | [DATA-ACCESS (JS)](../skil_n8n-code-javascript/modules/DATA-ACCESS.md) / [DATA-ACCESS (Python)](../skil_n8n-code-python/modules/DATA-ACCESS.md) | n8n-code-* |
| JS/Python error patterns | [ERROR-PATTERNS (JS)](../skil_n8n-code-javascript/modules/ERROR-PATTERNS.md) / [ERROR-PATTERNS (Python)](../skil_n8n-code-python/modules/ERROR-PATTERNS.md) | n8n-code-* |
| JS/Python common patterns | [COMMON-PATTERNS (JS)](../skil_n8n-code-javascript/modules/COMMON-PATTERNS.md) / [COMMON-PATTERNS (Python)](../skil_n8n-code-python/modules/COMMON-PATTERNS.md) | n8n-code-* |

---

## Tool Availability

**Always available** (no n8n API needed): search_nodes, get_node, validate_node, validate_workflow, search_templates, get_template

**Requires n8n API** (N8N_API_URL + N8N_API_KEY): n8n_create_workflow, n8n_update_partial_workflow, n8n_validate_workflow (by ID), n8n_list_workflows, n8n_get_workflow, n8n_test_workflow, n8n_executions, n8n_deploy_template
