# Decision Tree: Choosing the Right Primitive

Last updated: 2026-02-26

## Quick Decision

| You want to... | Use |
|----------------|-----|
| Add a complex, reusable capability | **Skill** |
| Create a quick action triggered with `/` | **Command** |
| Run work in parallel / isolated context | **Agent** |
| Store project instructions / rules | **Memory** |
| Configure permissions / environment | **Settings** |
| React to tool calls or events | **Hooks** |
| Integrate external tools | **MCP Server** |
| Change how Claude communicates | **Output Style** |
| Package and distribute capabilities | **Plugin** |

---

## Agentic Ops Decision Criteria

Workspace-specific guidance that supplements the generic flowchart below. **This is the canonical source** — the operationalization-loop rule and `/system-dev` command both defer here.

### Rule vs. Skill Module

**Litmus test:** Would the agent need this fact even when NOT working in the relevant domain?

| If yes → **Rule** | If no → **Skill module** |
|---|---|
| "Always verify outcomes, not just execution status" | "filterRows needs empty-row guard in Make.com" |
| "Update spec frontmatter before checkpointing" | "n8n Code nodes can't import external packages" |
| "After every fix, ask if this is preventable" | "Gmail modules are unreliable via API deployment" |

Rules discipline (no repo-wide LOC budget; the old "250 total" was ~8x under the real total and rewarded nothing). Two checks before adding or expanding a rule: (1) **no duplicated bans** — a ban already stated elsewhere is not restated; the voice / em-dash / corporate-thesaurus lists live once in `rule_anti_slop.md` and are reused by cross-reference; (2) **per-file soft ceiling ~250 lines** — a single `rule_*.md` over it is a split candidate. Check per-file with `wc -l .claude/rules/*.md`; `tools/anneal-metrics.py` surfaces per-file overages as an advisory.

### Extend vs. Create

Always prefer **adding a module to an existing skill** over creating a new skill. A new skill is warranted only when:
1. The domain is genuinely distinct from all existing skills, AND
2. The knowledge will be needed independently of existing skill contexts

Example: Outcome verification → added as a module inside `build-test-fix` (not a separate `outcome-validator` skill), because it's part of the build iteration loop.

### Agent Sub-Types

| Type | Description | Current examples |
|---|---|---|
| **User-invokable** | User triggers via Task tool or build-orchestrator delegates | `testing-agent`, `deployer`, `bug-fixer`, `api-fetcher`, `trigger-dev-expert` |
| **Orchestrator-internal** | Only called by `build-orchestrator` — never directly by user | `doc-generator`, `implementation-agent`, `project-manager` |

When creating an agent, decide which type it is. This determines the description phrasing and whether to add it to CLAUDE.md's user-invokable list.

### Friction-to-Primitive Mapping

When operationalizing after a fix or build, use this to bridge from the problem category to the right primitive:

| Friction / Error Category | Primitive | Example |
|---|---|---|
| Agent didn't know how to do X | Skill module (in existing skill) | Add IML gotcha to `make-mcp-tools-expert` |
| Agent did something it shouldn't / didn't do something it should | Rule (if universal) | Add outcome verification gate to `behaviors.md` |
| Same manual steps done 3+ times | Command | `/spec-cleanup` wrapping the `spec-cleanup` skill |
| Bug found only through manual testing | Validator/reconciler (skill module) | `blueprint-reconciler` DATA-STORE module |
| Blueprint/data store/sheet drift | Reconciliation tool (skill module) | `blueprint-reconciler` SHEETS-COLUMN module |
| Agent couldn't diagnose autonomously | Diagnostic module (in existing skill) | `WEBHOOK-PAYLOAD-INSPECTOR` in `make-mcp-tools-expert` |

---

## Flowchart

```
START: What do you want to add?
│
├─► "A capability (workflow, domain expertise)"
│   │
│   ├─► "Should it trigger automatically based on context?"
│   │   │
│   │   ├─► YES: "Does it need isolated context?"
│   │   │   │
│   │   │   ├─► YES (parallel work) → AGENT
│   │   │   │   Examples: testing-agent, bug-fixer, trigger-dev-expert
│   │   │   │
│   │   │   └─► NO → SKILL
│   │   │       Examples: make-mcp-tools-expert, build-test-fix, spec-creator
│   │   │
│   │   └─► NO (explicit trigger): "Simple or complex?"
│   │       │
│   │       ├─► Simple prompt → COMMAND
│   │       │   Examples: /checkpoint, /new-client, /status-check
│   │       │
│   │       └─► Complex workflow → SKILL (+ optional /command wrapper)
│   │           Examples: build skill + /build-automation command
│
├─► "Configuration / Instructions"
│   │
│   ├─► "What kind?"
│   │   │
│   │   ├─► Project instructions, coding standards → MEMORY (CLAUDE.md)
│   │   │   Examples: workspace structure, spec frontmatter format, git subtree
│   │   │
│   │   ├─► Universal behavioral constraints → MEMORY (rules/)
│   │   │   Examples: behaviors, detection
│   │   │
│   │   ├─► Permissions, env vars, tool config → SETTINGS
│   │   │   Examples: allow Bash, set API keys, model override
│   │   │
│   │   └─► Change output style → OUTPUT STYLE
│   │       Examples: verbose mode, learning mode, business mode
│
├─► "Automation / Event handling"
│   │
│   └─► React to tool calls, lifecycle events → HOOKS
│       Examples: lint before commit, notify on completion, block sensitive files
│
├─► "Integration"
│   │
│   └─► "External tool or service?"
│       │
│       └─► YES → MCP SERVER
│           Examples: GitHub, Slack, database, Stripe, Sentry
│
└─► "Distribution / Sharing"
    │
    └─► Package capabilities for others → PLUGIN
        Bundles: commands, agents, skills, hooks, MCP servers
```

