# Lead-gen delivery kit

The client-agnostic version of the cold-and-warm outreach pipeline that
shipped for Meji. It exists so a new lead-gen engagement (a uwi-won client, or
a subcontractor running one under us) starts from a proven runbook instead of
re-deriving the mechanics per client.

Two things it is, and one it is not:

- **A runbook.** `pipeline-playbook.md` is the stage-by-stage operation, the
  safeguards, and the who-decides-what split, written so someone who is not
  the person who built it can run a week of the operation correctly.
- **A skeleton set** (as the kit fills in): client-agnostic script shapes for
  the load/verify/health-check steps, an Instantly API-client template, and
  genericized engagement docs. These land beside the playbook as they are
  extracted; see the u5 status file for what is built vs pending.
- **NOT a spec for a specific client.** Per-client facts (the audience, the
  cities, the seasonal peak, the mailboxes, the provider chosen) live in that
  client's own `context/`, never here. The kit is the invariant; the client
  folder is the variables.

## Source

Extracted 2026-07-25 from the Meji engagement, the reference build:
`workspace/clients/meji-media/deliverables/shared/` (outreach-scope,
outreach-technical-approach, onboarding-2-day-schedule, first-two-weeks,
handoff-package, transition-state-and-deliverables). The Meji-specific
artifacts stay client-scoped; this kit keeps only the shape.

## The invariant safeguards (never negotiated down)

These four are the fix for how cold outreach fails; they run on every
engagement regardless of client:

1. **Verify before send.** Every address passes email verification before it
   enters a sequence. Single biggest lever on bounce rate.
2. **Sample-approval gate (cold only).** No cold campaign sends until the
   client has seen and approved a real sample of the list (~100-200 contacts,
   with title/company/location visible).
3. **Sequence, never a single send.** Every campaign is a multi-touch sequence
   with reply-stop and bounce-drop running underneath it.
4. **Paced ramp.** Volume rises gradually; no cold-start spikes.

The invasive-action gate (`rule_instantly_invasive`, B5) and its readiness
audit sit on top of all of this: any real send is a per-action, owner-approved,
readiness-checked step, never autonomous.

## Geography fence

List sourcing for cold email is UK/US only; DE/DACH cold is legally fenced
(UWG §7) and reached through content, LinkedIn, or referral instead. This is
structural in the sourcing step, not a per-client choice.

## Contents

| File | What | State |
|---|---|---|
| `pipeline-playbook.md` | The 8-stage operation + safeguards + decision split | built 2026-07-25 |
| `script-skeletons/` | Instantly loader (delay-semantics audit), MX pre-filter, verify wrapper, campaign health-check | pending |
| `instantly-api-client/` | API-client template (the platform the reference build runs on) | pending |
| `engagement-docs/` | Genericized onboarding / first-two-weeks / scope / handoff | pending |

Backs `rule_project_status` workstream `u5-delivery-kit`. Related:
`reference_cold_email_gateway_bounces` (MX pre-filter),
`reference_instantly_sequence_delay_semantics` (gap on the earlier step).
