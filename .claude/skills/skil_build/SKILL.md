---
name: build
description: Orchestrator-aware implementation guide. Use when implementing, coding, or building any automation or workflow — detects whether the client uses n8n, Make.com, Trigger.dev, or FastAPI and loads the correct sub-skills and implementation patterns for that orchestrator.
---

# Build

Orchestrates the full implementation of an automation by detecting the orchestrator and loading the correct sub-skills and patterns.

---

## Step 1: Detect Orchestrator

Check the client's automations folder to identify which orchestrator is in use:

| Check | Orchestrator |
|-------|-------------|
| `trigger.config.ts` exists in automations folder | **Trigger.dev** |
| `.mcp.json` has entry named `n8n-{client}` | **n8n** |
| `infrastructure.yaml` has `type: make` entry | **Make.com** |
| `railway.toml` exists (no trigger.config.ts) | **FastAPI (legacy)** |

```bash
# Quick detection
ls workspace/clients/{client}/automations/trigger.config.ts  # → Trigger.dev
grep -l "n8n-{client}" .mcp.json                   # → n8n
grep -l "type: make" workspace/clients/{client}/infrastructure.yaml  # → Make.com
ls workspace/clients/{client}/automations/railway.toml        # → FastAPI
```

---

## Step 2: Read the Spec

Locate the spec in `workspace/clients/{client}/specs/{stage}/{id}.md`.

Extract:
- **id, name, type, orchestrator** from frontmatter
- **Trigger type** (cron, webhook, manual, event)
- **Systems** (which APIs/services are involved)
- **Flow diagram** (Mermaid — understand the steps)
- **Step details** (initialize → fetch → transform → execute → finalize)
- **Edge cases** (error handling requirements)
- **Environment variables** needed
- **Acceptance criteria** (for tests)

---

## Step 3: Branch by Orchestrator

### n8n → Load `n8n-pack` skill + Read [N8N-BUILD.md](modules/N8N-BUILD.md)

Load the **`n8n-pack`** skill for the unified build procedure and module index. Load individual modules per task — never load all at once.

See [N8N-BUILD.md](modules/N8N-BUILD.md) for the full step-by-step workflow.

---

### Make.com → Load `make-pack` skill + Read [MAKE-BUILD.md](modules/MAKE-BUILD.md)

Load the **`make-pack`** skill for the unified build procedure and module index. Load individual modules per task.

See [MAKE-BUILD.md](modules/MAKE-BUILD.md) for the full step-by-step workflow.

---

### Trigger.dev → Load `trigger-pack` skill + Read [TRIGGER-DEV-BUILD.md](modules/TRIGGER-DEV-BUILD.md)

Load the **`trigger-pack`** skill for the unified build procedure and module index. Load individual modules per task.

See [TRIGGER-DEV-BUILD.md](modules/TRIGGER-DEV-BUILD.md) for the full step-by-step workflow.

---

### Platform (Next.js/portal) → Read [PLATFORM-DEV.md](modules/PLATFORM-DEV.md)

For work in `platform/` — Next.js 16, Tailwind CSS 4, Drizzle ORM, NextAuth 5, Neon DB, Playwright. Covers auth guard patterns, DB schema, Canva design workflow, and Playwright smoke tests.

See [PLATFORM-DEV.md](modules/PLATFORM-DEV.md) for the full implementation guide.

---

### FastAPI → Read [FASTAPI-BUILD.md](modules/FASTAPI-BUILD.md)

Legacy Python/FastAPI service. Follow the implementation-agent patterns:

1. Check API clients exist in `app/clients/{system}/`
2. Write automation class extending `BaseAutomation`
3. Add webhook route or cron endpoint
4. Update `app/config.py` with env vars
5. Write tests

See [FASTAPI-BUILD.md](modules/FASTAPI-BUILD.md) for the full step-by-step workflow.

---

## Step 4: Post-Implementation (All Orchestrators)

After implementation is complete:

### Update Spec Frontmatter

```yaml
stage: build          # or test if fully implemented
last_changes:
  - Implemented {feature}
  - Added {component}
next_steps:
  - Run tests
  - Set env vars: {VAR_1}, {VAR_2}
updated: {today}
```

### Testing

After code is written, use the testing-agent (`/test {client} {id}`) to verify the automation works end-to-end.

---

## Modules

| Module | Purpose |
|--------|---------|
| [N8N-BUILD.md](modules/N8N-BUILD.md) | Full n8n implementation workflow |
| [MAKE-BUILD.md](modules/MAKE-BUILD.md) | Full Make.com implementation workflow |
| [TRIGGER-DEV-BUILD.md](modules/TRIGGER-DEV-BUILD.md) | Full Trigger.dev implementation workflow |
| [TRIGGER-DEV-BASIC-TASKS.md](modules/TRIGGER-DEV-BASIC-TASKS.md) | Trigger.dev basic task patterns (v4) |
| [TRIGGER-DEV-ADVANCED-TASKS.md](modules/TRIGGER-DEV-ADVANCED-TASKS.md) | Advanced patterns (concurrency, retries, idempotency) |
| [TRIGGER-DEV-CONFIG.md](modules/TRIGGER-DEV-CONFIG.md) | trigger.config.ts & build extensions |
| [TRIGGER-DEV-REALTIME.md](modules/TRIGGER-DEV-REALTIME.md) | Realtime monitoring & React hooks |
| [TRIGGER-DEV-SCHEDULED.md](modules/TRIGGER-DEV-SCHEDULED.md) | Scheduled/cron tasks |
| [FASTAPI-BUILD.md](modules/FASTAPI-BUILD.md) | Full FastAPI implementation workflow |
| [PLATFORM-DEV.md](modules/PLATFORM-DEV.md) | Platform development (Next.js 16, auth, DB, Playwright) |
| [SHELL-GOTCHAS.md](modules/SHELL-GOTCHAS.md) | Shell pitfalls (echo newlines, Windows line endings, heredoc quoting) |
| [DETECTION.md](modules/DETECTION.md) | Standalone orchestrator-detection table; loaded by implementation-agent, deployer, and build-orchestrator |
| [DOC-GENERATION.md](modules/DOC-GENERATION.md) | Technical + client-facing docs; loaded by build-orchestrator Phase 4 |
| [BUILD-TEMPLATES.md](modules/BUILD-TEMPLATES.md) | Session summary, phase report, progress update, and build log templates |
