# Mini-Checkpoint: Brisken Recon Case 9 No Payment Info Plan

**Date:** 2026-09-25
**Status:** Planned and approved; backlog item 204 merged (#1346); five build prompts written, none run
**Type:** mini

---

## Summary
Planned case 9 of the card-attribution map, a receipt that prints no usable card, end to end. The work was read-only against the live months: seven months, 267 counted receipts, Fly `f744680b`. Each lever was scored against ground truth, and the owner took four decisions. The technical appendix is backlog item 204; five build prompts follow.

## What Was Done
- **Census.** 34 receipts print nothing, 12 only a Brisken card type, 7 an unrecognised phrase. Coverage per card came from `coverage[]` (keys `card_key` / `statements` / `period_*` / `n_transactions`).
  - The 2838 family is filed by calendar month.
  - 9693 and 1176 are filed by cycles closing on the 4th.
  - January, May and June have no statement.
- **Code traced.** Three places explain the open rows:
  - Twin lending walks reference groups only, so a Stripe invoice never takes the card its own receipt prints.
  - A receipt settled by a neighbour month's statement gets `settled_by` but no card, because `settled_charge_cards` skips borrowed docs.
  - No card cycle exists anywhere. The PDF's `Opening/Closing Date` is parsed and then discarded.
- **Levers scored leave-one-out:**

| Lever | Right / wrong / silent | Checkable rows |
|---|---|---|
| Vendor name (item 200) | 18 / 3 / 122 | 143 |
| Billing-account key (Stripe invoice prefix, all evidence agrees, at least 2) | 34 / 0 / 30 | 64 |
| Recurring charge | 44 / 8 | 229 |

  The recurring-charge lever becomes a suggestion only. Of the live no-card pairs, 2 of 30 are wrong. Both are human-labelled, and in both the vendor words disagree (`vendor_pct` below 50).
- **Evidence read live:**
  - 10 receipt files via `GET /api/runs/{id}/receipts/{doc}/image`.
  - 7 mail bodies via `GET /api/inbound/{archive}/body`.
  - The local 9693 cycle PDFs, parsed with the module parser. 20260704 holds July's AWS 3,352.59.
- **Owner decisions (2026-09-25):**
  - D1: calendar-month exports.
  - D4: key the card memory on the billing account (accepted after a plain-language re-explanation).
  - D5: the matcher guard, yes.
  - D6: Criss's OpenAI pick stays on its own row; the other rows follow the case-9 logic.
- **Shipped:**
  - PR #1346: item 204, merged at `80b058cf`.
  - PR #1348: a status-file paragraph.

## What Did NOT Work (and why)
- **Asking D4 in technical terms ("billing account, invoice-number prefix"):** the owner answered "i dont understand this please elaborate. draw a superficial explanation up aswell". What landed was a second pass with the Anthropic accounts drawn out (account, then card, then how many times).
- **`parse_statement_pdf_tolerant(path)` without a keyword:** it raises TypeError; the call needs `legal_entity_id=...`.
- **Reading OpenAI rendered-body PDFs with pypdf:** they have no text layer and return 0 lines. The mail body route carries the text.
- **Heredoc holding a Python triple-quoted block:** blocked by heredoc-size-gate. Write the script with the Write tool instead.
- **Numbering the item 201:** main had moved to 203 during planning (items 199 to 203 landed). The item is 204.

## Current Status
Item 204 is on main. Nothing is built.

Waiting on the owner or Criss:
- **D2:** Criss pulls the 9693 and 1176 activity weekly. She needs view access in Chase Access & Security Manager.
- **D3:** load the 9693 history already on disk and Criss's April to June sheets for 3876 and 0340. This is a live write, so it is hers.
- **D7:** a per-card close day. Not ruled; optional.

Also still waiting: PR #1343, a parallel case-6 build that also claims item 203, is open.

## Next Steps
Run the build prompts in this order:
1. Twins share the card (tiny, no risk).
2. Matcher guard for no-card pairs whose vendor disagrees. Includes the accuracy re-record and the deploy-gate ask.
3. The card flows back from a neighbour month's statement.
4. Billing-account card memory, replacing the held vendor-history prompt.
5. Honest waiting status, suggestions with evidence, apply-to-vendor, and a statement month suggestion. Includes a Lovable prompt that is written but not pasted.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, item 204 (the full appendix)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (top paragraph)

## Continuation prompt

````
/comd_resume brisken

Continue Brisken p1 expense-recon: build the case-9 ("no payment info") plan, backlog item 204, one step per session.

Where it stands (2026-09-25): item 204 merged (#1346, 80b058cf); status line #1348; live Fly f744680b; nothing built. The five build prompts, in order, are below in this checkpoint file ("Build prompts"): paste build prompt 1 as this session's task and run it to done (suite, PR, merge on green, deploy, cold drive), then continue with 2, 3, 4, 5 as context allows. Owner decisions taken: D1 calendar-month exports, D4 billing-account key (replaces item 200's vendor-name rule), D5 guard yes, D6 Criss's OpenAI pick stays on its row only. Waiting on the owner or Criss: D2 weekly export (Chase view access to 9693 / 1176), D3 history load (live write, Criss's), D7 close day (optional). PR #1343 (parallel case-6 build, also numbered 203) is open and not ours.

## How to work
- Worktree per item off origin/main; never edit, commit or stash in the shared checkout; never `git stash`.
- Module `workspace/clients/brisken/automations/expense-reconciliation`; full suite before each PR; ship on green; Fly deploy from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)`; verify `/healthz` commit; cold-drive the changed rows.
- Live API read-only (`POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`, never printed). Receipts from `GET /api/expense-batches/{id}`; charges from `GET /api/runs/{id}`. Never fetch `expense-report.pdf` live.
- No writes to Criss's months, settings, memory, SharePoint or any mailbox; predict what moves at the next natural re-match and stop.
- Scripts via the Write tool in the scratchpad (no Python triple quotes in heredocs); `git -C`, `uv run --directory`; MSYS_NO_PATHCONV=1 for colon or leading-slash args; `parse_statement_pdf_tolerant` needs `legal_entity_id=`.
- Record each step as a dated line under item 204 plus a Shipped row.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

## Build prompts

## Build prompt 1 of 5: invoice and receipt twins share the card (item 204, step 2)

````
/comd_resume brisken

# Brisken p1 expense-recon: an invoice takes the card its own payment receipt prints (backlog item 204, step 2)

## Owner direction
Case 9 ("no payment info") is "the backbone of the entire system's matching logic" (owner, 2026-09-24). Plan approved 2026-09-25 as backlog item 204; this is its step 2. Standing rulings: "a blank prompts Criss to look; a wrong card silently books the receipt to the wrong entity and the wrong person" (item 173); every expense's company and person come through its card (item 40).

## The rule to build
A Stripe vendor mails two documents for one purchase: the INVOICE (prints no card) and the RECEIPT (prints "Visa - 9693"). `duplicates.inherit_card_from_copies` already lends a card between copies, but walks only `find_duplicate_receipts_by_reference` groups; invoice `HMVWDWIL-0032` and receipt `2811-8284-7349` carry different references, so they sit in a vendor/date/total group and nothing is lent. Extend the lending to the duplicate groups the app itself SHOWS (the groups behind `expenses[].duplicate`, i.e. the ladder's verdict, not the raw `find_duplicate_receipts` buckets), under the existing guards unchanged: every card-bearing copy names ONE card; a group ruled `ignore` ("not a duplicate") lends nothing; a member whose payment mode is an operator-assigned hint keeps it; entity lends only when exactly one is named.

## Code pointers (origin/main; read by symbol)
`duplicates.inherit_card_from_copies`, `find_duplicate_receipts`, `find_duplicate_receipts_by_reference`, `duplicate_group_id`, `collapsed_duplicate_copies`; how `expenses[].duplicate` is built in `service.build_expense_view`; the three callers `# grid`, `# export`, `# before the card chain` (bake) in `service.py`. Four surfaces must agree (grid, CSV, month PDF, re-match bake).

## Live prediction (read-only, 2026-09-25, Fly f744680b)
September: `0029__Invoice-890D70BF-0034.pdf` Anthropic 184.35 -> card-9693 / Cloud Services (twin `0030` prints Visa 9693); `0008__Invoice-HMVWDWIL-0031.pdf` and `0033__Invoice-HMVWDWIL-0032.pdf` Lovable 50.00 -> 3645 / Corporate Services (twins `0009`, `0034`). September `n_needs_entity` 27 -> 24. July Supermercado Fenix 803.11 copy 2 takes 3876 from copy 1 (a decided copy, no count moves). No change: the May Lovable 200 pair (neither copy prints a card), July Aposto and Lovable pairs (the card-bearing copy got its card from the statement, not print), the three OpenAI 80.12 of 16 Sep (not a duplicate group; must never lend). Re-read all of this live before building; the months move.

## Tests (route-level, through GET /api/expense-batches/{id})
Invoice + receipt in one vendor/date group, different references: the invoice row reads the receipt's card, entity and person. Negatives: a group ruled `ignore` lends nothing; two copies naming different cards lend nothing; three same-vendor same-day same-amount receipts the ladder does NOT group lend nothing; an operator-assigned hint on a member survives. Caller-level regress: `uv run tools/regress_check.py` disabling the new group source at its wiring point in `inherit_card_from_copies`; a route test must go red. Run the attribution tool before/after (`tools/recon-match-attribution.py`, six bundles plus the live July/August bundles) and report class moves; the matcher pool changes because the kept invoice copy now carries a card.

## Out of scope
The billing-account memory (step 4), the cross-month flow-back (step 3), any matcher threshold, any live write.

## How to work
- Worktree off origin/main (`git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-twin-card C:\Users\neuma_p1qrsic\Repo\agentic-ops1-twin origin/main`); never edit, commit or stash in the shared checkout.
- Module: `workspace/clients/brisken/automations/expense-reconciliation`; suite `uv run --extra web --extra dev pytest -q` (about 10 minutes, run it before the PR).
- Live API read-only (`POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`, never printed; GET only). Receipts come from `GET /api/expense-batches/{id}`, never from `GET /api/runs/{id}` on a statement month.
- Ship: commit with explicit pathspecs, PR to `011matthias/agentic-ops1.01`, merge on green; Fly deploy after the green merge from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)`, verify `/healthz` commit, then drive the Expenses view of September cold (headless Chrome; type the code until Log in enables) and assert the three rows show their card.
- No live writes to Criss's months, settings or memory; rows move at the month's next natural re-match or read; report which, never trigger one.
- Scripts in your scratchpad via the Write tool (no Python triple quotes in heredocs); `git -C` / `uv run --directory`, never `cd X && ...`; prefix MSYS_NO_PATHCONV=1 for colon or leading-slash args.
- Record the result in item 204 (append a dated line under step 2) and a Shipped row.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

## Build prompt 2 of 5: a no-card pair whose vendor disagrees goes to review (item 204, step 6)

````
/comd_resume brisken

# Brisken p1 expense-recon: a receipt with no card evidence is not booked to a charge that does not carry its vendor (backlog item 204, step 6)

## Owner ruling (2026-09-25, D5)
Asked "a receipt with no card evidence whose paired charge does not carry its vendor's name goes to review instead of being booked?", the owner answered "Yes (Recommended)", knowing it costs three right pairs a click. Standing: "a blank prompts Criss to look; a wrong card silently books the receipt to the wrong entity and the wrong person" (item 173).

## The rule to build
When the matcher's chosen pair has `card_evidence.receipt == "none"` and the vendor words disagree (`_vendor_score` < 0.5, i.e. `vendor_pct` < 50), the pair goes to the REVIEW bucket with a new `review_code` (`no_card_vendor_disagrees`), not to reconciled. Flagging `requires_review` alone is NOT enough: today such a pair still lands in `outcome.matches`, sits in the reconciled bucket and lends its card through `settled_charge_cards` (item 204 section 3). The pair stays the top candidate, so Criss confirms it with one click. New knob in `MatchingConfig` (default on) mirrored into `config/match-tuning.json`. No threshold elsewhere moves.

## Code pointers (origin/main; read by symbol)
`matching/deterministic.py`: `card_evidence`, `NO_CARD_RIVAL_REVIEW` and its clause (the model to copy), `_vendor_score`, `strip_reference_tokens`, merchant precedence (item 133), `uniqueness_verdicts`, where `outcome.matches` vs `outcome.judgment_required` are filled; `service.apply_decisions` pass 2, `settled_charge_cards`, `confirmable_pair`; the SPA's review-code copy list (`docs/lovable-unmatched-reasons-prompt.md` section 5 says a new code needs SPA copy: write the Lovable prompt, do not paste it).

## Live prediction (read-only, 2026-09-25)
Two human-labelled WRONG pairs leave reconciled: August BASE44 50.00 (3645, Aug 22) holding `0025__Invoice-H0LHY2WQ-0032.pdf` (Lovable, `vendor_pct` 40; the row then loses its wrong 3645 card and Corporate Services), July HOTEL AM TIERGARTEN 24.02 (2838) holding Erste Fracht 21 EUR (47). Three right pairs go to review too: April 46.412.470 MARIA BETAN / Megacenter (17), July 48.247.796 BEATRYZ / Mega Center (15), August B91*E A LOCACOES / E A LOCACOES (33). All at each month's next natural re-match; no agent re-match. September has no such pair.

## Measurement and tests
Before AND after on a fresh DB copy: `tools/recon-match-attribution.py --live DB --run-id 50622baec444 --run-id 074a7b8905d7 --labels <July labels.csv> --labels <August labels.csv>` plus the six bundles; `tools/recon-match-accuracy.py` on the shipped asset (baseline determ_ok 70/95, 0 wrong, SCORE 76.0). Report every class move; expect the right-pair count to drop by the CNPJ pairs that appear in bundles and the wrong count to stay 0. The CI `accuracy` job gates on exact equality, so re-record `expected.json` with `--write-expected` in the same PR and say why; the deploy hook `recon-accuracy-deploy-gate.py` will ASK on a drop below `tools/recon-accuracy-baseline.json`: answer with the owner's D5 ruling in the PR body, do not lower the baseline silently. Tests: a matcher unit test plus a route-level test (GET /api/runs/{id}: the pair sits in review with the code; GET /api/expense-batches/{id}: the receipt has no card). Negatives: a no-card receipt whose charge carries its vendor stays reconciled; a receipt with a printed card number is untouched; the knob off restores today. Caller-level regress with `tools/regress_check.py` on the new clause.

## Out of scope
The FX near-misses (July Martino x3, Fenix 50.07 at 2.2-2.9%): never widen the band (S1 refuted it). Twin lending, account memory, statements.

## How to work
- Worktree `client/brisken/p1-no-card-vendor-guard` off origin/main; never the shared checkout; never `git stash`.
- DB copy for the tools: on-machine `sqlite3.backup` via `flyctl ssh console --pty=false`, then `flyctl ssh sftp get` with a Windows-form local path; delete it after. Set `RECON_MODULE_SRC` to the tree you mean to measure.
- Suite before the PR; ship on green; Fly deploy from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=...`, verify `/healthz`; read the months' payloads after and predict what moves at the next natural re-match. No live writes on Criss's months.
- Scripts via the Write tool in your scratchpad; `git -C`, `uv run --directory`; MSYS_NO_PATHCONV=1 where needed.
- Record in item 204 (step 6 line) and a Shipped row.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

