# Checkpoint: Recon Card Strip Speed

**Date:** 2026-09-25
**Status:** Backend live (`a5ab93ce`); SPA prompt being pasted by the owner, drive after publish pending

---

## Summary
Owner reported the months card strip lagging the rest of the page and months slow to open. Cause: `GET /api/cards/status` builds every month's Expenses page (2.30 s live vs 0.2 s for the months list). Two shipped fixes take the strip's first request after login to 0.03-0.06 s live, with every payload byte-identical.

---

## What Was Done This Session

### Diagnosis (zero load on the live machine)
1. Pulled the 02:39 UTC SharePoint backup (app-only Graph, read-only), ran the API in-process, profiled. Per month the roll-up rebuilt inputs every month shares: all-months statement evidence (6 reads per request), registry card types/issuers per payment hint, alias normalization per resolution (~126k), digit keys (~44k).
2. Measured a month open with and without the roll-up beside it (July 1.0 s alone, 1.9-2.2 s with it: GIL contention on one machine).
3. Built the SPA locally (node-server preset) against the local API and drove it: in-app month opens fire no roll-up; full loads (reload, bookmark, new tab) fire one.

### Shipped
1. **#1423 (live `f5a9802e`)**: one `EvidenceSource` per request; `lru_cache` on registry wording, `is_generic_tender`, matchable aliases, digit keys. Roll-up 2.30 -> 1.35 s live. 16 read payloads byte-identical (on two bases).
2. **#1426 (live `a5ab93ce`)**, owner chose "memo + warm-up": `web/card_status_memo.py` keeps the roll-up body until the data folder changes, warm-up rebuilds 20 s after writes go quiet (`EXPENSE_RECON_CARD_STATUS_WARM=1` in fly.toml). Live first request after login 0.03-0.06 s, ahead of the months list.
3. **#1425, #1428**: p1 status file lines. SPA prompt `docs/lovable-card-scope-no-rollup-prompt.md` + PROMPT-STATUS row (in #1423), handed to the owner as paste text.
4. Pattern rule `warn-pytest-or-true-masks-exit`; memory `reference_recon_local_perf_bench.md`; MEMORY.md trimmed 20.2 -> 19.2 KB (15 lines, no entry removed).

---

## Key Decisions Made

### Memo + warm-up (owner, AskUserQuestion)
- **Choice:** keep the roll-up in memory, rebuild in the background after 20 s quiet, over "memo only" and "stop at the exact fixes".
- **Rationale:** the exact fixes left the strip ~1 s behind the rows; only a pre-built body removes the wait on first open.

### The memo's key
- **Choice:** each SQLite file's header change counter + other top-level files' mtime/size + presets file + the day; WAL mode turns the memo off. Key read BEFORE the build; builds serialized.
- **Rationale:** probed live in the VM first: both DBs rollback-journal, counter still for 60 s idle. File mtimes alone are too coarse on Linux for back-to-back writes. A key read after the build would pair old data with the new key.

### The build opens its own billing-account scope
- **Choice:** `_card_status_body` wraps `account_request_scope(_account_index)`.
- **Rationale:** the warm-up thread has no request middleware; without the scope an account-linked receipt is filed under no card. Pinned by a thread-vs-request byte-equality test on the case-9 fixture.

---

