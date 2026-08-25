# Checkpoint: Recon Match Accuracy (date+amount program)

**Date:** 2026-07-23
**Status:** COMPLETE — scorer + matcher structure + tuning shipped, deployed to Fly, live-verified. Follow-through backlog remains (SPA publish, Zoho scope, spec reconciliation).

---

## Summary
Owner directive "match on date + time + amount, most accurate" → verified time-of-day is absent in every source, so the program is date+amount. Built an objective accuracy scorer over the 6 labelled months, restructured the FX matcher against it, ran a locked hill-climb, promoted the winner into the deployed defaults, and confirmed on the live app that Criss's April month reconciles 20 clean + 13 teed-up review with 0 wrong matches — byte-identical to a local replay.

---

## What Was Done This Session

### Measurement (PR #404, merged)
1. `tools/scorers/recon-match-accuracy.py` (pinned): +1.0 determ-correct / +0.3 deferred-correct / −2.0 determ-wrong or no_charge false positive over 95 confirmed labels; SCORE = train (four 2025-26 months); 2024 months held out.
2. `tools/recon-accuracy-guard.py` (pinned): invariant on all 6 bundles + holdout floor + no-new-holdout-wrongs + wrong-ceiling; PASS/FAIL output only (numeric leak control); imports the scorer by path so the two cannot drift.
3. Pre-change baseline recorded: determ_ok 3/95, train 8.9, holdout 5.5.

### Matcher structure (PR #405, merged)
1. `MatchType.FX_BASE_AMOUNT` — deterministic off the ER report's own per-receipt USD conversion (the E3 signal, 0/92 at baseline); fires even when the printed total failed to parse.
2. Self-derived per-run reference rates (statement-FX-line median n≥1 wins, else receipt-rate median n≥3, band-clamped; configured rates overlay).
3. Band candidates scored by amount agreement under the best rate (not midpoint distance).
4. **Bilateral-uniqueness gate** — clean rate-derived evidence auto-resolves ONLY when exclusive both ways (the labeling `auto_pairs` criterion). Without it, 38/46 no_charge receipts auto-matched to coincidences. This was the load-bearing fix, found by measurement.
5. Score-aware assignment sort key (amount+date = 0.85 of the blend); `contested_receipts` counter in calibrate.
6. 7 new tunables registered + shipped in `config/match-tuning.json` at defaults.

### Tuning + rollout (PR #406 + follow-up promotion, merged; deployed)
1. Optimize run `brisken-recon-tuning-v1`: 7 rounds, PLATEAU stop, one keep — `fx_base_amount_match_pct` 0.02→0.01 (knee bracketed). Dead ends + inert levers journaled.
2. Winner promoted into the `MatchingConfig` dataclass default (the Docker image ships only `src/`; acceptance test: empty-asset score == tuned-file score, 31.5 identical counts).
3. Deployed to Fly; live April re-run verified.

### Ledger (PRs #407, #408, merged)
ANNEALING resolved-entry, p1 status element row (+ stale label-fixture row corrected to re-validated-trustworthy), session shard.

---

## Key Decisions Made

### date+amount only (not date+time+amount)
- **Choice:** Drop time-of-day from the matching key.
- **Rationale:** Verified absent in Chase CSV/PDF, Zoho ER PDF, vision schema, and all domain types. Owner accepted. Receipt-photo till-times have no bank-side counterpart, so they could only ever be display context.

### Review-zone deferral + bilateral-uniqueness, not looser thresholds
- **Choice:** Clean rate-derived evidence resolves deterministically only when the pairing is unique both ways; 2–13% deviation defers to judgment.
- **Rationale:** The first ladder scored 89/95 deterministic but auto-matched 38/46 no-charge receipts — coincidences live inside the clean 2% band in dense months. The fixture's own `auto_pairs` rule (uniqueness) is the correct gate; precision must own the matches bucket.

