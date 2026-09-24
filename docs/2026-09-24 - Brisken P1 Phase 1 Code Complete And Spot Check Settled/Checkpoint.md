# Checkpoint: Brisken P1 Phase 1 Code Complete And Spot Check Settled

**Date:** 2026-09-24
**Status:** Phase 1 direct-to-GL backend complete on main, NOT deployed; the SPA half has no prompt yet

---

## Summary

Queue items 6 and 4b shipped (the categorization gate says it is bucket-path
only, the paid-through card is checked, the export gate judges GL batches by
Dirk's marking), the deferred comms sweep is written, and Dirk settled the six
SPOT-CHECK accounts as N. The deploy is blocked on a Lovable prompt that no
session ever wrote.

---

## What Was Done This Session

### Code (all merged, none deployed)
1. **#1302 `373a65dc` (item 6 + backlog 184).** `categorization_gate.py` reports
   `BUCKET PATH` and "GL path ... NOT measured"; calibrate JSON carries
   `path: bucket`, `gl_path_measured: false`. `zoho.accounts.resolve_paid_through`
   (numeric, in the org's chart, active, not DNU, `credit_card`, name matches the
   run's card) runs inside `build_expense_payload`; `_plan_kwargs` passes
   `card_name`. 15 tests, 7 wiring points red first.
2. **#1305 `175f697e` (4b).** `CoaGate.curated_org`, set by `_build_coa_gate`
   when the config carries `gl_entity_orgs`; `classify_account` then uses the
   curated marking (`NOT_EXPENSE_RELEVANT`, `OUTSIDE_CURATED_LIST`,
   `CHART_ORG_MISMATCH`). Real chart + provisioning: GL 56 Y diverted / 105 N
   passed -> 0 / 0; bucket unchanged. 12 tests incl. a gate-vs-resolver
   agreement test over every sheet account; 6 wiring points red first.
3. Module suite 3267 -> 3294 passed / 2 skipped. Docs PRs #1304, #1308.

### Records
1. comms-log: INTERNAL Phase 1 decision record; INBOUND Dirk confirms the six
   SPOT-CHECK accounts stay N; `last_contact` 2026-09-24.
2. Memory: `project_brisken_comms_sweep_deferred` deleted (trigger fired);
   `project_brisken_coa_expense_relevant` marks the SPOT-CHECK rows settled.
3. Review copy for Dirk built from the pinned workbook (source sha `800c0887`
   left untouched): `context/expense-reconciliation/CoA BRISKEN - 6 accounts for
   Dirk to decide 260924.xlsx`.
4. Pattern rule `warn-owner-publish-without-named-prompt` (stop event).

---

## Key Decisions Made

### Relabel the gate, do not re-point it
- **Choice:** the gate keeps measuring the bucket path and says so; no GL gate built.
- **Rationale:** the GL chain's model tier needs an LLM, so no deterministic
  fixture can score it; the brief asked for a relabel, and a false green was the defect.

### Keep two old tests as bucket pins
- **Choice:** `test_coa_provision` / `test_mixed_entity_export` drop
  `gl_entity_orgs` after `apply_to_config`.
- **Rationale:** they pin the chart rule; since item 3 the injector makes every
  hosted config GL, and a pre-Phase-1 batch config is exactly the key-less one.

### Review copy, not an edit of the source
- **Choice:** Dirk reviewed a highlighted copy; the pinned workbook is untouched.
- **Rationale:** the compiled asset pins the workbook's sha; editing it breaks provenance.

---

## What Did NOT Work (and why)
- **The brief's module baseline of 3263:** origin/main after #1295 was 3267; #1293 added 4 tests the figure missed.
- **Two provisioning tests left as written under 4b:** synthetic codes (`E500`, `C100`) in real curated org ids became GL batches via `apply_to_config` and refused `OUTSIDE_CURATED_LIST`.
- **Telling the owner to "publish the screen update":** there was nothing to publish. The Phase 1 prompt was never written; the Lovable repo and live bundle have 0 hits for `category_refused` / `gl_accounts` / `gl_revision`.
- **The watch-then-merge pattern rule on #1308:** it shipped in #1290, one commit after the primary clone's HEAD (`fa8104aa`), and the hooks read `.claude/patterns` from that clone, 25 commits behind, so it never fired.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/categorization_gate.py`, `calibrate.py` | Modified | bucket-path label (#1302) |
| `src/expense_recon/zoho/accounts.py`, `expense_post.py`, `reconcile_month.py`, `ingest/chart_of_accounts.py` | Modified | paid-through check (#1302) |
| `src/expense_recon/coa_gate.py`, `cli.py` | Modified | curated export gate (#1305) |
| `tests/test_paid_through_item_184.py`, `tests/test_coa_gate_curated_item_4b.py` | Created | caller-level tests |
| `docs/zoho-gl-categorization-architecture.md`, `status/p1-*.md` | Modified | step 6, item 184, 4b recorded |
| `context/comms-log.md` (gitignored) | Modified | two entries + frontmatter |
| `.claude/patterns/warn-owner-publish-without-named-prompt.md` | Created | friction fix |

---

## Current Status

On main, NOT deployed: #1277, #1281, #1286, #1291, #1295, #1302, #1305. Item 190
(card filter) is applied AND live (Lovable commits 13:13 UTC; live bundle has
`cardScope.`, `receipt_months`, `no_card`, controls valid). Card statements for
9693 / 0113 / 6013 / 8311 are in SharePoint per the owner. Ops: platform
unknown plan (no `platform` assessment in infrastructure.yaml).

---

## Next Steps
1. Card statements: read-only Graph walk of each entity's admin site > finance > banks > chase (0113 is GS Bank Apple Card, look outside chase); download to `context/expense-reconciliation/statements/`; put the upload into Criss's months to the owner as a decision.
2. Record Dirk's SPOT-CHECK confirmation in tracked docs; delete the review copy once Excel closes it.
3. Item 190 step 4: bundle audit + the section 7 table cold; mark applied.
4. Write `docs/lovable-gl-accounts-prompt.md` (contract first), hand it in a four-backtick fence.
5. After the owner publishes it: bundle check, deploy, cold consumer drive.
6. Pattern-rules gate staleness: make the hook read rules from `origin/main` (or fail loud) when the checkout is behind.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (items 4-6, 4b paragraphs)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (for the SPA prompt)

### Open Questions
- Owner: load the four cards' statements into Criss's months, or hand them to her?
- Dirk: card 3645's chart account (item 172).

### Working Notes
- Card identities from `context/zoho-books-coa.json`: 9693 and 8311 are Chase (Cloud Services 697686691); 6013 is "VISA 6013 TRAVEL EXPENSE" (Cloud, bank unnamed); 0113 is "GSBANK Apple Master Card 0113" (Corporate Services 822741658).
- Bundle check without editing the tracked tool: load `tools/lovable-bundle-audit.py` via importlib and swap `NEW`.
- The two older pattern rules `warn-chained-checks-watch-and-merge` and `warn-merge-chained-after-checks-watch` are duplicates.

### Reference Materials
- Lovable repo `011matthias/brisken-expense-review`; live SPA `expenses.brisken.com`

---

## How to Continue

Paste the continuation prompt handed in this session's reply (the one listing card statements first); it carries the ESTABLISHED facts and the SESSION LOOP.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring the 4b claim on the real chart before and after (56/105 -> 0/0) turned an estimate into a pinned number, and the same script proved bucket batches unchanged.

### Suggestions
- When a checkpoint says a deploy "waits on the owner", name the prompt file; the new stop rule enforces it, and it would have surfaced the missing prompt four checkpoints earlier.

### System Health
- Hooks enforce from a clone that lags `origin/main` by 25 commits while sibling sessions share it, so a same-day structural fix can be absent where it matters. Autonomy: 1 human intervention (the owner's "publish button not available" exposed the missing prompt).
