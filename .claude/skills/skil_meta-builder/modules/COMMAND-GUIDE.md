# Creating Slash Commands

Slash commands are user-invoked prompts triggered explicitly with `/command`.

Last updated: 2025-12-21

## When to Create a Command

- User wants explicit control over timing
- Quick, focused actions
- Daily routines
- Simple prompts that don't need auto-discovery

## File Locations

| Scope | Location | Priority |
|-------|----------|----------|
| Project | `.claude/commands/` | Higher (overrides user) |
| Personal | `~/.claude/commands/` | Lower |

## Structure

Single markdown file:
```
.claude/commands/command-name.md
```

### Namespacing with Subdirectories

Organize commands in subdirectories:
```
.claude/commands/frontend/component.md  → /component (project:frontend)
.claude/commands/backend/test.md        → /test (project:backend)
```

## Command File Format

### YAML Frontmatter

```yaml
---
description: Brief description of what the command does
argument-hint: [file-path] [format]
allowed-tools: Read, Grep, Glob
model: claude-3-5-haiku-20241022
disable-model-invocation: false
---
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Brief description (shown in command list) |
| `argument-hint` | No | Expected arguments for auto-completion |
| `allowed-tools` | No | Restrict available tools |
| `model` | No | Specific model to use (inherits if omitted) |
| `disable-model-invocation` | No | Prevent SlashCommand tool from calling this |

### Markdown Body

The body contains the prompt that executes when the command is invoked.

```markdown
---
description: Generate daily brief with TOP 2 priorities
---

Read the following files:
- workspace/foundations/tasks.md
- workspace/foundations/gains.md
- workspace/foundations/daily-brief.md (yesterday's)

Generate a daily brief following the format in directives/daily-ops/morning-brief.md

Output to: workspace/foundations/daily-brief.md
```

## Arguments

### Using $ARGUMENTS

All arguments as one string:
```markdown
---
description: Search for a term in the codebase
argument-hint: [search-term]
---

Search the codebase for: $ARGUMENTS
```

Usage: `/search TODO items`

### Using Positional Arguments

Individual arguments:
```markdown
---
description: Create a new file with content
argument-hint: [file-path] [content-type]
---

Create a new $2 file at $1
```

Usage: `/create src/utils.ts typescript`

## Tool Restrictions

Limit available tools:
```yaml
---
description: Read-only code review
allowed-tools: Read, Grep, Glob
---
```

## Dynamic Content

### Bash Command Execution (`!` prefix)

Execute bash commands inline using `!` prefix:

```markdown
---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
description: Create a git commit
---

## Context

- Current git status: !`git status`
- Current diff: !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes, create a single git commit.
```

### File References (`@` prefix)

Include file contents using `@` prefix:

```markdown
Review the implementation in @src/utils/helpers.js

Compare @src/old-version.js with @src/new-version.js
```

## MCP Slash Commands

Commands from MCP servers follow this format:

```
/mcp__<server-name>__<prompt-name> [arguments]
```

**Examples:**
```bash
/mcp__github__list_prs
/mcp__github__pr_review 456
/mcp__jira__create_issue "Bug title" high
```

## SlashCommand Tool

Claude can execute custom commands programmatically via the SlashCommand tool.

**Requirements:**
- Custom user-defined commands only (not built-in)
- Must have `description` frontmatter field

**Permission rules:**
```yaml
SlashCommand:/commit           # Exact match, no arguments
SlashCommand:/review-pr:*      # Prefix match, any arguments
```

**Disable for specific command:**
```yaml
---
description: Sensitive operation
disable-model-invocation: true
---
```

## Best Practices

### 1. Keep Commands Focused

One command = one action:
- `/morning` - Daily brief
- `/eod` - End of day review
- `/commit` - Git commit

### 2. Clear Descriptions

Description appears in command list:
```yaml
description: Generate daily brief with TOP 2 priorities and quick win
```

### 3. Reference Existing Instructions

Don't duplicate, reference:
```markdown
Follow the process in directives/daily-ops/morning-brief.md
```

### 4. Specify Output Location

Be explicit about where results go:
```markdown
Output to: workspace/foundations/daily-brief.md
```

## Template

Use [command-template.md](../templates/command-template.md) to create new commands.