### Promote tuned value into code default, not just the tuning file
- **Choice:** `fx_base_amount_match_pct=0.01` lives in the `MatchingConfig` default.
- **Rationale:** The hosted Docker image ships only `src/` and never reads `config/match-tuning.json`. A tuned value only reaches production as a default. CI drift test keeps file + default in lockstep.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| tools/scorers/recon-match-accuracy.py | Created | Pinned accuracy scorer (#404) |
| tools/recon-accuracy-guard.py | Created | Pinned anti-overfit guard (#404) |
| tools/scorers/PINS.json, tools/guard-pins.json, tools/INDEX.md | Modified | Pin registrations + manifest rows |
| src/expense_recon/matching/deterministic.py | Modified | FX ladder, self-derived rates, uniqueness gate, sort key, tuned default (#405/#406) |
| src/expense_recon/matching/types.py | Modified | `MatchType.FX_BASE_AMOUNT` (#405) |
| src/expense_recon/calibrate.py | Modified | `contested_receipts` counter (#405) |
| src/expense_recon/output/report_xlsx.py | Modified | Surface FX_BASE_AMOUNT reason (#405) |
| config/match-tuning.json | Modified | 7 new tunables + tuned match_pct 0.01 (#405/#406) |
| tests/test_fx_ladder.py | Created | 17 tests pinning the ladder + uniqueness + band-flip regression |
| tests/test_deterministic_matching.py | Modified | One legacy test updated to review-zone-defers semantics |
| docs/optimize/brisken-recon-tuning-v1/ | Created | RUN.md, holdout-baseline.json, results.tsv, SUMMARY.md |
| workspace/clients/brisken/automations/expense-reconciliation/ANNEALING.md | Modified | Resolved-entry 2026-07-23 |
| workspace/clients/brisken/status/p1-expense-reconciliation.md | Modified | Element row + label-fixture row correction |
| docs/sessions/2026-07-23-recon-match-accuracy.md | Created | Session shard (#408) |

---

## Current Status
All 6 PRs (#404–#408) merged to main. Tuned matcher deployed to Fly (brisken-expense-recon.fly.dev). Live April re-run: 94 tx → 20 clean deterministic (18 fx_base_amount + 2 fx_reference) + 13 teed-up review, invariant OK, 0 parse errors, byte-identical to a local no-LLM replay. Scorer arc: train 8.9 → 30.8 (structure) → 31.5 (tuned); determ-correct 3 → 55/95; 0 wrong deterministic matches at every step. Module suite 775 green; calibrate exit 0.

Platform: p1 backend is FastAPI on Fly (not Make/n8n/Trigger); no `platform` ops section applies. No infrastructure.yaml drift check needed (no Make scenarios).

---

## Next Steps
1. **card_accounts for 2838** (autonomous-capable): the COA is readable with the current Zoho token — enumerate candidate Chase bank/card accounts from coa-provision + zoho-books-coa.json, propose the mapping, set via `PUT /api/settings` on owner confirm.
2. **F3 / F9 backlog** from the 2026-07-22 SPA shard: in-flight runs visible on the dashboard; run rename/delete (then delete the 3 test runs 8074aa2bf7d9 / 8751a4045f42 / f03f14a47a25 + the 07-21 Chase run).
3. **Spec-vs-build reconciliation** (chosen big item, own session): all 28 sections of the functional spec vs shipped reality; map Dirk's 4 feedback notes onto the gap register.
4. **G2 / F7:** upload-form hint that a per-card xlsx unlocks posted-row skip + writeback; PT locale for Criss.

**User-action gates (surface once, do not nag):** (a) press Publish in the Lovable dashboard to make SPA PR #3's settings UI live; (b) re-consent the Zoho Books token with expense/bill read scope to unblock the memory seed.

**Owner decisions to surface once:** send Criss the SPA link + operator code (testing is done); whether to build matcher v2 (vendor/context signals) for the ~14 date+amount-inseparable no_charge coincidences.

---

## Context for Next Session
### Files to Read First
- docs/sessions/2026-07-23-recon-match-accuracy.md (this program)
- docs/sessions/2026-07-22-recon-spa-test.md (the SPA backlog this feeds into)
- workspace/clients/brisken/status/p1-expense-reconciliation.md
- docs/optimize/brisken-recon-tuning-v1/SUMMARY.md (read before any matcher v2 — dead ends journaled)

### Open Questions
- Do the ~14 remaining no_charge coincidences justify a matcher v2 (vendor/context signals), or are they acceptable review-queue noise? Date+amount alone cannot separate them.
- Is a per-month FX reference-rate settings entry worth wiring, or do self-derived medians suffice for hosted runs? (Self-derived covered the live April run without any configured rate.)

### Working Notes
- **Time-of-day is genuinely absent** — do not revisit as a matching key. Verified across all ingest paths + the vision schema; every domain date is `datetime.date`.
- **The uniqueness gate is the crux.** Base-amount agreement within 2% is NOT conclusive alone in dense months (June-2025: 26/31 no-charge receipts sat within 2% of some charge). Any future loosening of `fx_base_amount_match_pct` re-opens that false-positive surface — the knee is bracketed at 0.01 (0.005 loses, 0.02 loses).
- **Reference path needs its 3% headroom** — a self-derived month median deviates 1–3% from each receipt's own rate by construction; tightening `fx_reference_match_pct` to 0.015 was the worst round (25.7).
- **Circularity is watched, not ignored:** the scorer prints per-evidence-tier determ_ok every round. Gains were NOT E3-only — the E1-rich 2024 holdout improved (5.5→5.7, 13/22 deterministic).
- **Tuning file ≠ hosted behavior.** The Docker image ships only `src/`; hosted matching = code defaults + settings-injected inline rates. Keep tuning file and dataclass defaults in lockstep (CI drift test enforces).
- Live run ids this session (unpublished test runs, safe to delete once F9 lands): f03f14a47a25 (tuned April).

### Reference Materials
- Scorer: tools/scorers/recon-match-accuracy.py; guard: tools/recon-accuracy-guard.py
- Optimize journal: docs/optimize/brisken-recon-tuning-v1/{RUN.md, results.tsv, SUMMARY.md, holdout-baseline.json}
- PRs: #404 (scorer+guard), #405 (structure), #406 (tuning+promotion), #407 (client ledger), #408 (session shard)
- Memory: project_optimize_s1_recon_scorer_design (COMPLETE), project_brisken_expense_recon_master_data

---

## How to Continue
The accuracy program is done and live. Pick up with the follow-through backlog: start autonomous (card_accounts mapping proposal, F3/F9 dashboard + run management), surface the two user-action gates and the two owner decisions once, and schedule the spec-vs-build reconciliation as its own session. Work from a worktree off origin/main at a short path; the shared clone has live siblings.

---

## Strategic Feedback

### What Worked Well This Session
- Plan-mode with parallel explorers + adversarial design review caught the circularity/overfitting traps BEFORE any code — the uniqueness-gate need was anticipated in the adversarial pass, so the 38/46-false-positive result was diagnosed in minutes rather than shipped.
- "Measure first, then change code" (scorer as PR-1) meant every subsequent change had an objective before/after, and one of my own findings (B6 analog: the first ladder design) was killed by the number rather than by opinion.

### Suggestions
- The two standing user-action gates (Lovable Publish, Zoho scope re-consent) have blocked recon follow-through across three sessions now. Batching both into one 5-minute owner task would unblock the SPA settings UI and the memory seed together.

### System Health
- Autonomy score: 0 — fully autonomous session (3 instrumented candidates all classified as gates-working-correctly, no real interventions).
- The optimize harness handled a first-time client project cleanly (prior-art check, lock-on, guard-every-round, journal). The one friction was a CI drift-test failure on #406 because the tuned file and the default were in separate PRs briefly — resolved by cherry-picking the promotion into the same PR. Worth a note in the optimize skill: when a tuned value promotes to a code default, file + default must ship in ONE PR (the drift test is atomic).
