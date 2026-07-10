# Checkpoint: Meji P2 Retarget + P3 Ramp

**Date:** 2026-07-01
**Status:** P3 ramped + old P2 paused (live); new-audience first batch STAGED, pending reveal → NeverBounce → load → activate

---

## Summary
Diagnosed why P2 corporate cold produces zero opportunities (wrong audience: 57% CEO/MD of 11-50 firms, too small to buy managed events), redesigned the ICP to functional bookers at 201-2000-staff companies, got Gurmej's sample sign-off, ramped P3, paused the old P2 list, and staged the first new-audience batch.

---

## What Was Done This Session
### Diagnosis + ICP redesign
1. Profiled the live P2A/P2B lists: 57% CEO/MD of 11-50-employee firms (Tatami Fightwear, Rhodes Wealth Management) — mismatched to the premium Polestar/SJA offer. Deliverability fine (~3% bounce); relevance was the problem.
2. Ran a design workflow (10 agents: market research → 4 redesign angles → synthesis → adversarial). Corrected two of its soft numbers against ground truth: historical corporate cold was **2.0%** (21/1968), not 0.25%; Set C Midlands universe is thin.
3. Measured the real Apollo universe (free `total_entries`): Set A London/SE ~8.9k, Set B UK-wide ~2.8k, Midlands ~0.7k. Old failing band (CEO/MD 11-50) = 52.8k.

### New ICP (same product, new audience — user correction applied)
4. User corrected an over-reach: keep the product (bespoke corporate events), change only the audience. New split is by SENIORITY not company size: **P2A = deciders/event-owners, P2B = organisers, both 201-2000 staff**, event sectors, London/SE + Midlands, c-suite/owner + public sector excluded.
5. Built the 200-contact sample (`meji_p2_new_audience_sample_2026-06-29.py`), PDF'd it (Chrome fallback; Edge failed), sent to Gurmej. **Gurmej approved 2026-06-30.**

### Live Instantly changes (B5, user-confirmed, readiness-checked)
6. **P3 ramped:** campaign daily_limit 50→90, both mejixmas mailboxes 30→45 (warm-safe). Verified.
7. **Old 880 paused:** P2A `c3daf05c` + P2B `5d677062` → status 2 (PAUSED). Verified.
8. **First batch staged:** 300 London/SE candidates (`meji_p2_batch_2026-07-01.py`, ~253 with email on file, Apollo IDs captured). Free, no credits.

### Comms
9. Drafted + iterated Gurmej messages (retarget notice; P3-vs-P1 comparison reply). Kept internal jargon out.

---

## Key Decisions Made
### Same product, new audience (not a product pivot)
- **Choice:** Keep Gurmej's bespoke corporate-events product + canonical copy; change only who it's sent to.
- **Rationale:** User correction — "keep the product the same, only to somebody else." The venue-Christmas concrete-offer idea was scope creep (that's P3's product).

### Employee-count floor 201+ (for the bespoke product)
- **Choice:** Raise the size floor to 201-2000 for both campaigns.
- **Rationale:** Bespoke managed events need companies big enough to run + budget them. (The "keep it small" answer only held for the venue-Christmas product, which was dropped.)

