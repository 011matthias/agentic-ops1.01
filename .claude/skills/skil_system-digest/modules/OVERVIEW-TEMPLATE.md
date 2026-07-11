# Overview Template

Template for generating a full system overview digest. Two variants: internal (technical) and client-facing (value-focused).

## Data Collection

Before rendering, collect this data:

### Primitives Inventory

```bash
# Rules
ls .claude/rules/*.md
wc -l .claude/rules/*.md  # total lines + budget (250)

# Skills
ls .claude/skills/*/SKILL.md
# For each: read first line of description from frontmatter

# Agents
ls .claude/agents/*.md

# Commands
ls .claude/commands/*.md
```

### Client Inventory

```bash
# List clients
ls workspace/clients/

# Per client:
# - Read infrastructure.yaml for orchestrator type
# - Read specs/automation-status.yaml for automation list + status
# - Count specs per stage folder (1-spec, 2-build, 3-test, 4-live)
```

### Skill Module Counts

```bash
# Per skill: count modules
ls .claude/skills/*/modules/*.md 2>/dev/null | wc -l
```

---

## Internal Template

Use this template when `--client-facing` is NOT specified.

```markdown
# Agentic Ops — System Overview
Generated: {DATE}

## System Summary

Agentic Ops is an automation infrastructure for building, testing, deploying, and maintaining
client automations across four orchestrators (n8n, Make.com, Trigger.dev, FastAPI).

The system is built on four primitive types that form a self-annealing loop:
commands invoke agents, agents load skills, skills follow rules, and after every
build or fix the operationalization loop asks "should this become a new primitive?"

## Primitives Inventory

| Type | Count | Details |
|------|-------|---------|
| Rules | {RULE_COUNT} | {RULE_LINES} LOC; per-file soft ceiling 250 |
| Skills | {SKILL_COUNT} | {MODULE_COUNT} total modules |
| Agents | {AGENT_COUNT} | {USER_AGENT_COUNT} user-invokable, {INTERNAL_AGENT_COUNT} internal |
| Commands | {COMMAND_COUNT} | User-triggered via /command |

### Rules (auto-loaded every session)
{For each rule: "- **{name}** — {first line of file or purpose}"}

### Skills by Domain
{Group skills by domain (Core, Make.com, n8n, Trigger.dev, API, Comms, Meta)}
{For each: "- **{name}** — {description from frontmatter}"}

### Agents
**User-invokable:** {list}
**Orchestrator-internal:** {list}

### Commands
{Table: command | description (from frontmatter)}

## Architecture

```
User types /command
    → Command parses args, invokes Agent(s)
        → Agent loads relevant Skills
            → Skills follow Rules (auto-loaded constraints)
    → After completion: operationalization-loop fires
    → At checkpoint: strategic-feedback surfaces observations
```

## Build Lifecycle

```
/build-automation {client}
  Phase 1: Plan      → spec-creator → user approval
  Phase 2: Implement  → build skill (routes by orchestrator)
  Phase 3: Test       → build-test-fix (3-iteration loop)
  Phase 3.5: Dev Test → real APIs + outcome verification
  Phase 4: Document   → doc-generator
  Phase 5: Deploy     → deployer (test gate)
  Phase 6: Verify     → live output verification
```

## Clients

{For each client:}
### {Client Name}
- **Orchestrator:** {type}
- **Automations:** {count} ({count per status})
- **Status:** {summary of automation statuses}

## System Health

- Rules: {RULE_LINES} LOC total; per-file soft ceiling 250 (split candidates flagged by anneal-metrics)
- Skill coverage: {domains covered}
- Total modules: {MODULE_COUNT}
```

---

## Client-Facing Template

Use this template when `--client-facing` IS specified.

```markdown
# Automation Infrastructure — Overview
Generated: {DATE}

## What We've Built

A comprehensive automation system that handles the full lifecycle of your
business automations — from specification to deployment to monitoring.

## How It Works

1. **Specification** — We define exactly what each automation does, what triggers it,
   and what the expected outcomes are
2. **Implementation** — We build the automation using {ORCHESTRATOR} as the platform
3. **Testing** — Automated verification ensures everything works correctly with real data
4. **Deployment** — One-command deployment with safety gates
5. **Monitoring** — Ongoing verification that automations produce correct results

## Your Automations

{For each client (or specified client):}

### {Automation Name} ({Status Badge})
- **What it does:** {description from spec}
- **Triggered by:** {trigger type}
- **Systems involved:** {systems list}
- **Status:** {human-readable status}

## What's Configurable

Everything is designed to be adjustable without touching the underlying code:
{List configurable items from client's infrastructure.yaml or spec configurability sections}

## System Reliability

- Automated testing before every deployment
- Outcome verification (not just "did it run" but "did it produce the right result")
- Autonomous error recovery (up to 3 automatic fix attempts before escalation)
- Full audit trail of all changes and decisions
```
