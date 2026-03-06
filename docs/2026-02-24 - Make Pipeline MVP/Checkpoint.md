# Checkpoint: Make Pipeline MVP

**Date:** 2026-02-24
**Status:** MVP pipeline built, pending MCP credentials from client

---

## Summary
Built the MVP Make.com production pipeline for the agentic ops system — from zero Make.com tooling (0 skills, manual-only build module) to a full MCP-driven pipeline with 2 dedicated skills, a rewritten build module, and updated commands/rules. Also onboarded Meji Media client context and switched their folder from Trigger.dev to Make.com.

---

## What Was Done This Session

### Client Context (Meji Media)
1. Created `workspace/clients/meji-media/context/process-notes.md` — full client brief from Upwork chat (contacts, systems, problem statement, architecture decision, blockers, contract, original job description)
2. Updated `workspace/clients/meji-media/context/README.md` — filled in all TBD fields

### Client Config (Trigger.dev → Make.com)
3. Deleted all Trigger.dev boilerplate from `workspace/clients/meji-media/automations/` (~15 files)
4. Created `workspace/clients/meji-media/automations/README.md` — Make.com scenarios index
5. Created `workspace/clients/meji-media/automations/blueprints/.gitkeep` — blueprint version control dir
6. Created `workspace/clients/meji-media/infrastructure.yaml` — `type: make` instance entry
7. Updated `workspace/clients/meji-media/context/README.md` — orchestrator changed to Make.com

### New Skills (0 → 2)
8. Created `.claude/skills/make-mcp-tools-expert/SKILL.md` — MCP server setup (SSE + npm options), tool categories, scenario workflows, connection management, REST API fallback
9. Created `.claude/skills/make-mcp-tools-expert/modules/BLUEPRINT-FORMAT.md` — complete Make.com blueprint JSON schema (modules, routers, filters, mappers, error handlers, functions, full example)
10. Created `.claude/skills/make-scenario-patterns/SKILL.md` — 5 core patterns, module selection guide, Meji Media-specific A1/A2/A3 scenario patterns

### Updated Existing Files
11. Rewrote `.claude/skills/build/modules/MAKE-BUILD.md` — from manual-only to MCP-driven pipeline (architecture → connections → blueprint generation → deploy → test → activate)
12. Updated `.claude/skills/build/SKILL.md` — Make.com section references new skills
13. Updated `.claude/rules/automation-types.md` — Make.com section reflects MCP capability + blueprints folder
14. Updated `.claude/commands/make-instances.md` — added MCP server entry setup instructions
15. Updated `.claude/commands/new-client.md` — Make.com branch includes blueprints dir + MCP setup
16. Updated `CLAUDE.md` — skills table includes 2 new Make.com skills

---

## Key Decisions Made