---

## Decision Matrix

| Question | Answer | Result |
|----------|--------|--------|
| Auto-trigger + Same context? | Yes | **Skill** |
| Auto-trigger + Parallel/isolated? | Yes | **Agent** |
| Explicit trigger + Simple? | Yes | **Command** |
| Explicit trigger + Complex? | Yes | **Skill** (+ command) |
| Project instructions / rules? | Yes | **Memory** |
| Permissions / env config? | Yes | **Settings** |
| React to events / tool calls? | Yes | **Hooks** |
| External tools / services? | Yes | **MCP Server** |
| Change output / communication? | Yes | **Output Style** |
| Share as versioned package? | Yes | **Plugin** |

---

## Primitives by Category

### Core Primitives (Add Capabilities)

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Skill** | Complex workflows, domain expertise | Multi-file (`SKILL.md` + modules) |
| **Command** | Quick actions, daily routines | Single file (`.md`) |
| **Agent** | Parallel work, specialists | Single file (`.md`) |

### Configuration Primitives

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Memory** | Instructions, rules, context | `CLAUDE.md`, `.claude/rules/*.md` |
| **Settings** | Permissions, env vars, hooks | `.claude/settings.json` |
| **Output Style** | Communication style | `.claude/output-styles/*.md` |

### Integration Primitives

| Primitive | Best For | Files |
|-----------|----------|-------|
| **Hooks** | Event automation | `settings.json` (hooks key) |
| **MCP Server** | External tools | `.mcp.json` |
| **Plugin** | Distribution | `.claude-plugin/plugin.json` |

---

## Examples by Primitive (Agentic Ops)

### Skills (auto-discovered, domain knowledge)
- `make-mcp-tools-expert` - Make.com MCP tool usage, IML gotchas, blueprint format
- `build-test-fix` - Autonomous build/test/fix iteration loop with outcome verification
- `blueprint-reconciler` - Cross-validates blueprints against data stores, sheets, templates
- `spec-creator` - Creates automation specs from requirements with Mermaid diagrams
- `n8n-workflow-patterns` - Proven architectural patterns for n8n workflows

### Commands (explicit `/trigger`)
- `/build-automation` - End-to-end build via build-orchestrator agent
- `/checkpoint` - Save conversation state for session continuity
- `/system-dev` - Friction audit and system improvement loop
- `/new-client` - Initialize client folder structure
- `/resume` - Reload context from latest checkpoint

### Agents (isolated context, parallel work)
- `build-orchestrator` - Coordinates Plan > Implement > Test > Deploy lifecycle
- `testing-agent` - Validates automations against specs (user-invokable)
- `implementation-agent` - Generates code from specs (orchestrator-internal)
- `bug-fixer` - Analyzes test failures and implements fixes (user-invokable)

### Memory (rules, project instructions)
- `CLAUDE.md` - Workspace structure, spec format, quick start, primitives registry
- `behaviors.md` - Self-annealing, outcome verification, test fixtures, build escalation
- `detection.md` - Orchestrator detection and client assignment

---

## Hybrid Patterns

### Skill + Command
For complex workflows that user wants to trigger explicitly:
```
.claude/skills/build/            → The orchestrator-aware implementation guide
.claude/commands/build-automation.md → Explicit trigger (/build-automation)
```

**When to use:**
- Skill auto-triggers when building automations
- But user also wants explicit `/build-automation` entry point
- Command invokes the skill + orchestrates the build-orchestrator agent

### Agent + Skill
For specialists that use specific capabilities:
```
.claude/skills/build-test-fix/   → The iteration loop capability
.claude/agents/testing-agent.md  → Specialist that runs the loop in isolation
```

**When to use:**
- Skill provides the domain knowledge (failure taxonomy, fix patterns)
- Agent provides isolated context for parallel test runs
- Agent references skill modules in its instructions

