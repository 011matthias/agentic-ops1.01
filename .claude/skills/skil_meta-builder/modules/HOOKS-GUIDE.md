# Creating Hooks

Hooks are automated scripts that run in response to specific events in Claude Code's lifecycle.

## When to Use

- Automate code formatting after edits
- Log all executed commands for compliance
- Validate code before commits
- Send notifications on completion
- Block modifications to sensitive files
- Add context before prompt processing
- Clean up after sessions end

## Hook Events

| Event | Trigger | Can Block |
|-------|---------|-----------|
| **PreToolUse** | Before tool calls | Yes |
| **PermissionRequest** | Permission dialogs | Yes |
| **PostToolUse** | After tool completes | No (monitoring) |
| **UserPromptSubmit** | User submits prompt | Yes |
| **Notification** | Notifications sent | No |
| **Stop** | Claude finishes response | Yes (continue working) |
| **SubagentStop** | Subagent completes | Yes (continue working) |
| **PreCompact** | Before compact operation | No |
| **SessionStart** | Session starts/resumes | No |
| **SessionEnd** | Session ends | No |

## Structure

Hooks are configured in settings files:

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-script.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

## Format

### Command-Based Hook

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $FILE",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Prompt-Based Hook (Stop/SubagentStop only)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete: $ARGUMENTS",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Python Script Hook

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/file-protection.py"
          }
        ]
      }
    ]
  }
}
```

## Matchers

For tool-related events (PreToolUse, PermissionRequest, PostToolUse):

| Matcher | Matches |
|---------|---------|
| `"Bash"` | Exact tool name |
| `"Edit\|Write"` | Multiple tools (regex) |
| `"Bash.*"` | Tool name pattern |
| `"*"` | All tools |
| `""` | All tools (empty) |

**Common tool names:**
- `Task` - Subagent tasks
- `Bash` - Shell commands
- `Read`, `Write`, `Edit` - File operations
- `WebFetch`, `WebSearch` - Web operations
- `Glob`, `Grep` - File utilities
- `mcp__<server>__<tool>` - MCP tools

## Hook Input (via stdin)

Hooks receive JSON via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "src/utils.ts",
    "content": "..."
  },
  "tool_use_id": "toolu_01ABC123"
}
```

**Event-specific fields:**
- **PreToolUse/PostToolUse**: `tool_name`, `tool_input`, `tool_use_id`, `tool_response`
- **UserPromptSubmit**: `prompt`
- **Stop/SubagentStop**: `stop_hook_active`
- **PreCompact**: `trigger` ("manual" or "auto"), `custom_instructions`
- **SessionStart**: `source` ("startup", "resume", "clear", "compact")
- **SessionEnd**: `reason` ("clear", "logout", "prompt_input_exit", "other")

## Hook Output

### Exit Codes

| Code | Behavior |
|------|----------|
| **0** | Success. Parse `stdout` for JSON control |
| **2** | Blocking error. Use `stderr` as error message |
| **Other** | Non-blocking error. Show `stderr` in verbose |

### JSON Output (Exit Code 0)

```json
{
  "decision": "block" | "approve" | "allow" | "deny",
  "reason": "Explanation",
  "continue": true,
  "stopReason": "Message for user",
  "suppressOutput": true,
  "systemMessage": "Warning or context",
  "hookSpecificOutput": { /* ... */ }
}
```

### Hook-Specific Output

**PreToolUse:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask",
    "permissionDecisionReason": "Why decision made",
    "updatedInput": {
      "file_path": "modified_path.ts"
    }
  }
}
```

**PermissionRequest:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow" | "deny",
      "updatedInput": { /* ... */ },
      "message": "Reason for denial",
      "interrupt": false
    }
  }
}
```

**PostToolUse:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Context to add to conversation"
  }
}
```

**UserPromptSubmit:**
```json
{
  "decision": "block",
  "reason": "Prompt blocked because...",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Extra context for Claude"
  }
}
```

## Environment Variables

Available in all hooks:
- `CLAUDE_PROJECT_DIR` - Absolute path to project root
- `CLAUDE_CODE_REMOTE` - "true" if web environment, empty if local

**SessionStart only:**
- `CLAUDE_ENV_FILE` - File path to persist env vars for bash commands

## Best Practices

1. **Validate inputs** - Always sanitize data from stdin
2. **Quote shell variables** - Use `"$VAR"` not `$VAR`
3. **Block path traversal** - Check for `..` in paths
4. **Use absolute paths** - Avoid relative path issues
5. **Set timeouts** - Prevent hanging hooks
6. **Handle errors gracefully** - Use appropriate exit codes
7. **Test thoroughly** - Hooks execute with your credentials

## Example: Code Formatting Hook

**.claude/settings.json:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/format.sh"
          }
        ]
      }
    ]
  }
}
```

**.claude/hooks/format.sh:**
```bash
#!/bin/bash
set -euo pipefail

file_path=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)

if [[ -z "$file_path" ]]; then
  exit 0
fi

# Format TypeScript files
if [[ "$file_path" =~ \.tsx?$ ]]; then
  npx prettier --write "$file_path"
  echo "✓ Formatted $file_path"
fi

exit 0
```

```bash
chmod +x .claude/hooks/format.sh
```

## Example: File Protection Hook

**.claude/hooks/file-protection.py:**
```python
#!/usr/bin/env python3
import json
import sys

# Read input
input_data = json.load(sys.stdin)
tool_input = input_data.get("tool_input", {})
file_path = tool_input.get("file_path", "")

# Protected patterns
protected = [".env", "secrets/", "credentials.json", ".git/"]

# Block if protected
if any(p in file_path for p in protected):
    print(f"Blocked modification to protected file: {file_path}", file=sys.stderr)
    sys.exit(2)  # Blocking error

sys.exit(0)  # Allow
```

**.claude/settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/file-protection.py"
          }
        ]
      }
    ]
  }
}
```

## Example: Bash Command Logging

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' >> ~/.claude/bash-log.txt"
          }
        ]
      }
    ]
  }
}
```

## Example: Desktop Notifications

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' 'Awaiting your input'"
          }
        ]
      }
    ]
  }
}
```

## Example: Add Context on Session Start

**.claude/hooks/session-context.py:**
```python
#!/usr/bin/env python3
import json
import sys
import datetime

# Output context
context = f"Session started at {datetime.datetime.now()}"
print(context)  # Added to conversation context

sys.exit(0)
```

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/session-context.py"
          }
        ]
      }
    ]
  }
}
```

## Debugging

Enable detailed logging:
```bash
claude --debug
```

Check registered hooks:
```
/hooks
```

## Security Warning

⚠️ **CRITICAL**: Hooks execute arbitrary shell commands with your credentials.

**You are responsible for:**
- Commands configured
- File access/modification
- Data loss or system damage
- Security vulnerabilities

Always validate and sanitize inputs from stdin.

---

Last updated: 2025-12-21
