---
project: upwork-independence
workstream: u5-delivery-kit
group: uwi
spec:
state: active
updated: 2026-07-25
general_ref: status/uwi-general.md
---

# uwi / u5 — Lead-gen delivery kit (meji extraction)

The proven cold-outreach-as-a-service pipeline (list-build -> Apollo enrich ->
NeverBounce -> copy -> Instantly campaign -> weekly review) exists ONLY as
meji-specific gitignored context artifacts. Extracting it into
`workspace/templates/leadgen-delivery/` as client-agnostic stage playbooks +
script skeletons IS the delivery kit — and doubles as the subcontractor
runbook u7's 4x-leverage assumption needs before it can be validated. Free
work; prerequisite for u7 and for u1's first campaign.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Stage playbooks | done | `workspace/templates/leadgen-delivery/` created 2026-07-25: README (what the kit is, invariant safeguards, geo fence) + pipeline-playbook.md (8-stage operation source->clean/verify->segment->sequence->sample-approve->ramp->reply/bounce->weekly report, warm/cold split, seasonal-peak discipline, decision split, failure-mode table). Genericized from meji deliverables/shared/ (outreach-scope + technical-approach) | Extend with the pilot-routing/weekly-review detail from meji gitignored context (main checkout, not the worktree) | — | `workspace/templates/leadgen-delivery/` |
| Script skeletons | not-started | Client-agnostic versions of: Instantly loader w/ delay-semantics audit, MX pre-filter (Mimecast/no-MX drop), NB verify wrapper, campaign health-check engine | Re-derive (meji scripts embed client IDs, gitignored) | — | `project_meji_weekly_review_system` |
| Instantly API client template | not-started | `workspace/templates/api-clients/` has smartlead but NOT Instantly — the platform the reference build runs on | Generate via skil_api-boilerplate | — | api-clients/ |
| Tier scope mapping | not-started | pricing-tiers.json names axes (volume/channels/reporting) but nothing defines what 0.20/0.55/1.00 concretely include; menu unsellable + undelegatable without it | Write scope-to-deliverables doc | — | `../pricing-tiers.json` |
| Engagement doc templates | not-started | Genericize meji's onboarding-2-day-schedule / first-two-weeks / outreach-scope / handoff-package into `workspace/templates/client-docs/` | After stage playbooks | — | meji deliverables/shared/ |

## Open decisions / gates

- Tier scope mapping needs owner sign-off (it defines what is being sold).
- Deliverable-based scope only, never hour-based (no agency hourly —
  `user_rates_unpauseai`).

## Pointers

- Reference build: `workspace/clients/meji-media/` (specs 4-live, deliverables/shared/).
- Safety layer inherited by any campaign: `rule_instantly_invasive` (B5) +
  readiness audit.
- UK/US-only fence structural in list sourcing (UWG §7).
