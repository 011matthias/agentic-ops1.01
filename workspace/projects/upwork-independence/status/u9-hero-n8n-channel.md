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
| D1 node identity | decided | `n8n-nodes-hero-software` under UnpauseAI (owner, 2026-10-26). GitHub identity = USER account `UnpauseAI` (created 2026-10-26), not an org; gh here is authed as `011matthias` | Before publish: repo under UnpauseAI with 011matthias as collaborator (or gh logged in as UnpauseAI) + npm account with trusted publishing | owner | plan §Phase 0 |
| D2 WW as named reference | open | Needed for case study, n8n Experts entry, HERO pitch; anonymised fallback defined | Owner asks Raphael | owner | plan §Phase 0 |
| D3 package prices | open | Anchors: care EUR200, licence EUR600, tiers 650/1,850 | Owner decides | owner | plan §What we sell |
| HERO first contact | sent | Owner sent the German draft (WW unnamed, "ihr") 2026-10-26 to kooperationen@hero-software.de; whether optional question 6 (webhooks) went with it is unconfirmed. Publish clock runs to 2026-11-09 | Watch for HERO's reply; a test account unlocks `docs/live-verification.md` in the node repo | HERO | plan §Phase 0 |
| n8n node v1 | built (local) | `C:\Users\neuma_p1qrsic\Repo\n8n-nodes-hero-software`, 8 local commits, no remote. Build + lint pass; 93 tests (incl. every sent document validated against the 2026-10-09 HERO schema snapshot, opt-in via `HERO_SCHEMA_PATH`; a planted invalid argument turns it red). Zero HERO API calls: live use of the client's production key was denied by the auto-mode classifier. Every operation still "not yet verified against the live API" | Live checklist (10 points in the repo) on a HERO test account; `npm run dev` once in a real n8n; publish from a fresh squashed history (old commits name client files) | HERO test account | plan §Phase 1 |
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
