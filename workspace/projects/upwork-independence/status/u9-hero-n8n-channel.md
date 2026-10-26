---
project: upwork-independence
workstream: u9-hero-n8n-channel
group: uwi
spec:
state: active
updated: 2026-10-26
general_ref: status/uwi-general.md
---

# uwi / u9 — HERO x n8n channel (node, templates, partner listing)

Win HERO's trade-business users as automation clients by becoming their n8n
integration: publish the missing n8n node for HERO, turn the Wärme Wimmer
build into templates and a case study, and get listed through HERO's partner
doors. Opened 2026-10-26 (owner decision 8). Full plan:
`../context/hero-channel-plan.md`.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| D1 node identity | open | Recommended `n8n-nodes-hero-software` (free on npm 2026-10-26), own public repo under UnpauseAI | Owner decides name + GitHub owner | owner | plan §Phase 0 |
| D2 WW as named reference | open | Needed for case study, n8n Experts entry, HERO pitch; anonymised fallback defined | Owner asks Raphael | owner | plan §Phase 0 |
| D3 package prices | open | Anchors: care EUR200, licence EUR600, tiers 650/1,850 | Owner decides | owner | plan §What we sell |
| HERO first contact | not-started | 5 questions defined (terms, API cost/plan, limits + v9, test account, listing/webinar/Vorteilswelt) | Draft on owner request; owner sends to kooperationen@hero-software.de | D2 | plan §Phase 0 |
| n8n node v1 | not-started | Scope fixed: 5 polling triggers, contact/project/logbook/task/file actions, raw GraphQL; WW quirks handled | Build in parallel with the HERO email; publish after HERO's answer or 2 weeks | D1 | plan §Phase 1 |
| Verification submission | not-started | Requirements read 2026-10-26 (no runtime deps, provenance publish, lint) | Submit at creators.n8n.io/nodes when published | node v1 | plan §Phase 1 |
| Templates x3 | not-started | Inbox triage, form-to-project, status follow-up | After node v1 | node v1 | plan §Phase 2 |
| Case study + landing page | not-started | Measured numbers only | After D2 | D2 | plan §Phase 2 |
| HERO distribution | not-started | Listing, Community-Experte webinar, Vorteilswelt offer | After HERO reply | HERO | plan §Phase 3 |
| First paid HERO client | not-started | Milestone week 12; tripwire week 12 | — | — | plan §Measures |

## Gates

- Publishing the node waits for HERO's answer on terms, or two weeks of
  silence (then without logo, "not affiliated" line).
- No writes to WW's HERO tenant for node testing (invasive-action gate);
  read-only checks with the owner's key only.
- Client n8n instances are client-owned; never one shared instance.

## Pointers

- WW production build and HERO API quirks: `akkton/agentic-ops` clone,
  memory `reference_ww_hero_api_quirks`.
- n8n Experts waitlist (3-customer bar): memory
  `project_n8n_is_the_platform_not_make`.
