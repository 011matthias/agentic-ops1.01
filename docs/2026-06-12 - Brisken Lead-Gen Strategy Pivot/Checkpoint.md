# Checkpoint: Brisken Lead-Gen Strategy Pivot

**Date:** 2026-06-12
**Status:** Strategy reframed + Lane-1 assets built; deck (HTML+PDF) updated. PRE-TERMS, gated on Dirk. Branch `client/brisken/lead-gen-onepilot` (WIP, uncommitted).

---

## Summary
Owner pivoted p2 lead-gen away from cold email (Brisken's own ~150-mailbox/~2M-email campaign returned 0 leads) to a precision motion: a trigger-detection radar with a 3-axis ICP, borrowed-trust channels, and 1:1 LinkedIn. Built the radar (enriched the 7 warm accounts with real vendor evidence), the MDH outreach assets, updated both specs, and rewrote the Dirk-facing deck to the new scope, then compacted it (bullets + a funnel diagram, 14 -> 7 pages).

---

## What Was Done This Session

### Strategy reframe (owner-directed)
1. Cold email RETIRED. The 2M-email/0-lead result reframed as proof the market buys on trust + timing, not volume. Diagnosis: Brisken has a discovery problem, not a closing problem (>90% close); metric = warm, triggered at-bats/month.
2. Products narrowed 8 -> 3: Market Data Hub, Trade Automation, OnePilot platform. Other 5 apps become subfunctions/proof (Remittance/Calvin = the best forwardable asset).
3. NEW disposition ICP (owner's sharpening): data-vendor users (Bloomberg/Refinitiv/360T/FXall/OANDA/CME + SAP) = proven pain, not a firmographic guess; routes the product.
4. Pillars reweighted: SAP co-sell + active vendor referral moved OFF the critical path (slow, Brisken-driven); dependable near-term = Store-AEO + SAP-partner badge + reverse-sourced vendor signal + precision LinkedIn.
5. Pressure-tested the strategy inline (7 stress findings → hardened: trigger-detection as the spine, reachable-persona entry, AEO-as-corroboration not acquisition, Dirk-dependency mitigations).

### Radar build (Lane 1, autonomous, zero-spend)
6. Wrote the 3-axis precision model + sourcing rubric (`targeting-radar.md`).
7. Ran 7 parallel research agents to vendor-tag + trigger-verify the JOB-signal cohort with real public evidence + source URLs. Result ranked into tiers:
   - **Colgate A1** (Bloomberg confirmed, 3 own postings); **Corteva A2** (360T+Bloomberg in own job text); **J&J A2** (5+ concurrent S/4 treasury reqs = strongest trigger, vendor TBC); **Ford A2** (10-K hedging, vendor TBC); **Toyota A2** (ION WSS incumbent + S/4 build); **Penn Turnpike A2** (greenfield, MDH-rates only); **Amtrak B** (demoted: $32M portfolio, no trading).
   - Method learning: vendor evidence lives in the job-post BODY; 10-Ks/technographics don't carry it.
8. Built `mdh-outreach-assets.md`: the "your [vendor] feed into SAP, mapped" teardown template + Colgate/Corteva instances + ABM template. (No outbound message drafts — held per the no-unrequested-drafts rule.)

### Deck update (client-facing, 3 iterations)
9. Rewrote `lead-gen-strategy-2026-06-12.html` to the new scope (cold email out, 3 products, 3-axis targeting, enriched proof table, borrowed-trust channels, precision LinkedIn).
10. Reworded for plain language (account -> companies; personas -> people; disposition -> proof of the pain; reverse-sourcing -> spotting from public signals).
11. Compacted (user: "too much AI slop"): prose -> bullets, cut filler, added a funnel diagram (SVG), dropped forced page-break-per-h2. PDF 14 -> 7 pages. Validated clean each pass; PDF re-rendered via Chrome headless + content-verified.

### Produced for the user
12. A ruthless red-team prompt for Fable to sanity-check the strategy (files + thesis + named attack surface + output format).

---

## Key Decisions Made

### Cold email is dropped, not deferred
- **Choice:** Remove Track B (Instantly, lookalike domains, mailboxes, warm-up) entirely.
- **Rationale:** Brisken's own large-scale cold push returned zero leads; the buy is too high-risk to grant a meeting cold.

### Data-vendor usage is a first-class targeting axis
- **Choice:** Add "uses a market-data/trading vendor + runs SAP" as axis 2 of the ICP.
- **Rationale:** It is dispositional proof the pain exists (someone is moving that feed into SAP by hand) and it routes MDH vs Trade. Far sharper than firmographic fit.

### Trigger-detection is the spine
- **Choice:** Effort gates on a live per-account trigger; fit-without-trigger drops to AEO-background.
- **Rationale:** Borrowed trust converts a triggered account, it does not create the trigger (pressure-test finding #1).

### Single source of truth = HTML; PDF is a Chrome-headless render
- **Choice:** Edit HTML, re-render PDF via Chrome `--print-to-pdf` (not Edge, which collided with the open viewer).
- **Rationale:** Keeps one editable source; Chrome avoids the Edge single-instance collision when Edge is open as the viewer.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/lead-generation/targeting-radar.md | Created | 3-axis precision targeting model + sourcing rubric + 7 enriched accounts ranked into tiers |
| workspace/clients/brisken/context/lead-generation/mdh-outreach-assets.md | Created | MDH teardown template + Colgate/Corteva instances + ABM 1-pager template |
| workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md | Modified | Cold email retired; data-vendor-user ICP added to §3; frontmatter v0.4.0 |
| workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md | Modified | §0 strategy-hardening banner (supersedes cold-email sections); systems + frontmatter updated |
| workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html | Rewritten x3 | New scope, plain wording, compacted to bullets + funnel diagram |
| workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.pdf | Regenerated | Chrome headless render; 14 -> 7 pages |
| ~/.claude/.../memory/reference_html_deck_pdf_chrome_when_edge_open.md | Created | Memory: use Chrome headless for HTML-deck PDF when Edge is the open viewer |

---

## Current Status
- p2 strategy locked in the two specs + the radar; deck reflects it. All on branch `client/brisken/lead-gen-onepilot`, **uncommitted WIP** (G1: ledger to main via docs PR, never the p2 branch).
- Lane 1 (autonomous) ~60% done: radar + assets built; AEO substrate + Dirk enabler pack not yet built.
- Gated on Dirk (operational, not money): sending identity; which vendor relationships are live; go-ahead + ~$99/mo Sales Nav seat; demo owner per product.
- Deck is held for owner review before it reaches Dirk.

---

## Next Steps
1. **Harden axis-2** on J&J, Ford, Toyota: `scrapling`/`agent-browser` logged-in pass on the auth-walled job bodies to confirm the vendor (promotes A2 -> A1) and capture hiring-manager names.
2. **Run radar batch 2** (evidence-pack rows 1-8, 16-24) through the same sweep.
3. **Build the rest of Lane 1**: AEO substrate (~25-30 problem queries + Q&A page + Store-review plan) and the Dirk enabler pack (co-sell business case + vendor-relationship matrix).
4. **Owner**: review the deck; run the Fable red-team prompt; answer/forward the 4-item Dirk gate.
5. **(System)** Run `/system-dev` to build the rule_anti_slop Layer-1 detector (symmetry-collapse / volume) — the "third slop incident" trigger is now met (see Friction).

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/context/lead-generation/targeting-radar.md (the spine: model + enriched accounts)
- workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md (§0 hardening banner = current strategy)
- workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md (plan + terms, §3 ICP)
- workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html (the deck)

### Open Questions
- Will the Fable red-team surface a kill-shot we should address before the deck reaches Dirk? (await user)
- Comp-model attribution: content/AEO/co-sell build ambient inbound that can't be credited per-lead. Settle at terms (parked, delivery-first).

### Working Notes
- Vendor evidence is sourceable ONLY from the job-post body for most accounts; LinkedIn + careers SPAs are auth-walled (J&J/Ford/Toyota), so a logged-in/stealth pass is required to confirm them. The per-account source URLs + quotes are in the 7 research-agent returns (this session's transcript); fold the load-bearing quote for Colgate/Corteva into the teardown.
- Amtrak: keep in the universe but de-prioritize for MDH (no trading complexity).
- Penn Turnpike: greenfield angle (rates/SOFR curves into TRM during the live S/4 config), not rip-and-replace.
- PDF regen: Chrome headless `--print-to-pdf` with a temp `--user-data-dir`; Edge collides when it is the open viewer.

### Reference Materials
- Funnel diagram is inline SVG in the deck (theme-aware via CSS var fills).
- `tools/validate-html.py` (run before any deck deploy); `tools/md-to-pdf.py` (Edge-based; the deck uses direct Chrome print instead).

---

## How to Continue
Resume on `client/brisken/lead-gen-onepilot`. The strategy and deck are done and held for review. The next autonomous work is the `scrapling` vendor-confirm pass on J&J/Ford/Toyota + batch 2 + the AEO substrate and Dirk enabler pack. Nothing ships to Dirk until the owner reviews the deck (and optionally the Fable red-team result).

---

## Strategic Feedback

### What Worked Well This Session
- Tight iterative steering on the deck (plain language -> de-jargon -> compaction) converged fast; the funnel diagram landed the whole mechanism in one picture.
- Parallel research agents vendor-tagged 7 accounts with disciplined, sourced evidence in one fan-out, and the "evidence lives in the job-post body" learning is reusable.

### Suggestions
- For client-facing decks, ask up front whether the audience wants "dense bullets + a diagram" vs "narrative prose"; would have skipped two correction rounds (plain + compact were both predictable from the anti-slop + human-communication rules).

### System Health
- **rule_anti_slop Layer-1 detector is overdue.** The 2026-06-01 `infrastructure-deferred` entry said "if a third slop incident lands without the rule catching it, build the detectors." This session's deck-slop is that incident. Recurrence-kill = build the validate-output.py symmetry-collapse / prose-volume detector, not memorize harder.
- **Autonomy score: 3 human interventions this session (elevated — run /system-dev to close gaps).** Two were deck-form corrections (plain language, AI-slop volume) preventable by applying existing rules at write-time; one was the recurring B1 deferral cluster (hook held).
- `agent-deferred` (B1 closing-offer) remains a persistent generation reflex; the stop-b1-gate hook continues to catch it pre-user-harm.
