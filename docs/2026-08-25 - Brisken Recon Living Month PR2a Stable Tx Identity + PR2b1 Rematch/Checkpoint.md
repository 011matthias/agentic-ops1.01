# Checkpoint: Brisken Recon Living Month PR2a Stable Tx Identity + PR2b1 Rematch

**Date:** 2026-08-25
**Status:** Both PRs shipped, merged and deployed (Fly v91, v92); PR 2b-2 is next

---

## Summary

Shipped the two prerequisites the living month sits on. Transaction ids stopped
being row numbers, so an appended statement can no longer re-point an operator's
decision onto a different charge; and the attach path's match became
`service.rematch_month` with a judgment cache, so every incremental re-match to
come has one implementation and does not re-buy verdicts on Dirk's key.

---

## What Was Done This Session

### PR 2a — content-derived transaction identity (#620, Fly v91)

1. `ingest/_common.assign_content_ids` stamps every parsed statement row with a
   `sha1` over account / card / date / canonical amount / currency / vendor /
   reference. All three parsers (CSV, Excel, PDF) call it at the end of a parse.
2. The stamp is a POST-pass, not inline, because sign canonicalization runs per
   row with a mapped `type` column and whole-file otherwise; stamping inline
   would give one charge two identities depending on which path ran.
3. `Transaction.source_row` carries the spreadsheet row that used to be smuggled
   through the id, and `sheet_writeback._anchor_row` reads it.
4. Two existing tests were pinned to literal positional ids and now assert what
   they meant (the refund's `source_row`; the reconciled CSV's Account column).

### PR 2b-1 — `rematch_month` + the judgment cache (#621, Fly v92)

5. Extracted bake → match → judge → categorize → commit out of
   `execute_statement_attach` into `service.rematch_month`. The attach path is
   its first caller and keeps only the statement half. `require_no_statement` is
   the one thing that differs by caller.
6. `web/judgment_cache.py` proxies the two client methods every judgment call
   reaches the model through, keyed by call content plus the answering model.
7. Judgments MERGE onto the fresh row at commit rather than replacing it.

### Owner rulings absorbed

8. Pre-creating months intrudes: we do not open August/July 2026 on Criss's
   behalf and do not ask her to. Retired the "create the two months" step that
   sat at position 2 of the previous next-steps list.
9. The three Lovable prompts are being applied owner-side; left untouched.

---

## Key Decisions Made

### The occurrence suffix is `-N`, not `:N`
- **Choice:** repeat charges get `<digest>-2`, never `<digest>:2`.
- **Rationale:** `_anchor_row` reads the last `:` of a legacy id as a
  spreadsheet row, so `:2` would write an account beside an unrelated charge in
  Criss's workbook. `transaction_id` also travels as a URL path segment, which
  rules out `#`. A hex digest cannot contain `-`.

### The judgment cache is keyed by content, not `(transaction_id, document_id)`
- **Choice:** diverged from the plan's letter.
- **Rationale:** a reviewer can correct a receipt's amount after the pair was
  judged; an id key hands back the verdict the model gave for the old numbers,
  silently. The answering model is in the key too, so the 2026-08-24-style move
  to a stronger model re-judges instead of serving stale verdicts forever.

### PR 2 was split into 2a / 2b-1 / 2b-2
- **Choice:** three PRs, not one.
- **Rationale:** the plan's four parts are coupled through identity and through
  `rematch_month`. Shipping the prerequisites separately means each landed
  against a suite that already proved the path it changed, instead of leaving
  "did the refactor move behavior?" and "does append work?" tangled in one diff.

### The `has_statement` refusal is NOT one switch
- **Choice:** did not lift it; triaged and recorded instead.
- **Rationale:** it refuses at nine call sites in three classes. Three must open
  (receipts, statement, set-aside restore), two only mean something once a
  re-match follows (cards, refresh-master-data), and four expense-edit overlay
  routes must stay closed or get a real decision, because the attach BAKES edits
  into the snapshot receipts and reopening the overlay over a baked pool risks
  double-application. The plan reads as though it were a single flag.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `ingest/_common.py` | edit | `transaction_content_id`, `canonical_amount`, `assign_content_ids` |
| `ingest/statement_csv.py` · `statement_xlsx.py` · `statement_pdf.py` | edit | stamp at end of parse; carry `source_row` |
| `matching/types.py` | edit | `Transaction.source_row` |
| `output/sheet_writeback.py` | edit | `_anchor_row` prefers `source_row`, id-parsing kept as legacy fallback |
| `web/serialize.py` | edit | `source_row` round-trips the snapshot |
| `web/service.py` | edit | `rematch_month` extracted; judgments merged at commit |
| `web/judgment_cache.py` | new | content+model-keyed judgment memo |
| `tests/test_transaction_content_id.py` | new | 27 identity tests |
| `tests/test_rematch_judgment_cache.py` | new | 13 cache tests, driven through `rematch_month` |
| `tests/test_sheet_writeback.py` · `test_statement_csv.py` · `test_web_already_posted.py` | edit | de-pinned from literal positional ids |
| `docs/api-contract.md` | edit | living-month field table |
| `status/p1-{expense-reconciliation,improvement-backlog,recon-loop-prompt}.md` | edit | element row, item 29 split, loop brief |

