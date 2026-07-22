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
| AI agent tasks | [AGENTS](modules/AGENTS.md) | trigger-pack |
| Configuration reference | [CONFIG](modules/CONFIG.md) | trigger-pack |
| Realtime reference | [REALTIME](modules/REALTIME.md) | trigger-pack |
| New client setup | [SETUP](modules/SETUP.md) | trigger-pack |

### Reference Modules (load ONLY for specific lookups)

| When | Module | Source |
|------|--------|--------|
| Task orchestration patterns | [orchestration](references/orchestration.md) | trigger-pack |
| Streaming patterns | [streaming](references/streaming.md) | trigger-pack |
| Waitpoint patterns | [waitpoints](references/waitpoints.md) | trigger-pack |
| AI tool integration | [ai-tool](references/ai-tool.md) | trigger-pack |
| Basic task reference | [basic-tasks](references/basic-tasks.md) | trigger-pack |
| Advanced task reference | [advanced-tasks](references/advanced-tasks.md) | trigger-pack |
| Scheduled task reference | [scheduled-tasks](references/scheduled-tasks.md) | trigger-pack |
| Full trigger.config.ts reference (custom + advanced build extensions) | [config](references/config.md) | trigger-pack |
| Full realtime reference (public tokens, run object properties) | [realtime](references/realtime.md) | trigger-pack |
| Env vars, dev vs prod keys, CI/CD and multi-environment setup | [environment-setup](references/environment-setup.md) | trigger-pack |
| Project layout, monorepos, multiple or collocated task dirs | [project-structure](references/project-structure.md) | trigger-pack |
