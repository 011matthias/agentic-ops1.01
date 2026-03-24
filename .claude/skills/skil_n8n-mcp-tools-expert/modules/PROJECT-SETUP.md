# n8n Workflow Building with n8n-mcp

Instructions for building and managing n8n workflows using n8n-mcp tools.

## Core Principles

### 1. Silent Execution
Execute tools without commentary. Only respond AFTER all tools complete.

### 2. Parallel Execution
When operations are independent, execute them in parallel.

### 3. Templates First
ALWAYS check templates before building from scratch (2,709+ available).

### 4. Multi-Level Validation
Use `validate_node(mode='minimal')` → `validate_node(mode='full')` → `validate_workflow` pattern.

### 5. Never Trust Defaults
Default parameter values are the #1 source of runtime failures. ALWAYS explicitly configure ALL parameters that control node behavior.

## Workflow Process

### 1. Template Discovery (do this FIRST)

```
search_templates({searchMode: 'by_metadata', complexity: 'simple'})
search_templates({searchMode: 'by_task', task: 'webhook_processing'})
search_templates({query: 'slack notification'})
search_templates({searchMode: 'by_nodes', nodeTypes: ['n8n-nodes-base.slack']})
```

**Filtering strategies:**
- Beginners: `complexity: "simple"` + `maxSetupMinutes: 30`
- By role: `targetAudience: "marketers"` | `"developers"` | `"analysts"`
- By time: `maxSetupMinutes: 15` for quick wins
- By service: `requiredService: "openai"` for compatibility

### 2. Node Discovery (if no suitable template)

```
search_nodes({query: 'keyword', includeExamples: true})
search_nodes({query: 'trigger'})
search_nodes({query: 'AI agent langchain'})
```

### 3. Configuration Phase

```
get_node({nodeType, detail: 'standard', includeExamples: true})  # Default
get_node({nodeType, detail: 'minimal'})   # Basic metadata (~200 tokens)
get_node({nodeType, detail: 'full'})       # Complete info (~3000-8000 tokens)
get_node({nodeType, mode: 'search_properties', propertyQuery: 'auth'})
get_node({nodeType, mode: 'docs'})         # Human-readable markdown
```

Show workflow architecture to user for approval before proceeding.

### 4. Validation Phase

```
validate_node({nodeType, config, mode: 'minimal'})                    # Quick required fields
validate_node({nodeType, config, mode: 'full', profile: 'runtime'})   # Full validation
```

Fix ALL errors before proceeding.

### 5. Building Phase

- If using template: `get_template(templateId, {mode: "full"})`
- **MANDATORY ATTRIBUTION**: "Based on template by **[author.name]** (@[username]). View at: [url]"
- Explicitly set ALL parameters — never rely on defaults
- Connect nodes with proper structure
- Add error handling
- Use n8n expressions: `$json`, `$node["NodeName"].json`

### 6. Workflow Validation (before deployment)

```
validate_workflow(workflow)                    # Complete validation
validate_workflow_connections(workflow)        # Structure check
validate_workflow_expressions(workflow)       # Expression validation
```

### 7. Deployment (if n8n API configured)

```
n8n_create_workflow(workflow)                 # Deploy
n8n_validate_workflow({id})                   # Post-deployment check
n8n_update_partial_workflow({id, operations}) # Batch updates
n8n_test_workflow({workflowId})              # Test execution
```

## Validation Strategy (4 Levels)

| Level | When | Tool |
|-------|------|------|
| 1 - Quick Check | Before building | `validate_node({mode: 'minimal'})` |
| 2 - Comprehensive | Before building | `validate_node({mode: 'full', profile: 'runtime'})` |
| 3 - Complete | After building | `validate_workflow(workflow)` |
| 4 - Post-Deploy | After deployment | `n8n_validate_workflow({id})` + `n8n_autofix_workflow({id})` |

## Critical Warnings

### Never Trust Defaults

```json
// FAILS at runtime
{"resource": "message", "operation": "post", "text": "Hello"}

// WORKS — all parameters explicit
{"resource": "message", "operation": "post", "select": "channel", "channelId": "C123", "text": "Hello"}
```

### addConnection Syntax

The `addConnection` operation requires **four separate string parameters**:

```json
// CORRECT
{
  "type": "addConnection",
  "source": "node-id-string",
  "target": "target-node-id-string",
  "sourcePort": "main",
  "targetPort": "main"
}
```

Do NOT use object format or combined strings — they fail silently.

### IF Node Multi-Output Routing

IF nodes have two outputs (TRUE and FALSE). Use the `branch` parameter:

```json
// Route to TRUE branch
{"type": "addConnection", "source": "if-node", "target": "success", "sourcePort": "main", "targetPort": "main", "branch": "true"}

// Route to FALSE branch
{"type": "addConnection", "source": "if-node", "target": "failure", "sourcePort": "main", "targetPort": "main", "branch": "false"}
```

## Batch Operations

Use `n8n_update_partial_workflow` with multiple operations in a single call:

```json
n8n_update_partial_workflow({
  id: "wf-123",
  operations: [
    {"type": "updateNode", "nodeId": "slack-1", "changes": {}},
    {"type": "updateNode", "nodeId": "http-1", "changes": {}},
    {"type": "cleanStaleConnections"}
  ]
})
```

Never make separate calls for each operation.
