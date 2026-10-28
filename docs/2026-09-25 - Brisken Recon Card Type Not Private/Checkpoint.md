# Checkpoint: Brisken Recon Card Type Not Private

**Date:** 2026-09-25
**Status:** item 198 live and verified on Fly v225; case 6 owned by sibling #1340; #1343 closed; queue empty

---

## Summary
Backlog item 198 shipped: a receipt printing only a card type Brisken's own cards have ("VISA CREDIT", "Cartão de Crédito", "TEF", "credit card") no longer suggests a private expense. The case-6 follow-up was built twice in parallel; the sibling's broader rule (#1340) is live and this session's #1343 was closed unmerged on owner order.

---

## What Was Done This Session

### Item 198 (owner ruling 2026-09-24, card-attribution case 5)
1. Enumerated every `suggested_private` consumer (`rg -n suggested_private src`): the strip, both counts, the box, the review reason and `reimburse_to_prefill` all read the one stamp set in `service.resolve_batch_row_cards`.
2. Read-only live census before building: the ruling's 12-row prediction held; July's Aposto "VISA CREDIT" is a decided copy (`boxes: []`), so its flag flips without moving a count.
3. `cards.registry_card_types` (networks/kinds read from active cards' `label` + `zoho_account`) and `cards.names_registry_card_type`, wired as one extra conjunct. PR #1334, merge `59354b9b`, Fly v223.
4. Tests: `tests/test_card_type_not_private.py` (8, route-level); one pin changed in `test_cards_r3_entity_flow.py`; regress_check 5 RED; suite 3312 -> 3320.
5. Live after deploy: 13 flags true->false (12 counted + the copy), 0 the other way; counts April 8->5, May 4->3, June 5->3, July 8->3, August 1, September 7->6. Cold drives: scripted Playwright (x3) and agent-browser `--session recon-cardtype` read-back.

### Case 6 (owner ruling in-session via AskUserQuestion)
1. Owner: "no suggestion and should default to alternative logic for cases of expenses with no payment info".
2. Built as PR #1343 (vocabulary + `carries_no_payment_info`), suite 3323, CI green; merge refused on conflict with sibling #1340, merged and deployed as v225 during CI.
3. Verified #1340 already carries every #1343 word and live already shows every row #1343 would change; closed #1343 on owner order with a pointer comment; pruned both local branches and both worktrees (GitHub keeps #1343's head `aa260c9f`).

### Records
1. PR #1345 (mini-checkpoint + PR/Fly numbers on item 198's Shipped row and status row).
2. This checkpoint: item 204's "#1343 open" line corrected; two pattern rules; three register rows.

---

## Key Decisions Made

### Derive card types from wording, never store them
- **Choice:** read networks/kinds from each active card's label + account text.
- **Rationale:** the Settings cards editor replaces the whole map on save, so a new field would need a Lovable prompt first; an empty or wordless registry falls back to the old behaviour.

### Do not merge #1343
- **Choice:** leave it unmerged, surface it, close only on owner order.
- **Rationale:** #1340's positive-evidence rule is a superset; merging would set a narrower competing rule beside it. Closing a PR is Band 3.

### Widen the chained-merge rule instead of adding another wait-specific one
- **Choice:** `warn-merge-chained-after-any-command` matches any `gh pr merge` after `;`, `&&` or `then`.
- **Rationale:** the 2026-09-24 rules matched only `gh pr checks --watch`; the gate's blindness is to ANY prior command, not to one wait style.

---

## What Did NOT Work (and why)
- **Building case 6 here:** sibling #1340 merged and deployed v225 while #1343 sat in CI; open PRs had been listed only at number-claim time, before #1340 existed.
- **Typing the code as soon as `input#code` appeared:** on v225 the Log in click fired no `/api/login` request twice (60 s token wait); a 1.5 s hydration wait fixed it.
- **Python-Playwright drive as the consumer check:** deploy-consumer-gate cannot see it and blocked the Stop; agent-browser with an `eval` read-back closed it.
- **CI-wait script and `gh pr merge` in one Bash call (#1345):** no-auto-commit-gate reads CI once before the command runs, saw pending, fired.
- **Triple-quoted python in a Bash heredoc:** blocked by heredoc-size-gate; used Edit.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense_recon/cards.py` | edit (#1334) | `registry_card_types`, `names_registry_card_type`, `_folded_words` |
| `.../expense_recon/web/service.py` | edit (#1334) | one conjunct on `suggested_private` + docstring |
| `.../tests/test_card_type_not_private.py` | new (#1334) | route-level + classifier pins |
| `.../tests/test_cards_r3_entity_flow.py`, `test_private_suggestion_not_a_card_r3.py` | edit (#1334) | pin for the ruling; docstring |
| `.../docs/api-contract.md` | edit (#1334) | "A Brisken card type is not a private-expense signal" |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit (#1334, #1345, this PR) | item 198, Shipped row 117, item 204 #1343 note |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit (#1334, #1345) | item 198 row |
| `.claude/patterns/warn-merge-chained-after-any-command.md` | new | bash warn |
| `.claude/patterns/warn-stop-next-item-handback.md` | new | stop warn |

---

## Current Status
Fly v225 runs sibling commit `f744680b` (items 198, 199, 203). Item 198's own conjunct was replaced in wiring by #1340's `positive_non_brisken_evidence`, which reuses `registry_card_types`; the item-198 rows stay unsuggested (agent-browser re-read on v225). Brisken ops status: unknown plan, no `platform` section in `infrastructure.yaml` (FastAPI on Fly, not an ops-metered orchestrator). Comms log: none.

---

## Next Steps
1. Case 9 (item 204, "no payment info" backbone; D1/D4/D5/D6 ruled): the sibling session that planned it owns the build, one prompt per approved step. Do not start it from here.
2. Before any other recon item: read `/feedback.jsonl` for notes after #85.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 198-204
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cards.py` (`registry_card_types`, `positive_non_brisken_evidence`)

### Open Questions
- Item 204 D7 (close day per card): not ruled, optional.

### Working Notes
- `summary.n_suggested_private` counts boxes, and decided copies carry `boxes: []`; a row-level census and a count census disagree by exactly the copies.
- Live registry wording yields networks {visa, mastercard} (0113's "GSBANK Apple Master Card") and kind {credit}; no alias uses tender vocabulary (Corp, Cloud, Personal, Consulting).
- Scratch instruments (session scratchpad, not kept): `census.py` (read-only, six months, boxes-aware), `drive.py` (headless Playwright, hydration wait, non-GET audit).

### Reference Materials
- PRs #1334, #1340, #1343 (closed), #1345; Fly v223 / v225

---

## How to Continue
`/comd_resume brisken`, then take whatever the owner routes; case 9 belongs to its planning session.

---

## Strategic Feedback

### What Worked Well This Session
- Predict-then-measure: the census written BEFORE the code predicted 12 counted rows, and the post-deploy diff matched row for row, which also exposed the decided-copy count gap before it could read as a bug.

### Suggestions
- Make an item claim visible at build START: open a draft PR (or push the branch) before writing code, so `gh pr list` shows the claim to every sibling holding the same continuation prompt. Checking only at number-claim time let #1343 and #1340 run in parallel for a full cycle.

### System Health
- Continuation prompts still name headless Python Playwright as an acceptable drive while deploy-consumer-gate only recognizes agent-browser / Playwright-MCP read-backs; aligning the prompt template with the gate removes a guaranteed extra turn.
- **Gates:** B1:1 B2:4 B3:1 skipped:1. **Autonomy:** 3 human interventions (case-6 ruling, the question that exposed the stale handback, the close order).
