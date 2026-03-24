# Creating Agents

Agents (subagents) are specialists that run in isolated context for parallel work.

Last updated: 2025-12-21

## When to Create an Agent

- Work should happen in parallel
- Needs isolated context (won't pollute main conversation)
- Specialist that can be delegated to
- Deep research or analysis tasks

## File Locations

| Scope | Location | Priority |
|-------|----------|----------|
| Project | `.claude/agents/` | Higher |
| Personal | `~/.claude/agents/` | Lower |

## Structure

Single markdown file:
```
.claude/agents/agent-name.md
```

## Agent File Format

### YAML Frontmatter

```yaml
---
name: agent-name
description: What this agent specializes in. Use proactively when [trigger conditions].
tools: Read, Edit, Bash, Grep, Glob
model: inherit
permissionMode: default
skills: skill1, skill2
---
```

**Fields:**

| Field | Required | Options | Description |
|-------|----------|---------|-------------|
| `name` | Yes | lowercase with hyphens | Unique identifier |
| `description` | Yes | text | Purpose + when to use (include "proactively" for auto-delegation) |
| `tools` | No | comma-separated | Available tools (inherits all if omitted) |
| `model` | No | `inherit`, `sonnet`, `opus`, `haiku` | Model to use |
| `permissionMode` | No | `default`, `acceptEdits`, `bypassPermissions`, `plan`, `ignore` | How to handle permissions |
| `skills` | No | comma-separated | Skills to auto-load on startup |

### Markdown Body

The body contains the agent's system prompt:

```markdown
---
name: researcher
description: Deep research specialist. Use proactively for research tasks requiring isolated context.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: inherit
---

You are a research specialist focused on thorough investigation.

## Your Role

- Conduct deep research on topics
- Explore codebases and documentation
- Synthesize findings into actionable insights

## Process

1. Understand the research question
2. Search broadly, then narrow down
3. Cross-reference multiple sources
4. Summarize key findings

## Output Format

Provide:
- Executive summary (2-3 sentences)
- Key findings (bulleted list)
- Recommendations (if applicable)
- Sources consulted
```

## Tool Access

### Common Tool Sets

**Read-only research:**
```yaml
tools: Read, Grep, Glob
```

**Research with web access:**
```yaml
tools: Read, Grep, Glob, WebFetch, WebSearch
```

**Full access:**
```yaml
tools: Read, Edit, Bash, Grep, Glob
```

### Model Selection

- `inherit` - Same as parent conversation
- `haiku` - Fast, lightweight tasks
- `sonnet` - Balanced (default for most)
- `opus` - Complex reasoning

## Built-in Agents

Claude Code includes these built-in agents:

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| `general-purpose` | Sonnet | All | Complex multi-step tasks |
| `plan` | Sonnet | Read, Glob, Grep, Bash | Codebase research in plan mode |
| `explore` | Haiku | Read-only | Fast codebase searching |

## Management

### Using `/agents` Command

```
/agents
```

Interactive interface to:
- View all agents (built-in, user, project)
- Create new agents
- Edit existing agents
- Delete custom agents
- Manage tool permissions

### CLI Configuration

Define agents dynamically with `--agents` flag:

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

## Resumable Agents

Agents can be resumed to continue previous conversations:

- Each execution gets a unique `agentId`
- Transcript stored in: `agent-{agentId}.jsonl`
- Resume with: `resume: "abc123"` parameter

**Use cases:**
- Long-running research
- Iterative refinement
- Multi-step workflows

## Best Practices

### 1. Single Responsibility

One agent = one specialty:
- `researcher` - Deep research
- `doc-updater` - Documentation updates
- `lead-specialist` - Lead qualification

### 2. Include Trigger Conditions

Use "proactively" in description for auto-delegation:
```yaml
description: Review code quality. Use proactively after code changes.
```

### 3. Limit Tool Access

Principle of least privilege:
```yaml
# Read-only agent
tools: Read, Grep, Glob

# Not this:
tools: Read, Edit, Bash, Grep, Glob, Write
```

### 4. Define Clear Process

Include step-by-step process in the body:
```markdown
## Process

1. First, do X
2. Then, do Y
3. Finally, output Z
```

### 5. Specify Output Format

Be explicit about expected output:
```markdown
## Output Format

Return a JSON object with:
- summary: string
- findings: array
- confidence: number
```

## Template

Use [agent-template.md](../templates/agent-template.md) to create new agents.
