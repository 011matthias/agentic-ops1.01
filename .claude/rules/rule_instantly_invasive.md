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
3. **Pre-execution readiness check (automatic, after the yes, before the mutation).** A clear yes authorizes the action; it does not prove the action is correctly set up. Before firing the mutating call, run the read-only readiness audit in the next section against the live account and the canonical routing, and report the result in one short pass/fail block. All green: proceed. Any fail or unknown: surface it plainly and fix or re-confirm first, never execute on a failed check. This closes the gap between "approved" and "actually ready", and catches a forgotten precondition before it reaches real recipients.
4. Only after a clear yes AND a green readiness check, execute. If the user's yes is ambiguous or partial, ask again rather than assume.

This is consistent with the ship-gate's no-undo exception in `rule_behaviors.md`: invasive Instantly actions are high-blast-radius and irreversible (real emails to real recipients, sender-reputation damage), so they always pause for explicit confirmation, never proceed on inferred approval.

## Pre-activation readiness check (the automatic last check)

The audit is entirely read-only (GET / read-style POST), so it runs under autonomy and MUST run every time, immediately after approval and before the mutating call. It verifies that the specific preconditions of THIS action are actually true, not assumed. Report a short pass/fail block; a single fail pauses execution.

For a campaign go-live (activate / start sending), verify against the live API and `context/pilot-routing.md`:

- **Right campaign.** The campaign id is the intended one, not a legacy / superseded campaign; the name matches what was approved.
- **Senders.** `email_list` is exactly the mailboxes that belong to this piece per the pilot-routing hard rules (no cross-wire from another piece's domain); each sender is `warmup_status=1`, has a `daily_limit` set, and is active.
- **Sequence.** Step count matches the approved copy; per-step `delay` puts the gap on the EARLIER step (the 2026-06-09 double-send fix); per-lead merge vars resolve from the lead `payload` (no null venue / city / first-name); no stale `{{icebreaker}}` gate.
- **Leads.** Loaded count matches the approved list; deduped against every other live piece (no lead gets two campaigns); verified-only / bounce-safe (NeverBounce the bounce-prone segments); geography matches the piece's scope (e.g. P3 is the 3 venue cities only, mis-located records dropped).
- **Settings.** Stop-on-reply on, bounce-protection on, sending window correct, unsubscribe header per house style.
- **Cost + capacity.** Apollo credit cost noted; daily cap is sane against the list size and the September peak.

For other invasive actions (bulk lead delete, mailbox / sending-limit change, sequence edit), the same principle applies: enumerate the specific preconditions of THAT action and confirm each is actually true before firing. The general rule is verify-the-preconditions, not just re-read-the-request. Added 2026-06-20 on user direction: once an invasive action is approved, automatically confirm the thing is really ready to go live before firing, rather than trusting that approval implies correctness.

**Enforcement.** `.claude/hooks/instantly-invasive-gate.py` (PreToolUse:Bash) is the structural backstop: it intercepts mutating `api.instantly.ai` calls and forces a permission stop. The hook is a tripwire, not a substitute for the protocol above; the plain-language scope-of-effects explanation AND the post-approval readiness check are both mandatory before any invasive call is executed. The hook fires on the same mutating call whether or not the readiness check ran, so the check is agent discipline, not hook-enforced. Skipping either half of the protocol = friction event (`skipped-gate`, B5).
