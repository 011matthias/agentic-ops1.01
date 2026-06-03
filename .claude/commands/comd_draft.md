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

3. **Pre-flight context load (mandatory, before drafting).** Closes the 2026-05-25 over-iteration class (register #120, #124) and the cost-anchor-drift class (#121). Don't draft until these are loaded:
   - Read the LAST 25 entries of `workspace/clients/$1/context/comms-log.md`. Quote the most recent 3 client messages verbatim in your own response so the agent's draft anchors on the client's actual words (per `feedback_anchor_on_clients_words`).
   - Read every open draft in `workspace/clients/$1/context/drafts/*.md`. If one already addresses the same topic, EDIT it; do not create a parallel draft.
   - Extract every cost figure (£/$/€ + per year/month/etc.) committed in the last 60 days. Surface them in a one-line "Prior commitments:" header so any new figure can be checked against them (the cost-anchor-drift gate in validate-output.py will also flag this at write-time).
   - Identify any client questions in the recent thread that are still UNANSWERED. If your draft would skip one, name the skip explicitly before drafting.

4. **Load the client-comms skill** and follow its 6-step process:
   - Load client profile (or set one up)
   - Determine message type (from $2, conversation context, or ask)
   - Load context files
   - Draft the message (write it to `workspace/clients/$1/context/drafts/{slug}.md`)
   - Run sanity check
   - Do NOT present yet — go to step 5 first

5. **Critic pass (mandatory, before showing the draft to the user).** Spawn the `agnt_comms-critic` agent to audit the draft against comms feedback memories and the live thread. Closes the memory-doesn't-hold class (register #84, #85, #108, #120, #121, #124) by adding a structural second-agent gate above the memory layer. The critic does not edit; it returns OK or a numbered fix list.

   Use the Task tool:

   ```text
   Launch agent: agnt_comms-critic

   Prompt:
   Audit the draft at {absolute path to draft file} for client {$1}.
   Read it, read the last 60 lines of workspace/clients/{$1}/context/comms-log.md,
   load the standard set of comms feedback memories, and return findings
   in your strict output shape (OK or numbered list).
   ```

   Apply the critic's output:
   - If `OK`: proceed to step 6.
   - If a fix list: apply each finding with ONE edit pass. After the pass, do NOT re-invoke the critic — proceed to step 6. The critic is a single-pass gate, not an iterative loop (register #120: the third-revision stop-gate still applies and the critic itself counts as a revision attempt).
   - If the critic returns the `[HIGH] [invocation]` shape: fix the invocation (likely a missing path) and re-launch ONCE.

6. **Present the draft to the user**, including a one-line summary of what the critic flagged and what you changed (e.g., "Critic flagged 2 (unanswered-question, pre-concession) — fixed inline.").

7. **If the user provides context in the conversation** (e.g., "draft a message telling them the webhooks are set up"), use that as the message intent. Don't ask again for what they already told you.

8. **Third-revision stop-gate.** If you find yourself producing a third revision of the same draft in one session (per register #120), STOP. State: "This is revision 3 of the same draft. Surfacing the upstream confusion instead of iterating: {what's actually being negotiated / what constraint shifted}." Do not draft revision 4 without user input on the framing. The critic-fix pass in step 5 counts as a revision.

## Examples

```
/draft meji-media                           # Infer type from context
/draft meji-media status-update             # Explicit type
/draft meji-media technical-to-dev Anuj     # Explicit type + recipient
```
