# Instantly Invasive-Action Gate (B5)

**Hard constraint.** Never take an invasive action in a client's live Instantly account unless the user has specifically asked for that exact action in the current conversation. General permission to "work on the build", "do what's best", or autonomy grants do NOT authorize invasive Instantly actions. Autonomy covers read-only work only.

## What counts as invasive (state-changing in the client's live sending system)

- Creating, starting, pausing, resuming, duplicating, or deleting a campaign
- Importing, adding, editing, moving, or deleting leads / contacts
- Creating or editing a sequence, schedule, or sending settings
- Sending, scheduling, or triggering any email (test sends included)
- Modifying mailboxes / email accounts, warm-up settings, or sending limits
- Editing the blocklist / suppression list
- Any `POST` / `PUT` / `PATCH` / `DELETE` to `api.instantly.ai` that changes data

## What is NOT invasive (allowed under autonomy)

- Reading campaigns, leads, lists, analytics, email events, account status
- `GET` calls, and read-style `POST` endpoints that only query (`/leads/list`, `/campaigns/analytics`)
- Exporting / counting data without modifying it

## Required response protocol when the user asks for an invasive action

Do NOT execute immediately. First respond with:

1. **Scope-of-effects, in plain human language.** No API jargon. Explain, so a non-technical reader fully understands:
   - What exactly will change, in concrete terms
   - Who it touches in the real world (e.g., "this sends a real email to ~1,900 real people", "this removes 300 contacts from the campaign")
   - What is reversible and what is not (sent emails cannot be unsent; deleted leads may not be recoverable)
   - Knock-on effects: sender-reputation / deliverability impact, Instantly credit cost, whether it could trip bounce-protection or pause a campaign, effect on the September peak
   - What stays unaffected (reassure where true)
2. **An explicit confirmation question:** ask, in plain words, whether the user is sure they want to proceed with this specific action, and wait for a clear yes.
3. Only after a clear yes, execute. If the user's yes is ambiguous or partial, ask again rather than assume.

This is consistent with the ship-gate's no-undo exception in `rule_behaviors.md`: invasive Instantly actions are high-blast-radius and irreversible (real emails to real recipients, sender-reputation damage), so they always pause for explicit confirmation, never proceed on inferred approval.

**Enforcement.** `.claude/hooks/instantly-invasive-gate.py` (PreToolUse:Bash|PowerShell) is the structural backstop: it intercepts mutating `api.instantly.ai` calls and forces a permission stop. The hook is a tripwire, not a substitute for the protocol above; the plain-language scope-of-effects explanation is still mandatory before any invasive call is attempted. Skipping the protocol = friction event (`skipped-gate`, B5).
