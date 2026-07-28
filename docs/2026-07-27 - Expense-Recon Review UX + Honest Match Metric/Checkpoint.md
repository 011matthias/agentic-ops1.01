# Checkpoint: Expense-Recon Review UX + Honest Match Metric

**Date:** 2026-07-27
**Status:** Backend shipped (Fly v38→v42); several SPA halves pending Lovable publish

---

## Summary

A multi-day expense-recon working session driven by owner review of the live
tool: fixed a "the app is broken" report (a deleted-run dead-end, not an
outage), fixed a regression that had silently broken every hosted upload for
~a day, and built four review-UX improvements plus an honest match metric.
Closed the session by proving the "24.5% match is bad" concern was a
denominator artifact, not a matcher failure.

---

## What Was Done This Session

### Broke-in-production fixes
1. **Run-not-found dead-end** (SPA #4, published): a `/runs/<id>` URL for a
   deleted run showed "Failed to load run" with no way back. Now a plain
   deleted-run message (EN/PT) + Dashboard button on any load failure. The
   backend was healthy the whole time; the screenshot was a stale tab.
2. **Hosted-run Zoho-creds regression** (PR #435, Fly v38): the master-data
   ship (v35) injected a `zoho:` block with no `coa_source`, which the chart
   builder read as a live-API pull → every hosted upload died on "Zoho
   credentials missing" (Fly has no ZOHO_* vars). Added `coa_source:"none"`.
   Had broken ALL hosted runs for ~a day; caught by the owner's manual test.

### Review-UX build-out
3. **Emailed-receipt upload + FX suggest floor** (PR #437, Fly v39):
   `POST /api/runs/{id}/transactions/{tx}/receipt` attaches a receipt that
   arrived by email to an unmatched charge; `matching.fx_judgment_suggest_floor`
   (0.2) unbinds the p=0.10 absurd suggestions the reviewer flagged.
4. **Per-receipt image preview** (PR #440, Fly v40): persist the vision join's
   ER-PDF page mapping + serve it via `GET …/receipts/{doc}/image`.
5. **Structured FX breakdown** (PR #445, Fly v41): each cross-currency
   candidate carries an `fx` object (charge vs receipt vs Zoho's own
   conversion, implied vs booked rate, the gap) so an uncertain pair is
   reviewable without decoding the prose reason.
6. **Honest receipt-based match rate** (PR #446, Fly v42): `receipt_match_rate`
   + `n_receipts_matched` alongside the charge-based figure.

### Diagnosis (no build)
7. Confirmed the matcher is near ceiling: local no-LLM run vs the 21 labelled
   April true pairs → 18/21 clean deterministic, ~0 false positives. The
   24.5% headline was reconciled ÷ all-94-charges where 57 charges never had a
   receipt. Statement-PDF lever tested and rejected (only the wrong-cycle
   Chase PDF is on hand, and Chase PDFs don't expose per-charge foreign
   amounts — the "upload the PDF" advisory doesn't hold for this data).

### SPA prompts handed to owner (Lovable)
PT-translation completion, attach-receipt UI + cross-currency badge fix,
receipt quick-look, FX comparison panel, needs-review row restructure, and
the honest-metric header reframe.

---

## Key Decisions Made

### Do not tune the matcher further
- **Choice:** treat 18/21 deterministic / ~0-wrong as near-ceiling; no more
  matcher tuning without new labelled months.
- **Rationale:** the low headline was the denominator, not accuracy; the
  remaining unmatched are receiptless charges no algorithm can pair.

### Honest metric is additive, not a replacement
- **Choice:** add `receipt_match_rate` beside the existing `match_rate`; SPA
  leads with the receipt rate.
- **Rationale:** a client-facing number Criss relies on; additive keeps the
  charge figure available and is reversible.

### FX breakdown computed server-side
- **Choice:** build the `fx` comparison object in `service.py`, not the SPA.
- **Rationale:** api.ts mandates the frontend does zero business logic;
  rate-direction correctness belongs where the currency logic lives.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `…/web/service.py` | edit | `coa_source:"none"`, `attach_emailed_receipt`, `_fx_breakdown`, `fx` on candidates, `receipt_match_rate` |
| `…/web/app.py` | edit | manual-receipt POST, receipt-image GET |
| `…/web/store.py` | edit | `update_run_snapshot` |
| `…/web/serialize.py` | edit | `receipt_image_page` round-trip |
| `…/matching/deterministic.py` | edit | `fx_judgment_suggest_floor` tunable |
| `…/matching/types.py` | edit | `receipt_image_page` field |
| `…/ingest/expense_report_images.py` | edit | keep the page index in the join; `render_receipt_page` |
| `…/cli.py` | edit | `coa_source` none-path; suggest-floor unbind |
| `…/tests/*` (5 files) | edit/add | regression tests for each of the above |
| `…/status/p1-expense-reconciliation.md` | edit | this session's six elements (PR #447) |
| SPA repo `brisken-expense-review` | PR #4 | run-not-found recovery |

---

## Current Status

Backend at Fly **v42**, healthy (healthz 200). All six backend changes
live-verified via the API. `platform: unknown plan, ~?/? ops/mo` (no platform
section for brisken — orchestrator-less client). Six SPA prompts are with the
owner; only run-not-found recovery + the earlier PT/attach-receipt work are
confirmed published. The receipt quick-look control was NOT visible in a DOM
probe of the live SPA — either unfinished or unpublished.

---

## Next Steps

1. **Owner: publish the pending Lovable changes** (receipt quick-look, FX
   panel, needs-review restructure, honest-metric header) and confirm each
   with a DOM probe, not a label.
2. **Run one fresh reconciliation** (real upload) to exercise previews on
   vision-mapped receipts, the suggest floor, the FX panel, and the honest
   metric end to end. Prefer a real statement over the sample CSV.
3. **Delete the two "2838" test runs** — both carry verification artifacts
   (a 1×1 test image on the ANTHROPIC charge).
4. Pre-existing, unchanged: brief Criss + send her the SPA URL (she has only
   the old Fly URL, which now answers raw JSON 401); dev-notifier is live +
   scheduled; localize backend advisory/error text (owner decision).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (the roll-up)
- `…/automations/expense-reconciliation/BLUEPRINT.md`, `ANNEALING.md`

### Open Questions
- Which Lovable prompts actually landed on the published SPA? (probe, don't trust labels)
- Does the owner want backend-generated advisory/error text localized to PT?

### Working Notes
- The matcher ceiling for April is 21 true pairs (15 receipts are ambiguous /
  unscored); deterministic gets 18. The FX-review bucket holds the ~3
  remaining true pairs + speculative noise the suggest-floor now trims.
- Statement-PDF path is a dead end for this data: `20260404-statements-2838-.pdf`
  is the wrong billing cycle (ingested 125 txns, matched 9, orphaned 25
  receipts), and text extraction found no per-charge foreign amounts (the
  "foreign" hits were "no foreign transaction fees" boilerplate).
- GitHub had repeated connectivity blips this session; pushes needed retry loops.

### Reference Materials
- Fly app `brisken-expense-recon` (owner `matneumann07@gmail.com`); deploy from a clean origin/main worktree.
- SPA repo `011matthias/brisken-expense-review`; live at `brisken-reconcile-dash.lovable.app`.

---

## How to Continue

`/comd_resume brisken`. The backend is done for this round; the open work is
owner-side (publish + verify the SPA halves, run a fresh reconciliation).

---

## Strategic Feedback

### What Worked Well This Session
- Diagnosing before building: the "24.5% is bad" turn ended in a metric fix +
  a "don't tune the matcher" decision, not wasted tuning, because the honest
  accuracy was measured against labelled ground truth first.
- Every backend change was live-verified against the real run via the API, not
  declared done on a green build.

### Suggestions
- The receipt-based rate should have existed from the first hosted run; the
  charge-based denominator was a latent AI-tell that a working tool looked
  broken. Worth a scan for other single-number metrics with misleading
  denominators across client dashboards.

### System Health
- **Autonomy: 2 human interventions** (one model-framing correction — the run
  executes on Fly even though the owner drives it from Lovable; one mid-turn
  scope addition). Not elevated.
- The B1 stop-gate fired ~5 times on closing-message deferrals and caught every
  one; the structural gate is holding, but the authoring habit (ending on
  "want me to…" / "say the word") kept re-triggering it. Residual is discipline,
  not a missing gate.
