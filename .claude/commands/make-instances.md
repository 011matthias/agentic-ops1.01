---
description: Manage per-client Make.com instance tracking
argument-hint: [list | add <client-name> | remove <client-name>]
---

Manage per-client Make.com instance tracking in `infrastructure.yaml`.

## What this does

Each client using Make.com gets an entry in their `infrastructure.yaml` file tracking the organization URL and team details. For clients on paid Make.com plans with API/MCP access, this also informs the MCP server configuration in `.mcp.json`.

## Instructions

Handle the user's request:

### List instances

Scan all `workspace/clients/*/infrastructure.yaml` files for entries with `type: make`. Show results in a table:

| Client | Instance Name | Org URL | Team |
|--------|--------------|---------|------|

If no Make.com instances are found, report that.

### Add a client instance

When adding Make.com tracking for a client (argument: `$ARGUMENTS`):

1. Determine the client name (should match a folder in `workspace/clients/`)
2. Ask the user for:
   - **Make.com organization URL** (e.g., `https://www.make.com/en/organizations/12345`)
   - **Team name** (if applicable, otherwise leave empty)
3. Create or update `workspace/clients/$ARGUMENTS/infrastructure.yaml`:

```yaml
instances:
  - type: make
    name: make-{client-name}
    org_url: {provided-url}
    team: {provided-team}
```

If `infrastructure.yaml` already exists with other entries (e.g., n8n), append the Make.com entry to the existing `instances` list. Do not overwrite existing entries.

### Remove a client instance

When removing (argument: `$ARGUMENTS`):

1. Remove the `type: make` entry from `workspace/clients/$ARGUMENTS/infrastructure.yaml`
2. If no entries remain, inform the user (don't delete the file)

### Add MCP server entry (if API access available)

If the client has a Make.com paid plan with API/MCP access:

1. Ask for the **MCP Token** (from Make.com Profile → API/MCP access)
2. Ask for the **Make.com zone** (e.g., `eu2.make.com`, `us1.make.com`)
3. Add entry to `.mcp.json` (create file if it doesn't exist):

```json
{
  "mcpServers": {
    "make-{client-name}": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<MAKE_ZONE>/mcp/u/<MCP_TOKEN>/sse"]
    }
  }
}
```

4. Tell the user to restart Claude Code for the new MCP server to take effect.

## Important

- Make.com instances are tracked in `infrastructure.yaml` for **detection and documentation**
- For clients with API/MCP access, also configure the MCP server entry in `.mcp.json`
- After adding MCP server entries, the user must **restart Claude Code**
- No credentials stored in `infrastructure.yaml` -- auth is via MCP token in `.mcp.json` or Make.com Connections UI
- **Detection**: the build skill checks `infrastructure.yaml` for `type: make` entries to identify Make.com clients
- Client instance names follow the pattern `make-{client-name}` matching `workspace/clients/` folder names
