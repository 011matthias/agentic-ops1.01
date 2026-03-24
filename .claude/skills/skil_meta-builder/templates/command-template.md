# Command Template

Copy this template to create a new slash command.

## File Location

```
.claude/commands/[command-name].md
```

## Basic Template

```yaml
---
description: [Brief description - appears in command list]
---

[Instructions for Claude to execute]

## Data Sources

- [file/folder to read]
- [another source]

## Process

1. [Step 1]
2. [Step 2]

## Output

[Where to save results or how to present them]
```

## Template with Arguments

```yaml
---
description: [Description with argument context]
argument-hint: [arg1] [arg2]
---

Process $1 with format $2.

Or use all arguments: $ARGUMENTS
```

## Template with Tool Restrictions

```yaml
---
description: [Read-only operation description]
allowed-tools: Read, Grep, Glob
---

[Instructions - only allowed tools will be available]
```

## Examples

### Daily Routine Command

```yaml
---
description: Generate daily brief with TOP 2 priorities and quick win
---

Read the following files:
- workspace/foundations/tasks.md
- workspace/foundations/gains.md
- workspace/foundations/daily-brief.md

Generate a daily brief with:
1. TOP 2 priority tasks for today
2. Quick win (10-15 min revenue activity)
3. Context section

Output to: workspace/foundations/daily-brief.md
```

### Search Command

```yaml
---
description: Search codebase for a term
argument-hint: [search-term]
allowed-tools: Grep, Glob, Read
---

Search the codebase for: $ARGUMENTS

Report:
- Files containing the term
- Relevant code snippets
- Suggested next steps
```

## Checklist

Before finalizing:

- [ ] Description is clear and concise
- [ ] Instructions are unambiguous
- [ ] Output location is specified (if applicable)
- [ ] Arguments are documented (if used)
- [ ] Tool restrictions are appropriate (if needed)
