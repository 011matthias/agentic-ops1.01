# Checkpoint: Brisken Expense-Recon Vision + Adjudication (WS2 / PR2)

**Date:** 2026-07-21
**Status:** PR2/WS2 built, merged (#315), and DEPLOYED to Fly with PR1; corpserv COA scope fix applied to the live `/data` volume. WS3 (matching) is the next build.

---

## Summary

Built and shipped WS2 of the "LLM improves, not copies" expense-recon work: the LLM
reads the ER PDF's receipt IMAGES (vision) to fill the ~half of summary rows that carry
no merchant, plus a deterministic Zoho-root-group adjudication gate so the tool's category
overrides the report's only on a heavy top-level mismatch. Merged #315, deployed PR1+PR2 to
Fly, and fixed a live COA-scope config gap that the new gate exposed.

---

## What Was Done This Session

### WS2 build (PR #315, merged + deployed)
1. **Vision receipt-image extraction** — new `ingest/expense_report_images.py`: renders the
   report PDF's receipt-image pages (skips the EXPENSE SUMMARY + trailer via the
   `REPORT SUMMARY BY CURRENCY` boundary), runs the existing `extract_receipt` per image, and
   maps each reading to its summary row (reference first, then amount+currency with page order
   as tiebreak). Fills the merchant (only when the summary lacked one) + line items; keeps the
   summary amount/currency/date as the deterministic matching backbone; records a
   `data_quality_note` on any vision-vs-summary disagreement.
2. **Vision stage** wired into `cli.reconcile()` between `_load_receipts` and
   `categorize_receipts`, gated by `categorization.vision_receipts` + an LLM client + the
   `expense_report_pdf` source (`_apply_vision_receipts`).
3. **Deterministic adjudication** — `categorize.adjudicate_receipts` / `adjudicate_categorization`:
   compare the tool's category/account vs the report's `zoho_category` at the Zoho root-group
   (both resolve through the chart). Different root => `ai_override_heavy` (the review queue);
   same root / unresolvable => `kept_er` / `review_unresolved`. `EXPENSE_CATEGORY_ROOT_GROUP`
   static fallback for a top-8 category with no GL leaf; a mapped root not in the run's
   chart/scope stays conservative.
4. **Surfacing** — `Category Decision` column in the reconciled CSV; new fields
   `Categorization.decision` + `Receipt.data_quality_note` (serialize round-trip + workbench view).
5. **Hosted wiring** — `reconcile()` now builds the categorizer chart from the `coa_validation`
   block when there's no `zoho` block (`_resolve_categorizer_chart`), so the account override AND
   the adjudication fire on hosted runs (previously no-ops). `_build_config` turns vision on with
   the LLM (`EXPENSE_RECON_VISION_RECEIPTS` off-switch).
6. **Tests** — +27 (vision extraction + image->row mapping in new `test_expense_report_images.py`;
   adjudication gate + static fallback + scope filtering in `test_categorize_llm.py`; Category
   Decision in `test_reconciled_csv.py`; updated 2 PR1 tests for the new categorization block).
   Full module suite **717 passed**. New files ruff-clean.

### Deploy + live fix
7. Deployed PR1+PR2 to `brisken-expense-recon.fly.dev` from a clean `origin/main` worktree
   (`flyctl deploy`, owner `matneumann07@gmail.com`); verified healthz 200 + new image.
8. Broadened the corpserv COA scope in `context/coa-provision.json` (added `CorpServ | OpeEx`)
   and uploaded it to `/data/coa-provision.json` via sftp (user-run, classifier-blocked for the agent).

### Live verification (real ER-00216 + corpserv COA + OpenAI key)
9. Vision filled all 9 previously-blank vendors (FMA FOOD, BAR MOLINARI, PASSAGUAI, SAMMONTANA,
   PRET, DB Fernverkehr, SNCF, ANNADA, + one more); 15-16 rows got real line items.
10. Adjudication under the full CorpServ operating scope: 15/20 correct "kept ER" + a genuine
    catch (Annada Rouen, booked Parking, is a meal -> correct override). Under the OLD provisioned
    scope (`MS | OpeEx` only) the gate over-fired (17 spurious overrides) -> the config finding below.

