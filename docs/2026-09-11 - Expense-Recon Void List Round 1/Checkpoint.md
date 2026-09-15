# Checkpoint: Expense-Recon Void List Round 1

**Date:** 2026-09-11
**Status:** Round 1 shipped (PR #811, Fly v115); API-verified on both live months; the SPA drive waits on the Lovable host, which refuses connections; two owner rulings gate round 2.

---

## Summary

The ten voids from the morning session are backlog items 57-64 (voids 6 and 7 reference items 56 and 55). Items 57 and 58 shipped: readiness refuses a month the matcher could not see and names the broken input, and every re-match leaves an event the dev notifier mails as one line. Items 59 (unknown-card entity) and 56 (invoice+receipt pair) are put to the owner as decisions before any code.

---

## What Was Done This Session

### Setup
1. Worktree `agentic-ops1-voids` on `client/brisken/p1-recon-voids` off `origin/main` (siblings share the main tree). First commit appended items 57-64 to the backlog.
2. Live records read before code: both months' workbench and grid payloads, 14 exact same-day same-amount pairs in August and 18 in July, the LOVABLE 25.00 row's candidates (item 60 evidence), the unmatched pools.

### Item 57: month health (`web/month_health.py`)
3. `summary.month_health` on BOTH payloads: `broken` when the matcher proposed nothing in any tier while at least one receipt is the same absolute amount within a day of a charge; `suspects` from the matcher's own scoping rules (`sign` = charge is a credit, `currency`, `entity` = both named and differ, `card` = payment mode names another present card, `unknown`); `n_exact_pairs`; one English `detail`; `checked: false` before a statement.
4. `ready_to_post` = `n_undecided == 0 AND health ok`. The rule only refuses; a healthy month is judged by decisions as before, and a month with no exact pair is not its business.
5. Contract pins `summary.month_health.suspects[]` on both views; `docs/api-contract.md` section; Lovable prompt `docs/lovable-month-health-prompt.md` (blocked-bar render, EN/PT copy); PROMPT-STATUS Not-applied row.

### Item 58: re-match events
6. `rematch_month` gains `trigger` and appends `{event_id, at, trigger, counts}` to the snapshot's `rematch_log` (cap 50) inside the commit lock, on the FRESH row; `at` is the commit clock in the app's UTC format (the first draft used the caller's `now_iso`, which put a re-read before the attach that preceded it).
7. Callers name their trigger: `statement`, `reread`, `receipts`, `cards`, `master_data`, `set_aside`, `trip`.
8. `GET /api/operator/state` lists `rematches[]` (oldest first, stable sort). `tools/brisken-recon-notify.py`: `diff_rematches` on `event_id`, `rematch_line` ("August 2026: 14 of 111, pool 7 (statement, <when>)"), `seen_rematches` in state, baseline migration for pre-upgrade state files, one mail per pass with one line per event.

### Verification
9. `test_month_health.py` (9 route-level: the 2026-09-10 state reproduced through the real attach with the pre-fix parser reads `broken`/`sign` on both payloads; re-read clears it and the confirm-all opens the gate; entity / currency / card suspects; healthy, no-pair and pre-statement silence). `test_rematch_log.py` (4: statement / receipts / reread / cards events through the operator-state route; cap + junk tolerance). `test_recon_notify_diff.py` +3. Suite 1538 collected, green. Ruff clean.
10. Three `regress_check.py` proofs RED under mutation, green restored: the readiness wiring, the grid wiring, the log append.
11. CI green (7 checks), squash-merged `02ed3f04`, deployed v115 from a detached origin/main worktree. Platform config intact (recon_data_v2, always-on both services, 1024 MB).
12. Distinguishing probe on the live API: August `ok` / 14 exact pairs, July `ok` / 18, `ready_to_post` false on both from undecided rows; `rematches` present (0 events yet). Notifier dry-run with the deployed code against live state and env: login and diff clean.

---

## Key Decisions Made

### Health names the input, never the row
- **Choice:** one verdict per month with `suspects`, computed from the same committed pool and outcome both payloads render, in a new module rather than inside `build_view`.
- **Rationale:** the failure is "the matcher could not see the month", which no per-row state carries; and the grid and the workbench must not disagree about it.

### The re-match log lives in the snapshot, not the summary
- **Choice:** `rematch_log` is a parallel snapshot key, capped at 50, read only by the operator-state route.
- **Rationale:** `batch_list_summary` spreads `run.summary` onto the batch list, so a summary key would have leaked a list the SPA never pinned; the snapshot already carries parallel keys (`statements`, `extracted_receipts`, `llm_judgments`).

### Voids 6 and 7 are references, not new items
- **Choice:** item 56 gets a "ruling open" note; item 55 gets a "parser fingerprint" follow-up paragraph; 57-64 are the other eight.
- **Rationale:** the owner's instruction, and a duplicate item is a second place for the same truth to drift.

### The shared main tree was not fast-forwarded
- **Choice:** left `C:\Users\neuma_p1qrsic\Repo\agentic-ops1` 11 commits behind.
- **Rationale:** upstream touches `workspace/clients/meji-media/status/enquiry-automation.md`, which a sibling session holds dirty; a pull would have to overwrite another session's uncommitted work. Consequence: the scheduled notifier keeps running the old script until main is pulled.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/month_health.py` | new | the health rule |
| `.../src/expense_recon/web/service.py` | edit | health on both views, `ready_to_post` wiring, `rematch_log` append, `trigger` on every re-match path |
| `.../src/expense_recon/web/app.py` | edit | `rematches[]` on the operator state |
| `.../tests/test_month_health.py`, `tests/test_rematch_log.py` | new | route-level tests |
| `.../tests/test_view_contract.py` | edit | contract pins on both views |
| `.../docs/api-contract.md`, `docs/lovable-month-health-prompt.md`, `docs/PROMPT-STATUS.md` | edit / new | contract, SPA half, applied-state ledger |
| `tools/brisken-recon-notify.py`, `tools/tests/test_recon_notify_diff.py`, `tools/INDEX.md` | edit | re-match lines |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | items 57-64, notes on 55 and 56, Shipped row 32 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | evening paragraph, elements row |
| memory `project_brisken_expense_recon_usability_loop.md`, `MEMORY.md` | edit | round-1 outcome, the two gaps, the open rulings |

All repo edits merged in PR #811 (`02ed3f04`).

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ? (no `platform` section; Fly hosts the FastAPI app).

Backend live at v115. Both live months carry `month_health` (`ok`) and the unchanged `ready_to_post: false` from their undecided rows. Two gaps are open at close: (a) the SPA host `expenses.brisken.com` (185.158.133.1) refused connections from this machine and from an external vantage at 18:1x-18:2x CEST, and `brisken-reconcile-dash.lovable.app` 302s every route to it, so the consumer drive of the ready bar has not run; a 45 s probe was left running for 30 minutes. (b) The Windows task `BriskenReconNotify` runs from the main checkout, which is behind and cannot be fast-forwarded past a sibling's dirty file, so re-match mails start only after main is pulled. The p2 status files flagged stale (82 / 50 / 51 / 51 d) belong to a p2 session.

---

## Next Steps

1. Owner rulings, asked as decisions with a recommendation: item 59 (charges on cards the registry does not know: blank entity, recommended, vs inherit the upload's entity) and item 56 (collapse an unresolved invoice+receipt duplicate group to one matcher candidate automatically, vs only after the reviewer confirms).
2. When `expenses.brisken.com` answers: drive the August and July workbenches in agent-browser (session `recon-voids`), assert the tiles and the ready bar render real values with no fallback strings; then `uv run tools/bg_watch.py done expenses-brisken-com-reachabilit`.
3. Pull the main checkout once the meji file is committed by its session, so the scheduled notifier runs the new script; the first pass baselines `seen_rematches`.
4. Round 2 in order: item 59 (after the ruling), item 60 (bucket-vs-label on a charge with waiting candidates; backend half first, Lovable prompt for the SPA half), item 61 (adjacent-month receipt pool under `receipt_claims`).
5. Then items 62 (settled-outside-the-card disposition), 63 (same-currency candidates off the FX band; `calibrate` as the gate), 64 (column map + card currency per `statements[]` entry; unknown `Type` labels keep the printed sign), and the item-56 build after its ruling.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 57-64, Shipped row 32)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Month health", "Re-match events")
- `.../src/expense_recon/web/month_health.py`, `service.py` (`rematch_month` commit block, `run_month_health`)
- memory `project_brisken_expense_recon_usability_loop.md` (2026-09-11 evening paragraph)

### Open Questions
- Item 59 ruling (blank vs inherit for unknown cards). 77 of August's 111 charges sit on cards 3645 / 3876, both absent from the registry, all stamped Corporate Services today.
- Item 56 ruling (auto-collapse vs after confirm). 23 of August's 31 receipts sit in invoice+receipt pairs.
- Item 60: is the bucket wrong (`effective_bucket: unmatched` with two candidates) or the label? The row sits in the `attention` section with `initial_bucket: review`; both candidates unchosen.

### Working Notes

**Item 60 evidence (live, 2026-09-11).** LOVABLE 25.00 on 2026-08-05: `section: attention`, `initial_bucket: review`, `effective_bucket: unmatched`, `status: pending`, `review.state: none`, candidates `0027__Invoice-HMVWDWIL-0028.pdf` (ambiguous, p=0.90, "both candidates identical in vendor, amount, date") and `0028__Receipt-2167-5718.pdf` (exact, 0.99), neither chosen. The effective bucket falls to `unmatched` while the row still carries candidates, so the SPA's bucket-derived label reads "No receipt found". July has the same shape on GOOGLE 71.64 (07-01, receipt dated 06-30, `posted` section, `unmatched`, 2 candidates), which is also item 61's case.

**Item 62 evidence.** July unmatched pool: Konsultancy Finance 15,972.00 EUR (rendered body), Redis 13,200.00 USD (invoice), 360Crossmedia 900.00 EUR dated 2026-03-30: none will post to a card.

**Suspect detection, for reuse.** `_tx_card_keys` / `_card_keys` from `matching/deterministic.py` are the card identity the matcher scopes on; `exact_pairs()` in `month_health.py` mirrors the entity, card and currency gates one by one and is the place to add a new suspect.

**Traps met.** `uv run ruff` is not in the module venv (`uvx ruff check` works). Card assignment body is `{"assignments": [{"hint", "card"}]}` and needs the card in settings first. The notifier state file is only rewritten when something was announced. agent-browser `open` hangs for the full timeout when the host does not answer; check `curl -m 20` first.

### Reference Materials
- PR #811 https://github.com/011matthias/agentic-ops1.01/pull/811
- Live API `https://brisken-expense-recon.fly.dev` (operator code in vault "Expense Recon App"); SPA `https://expenses.brisken.com`
- Fly release v115; `flyctl config show -a brisken-expense-recon` equals the module's `fly.toml`

---

## How to Continue

`/resume brisken`. Answer the two rulings (or read them from the AskUserQuestion this session left). Reuse worktree `agentic-ops1-voids` on `client/brisken/p1-recon-voids` (merge `origin/main` first; the branch is one squash behind). Drive the SPA if the host is back. Then item 59 per the ruling, item 60, item 61: one PR per round, route-level tests, `regress_check.py` per fix, CI-green merge, `flyctl deploy .` from a detached origin/main worktree, agent-browser drive.

---

## Strategic Feedback

### What Worked Well This Session
- Reading both live payloads and running the exact-pair analysis before code meant the health rule's thresholds came from the real months (14 and 18 pairs, all matched or in review), and the deployed field reproduced those counts exactly.
- The first-draft ordering bug (`at` from the caller's clock) was caught by the route-level test asserting event order across attach / receipts / re-read, not by a unit test of the helper.

### Suggestions
- The dev notifier's scheduled task should run from a dedicated, auto-pulled checkout (or the nightly repo-sweep should pull main), so a shipped notifier change cannot sit inert behind a sibling's dirty file.

### System Health
- Autonomy: 0 human interventions. Gates: B1:0 B2:5 (three regress proofs, full suite, live distinguishing probe; the consumer drive is stated as pending, not claimed) B3:1 (event-order failure attributed to my own `at` stamp first) skipped:0.
- Two external limits, both reported rather than worked around: github.com refused connections twice mid-session, and the Lovable custom-domain host refused connections at close.
