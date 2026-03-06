---
name: testing-checklist
description: "DEPRECATED — FastAPI-only testing checklist. Current orchestrators (n8n, Make.com, Trigger.dev) have testing procedures in their spec templates."
---

# Testing Checklist (DEPRECATED)

This skill generates testing checklists for FastAPI automations only (`app/automations/{id}.py`). Since FastAPI is the legacy orchestrator and active clients use n8n, Make.com, or Trigger.dev, this skill is deprecated.

For current testing procedures, see:
- Make.com: `make-pack` → POST-EXECUTION-VERIFICATION module
- n8n: `n8n-pack` → POST-EXECUTION-VERIFICATION module
- Trigger.dev: `trigger-pack` → testing modules
