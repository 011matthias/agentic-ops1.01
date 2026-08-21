# Checkpoint: Brisken Cards R3 Entity-Less Batches

**Date:** 2026-08-21
**Status:** Cards R3 shipped (PR #559), deployed, live-verified

---

## Summary

Cards R3, the headline round of the 2026-08-21 feedback wave, is live:
entity-less batch creation with per-receipt entity resolution from the
paying card, the card-review strip, hint-to-card assignment with
settings learning, and the audited refresh-master-data endpoint. A
3-lens adversarial review ran pre-commit; every HIGH finding was fixed
and pinned as a test before merge.

---

## What Was Done This Session

### Cards R3 (PR #559, merged d5976bb7, deployed to Fly)

1. Deleted the legal-entity guard in `create_expense_batch` AND
   `generate_expenses`; batch label handles the empty case.
2. One resolution chain (`resolve_batch_row_cards`): field override ->
   batch `card_hints` exact assignment -> card registry
   (`resolve_hinted_card_ex`, ambiguity refused, alias never overrides
   contradicting digits, masked-PAN last-run-only) -> stamped value ->
   `needs_entity` review state. Shared by grid rows
   (`card`/`entity_source`/`payment_hint`), export, paid-through, and
   statement graduation.
3. `card_review` strip server-grouped (unresolved hints with
   generic/ambiguous markers, resolved cards, needs-entity counts);
   summary gains `n_needs_entity`.
4. `POST /api/expense-batches/{id}/cards`: exact hint assignments;
   `learn: true` persists identifying tokens (single-digit-run rule;
   multi-run hints learn as exact-string aliases; generic tenders never
   learn). Duplicate hints and existing-slug `new_cards` are 400s;
   learn validates only touched entries.
5. `POST /api/expense-batches/{id}/refresh-master-data`: audited
   re-derive from live settings; preserves assignment-target cards;
   reports row-entity impact.
6. Export ruling pinned: `(entity - assign)` placeholder, never a
   block; assign-after-export + re-export folds it in.
7. Adversarial hardening: generic-tender word-subset vocabulary
   (EN/PT/DE, compounds); legacy-map generic keys and stored generic
   aliases inert at read time; refused ambiguity blocks the
   paid-through flat map; `_card_account` digit compare tightened to
   exact-length; statement graduation bakes chain entities into the
   matcher pool (pre-fix an assigned entity-less batch reconciled 0
   silently); `restore_set_aside_file` and the attach final write now
   commit under `_BATCH_ADD_LOCK` against a fresh re-read (mid-attach
   mail adds append as unmatched instead of vanishing).

### Process

1. 3 adversarial reviewers (wrong-money, state/lifecycle, API/contract)
   executed repros against the diff; consolidated fix wave applied
   before any commit; every HIGH has a named regression test.
2. Bookkeeping in-PR: backlog item 10 R3 row + review-residue tail,
   loop brief (baseline 1178/2, rounds renumbered), workstream status
   row, Lovable prompt `docs/lovable-cards-r3-prompt.md`.
3. Memory `project_brisken_expense_recon_usability_loop` updated.

---

## Key Decisions Made

### Single-digit-run learn rule

- **Choice:** a hint teaches a card digit only when it carries exactly
  one 3-8 digit run; multi-run hints learn as exact-string aliases.
- **Rationale:** no deterministic way to tell the card number from
  expiry/auth/BIN noise; the executed repro showed "Visa 1672 exp
  12/2026" teaching year 2026 and mis-resolving unrelated cards.

### Chain verdict binds the money path

- **Choice:** when the registry chain refuses (ambiguity) or resolves a
  card without a Zoho account, the paid-through flat map is BLOCKED for
  that row (placeholder, not guess).
- **Rationale:** the grid said "unresolved - review" while the CSV
  posted money to a first-endswith-match account; grid == export is the
  round's core contract.

### Graduation bakes the chain

- **Choice:** statement attach stamps chain-resolved entities into the
  matcher pool; the mismatch warning now judges against actual pool
  entities.
- **Rationale:** matching is entity-scoped; pre-fix, a card-assigned
  entity-less batch reconciled 0 with no warning (executed repro).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| src/expense_recon/cards.py | modified | generic vocab, learn rule, resolver hardening, cfg round-trip, stamping |
| src/expense_recon/cli.py | modified | guard removal + post-OCR entity stamping |
| src/expense_recon/web/service.py | modified | chain, card_review, assign/refresh endpoints' logic, attach bake + lock, restore lock |
| src/expense_recon/web/app.py | modified | two new endpoints |
| src/expense_recon/output/zoho_expense_export.py | modified | entity placeholder, hint-account slot, blocked flat map, exact-length compare |
| tests/test_cards_r3_entity_flow.py | added | 30 tests incl. 12 adversarial pins |
| tests/test_generate_expenses.py, tests/test_web_expense_batches.py | modified | old guard tests -> new contract |
| docs/lovable-cards-r3-prompt.md | added | the UI half (owner applies) |
| status/p1-{improvement-backlog,recon-loop-prompt,expense-reconciliation}.md | modified | loop bookkeeping |

(All under `workspace/clients/brisken/automations/expense-reconciliation/`
unless prefixed.)

---

## Current Status

R3 live on `brisken-expense-recon.fly.dev` and verified by probe:
healthz 200, unauth 401, operator login 200, the real 13-row January
batch serves `card_review` (4 unresolved hints incl. 'Visa ...1672',
generics marked) with all rows still (Cloud Services, batch) — the
deploy moved nothing on existing batches by design. Prod
`settings["cards"]` is empty (5 composed cards), so the stored-
generic-alias round-trip residue has no live exposure. Suite baseline
1178 passed / 2 skipped; calibrate gate OK. Ops status: platform plan
unknown (no `platform` section in infrastructure.yaml for the Fly
apps — pre-existing).

---

## Next Steps

1. Feedback-wave round: intake quick wins (delivered files + Month
   column) + delete month (brief item 1).
2. Body-only mail handling (Dirk's real held mail is the acceptance
   test), then memory validate/adjust, then language + receipt
   visibility, then Cards R4 (owner answers pending).
3. Owner applies `docs/lovable-cards-r3-prompt.md` (+ the two earlier
   cards prompts); DOM-probe the SPA after publish. Until applied, the
   old SPA shows a card-resolved entity with no explanation — hand the
   prompt promptly.
4. Operator data entry: card entities for 0113/6013/9693/8311 in the
   Cards editor; then refresh-master-data on the January batch and
   assign 'Visa ...1672' / 'brisken' hints once.

---

## Context for Next Session

### Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md (paste-in brief, current)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 11-17 open)
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (wave design)

### Open Questions

- R4 owner calls (backlog item 10): per-entity export files,
  cash/personal tenders as cards, per-entity zoho_account, presets-file
  retirement.
- Review residue (backlog item-10 tail): refresh re-stamp semantics vs
  memory-origin stamps; settings PUT whole-map RMW race (cosmetic).

### Working Notes

- p2 status files flagged stale (30-61d) by the sweep — p2 sessions'
  scope, untouched here.
- Friction register archived this checkpoint (>200 KB advisory).
- Pre-existing ruff F821 (`Callable`) at cli.py:1347/1404 — on
  origin/main before this round, CI does not gate this subtree.

### Reference Materials

- PR #559; live origin https://brisken-expense-recon.fly.dev

---

## How to Continue

`/resume brisken`, paste `status/p1-recon-loop-prompt.md`, start the
intake quick wins round in the `agentic-ops1-recon` worktree off a
fresh `origin/main`.

---

## Strategic Feedback

### What Worked Well This Session

- The mandated pre-commit adversarial review earned its cost: three
  independent lenses found four executable HIGH classes the 1166-test
  suite missed (year-token learning, flat-map guessing past a refused
  chain, settings replacement via new_cards, the silent 0-match
  graduation), all fixed and pinned before merge.

### Suggestions

- The graduation 0-match class suggests a standing invariant test
  shape: "whatever the grid shows must be what downstream consumers
  compute from" — a shared-pass audit across view/export/attach would
  have caught F1 without a reviewer.

### System Health

- Autonomy: 0 human interventions (fully autonomous session).
- The gate-skip-iteration-3x detector false-positived twice on reviewer
  attack-suite runs (similar uv invocations that were not a fix loop);
  candidates discarded with reason. If reviewers become routine, the
  detector may need an agent-context exemption.
