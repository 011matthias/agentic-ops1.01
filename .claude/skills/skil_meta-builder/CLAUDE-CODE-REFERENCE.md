# Claude Code Official Reference

Last updated: 2025-12-21

This document is an index of all Claude Code primitives. Use the doc-updater agent to refresh content from official documentation.

---

## Quick Reference: All 9 Primitives

| Primitive | Type | Location | Trigger | Guide |
|-----------|------|----------|---------|-------|
| **Skills** | Auto-invoked | `.claude/skills/` | Automatic (context) | [SKILL-GUIDE](modules/SKILL-GUIDE.md) |
| **Commands** | User-invoked | `.claude/commands/` | `/command` | [COMMAND-GUIDE](modules/COMMAND-GUIDE.md) |
| **Agents** | Specialist | `.claude/agents/` | Auto or explicit | [AGENT-GUIDE](modules/AGENT-GUIDE.md) |
| **Memory** | Configuration | `CLAUDE.md`, `.claude/rules/` | Automatic load | [MEMORY-GUIDE](modules/MEMORY-GUIDE.md) |
| **Settings** | Configuration | `.claude/settings.json` | Automatic load | [SETTINGS-GUIDE](modules/SETTINGS-GUIDE.md) |
| **Hooks** | Event-driven | `settings.json` | Lifecycle events | [HOOKS-GUIDE](modules/HOOKS-GUIDE.md) |
| **MCP Servers** | Integration | `.mcp.json` | Tool access | [MCP-GUIDE](modules/MCP-GUIDE.md) |
| **Output Styles** | Configuration | `.claude/output-styles/` | `/output-style` | [OUTPUT-STYLES-GUIDE](modules/OUTPUT-STYLES-GUIDE.md) |
| **Plugins** | Distribution | `.claude-plugin/` | Install/enable | [PLUGINS-GUIDE](modules/PLUGINS-GUIDE.md) |

---

## Decision Helper

See [DECISION-TREE.md](modules/DECISION-TREE.md) for choosing the right primitive.

**Quick decision:**
- Need auto-discovery based on context? → **Skill**
- User triggers explicitly with `/`? → **Command**
- Needs isolated context / parallel work? → **Agent**
- Project instructions / rules? → **Memory**
- Permissions / environment config? → **Settings**
- React to tool calls / events? → **Hooks**
- External tool integration? → **MCP Server**
- Change Claude's communication style? → **Output Style**
- Distribute capabilities as package? → **Plugin**

---

## Primitive Categories

### Core Primitives (Capabilities)

| Primitive | What | When | Complexity |
|-----------|------|------|------------|
| Skills | Multi-file workflows | Complex, reusable capabilities | Multi-file |
| Commands | Prompt shortcuts | Quick actions, routines | Single file |
| Agents | Specialists | Parallel work, isolation needed | Single file |

### Configuration Primitives

| Primitive | What | Scope |
|-----------|------|-------|
| Memory | Instructions (CLAUDE.md, rules/) | Project / User / Enterprise |
| Settings | JSON config (permissions, env, hooks) | Project / User / Enterprise |
| Output Styles | System prompt variants | Project / User |

### Integration Primitives

| Primitive | What | Purpose |
|-----------|------|---------|
| Hooks | Event handlers (bash/prompt) | Automation, validation |
| MCP Servers | External tools (HTTP/stdio) | Extend capabilities |
| Plugins | Distributable packages | Share capabilities |

---

## File Locations Summary

```
~/.claude/                      # User level
├── CLAUDE.md                   # User memory
├── settings.json               # User settings
├── rules/                      # User rules
├── skills/                     # User skills
├── commands/                   # User commands
├── agents/                     # User agents
└── output-styles/              # User output styles

.claude/                        # Project level
├── CLAUDE.md                   # Project memory
├── settings.json               # Project settings (shared)
├── settings.local.json         # Project settings (personal)
├── rules/                      # Project rules (path-specific)
├── skills/                     # Project skills
├── commands/                   # Project commands
├── agents/                     # Project agents
└── output-styles/              # Project output styles

.mcp.json                       # Project MCP servers
.claude-plugin/                 # Plugin manifest
  └── plugin.json
```

---

## Key Concepts

### Memory Hierarchy
1. **Enterprise** - Organization-wide (managed)
2. **Project** - Team shared (git)
3. **Project Rules** - Path-specific rules
4. **User** - Personal (all projects)
5. **Local** - Personal (this project only, gitignored)

### Settings Precedence
1. Managed settings (remote/enterprise)
2. Command line arguments
3. Local project settings
4. Shared project settings
5. User settings

### Hook Events
- **PreToolUse** - Before tool execution (can block)
- **PermissionRequest** - Permission dialogs (can override)
- **PostToolUse** - After tool completion (monitoring)
- **UserPromptSubmit** - Before prompt processing (can add context)
- **Stop/SubagentStop** - Task completion (can continue)
- **SessionStart/SessionEnd** - Session lifecycle
- **Notification** - Notification events
- **PreCompact** - Before compacting

### MCP Server Types
- **HTTP** - Cloud-based services (recommended)
- **SSE** - Server-Sent Events (deprecated)
- **Stdio** - Local processes

### Plugin Components
- Commands (slash commands)
- Agents (subagents)
- Skills (capabilities)
- Hooks (event handlers)
- MCP Servers (external tools)
- LSP Servers (code intelligence)

---

## Common Patterns

### Hybrid: Skill + Command
Complex workflow with optional explicit trigger:
```
.claude/skills/lead-generation/  → Auto-discovered capability
.claude/commands/leads.md         → Explicit trigger (optional)
```

### Hybrid: Agent + Skill
Specialist using specific capabilities:
```
.claude/skills/lead-generation/  → The capability
.claude/agents/lead-specialist.md → Specialist using it
```

### Configuration Stack
Project configuration:
```
CLAUDE.md                        → Instructions and context
.claude/rules/                   → Path-specific rules
.claude/settings.json            → Permissions and env vars
.mcp.json                        → External integrations
```

### Plugin Distribution
Complete solution packaging:
```
.claude-plugin/plugin.json       → Manifest
commands/                        → Slash commands
agents/                          → Subagents
skills/                          → Skills
hooks/hooks.json                 → Event handlers
.mcp.json                        → MCP servers
```

---

## Quick Reference by Use Case

| I want to... | Use | Guide |
|--------------|-----|-------|
| Add complex workflow | **Skill** | [SKILL-GUIDE](modules/SKILL-GUIDE.md) |
| Create quick command | **Command** | [COMMAND-GUIDE](modules/COMMAND-GUIDE.md) |
| Run parallel research | **Agent** | [AGENT-GUIDE](modules/AGENT-GUIDE.md) |
| Store project rules | **Memory** | [MEMORY-GUIDE](modules/MEMORY-GUIDE.md) |
| Configure permissions | **Settings** | [SETTINGS-GUIDE](modules/SETTINGS-GUIDE.md) |
| Auto-format on save | **Hooks** | [HOOKS-GUIDE](modules/HOOKS-GUIDE.md) |
| Integrate GitHub | **MCP Server** | [MCP-GUIDE](modules/MCP-GUIDE.md) |
| Enable verbose mode | **Output Style** | [OUTPUT-STYLES-GUIDE](modules/OUTPUT-STYLES-GUIDE.md) |
| Share with team | **Plugin** | [PLUGINS-GUIDE](modules/PLUGINS-GUIDE.md) |

---

## Sources

All documentation fetched from official Claude Code documentation:

- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/slash-commands
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/hooks-guide
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/output-styles
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/plugins-reference
