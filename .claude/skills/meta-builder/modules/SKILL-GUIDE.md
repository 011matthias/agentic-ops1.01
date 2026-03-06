# Creating Skills

Skills are model-invoked capabilities that Claude auto-discovers based on context.

Last updated: 2025-12-21

## When to Create a Skill

- Complex multi-step workflows
- Domain-specific expertise
- Reusable across multiple requests
- Should auto-trigger when relevant

## File Locations

| Scope | Location | Use Case |
|-------|----------|----------|
| Project | `.claude/skills/skill-name/` | Shared with team via git |
| Personal | `~/.claude/skills/skill-name/` | Available across all projects |

## Structure

### Simple Skill (Single File)

```
.claude/skills/my-skill/
└── SKILL.md
```

### Multi-File Skill (Progressive Disclosure)

```
.claude/skills/my-skill/
├── SKILL.md              # Entry point (<500 lines)
├── modules/              # Detailed instructions (loaded as needed)
│   ├── STEP-1.md
│   └── STEP-2.md
├── templates/                      # Reusable templates
│   └── template.txt
├── scripts/              # Executed via bash (zero context cost)
│   └── helper.py
└── examples.md           # Optional usage examples
```

## SKILL.md Format

### YAML Frontmatter

```yaml
---
name: skill-name
description: What it does and when to use it. Third person. Include trigger terms.
allowed-tools: Read, Grep, Glob    # Optional - restrict available tools
---
```

**Fields:**

| Field | Required | Limits | Description |
|-------|----------|--------|-------------|
| `name` | Yes | max 64 chars, lowercase/numbers/hyphens | Unique identifier |
| `description` | Yes | max 1024 chars | WHAT it does + WHEN to use it |
| `allowed-tools` | No | comma-separated | Restricts tools when skill is active |

### Tool Restrictions

Use `allowed-tools` to limit Claude's capabilities when the skill is active:

```yaml
---
name: safe-file-reader
description: Read files without making changes. Use when you need read-only file access.
allowed-tools: Read, Grep, Glob
---
```

**Use cases:**
- Read-only skills (no Edit, Write, Bash)
- Security-sensitive workflows
- Limited scope analysis

### Markdown Body

```markdown
# Skill Name

## Quick Start
[Most common usage pattern]

## Available Operations
[Table of capabilities with links to modules]

## Scripts
[List of available scripts with usage]
```

## Best Practices

### 1. Write Specific Descriptions

Include WHAT it does AND WHEN to use it:

**Bad:**
```yaml
description: Helps with documents
```

**Good:**
```yaml
description: Extracts text and tables from PDF files, fills forms, merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

### 2. Use Third Person

**Bad:** "I can help you process..."
**Good:** "Processes files and generates..."

### 3. Keep SKILL.md Under 500 Lines

Use modules for detailed instructions:
```markdown
For detailed form filling, see [FORMS.md](modules/FORMS.md).
```

### 4. Keep References One Level Deep

All modules should link directly from SKILL.md, not nested:

**Bad:**
```
SKILL.md → advanced.md → details.md
```

**Good:**
```
SKILL.md → STEP-1.md
SKILL.md → STEP-2.md
SKILL.md → REFERENCE.md
```

### 5. Scripts in scripts/ Folder

Scripts are executed via bash, never loaded into context:
```markdown
## Scripts

Run validation:
```bash
uv run scripts/validate.py input.csv
```
```

### 6. Extract Prompts to prompts/ Folder

User-facing prompts should be extracted to reusable files:

**Instead of inline prompts:**
```markdown
Ask the user:
> "What is your campaign name?"
```

**Use prompt files:**
```markdown
Load and follow `prompts/campaign-setup.md`
```

**Benefits:**
- Easy to customize without touching skill logic
- A/B test different prompt variations
- Reuse prompts across modules
- Keep SKILL.md and modules concise

**Structure:**
```
prompts/
├── setup.md              # Initial setup questions
├── validation.md         # Confirm before proceeding
└── workflow/             # Workflow-specific subfolder
    ├── step-1.md
    └── step-2.md
```

### 7. Use Gerund Naming

Prefer verb-ing form:
- `processing-pdfs` not `pdf-processor`
- `generating-leads` not `lead-gen`

### 8. Model Selection in Scripts

When scripts call AI models, use **OpenRouter** as the default API and select cost-appropriate models.

**Reference:** See `context/models/openrouter-model-selection.md` for full guide.

**Quick Decision Tree:**

| Task Type | Recommended Model | Cost |
|-----------|-------------------|------|
| Simple extraction/parsing | `google/gemini-2.5-flash` | $0.30-2.50/M |
| JSON/structured output | `openai/gpt-4o-mini` | $0.15-0.60/M |
| Summarization | `anthropic/claude-3.5-haiku` | $0.80-4.00/M |
| Code generation | `anthropic/claude-sonnet-4` | $3.00-15.00/M |
| Image generation | `google/gemini-2.5-flash-image-preview` | ~$0.04/image |

**Pattern for scripts:**

```python
import os
import requests

def call_openrouter(prompt: str, model: str = "anthropic/claude-3.5-haiku") -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
```

**Cost Variants:**
- Add `:floor` suffix for cheapest provider: `anthropic/claude-3.5-haiku:floor`
- Add `:nitro` suffix for fastest provider: `openai/gpt-4o:nitro`

## Sharing Skills

### Via Git (Project Skills)
1. Add skill to `.claude/skills/` in project
2. Commit to git
3. Team members get skills on `git pull`

### Via Plugins (Recommended for Distribution)
1. Create plugin with skills in `skills/` directory
2. Add plugin to marketplace
3. Users install plugin

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Claude doesn't use skill | Include both WHAT and WHEN in description; add trigger keywords |
| Invalid YAML | Check opening/closing `---`, no tabs, proper indentation |
| Wrong file path | Project: `.claude/skills/name/SKILL.md`, Personal: `~/.claude/skills/name/SKILL.md` |
| Missing files | Verify SKILL.md exists in correct location |

## Template

Use [skill-template.md](../templates/skill-template.md) to create new skills.
