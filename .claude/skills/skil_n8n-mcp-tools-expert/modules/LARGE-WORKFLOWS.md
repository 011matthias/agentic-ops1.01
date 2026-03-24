# Handling Large n8n Workflows

Rules for avoiding tool output limits when working with n8n workflows via MCP.

## Default Mode: `structure` (NOT `full`)

When calling `n8n_get_workflow`, **always use `mode: 'structure'`** unless you have a specific reason for more data. The `full` mode (default) returns complete workflow JSON including pinned data, which regularly exceeds 1MB on complex workflows and triggers output truncation.

```
n8n_get_workflow({ id: "wf-123", mode: "structure" })   # DO THIS
n8n_get_workflow({ id: "wf-123" })                       # DON'T — defaults to full
```

## Mode Selection Guide

| Mode | Use When |
|------|----------|
| `minimal` | Checking if workflow exists, is active, or listing workflows |
| `structure` | **Default choice.** Understanding topology, verifying connections, planning modifications |
| `details` | Need execution stats or metadata beyond structure |
| `full` | Only when user explicitly requests complete JSON, or for backup/export |

## When Full Data IS Needed

If the response exceeds the output limit, it gets saved to a temp file. Handle it:

1. **Extract specific nodes** — use Bash with jq:
   ```bash
   cat /path/to/saved-file.txt | jq '.[0].text' | jq 'fromjson' | jq '.nodes[] | select(.name == "NodeName")'
   ```

2. **Read in chunks** — use the Read tool with offset/limit parameters

3. **Search for content** — use Grep to find specific node configs or expressions

## For Modifications: Use Partial Updates

Never read the full workflow just to modify it. Use `n8n_update_partial_workflow` with diff operations:

```
n8n_update_partial_workflow({
  id: "wf-123",
  operations: [
    { type: "updateNode", nodeId: "node-id", changes: { ... } },
    { type: "addConnection", source: "a", target: "b", sourcePort: "main", targetPort: "main" }
  ]
})
```

Then verify with `n8n_get_workflow({ id: "wf-123", mode: "structure" })`.
