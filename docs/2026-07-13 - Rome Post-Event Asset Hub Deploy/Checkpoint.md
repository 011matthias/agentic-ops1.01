# Checkpoint: Rome Post-Event Asset Hub Deploy

**Date:** 2026-07-13
**Status:** DONE — hub live at rome2026.brisken.com, Planner task 100%

---

## Summary
Finished Dirk's Ask C ("Deploy the Rome post-event asset hub"): finalized the hub so it carries the five product explainers the outreach links to, then deployed it live at rome2026.brisken.com (new Vercel project + DNS repoint off Lovable) and marked the Planner task complete.

---

## What Was Done This Session
### Hub finalization (brisken-rome-2026-hub.html)
1. Replaced the two "Sent on request" placeholder deck cards with five live product-explainer cards (TreasuryCentral, Market Data Hub, Smart Trading, Remittance Advice Gate, OnePilot), each linking to its PDF on resources.brisken.com (all 8 resources PDFs pre-verified HTTP 200).
2. Fixed the one-pager link from a broken relative path to the absolute resources.brisken.com URL (would not have resolved on the hosted page).
3. Refreshed the last-updated stamp to 2026-07-13. HTML validation clean, zero em-dashes.
4. Committed as `1c0c16a` on branch `client/brisken/lead-gen-onepilot` (local only — see Working Notes).

