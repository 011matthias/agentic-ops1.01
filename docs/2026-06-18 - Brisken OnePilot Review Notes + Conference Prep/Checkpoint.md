# Checkpoint: Brisken OnePilot Review Notes + Conference Prep

**Date:** 2026-06-18
**Status:** Prototype live with all implementable review notes applied; Rome conference Track-1 build staged and ready to execute in a fresh session.

---

## Summary
Implemented Dirk's in-page review notes on the Brisken OnePilot prototype (the ones buildable without missing inputs) plus replaced the hero diagram with an open Universal-AI hub per Matthias, all deployed to Fly and verified. Then set up the SAP Treasury Conference 2026 (Rome) pre-event work: logged the Dirk→Rachel thread, inventoried the `05-lists` golden-copy repository, and wrote an execution runbook.

---

## What Was Done This Session

### OnePilot prototype (p2, branch client/brisken/lead-gen-onepilot)
1. OnePilot Agents text block → four-tier command-stack diagram (commit `b5835f8`).
2. Hero restructured: research stats (81/62/38) and pipeline art side by side; removed the "first sample of 21 / method on request" footnote (`029f03a`).
3. Dirk's review notes implemented (`fa70211`): headline → "Financial Data. Solved. End to End."; badge + title/meta → "AI native"; research-block alignment (81% + "Our research" centered over a fixed-width text column, 62/38 in a left column); market-data providers moved out of the trust band into the Market Data Hub card; customer logos → rolling marquee banner (logos cloned at runtime so base64 stays single).
4. Hero pipeline diagram → open Universal-AI hub (`7c7cf17`): translucent OnePilot core, systems flow in from every side, governed stream out to SAP; retired the `pl-*` pipeline styles for `uh-*`.
5. Every change deployed to brisken-onepilot-proto.fly.dev and verified behind the name gate (healthz 200 + markers).

### Concurrent-session reconciliation
6. A parallel session committed on the same branch (`7b4c446`, `589c468`): benchmark re-locked to 71/34/22, SOC reverted to "SOC 1 Type II". Per owner directive ("their data + actions trump yours, keep them"), kept all of it; my hero edits did not clobber it; staged only the deliverable HTML so their uncommitted WIP (docs, md-to-pdf.py, p2 spec) was untouched. Corrected the stale "SOC 2 resolved" claim in memory.

