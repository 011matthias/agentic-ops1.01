---
description: Save conversation checkpoint for session continuity. Enables seamless handoff between agent sessions.
argument-hint: [topic-name]
---

Create a checkpoint that captures the current conversation state for future session continuity.

The mechanical half (folder, session log, INDEX row, context YAML, register rows) is done by `tools/checkpoint_scaffold.py` in two calls. You author exactly ONE prose artifact (the checkpoint file) plus a compact payload; the script derives the session-log entry and YAML from the payload. Never Read `docs/INDEX.md` or `docs/friction-register.md` into context — the script edits them string-level, and the regression check is a targeted grep.

## 1. Determine Topic and Mode

1. If `$ARGUMENTS` is provided, use it as the topic name (title case, e.g. "Fortnox API Integration"). Otherwise infer from the session.
2. If `$ARGUMENTS` contains `--mini`: strip it; use **MINI mode** — skip the Friction Self-Audit, Gate Compliance Audit, Comms Staleness ask, and Strategic Feedback; use the Mini-Checkpoint Template. Mini still runs both scaffold calls (the YAML is critical for /resume).

## 2. Pre-flight (one call)

```
uv run tools/checkpoint_scaffold.py pre --clients {clients touched} --topic "{TOPIC}" [--mini] [--register-types {comma-separated friction types you expect to log}]
```

This prints everything the closing sections need:
- **Target path** for the checkpoint prose file (handles Mini-Checkpoint-{N} numbering)
- **Friction candidates** (the `session_state.py --list-candidates` drain)
- **Per-client ops status** from `infrastructure.yaml` (include the line in Current Status; if ORANGE/RED add "Run `/ops-audit {client}`" to Next Steps; if no `platform` section but the client uses an orchestrator, add a feasibility-assessment next step)
- **Comms staleness** per client (used in step 7)
- **Project-status check** results (used in step 6)
- **Register size advisory + regression rows** for the types you passed

## 3. Friction Self-Audit (full mode only)

Review the session for friction events. Include events already noted mid-session (per the friction logging rule in rule_behaviors.md) plus newly discovered ones.

**Candidates first.** For EACH candidate printed by `pre`, make the judgment call the hook cannot: **promote** to a register row (assign type + gate) if it was real friction, or **discard** if the gate fired correctly and the system worked (note the reason in the session-log entry's Friction line, do not promote). A candidate is NOT automatically friction. Then run `uv run tools/session_state.py --clear-candidates`.

**Conversation scan** for what the hooks cannot detect:
1. User corrections (redirected approach or goal)
2. User-performed tasks you could have done via fixtures/tools
3. Missed tools (asked the user for something `tools/`, fixtures, or MCP could do)
4. Invisible friction: slow paths, scope creep, verification theater, skipped gates
5. Intent misalignment / over-literal readings of exploratory input
6. Strategic gaps (built before questioning whether to build)
7. Infrastructure deferral (same manual fix suggested in 2+ checkpoints)

For each event record: **Type** (`agent-deferred`, `missed-tool`, `redundant-escalation`, `slow-path`, `scope-creep`, `verification-theater`, `skipped-gate`, `intent-misalignment`, `over-literal`, `strategic-gap`, `missed-memory-recall`, `infrastructure-deferred`), **Detected by** (user/agent), **Gate** (B1–B7 or none), **Fix** (`structural`/`memory`/`documented`/`ext-limit`).

**Regression check:** use the `pre` output's regression rows (or a targeted Grep on `docs/friction-register.md` — never a full Read). If a previous same-type entry was Resolved=Yes, mark the new row `Regression: Yes ({date} fix, {fix type} didn't hold)`. If fix = `memory`, note: "Fragile fix — consider structural alternative."

## 4. Gate Compliance Audit (full mode only)

1. Count instances where B1/B2/B3 fired, and any instance where a gate SHOULD have fired but didn't → `**Gates:** B1:{N} B2:{N} B3:{N} skipped:{N}`. Each skip is friction type `skipped-gate`, fix `structural`.
2. **Autonomy Score** = total human interventions this session. 0 → "fully autonomous session". >3 → "(elevated — run /system-dev to close gaps)". Goes in the checkpoint's System Health section and the payload's `autonomy` field.

## 5. Write the Checkpoint File (the ONE prose artifact)

Write to the target path from `pre`, using the template below (Mini template in mini mode). This is the only place session prose is authored — keep it dense (rule_anti_slop applies; Summary, What Was Done, Current Status, and Next Steps must not restate each other).

```markdown
# Checkpoint: [Topic Name]

