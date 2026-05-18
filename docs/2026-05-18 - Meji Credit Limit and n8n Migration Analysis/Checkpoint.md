# Checkpoint: Meji Credit Limit and n8n Migration Analysis

**Date:** 2026-05-18
**Status:** Client recommendation drafted (held, B5/external); internal migration analysis captured

---

## Summary
Nicolas flagged a Make credit-limit warning; diagnosed it end-to-end from live org data (90% of plan consumed in quiet season, ~90% of it timed-polling overhead not enquiry volume), drafted a client recommendation with a precise free-fix path, and produced an internal Make→n8n migration cost-benefit analysis tied to the deferred commercial trigger.

---

## What Was Done This Session
### Diagnosis (live data)
1. Queried Make org 5473701 (`organizations_get`) + team 2826470 (`scenarios_list`). Established: Core plan, 20,000 ops/mo, 18,040 used (90%), 1,960 left, resets 2026-05-20 ~10:44 UTC, auto-purchase OFF, ~644/day burn.
2. Attributed the 18,040: A0 6,082 / A3 5,743 / A2 4,690 / A1 2,130 / UTIL 150. Key finding: ~16,500 is fixed-cadence polling, only ~2,130 is volume-driven, and this is the quiet pre-September season.
3. Computed precise retune projection from per-scenario ops÷executions: A0 30→60min + A2 10→20min cuts baseline ~18,000 → ~12,650/mo (~30%, ~5,400 ops freed) without touching A3 (April-failure-sensitive).

### Deliverables
4. Drafted client recommendation `credit-limit-recommendation-gurmej-2026-05-18.md` (structured: where it stands → why it doesn't add up → ordered path → decision deadline). No fabricated Make pricing (B4). Every figure traced to the two live queries, sources logged in frontmatter. Em-dash strip hook fired; re-verified clean.
5. Produced internal `make-to-n8n-migration-analysis.md`: per-operation vs flat-cost model fit, Meji-specific benefits/downsides, rebuild inventory from live scenario list, sequencing tied to `project_meji_commercial_model` deferred trigger.

---

## Key Decisions Made
### Retune precision over directional estimate
- **Choice:** Replaced "roughly a third" with the computed ~18,000→~12,650 figure in the client draft.
- **Rationale:** Accuracy gate + the data was already in the `scenarios_list` payload (no extra query). A3 deliberately excluded — its interval is what caused the April silent failure.

### Migration analysis stays internal
- **Choice:** Captured as `context/` doc, flagged not-client-facing, kept out of the credit message and commercial intro.
- **Rationale:** `project_meji_commercial_model` memory: migration is a separately-priced project pitched only when outbound is live and post-September.

### No fabricated platform pricing
- **Choice:** Left Make-vs-n8n cost figures as TBD in both documents.
- **Rationale:** B4 — no sourced figure available; "TBD" beats a plausible invented number in a client deliverable and its internal basis.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/drafts/credit-limit-recommendation-gurmej-2026-05-18.md | Created | Client recommendation, held for user send (B5) |
| workspace/clients/meji-media/context/make-to-n8n-migration-analysis.md | Created | Internal cost-benefit, ready to harden into deferred pitch |

---

## Current Status
- Credit message: ready, NOT sent (external Upwork Thread 1, B5/user-sends).
- Make org: 18,040/20,000 (90%, **RED**), resets 2026-05-20 ~10:44 UTC, auto-purchase off. ~2 days runway vs ~3 at avg pace — spiky-day pause risk before reset.
- Infra reconciliation: live `scenarios_list` vs `infrastructure.yaml` — A0 1800s/active, A1 webhook/active, A2 600s/active, A3 3600s/active. No drift.
- Migration analysis: internal, parked behind deferred trigger.
- Comms: meji-media last contact 2026-05-15 (3 days, OK).

---

## Next Steps
1. **User:** review + send the credit recommendation on Upwork Thread 1 (external, B5).
2. On Gurmej's go-ahead: implement the retune (A0 1800→3600s, A2 600→1200s), revert tighter for Aug–Oct, update `infrastructure.yaml` same turn (modify-scenario gate).
3. Banter origin question still ready/unsent (carried, B5) — gates the Banter campaign.
4. Run platform feasibility assessment for meji-media (no `platform` section in `infrastructure.yaml`; this session's live numbers are the input).
5. Deferred trigger unchanged: pitch Make→n8n migration when outbound is live AND post-September.

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/context/drafts/credit-limit-recommendation-gurmej-2026-05-18.md
- workspace/clients/meji-media/context/make-to-n8n-migration-analysis.md
- workspace/clients/meji-media/context/drafts/ask-gurmej-banter-origin-2026-05-17.md (still unsent, B5)

### Open Questions
- Will Gurmej approve the one-off top-up before the 2026-05-20 reset, and the retune go-ahead?
- Make Core annual cost vs n8n hosting cost (both TBD — needed before migration becomes a pitch).

### Working Notes
- Per-scenario ops÷executions (stable, from `scenarios_list`): A0 4.22, A2 1.09, A3 8.53, A1 ~13. Retune math derives from these — no re-query needed next session.
- A3 left untouched on purpose: its filter/interval is the April silent-failure surface; do not widen it without the same empirical pre-deploy verification used in the 2026-04-27 fix.
- Auto-purchase is OFF — leave it off; recommend controlled manual top-up, not open-ended auto-buy.
- rename-chat.py: `python`/`py` not on PATH on this machine; use `uv run python tools/rename-chat.py`.

### Reference Materials
- Memory: project_meji_commercial_model, project_meji_volume_forecast, feedback_no_closing_offers
- Volume forecast: unpauseai.com/docs/meji-media/volume-forecast (Aug–Oct = 61% annual intake)

---

## How to Continue
The credit message is the live thread — once the user sends it and Gurmej replies, branch: top-up yes → confirm; retune yes → execute schedule change + infra.yaml update. Migration analysis sleeps until the outbound trigger.

---

## Strategic Feedback

### What Worked Well This Session
- "Nicolas flagged this, I looked at the history, here's my end-to-end recommendation" framing request produced a genuinely decision-useful message structure. Exploratory voice input correctly read as directional, not literal spec.

### Suggestions
- The credit fire-drill is recurring (5,000-credit top-up 2026-04-10 was occurrence one; this is two). Consider a scheduled `/ops-audit meji-media` (e.g., weekly) so the next ceiling approach is caught by the system, not by an email Nicolas happens to see.

### System Health
- No `platform` section in `infrastructure.yaml` despite a Make.com client running near plan ceiling — the ops-status safety net in `/comd_checkpoint` can't fire without it. Gap: platform feasibility data was never backfilled for meji-media.
- Autonomy score: 0 user interventions — fully autonomous on substance. 2 `agent-deferred` closing-offers generated then caught by the B1 stop-hook (structural backstop working; pattern still being produced despite `feedback_no_closing_offers`).
- Gates: B1 applied well in main flow (queried MCP instead of asking user for credit data); B4 strong (refused fabricated pricing, sourced every figure); B2 (re-verified draft after em-dash strip). B1:3 B2:1 B4:2 skipped:0.