---

## Current Status

Fly **v92**, healthz 200. Suite **1297 passed / 2 skipped**, calibrate exit 0,
ruff E9,F clean. Live verification after each deploy: 5 runs with transactions,
449 charges, 13 operator decisions — all still resolve their positional ids, no
blanks, no duplicates. No migration ran and none is needed.

`platform:` ops status unknown for brisken (no plan/ops figures in
`infrastructure.yaml`).

Six real receipts remain pooled for 2026-07 (2) and 2026-08 (4). Per today's
ruling they wait until Criss opens those months herself.

---

## Next Steps

1. **PR 2b-2**: open the guard by class (start with receipts / statement /
   set-aside restore), wire receipt arrivals to `rematch_month`, make the
   statement upload append-capable with content-id dedupe and a `statements[]`
   parallel field.
2. Decide whether a partial-vs-full upload whose SIGN inference differs deserves
   a visible warning (PR 2a pinned the behavior; the decision is open).
3. Owner-side: the three Lovable prompts, `lovable-months-list-prompt.md` first.
4. Owner-side: card registry entities for 0113 / 6013 / 9693 / 8311 and the
   missing 0340 card — that IS the live MISSING ENTITY count.
5. `infrastructure.yaml` has no `platform` section for brisken; a feasibility
   assessment would make the ops status line meaningful.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the brief)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 29)
- `C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md` (approved plan)
- `automations/expense-reconciliation/docs/api-contract.md` (living-month table)

### Open Questions
- Does a sign-inference disagreement between a partial and a full statement
  upload warrant a visible warning, or is two rows self-explanatory?
- Do the four expense-edit overlay routes stay closed once the month stays open,
  or does the bake become idempotent enough to reopen them?
- Brisken comms-log is 4 days stale; any unlogged conversations?

### Working Notes
- `execute_statement_attach` was the LAST top-level node in service.py, which is
  what made the extraction safe to splice; verified with `ast`, not line
  arithmetic, per the 2026-07-22 lesson.
- The primary clone is ~200 commits behind origin/main, so
  `project_status.py --check` reports brisken's p1 files as 12 days stale. They
  are current on `main` — that reading is a stale-checkout artifact, not drift.
- `regress_check.py`'s inner test command needs a WINDOWS-style path
  (`C:/Users/...`); a git-bash `/c/...` path fails to spawn inside the subprocess.
- Multi-line literals in `--replace` do not match: the sources are CRLF. Use a
  single-line anchor.

### Reference Materials
- PR #620, PR #621
- `%TEMP%/claude/recon-probe/verify_pr2a.py` (read-only live no-migration check)

---

## How to Continue

Read the loop brief, then start PR 2b-2 with the guard triage rather than a
blanket lift. Work in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-recon` off a
fresh branch from `origin/main`; the primary clone is far behind and shared with
live sibling sessions.

---

## Strategic Feedback

### What Worked Well This Session
- `regress_check.py` earned its keep twice: it rejected a test that asserted a
  hardcoded id string and another that injected its fixture before the read
  rather than mid-flight. Both would have shipped as green theatre. Writing the
  test, then proving it red, is catching a different class of defect than the
  suite does.
- Enumerating before building (B7) changed the design twice — nine guard sites
  instead of one, and the `sheet_writeback` coupling the plan never named.

### Suggestions
- **Corrected after writing this file.** The suggestion here was originally to
  widen `heredoc-size-gate.py`, on the reading that it keys on payload size
  while the failure mode is escape content. That was wrong: the gate already
  denies on a triple-quoted block and on a literal backslash in a
  Python-context body, and would have caught the payload. It never ran,
  because the primary clone is ~200 commits behind and does not contain the
  file.

- The real finding is worse and is now its own register row: SessionStart
  reported "enforcement layer intact (20/20 hooks)" for a checkout with ZERO
  hooks wired and one gate missing outright. `wire-hooks.py` validates against
  its own checkout's `CANONICAL_HOOKS`, so a stale clone cannot tell that the
  trunk has moved; the confident count is what hides it. Make the SessionStart
  check compare against `origin/main` and say so when behind.

### System Health
- The split-PR rhythm (prerequisite → prove neutral → build on it) held under a
  large plan item and is worth keeping as the default for anything with more
  than two coupled parts.
- **Autonomy: 1 human intervention** — fully autonomous apart from one interrupt.