## Build prompt 3 of 5: a receipt paired by another month's statement carries its card (item 204, step 3)

````
/comd_resume brisken

# Brisken p1 expense-recon: the card flows back to a receipt that a neighbour month's statement settled (backlog item 204, step 3)

## Owner direction
Owner decision D1 (2026-09-25): the 9693 and 1176 cards move to calendar-month Chase activity exports ("Calendar-month exports (Recommended)"). Charges still post a day or three after the purchase, and the history already on disk is in card-cycle PDFs, so a receipt dated in one month is regularly settled by a charge in the next month's statement. Item 40: company and person come through the card.

## The rule to build
Today the neighbour month borrows the receipt (`adjacent_pool_for_month`), pairs it, writes a `receipt_claims` row, and the receipt's own month shows only `settled_by` with NO card, entity or person: `settled_charge_cards` reads only its own charges and skips borrowed docs. Make the settled-charge link of the card chain also read the claim another run holds on this receipt (claims are written only for deterministic matches and confirmed decisions, never for review proposals), resolve that run's charge through `_charge_card_identity`, and give the row `card_source: "settled_charge"` with the borrowing month named in `settled_by`. The statement is truth, so this outranks everything below a printed number and a pick, as the same-month link does today. Same answer on grid, CSV, month PDF and the learner's `settled_cards` (item 171).

