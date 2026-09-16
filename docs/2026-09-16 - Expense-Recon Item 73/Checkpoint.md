# Checkpoint: Expense-Recon Item 73

**Date:** 2026-09-16
**Status:** Backend live (PR #905, Fly v136); SPA half waiting on the owner's Lovable paste

---

## Summary
Backlog item 73 (note #42) is shipped. Every charge row on `GET /api/runs/{id}` now says what kind of statement line it is (`row_type`) and where its company came from (`entity_source`), so the Chase card payoff reads `payment` instead of sitting under "Refund". Matching, buckets and counts did not move.

---

## What Was Done This Session

### Live evidence before building
1. Both live months hold exactly one credit, the "Payment Thank You-Mobile" payoff (July -9,664.81, August -7,823.16). I read all 9 runs on the volume (`recon-web.sqlite`, opened read-only over `flyctl ssh`) and found no other `is_credit` row.
2. The uploaded workbooks already carry a `Type` column: July has 111 Sale + 1 Payment; August has 109 Sale + 1 Payment + 1 Fee (`ANNUAL MEMBERSHIP FEE`).
3. The item's secondary claim was refuted. The payoff row printed card 2838, the stored charge has `card_last4: "2838"`, and its company comes from the registry through item 59, not from the upload.

### Build (PR #905, merge `f07adcf3`)
1. Taxonomy: `ingest/_common.py` gained `ROW_TYPES`, `ROW_TYPE_BY_LABEL`, `row_type_for_label`, `row_type_of` (sign fallback) and `type_label_from_raw_text`. The last one uses `ast`, never evaluates, and accepts the headers `Type` and `Transaction Type`.
2. `Transaction.row_type` is stamped by the xlsx and csv parsers and round-tripped by `serialize.py`. A snapshot that has no key reads the Type cell back from `raw_text`.
3. The view appends `rows[].row_type` and `rows[].entity_source` (`service.charge_entity_source`). `month_health` skips payments. The reconciliation PDF says "card payment". The report workbook's credits section gains a Type column, and CLI `--explain` labels credits PAYMENT / REFUND / REVERSAL.
4. Tests: `tests/test_row_type.py` (11, route-level) plus a pin in `test_view_contract.py`. There are 8 `regress_check.py` proofs, all red first.
5. Docs: an api-contract section, `docs/lovable-row-type-prompt.md`, a PROMPT-STATUS Not-applied row, backlog item 73 marked shipped as Shipped row 48 (item 81 took 47), and a status element row.

### Ship and verify
1. Suite: 1832 on `178827a7` -> 1844 -> 1876 after rebasing onto item 80 -> **1887 passed / 2 skipped** after merging item 81. I resolved four rounds of append conflicts with items 79/80/81 by keeping both sides.
2. Deployed v136 from a detached `origin/main` worktree after confirming `fly.toml` matches the live config.
3. I diffed both live payloads against pre-deploy copies. The only change is the two new keys on every row (July 111 purchase + 1 payment, August 109 purchase + 1 fee + 1 payment, all `entity_source: card`).
4. The live reconciliation PDFs print "Payment Thank You-Mobile -9,664.81 USD card payment" and the August equivalent.
5. I drove the SPA cold through the login gate: the "Credits on the statement" view renders the payoff row with no error and no fallback. No type chip appears, which is expected before the paste.
6. Mini-checkpoint #912 (three merge-and-renumber rounds against sibling checkpoints). I handed over the full Lovable prompt a second time, as one copyable block.

---

## Key Decisions Made

### Parallel field, bucket untouched
- **Choice:** Add `row_type` beside `effective_bucket` instead of splitting the `refund` bucket.
- **Rationale:** The SPA groups rows by bucket through a fixed `BUCKET_ORDER`, so an unknown bucket value would hide the row. `refund` also still truthfully means "money back to the card, never receipt-matched". This follows api-contract rules 1 and 5.

### Read stored months back instead of re-reading statements
- **Choice:** Recover the label from `raw_text` at snapshot load.
- **Rationale:** A statement re-read on Criss's live months is a production mutation that needs a per-action yes. The stored raw row already holds the bank's own label, and I proved it on both live rows before deploy.

### Ship `entity_source` although its named instance did not reproduce
- **Choice:** Build it, and record the refutation in the backlog and the PR.
- **Rationale:** The page never showed the basis of a company either way. The field reads `card` on every live row, which is the honest answer to the owner's "you don't even know which card".

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/ingest/_common.py` | edit | taxonomy, label map, sign fallback, raw-text reader |
| `.../ingest/statement_xlsx.py`, `.../ingest/statement_csv.py` | edit | stamp the label's row type |
| `.../matching/types.py` | edit | `Transaction.row_type` |
| `.../web/serialize.py` | edit | round-trip + legacy read-back |
| `.../web/service.py` | edit | `charge_entity_source`, row fields in `build_view` |
| `.../web/month_health.py` | edit | skip card payments |
| `.../output/reconciliation_report_pdf.py`, `.../output/report_xlsx.py` | edit | credit labels, Type column |
| `.../tests/test_row_type.py` | new | route-level behaviour |
| `.../tests/test_view_contract.py` | edit | pin both fields |
| `.../docs/api-contract.md`, `.../docs/lovable-row-type-prompt.md`, `.../docs/PROMPT-STATUS.md` | edit/new | contract, SPA prompt, pending row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edit | item 73 shipped, Shipped row 48, element row |

---

## Current Status
Live on v136, verified by API diff, PDF text and a cold SPA drive. The SPA renderer is pending: until `lovable-row-type-prompt.md` is pasted, the payoff shows under "Credits on the statement" with no "Card payment" chip. brisken ops: platform plan unknown in `infrastructure.yaml`. Two p2 status files are stale (`p2-product-decks.md` 55d, `p2-targeting.md` 56d); that is outside this workstream and was left for a p2 session.

---

## Next Steps
1. Once the owner publishes the prompt: `uv run tools/lovable-bundle-audit.py` for `row_type`, `entity_source`, `wb.rowType.payment`. Then browser-drive July (payoff shows "Card payment", company tooltip names card 2838) and August ("ANNUAL MEMBERSHIP FEE" shows "Card fee"), and move the PROMPT-STATUS row to Applied.
2. Build the three structural fixes the register now shows recurring 2-3 times today (see Strategic Feedback) in one `/system-dev` round, before the next parallel wave.
3. Continue the feedback wave in its ruled order (74, 75, 77, 82), checking `git log origin/main` first: siblings are shipping these today.
4. Decide where the payoff row's category prompt goes. It still shows "ASSIGN" and a disabled "Confirm match", and a card payment needs neither. This sits with item 76/79 row handling.
5. brisken `infrastructure.yaml` has no platform plan or ops figures. Assess feasibility when the Fly and Lovable estate is next reviewed.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`, section "What a statement line is ... (item 73)"
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-row-type-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, item 73 and Shipped row 48

### Open Questions
- A PDF statement has no Type label, so its payoff still reads `refund`. Should the PDF parser learn the statement's "PAYMENTS AND OTHER CREDITS" section? No live PDF month exists today.
- Should a card payment carry no category at all (hide ASSIGN) rather than wait for one?

### Working Notes
- Vault entry "Expense Recon App" has fields `notes`, `operator_code`, `url`. The code is `operator_code`; `PARALLEL-ROUND-PROTOCOL.md` §3 does not name the field. Scratch helpers that never print the secret: `recon_login.py`, `recon_get.py`, `browser_login.py` (they call agent-browser via `shutil.which`, because Windows needs the `.cmd` shim).
- The auto-mode classifier blocks any command that prints part of a vault value, even masked. Read it inside a script and use it from there.
- Stored xlsx `raw_text` is `str(dict)` with `datetime.datetime(...)` values, so `ast.literal_eval` fails. Walk the `ast.Dict` node for Constant string pairs instead.
- The web report has no Explain sheet (`explain=False`); only the CLI writes one. Test the credits section of the `Unmatched` sheet instead.
- A pre-3.15 run (`b67133b8df98`) stores purchases with negative amounts and no `is_credit` key. Its Type cells read `Sale`, so it reads `purchase`. A negative-amount filter over-counts "credits" there.
- `agent-browser open` + `wait --load networkidle` never settles on this polling SPA. Use `wait <ms>` or `wait --text`, click cards by ref after `scrollintoview`, and re-snapshot before trusting refs.

### Reference Materials
- PR #905 (code), PR #912 (mini-checkpoint), Fly release v136
- `docs/2026-09-16 - Expense-Recon Item 73/Mini-Checkpoint-2.md`

---

## How to Continue
`/resume brisken`, then pick up Next Steps 1 once the owner reports the paste. The backend needs nothing further for item 73.

---

## Strategic Feedback

### What Worked Well This Session
- **Measuring the live data before building changed the design.** Reading the stored `raw_text` of both payoff rows proved the read-back path would work, which removed a production re-read (a per-action-yes mutation). Reading `card_last4` refuted half the item before any code went into it.
- **The post-deploy check was field-by-field.** Both months diffed against pre-deploy copies came back with exactly the predicted change and nothing else. That was a stronger check than a status code or a spot read.

### Suggestions
- Three defects each hit two or three parallel sessions today: the consumer gate closing on a harness-backgrounded command, Lovable prompts handed over as rendered markdown, and `checkpoint_scaffold` mini renumbering plus the `--root` placement. All three have a structural fix written down as "pending" in the register and none is built. Close them in one `/system-dev` round before the next wave. The cheapest to build first: `deploy-consumer-gate.py` treats a timeout-backgrounded tool response as not observed (one case in `test_deploy_consumer_gate.py`).

### System Health
- Autonomy: 1 human intervention (the copy-pastable prompt re-ask). The parallel-round protocol worked for code and failed for the shared session log: the mini-checkpoint needed three merge-and-renumber rounds, one per sibling checkpoint landing during a roughly 4-minute CI cycle.
