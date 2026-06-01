# Test fixture for agnt_intent-reviewer — clean baseline

This fixture pairs a clear directive user input with a tight plan that anchors on the user's words, surfaces strategy choices where they exist, and re-asks nothing already settled. The agent should return `OK`.

---

## Context

Recent conversation lines from this client thread (last 2 turns):

1. Gurmej (client) to Matthias, yesterday: "Send me the build update when you have a moment — no rush, end of week is fine."
2. Matthias to Gurmej, yesterday: "Will do, end of week."

The client has already defined:
- Recipient list scope: "the 983 past Moonlight & Mistletoe attendees only" (stated 4 days ago)
- Cadence: "3-touch sequence, one per week" (stated 4 days ago)
- Build-update deadline: "end of week"

---

## User input

Direct message from Matthias, 9:12am today:

> "Draft the build update for Gurmej. Cover the warm rebuild progress, the first sequence template draft, and the sender-domain warm-up status. Send it by end of Friday per his ask. Keep it short."

---

## Proposed plan

The build-orchestrator's Phase 1 spec output for this directive:

1. Compose a build update message to Gurmej covering three items: (a) warm rebuild progress against the 983 past Moonlight & Mistletoe attendees, (b) status of the Touch 1 draft for the 3-touch sequence, (c) sender-domain warm-up status (SPF/DKIM check today).
2. Length target: under 200 words. Matthias asked for "short."
3. Send by end of Friday per Gurmej's stated deadline ("end of week is fine").
4. No open items for Matthias on scope — recipient list, cadence, and deadline are all settled.
5. After drafting, route through `agnt_comms-critic` before showing to Matthias.

---

## Expected agent behavior

The agent should return `OK` and nothing else.

Reasoning (for human reviewers re-running this fixture):
- **I1**: User input is directive, not exploratory. No hedging. No exploratory-as-directive risk.
- **I2**: No illustrative examples in the user input. No example-as-spec risk.
- **I3**: Plan does not commit to a strategy beyond what the user directly asked for (cover three named items, short, by Friday). No strategic-bypass.
- **I4**: Plan step 4 explicitly notes recipient list / cadence / deadline are settled (no re-ask). All three were defined by the client in Context; the plan respects that.
- **I5**: Plan lifts the user's verbatim "983 past Moonlight & Mistletoe attendees", "3-touch sequence", "end of week / Friday" anchors. No paraphrase-drift.
- **I6**: Context is not a pushback (it's a no-rush status request). Plan adopts a neutral, deferential posture — appropriate.
- **I7**: No identity / capability / limitation claims in the plan.

The agent's output should be exactly the single line `OK`.
