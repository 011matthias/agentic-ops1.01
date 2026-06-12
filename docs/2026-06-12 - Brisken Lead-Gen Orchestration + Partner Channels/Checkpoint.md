# Checkpoint: Brisken Lead-Gen Orchestration + Partner Channels

**Date:** 2026-06-12
**Status:** p2 lead-gen operating model locked + partner-channel track added; pre-terms, gated on Dirk's 3 operational answers. Posture: delivery-first (build before compensation).

---

## Summary
Continued Brisken p2 (OnePilot lead-gen). Shipped a branch-isolation + shared-ledger rule (Layer 1), built the orchestration operating-model spec (engine, force multipliers, go-forward, partner-channel track), confirmed via research that Brisken's SAP Store / AFP / data-vendor channels are already live, and added a partner-channel section to the Dirk-facing deck. The engagement reframed from money-first to delivery-first.

---

## What Was Done This Session
### Branch isolation (system-infra)
1. Resolved the session-start git tangle: uncommitted shared-ledger WIP (INDEX / friction-register / Session-5 log) was blocking the checkout to the p2 branch. Routed it to `main` via docs PR #143, not onto the feature branch.
2. Shipped `rule_branch_isolation_and_shared_ledger.md` (G1): shared system ledger reaches `main` only via a `docs/...` PR; one project per branch, cut before the first edit; never `git stash` for cross-project isolation. PR #143 merged to main.

### p2 orchestration (client-dev)
3. Created `specs/2-build/p2-lead-gen-orchestration.md` (id `p2.ops1`): the manual-first engine (source -> personas -> verify -> LinkedIn-first outreach -> BANT -> book -> report), the build-now vs go-live-gated split, the BANT-lead definition, wave-1 = Market Data Hub.
4. Added §9 force multipliers, §10 go-forward (campaign 1 = MDH, the 24-account base, draft Bloomberg/Refinitiv message variants), §11 partner-channel track (SAP + data-vendor only, cloud-focused, excludes anything already running as a task).