### Activation is the final gate
- **Choice:** Load the batch into paused campaigns; the first real send (activation) needs explicit go + a readiness check.
- **Rationale:** B5 — real cold emails to ~250 brand-new recipients, irreversible.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/analysis-scripts/meji_p2_new_audience_sample_2026-06-29.py` | Created | New-ICP sample sourcing (free search) |
| `context/analysis-scripts/meji_p2_batch_2026-07-01.py` | Created | First-batch sourcing (London/SE, with Apollo IDs) |
| `context/p2/p2-new-audience-sample-2026-06-29.{md,json,pdf}` | Created | 200-contact sample (Gurmej-approved) |
| `context/p2/p2-firstbatch-2026-07-01-candidates.json` | Created | 300 staged candidates (to reveal) |
| `context/drafts/gurmej-p2-retarget-2026-06-29.md` | Created | Gurmej retarget message |
| `context/pilot-routing.md` | Updated | 2026-07-01 changes block (P3 ramp, P2 pause, new ICP, staged batch) |
| Instantly (live) | Mutated | P3 ramp (limits); P2A+P2B paused |

Deleted (superseded): `piece2-sequence-concrete-offer-2026-06-29.md`, `piece2-sequence-new-audience-2026-06-29.md` (user deleted the proposed sequence; canonical `piece2-cold-copy.md` stands).

---

## Current Status
- **P3:** ACTIVE, ramped to ~90/day, 0% bounce, ~433 leads queued (~5 days runway, then hits the 3-city universe ceiling).
- **P2A/P2B:** PAUSED. Old 880 retired.
- **New P2 batch:** 300 candidates staged, NOT revealed/loaded/sent.
- **P1:** warm, ~337 queued (~2 weeks then finite/done unless Gurmej supplies more warm data).

---

## Next Steps
1. **Execute the P2 first batch** (see the handoff prompt): reveal (Apollo `bulk_match`, check credit balance first) → NeverBounce → load into P2A/P2B → activate (B5 gate).
2. Handle the old queued leads on load: P2A/P2B are paused with ~35 old queued leads; remove/pause those before activating so only new leads send (840 old completed are inert).
3. After first batch reads clean on deliverability, scale (more London/SE, then Midlands tier ~0.7k).
4. Ask Gurmej whether more warm contacts exist to extend P1 before it runs dry (~2 weeks).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/context/pilot-routing.md` (2026-07-01 changes block — current state of all campaigns)
- `workspace/clients/meji-media/context/p2/p2-firstbatch-2026-07-01-candidates.json` (the 300 staged candidates)
- `workspace/clients/meji-media/context/analysis-scripts/meji_p2_batch_2026-07-01.py` (batch sourcing; reveal/load stages not yet built)
- `workspace/clients/meji-media/context/analysis-scripts/meji_p2_full_pull_2026-06-18.py` (reference: `--enrich`/`--format` stages to adapt for the new batch)
- `workspace/clients/meji-media/context/analysis-scripts/meji_nb_verify.py` + `meji_p2_instantly_load.py` (NeverBounce + loader)

### Open Questions
- Reveal all ~253 with-email candidates, or a smaller first slice, given Apollo credit balance?
- Load target mechanics: reuse paused P2A/P2B (remove old queued + resume) vs anything else. Recommend reuse (canonical copy + mailboxes already configured).

### Working Notes
- Apollo FREE `api_search` returns only company name + `has_*` flags (no headcount/industry/domain values); those need paid reveal. Size/sector are still guaranteed by the server-side filter.
- Instantly `POST /campaigns/{id}/pause` needs a non-empty body (`{}`) or it 400s "Body cannot be empty."
- Instantly mutations: `PATCH /campaigns/{id}` (daily_limit), `PATCH /accounts/{email}` (daily_limit), `POST /campaigns/{id}/pause` / `/activate`.
- P2B drip rule (pilot-routing rule 6): NeverBounce valid+catchall only, ≤50/batch, check bounce between batches.
- Instantly rate limit 20/min → space calls ≥3.2s (see `meji_campaign_health_check.py` `api()`).

### Reference Materials
- Comparison data (2026-07-01): P1 723 contacted / 14 replies / 5 opps / 2.1% bounce; P3 104 contacted / 3 replies / 1 opp / 0% bounce.

---

## How to Continue
Use the handoff prompt (written this session) in a fresh chat: `/resume meji-media`, read the pilot-routing 2026-07-01 block, then reveal → NeverBounce → load → activate the staged first batch, stopping at activation for explicit go.

---

## Strategic Feedback

### What Worked Well This Session
- The design workflow + adversarial pass caught its own inflated numbers; grounding them against `cold-data-explainer.md` and live Apollo probes before anything reached Gurmej prevented over-promising.

### Suggestions
- The "change audience vs change product" distinction is the load-bearing lesson: when fixing a failing campaign, separate the targeting lever from the offer lever explicitly before proposing.

### System Health
- `md-to-pdf.py` has now failed on Edge (open-as-viewer collision) twice (2026-06-12, 2026-07-01), each needing a manual Chrome fallback. Candidate: add automatic Chrome fallback to the tool.
- Autonomy score: 2 human interventions this session (product-pivot correction; sequence deletion preference). B1 stop-hook fired ~3x on closing-offer phrasing and self-corrected each (structural gate working).
