---
description: Manage per-client n8n MCP server instances
argument-hint: [list | add <client-name> | remove <client-name>]
---

Manage per-client n8n MCP server instances in `.mcp.json`.

## What this does

Each client with an n8n instance gets their own named MCP server entry in `.mcp.json`. This gives you dedicated n8n-mcp tools namespaced per client (e.g., `mcp__n8n_herbox__n8n_create_workflow`).

## Instructions

Read `.mcp.json` from the project root. Then handle the user's request:

### List instances

Show all `n8n-*` entries from `.mcp.json` in a table:

| Instance | Has API URL | Has API Key |
|----------|-------------|-------------|

The base `n8n-mcp` entry (docs-only, no credentials) should be labeled as such.

### Add a client instance

When adding a new client (argument: `$ARGUMENTS`):

1. Determine the client name (should match a folder in `workspace/clients/`)
2. The MCP server entry name should be `n8n-{client-name}` (e.g., `n8n-herbox`)
3. Ask the user for:
   - `N8N_API_URL` - The client's n8n instance URL (e.g., `https://herbox.app.n8n.cloud/api/v1`)
   - `N8N_API_KEY` - The client's n8n API key
4. Add the entry to `.mcp.json`:

```json
"n8n-{client-name}": {
  "command": "npx",
  "args": ["n8n-mcp"],
  "env": {
    "MCP_MODE": "stdio",
    "LOG_LEVEL": "error",
    "DISABLE_CONSOLE_OUTPUT": "true",
    "N8N_API_URL": "{provided-url}",
    "N8N_API_KEY": "{provided-key}"
  }
}
```

5. Tell the user to restart Claude Code for the new MCP server to take effect.

### Remove a client instance

When removing (argument: `$ARGUMENTS`):

1. Remove the `n8n-{client-name}` entry from `.mcp.json`
2. Never remove the base `n8n-mcp` docs-only instance
3. Tell the user to restart Claude Code for changes to take effect.

## Important

- The base `n8n-mcp` instance (docs-only, no API credentials) should never be removed
- Client instance names follow the pattern `n8n-{client-name}` matching `workspace/clients/` folder names
- After adding/removing instances, the user must restart Claude Code for changes to take effect
- API credentials are stored directly in `.mcp.json` — ensure this file is in `.gitignore`