### Memory + Settings
For project configuration:
```
CLAUDE.md                        → Instructions and context
.claude/rules/                   → Path-specific rules
.claude/settings.json            → Permissions and env vars
```

**When to use:**
- Memory for what to do
- Settings for what's allowed
- Rules for path-specific instructions

### Settings + Hooks
For automation with permissions:
```
.claude/settings.json            → Permissions, env, hooks config
.claude/hooks/format.sh          → Hook script
```

**When to use:**
- Settings define when hooks run
- Hooks define what happens
- Permissions control what's allowed

### Plugin (All-in-one)
For distributing a complete solution:
```
.claude-plugin/
├── plugin.json                  → Manifest
├── commands/                    → Slash commands
├── agents/                      → Subagents
├── skills/                      → Skills
├── hooks/hooks.json             → Event handlers
└── .mcp.json                    → MCP servers
```

**When to use:**
- Sharing with team or community
- Versioned releases
- Bundled functionality
- Reusable across projects

---

## Detailed Decision Questions

### 1. Is this a capability or configuration?

**Capability** (adds new functionality):
- → Skill, Command, or Agent

**Configuration** (modifies behavior):
- → Memory, Settings, Output Style

**Integration** (external tools):
- → Hooks, MCP Server

**Distribution** (package for sharing):
- → Plugin

### 2. For capabilities: How is it triggered?

**Auto-trigger** (Claude decides when):
- Same context → **Skill**
- Isolated context → **Agent**

**User-trigger** (explicit `/command`):
- Simple prompt → **Command**
- Complex workflow → **Skill** (+ optional command)

### 3. For configuration: What does it configure?

**Instructions / Rules**:
- Project-wide → **Memory** (CLAUDE.md)
- Path-specific → **Memory** (rules/)

**Behavior / Permissions**:
- Permissions, env vars → **Settings**
- Communication style → **Output Style**

**Automation**:
- Event-driven actions → **Hooks**

### 4. For integration: What type?

**External service**:
- → **MCP Server**

**Event automation**:
- → **Hooks**

**Distribution**:
- → **Plugin**

---

## Common Scenarios (Agentic Ops)

| Scenario | Solution |
|----------|----------|
| "Agent didn't know Make.com IML syntax" | **Skill module** (add to `make-mcp-tools-expert/IML-GOTCHAS.md`) |
| "Agent should always verify outcomes after builds" | **Rule** (`behaviors.md` — universal constraint) |
| "User wants `/spec-cleanup` command" | **Command** (wraps existing `spec-cleanup` skill) |
| "Agent needs to run blueprint validation in isolation" | **Agent** (if context isolation needed) or **Skill** (if same context) |
| "n8n nodes need specific config patterns" | **Skill module** (`n8n-node-configuration`) |
| "Same manual steps done every deploy" | **Command** (`/deploy`) |
| "Agent checked execution status but not output correctness" | **Skill module** (`build-test-fix/OUTCOME-VERIFICATION.md`) |
| "Integrate Make.com MCP tools" | **MCP Server** (`.mcp.json` entry) |
| "Agent keeps forgetting to update frontmatter" | **Rule** (if every session) or **Skill** (if only during spec work) |
| "Need to detect which orchestrator a client uses" | **Rule** (`detection.md` — needed every session) |

---

## Anti-Patterns (What NOT to Do)

❌ **Don't use Command for complex workflows**
- Commands are single-file prompts
- Use Skill for multi-step processes

❌ **Don't use Skill when Command is enough**
- If it's just a quick prompt, use Command
- Skills are for complex, reusable capabilities

❌ **Don't put configuration in Skills**
- Use Memory for instructions
- Use Settings for permissions/env

❌ **Don't duplicate Memory and Settings**
- Memory = what to do
- Settings = what's allowed

❌ **Don't create Agent for simple tasks**
- Agents have context isolation overhead
- Use Skill for same-context work

❌ **Don't hardcode secrets in Settings**
- Use environment variables
- Reference via `${VAR}` syntax

❌ **Don't use Hooks for capabilities**
- Hooks are event-driven automation
- Use Skill/Command for user-facing features

---

## Migration Paths

### Outgrew a Command → Skill
Command got too complex:
```
Before: .claude/commands/complex-task.md
After:  .claude/skills/complex-task/SKILL.md
        .claude/commands/complex-task.md (optional trigger)
```

### Need to Share → Plugin
Project-level primitives → Distributable:
```
Before: .claude/skills/my-skill/
        .claude/commands/my-cmd.md
After:  my-plugin/
        ├── .claude-plugin/plugin.json
        ├── skills/my-skill/
        └── commands/my-cmd.md
```

### Settings Grew → Split
Large settings file → Organized:
```
Before: .claude/settings.json (everything)
After:  .claude/settings.json (permissions, env)
        CLAUDE.md (instructions)
        .claude/rules/ (path-specific)
```

---

Last updated: 2026-02-26
