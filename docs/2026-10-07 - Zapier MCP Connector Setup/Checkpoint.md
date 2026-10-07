# Checkpoint: Zapier MCP Connector Setup

**Date:** 2026-10-07
**Status:** Blocked on a new conversation (connector live on the account, not loaded in this session)

---

## Summary
The owner connected the Zapier claude.ai connector mid-conversation, but this conversation's tool list was fixed before that, so `list-zapier-skills` and the onboarding skill could not run here; the demo moves to a fresh conversation.

---

## What Was Done This Session
### Zapier connector enumeration
1. Turn 1: three ToolSearch probes plus a config grep found no Zapier tools; prompted the owner to connect Zapier under claude.ai Settings → Connectors, then start a new conversation.
2. Turn 2 (owner had connected, same conversation): ToolSearch still found no Zapier tools. `claude mcp list` showed `claude.ai Zapier: https://mcp.zapier.com/api/v1/connect - ✔ Connected`, which separates "connected on the account" from "loaded in this session".
3. Weighed running the onboarding through a headless `claude -p` child (which would load the connector fresh) and rejected it, reasons below.

### System
1. Pattern rule `warn-grep-config-for-mcp-connector` (bash, warn): a grep of `~/.claude.json` for a connector is blind to claude.ai connectors; points at `claude mcp list`. Tested: fires on the incident command, quiet on `claude mcp list | grep` and `cat ~/.claude.json`.

---

## Key Decisions Made
### No headless child session for the onboarding
- **Choice:** Hand the run to a new conversation instead of a `claude -p` subprocess.
- **Rationale:** The onboarding asks the owner which apps to use and the live demo writes into real apps; a headless child can neither ask mid-run nor stop for the per-action yes those writes need.

### Demo stays off Brisken M365
- **Choice:** Build the Zapier demo on the owner's non-Brisken apps.
- **Rationale:** rule_brisken_graph_first routes Brisken mail/calendar through the Graph app only, and rule_brisken_graph_send_by_id restricts sends; a Zapier Outlook action on Brisken would bypass both.

---

## What Did NOT Work (and why)
- **Grepping `~/.claude.json` / `.mcp.json` for "zapier":** claude.ai connectors are account-side and never appear in local config files, so the probe can only ever return a negative.
- **ToolSearch for Zapier after the owner connected it:** the running conversation's MCP tool set is fixed at start; a connector added later shows Connected in `claude mcp list` but exposes no tools to this session.
- **`gh pr create --repo` without the `.01` suffix (checkpoint ship):** gh answered "Head sha can't be blank / No commits between"; the slug is `011matthias/agentic-ops1.01` (reference_repo_tooling_gotchas.md). The `warn-gh-repo-slug-missing-01` rule fired but a warn does not stop the call.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/patterns/warn-grep-config-for-mcp-connector.md` | Created | Warn on config-grep connector checks; name `claude mcp list` |
| `docs/2026-10-07 - Zapier MCP Connector Setup/Checkpoint.md` | Created | This checkpoint |

---

## Current Status
Zapier connector is connected on the account and healthy per `claude mcp list`. Nothing has been read from or written to any Zapier-connected app yet. No client scope touched (no ops status or comms lines apply).

---

## Next Steps
1. Owner starts a new conversation and repeats the request; there, call `list-zapier-skills`, load the onboarding skill, follow it.
2. During the demo: reads run freely; every write (send, create, post) gets an explicit per-action yes first; Brisken M365 stays out.

---

## Context for Next Session
### Files to Read First
- `.claude/rules/rule_brisken_graph_first.md` (only if the owner's connected apps include Brisken Outlook/Calendar)

### Open Questions
- Which apps the owner has connected inside Zapier (unknown until `list-zapier-skills` / the onboarding runs).

### Working Notes
- `claude mcp list` is the authoritative enumeration: it lists claude.ai connectors (prefixed `claude.ai`) with health, independent of what the current conversation loaded.

### Reference Materials
- Zapier MCP endpoint per `claude mcp list`: `https://mcp.zapier.com/api/v1/connect`

---

## How to Continue
Open a new Claude Code conversation, confirm Zapier tools appear via ToolSearch (`zapier`), then run the onboarding skill the list-skills tool returns. No `/resume` scope needed; this is system-level.

---

## Strategic Feedback

### What Worked Well This Session
- `claude mcp list` resolved the turn-2 question in one call: it showed the connector live on the account, so the diagnosis was "session not reloaded" rather than "connector broken".

### Suggestions
- Run `claude mcp list` first for any "is connector X available" question, before ToolSearch or config greps; the new pattern rule nudges toward it.

### System Health
- Autonomy: 1 human intervention (the Zapier OAuth connect, which only the owner can do). Gates: B1:2 B2:0 B3:1 skipped:0.
