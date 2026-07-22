---
project: upwork-independence
workstream: u3-linkedin-outbound
group: uwi
spec:
state: not-started
updated: 2026-07-22
general_ref: status/uwi-general.md
---

# uwi / u3 — LinkedIn outbound

Second-largest channel (0.289 effort, ~520h, pool 30, 2-mo ramp, 20h fixed
setup). Reuse-shaped: CDP tooling (`tools/edge_cdp.py`), the Brisken Sales-Nav
targeting METHOD (three-axis radar -> account lists -> persona searches ->
saved-search net), and the human-in-seat doctrine (agent prepares — targeting,
lists, drafts, tracking; human sends — automation on a live seat is
account-risk). Three from-zero elements below. Starts weeks 3-6.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Owned identity | not-started | No company page, no profile assets, no LinkedIn link on the platform site | Company-page content + profile positioning | — | recon: zero owned assets |
| Sales Nav seat | blocked | Brisken's seat is client-scoped, off-limits; model amortizes EUR25/mo | — | purchase gate | `../infrastructure.yaml` |
| ICP recipes | not-started | Clone the Brisken radar/persona recipe SHAPE; persona + filters now defined in icp.md (DE included — LinkedIn is DE-legal) | Write the Sales Nav recipes off icp.md | — | `../context/icp.md` (landed 2026-07-22) |
| Message cadences | not-started | Connection-request + DM sequences; no skill home exists (extend cold-email principles) | Draft after recipes | — | — |
| Human-send split | not-started | Budget human send-time as a first-class element (~520h is NOT fully agent-executable) | Split table when workstream activates | — | human-in-seat doctrine |
| Pipeline tracking | not-started | Lead-Desk pattern clone or tracked ledger; no UnpauseAI pipeline state exists anywhere | Decide with u5 | — | `project_brisken_lead_desk` (pattern) |

## Open decisions / gates

- Seat purchase [GATED].
- Tracking store shape: thin Lead-Desk clone vs tracked ledger file (decide
  when the first channel goes live; W1 — no store before need).

## Pointers

- CDP tooling: `tools/edge_cdp.py`, `tools/launch-edge-cdp.ps1`.
- Doctrine + mechanics (75s pacing, page-1 lies, save-to-list on lead page):
  memory `project_brisken_rome_salesnav_list`, brisken sales-nav-targeting.md.
