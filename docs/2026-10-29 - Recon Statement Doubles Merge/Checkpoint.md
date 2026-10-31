# Checkpoint: Recon Statement Doubles Merge

**Date:** 2026-10-29
**Status:** Item 257 (statements on what is left) LIVE; September re-read on the owner's yes

---

## Summary
One card's charge printed in two statement files now counts once: `merge_transactions` folds same card + day + amount + currency across two files of a card (max(n, m), never within one file, decided side kept). Shipped as PR #1681 on Fly `d37a3c96`; September re-read live after a local preview the owner approved: 216 -> 201 charges.

---

## What Was Done This Session

### Measure (read-only, live API)
1. September `51a22ad72864`: exactly 15 cross-file doubles, all `20261004-statements-9693-.pdf` x `Chase9693_2026-09_posted_0906-0915` xlsx, all pairs; 3 same-file repeats. PDF side: 15 unmatched, 0 decided. xlsx side: 9 reconciled (3 with a tool decision), 6 unmatched. August 0 doubles, October has no statement.

### Build (PR #1681)
1. `ingest/_common.merge_transactions(existing, incoming, *, files=, incoming_file=, decided=)`: id dedupe first (claimed held lines leave the pool), then a pool of held lines from OTHER files keyed by `_double_key` (card via `matching.deterministic._tx_card_keys`, so `9693` and `card-9693` agree; date; `canonical_amount`; currency). Incoming-only decided -> swaps in place; both decided -> both stay (`held`); neither -> held line stays (`folded`). Unknown card or unknown file never folds. `TransactionMerge` gains `folded`, `swapped`, `held`, `files`.
2. Wired in `service.py`: attach (files from `origins_from_snapshot`, decided from `store.get_decisions`) and `reread_statements` (files built in upload order; result gains `n_doubles_folded`, service-level only, not on the job).
3. Tests `tests/test_statement_doubles_item_257.py` (18: unit + route through attach and re-read, incl. a month built with the fold monkeypatched off, i.e. today's live shape). `regress_check` on both caller wirings: green -> red -> green. Full module suite 4335 passed.
4. `test_statement_append.py::test_one_card_typed_against_two_accounts_says_so` pinned the old doubling; now asserts one charge, advisory + warning stage still say "two account ids".

### Preview, deploy, live write
1. Local preview on backup `expense-recon-data-20261029T122203Z.zip`: re-read with fold off vs on on fresh copies. Fold delta: -15 PDF-side unmatched lines, 0 surviving-row changes, USD 7,288.38 -> 5,345.57.
2. Owner said yes (AskUserQuestion). `deploy.py` from detached origin/main: `/healthz` on `d37a3c96`, size matches fly.toml.
3. Read-only readiness, then live re-read: 216 -> 201, receiptless 125 -> 110, USD 7,288.38 -> 5,345.57, reconciled 73 / review 14 / unmatched receipts 27 unchanged; one re-read-alone move (Dollar General 24.25, 10-02, pending -> confirmed by tool).
4. Cold SPA drive (Python Playwright, installed Chrome, writes aborted, 0 aborted): September page reads "201 charges", "73 of 201 charges paired, 14 to review", "110 charges without a receipt"; the 10-04 9693 PDF row reads 49 rows / 34 new.
5. Records: backlog PR #1688 (item 257 heading + shipped row 168), status PR #1691 (`status/p1-expense-reconciliation.md`).

---

## Key Decisions Made

### Which side survives when neither is decided
- **Choice:** first-write-wins (the held line). In September's upload order that is the interim xlsx.
- **Rationale:** the docstring's identity rule; and measured, the xlsx side carries all 9 receipts, so keeping it moved no match.

### Same card typed against two account ids
- **Choice:** folds (the old test asserted two charges); advisory still names the two accounts.
- **Rationale:** the owner's rule keys on the card, and the measured live case itself differs in account id (`card-9693` vs `9693`).

---

## What Did NOT Work (and why)
- **First local preview re-read:** refused `statement_file_missing`; the backup's `runs.work_dir` is the Fly path `/data/runs/{id}`. Fixed by repointing `work_dir` in the copy (now in memory `reference_recon_local_perf_bench`).
- **Graph listing with `$select=...@microsoft.graph.downloadUrl`:** the URL is not returned; list with `?$top=999` and no `$select`.
- **First CI run of #1681:** hooks job red on F401 (unused `replace`, `Path`) in the new test; `uv run ruff` is not available in the module env, and `ruff-push-gate.py` only scopes `tools/` + `.claude/hooks/`, so the push went out unlinted.
- **`cd ... && gh pr merge`:** blocked by `block-merge-chained-after-any-command`; ran it alone with `-R`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py` | edit | the statement-double fold |
| `.../src/expense_recon/web/service.py` | edit | wire attach + re-read |
| `.../tests/test_statement_doubles_item_257.py` | new | 18 tests |
| `.../tests/test_statement_append.py` | edit | old doubling assertion -> one charge |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 257 built + live, shipped row 168 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | status-of-elements |
| memory `reference_recon_local_perf_bench.md` | edit | re-read preview recipe + traps |

---

## Current Status
Item 257 is complete: recognition (#1670), apply (natural re-match), and the statement-double merge (#1681) all live. September holds 201 charges, 0 cross-file doubles. brisken platform: unknown plan, ops not assessed (n/a for the FastAPI recon app).

---

## Next Steps
1. Feedback notes #128-#132 (backlog, not yet itemized): read `/feedback.jsonl` and itemize.
2. Explain the local-vs-live bucket gap (local untouched September read 121 unmatched / 17 review vs live 125 / 14) before the next preview relies on absolute counts.
3. Widen `ruff-push-gate.py` to the CI ruff scope (module tests too), so a new test file cannot reach CI unlinted.
4. Stale status files flagged by `pre` (p1-recon-loop-prompt, p2-*): owners of those workstreams to update or delete; not touched here.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 257, feedback notes table)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py` (`merge_transactions` docstring)

### Open Questions
- Why do locally rebuilt September views differ from live in bucket counts (no LLM / FX keys locally, or a date-dependent view)?

### Working Notes
- `n_doubles_folded` exists only on the service result; the job and the rematch event do not carry it. If the SPA should say "15 doubles merged", that needs a field.
- The PDF folded ids still appear in `statement_origins` under the PDF file (harmless: origins index ids, the month set does not hold them).
- Backup zip kept at `agentic-ops1-stmtdoubles/.scratch/bk/` (gitignored, 229 MB); unzipped copies deleted.

### Reference Materials
- PR #1681 (code), #1688 (backlog record), #1691 (status)
- Preview / diff scripts: session scratchpad `preview_run.py`, `compare.py`, `live_reread.py`, `spa_drive.py` (ephemeral)

---

## How to Continue
`/resume brisken`, then pick from Next Steps; item 257 needs no further work.

---

## Strategic Feedback

### What Worked Well This Session
- Isolating the fold's effect by re-reading two fresh backup copies (fold off vs on) turned "what will the live write do" into an exact prediction: the live diff matched it to the cent (201 charges, USD 5,345.57).

### Suggestions
- Build the shared recon drive helper the replay memory already proposes (prefetch, replay, write-abort guard, hydration-safe login); this session wrote it ad hoc a fourth time.

### System Health
- Session header skipped again (6th recurrence of the documented fix). Autonomy: 1 human intervention (the owner's yes on the live write, a designed decision point).