---

## Key Decisions Made

### Premise correction: ADOBE/ANTHROPIC are receiptless, not ER receipts
- **Finding:** the plan/checkpoint said ADOBE/ANTHROPIC are ER-00216 receipts mis-labeled
  "Travel Expense | Food". They are NOT — they are receiptless STATEMENT software charges;
  three get FX-false-paired into `judgment_required` against unrelated EUR Food receipts, which
  is why the CSV showed them beside "Travel Expense | Food".
- **Consequence:** WS2 (categorization/vision) cannot make them "post Software" via adjudication;
  that is a MATCHING problem = WS3. WS2 fixes the real confirmed root cause (the 9 vendorless
  summary rows). Verified empirically by a deterministic reconcile of the real data.

### Corpserv COA scope must include CorpServ | OpeEx (config, not code)
- **Finding:** corpserv (org 822741658) uses ENTITY-bucket root groups (`CorpServ | OpeEx`,
  `MS | OpeEx`), not semantic ones. The 2026-07-01 provisioning scoped corpserv to `MS | OpeEx`
  only, which EXCLUDES Dirk's actual travel accounts -> the categorizer can't reach them and the
  adjudication over-fires on every travel row.
- **Fix (applied):** added `CorpServ | OpeEx` to the corpserv `scope_groups`. Under the fixed
  scope the gate behaves correctly (15/20 kept ER).

