# Mini-Checkpoint: Brisken Recon Card-Scoped Matching

**Date:** 2026-09-17
**Status:** item 137 shipped and live (PR #1016, Fly v156), SPA prompt pending paste; item 138 not started; stopped at 396k own context
**Type:** mini

---

## Summary
Backlog item 137 went end to end: the card the tool resolved for a receipt (picked, hinted, remembered) now scopes and ranks matching, and the month payload names a held pair whose cards disagree. Item 138 (per-card PDFs) is budgeted at 150-250k and would cross 500k from 396k, so the loop stopped here.

## What Was Done
- **Before-measurement** on a read-only live DB copy (on-machine `sqlite3.backup`, receipts tarball, `learning.sqlite`): July 30 right / 0 wrong, August 6 right / 1 wrong (Lovable 50 invoice on BASE44), six bundles 70/95, score 76.0.
- **Live census of card-known receipts:** July has none unscoped (19 printed-scoped, 33 no card). August: 10 printed-scoped, 9 picked by Criss 09:45-11:28 (all `card-2838`), 2 hinted (9693, absent from the statement), 4 no card. Registry: 2838 is a real card with its own August charges; 3645 is a separate card posting to Zoho "Credit Card - 2838".
- **PR #1016** (merge d9e05ed8, Fly v156): `Receipt.card_scope_keys` / `card_scope_source` stamped by `service.bake_card_scope` (replaces note #63's payment-mode rewrite); `deterministic.scored_pairs` (hard pick scope with fallback), `cards_differ`, demotion (`requires_review`, reason "the cards differ", confidence 0.55), `RESOLVED_CARD_SIGNAL` 0.75; `rows[].cards_differ` + `summary.n_cards_differ`; attribution tool calls `bake_card_scope` and traces `scored_pairs`, PEP 723 gains `rapidfuzz` / `reportlab`. Route-level `tests/test_card_scope_item_137.py` (7), note #63 no-card test rewritten to the new contract; regress_check red on all three wires (bake 5/14, view flag 3/6, tie signal 1/7); full suite 2157 passed / 2 skipped; CI green.
- **After-measurement:** July and August class tables identical, bundles 70/95 / 76.0. Live after deploy: July `n_cards_differ` 0, August 1 (LOVABLE 25.00 2026-08-05, confirmed by the tool, charge 3645, receipt picked 2838); other summary figures unchanged. Cold Chrome login read the same payload from Criss's seat (`erc-token`); page renders "USD 10,898.66 still open".
- Backlog item 137 heading + Shipped row 59, API contract section + `n_cards_differ` row, `docs/lovable-cards-differ-prompt.md` with a Not-applied PROMPT-STATUS row, p1 status row.
- Memory `feedback_continuation_prompt_carries_loop`: owner directive that every loop iteration's closing reply lists the items still left.

## What Did NOT Work (and why)
- **Hand pick as a pure hard scope (the brief's wording):** `0027` LOVABLE 25.00 is picked 2838 but the bank line and the label put it on 3645 (tool-confirmed 2026-09-16, before the pick); a hard scope un-matches that real pair. A pick with no candidate on its card now falls back, demoted.
- **Resolved agreeing card at tie-break signal 1.0:** August resolved_clean 6 -> 5; ZOHOCORP 576.00 tied `0007` (prints ...2838, labelled) with its copy `0006` (picked 2838). Signal 0.75 restores it.
- **Demoting into the review bucket:** every `judgment_required` entry goes through the FX model and has its reason replaced; demotion stays deterministic.
- **The attribution tool as it stood on main:** `ModuleNotFoundError: rapidfuzz`, and its `load_live` never applied note #63's rewrite; both fixed in #1016.
- **Importing the `client` fixture from another test module:** CI ruff F811 on every test using it; defined locally.
- **flyctl sftp target inside double quotes with `\\$f`:** wrote the DB to `scratchpad$f` in the parent directory; single-quoted Windows paths work.

## Current Status
Fly v156 carries item 137. Its SPA half waits on the owner's paste, as do items 94/99/100 (PR #1004) and 102. At Criss's next August re-match, LOVABLE 25.00's tool confirmation returns to pending with the "cards differ" reason; nothing else moves. Brisken platform line: unknown plan, no ops data. No friction candidates this session.

## Next Steps
1. Item 138 (per-card PDFs), per the continuation prompt below.
2. After the owner publishes `lovable-cards-differ-prompt.md`: bundle-audit `wb.cardsDiffer`, drive August's LOVABLE 25.00 row cold, PROMPT-STATUS row to Applied.
3. Owner/Criss items unchanged (see the prompt).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 138; item 137's shipped notes)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Matching is separated by card (item 137)")

## Continuation Prompt
Delivered in chat 2026-09-17; the same text:

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop exactly where the 2026-09-17 session stopped. Read first: `docs/2026-09-17 - Brisken Recon Card-Scoped Matching/Mini-Checkpoint-1.md`, then backlog items 138 and 137 (137's "Shipped" notes) in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_recon_matching_program`, `project_brisken_expense_recon_testing_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`.

## Where it stands

- Shipped on 2026-09-17 in this line of work: note #64 picker applied (PR #995); items 137/138 written (PR #1002); item 102 backend (PR #1007, Fly v154); **item 137 (PR #1016, Fly v156)**: the card the tool resolved for a receipt (`card_source` override / hint / learned) scopes and ranks matching. A hand pick scopes hard while its card offers a candidate, else the other cards' charges come back demoted; a pair on another card gets `requires_review`, reason "the cards differ", confidence 0.55; a printed card beats a resolved one in a tie (1.0 vs 0.75). `GET /api/runs/{id}` `rows[].cards_differ` + `summary.n_cards_differ`: live July 0, August 1 (LOVABLE 25.00 of 2026-08-05, tool-confirmed, charge 3645, receipt `0027` picked 2838). Attribution class tables and six bundles (70/95, score 76.0) unchanged on a live DB copy.
- SPA prompts NOT applied (the owner pastes them): `docs/lovable-cards-differ-prompt.md` (item 137), `docs/lovable-booked-no-receipt-prompt.md` (item 102), items 94/99/100 from PR #1004. Once one is published: bundle-audit its decisive string, drive the named row cold, move its PROMPT-STATUS row to Applied.
- Feedback notes #1-#64 answered except #61 (parked on item 23, question with the owner).
- Owner ruling: covered-class defects only until the EUR 600 licence is signed. No new functions.
- Waiting on the owner or Criss, not on you: #61 (GL account codes), Criss restoring the two July invoices set aside as statement pages (AWS USD 3,352.59, Tricarico BRL 27,203), "refresh master data" on June, the Pressmaster FZCO 96.00 line category, a yes for `intake.alert_recipients`, pasting the pending Lovable prompts, and Criss's own call on her August card picks (all 9 name 2838; the Lovable invoices' charges are on 3645, which `cards_differ` now shows her).

## Queue, in order

1. **Item 138: the PDFs are not organized by card.** `expense-report.pdf` (`build_expense_report`, `output/month_report_pdf.py`: flat listing, cost-center sections only, registry `cost_centers: {}` live) and `reconciliation-report.pdf` (`output/reconciliation_report_pdf.py`: per card only in the coverage table and the charge listing; header totals, exceptions lists and receipt pages are not) get one per-card structure: per card its charges with their receipts, its exceptions, its total and unreconciled figure (and item 102's booked-without-receipt figure), then its receipt pages; a last, never-dropped section for receipts with no card and charges no coverage entry claims. Charges group on `rows[].coverage_key` (joins `coverage[].key`; two live shapes, `3645` bare and `card-2838` prefixed, never parse it). Receipts group on item 137's resolved card: `service.resolve_batch_row_cards(receipts, run.config, field_overrides)[doc]["card"].key` (the same chain `bake_card_scope` stamps), which matches `coverage[].key` for registry cards. A held receipt follows its charge's card section; flag a `cards_differ` row inside that section rather than moving it. Live August reconciliation PDF read 2026-09-17: 69 pages, page 1 "114 charges · 9 matched (7.9%) · unreconciled USD 10,898.66" over cards 1176/2838/3645/3876, exceptions pages 2-4, per-card listings 5-7, receipts from page 8. Where the cost-center partition goes is the owner's call; leave it as today. Budget 150-250k (two builders).

After item 138 the queue is empty: follow SESSION LOOP step 8 unless a new feedback note arrived.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open` and `git worktree list` for a sibling claim (skip a claimed item), and read `GET /feedback.jsonl` for new notes (a new Criss note outranks the queue; 64 notes at the 2026-09-17 stop).

## How to work

- One git worktree off origin/main per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge origin/main before pushing, never rebase a pushed branch.
- No writes to Criss's live months; reads only. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes to the run (item 67), so never fetch it live; `reconciliation-report.pdf` is read-only. If a fix needs a live data action, name it and stop.
- Match live data exactly (no substring card checks). Python DNS to api.expenses.brisken.com failed intermittently on 2026-09-17 while curl worked (bearer from `POST /api/login`, code in memory `project_brisken_expense_recon_review_surface`). The months list is `GET /api/expense-batches`; readiness is `GET /api/runs/{id}` `.summary`. Windows Python cannot open `/c/...` paths: pass `C:\...` forms.
- A read-only live DB copy: `flyctl ssh console --pty=false -C "sh -c '...sqlite3 backup to /tmp...'"`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get /tmp/<f> 'C:\...\scratchpad\<f>'` (single-quoted target), then delete the `/tmp` copies. `tools/recon-match-attribution.py --live DB --learning L --files DIR --run-id ID --labels CSV`; scorer `uv run --with rapidfuzz --with reportlab --with openpyxl --with pypdf --with pypdfium2 --with pillow --with openai tools/scorers/recon-match-accuracy.py config/match-tuning.json --split all`. Labels live in the main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/`.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py` (disable the fix, watch it go red; "no pytest summary line" means reproduce by hand with a cp backup and cp restore). Python heredocs containing triple quotes are blocked by a hook: write the script with the Write tool and run the file. Do not import a pytest fixture from another test module (CI ruff F811); importing plain helpers is fine. CI's ruff: `uv run --no-project --with ruff ruff check tools .claude/hooks tools/tests <module>/src <module>/tests`. Full module suite before the PR (about 4.5 min, 2,157 tests at v156, no `-n`). Commit, push and open the PR autonomously; wait for CI with `gh run list --branch <b>` filtered by head SHA (not `gh pr checks --watch` right after a push), merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized). After the deploy: a live API probe of the changed field and a real-Chrome read-back from a cold login (`agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe" open <url>` in the background, then `get url` / `snapshot` / `eval` in the foreground; the SPA's bearer sits in localStorage `erc-token`; a Radix Select opens with focus + `press ArrowDown`). A PDF change is proven by rendering the document from a local route test or a local data root, never by fetching `expense-report.pdf` live.
- In the same PR, update the backlog item's heading/status and add its Shipped row (row 59 was the last). SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence with EN + PT-BR strings and a "checking it landed" list, saved as `docs/lovable-<slug>-prompt.md` with a Not-applied row in `docs/PROMPT-STATUS.md`.

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
