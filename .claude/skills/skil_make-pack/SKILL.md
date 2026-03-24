---
name: make-pack
description: Consolidated Make.com skill pack. Use when building, editing, testing, or debugging Make.com scenarios. Replaces make-mcp-tools-expert, make-scenario-patterns, webhook-inspector, and blueprint-reconciler. Load modules individually per task.
---

# Make.com Pack

Unified reference for building Make.com scenarios. Consolidates: make-mcp-tools-expert, make-scenario-patterns, webhook-inspector, blueprint-reconciler.

---

## Build Procedure

1. **Detect** — Confirm Make.com orchestrator (`infrastructure.yaml` has `type: make`)
2. **Read spec** — Extract flow, systems, edge cases, acceptance criteria
2.5. **Estimate ops** — For each scenario, estimate monthly operations before building. Scheduled: `(2,592,000 / interval_seconds) × modules_in_flow`. Webhook: `events_per_month × modules_in_flow`. Compare total against client's Make.com plan — if projected > 80% of limit, flag before building. Load [OPERATIONS-ANALYZER](../make-mcp-tools-expert/modules/OPERATIONS-ANALYZER.md) Section A for full estimation procedure.
3. **List connections** — Verify auth connections exist for required services
4. **Generate blueprint** → Load BLUEPRINT module for JSON format
5. **Deploy** — Try MCP `scenarios_update` first; fall back to `uv run tools/make-api.py update|deploy` or UI import if MCP fails.
6. **Post-deploy binding check** — Load [POST-DEPLOYMENT-VERIFICATION](../make-mcp-tools-expert/modules/POST-DEPLOYMENT-VERIFICATION.md) after API deployment. Alert user to rebind data store/connection modules in UI.
7. **Verify** — Test with Run Once, check execution inspector
8. **Activate** — Enable scheduling or webhook listening

---

## Critical Rules (Always Apply)

- **Check API impossibilities FIRST** — Before attempting any API approach, load [API-IMPOSSIBILITIES](../make-mcp-tools-expert/modules/API-IMPOSSIBILITIES.md). Gmail/OAuth scenarios cannot be made functional via API alone. State UI requirements in your FIRST response — do not iterate.
- **MCP blueprint deployment may work** — `scenarios_update` with blueprint param succeeded for A3 on 2026-03-14 after previously failing with 500. Test each deployment; fall back to REST API (`tools/make-api.py`) or UI import if it fails.
- **Module name casing matters** — `datastore:AddRecord` (capital A), not `datastore:addRecord`
- **Connection IDs are instance-specific** — cannot copy between orgs
- **Blueprint as JSON string** for REST API (MCP may auto-stringify)
- **Key terminology (vs n8n):** Scenario=Workflow, Module=Node, Route=Connection, Connection=Credential, Router=IF/Switch

---

## Module Index

Load ONE module at a time based on your current task.

### Procedure Modules

