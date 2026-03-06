# Creating Settings

Settings configure Claude Code behavior through JSON files including permissions, environment variables, hooks, and model selection.

## When to Use

- Configure tool permissions (allow/ask/deny)
- Set environment variables
- Configure hooks for automation
- Override default model
- Manage sandbox settings
- Configure plugins and MCP servers

## Settings File Locations

| Scope | Location | Who It Affects | Shared |
|-------|----------|----------------|--------|
| **Enterprise** | `managed-settings.json` (system) | All users | Yes (IT) |
| **User** | `~/.claude/settings.json` | You (all projects) | No |
| **Project** | `.claude/settings.json` | Team via git | Yes |
| **Local** | `.claude/settings.local.json` | You (this project) | No (gitignored) |

**System paths for managed settings:**
- macOS: `/Library/Application Support/ClaudeCode/`
- Linux/WSL: `/etc/claude-code/`
- Windows: `C:\Program Files\ClaudeCode\`

## Settings Precedence (Highest to Lowest)

1. Managed settings (Remote via Claude.ai console)
2. File-based managed settings (`managed-settings.json`)
3. Command line arguments
4. Local project settings (`.claude/settings.local.json`)
5. Shared project settings (`.claude/settings.json`)
6. User settings (`~/.claude/settings.json`)

## Format

### Basic Structure

```json
{
  "permissions": { /* ... */ },
  "env": { /* ... */ },
  "hooks": { /* ... */ },
  "model": "claude-sonnet-4-5-20250929",
  "outputStyle": "Explanatory"
}
```

### Complete Example

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run:*)",
      "Bash(git diff:*)",
      "Read(src/**)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Edit(*.config.js)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "WebFetch"
    ],
    "defaultMode": "acceptEdits",
    "additionalDirectories": ["../docs/"]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "API_URL": "https://api.example.com"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $FILE"
          }
        ]
      }
    ]
  },
  "model": "claude-sonnet-4-5-20250929",
  "attribution": {
    "commit": "🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <[email protected]>",
    "pr": "🤖 Generated with Claude Code"
  },
  "outputStyle": "Explanatory",
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  },
  "enableAllProjectMcpServers": true,
  "alwaysThinkingEnabled": true,
  "cleanupPeriodDays": 30
}
```

## Key Options

### Permissions

Control tool access with `allow`, `ask`, or `deny`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git diff:*)",       // Prefix matching for bash
      "Bash(npm run lint)",     // Exact command
      "Read(src/**)",           // Glob for files
      "Edit(dist/**)"
    ],
    "ask": [
      "Bash(git push:*)",       // Require confirmation
      "Edit(*.config.js)"
    ],
    "deny": [
      "WebFetch",               // Block tool entirely
      "Read(./.env)",           // Block specific file
      "Read(./secrets/**)"      // Block directory
    ]
  }
}
```

**Tool names:** `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`

**Pattern types:**
- Bash: Prefix matching (e.g., `git diff:*`)
- Files: Glob patterns (e.g., `src/**`, `.env*`)

### Environment Variables

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "API_KEY": "your-key-here",
    "NODE_ENV": "development"
  }
}
```

### Sandbox Configuration

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker", "git"],
    "allowUnsandboxedCommands": false,
    "network": {
      "allowUnixSockets": ["~/.ssh/agent-socket"],
      "allowLocalBinding": true,
      "httpProxyPort": 8080,
      "socksProxyPort": 8081
    }
  }
}
```

### Plugin Configuration

```json
{
  "enabledPlugins": {
    "formatter@marketplace": true,
    "deployer@marketplace": true,
    "analyzer@security": false
  },
  "extraKnownMarketplaces": {
    "company": {
      "source": {
        "source": "github",
        "repo": "company/claude-plugins"
      }
    }
  }
}
```

### MCP Server Auto-Approval

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["memory", "github"],
  "disabledMcpjsonServers": ["filesystem"]
}
```

### Enterprise MCP Restrictions

```json
{
  "allowedMcpServers": [
    { "serverName": "github" },
    { "serverName": "sentry" }
  ],
  "deniedMcpServers": [
    { "serverName": "filesystem" },
    { "serverUrl": "https://*.untrusted.com/*" }
  ]
}
```

### Other Settings

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "outputStyle": "Explanatory",
  "alwaysThinkingEnabled": true,
  "cleanupPeriodDays": 30,
  "attribution": {
    "commit": "🤖 Co-authored-by: Claude",
    "pr": "🤖 Generated with Claude Code"
  },
  "apiKeyHelper": "/bin/generate_api_key.sh",
  "forceLoginMethod": "claudeai",
  "forceLoginOrgUUID": "xxxxxxxx-xxxx-..."
}
```

## Best Practices

1. **Use appropriate scope**
   - User: Personal preferences
   - Project: Team-shared configuration
   - Local: Machine-specific settings
   - Enterprise: Security policies

2. **Protect sensitive files**
```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./config/credentials.json)"
    ]
  }
}
```

3. **Enable sandbox for security**
```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  }
}
```

4. **Version control project settings**
   - Commit `.claude/settings.json` (shared)
   - Ignore `.claude/settings.local.json` (personal)

5. **Use environment variables for secrets**
   - Never commit API keys in settings
   - Use env vars or apiKeyHelper

## Configuration Scopes Use Cases

| Use Case | Recommended Scope |
|----------|-------------------|
| Personal preferences | User (`~/.claude/settings.json`) |
| Team tools/plugins | Project (`.claude/settings.json`) |
| Testing configurations | Local (`.claude/settings.local.json`) |
| Security policies | Enterprise (`managed-settings.json`) |
| Machine-specific | Local (`.claude/settings.local.json`) |

## Example: Safe Project Settings

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run:*)",
      "Bash(git diff:*)",
      "Bash(git status:*)",
      "Read(src/**)",
      "Read(tests/**)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Edit(package.json)",
      "Edit(tsconfig.json)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "env": {
    "NODE_ENV": "development"
  },
  "outputStyle": "default"
}
```

## Example: Development vs Production

**Development (`.claude/settings.local.json`):**
```json
{
  "permissions": {
    "defaultMode": "acceptEdits"
  },
  "env": {
    "API_URL": "http://localhost:3000"
  }
}
```

**Production (`.claude/settings.json`):**
```json
{
  "permissions": {
    "deny": [
      "Bash(rm:*)",
      "Bash(sudo:*)"
    ]
  },
  "env": {
    "API_URL": "https://api.production.com"
  }
}
```

---

Last updated: 2025-12-21
