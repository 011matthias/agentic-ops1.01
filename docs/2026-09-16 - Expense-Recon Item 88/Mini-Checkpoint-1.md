# Mini-Checkpoint: Expense-Recon Item 88

**Date:** 2026-09-16
**Status:** Item 88 shipped and live (Fly v142); items 87 and 82 handed to a fresh session
**Type:** mini

---

## Summary
Publishing a month now saves its corrections to memory, because Publish is the app's month sign-off. The same corrections are never counted twice, and a failed save never fails the publish. No month has been published yet, so the first automatic save happens at the first publish.

## What Was Done
- Read first: "month sign-off" in code is `POST /api/runs/{id}/publish` (SPA copy: "Open a run, resolve every row, then hit Publish"; disabled with "Resolve the blockers above before publishing"). `/api/operator/state` `published_runs` is empty. `/api/memory` counts read merchant_category 103, merchant_entity 0, field_correction 0, vendor_alias 0, merchant_fx 0.
- PR #940 (merge `f54e79e6`), Fly v142. `commit_month_memory` (used by Publish and by the button), `memory_commit_digest` (verdicts, overrides, header edits, adds and deletes, no timestamps), and a new `memory_commits` table: the run summary could not hold the digest because every re-match rebuilds it. The publish reply gains `memory` (saved + learned / unchanged / error). Suite 1968 -> 1974 passed / 2 skipped. Four regress proofs bite; two that `regress_check.py` reported as "RED (no pytest summary line)" were reproduced by hand with pytest's own failure output before being counted.
- Live after deploy: both payloads unchanged (July 11 unmatched receipts + 2 set aside with reasons; August boxes on every row), memory counts unchanged, nothing published. Driven: July Matching renders Publish and Commit learnings, no fallback. The publish reply has no renderer and no live case; publishing Criss's month is a write, and a scratch month risks claiming pooled mail, so the behaviour is route-tested only.
- SPA half: `docs/lovable-memory-at-signoff-prompt.md` (publish toast with the saved count; the save button's tooltip mentions publishing).

## Current Status
Four SPA prompts pending the owner's paste (PROMPT-STATUS Not applied): unmatched reasons (83 + 75), expense boxes (84), controls as buttons (85 + 86), memory at sign-off (88). Session at critical pressure by tool-call count; items 87 and 82 are not started.

## Next Steps
1. Item 87: read July's card-review strip as note #33's author saw it; list its rows and the path each would take (Cards R3 assignment, Define card via `seen_undefined`, suggested private); check whether "the tool will not remember them" is true for digit-bearing hints (R3 says they learn as aliases). Then decide: copy defect, or one "fix card" action per row.
2. Item 82: simulate ECB monthly rates (EXR/M.USD.EUR.SP00.A, EXR/M.BRL.EUR.SP00.A, BRL:USD cross) with `tools/recon-match-attribution.py` on the six bundles and both live months; report which July and August pairs change bucket before building.
3. After each prompt is published: `tools/lovable-bundle-audit.py` with the names in PROMPT-STATUS, then a cold drive.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 87, 82; Shipped rows 52-54)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last three sections)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied)