## Code pointers (origin/main; read by symbol)
`service.settled_charge_cards`, `export_settled_cards`, `month_charge_states`, `RECEIPT_SOURCES_KEY`, `_charge_card_identity`, `stamp_charge_entities`; `adjacent_pool_for_month`, `effective_settlements`, the `receipt_claims` store and `borrowed_source_view`; where `settled_by` is attached to `expenses[]` in `build_expense_view`; `resolve_batch_row_cards` (the `settled` link); `commit_to_memory` (item 171 passes `export_settled_cards`).

## Live prediction
Measure first: every expense row with `settled_by` and `card_source` other than hint/override, all months. Expected today: 0 to 1 rows (August's two OpenAI receipts borrowed by September already print 9693; July has one borrowed receipt, identify it). The value is structural: every receipt of the month's last days from October on. Say so plainly if the live count is 0; do not invent one.

## Tests (route-level)
Two months, a receipt in month A with no card, the charge on month B's statement; after B's re-match, GET /api/expense-batches/{A} shows the card, entity and person and `settled_by` names B. Negatives: a review-bucket proposal in B lends nothing; a rejected pairing lends nothing; a confirmed-private receipt is never borrowed; deleting B (or its statement) takes the card away again (item 114's lifecycle). Caller-level regress on the new wiring in `settled_charge_cards` (or wherever the claim is read).

## Out of scope
Changing the adjacent window, borrowing charges instead of receipts, the account memory, statement loading.

## How to work
- Worktree `client/brisken/p1-card-flows-back` off origin/main; never the shared checkout; never `git stash`.
- Read-only live API; no re-match, refresh or reset on Criss's months; predict what moves.
- Suite before PR; ship on green; deploy from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=...`; verify `/healthz`; drive the Expenses page cold if a row moved.
- Scripts via the Write tool; `git -C`; MSYS_NO_PATHCONV=1 where needed.
- Record in item 204 (step 3 line) and a Shipped row.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

## Build prompt 4 of 5: a card from the billing account's own history (item 204, step 4; replaces the held vendor-history prompt)

````
/comd_resume brisken

# Brisken p1 expense-recon: a receipt with no card takes the card its billing account has always been paid with (backlog item 204, step 4)

## Owner rulings
- D4 (2026-09-25), after a plain-language explanation: "Change to the billing account (Recommended)". This REPLACES the held vendor-history prompt; item 200 (vendor NAME, 3 wrong of 21) stays not built.
- D6 (2026-09-25), on September's OpenAI rows: "keep criss's pick for the sepcific expense, but have the other expenses default to the alternative logic for when no payment info is present". A pick stays on its row; the tool never spreads it.
- 2026-09-24: only corrections may be memorized; amended the same day so observations may decide a vendor's card through a DERIVED, not memorized, index.
- Item 173: a blank beats a wrong card. Item 40: company and person come through the card. OpenAI, Anthropic and Lovable are never written into the merchant registry ("not yet, and dont re ask", 2026-09-18).

## The rule to build
- Key: the billing account = the Stripe customer prefix of the invoice number. From `invoice_number`, else `reference`, matching `^[A-Z0-9]{8}[- ]?\d{4}$` with a prefix that is not all digits (`WWT1PNYP-0016` -> `WWT1PNYP`; Stripe receipt numbers `2642-9215-3921` are all digits and never a key). No key, no answer: POS and grocery receipts are out by construction.
- Evidence, per PURCHASE (collapse duplicate copies; `counts_in_total: false` never counts; the twin rule of step 2 means the invoice copy already carries its receipt's card): a printed Brisken card number (`card_source: hint` with digits, not an assigned alias, not a two-digit ending), a statement charge (`settled_charge`, same month or, after step 3, a neighbour's), a reviewer pick (`override`). Two-digit endings and alias hints may CONTRADICT but never count. Never evidence: `learned`, `merchant`, the new source itself, private or settled-outside rows.
- Decision: at least 2 purchases of the account on one card and none on any other card, across all company months, derived on every read (never stored). A row's own evidence is excluded when it is judged (leave-one-out).
- Chain position in `resolve_batch_row_cards`: after the settled charge, before `learned` and `merchant`, under the same guard (no printed number, not private). New `card_source: "account"`; entity and person ride the card; `can_mark_private` stays true (it is memory about the account, not a decision about the row). Not in `CARD_SCOPE_SOURCES` (never scopes the matcher).
- The circularity fix from the held prompt: `learned` leaves `_CARD_OBSERVATION_SOURCES`, and `account` is never added to it.
- Every surface that resolves the chain with live settings gets the index (grid, CSV, month PDF, card tabs, cost-center roll-up, `/api/cards/status`); build it once per request, and measure the latency of `/api/cards/status` before and after (it already builds every month).

## Measured (item 204 section 5; re-measure with copies collapsed before building)
Leave-one-out over 64 checkable receipts: 34 right, 0 wrong, 30 silent (the plan's run counted invoice + receipt copies separately; collapse them and re-run). Accounts: `WWT1PNYP` Nicolas's Anthropic 3876 only; `890D70BF` Anthropic API card-9693 only; `HQXED19R` Fireflies, `HYWGENV2` Wispr, `K9H3XEAQ` Vercel 3876 only; `DZ9BH3VA` 3645 then 1176 and `HMVWDWIL` / `H0LHY2WQ` Lovable on three cards: silent. OpenAI `58596F4C`: one pick only, silent (D6).

## Live prediction
Ten rows gain a card, all 3876 / Corporate Services / Nicolas Neumann unless noted: May Anthropic 99.95, 12.70, 90.00 EUR and Fireflies 5.00, 18.00, Wispr 30.00 BRL; June Anthropic 180.00 EUR, Fireflies 18.00, Wispr 30.00 BRL; September Anthropic 184.35 (card-9693, Cloud Services; if step 2 shipped first it already has it through its twin). OpenAI September: the pick row keeps 3645, the other ten stay blank. Re-read live first; state which moved and why.

## Tests (route-level, GET /api/expense-batches/{id})
Two earlier purchases of an account printed on 3876 in other months -> a third, card-less, reads 3876 with `card_source: account` and the card's entity and person. Negatives (each its own test): the account seen on two cards -> blank; one purchase of evidence -> blank; a pick on one row does not reach its siblings (D6); invoice + receipt copies of ONE purchase count once; a printed number, a pick and the statement each outrank `account`; a key that is all digits is not a key; publish does not teach `learned` rows into `cards_seen` (through `POST /api/runs/{id}/publish`). Caller-level regress with `tools/regress_check.py` at the chain wiring, a route test must go red.

## Out of scope
Company from bill-to text (item 40 forbids company without a card); the OpenAI workspace name from the mail body (a later extension, needs the untrusted-inbound handling); any registry write; the positive-evidence and private-card-list rules.

## How to work
- Worktree `client/brisken/p1-account-card` off origin/main; never the shared checkout; never `git stash`.
- Read-only live API for the before/after census (GET only). No live writes; the rows move on read, report them.
- Suite before PR; ship on green; deploy from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=...`, verify `/healthz`; cold-drive May and June Expenses and assert the rows show the 3876 card and the account reason. Write the Lovable prompt for the new source's label (EN + PT: "from this billing account's earlier invoices") as `docs/lovable-account-card-prompt.md`; do not paste it.
- Scripts via the Write tool; `git -C`; MSYS_NO_PATHCONV=1 where needed.
- Record in item 204 (step 4 line) and a Shipped row.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````

## Build prompt 5 of 5: the row says what it waits for, offers evidence, and a card can be applied per vendor (item 204, steps 1 and 5)

````
/comd_resume brisken

# Brisken p1 expense-recon: an honest waiting status, evidence-backed suggestions, apply-to-vendor, and a statement that says which month it belongs to (backlog item 204, steps 1 and 5)

## Owner rulings
- D1 (2026-09-25): calendar-month Chase activity exports for the 9693 and 1176 cards ("Calendar-month exports (Recommended)").
- D6 (2026-09-25): "keep criss's pick for the sepcific expense, but have the other expenses default to the alternative logic for when no payment info is present". Nothing is spread without Criss's own click.
- Item 173: a blank beats a wrong card; suggestions are never auto-applied.

## The rules to build (backend; one Lovable prompt for the SPA half, written, not pasted)
1. **Waiting status.** A card-less, non-private row whose date no loaded statement covers reads a new review code ahead of `needs_entity`, `waits_for_statement`, with `waits_for_statements: [card labels]`, i.e. the active cards whose loaded periods (any month, via `month_coverage` / `build_card_status`) do not cover the receipt date. When every active card's statement covers the date, today's `needs_entity` stands (a human has to look). `unmatched_reasons.receipt_reason_code` gets the same fact for the run payload (`card_statement_not_loaded` today requires printed digits). No close day is modelled (D7 not ruled; under D1 the calendar month makes it moot).
2. **Recurring-charge suggestion, never applied.** `card_suggestion: {card_key, evidence: [{month, date, amount, description}]}` on a card-less row when every loaded charge whose description carries the vendor's first word and whose amount is within 3% of the receipt (±45 days) sits on ONE card. Measured 44 right / 8 wrong as an automatic rule, so it is a suggestion only; live today: Network Solutions 2.76 and 173.98 -> 3645, Proton 9.99 -> 3876.
3. **Apply to this vendor.** `POST /api/expense-batches/{run_id}/cards/by-vendor {vendor, card_key}` writes the same per-row override the row PUT (`field=card_key`) writes, to every card-less, non-private, counting row of that display vendor in that month, and returns the documents it changed. An explicit click only (D6); `assign_batch_cards` cannot do this because it keys on a printed hint and refuses an empty one.
4. **A statement upload says which month it belongs to.** The attach entry carries `month_suggestion` (the month holding most of the file's charge days) and an advisory when it differs from the month it is being attached to, so a card-cycle PDF or a late export does not silently land in the wrong month.

## Code pointers (origin/main; read by symbol)
`service._expense_review` (reason order), `expense_boxes`, `build_expense_view`, `attach_expense_card_tabs` (`without_charge`), `month_coverage`, `build_card_status` (`receipt_months[].statement`, `no_card`), `unmatched_reasons.receipt_reason_code`, `assign_batch_cards`, the row PUT in `app.py` (`field == "card_key"`), `build_statement_entry` / `_statement_period` / `statement_advisory`, `period_suggestion` (the receipt-side shape to copy), `POST /api/expense-batches/{run_id}/statement`.

## Live prediction (re-read first)
September: the 20 blank rows read `waits_for_statement` (no September statement for the 2838 family, 1176 or 0113; 9693 covers only to Sep 4). May and June: every card-less row waits (no statement at all). July AWS 3,352.59 waits for 9693 (the 20260704 cycle is not loaded). August Perplexity 25.00 stays `needs_entity` only if every active card's August statement covers Aug 20 (0113, 6013, 8311 never loaded, so it waits too). Three suggestions as above.

## Tests
Route-level for each of the four rules, plus negatives: a covered date keeps `needs_entity`; a suggestion never sets `card`; the by-vendor route leaves printed, picked, private and copy rows alone and is idempotent; the month suggestion names the majority month for a cycle PDF spanning two months. Caller-level regress for each wiring point with `tools/regress_check.py`. SPA prompt `docs/lovable-case9-status-prompt.md` (EN + PT copy, the suggestion chip with its evidence and one-click apply, the "apply to the N other rows of this vendor" control after a pick, the attach advisory); not pasted.

## Out of scope
Any automatic card from the suggestion; a cycle close day; pulling statements automatically (no Chase API route exists for a small business without an aggregator; out of this item).

## How to work
- Worktree `client/brisken/p1-case9-status` off origin/main; never the shared checkout; never `git stash`.
- Read-only live API; no writes to Criss's months (the by-vendor route is tested on a synthetic `TEST - case9` batch created and purged in the same session, never on a real month).
- Suite before PR; ship on green; deploy from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=...`; verify `/healthz` and read the September payload for the new codes.
- Scripts via the Write tool; `git -C`; MSYS_NO_PATHCONV=1 where needed.
- Record in item 204 (steps 1 and 5 lines) and Shipped rows.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
