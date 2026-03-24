# Creating MCP Servers

MCP (Model Context Protocol) servers connect Claude Code to external tools, databases, and APIs.

## When to Use

- Integrate with external services (GitHub, Slack, Notion)
- Access databases (PostgreSQL, MongoDB)
- Connect to APIs (Stripe, Sentry, Jira)
- Extend Claude's capabilities with custom tools
- Share tools across team

## Installation Types

| Type | Use Case | Example |
|------|----------|---------|
| **HTTP** | Cloud services | GitHub, Stripe, Notion |
| **SSE** | Server-Sent Events (deprecated) | Legacy services |
| **Stdio** | Local processes | Custom scripts, local databases |

## Installation Scopes

| Scope | File | Visibility | Use Case |
|-------|------|------------|----------|
| **Local** | `~/.claude.json` | Private (this project) | Secrets, experimental |
| **Project** | `.mcp.json` | Team via git | Shared tools |
| **User** | `~/.claude.json` | All projects | Personal utilities |
| **Enterprise** | `managed-mcp.json` | System-wide | Org policy |

**Precedence:** Local > Project > User > Enterprise

## Format

### HTTP Server

```bash
# Add HTTP server
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# With authentication header
claude mcp add --transport http stripe https://mcp.stripe.com \
  --header "Authorization: Bearer your-token"
```

### Stdio Server

```bash
# Add local stdio server
claude mcp add --transport stdio airtable \
  --env AIRTABLE_API_KEY=YOUR_KEY \
  -- npx -y airtable-mcp-server

# Custom script
claude mcp add --transport stdio custom \
  -- python3 /path/to/server.py
```

**Windows:** Use `cmd /c` wrapper:
```bash
claude mcp add --transport stdio my-server -- cmd /c npx -y @some/package
```

### Project Scope (.mcp.json)

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "database": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "--dsn", "${DB_URL}"],
      "env": {
        "DB_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

### Plugin MCP Servers

In `.mcp.json` or inline in `plugin.json`:

```json
{
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

## Environment Variable Expansion

Use `${VAR}` syntax in `.mcp.json`:

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

**Syntax:**
- `${VAR}` - Expand to environment variable
- `${VAR:-default}` - Use default if not set
- `${CLAUDE_PLUGIN_ROOT}` - Plugin directory (for plugins)

## Authentication

### OAuth 2.0 (HTTP Servers)

```bash
# 1. Add server
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp

# 2. Authenticate in Claude Code
/mcp
# Follow browser OAuth flow
```

### Bearer Token

```bash
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

### Custom Headers

```bash
claude mcp add --transport sse private-api https://api.company.com/sse \
  --header "X-API-Key: your-key"
```

## MCP Features

### Resources (@mentions)

Reference external resources:

```
@github:issue://123
@docs:file://api/authentication
@postgres:schema://users
```

### Prompts (Slash Commands)

Execute MCP-provided prompts:

```
/mcp__github__list_prs
/mcp__github__pr_review 456
/mcp__jira__create_issue "Bug title" high
```

### Tools

MCP servers provide tools that Claude can use:
- Auto-inherited if `tools` field omitted in agents
- Accessible via `/mcp` command

## Management Commands

```bash
# List all servers
claude mcp list

# Get server details
claude mcp get github

# Remove server
claude mcp remove github

# Reset project approval choices
claude mcp reset-project-choices

# Import from Claude Desktop
claude mcp add-from-claude-desktop

# Add from JSON
claude mcp add-json github '{"type":"http","url":"..."}'

# Serve Claude Code as MCP server
claude mcp serve
```

## Configuration & Settings

### Auto-Approval

In `.claude/settings.json`:

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["memory", "github"],
  "disabledMcpjsonServers": ["filesystem"]
}
```

### Environment Variables

```bash
# Set startup timeout (milliseconds)
MCP_TIMEOUT=10000 claude

# Increase output token limit (default: 25,000)
MAX_MCP_OUTPUT_TOKENS=50000 claude
```

## Enterprise MCP Configuration

### Option 1: Exclusive Control (managed-mcp.json)

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "company-internal": {
      "type": "stdio",
      "command": "/usr/local/bin/company-mcp-server",
      "args": ["--config", "/etc/company/mcp-config.json"],
      "env": {
        "COMPANY_API_URL": "https://internal.company.com"
      }
    }
  }
}
```

### Option 2: Policy-Based (Allowlists/Denylists)

In `managed-settings.json`:

```json
{
  "allowedMcpServers": [
    { "serverName": "github" },
    { "serverName": "sentry" },
    { "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem"] },
    { "serverUrl": "https://mcp.company.com/*" }
  ],
  "deniedMcpServers": [
    { "serverName": "dangerous-server" },
    { "serverUrl": "https://*.untrusted.com/*" }
  ]
}
```

**Restriction types:**
- `serverName` - Match configured name
- `serverCommand` - Match exact command array (stdio only)
- `serverUrl` - Match URL with wildcards

**Denylist takes precedence.**

## Best Practices

1. **Use appropriate scope**
   - Local: API keys, credentials
   - Project: Shared team tools
   - User: Personal utilities
   - Enterprise: Organization policy

2. **Secure credentials**
   - Use environment variables
   - Never commit keys in `.mcp.json`
   - Use OAuth when available

3. **Test before sharing**
```bash
# Test locally first
claude mcp add --transport stdio test -- python3 server.py

# Then add to project
# Add to .mcp.json manually
```

4. **Document server purpose**
```json
{
  "mcpServers": {
    "// github": "GitHub API access for PR reviews",
    "github": { /* ... */ }
  }
}
```

5. **Set reasonable timeouts**
```bash
MCP_TIMEOUT=30000 claude  # 30 seconds
```

## Examples

### GitHub Integration

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
/mcp  # Authenticate

# Usage:
/mcp__github__list_prs
/mcp__github__pr_review 456
```

### PostgreSQL Database

```bash
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub \
  --dsn "postgresql://readonly:[email protected]:5432/analytics"

# Usage:
"What's the total revenue this month?"
"Find inactive users"
```

### Sentry Error Monitoring

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
/mcp  # Authenticate

# Usage:
"Show errors from last 24 hours"
"Stack trace for error ID abc123"
```

### Custom Local Server

**server.py:**
```python
#!/usr/bin/env python3
# Custom MCP server implementation
# See: https://modelcontextprotocol.io/
```

```bash
claude mcp add --transport stdio custom \
  --env API_KEY=your-key \
  -- python3 /path/to/server.py
```

## Debugging

```bash
# Debug mode
claude --debug

# Check MCP status
/mcp

# View logs
# Logs are shown in debug output
```

## Project Configuration Example

**.mcp.json:**
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "analytics": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "--dsn", "${ANALYTICS_DB}"],
      "env": {
        "ANALYTICS_DB": "${DATABASE_URL}"
      }
    }
  }
}
```

**.claude/settings.json:**
```json
{
  "enableAllProjectMcpServers": true
}
```

---

Last updated: 2025-12-21