### Rome conference prep (p2, comms + planning)
7. Pulled the prototype feedback log: Dirk left 8 in-page notes; Matthias left 1 (the hero-visual note, now done).
8. Logged the Dirk→Rachel conference thread + sponsorship constraints to `comms-log.md`.
9. Inventoried the `05-lists` golden-copy repository (past-event lists AFP '24 + WebSummit Lisbon; country lists UK/Ireland/Zurich; SAP ACCOUNT LIST 11k + the 4.7MB master).
10. Wrote `conference-rome-2026-plan.md` (the runbook) + a ready-to-paste resume prompt covering Track 1 (Rachel list) and Track 2 (email campaign + landing page).

---

## Key Decisions Made

### Keep the concurrent session's data and actions
- **Choice:** SOC stays "SOC 1 Type II", benchmark stays 71/34/22; do not re-apply my earlier SOC-2 flip.
- **Rationale:** Owner directive 2026-06-18 — the other session's data + actions take precedence.

### Hero visual = open Universal-AI hub
- **Choice:** Replace the MDH-style pipeline SVG with a translucent hub (Matthias picked "Open universal hub").
- **Rationale:** Conveys transparency/openness + "Universal AI"; also de-MDHs the hero Dirk flagged as "100% MDH".

### Defer the conference list build to a fresh session
- **Choice:** Stage everything in a runbook; execute the extraction/curation in a new `/resume brisken`.
- **Rationale:** Critical context pressure after a long site+comms session; the deliverable goes to a third party and deserves a clean pass. Thursday still achievable.

### Contact identification source
- **Choice:** Brisken's own Sales Navigator (Dirk-granted) + public research + the existing list exports. Meji's Apollo/Sales Nav/Instantly stay off-limits.
- **Rationale:** Project boundary; the past-event lists already carry names + emails.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html | Modified | Diagram, hero split, Dirk's notes, Universal-AI hub (commits b5835f8, 029f03a, fa70211, 7c7cf17) |
| workspace/clients/brisken/context/comms-log.md | Modified | 2026-06-18 Dirk→Rachel conference thread |
| workspace/clients/brisken/context/lead-generation/conference-rome-2026-plan.md | Created | Runbook for the Rome pre-event build (2 tracks, source-list map, steps) |
| memory/project_brisken_onepilot_site_hosting.md | Modified | Dirk-notes status, hub replacement, concurrent-session note, SOC correction |
| memory/reference_repo_tooling_gotchas.md | Modified | flyctl token auto-load gotcha + fix |

---

## Current Status
- Prototype: live on https://brisken-onepilot-proto.fly.dev with all implementable review notes + the Universal-AI hub, verified both themes + name gate.
- Conference: Track-1 build fully staged (runbook + sources inventoried + resume prompt). Not yet built.
- p1 expense-reconciliation platform: custom SaaS build (tier unknown, no workflow-engine op count) — untouched this session.

---

## Next Steps
1. Fresh `/resume brisken`: execute `conference-rome-2026-plan.md` Track 1 — EU company list + one treasury contact each for Rachel (due Thursday).
2. Track 2: draft the 2-3 email pre-event sequence + landing page (repurpose existing PDFs/PPTX to live downloadable web pages); Dirk-gated to send/publish.
3. Dirk's still-open prototype notes: real booking link (4), research-paper URL (5), more customer logos from SharePoint (6), MDH-vs-OnePilot brand decision (8).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/context/lead-generation/conference-rome-2026-plan.md
- workspace/clients/brisken/context/comms-log.md (2026-06-18 entry)
- workspace/clients/brisken/context/lead-generation/targeting-radar.md
- workspace/clients/brisken/PROJECT-BOUNDARIES.md

### Open Questions
- Conference list volume (default: warm EU set ~20-40 companies).
- Track-2 landing-page scope (reuse OnePilot shell? which assets to repurpose).
- Dirk notes 4/5/6/8 need inputs/decision.

### Working Notes
- The `05-lists` exports already contain contacts + emails (Apollo/Instantly), so Sales Nav is top-up, not the primary source. Filter European by Country/Location columns; AFP lists lack a country column (resolve by company HQ).
- flyctl in Git Bash sometimes fails to auto-load its token; pass `FLY_API_TOKEN="$(grep -E '^access_token:' ~/.fly/config.yml | sed -E 's/^access_token:[[:space:]]*//')"` for the deploy (see reference memory). The token is valid; do NOT trigger an interactive login.
- Shared clone with a concurrent session on this branch: always `git add` only the specific deliverable, never `git add -A`; check `git log` for parallel commits before committing.
- The local static-preview server runs on `python -m http.server 8771` in `onepilot-site/site`; cache-bust with `?v=N`.

### Reference Materials
- Live proto: https://brisken-onepilot-proto.fly.dev (name gate, any name)
- Feedback log: gated `/feedback.jsonl` behind the name gate (canonical record of Dirk's + Matthias's notes)

---

## How to Continue
Paste the resume prompt (in the session transcript) into a fresh session, or open the runbook and execute Track 1. Everything needed is on disk; nothing depends on this session's context.

---

## Strategic Feedback

### What Worked Well This Session
- The in-page feedback tool paid off: Dirk's and Matthias's notes came back with exact element selectors + positions, so each was unambiguous to action.
- Catching the concurrent-session commits before `git add` prevented clobbering and an accidental commit of another session's WIP.

### Suggestions
- For parallel work on one client branch, use separate git worktrees per session (per `feedback_worktree_for_concurrent_sessions`) — the shared working tree this session held another session's uncommitted edits, which is a clobber risk every commit.

### System Health
- The B1 stop-hook fired twice on deferral phrasing in final responses ("say the word", "if you want me to fold…") and forced corrections both times — the structural gate is holding, but the pattern recurs at turn-end on legitimately-gated actions (deploy) where surfacing is correct but the phrasing reads as an offer. Wording discipline, not a gate gap.
- Autonomy score: 2 human/hook interventions this session (both B1 deferral catches).
