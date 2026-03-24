---
description: Draft a client message using project context and anti-AI style rules
argument-hint: <client-name> [message-type] [recipient]
---

# Draft Client Message

## Context
- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Process

1. **Parse arguments:**
   - `$1` = client name (required). If empty, ask the user.
   - `$2` = message type (optional). One of: status-update, info-request, blocker-notification, deliverable-handover, milestone, follow-up, technical-to-dev, scope-discussion, invoice-context, proposal, meeting-recap.
   - `$3` = recipient name (optional).

2. **Verify client exists:** Check that `workspace/clients/$1/` exists. If not, list available clients and ask.
   - Note: `/draft` only applies to `type: client` projects. If the project is found in `workspace/projects/` with `type: internal` or `type: platform`, stop with: "Client comms don't apply to `type: {type}` projects."

3. **Load the client-comms skill** and follow its 6-step process:
   - Load client profile (or set one up)
   - Determine message type (from $2, conversation context, or ask)
   - Load context files
   - Draft the message
   - Run sanity check
   - Present and iterate

4. **If the user provides context in the conversation** (e.g., "draft a message telling them the webhooks are set up"), use that as the message intent. Don't ask again for what they already told you.

## Examples

```
/draft meji-media                           # Infer type from context
/draft meji-media status-update             # Explicit type
/draft meji-media technical-to-dev Anuj     # Explicit type + recipient
```