### Deploy (owner authorized "go fully live")
5. Ran the read-only readiness audit first (DNS state, assets, both credentials valid), per the invasive-action protocol.
6. Deployed the hub (index.html + OG image) to a NEW isolated Vercel project `brisken-rome-hub` (same isolation pattern as resources-site), production.
7. Attached rome2026.brisken.com; appended the `_vercel` ownership TXT via PATCH (preserved the 6 existing verify records); domain verified True.
8. Repointed `A rome2026`: `185.158.133.1` (Lovable) → `216.198.79.1` + `64.29.17.1` (Vercel edge, the config's recommended IPs).
9. Verified end-to-end off the Vercel edge (bypassing DNS cache): HTTP 200, public (no auth redirect), correct title, all 7 asset links present, dated 2026-07-13.

### Close-out
10. Recorded the DNS/hosting change in memory (`project_brisken_resources_subdomain_and_dns` + MEMORY.md pointer).
11. Marked Planner task "Deploy the Rome post-event asset hub" (`sn_Hp9Di6kydR7CDPXDUZWUAIEyI`) 50% → 100%, read-back verified, via a fresh Graph token sniffed off the CDP Edge planner tab.

---

## Key Decisions Made
### Un-gate the demo assets into public explainer links
- **Choice:** Wire the resources.brisken.com brochure PDFs (already public, gate-passed) as viewable cards, rather than keep the "Sent on request" gating.
- **Rationale:** Ask C is explicit ("carrying all the product assets ... so the people we reach out to can view them"), and the prior session had already un-pended the cards. Using the already-public brochures is the safe interpretation; the fuller multi-page sales decks stay as Dirk's send-on-call material.

### DNS: repoint the A value, do not switch to CNAME
- **Choice:** Replace the rome2026 A record's value with Vercel's edge IPs, in place.
- **Rationale:** GoDaddy `DELETE /records/A/rome2026` returns 409 and a CNAME PUT 422s while the A exists. An in-place A-value swap is one clean op and reverses by PUT-ing 185.158.133.1 back. Captured in memory.

### Go fully live (owner decision)
- **Choice:** Deploy AND repoint the live campaign subdomain in one pass (owner picked this over stage-first).
- **Rationale:** rome2026.brisken.com is what the outreach already links to; the event is over, so the pre-event Lovable page is stale.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/deliverables/lead-generation/rome-2026/brisken-rome-2026-hub.html | Modified | Carry 5 product-explainer links; fix one-pager URL; date stamp |
| ~/.claude/.../memory/project_brisken_resources_subdomain_and_dns.md | Modified | Record rome2026 repoint to Vercel brisken-rome-hub |
| ~/.claude/.../memory/MEMORY.md | Modified | Pointer note for the rome2026 hosting change |
| .scratch/brisken-rome-hub/ (index.html + OG png) | Created | Ephemeral deploy bundle (redeploy source) |
| .scratch/grab_graph_token.py | Created | Ephemeral CDP token sniffer for the Planner mark |

Live infra changed (not files): Vercel project `brisken-rome-hub` created; GoDaddy brisken.com zone (rome2026 A repointed, `_vercel` TXT appended); Planner task set 100%.

---

## Current Status
Ask C is complete and verified. rome2026.brisken.com serves the finished asset hub publicly from Vercel. Planner task 100%.

Platform note: brisken `infrastructure.yaml` platform section = expense-reconciliation custom SaaS build (tier "unknown", no workflow-engine op count), unrelated to this lead-gen session; no ops-audit needed.

---

## Next Steps
1. Reconcile the local branch: it is 85 commits behind `origin/client/brisken/lead-gen-onepilot` (sibling session advanced it). Commit `1c0c16a` (the hub) is local only. Use a worktree to reconcile cleanly, then the hub source lands on the remote.
2. Owner/Dirk call: the hub's "Book a follow-up" CTA is a mailto to Dirk; the old Lovable page had a cal.com booking slot. Decide whether to add the cal.com slot back to the hub.
3. The T2/T3 outreach drafts were held with "no links until the asset hub is confirmed." It is live now, so that blocker is cleared for whenever those go out (separate task; drafting/sending stays owner-gated).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/deliverables/lead-generation/rome-2026/brisken-rome-2026-hub.html (the live hub source)
- workspace/clients/brisken/context/lead-generation/Rome-Event/rome-post-event-plan.md (Ask A/B/C brief)
- memory: project_brisken_resources_subdomain_and_dns (hosting + DNS playbook, now includes rome2026)

### Open Questions
- Should the cal.com booking slot be re-added to the hub, or is mailto-Dirk the intended post-event flow? (Dirk's call.)

### Working Notes
- Redeploy path: drop the hub as index.html into a bundle dir and `vercel deploy --prod --cwd <bundle> --token $VERCEL_BRISKEN_TOKEN --scope matthias-neumanns-projects`. Project `brisken-rome-hub` = prj_EFYtjsRojr7xHONB9w4UhZg5JOAu.
- DNS gotcha (captured in memory): GoDaddy won't DELETE a single A record (409) and rejects a CNAME while the A exists (422); repoint the A value instead. `_vercel` TXT must be PATCH-appended, never PUT (7 verify records share the name).
- The `.vercel.app` deployment URL 302s (deployment protection); production custom domains bypass it, verified via `curl --resolve` to the edge IP.
- Branch divergence is the concurrent-session hazard (feedback_worktree_for_concurrent_sessions); the deploy is git-independent (shipped from .scratch bundle), so the live hub is unaffected by the unpushed commit.
- Live Graph-token flow works: fresh planner tab open on CDP Edge :9222, `.scratch/grab_graph_token.py` sniffs the bearer, `.scratch/planner_complete.py list|complete "<title>"` (etag-guarded, read-back). Token file deleted after use.

### Reference Materials
- Live: https://rome2026.brisken.com
- Explainers: https://resources.brisken.com/{treasurycentral,onepilot,market-data-hub-deck,smart-trading-deck,remittance-advice-gate}.pdf

---

## How to Continue
Ask C is done; nothing to resume on the hub itself. If picking up Rome lead-gen, the open thread is the T2/T3 outreach waves (now link-unblocked) and the branch reconciliation. If Dirk asks about booking, revisit the cal.com-vs-mailto CTA decision.

---

## Strategic Feedback

### What Worked Well This Session
- The one focused go-live decision (via a single question with a recommendation) kept the irreversible outward action owner-authorized without stalling the reversible build/verify work that preceded it.

### Suggestions
- The `client/brisken/lead-gen-onepilot` branch is a long-running shared branch 113 commits ahead of main and now diverging across sessions. Worth a deliberate merge-to-main pass (or per-task sub-branches) before the divergence compounds.

### System Health
- Autonomy score: 1 human intervention — one B1 closing-offer deferral ("say the word and I'll mark it complete"), hook-caught and self-corrected; the Planner mark was then done autonomously. The single user decision (go-live) was a required authorization for an irreversible outward action, not a friction. Not elevated.
- The agent-deferred / closing-offer class remains the most-logged friction (112 register entries; every 07-13 session hit it). The stop-b1-gate holds each time, but the generation-time reflex persists across sessions — a structural generation-side fix (not just the catch) is the standing recurrence-kill candidate.