## What Did NOT Work (and why)
- **`vite preview` on the Lovable build:** the preset is `cloudflare-module`; preview needs `dist/server/server.js`. `NITRO_PRESET=node-server` + `node .output/server/index.mjs` works.
- **Playwright MCP and agent-browser for the live drive:** MCP is bound to the user's Edge on :9222 (closed); agent-browser hung on launch. A PEP 723 Playwright script on system Chrome under `uv run --python 3.12` works (py3.14 has no greenlet wheel for older pins).
- **Background `pytest -n auto ... | tail || true`:** xdist is not installed, pytest never ran, the task still reported exit 0. Now a warn pattern rule.
- **`grep -c "/jobs/"` without `MSYS_NO_PATHCONV=1`:** Git Bash rewrote the pattern to a Windows path; the "0 jobs running" before a deploy was blind. Re-run correctly: 0 jobs.
- **Test assumptions on the memo:** a receipt-only card's roll-up label is its key, and retiring a card changes nothing for existing months (a month keeps its creation-time registry). Tests now assert the rebuild, not a visible difference.
- **Live drive login:** 2 of 4 runs typed the code before hydration; no `/api/login` fired. Not an app fault.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense_recon/cards.py` | Edit | cached registry wording, generic-tender, aliases, digit keys |
| `.../expense_recon/web/app.py` | Edit | shared `EvidenceSource`; `_card_status_body` + memo wiring |
| `.../expense_recon/web/card_status_memo.py` | New | key, memo, warm-up |
| `.../tests/test_card_status_shared_reads.py` | New | 7 tests |
| `.../tests/test_card_status_memo.py` | New | 15 tests |
| `.../fly.toml` | Edit | `EXPENSE_RECON_CARD_STATUS_WARM=1` |
| `.../docs/lovable-card-scope-no-rollup-prompt.md` | New | SPA half |
| `.../docs/PROMPT-STATUS.md` | Edit | Not-applied row |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | status lines |
| `.claude/patterns/warn-pytest-or-true-masks-exit.md` | New | pattern rule |

(`...` = `workspace/clients/brisken/automations/expense-reconciliation`)

---

## Current Status
Backend `a5ab93ce` live on Fly, `/healthz` on that commit, published SPA driven cold after deploy (strip + rows + July render, no write). Module suite 3714 passed, 2 skipped. SPA prompt: owner pasting now, not yet verified. brisken ops: platform plan unknown (not assessed in `infrastructure.yaml`).

---

## Next Steps
1. After the owner publishes the SPA prompt: drive a fresh full load of `/expenses/<id>` (0 `/api/cards/status` requests) and `?card=card-2838` (exactly 1, scope reads 2838); move the PROMPT-STATUS row to Applied.
2. Watch the warm-up under Criss's real editing: `flyctl logs` for "card status warm-up failed"; a strip open ~25 s after an edit should be fast.
3. Owner call (suggested below): promote `warn-stop-merge-left-pending` from warn to a Stop-event block.
4. Compact MEMORY.md below 17.1 KB (19.2 KB now) when no sibling session is writing it.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/card_status_memo.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-scope-no-rollup-prompt.md`
- memory `reference_recon_local_perf_bench.md`

### Open Questions
- Does any live background writer (mail intake, FX poll, jobs) fire often enough during Criss's day to keep the warm-up from settling? Idle probe said no; not yet observed under use.

### Working Notes
- A local timing of `/api/cards/status` now measures the memo; time a build with `app.state.card_status_memo._build()`.
- `/api/settings` costs ~0.7-1.1 s only on the first call per process.
- Remaining per-month cost is the month report's `build_view` and `receipt_image_file` path resolution (Windows-heavy locally, cheap on Linux).

### Reference Materials
- PRs #1423, #1425, #1426, #1428 (011matthias/agentic-ops1.01)

---

## How to Continue
`/resume brisken`, then Next Step 1 once the owner says the prompt is published. The local bench recipe is in `reference_recon_local_perf_bench.md`; delete the pulled backup afterwards.

---

## Strategic Feedback

### What Worked Well This Session
- Proving "changes speed, not numbers" by byte-diffing all 16 read payloads before/after on a real-data copy, then regress-checking every wiring point (9 mutations, 1 honest "does not bite" that exposed which guard actually matters).
- Probing the live VM read-only (journal mode, counter over 60 s) before choosing the memo key, instead of assuming.

### Suggestions
- `warn-stop-merge-left-pending` recurred twice today across sessions because a warn surfaces only on the NEXT prompt. Promote it to a Stop-event block (the Stop arm honors `stop_hook_active`, so it costs one turn and cannot wedge a session).

### System Health
- The sibling-session environment (5 live sessions) made single timing samples swing by a second; min-of-N alternating A/B against a detached `origin/main` worktree was the only trustworthy instrument.
- Autonomy: 1 human intervention (the memo + warm-up decision; the Lovable paste is Lovable's own boundary).
