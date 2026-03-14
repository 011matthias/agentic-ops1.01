---
name: client-comms
description: Bidirectional client communication system. Drafts outbound messages with project context, anti-AI style rules, and feasibility checks. Processes inbound client responses to extract decisions, update project state, and maintain conversation continuity. Use when drafting messages, processing client replies, or managing client conversation history. Triggered by /draft (outbound) and /comms (inbound/log/status) commands.
---

# Client Communications

Bidirectional client communication system. Two entry points:

- **`/draft`** — Outbound: drafts context-aware, human-sounding messages with feasibility checks
- **`/comms`** — Inbound: processes client responses, manages conversation history, tracks decisions

Both read from and write to the **comms log** (`context/comms-log.md`) — the persistent per-client conversation record that bridges outbound and inbound flows.

## Outbound Process (`/draft`)

### 1. Load Client Profile

Read `workspace/clients/{client}/context/comms-profile.md`.

If it doesn't exist, run the profile setup: load and follow `prompts/client-profile-setup.md`, then write the result using `templates/comms-profile-template.md`.

### 2. Determine Message Type

If the user specified a type, use it. Otherwise, infer from conversation context:
- Talking about progress? `status-update`
- Need something from client? `info-request`
- Stuck waiting? `blocker-notification` or `follow-up`
- Shipping work? `deliverable-handover`
- Finished something big? `milestone`
- Talking to a developer? `technical-to-dev`
- Discussing new work? `scope-discussion` or `proposal`
- Billing period? `invoice-context`
- After a call? `meeting-recap`

If still unclear, ask the user.

### 3. Load Context

Follow [CONTEXT-LOADING.md](modules/CONTEXT-LOADING.md) to read the right files for this message type. Extract the relevant facts. This now includes the comms log for conversation continuity and temporal context.

### 4. Draft Message

Apply the structure from [MESSAGE-TYPES.md](modules/MESSAGE-TYPES.md) for the chosen type.

Apply ALL rules from [STYLE-RULES.md](modules/STYLE-RULES.md):
- Hard rules are non-negotiable (no em-dashes, no banned phrases, contractions, etc.)
- Soft rules use defaults from the comms profile (imperfection density, formality, length)
- Platform-specific formatting (no bullets on Upwork, etc.)
- Temporal opener rules (time since last contact determines greeting style)

### 5. Sanity Check + Feasibility

Before presenting the draft, run [SANITY-CHECK.md](modules/SANITY-CHECK.md):
- Verify all claims against project state
- Check names against comms profile
- Ensure no internal details leak to client
- For scope-discussion, proposal, or technical-to-dev: also run [FEASIBILITY-CHECK.md](modules/FEASIBILITY-CHECK.md) — quality gates, complexity flags, constraint checks
- Flag any warnings to the user alongside the draft

### 6. Present and Iterate

Present the draft. If there are sanity check or feasibility warnings, show them below the draft.

The user may ask to adjust: "shorter", "more casual", "add X", "remove the part about Y", "make it friendlier". Apply changes and re-run the style validation.

### 7. Auto-Log

After the user approves the final draft, automatically log it:

1. Auto-generate an outbound entry from the approved draft (follow [COMMS-LOG.md](modules/COMMS-LOG.md) outbound write procedure)
2. Extract open items (questions asked, things requested from client)
3. Show the log entry to the user: "Logged to comms history:" followed by the entry
4. Append to `context/comms-log.md` and update frontmatter

Do NOT ask "Want me to log this?" — outbound drafts are always logged. The system created the message; the system logs it.

## Inbound Process (`/comms`)

For processing client responses, viewing conversation history, and managing open items, see the `/comms` command. The inbound processing procedure is defined in [INBOUND-PROCESSING.md](modules/INBOUND-PROCESSING.md).

## Modules

| Module | Purpose |
|--------|---------|
| [STYLE-RULES.md](modules/STYLE-RULES.md) | Anti-AI patterns, formatting, temporal openers, humanization rules |
| [MESSAGE-TYPES.md](modules/MESSAGE-TYPES.md) | Templates and structure per message type |
| [CONTEXT-LOADING.md](modules/CONTEXT-LOADING.md) | Which files to read and what to extract (incl. comms log + temporal context) |
| [SANITY-CHECK.md](modules/SANITY-CHECK.md) | Accuracy validation before presenting draft |
| [FEASIBILITY-CHECK.md](modules/FEASIBILITY-CHECK.md) | Quality gates + complexity flags for scope/proposal messages |
| [COMMS-LOG.md](modules/COMMS-LOG.md) | Persistent conversation record format, read/write procedures |
| [INBOUND-PROCESSING.md](modules/INBOUND-PROCESSING.md) | Client response processing: dedup, decisions, implications |

## Prompts

| File | Purpose |
|------|---------|
| [client-profile-setup.md](prompts/client-profile-setup.md) | Questions for creating a new client comms profile |

## Templates

| File | Purpose |
|------|---------|
| [comms-profile-template.md](templates/comms-profile-template.md) | Template for `context/comms-profile.md` |
