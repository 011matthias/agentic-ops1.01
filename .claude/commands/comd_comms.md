---
description: Process client replies, view conversation history, or check open items
argument-hint: <client-name> <inbound|log|status>
---

# Client Communication Management

## Context
- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Process

1. **Parse arguments:**
   - `$1` = client name (required). If empty, ask the user.
   - `$2` = subcommand (required). One of: `inbound`, `log`, `status`.

2. **Verify client exists:** Check that `workspace/clients/$1/` exists. If not, list available clients and ask.
   - Note: `/comms` only applies to `type: client` projects. If the project is found in `workspace/projects/` with `type: internal` or `type: platform`, stop with: "Client comms don't apply to `type: {type}` projects."

3. **Load the client-comms skill** and execute based on subcommand:

### `inbound` — Process Client Response

Load and follow the INBOUND-PROCESSING.md module:
1. Accept pasted chat content or description from the user
2. Deduplicate against existing comms-log entries
3. Detect time gaps since last logged contact
4. Extract decisions, facts, action items, questions
5. Sanity check client statements against project state
6. Identify implications (spec, infrastructure, scope)
7. Suggest next actions
8. Offer to log (ask before writing)

If the user wants to reply after processing, suggest: "Want me to draft a reply? I'll use `/draft` with this context."

### `log` — View Conversation History

Read `workspace/clients/$1/context/comms-log.md` and present:
1. All entries in chronological order (summarized if long)
2. Highlight unresolved open items
3. Note last contact date and who spoke last

If no comms-log exists, say so and offer to create one.

### `status` — Quick Overview

Read `workspace/clients/$1/context/comms-log.md` and present a concise summary:
1. **Last contact:** date + direction + who
2. **Unresolved items:** list with assigned contacts and age (days since asked)
3. **Recent decisions:** from last 2 weeks
4. **Staleness tier:**
   - OK (0-3 days) — no action needed
   - NOTICE (4-7 days) — mention in passing
   - STALE (8-14 days) — suggest: "Consider `/draft {client} follow-up`"
   - URGENT (15+ days) — flag prominently: "No contact in {N} days. Send a follow-up."

## Examples

```
/comms meji-media inbound              # Process a client reply (then paste it)
/comms meji-media log                  # View conversation history
/comms meji-media status               # Quick overview of open items
```
