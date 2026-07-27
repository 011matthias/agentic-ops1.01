# Checkpoint: Expense-Recon Categorization UX (Review-by-Exception)

**Date:** 2026-07-27
**Status:** Backend complete + deployed (Fly v47); SPA render is the only remaining half (owner-driven Lovable paste)

---

## Summary
Adopted a live sibling session's near-complete bulk folder-receipt-upload feature and shipped it, then on owner direction reworked expense-recon categorization review into a "review by exception" model: a server-computed per-row `review` state (ready/check/pick/none) plus a safe bulk Confirm-all, designed and adversarially verified by an 8-agent workflow before any code. Six PRs (#449-#456), Fly v43 -> v47, 841 tests green.

---

## What Was Done This Session

### Bulk folder-receipt upload (adopted, not rebuilt)
1. Enumerated worktrees (B7) before building; found a sibling session actively editing `client/brisken/receipts-folder-bulk` (files touched ~2 min prior). Surfaced the collision; owner chose take-over. Adopted the branch, ran its suite, found **2 tests red on wrong view-key names** (`matched_document_id`->`chosen_document_id`, `member_ids`->`members`) the sibling never ran; fixed to the real contract (assertions still verify constraint-1 + dedup). 810 pass -> #449 (v43).
2. Closed a half-wired contract: `ingest_receipts_folder_into_run` stored a `folder_ingest` summary "so the SPA can show it" but `build_view` never exposed it -> surfaced it on the run view (#451).

### Categorization visibility (the "it doesn't show in UI" thread)
3. Diagnosed from code: matched rows carried **no row-level category** and the posting **account was absent from the view entirely**; only receiptless charges had `charge_category`. Added `posting_category = {category, zoho_account, source}` resolved server-side for matched AND receiptless rows, override-aware, mirroring the export's `_ai_category_cells` (#453, v45).

### Review-by-exception (the approved concept)
4. Built a private mockup (artifact `afb9422d`); owner approved ("sounds good").
5. Ran an **8-agent workflow** (investigate -> design -> adversarial-verify) that caught **4 high-severity holes before any code**: partial-uncategorization leaking into READY (a categorization-less line is silently dropped from the joined source), confirmed-MATCH wrongly treated as confirmed-CATEGORY, `review_unresolved` slipping past Check, and READY mislabeled "account verified" on non-adjudicated runs.
6. Implemented the corrected classification: `row.review = {state, reason, reason_code}`, run-level `adjudication_available`, `ready_confirm_pairs`, and `POST /decisions/confirm-ready` (confirms only ready ∩ pending ∩ matches; caps 1000 + reports remainder; reversible in-app pre-export) (#454, v46). Added `reason_code` for PT localization + split uncategorized/partial (#455, v47).

### Infra
7. Found the module CI never exercised the web/SPA-API layer (`importorskip` without the `web` extra); switched to `uv run --extra dev --extra web pytest` + self-triggering path (#452, test job 16s->27s, web layer now covered).

---

## Key Decisions Made

### Take over the sibling WIP instead of building parallel
- **Choice:** adopt `receipts-folder-bulk`. **Rationale:** ~complete, matched the spec point-for-point; a parallel build guarantees a merge collision (the exact branch-isolation failure mode).

### review classification lives server-side, not in the SPA
- **Choice:** compute Ready/Check/Pick in `build_view`. **Rationale:** the codebase's "frontend does zero business logic" rule; the same computation also defines the safe Confirm-all set.

### Confirm-all = confirm-matched ∩ ready, never /bulk
- **Choice/Rationale:** adversarial-verify showed `/bulk` can confirm an unsettled top candidate; intersecting the matcher's pending auto-pick set with review.state=='ready' is structurally safe (always a subset of `outcome.matches`).

### Detect uncategorized lines STRUCTURALLY, not from the source string
- **Rationale:** `_row_posting_category` drops a categorization-less line, so the joined `source` reads all-trusted; only iterating `matched_rec.line_items` catches the gap that would let Confirm-all ratify an uncleanly-posting row.

### reason (English prose) + reason_code (stable enum)
- **Rationale:** Criss reads PT; the SPA localizes off the code, not the server prose.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `web/service.py` | edit | `posting_category`, `resolve_review`/`_matched_category_review`, `ready_confirm_pairs`, `adjudication_available` |
| `web/app.py` | edit | `POST /decisions/confirm-ready` + import |
| `web/serialize.py`, `cli.py` | edit | folder-upload glue (`card_last4` round-trip, `build_match_cfg`) |
| `tests/test_web_review_state.py` | new | 25-case classification matrix + Confirm-all safety invariant |
| `tests/test_web_charge_categorization.py` | edit | posting_category cases |
| `tests/test_web_receipts_folder_upload.py`, `test_entry_status.py` | edit/new | folder feature |
| `.github/workflows/expense-recon-tests.yml` | edit | run the web tests in CI |
| `status/p1-expense-reconciliation.md` | edit | v43/v45/v46/v47 rows |

---

## Current Status
Backend complete and live on **Fly v47** (healthz 200, API-only gate intact, 841 pass / 2 skip). PRs #449-#456 all merged to main. brisken platform: no `platform` section in `infrastructure.yaml` (expense-recon is FastAPI-on-Fly, not an orchestrator plan) — no ops-audit applicable. comms-log current (0 days). The SPA render is the only remaining half and is owner-driven (Lovable).

---

## Next Steps
1. **Owner:** paste the review-by-exception Lovable prompt into the SPA editor + Publish (`brisken-reconcile-dash.lovable.app`); verify with a DOM probe (merge != live).
2. **Owner:** the earlier folder-upload Lovable prompt (picker/zip + ingest-progress + suggestions) is still pending paste from #449.
3. Run `checkpoint_scaffold.py archive-register` (register at 417 KB) — deferred this checkpoint under session pressure.
4. `p2-lead-gen-general.md` is 36 days stale — refresh when next in that workstream.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (v45/v46/v47 rows)
- `.../src/expense_recon/web/service.py` — `resolve_review`, `_matched_category_review`, `ready_confirm_pairs`
- The workflow output `tasks/wp8brsmde.output` (ephemeral) — the full decision table + 4 verified highs; read before any change to `resolve_review`.

### Open Questions
- Should Confirm-all be **hard-gated** (disabled) on non-adjudicated runs, or is honest labeling via `adjudication_available` enough? Shipped the labeling; owner may want the harder gate.
- Should a `review_unresolved`-only adjudication surface distinctly from `ai_override_heavy`? Currently both fold into Check (fine).

### Working Notes
- Confirm-all reversibility is **in-app + pre-export only** (undo = re-POST `/decisions` status pending, chosen_document_id null). Once exported to Zoho Books it is not un-posted.
- The example run's deterministic keyword categorizer classifies 2 rows "ready" with NO LLM — that is why the confirm-ready smoke test asserts `confirmed == len(ready_pending)`, not 0.
- `reason_code` values: uncertain_match, uncategorized, partial_uncategorized, category_account_mismatch, vendor_guess, unknown_provenance, receiptless_suggested; null for ready/none.

### Reference Materials
- Concept mockup artifact: https://claude.ai/code/artifact/afb9422d-ff05-4f9a-bdbe-05167f3e5253
- Both Lovable prompts are in this session's conversation transcript.

---

## How to Continue
Backend is done and live; remaining work is SPA-side (Lovable, owner-driven). If iterating the backend classification, read `tasks/wp8brsmde.output` (the verified decision table) first so a change does not reopen one of the four fixed highs.

---

## Strategic Feedback

### What Worked Well This Session
- The 8-agent adversarial-verify workflow earned its cost concretely: 4 real high-severity holes fixed **before** code, not after a wrong deploy. Verification-before-implementation, not verification-theater.
- Adopting the sibling WIP and immediately running its suite surfaced the 2 red tests it left behind; shipping half-verified WIP would have regressed the review view.

### Suggestions
- `posting_category` and `review` both derive from the same per-line-item scan of the matched receipt; a later refactor could share one pass. Minor, non-urgent.

### System Health
- **Autonomy:** ~1 user redirect (the "categorization doesn't show in UI" gap I had implied was handled) + 3 stop-b1-gate deferral blocks self-corrected in-session. Not elevated on the human axis.
- The closing-deferral reflex recurred 3x (CI-fix offer, reject-semantics offer, checkpoint offer); the input-classifier B1 primer fired but the generation-time reflex persists — an ~8th-day same-pattern occurrence. Containment (stop-b1-gate) holds; the reflex itself is uncured.
- Friction register at 417 KB — archive due.