### Channel confirmation (research)
5. Confirmed (web research + owner's SAP Store screenshot): OnePilot is LIVE on SAP Store (Trade Automation + Market Data Hub variants for Central Banks / Financial Services / Commodities / OANDA + Remittance + Bank Fee), surfaced by the SAP Store AI advisor; Brisken is a listed AFP-marketplace vendor; the data-vendor integrations (Bloomberg, Refinitiv/LSEG, 360T, CME, OANDA) are live. Bloomberg Enterprise App Portal and the LSEG partner program are real referral/listing channels.

### Deck (deliverable)
6. Added "A second track: your SAP and data-vendor ecosystem" to the Dirk deck (SAP partner channel + data-vendor channel, framed as Brisken's own ecosystem; already-running treated as an asset, not a task). Verified: `validate-html` 0 hits, zero em-dashes, PDF regenerated via headless Chrome (15pp), pypdfium2 text-extract confirms the new section is in the render.

---

## Key Decisions Made
### Delivery-first, not money-first
- **Choice:** build the engine and generate first BANT leads as proof; settle commission afterward (the §2 term sheet is deferred, not dropped).
- **Rationale:** owner reframe ("quality delivery first, then compensation").

### Partner track scoped to cloud-platform partners
- **Choice:** include only SAP (point 1) and the data vendors (point 3); drop SAP-treasury SIs, treasury associations/events, and banks (treasury-vertical); exclude anything Brisken already runs from the task list (it stays an asset).
- **Rationale:** owner directive (focus on Brisken's cloud solutions, not treasury).

### The gate shifted from money to Dirk's operational consent
- **Choice:** real outbound to Brisken's prospects under a Brisken identity needs Dirk's operational go-ahead regardless of money; everything up to "press send" we build now.
- **Rationale:** we cannot represent a client to its market without consent; this is a smaller, faster gate than negotiating commission.

### Ledger routed to main via a docs PR (the new G1 rule, applied to this checkpoint)
- **Choice:** p2 work committed to the p2 branch; the checkpoint ledger written on a docs branch off `origin/main` and PR'd, never on the feature branch.
- **Rationale:** the rule shipped this session; this checkpoint is its first exercise.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/rules/rule_branch_isolation_and_shared_ledger.md` | Created (PR #143) | G1 git-hygiene rule |
| `workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md` | Created (p2 commit 6fb49c8) | Operating model: engine + §9 multipliers + §10 go-forward + §11 partner track |
| `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` | Modified (p2 commit 6fb49c8) | Added the partner-channel ("second track") section |
| `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.pdf` | Regenerated (untracked artifact) | 15pp render of the deck |
| docs ledger (INDEX / friction-register / sessions / this Checkpoint) | This checkpoint (docs PR) | Continuity |

---

## Current Status
- **Branch:** p2 work on `client/brisken/lead-gen-onepilot` (commit `6fb49c8`, pushed to origin). `main` holds p1 finance + system.
- **Pre-terms:** no spend, no outbound until Dirk's 3 operational gates clear.
- **Built to "press send":** the engine, the 24-account starting list, the message shape, the deck with both tracks. No orchestrator (manual-first); no Make/n8n usage.

---

## Next Steps
1. **Dirk gate 1:** which of the 6 data-vendor relationships are active (co-marketing/referral vs technical only). Unlocks the partner-referral track (Way 2).
2. **Dirk gate 2:** sending identity (whose name and domain front the outreach).
3. **Dirk gate 3:** go-ahead to contact + the ~$99/mo Sales Navigator seat.
4. **Open for Dirk:** is SAP co-sell (account-exec referral) active? Distinct from being SAP-listed; the bigger prize.
5. **On go-live:** provision the seat, Dirk-validate the MDH target list, tag the 24 accounts by data-vendor signal, start LinkedIn (Way 1) while Dirk opens the vendor conversations (Way 2).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` (binding; p1/p2 isolation + swap history)
- `workspace/clients/brisken/specs/2-build/p2-lead-gen-orchestration.md` (the operating model + §9/§10/§11)
- `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md` (plan + ICP + term sheet)
- `workspace/clients/brisken/context/lead-generation/brisken-product-catalog.md` (products + per-product campaigns; gitignored, on disk)
- `workspace/clients/brisken/deliverables/lead-gen-strategy-2026-06-12.html` (Dirk deck)
- `.claude/rules/rule_branch_isolation_and_shared_ledger.md` (G1 git hygiene)

### Open Questions
- Dirk's 3 operational answers (the gates above).
- Per vendor: which relationships are active enough to open.
- Is SAP co-sell active?

### Working Notes
- **SAP Store presence is extensive and verified.** The key Dirk question is the lead-starved-despite-live-channels paradox: are the SAP Store / AFP inbound leads being captured and worked, or surfaced only for brand-name searches? If not worked, that gap is exactly where our engine plugs in (capture + qualify the existing inbound, then add outbound).
- `context/` is gitignored; the product catalog + evidence pack live on disk only.
- **Git flow this session:** p2 work -> p2 branch (`6fb49c8`); ledger -> docs branch off `origin/main` -> PR. Local `main` was stale (behind origin by PR #143); always base the docs branch on `origin/main`.

### Reference Materials
- SAP Store (Brisken): https://store.sap.com/dcp/en/product/display-2001008447_live_v1/brisken-onepilot-market-data-hub/
- AFP marketplace (Brisken): https://marketplace.afponline.org/company/920551/brisken-llc
- Bloomberg Enterprise App Portal; LSEG partner program (referral channels)

---

## How to Continue
`git checkout client/brisken/lead-gen-onepilot`. The operating model (spec §3-§11), the deck, and the catalog are current. Everything downstream is gated on Dirk's 3 operational answers; when he confirms, provision the Sales Navigator seat, Dirk-validate the MDH target list, and start LinkedIn outreach while Dirk opens the vendor conversations. Do NOT do p2 work on `main` or a finance branch; do NOT commit ledger files on the p2 branch (G1 rule).

---

## Strategic Feedback

### What Worked Well This Session
- The owner's fast, tight redirects (delivery-first, then partner channels, then cloud-not-treasury, then into the deck) converged the strategy quickly without over-building any one version.
- Grounding the SAP Store / AFP / data-vendor findings with real research plus the owner's screenshot turned several "validate with Dirk" assumptions into confirmed facts, which materially reshaped the plan (the partner channels are live, so the move is exploit-not-build).

### Suggestions
- Opening a working markdown spec for review via `Start-Process` hands it to Word, which exclusive-locks the file and blocks the agent's own edits (this cost ~40 minutes this session). For specs the owner reads in-IDE, just reference the path; reserve `Start-Process` for rendered deliverables (HTML to a browser, PDF to a viewer).

### System Health
- The branch-isolation rule (G1) shipped this session was immediately exercised by this checkpoint: ledger routed to a docs PR off `origin/main`, p2 work kept on the p2 branch. The flow is correct but heavy (commit p2, fetch, cut docs branch, PR). A `/checkpoint` helper that auto-detects "on a feature branch" and routes the ledger to a docs PR would remove the manual dance.
- Autonomy score: 2 human interventions this session (file-close to clear the Start-Process lock; the branch-handling redirect).
