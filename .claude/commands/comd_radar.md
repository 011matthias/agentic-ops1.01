---
description: Opportunity radar for a client - weekly light pass or biweekly multi-agent deep sweep. Finds leaks, gaps, and ROI opportunities from live state; scores them; maintains the candidate ledger.
argument-hint: "{client} [light|deep]"
---

# Opportunity Radar

Systematic opportunity finding for a client engagement. The method lives in the
client's own files (all under `workspace/clients/{client}/`):

- `context/weekly-review-blueprint.md` sec J - lens catalog (J1), scoring
  rubric (J2), cadence + ledger contract (J3)
- `context/opportunity-radar.md` - the candidate ledger (funnel states:
  candidate / promoted / rejected / watch)
- `context/analysis-scripts/` engine with a `--radar` mode (deterministic feeds)
- `status/ops-radar.md` - method-state anchor (tracked, value-free)

If the client has no sec-J / ledger, stop and say so; instantiate them from the
meji-media precedent first.

## Mode: light (default) - the weekly ~2h pass

1. Run the client's engine with `--radar` (python, from its own directory).
2. Complete the review judgment layers (E-I) plus the J pass: score each
   section-R candidate per J2, disposition into the ledger (update in place,
   bump `last_light_pass`).
3. Work the always-on lenses (J1) plus ONE rotating deep lens; pick the least
   recently visited.
4. Execute the autonomous (gate 1) top items now. Batch every gate-2 item into
   ONE owner-decision block at the end (B5: plain-language scope-of-effects per
   item; never execute on inferred approval). Gate-4 items go to the comms
   plan, never directly to the client.
5. Promote / reject / watch per J2 dispositions; promoted items are copied into
   `context/next-outbound-deliverables.md` with their RAD-ID.
6. Hard ceiling 2h. Over it two weeks running: cut lenses, do not extend hours.

## Mode: deep - the biweekly multi-agent sweep

Invoke the `opportunity-radar` workflow (Workflow tool, `name:
"opportunity-radar"`) with args `{client: "{client}", date: "{today
YYYY-MM-DD}", agents: 12}`. Typing this command is the user's opt-in to the
multi-agent run. The workflow is read-only against live systems, adversarially
verifies its own brief, writes `context/weekly-reviews/{date}-deep-sweep.md`,
updates the ledger, and stops at the commit boundary (B6).

After it returns: read the brief, execute the autonomous top items, surface the
gated block, and set the next sweep date in the ledger frontmatter.

## Boundaries (both modes)

- Read-only against live systems throughout; mutations only via an explicit
  per-action owner yes (B5 / rule_instantly_invasive).
- Never draft client outbound from radar output
  (feedback_no_unrequested_client_drafts); radar findings reach the client only
  through the weekly report lane.
- Scores are internal-only ranking aids; never put a score or an unsourced
  claim in anything client-facing (B4).
- Ledger discipline: update in place, no dated snapshots, prune per the
  ledger's own lifecycle rules (W1 supersession).
