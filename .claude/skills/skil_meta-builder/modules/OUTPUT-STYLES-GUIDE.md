# Creating Output Styles

Output Styles adapt Claude Code's communication style by modifying the system prompt.

## When to Use

- Change verbosity (concise vs explanatory)
- Enable learning mode with educational insights
- Adapt for non-coding use cases
- Create domain-specific communication styles
- Customize Claude's behavior patterns

## Built-in Styles

| Style | Description |
|-------|-------------|
| **Default** | Efficient software engineering (concise, action-focused) |
| **Explanatory** | Educational insights between tasks |
| **Learning** | Collaborative learn-by-doing with `TODO(human)` markers |

## Structure

Custom output styles are stored as Markdown files:

```
~/.claude/output-styles/          # User level (all projects)
.claude/output-styles/            # Project level (team)
```

File naming:
- `my-style.md` - Filename becomes style name
- Or use `name` in frontmatter

## Format

### Basic Structure

```markdown
---
name: My Custom Style
description: Brief description shown in /output-style UI
keep-coding-instructions: false
---

# Custom Style Instructions

You are an interactive CLI tool that helps users with software engineering tasks.

[Your custom instructions here...]

## Specific Behaviors

- [Define how assistant should behave]
- [Communication patterns]
- [Output format preferences]
```

### Frontmatter Fields

| Field | Required | Default | Purpose |
|-------|----------|---------|---------|
| `name` | No | Filename | Style name shown in UI |
| `description` | No | None | Brief description for `/output-style` menu |
| `keep-coding-instructions` | No | `false` | Retain Claude Code's coding system prompt |

**Note:** Custom styles exclude coding instructions by default unless `keep-coding-instructions: true`.

## Examples

### Verbose/Explanatory Mode

```markdown
---
name: Verbose
description: Detailed explanations with reasoning
keep-coding-instructions: true
---

# Verbose Output Style

Provide detailed explanations for all actions.

## Behavior

- Explain reasoning before taking action
- Describe what you're doing and why
- Include alternative approaches considered
- Highlight trade-offs and decisions made

## Output Format

Before executing commands:
1. State the goal
2. Explain the approach
3. Describe expected outcome
4. Execute and verify
```

### Learning Mode

```markdown
---
name: Learning
description: Collaborative learn-by-doing with explanations
keep-coding-instructions: true
---

# Learning Output Style

Teach by doing. Explain concepts and ask learner to contribute.

## Approach

- Explain concepts before implementing
- Add `TODO(human)` markers for learner to implement
- Provide hints and guidance
- Review learner's contributions

## TODO Format

```python
# TODO(human): Implement user authentication
# Hint: Use bcrypt for password hashing
# Requirements:
# - Hash password with salt
# - Return boolean for success/failure
def authenticate_user(username: str, password: str) -> bool:
    pass
```

## Feedback

After learner implements:
- Review their code
- Highlight good practices
- Suggest improvements
- Explain best practices
```

### Concise Mode

```markdown
---
name: Concise
description: Minimal output, maximum efficiency
keep-coding-instructions: true
---

# Concise Output Style

Minimize output. Focus on actions and results.

## Rules

- No explanations unless asked
- Show code/commands only
- Brief confirmations only
- No preambles or summaries
```

### Business Analyst Mode

```markdown
---
name: Business Analyst
description: Non-technical explanations for business users
keep-coding-instructions: false
---

# Business Analyst Style

Communicate in business terms, avoiding technical jargon.

## Communication

- Use business language, not code terms
- Explain impact and value
- Focus on outcomes, not implementation
- Provide analogies for technical concepts

## Output Format

When analyzing:
1. What this means for the business
2. Expected impact
3. Risks and mitigation
4. Next steps
```

## Changing Output Style

### Via Commands

```bash
/output-style                    # Access menu
/output-style explanatory        # Switch directly
/config                          # Also accessible
```

### Via Settings

In `.claude/settings.local.json`:

```json
{
  "outputStyle": "Verbose"
}
```

## Best Practices

1. **Be specific about behavior**
   - Define communication patterns
   - Specify output format
   - Set expectations clearly

2. **Use `keep-coding-instructions` wisely**
   - `true` - Keep Claude Code's coding capabilities
   - `false` - Pure custom style (non-coding use cases)

3. **Test with real tasks**
   - Verify style works as intended
   - Adjust based on actual usage
   - Iterate on clarity

4. **Document scope**
   - User level: Personal preference across all projects
   - Project level: Team-shared style

5. **Provide examples in the style**
```markdown
## Example Output

When analyzing code:

"This function handles user authentication. It checks the password
against a hashed version stored in the database. If the password
matches, it creates a session token and returns it to the client."
```

## Comparison to Related Features

### Output Styles vs CLAUDE.md

| Aspect | Output Styles | CLAUDE.md |
|--------|---------------|-----------|
| What | System prompt modification | User message content |
| When | Global behavior change | Project instructions |
| Use | Communication style | Project context/rules |

### Output Styles vs Agents

| Aspect | Output Styles | Agents |
|--------|---------------|--------|
| Scope | Main conversation | Isolated context |
| Purpose | Change communication | Specialized tasks |
| Settings | Model, tools, context | Only system prompt |

### Output Styles vs Slash Commands

| Aspect | Output Styles | Commands |
|--------|---------------|----------|
| Type | System prompt | User prompt |
| Trigger | `/output-style` | `/command-name` |
| Scope | Session-wide | Single invocation |

## Example: Code Review Style

```markdown
---
name: Code Reviewer
description: Structured code review with best practices
keep-coding-instructions: true
---

# Code Review Style

Provide thorough code reviews following industry standards.

## Review Structure

For each file reviewed:

### ✅ Strengths
- What's done well
- Good practices observed

### ⚠️ Issues
**Critical** (must fix):
- Security vulnerabilities
- Logic errors
- Performance problems

**Warnings** (should fix):
- Code smell
- Maintainability concerns
- Missing error handling

**Suggestions** (consider):
- Optimization opportunities
- Refactoring ideas
- Alternative approaches

### 📝 Recommendations
1. Priority actions
2. Best practices to adopt
3. Resources for improvement

## Tone
- Constructive and encouraging
- Specific and actionable
- Explain the "why" behind suggestions
```

## Example: Documentation Writer

```markdown
---
name: Documentation Writer
description: Clear, comprehensive documentation
keep-coding-instructions: true
---

# Documentation Writer Style

Create clear, user-friendly documentation.

## Documentation Structure

### Overview
- What it does (1-2 sentences)
- When to use it
- Prerequisites

### Quick Start
- Minimal example
- Expected outcome
- Common first steps

### Detailed Guide
- Step-by-step instructions
- Code examples with comments
- Screenshots or diagrams (when applicable)

### API Reference
- All functions/classes
- Parameters and return types
- Examples for each

### Troubleshooting
- Common issues
- Solutions
- Debug tips

## Writing Style
- Clear and concise
- Active voice
- Present tense
- Examples for every concept
- Avoid jargon (or explain it)
```

---

Last updated: 2025-12-21
