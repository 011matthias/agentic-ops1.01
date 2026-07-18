# Checkpoint: Brisken Match Fixtures + Ingest Hardening

**Date:** 2026-07-17
**Status:** SHIPPED — PR #263 merged (squash) on CI green; labels.csv accepted + check-green for all six bundles

---

## Summary

Blocks 1b–2 of the Brisken match-accuracy optimize target: sourced the six
bundle-month ER PDFs (found locally — no Graph needed), fixed four real
ingest gaps the rebuild surfaced (all six reports had failed the printed-total
cross-check), rebuilt the bundles production-shape, ran the full
propose → decide → accept → check labeling flow (141/218 receipts labeled,
77 excluded as ambiguous), and shipped the file-loadable MatchingConfig
(Block 2). One PR (#263), three commits, merged on green.

---

## What Was Done This Session

### ER PDF sourcing (Next Step 1)
1. Fly volume intake archive: empty (`/data` has no `runs/`/`intakes/` dirs —
   the app has archived no uploads). Machine started + stopped for the check.
2. Graph mail scan of both allowlisted mailboxes: the six report numbers do
   not appear in mail (the five `dirk__ER-*.pdf` from 07-16 are different
   reports that did travel by mail).
3. Local-disk sweep found all six in `C:/Users/neuma_p1qrsic/Desktop/Downloads/`
   (ER-00181/00183/00194/00214/00215/00216). Copied into their bundle dirs.

### ER-PDF ingest hardening (PR #263, commit 1c887b8)
4. Parse-verified all six with the production ingest: every report failed the
   to-the-cent printed-total cross-check. Diagnosed from raw text (enumerated
   FX lines, TOTAL lines, meta labels across all six):
   - `BRL3,099.99` / `DKK35.00` ISO-prefixed originals invisible to the
     symbol-only money regex → USD conversion read as the original.
   - Inline numbered rows (`3. 05/17/2026 FLiX $155.61 $155.61`) silently
     absorbed into the previous row — one row lost in 4 of 6 reports,
     shifting every later `document_id` (fixture-stability hazard).
   - Number format is per-token, not per-currency (EUR EU-style, BRL/DKK
     US-style in the same report) → `_parse_amount` sniffs separators.
   - `Expense Location :` meta (188 rows) normalized to Location.
5. After the fix: all six parse with 0 issues, row counts match the June
   ground truth exactly (45/36/20/50/29/38), per-currency sums equal the
   printed totals to the cent. +12 regression tests.

### Bundle rebuild + labeling (Next Steps 2–3)
6. All six `run.json` receipts blocks → `{path: ER-*.pdf, source:
   expense_report_pdf}`; superseded `labels-proposed*.csv` / `run-pdf-*.json`
   experiments deleted (W1).
7. `label propose` on all six: 4 AUTO / 188 PICK / 26 NONE; E3 (Zoho's own
   USD conversion) carries the FX months as predicted, E2 only on native-USD
   rows, E1 never (CSV statements have no FX detail).
8. Accept pass via an explicit conservative decision engine (scratchpad,
   discarded): payment-mode card refs (Cloud 6013/2155 → `no_charge`,
   sub-card filtering where the statement's Card column carries it) +
   offline E1-grade corroboration from the four 2026 statement PDFs' FX
   originals + global conflict resolution. Result: **95 confirmed +
   46 no_charge = 141/218 labeled (65 %), 77 excluded**. Confirm evidence:
   32 stmt-PDF FX originals, 3 labeling-conclusive AUTOs, 1 unique exact
   base-amount, 59 sole-E3.
9. Found + fixed a labeling bug running the real accept: decision token
   `exclude` was written through as status (VALID_STATUSES wants `excluded`)
   → every excluded row failed `label check`. Fixed + round-trip test
   (commit 0a958c5). `label check` now **Result: OK on all six**, full
   coverage, zero warnings.

### Block 2 — file-loadable MatchingConfig (commit 601af82)
10. Blend weights (0.55/0.30/0.15) moved onto `MatchingConfig`; all scalar
    tunables + `fx_rate_bands` loadable via `from_dict`/`from_file` (unknown
    keys refuse; file bands REPLACE defaults). `config/match-tuning.json`
    shipped mirroring code defaults with a parity test as the drift alarm —
    this file is the optimize-loop's writable asset. run.json gains optional
    `matching.tuning_path`; learned memory merges on top. End-to-end CLI
    runs verified (positive: report produced; negative: missing file fails
    loudly). Suite 457 passed / 21 skipped.

---

## Key Decisions Made

### Fix the ingest BEFORE accepting labels
- **Choice:** Treat the parser gaps as a blocker for the accept pass, not a
  later "enrich" step.
- **Rationale:** Wrong currencies poison evidence, and `document_id` is
  row-index-based — a dropped row shifts every later id, so labels built on
  the broken parse would be invalidated by the very extractor improvement
  the optimize loop is for.

### Conservative accept policy, richer-than-pipeline evidence
- **Choice:** Confirm only on (a) conclusive E1/E2, (b) offline stmt-PDF FX
  original equality, or (c) a sole surviving E3 candidate after card
  filtering; everything contested/tied → exclude; off-card payment mode →
  no_charge (unless a conclusive amount hit contradicts — then exclude).
- **Rationale:** RECIPES constructed-metric protocol (ambiguity excluded,
  never guessed) + sanctioned truth/test separation (labels may use evidence
  the scored pipeline never sees).

### Train/held-out split recommendation (for Block 3)
- **Train:** 2026-03 ER-00214 (32 labeled), 2026-04 ER-00215 (21),
  2025-06 ER-00194 (39) — 92 labeled rows; keeps both BRL months and the
  big Cloud-card `no_charge` cohort (card-scoping signal).
- **Held-out:** 2026-05 ER-00216 (13), 2024-10 ER-00181 (15),
  2024-11 ER-00183 (21) — 49 rows (~35 %); one strong-label 2026 month +
  both historic months, and DKK never appears in train (currency
  generalization is tested, matching the prior checkpoint's lean).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/.../ingest/expense_report_pdf.py | Modified (PR #263) | ISO-ccy money tokens, inline rows, per-token format sniffing, Expense Location meta |
| workspace/.../tests/test_expense_report_pdf.py | Modified (PR #263) | +12 regression tests mirroring the real shapes |
| workspace/.../src/expense_recon/labeling.py | Modified (PR #263) | decision `exclude` → status `excluded` mapping |
| workspace/.../tests/test_labeling.py | Modified (PR #263) | exclude round-trip coverage |
| workspace/.../matching/deterministic.py | Modified (PR #263) | blend weights on MatchingConfig; from_dict/from_file loaders |
| workspace/.../src/expense_recon/cli.py | Modified (PR #263) | run.json `matching.tuning_path` wiring; docstring sample |
| workspace/.../config/match-tuning.json | Created (PR #263) | the optimize asset (mirrors defaults; parity-tested) |
| workspace/.../tests/test_match_tuning.py | Created (PR #263) | 5 tuning tests incl. defaults-parity drift alarm |
| workspace/clients/brisken/status/p1-expense-reconciliation.md | Modified (PR #263) | fixture + ingest element rows |
| context/.../csv/by-month/*/{ER-*.pdf, run.json, labels-proposed.csv, labels.csv} | Created/Modified (gitignored) | production-shape bundles + accepted ground truth |

---

## Current Status

main carries PR #263 (squash-merged 2026-07-17 13:38Z, all CI green). All six
bundles are production-shape (CSV statement + ER PDF) with accepted,
check-green labels.csv. The optimize asset (`config/match-tuning.json`)
exists and is wired. Platform ops line: p1 is a custom FastAPI/Fly build —
no workflow-engine ops tier to report. Session ran in worktree
`../agentic-ops1-match` (branch `client/brisken/p1-match-fixtures`, now
merged; safe to delete).

---

## Next Steps

1. **Block 3 — the scorer**: `tools/scorers/recon-match-accuracy.py`
   (maximize; fixture checksum self-check; held-out floor guard per the
   split above). Pinning needs the user's explicit `SCORER_LOCK_ALLOW=1` —
   user-order-only, do not self-serve.
2. **Manifest + run**: `project: brisken`, tag `brisken-match-accuracy-v1`,
   own worktree, mode continuous (RECIPES multi-project section).
3. Optional label deepening: 77 excluded rows could shrink with 2026-05
   and 2024 statement PDFs (only 4 cycles exist locally; ER-00216's month
   has none) — ask Dirk only if the scorer proves label-starved.

---

## Context for Next Session

### Files to Read First
- `docs/optimize/RECIPES.md` (constructed-metric + multi-project protocol)
- `workspace/.../src/expense_recon/labeling.py` (label check = the fixture-integrity core the scorer reuses)
- `workspace/.../config/match-tuning.json` (the writable asset)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Scorer metric shape: pairing accuracy only, or accuracy + no_charge
  correctness (a matcher that "finds" a charge for a no_charge receipt is a
  false positive worth penalizing)?
- Do the 77 excluded rows stay excluded forever, or revisit after the
  matcher improves (labels are versioned by the bundle dirs; re-propose is
  cheap)?

### Working Notes
- The six ER PDF originals also remain in `Desktop/Downloads/` — sweep the
  local disk FIRST next time an artifact was ever locally present; both
  remote probes (Fly volume, Graph mail) were misses this session.
- labels.csv format: `document_id,transaction_id,status,source,evidence`;
  statuses confirmed/excluded/no_charge; `label check --config run.json`
  exits 1 on structural violations — the scorer should shell out to it (or
  reuse `cmd_check`) as its fixture self-check.
- Transaction ids are `{account_id}:{csv_row_index}` (row 2 = first data
  row) — labels break if statement.csv rows are reordered; never resort.
- The decision engine was scratchpad-only (W1) — the labels + evidence
  strings in labels.csv and the reasons in this checkpoint are the durable
  record. Reason distribution: 32 stmt-pdf-FX, 59 sole-E3, 3 conclusive,
  1 unique-exact-base; excludes: 40 multi-candidate, 28 no-survivor, 7
  contested, 1 conclusive-vs-off-card conflict, 1 two-conclusive.
- The tuning file uses REPLACE semantics for `fx_rate_bands` (a file
  without a band removes it) — deliberate, so the optimizer can prune.
- Shared-tree hazard observed live: a sibling session deleted
  `graph_mail_scan.py` + `_graph_file_meta.json` from the shared context
  dir between two of my directory listings. Worktrees isolate code but
  `context/` is a single shared copy by design.

### Reference Materials
- PR #263 https://github.com/011matthias/agentic-ops1.01/pull/263
- Prior checkpoint: `docs/2026-07-17 - Optimize Onboarding + Brisken Match Labeling/Checkpoint.md`

---

## How to Continue

`/resume brisken`, then Block 3 per Next Steps: author the scorer against the
six bundles with the train/held-out split above, PR it, and STOP before
pinning — `SCORER_LOCK_ALLOW=1` is a user order. Then manifest + worktree +
`/comd_optimize`.

---

## Strategic Feedback

### What Worked Well This Session
- Running the REAL accept flow immediately exposed two shipped-yesterday
  bugs (the `exclude`/`excluded` vocabulary mismatch and the ingest gaps)
  that 440 green tests had not — real-data execution beats synthetic
  coverage for freshly shipped CLI flows.
- The printed-total cross-check (built 07-16 as a "nice to have") was the
  single signal that caught all four parser gaps. Self-validating parsers
  pay for themselves the first time the input distribution shifts.

### Suggestions
- The six ER PDFs sat in `Desktop/Downloads/` the whole time while two
  remote sourcing probes ran. A one-line "sweep local disk first" step in
  sourcing plans (brief or skill) would have saved both probes.

### System Health
- Sibling sessions sharing this clone's `context/` can delete files another
  session is mid-way through using (observed live this session). Worktrees
  fix code isolation; shared gitignored context has no equivalent. Low
  urgency, but if it recurs: a per-session "context files in use" note or
  copy-to-scratchpad-before-use discipline.
- Autonomy score: 0 — fully autonomous session.
