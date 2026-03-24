# Creating Memory

Memory provides instructions and context that persist across sessions through CLAUDE.md and rules files.

## When to Use

- Define project-wide coding standards
- Store team instructions and context
- Path-specific rules for different file types
- Personal preferences across projects
- Organization-wide policies

## Memory Hierarchy

| Tier | Location | Scope | Shared |
|------|----------|-------|--------|
| **Enterprise** | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | All users in organization | Yes (via IT) |
| **Project** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team via git | Yes |
| **Project Rules** | `./.claude/rules/*.md` | Team via git | Yes |
| **User** | `~/.claude/CLAUDE.md` | Personal (all projects) | No |
| **Local** | `./CLAUDE.local.md` | Personal (this project only) | No (gitignored) |

**Precedence:** Lower-level memories override higher-level ones. Local > User > Project Rules > Project > Enterprise.

## File Locations

### CLAUDE.md Locations

```
# Project memory (shared with team)
./CLAUDE.md                      # Option 1: Project root
./.claude/CLAUDE.md              # Option 2: Inside .claude/

# User memory (personal, all projects)
~/.claude/CLAUDE.md

# Local override (personal, this project only)
./CLAUDE.local.md                # Auto-added to .gitignore
```

### Rules Directory

```
.claude/rules/
├── code-style.md               # Coding conventions
├── testing.md                  # Test requirements
├── api.md                      # API patterns
└── frontend/                   # Subdirectory organization
    ├── react.md
    └── styles.md
```

All `.md` files in `.claude/rules/` are automatically loaded.

## Format

### Basic CLAUDE.md

```markdown
# Project Name

You are the orchestration layer for this workspace.

## Coding Standards

- Use 2-space indentation
- TypeScript for all new code
- Test coverage required

## Project Context

- API base: https://api.example.com
- Auth: JWT tokens in localStorage
- DB: PostgreSQL on localhost:5432
```

### Path-Specific Rules

Use YAML frontmatter with `paths` field:

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules

- All endpoints must include input validation
- Use standard error response format
- Include OpenAPI documentation comments
```

**Glob patterns:**
- `**/*.ts` - All TypeScript files
- `src/**/*` - All files under src/
- `{src,lib}/**/*.ts` - Multiple directories
- `*.test.ts, *.spec.ts` - Multiple extensions

## Import Syntax

Include other files using `@path`:

```markdown
See @README for project overview.

Additional context:
- Git workflow: @docs/git-instructions.md
- Deployment: @~/.claude/deploy-process.md

Available npm commands: @package.json
```

**Features:**
- Relative paths: `@docs/file.md`
- Absolute paths: `@/absolute/path/file.md`
- Home directory: `@~/.claude/file.md`
- Max depth: 5 hops (prevents circular imports)
- Not evaluated in code blocks: `` `@example` ``

## Organization Patterns

### Simple Project

```
./CLAUDE.md                     # All instructions in one file
```

### Organized Project

```
.claude/
├── CLAUDE.md                   # Overview + imports
└── rules/
    ├── code-style.md
    ├── testing.md
    ├── api.md
    └── security.md
```

### Large Project

```
.claude/
├── CLAUDE.md                   # Overview + imports
└── rules/
    ├── general.md
    ├── frontend/
    │   ├── react.md
    │   ├── styles.md
    │   └── testing.md
    └── backend/
        ├── api.md
        ├── database.md
        └── security.md
```

## User-Level Rules

Create personal rules for all projects:

```
~/.claude/rules/
├── preferences.md              # Personal coding preferences
├── workflows.md                # Preferred workflows
└── shortcuts.md                # Custom shortcuts
```

User-level rules load before project rules (project takes precedence).

## Best Practices

1. **Be specific** - "Use 2-space indentation" > "Format code properly"
2. **Use structure** - Organize with headings and bullet points
3. **Review periodically** - Update as project evolves
4. **Keep rules focused** - One topic per file in rules/
5. **Use path-specific rules sparingly** - Only when truly necessary
6. **Organize with subdirectories** - Group related rules
7. **Use imports for team docs** - Alternative to duplication

## Memory Commands

```bash
/init      # Bootstrap a CLAUDE.md for your codebase
/memory    # Open memory file in editor
```

View loaded memory files with `/memory` command in Claude Code.

## Lookup Behavior

Claude Code reads memories **recursively** from current working directory up to (but not including) root `/`.

Example: If in `foo/bar/`, it loads:
- `foo/CLAUDE.md`
- `foo/bar/CLAUDE.md`
- `foo/bar/CLAUDE.local.md`
- All files in `foo/bar/.claude/rules/`

## Enterprise Deployment

Deploy organization-wide CLAUDE.md via:
- MDM (Mobile Device Management)
- Group Policy
- Ansible
- Configuration management systems

Place at enterprise policy locations (see hierarchy table above).

## Example: Path-Specific Testing Rules

```markdown
---
paths: **/*.test.ts, **/*.spec.ts
---

# Testing Conventions

- Use Vitest for all tests
- Follow Arrange-Act-Assert pattern
- Mock external dependencies
- Minimum 80% coverage for new code
```

## Example: API-Specific Rules

```markdown
---
paths: src/api/**/*.ts
---

# API Endpoint Standards

- All endpoints return consistent JSON structure
- Use Zod for input validation
- Include rate limiting
- Log all errors with request ID
```

---

Last updated: 2025-12-21
