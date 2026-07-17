# Mini-Checkpoint: Brisken Lead-Gen Research Channel + Go-Live Prep

**Date:** 2026-06-18
**Status:** p2 engine built-to-ready end to end; gated on Dirk decisions + the who-drives-seat call
**Type:** mini

---

## Summary
Resumed p2 from the 2026-06-17 SAP-audit checkpoint and ran the queued build-to-ready batch: the research channel + issue-#1 Shadow Integration report (locked 71%), the LinkedIn reposition, the SAP Store fixes pack, the Sales Nav targeting recipes, and a consolidated Dirk go-live decision sheet. Also corrected the prototype's SOC cert and stale benchmark band.

## What Was Done
- `context/lead-generation/research-channel.md` — spec for the data/benchmark publishing engine: canonical hub, the Shadow Integration series (issue #1 locked; #2 migration / #3 vendor as candidates from the same dataset), AEO cluster wiring, LinkedIn-primary/X distribution. (gitignored context)
- `deliverables/shadow-integration-report.html` — issue #1 founding asset. Dataset + Article + FAQPage JSON-LD (all parse), locked 71/34/22, honest caveats, extractable AEO Q&A blocks. validate-html clean, zero em-dashes. Committed `7b4c446`.
- `context/lead-generation/linkedin-reposition.md` — company-page rewrite (tagline/About/specialties/CTA) + 4-post launch batch, staged for Dirk look, `[HIERARCHY]` flags on the nesting-dependent lines. (gitignored)
- `dirk-enabler-pack.md` Part 4 — SAP Store quick wins (Trade Automation Terms link points to the MDH terms PDF; review-seeding kickoff for the 3 reference customers) + the `solutionhub.store.sap.com` partner-cockpit access request. (gitignored)
- `specs/2-build/p2-lead-gen-orchestration.md` — Sales Nav seat gate corrected (Dirk granted Brisken's seat; ICP/list-building autonomous, sending still gated); v0.1.2. Committed `7b4c446`.
- Prototype `brisken-onepilot-website-prototype.html` — SOC 2 → SOC 1 Type II across 6 spots (verified vs brisken.com: "ISO 27001 & SOC 1 Type 2 Certified"); benchmark band 81/62/38 (retired N=21 pilot) → 71/34/22 (locked N=41). Committed `589c468`.
- `context/lead-generation/sales-nav-targeting.md` — ICP→Sales Nav recipes: named Wave-1 account list, per-account persona targets (from radar §6), two alerting saved searches. (gitignored)
- `context/lead-generation/dirk-go-live-sheet.md` — consolidated decision sheet: every staged asset + every Dirk gate, smallest-to-biggest, with recommended ask order. (gitignored)

## Current Status
Two commits pushed (`7b4c446`, `589c468`) on `client/brisken/lead-gen-onepilot` (29 ahead / 53 behind main, no PR; left to user). The bulk of the build is gitignored internal context (intentional, same as the AEO substrate). Concurrent same-branch session ("OnePilot Review Notes + Conference Prep") ran today and preserved this session's 71/34/22 + SOC 1 Type II data; collision-zone branch, watch for divergence (7c7cf17 referenced by that session may be unpushed elsewhere).

**Folder reorg (external, mid-session):** the `context/lead-generation/` folder was reorganized into subfolders by another session / linter: `outreach-assets/` (research-channel, linkedin-reposition, aeo-substrate, shadow-integration-benchmark, mdh-outreach-assets), `targeting/` (targeting-radar, sales-nav-targeting), `accounts/` (dirk-enabler-pack, account-colgate), `evidence/` (evidence-pack, product-catalog, negotiation-benchmarks), `Rome-Event/`. `dirk-go-live-sheet.md` stays at the lead-generation root and its internal paths were auto-updated. The flat-path mentions in "What Was Done" above resolve under these subfolders.

## Next Steps
1. **Who-drives-the-seat decision** (human runs recipes in-seat vs agent-browser drives Brisken's live LinkedIn). Unblocks materializing the Sales Nav Wave-1 lists.
2. **Take `dirk-go-live-sheet.md` to Dirk** — identity + contact green-light + publish + partner-cockpit access are the high-leverage unlocks.
3. **Remaining autonomous build (no decision needed):** cluster Q&A pages (MDH cluster A + Remittance cluster D), folding in the 71% as a first-party sourced stat.

## Files to Read First
- `workspace/clients/brisken/context/lead-generation/dirk-go-live-sheet.md`
- `workspace/clients/brisken/context/lead-generation/outreach-assets/research-channel.md`
- `workspace/clients/brisken/context/lead-generation/targeting/sales-nav-targeting.md`
- `workspace/clients/brisken/context/lead-generation/outreach-assets/shadow-integration-benchmark.md`
- `workspace/clients/brisken/deliverables/shadow-integration-report.html`