### Make.com MCP Server Discovery
- **Choice:** Use Make.com's official MCP server for programmatic scenario management
- **Rationale:** Discovered Make.com has an official MCP server (https://developers.make.com/mcp-server) supporting SSE transport. This enables a pipeline similar to n8n's MCP-driven approach, rather than manual UI-only building.

### SSE Transport (Cloud-Hosted)
- **Choice:** Recommend SSE via `mcp-remote` over legacy npm package
- **Rationale:** The cloud-hosted version has management tools (create/update scenarios) on paid plans. Legacy `@makehq/mcp-server` npm package is marked as legacy and only supports scenario run tools.

### Architecture Decision: Option A (Lightweight Tracking Table)
- **Choice:** Client's CRM stays as-is, separate tracking table (Airtable/Google Sheets) manages follow-up state
- **Rationale:** Meji Media chose this over full CRM integration ($350 vs $800 scope). CRM remains untouched; tracking table handles step, timing, stopped flag, priority/score.

### Blueprint JSON as Code
- **Choice:** Generate Make.com blueprint JSON from specs, deploy via MCP
- **Rationale:** Blueprints are standard JSON that can be version-controlled, imported/exported, and programmatically generated. This matches the spec-driven philosophy.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/process-notes.md` | Created | Full client brief from chat + Upwork job description |
| `workspace/clients/meji-media/context/README.md` | Modified | Filled TBD fields, changed orchestrator to Make.com |
| `workspace/clients/meji-media/automations/README.md` | Created | Make.com scenarios index (replaced Trigger.dev) |
| `workspace/clients/meji-media/automations/blueprints/.gitkeep` | Created | Blueprint version control directory |
| `workspace/clients/meji-media/infrastructure.yaml` | Created | Make.com instance tracking entry |
| `workspace/clients/meji-media/automations/` (Trigger.dev files) | Deleted | Removed ~15 Trigger.dev boilerplate files |
| `.claude/skills/make-mcp-tools-expert/SKILL.md` | Created | MCP tools guide for Make.com |
| `.claude/skills/make-mcp-tools-expert/modules/BLUEPRINT-FORMAT.md` | Created | Blueprint JSON schema reference |
| `.claude/skills/make-scenario-patterns/SKILL.md` | Created | Make.com scenario architecture patterns |
| `.claude/skills/build/modules/MAKE-BUILD.md` | Rewritten | MCP-driven pipeline (was manual-only) |
| `.claude/skills/build/SKILL.md` | Modified | Make.com section references new skills |
| `.claude/rules/automation-types.md` | Modified | Make.com MCP capability + blueprints folder |
| `.claude/commands/make-instances.md` | Modified | Added MCP server setup instructions |
| `.claude/commands/new-client.md` | Modified | Make.com branch + blueprints dir + MCP setup |
| `CLAUDE.md` | Modified | Added 2 new skills to table |

---

## Current Status
The MVP Make.com pipeline is fully built within the agentic ops system. All skills, rules, commands, and client config are in place. **Blocked on MCP credentials from Meji Media** — need their MCP token and Make.com zone to create `.mcp.json` and verify tools work.

---

## Next Steps
1. **Get MCP credentials from Meji Media** — MCP token from Make.com Profile → API/MCP access, and their zone (us1/eu1/eu2)
2. **Create `.mcp.json`** — with `make-meji-media` MCP server entry, verify tools are accessible
3. **Create first spec** — run `/spec-creator` for the A1 enquiry follow-up automation (pattern already documented in `make-scenario-patterns`)
4. **Get remaining operational details from client** — outreach cadence, email templates/voice, priority thresholds
5. **Generate first blueprint** — use the pipeline end-to-end: spec → blueprint JSON → deploy via MCP

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/process-notes.md` — full client brief and blockers
- `.claude/skills/make-scenario-patterns/SKILL.md` — Meji Media A1/A2/A3 pattern
- `.claude/skills/make-mcp-tools-expert/SKILL.md` — MCP setup instructions
- `.claude/plans/foamy-tumbling-lobster.md` — original implementation plan

### Open Questions
- What is Meji Media's Make.com zone? (us1, eu1, eu2)
- Does Meji Media have a paid Make.com plan with API/MCP access?
- Outreach speed/frequency guardrails still needed from client
- Follow-up cadence by priority still needed
- Email templates/voice for "human-looking" emails still needed
- Google Sheets vs Airtable for tracking table — final decision pending

### Reference Materials
- Make.com MCP Server docs: https://developers.make.com/mcp-server
- Make.com MCP Server GitHub: https://github.com/integromat/make-mcp-server
- Make.com API docs: https://developers.make.com/api-documentation/api-reference/scenarios

---

## How to Continue
Read `workspace/clients/meji-media/context/process-notes.md` for the full client brief. The pipeline is built — next step is getting MCP credentials from the client to connect to their Make.com instance, then creating the first automation spec with `/spec-creator`. The `make-scenario-patterns` skill already has the Meji Media A1/A2/A3 patterns documented.