**Date:** [TODAY]
**Status:** [Current Phase/Status]

---

## Summary
[1-2 sentence overview]

---

## What Was Done This Session
### [Category]
1. Item

---

## Key Decisions Made
### [Decision]
- **Choice:** What was decided
- **Rationale:** Why

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|

---

## Current Status
[Where things stand, incl. the ops status line from `pre`]

---

## Next Steps
1. [Priority action]

---

## Context for Next Session
### Files to Read First
- [path]

### Open Questions
- [Question]

### Working Notes
Findings and intermediate state expensive to re-derive: failed approaches (and why), partial results, best current hypotheses.

### Reference Materials
- [URL or path]

---

## How to Continue
[Brief instructions]

---

## Strategic Feedback

### What Worked Well This Session
- [Specific pattern]

### Suggestions
- [One actionable improvement]

### System Health
- [One observation; include the Autonomy score line]
```

### Mini-Checkpoint Template

```markdown
# Mini-Checkpoint: [Topic Name]

**Date:** [TODAY]
**Status:** [Current Phase/Status]
**Type:** mini

---

## Summary
[1-2 sentences]

## What Was Done
- [Item]

## Current Status
[Where things stand]

## Next Steps
1. [Priority]

## Files to Read First
- [path]
```

## 6. Project Status Update (status-of-elements)

For each touched client with a `status/` folder (see the `pre` check output): update the touched workstreams' `status/{spec-id}-{slug}.md` in place (element states, Next action, blockers, `updated:` = today); scaffold new workstreams (`uv run tools/project_status.py --client {c} --scaffold {slug} --group {g} --spec {id}`); delete shipped/abandoned ones (W1 §4). Resolve any stale/malformed flags `pre` reported. Include changed files in the payload's `built`/Files Modified.

For Make.com clients with `ship: true` scenarios, optionally reconcile live vs `infrastructure.yaml` (one `scenarios_list` call; skip silently if the MCP server is not connected — no spiral, no friction event). Update `infrastructure.yaml` inline on drift.

## 7. Comms Staleness (full mode only)

If `pre` reported any client's comms-log at 4+ days stale: ask once — "{client} comms log is {N} days old. Any conversations to log before closing out?" (Quick Capture per COMMS-LOG.md if yes.) Multiple stale clients → one combined ask.

## 8. Finalize (one call)

Build the payload and apply it:

```
uv run tools/checkpoint_scaffold.py finalize --payload .scratch/checkpoint-payload.json
```

Payload (write to `.scratch/` — gitignored):

```json
{
  "topic": "{TOPIC}", "date": "{YYYY-MM-DD}", "work_type": "{client-dev|system-infra|comms|misc}",
  "section": "{INDEX section: client name, or system/platform}",
  "mini": false,
  "projects": ["{client-id}"],
  "entry": {
    "focus": "{1-2 sentence summary — same content as the checkpoint Summary}",
    "built": "{key deliverables}",
    "friction": "{N — type (desc), ... or None}",
    "gates": "B1:{N} B2:{N} B3:{N} skipped:{N}",
    "autonomy": "{N} human interventions",
    "outcome": "{current status, one line}"
  },
  "friction_rows": [
    {"client": "{c}", "type": "{type}", "desc": "{description incl. gate + detected-by}", "resolved": "No", "fix": "{fix}", "regression": "{No | Yes (...)}"}
  ],
  "yaml_clients": {
    "{client-id}": {
      "orchestrator": "{n8n|make|trigger-dev|fastapi}",
      "active_specs": [{"id": "{id}", "stage": "{stage}", "name": "{name}"}],
      "next_steps": ["{priority 1}"],
      "open_questions": ["{q}"]
    }
  }
}
```

The script bumps the session-log frontmatter, appends the derived `### Session {N}` entry, inserts the INDEX row (URL-encoded), merges the context YAML (add/update touched clients, others preserved), and appends the register rows. In mini mode omit `friction_rows`/`gates`/`autonomy`.

**Register archive:** if `pre` printed the >200 KB advisory, also run `uv run tools/checkpoint_scaffold.py archive-register` so the split ships in the same docs PR as this checkpoint's ledger edits (rule_branch_isolation §1).

## 9. Confirm

Output the confirm line `finalize` printed (it is already URL-encoded and VSCode-clickable):

- Full: `Checkpoint saved → [Checkpoint.md](docs/{DATE}%20-%20{TOPIC}/Checkpoint.md)`
- Mini: `Mini-checkpoint saved → [Mini-Checkpoint-{N}.md](...)`
