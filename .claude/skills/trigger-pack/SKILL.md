---
name: trigger-pack
description: Consolidated Trigger.dev skill pack. Use when building, testing, or deploying Trigger.dev tasks. Replaces trigger-agents, trigger-config, trigger-realtime, trigger-setup, trigger-tasks, and build/TRIGGER-DEV-* modules. Load modules individually per task.
---

# Trigger.dev Pack

Unified reference for building Trigger.dev automations. Code-first: TypeScript task wrappers call Python scripts via `python.runScript()`. Deployed via `npx trigger.dev deploy`.

---

## Build Procedure

1. **Detect** — Confirm Trigger.dev orchestrator (`trigger.config.ts` exists in automations/)
2. **Read spec** — Extract flow, trigger type, systems, acceptance criteria
3. **Write task** → Load TASKS module for task patterns
4. **Add AI agents** → Load AGENTS module if automation uses LLMs
5. **Configure** → Load CONFIG module for trigger.config.ts changes
6. **Test locally** — `npx trigger.dev dev`
7. **Deploy** — `npx trigger.dev deploy`

---

## Critical Rules (Always Apply)

- **TypeScript wraps Python** — task files are `.ts`, they call Python scripts
- **Environment variables** via `TRIGGER_SECRET_KEY`, `TRIGGER_API_URL`, client API keys in `.env`
- **Default for new clients** — Trigger.dev is the default orchestrator

---

## Module Index

Load ONE module at a time based on your current task.

### Procedure Modules

| When | Module | Source |
|------|--------|--------|
| Writing basic tasks | [TRIGGER-DEV-BASIC-TASKS](../build/modules/TRIGGER-DEV-BASIC-TASKS.md) | build |
| Full build workflow | [TRIGGER-DEV-BUILD](../build/modules/TRIGGER-DEV-BUILD.md) | build |
| Modifying trigger.config.ts | [TRIGGER-DEV-CONFIG](../build/modules/TRIGGER-DEV-CONFIG.md) | build |
| Advanced patterns (concurrency, retries) | [TRIGGER-DEV-ADVANCED-TASKS](../build/modules/TRIGGER-DEV-ADVANCED-TASKS.md) | build |
| Scheduled/cron tasks | [TRIGGER-DEV-SCHEDULED](../build/modules/TRIGGER-DEV-SCHEDULED.md) | build |
| Frontend monitoring | [TRIGGER-DEV-REALTIME](../build/modules/TRIGGER-DEV-REALTIME.md) | build |
| AI agent tasks | [trigger-agents SKILL](../../.agents/skills/trigger-agents/SKILL.md) | .agents |
| Configuration reference | [trigger-config SKILL](../../.agents/skills/trigger-config/SKILL.md) | .agents |
| Realtime reference | [trigger-realtime SKILL](../../.agents/skills/trigger-realtime/SKILL.md) | .agents |
| New client setup | [trigger-setup SKILL](../../.agents/skills/trigger-setup/SKILL.md) | .agents |

### Reference Modules (load ONLY for specific lookups)

| When | Module | Source |
|------|--------|--------|
| Task orchestration patterns | [orchestration](../../.agents/skills/trigger-agents/references/orchestration.md) | .agents |
| Streaming patterns | [streaming](../../.agents/skills/trigger-agents/references/streaming.md) | .agents |
| Waitpoint patterns | [waitpoints](../../.agents/skills/trigger-agents/references/waitpoints.md) | .agents |
| AI tool integration | [ai-tool](../../.agents/skills/trigger-agents/references/ai-tool.md) | .agents |
| Basic task reference | [basic-tasks](../../.agents/skills/trigger-tasks/references/basic-tasks.md) | .agents |
| Advanced task reference | [advanced-tasks](../../.agents/skills/trigger-tasks/references/advanced-tasks.md) | .agents |
| Scheduled task reference | [scheduled-tasks](../../.agents/skills/trigger-tasks/references/scheduled-tasks.md) | .agents |