### Adjudication design (owner, carried from PR1 plan)
- Deterministic root-group comparison; the gate GOVERNS insertion (heavy mismatch inserts the
  tool's finding, same-root keeps ER). No LLM adjudication call.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/ingest/expense_report_images.py` | Created | Vision receipt-image render + extract + image->row mapping |
| `.../categorize.py` | Modified | `adjudicate_receipts` + `EXPENSE_CATEGORY_ROOT_GROUP` + resolver |
| `.../cli.py` | Modified | Vision stage + `_resolve_categorizer_chart` (coa_validation fallback) + adjudication step |
| `.../matching/types.py` | Modified | `Categorization.decision` + `Receipt.data_quality_note` |
| `.../output/reconciled_csv.py` | Modified | `Category Decision` column |
| `.../web/serialize.py` | Modified | round-trip the two new fields |
| `.../web/service.py` | Modified | `_vision_receipts_on` + vision in `_build_config` + `data_quality_note` in `_receipt_view` |
| `.../tests/test_expense_report_images.py` | Created | vision + image->row mapping tests |
| `.../tests/test_categorize_llm.py`, `test_reconciled_csv.py`, `test_web_llm_default.py` | Modified | adjudication, Category Decision, updated PR1 block tests |
| PR #315 | Merged to main | the above, deployed to Fly |
| `context/coa-provision.json` | Modified (gitignored) | corpserv scope + `CorpServ | OpeEx`; uploaded to `/data` |

Ledger writes (this checkpoint, session log, INDEX, context YAML, friction register, status file)
are LOCAL only — the shared working tree has sibling-session uncommitted ledger edits; committing
would entangle them (G1). Batch onto a `docs/...` PR later.

---

## Current Status

- **PR1 + PR2 (#313 + #315): merged AND DEPLOYED** to `brisken-expense-recon.fly.dev` (healthz 200,
  new image live). The LLM-owns-category + vision + adjudication pipeline is now live for Chris.
- **Corpserv COA scope fix applied** to `/data/coa-provision.json` (added `CorpServ | OpeEx`).
- **WS3 (matching): not started** — the real fix for the ADOBE/ANTHROPIC FX-false-pairs.
- Platform: expense-recon runs on **Fly** (not Make/n8n) — no infra reconciliation needed.

---

## Next Steps

1. **Build WS3 (PR3) in a fresh session** — card as a first-class matching signal + FX-judgment
   enriched with card + optional second-chance pass over unmatched. This is what actually fixes
   ADOBE/ANTHROPIC (currently FX-false-paired). Plan: `~/.claude/plans/plan-out-how-we-playful-boole.md`.
2. **Passive check:** on Chris's next corpserv SPA run, confirm `Category Decision` reads mostly
   "kept ER" (not a wall of overrides), confirming the scope fix took in the wild.
3. **Optional:** watch per-run vision cost (~$0.14/run, 21 high-detail images vs the ~$0.01 text-only
   estimate); `EXPENSE_RECON_VISION_RECEIPTS=0` is the off-switch if it needs capping.

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/plan-out-how-we-playful-boole.md` — WS3 = Workstream 3 (matching)
- `src/expense_recon/matching/deterministic.py` — the matcher (card signal + tie-break go here)
- `src/expense_recon/matching/judgment.py` + `llm/client.py` `_FX_JUDGMENT_PROMPT_TEMPLATE` — FX-judgment card enrichment
- `src/expense_recon/cli.py` `reconcile()` — where a second-chance unmatched pass slots in
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- WS3 `blend_card_weight` default (plan says 0.0 = tie-break only, keeps `test_match_score.py` byte-for-byte) vs a numeric weight (needs renormalizing 0.55/0.30/0.15 + score-test updates).
- The corpserv chart's entity-bucket roots make the adjudication coarse there; acceptable (conservative, review-queued) but worth revisiting if precision matters.

### Working Notes (do not re-derive)
- **ADOBE/ANTHROPIC are receiptless statement charges**, NOT ER receipts. ER-00216 is all
  travel/food/tolls. The FX-false-pair (ADOBE $16.23 <-> €16.20 Food receipt, etc.) is the
  matching problem WS3 fixes. Deterministic reconcile confirms: 1 matched (FLiX), 18 judgment
  (incl. 3 software-vs-Food FX pairs), 115 unmatched.
- **9 of 20 ER summary rows have no vendor** (the real WS2 root cause). Vision fills them.
- **Corpserv chart (822741658)** roots = `CorpServ | OpeEx` (23 acct, incl. travel E100010-*) +
  `MS | OpeEx` (49 acct, incl. IT: Cloud Subscriptions). The provisioning scope now includes both.
- Vision cost ~$0.14/run; the sftp shell escapes `\` (use forward slashes), won't overwrite
  (put to `.new.json` then `mv`), and has no `quit`/`rm` (Ctrl+C to exit); the app scales to zero
  so `fly machine start 48ee133c363758` before any `fly ssh`.
- **Deploy owner** `matneumann07@gmail.com`; deploy from a clean `origin/main` worktree.

### Reference Materials
- Live app: https://brisken-expense-recon.fly.dev (operator code vault "Expense Recon App" = `mn040307`)
- OpenAI key: vault "OpenAI Brisken" field `api_key`
- COA: `context/zoho-books-coa.json`; provisioning: `context/coa-provision.json` -> `/data`
- PR #313, #315 on `011matthias/agentic-ops1.01`

---

## How to Continue

`/resume brisken`, read the plan, then build **WS3 (PR3, matching)** in a fresh session. Cut a
`client/brisken/...` worktree off latest `origin/main` (`git fetch origin main` first — concurrent
sibling sessions share this clone). Ship via CI-green auto-merge; the Fly deploy is Band-3.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding the design against the REAL data BEFORE building (examine the PDF page structure, run
  a deterministic reconcile, inspect the COA) caught the ADOBE premise conflation and the corpserv
  scope gap that the plan carried — the "resolve the mapping against real data first" discipline
  earned its keep.
- The two-scope live verification (real hosted scope vs full operating scope) turned a "the gate
  over-fires" surprise into a precise, actionable config finding with evidence.

### Suggestions
- The corpserv scope gap traces to the 2026-07-01 provisioning being derived from a root-group
  breakdown that read the entity buckets as if semantic. Worth a one-pass re-check of every
  entity's scope_groups against what its card statements actually contain.

### System Health
- The Fly `flyctl ssh`/`sftp` classifier block forced a user-run handoff for the `/data`
  provisioning upload; the handoff instructions failed on foreseeable specifics (backslash
  escaping, put-no-overwrite, scale-to-zero machine-not-started), costing several round-trips and
  user frustration. A `docs/references/` note on the Fly sftp gotchas would have made the first
  handoff correct.
- Autonomy score: 1 human-execution-adjacent intervention (the sftp handoff friction, forced by
  the classifier block + imperfect handoff commands). The build itself was 0 corrections.
</content>