| When | Module | Source |
|------|--------|--------|
| Generating blueprint JSON | [BLUEPRINT-FORMAT](../make-mcp-tools-expert/modules/BLUEPRINT-FORMAT.md) | make-mcp-tools-expert |
| Setting up a new project | [PROJECT-SETUP](../make-mcp-tools-expert/modules/PROJECT-SETUP.md) | make-mcp-tools-expert |
| Testing webhooks | [WEBHOOK-TESTING](../make-mcp-tools-expert/modules/WEBHOOK-TESTING.md) | make-mcp-tools-expert |
| Diagnosing scenario failures | [AUTONOMOUS-DIAGNOSTICS](../make-mcp-tools-expert/modules/AUTONOMOUS-DIAGNOSTICS.md) | make-mcp-tools-expert |
| Verifying execution outcomes | [POST-EXECUTION-VERIFICATION](../make-mcp-tools-expert/modules/POST-EXECUTION-VERIFICATION.md) | make-mcp-tools-expert |
| After API blueprint deployment | [POST-DEPLOYMENT-VERIFICATION](../make-mcp-tools-expert/modules/POST-DEPLOYMENT-VERIFICATION.md) | make-mcp-tools-expert |
| Iterating on fixes | [ITERATION-CYCLE](../make-mcp-tools-expert/modules/ITERATION-CYCLE.md) | make-mcp-tools-expert |
| Adding/modifying data store fields | [SCHEMA-EVOLUTION](../make-mcp-tools-expert/modules/SCHEMA-EVOLUTION.md) | make-mcp-tools-expert |
| Discovering webhook payloads | [WEBHOOK-PAYLOAD-INSPECTOR](../make-mcp-tools-expert/modules/WEBHOOK-PAYLOAD-INSPECTOR.md) | make-mcp-tools-expert |
| Pre-handover checklist | [PRE-CLIENT-REVIEW](../make-mcp-tools-expert/modules/PRE-CLIENT-REVIEW.md) | make-mcp-tools-expert |
| Cross-validating blueprint vs data stores | [DATA-STORE-RECONCILER](../blueprint-reconciler/modules/DATA-STORE-RECONCILER.md) | blueprint-reconciler |
| Validating Sheets column refs | [SHEETS-COLUMN-RECONCILER](../blueprint-reconciler/modules/SHEETS-COLUMN-RECONCILER.md) | blueprint-reconciler |
| Checking IML `{{N.field}}` refs | [IML-REFERENCE-CHECKER](../blueprint-reconciler/modules/IML-REFERENCE-CHECKER.md) | blueprint-reconciler |
| Validating email template placeholders | [TEMPLATE-PLACEHOLDER-CHECKER](../blueprint-reconciler/modules/TEMPLATE-PLACEHOLDER-CHECKER.md) | blueprint-reconciler |
| Pre-handover blueprint format check | [HANDOVER-FORMAT-CHECKER](../blueprint-reconciler/modules/HANDOVER-FORMAT-CHECKER.md) | blueprint-reconciler |
| Capturing webhook payloads | [CAPTURE-PATTERN](../webhook-inspector/modules/CAPTURE-PATTERN.md) | webhook-inspector |
| Analyzing captured payloads | [ANALYZE-PAYLOAD](../webhook-inspector/modules/ANALYZE-PAYLOAD.md) | webhook-inspector |
| Estimating or analyzing operations costs | [OPERATIONS-ANALYZER](../make-mcp-tools-expert/modules/OPERATIONS-ANALYZER.md) | make-mcp-tools-expert |
| Onboarding platform feasibility check | [PLATFORM-FEASIBILITY](../make-mcp-tools-expert/modules/PLATFORM-FEASIBILITY.md) | make-mcp-tools-expert |
| Before attempting any API approach | [API-IMPOSSIBILITIES](../make-mcp-tools-expert/modules/API-IMPOSSIBILITIES.md) | make-mcp-tools-expert |

### Reference Modules (load ONLY for specific lookups)

| When | Module | Source |
|------|--------|--------|
| IML expression error | [IML-GOTCHAS](../make-mcp-tools-expert/modules/IML-GOTCHAS.md) | make-mcp-tools-expert |
| Known webhook provider formats | [KNOWN-PROVIDERS](../webhook-inspector/modules/KNOWN-PROVIDERS.md) | webhook-inspector |

---

## Scenario Architecture Patterns (from make-scenario-patterns)

| Pattern | Trigger | Use When |
|---------|---------|----------|
| Webhook Processing | `gateway:CustomWebhook` | Form submissions, CRM events, payment hooks. Set `instant: true`. Always send `WebhookResponse`. |
| Scheduled Sequence | `builtin:BasicScheduler` | Follow-ups, batch processing, periodic syncs. Use `Sleep` inside iterators. |
| Email + Reply Detection | `gmail:watchEmails` | Monitoring inbox, stopping follow-ups on reply. Update tracking immediately. |
| Conditional Branching | `builtin:BasicRouter` | Different actions by lead value/type/urgency. Routes evaluated in order; last = fallback. |
| Data Sync | Scheduler or Watch | Keeping two systems in sync. Use `searchRows` before `addRow` to prevent duplicates. |

---

## MCP Server Setup

```json
{
  "mcpServers": {
    "make-{client}": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<ZONE>/mcp/u/<TOKEN>/sse"]
    }
  }
}
```

## Known API Limitations

- No module-level I/O for successful executions — `executions_get_detail` returns status + counts ONLY, not module output values. Workaround: add a temporary `datastore:AddRecord` module after the step you want to inspect; read it back via `data-store-records_list`. This is the **data store write-back pattern** — the only way to surface intermediate values autonomously. Do NOT waste operations guessing via repeated scenario runs.
- No sheet cell reading via MCP RPCs — use direct Google Sheets API
- `validate_blueprint_schema` validates API format only — not UI import format. Run HANDOVER-FORMAT-CHECKER before handover.
- **Blueprint deployment tool:** `uv run tools/make-api.py {update|deploy|get|list|ds-upsert|scenario-run}` — full REST API wrapper that bypasses MCP 500 errors on blueprint params.
- **Email template import:** `uv run tools/docx-to-datastore.py {extract|validate|upload}` — converts .docx email templates to data store records. Validates `##placeholder##` patterns.
