# Mini-Checkpoint: Brisken Recon Note 64 And Card Separation Items

**Date:** 2026-09-17
**Status:** note #64 applied and verified; backlog items 137-138 written; item 137 not started (stopped at 474k context)
**Type:** mini

---

## Summary
The note #64 per-line category prompt went live (owner published 12:42 UTC) and was bundle-audited plus cold-driven; the owner then reported two card-separation defects, verified against code and live July/August and appended as backlog items 137 and 138. The session stopped before building 137 because a matcher change would cross the 500k pressure line.

## What Was Done
- **#64 verified (PR #995, merged):** bundle 12:43 UTC has `expx.lines.open.one/.many/.pick` + `line_index` in `chunk-expenses._batchId`, strings in `chunk-i18n`, all nine absent at 12:35 (controls hit). Cold Chrome drive through the login gate: Pressmaster FZCO 135.00 is the only one of 25 August rows with the block; picker lists the 8 `category_options`; Escape, nothing picked; PT strings render (localStorage `brisken.lang`); OpenAI rows show no block; only non-GET was `POST /api/login`. PROMPT-STATUS row moved to Applied, prompt banner flipped, backlog item 136 marked SPA APPLIED.
- **Items 137 + 138 (PR #1002, merged):**
  - 137: `match_month` card-scopes a receipt only via `receipt_card_scope` (card digits printed in its own `payment_mode` and present on the statement). The resolved card (Settings hint, hand pick, learned) never scopes. July: 19 of 52 receipts scoped, 33 compete across four cards (19 matched). August: 10 of 25 scoped, 11 card-known-but-unscoped (9 override, 2 hint), 4 no card. One confirmed cross-card pair: LOVABLE 25.00 on 3645 (2026-08-05) confirmed with `0027__Invoice-HMVWDWIL-0028.pdf`, card override 2838.
  - 138: month report (`expense-report.pdf`) is a flat listing (sections only by cost center, registry `{}` live); reconciliation report is per card only in its coverage table and charge listing, not header totals, exceptions, or receipt pages (August PDF, 69 pages).
- **List correction delivered to owner:** siblings shipped item 94 (#998), 116 + 95 (#993); 99 + 100 merged with prompts pending paste (#1004); 117 in PR #1003; 121 in #1001.
- Memory `project_brisken_expense_recon_usability_loop` updated (notes #1-#64 answered except #61; new traps).

## What Did NOT Work (and why)
- **`line_index` as a bundle-audit control:** it only enters the bundle with the prompt itself, so the first run printed INSTRUMENT INVALID; moved it to the new-signature list.
- **Python httpx/requests to api.expenses.brisken.com:** `getaddrinfo failed` [Errno 11001] twice in a row while `curl` and `nslookup` resolved it; used curl with the cached bearer.
- **`GET /api/runs`:** 405 Method Not Allowed (POST-only); readiness lives at `GET /api/runs/{id}` `.summary.ready_to_post`, month list at `GET /api/expense-batches`.
- **`agent-browser click` on the Radix line Select:** did not open it; focus + `press ArrowDown` did.
- **`MSYS_NO_PATHCONV=1 git -C /c/...`:** "not a git repository", because the unconverted POSIX path reaches Windows git; use `C:/...` with that prefix.

## Current Status
Fly unchanged this session (v150+ from siblings). Open brisken PRs at stop: #1003 (item 117, sibling), #1004 (prompts 94/99/100 pending paste), #1001 (item 121). Queue for this line of work: 137 -> 102 -> 138. Brisken platform line: unknown plan, no ops data. p2 status files `p2-product-decks.md` (56d) and `p2-targeting.md` (57d) are stale (p2 scope, not touched here).

## Next Steps
1. Item 137: resolved card scopes matching (hand pick = hard scope; hint/learned disagreement = demote to review with a "cards differ" reason; flag a confirmed cross-card pair). Measure before/after on a fresh DB copy (July/August right/wrong, six-bundle score, currently 70/95) per `project_brisken_recon_matching_program`.
2. Item 102: yellow rows hide missing receipts from the gap figure (47 July charges, USD 3,385 per the audit; re-read live first).
3. Item 138: one per-card structure in both PDFs, grouped on `coverage_key` for charges and 137's resolved card for receipts.
4. Owner/Criss, not agent: #61 (does Brisken still want GL account codes), Criss restores the two July invoices set aside as statement pages, June refresh master data, Pressmaster line pick, `intake.alert_recipients` yes, paste the #1004 prompts.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 137, 138, 102)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/matching/deterministic.py` (`receipt_card_scope`, `pair_in_scope`, `match_month`)
- `.../web/service.py` (`rematch_month`, `hand_picked_card_mode`, `resolve_batch_row_cards`, `build_expense_report`)
- `.../output/reconciliation_report_pdf.py`, `.../output/month_report_pdf.py`

## Continuation Prompt
Delivered in chat 2026-09-17; the same text:

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop exactly where the 2026-09-17 session stopped. Read first: `docs/2026-09-17 - Brisken Recon Note 64 And Card Separation Items/Mini-Checkpoint-1.md`, then backlog items 137, 102 and 138 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_recon_matching_program`, `project_brisken_expense_recon_testing_loop`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`.

## Where it stands

- The note #64 per-line category picker is live and verified (PR #995). Feedback notes #1-#64 are answered except #61 (parked on item 23; the question is with the owner).
- Items 137 and 138 were written from the owner's report (PR #1002). Nothing is built.
- Sibling work at the stop: item 117 in PR #1003, item 121 in PR #1001, the Lovable prompts for items 94/99/100 recorded as pending in PR #1004. Items 94, 95, 116, 99 and 100 shipped on 2026-09-17.
- Owner ruling: covered-class defects only until the EUR 600 licence is signed. No new functions.
- Waiting on the owner or Criss, not on you: #61 (does Brisken still want GL account codes), Criss restoring the two July invoices set aside as statement pages (AWS USD 3,352.59, Tricarico BRL 27,203), "refresh master data" on June, the Pressmaster FZCO 96.00 line category, a yes for `intake.alert_recipients`, pasting the #1004 prompts.

## Queue, in order

1. **Item 137: receipts are matched across cards.** `match_month` scopes a receipt only when its own `payment_mode` prints a card present on the statement (`receipt_card_scope`, `pair_in_scope` in `matching/deterministic.py`). The card the tool resolved (Settings hint, hand pick, learned; `resolve_batch_row_cards` in `web/service.py`) never scopes; item 135's `hand_picked_card_mode` only covers a pick that contradicts a printed card. Build: the resolved card scopes candidates. A hand pick (`card_source == "override"`) scopes hard. A hint or learned card that disagrees with the charge's card (`coverage_key` / `_tx_card_keys`) demotes the pair to review with a "the cards differ" reason and never silently drops a real match. A confirmed pair whose cards disagree gets a flag in the month payload. Live case to re-read: August LOVABLE 25.00 on card 3645 (2026-08-05), confirmed with `0027__Invoice-HMVWDWIL-0028.pdf` whose card override is 2838. Measure the before on a fresh DB copy (July and August right/wrong counts, the six-bundle score, 70/95 at last measure) per `project_brisken_recon_matching_program`, and report the cost next to the gain (pairs that stop matching). The attribution tool imports the matcher's rules; keep it importing them.
2. **Item 102: yellow rows hide missing receipts** from the gap figure (audit: 47 July charges, USD 3,385). Re-read live before quoting numbers.
3. **Item 138: the PDFs are not organized by card.** `expense-report.pdf` (`build_expense_report`, `output/month_report_pdf.py`: flat listing, cost-center sections only, registry empty live) and `reconciliation-report.pdf` (`output/reconciliation_report_pdf.py`: per card only in the coverage table and the charge listing) get one per-card structure: per card its charges with their receipts, its exceptions, its total and unreconciled figure, then its receipt pages; a last, never-dropped section for receipts with no card and charges no coverage entry claims. Charges group on `coverage_key`, receipts on item 137's resolved card. Where the cost-center partition goes is the owner's call; leave it as today.

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open` and `git worktree list` for a sibling claim (skip a claimed item), and read `GET /feedback.jsonl` for new notes (a new Criss note outranks the queue).

## How to work

- One git worktree off origin/main per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge origin/main before pushing, never rebase a pushed branch.
- No writes to Criss's live months; reads only. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes to the run (item 67), so never fetch it live; `reconciliation-report.pdf` is read-only. If a fix needs a live data action, name it and stop.
- Match live data exactly (no substring card checks). Python DNS to api.expenses.brisken.com failed intermittently on 2026-09-17 while curl worked (bearer from `POST /api/login`, code in memory `project_brisken_expense_recon_review_surface`). The months list is `GET /api/expense-batches`; readiness is `GET /api/runs/{id}` `.summary`.
- Every backend fix: a route-level test through the caller, then `uv run tools/regress_check.py` (disable the fix, watch it go red; "no pytest summary line" means reproduce by hand with a cp backup and cp restore). Full module suite before the PR (about 3.5 min, about 2,090 tests, no `-n`). Commit, push and open the PR autonomously, merge on CI green, then `flyctl deploy . -a brisken-expense-recon --remote-only` from a clean detached origin/main worktree (pre-authorized). After the deploy: a live API probe of the changed field and a real-Chrome read-back from a cold login (`agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe" open <url>` in the background, then `get url` / `snapshot` / `eval` in the foreground; a Radix Select opens with focus + `press ArrowDown`).
- In the same PR, update the backlog item's heading/status and add its Shipped row. SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence with EN + PT-BR strings and a "checking it landed" list, saved as `docs/lovable-<slug>-prompt.md` with a Not-applied row in `docs/PROMPT-STATUS.md`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure pressure with `uv run tools/session_state.py --status` and read `context=` (not `calls=`: sibling sessions reset that shared counter). Bands on the 1M window: moderate 300k, high 500k, critical 700k. Also act on the pressure meter's band advisories when they appear.
2. Measure before starting each item and after each merge or deploy. A backend item with tests, suite, deploy and live check costs roughly 150-300k; a matcher item with before/after measurement costs more. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence and append the same text to the checkpoint file.
7. At critical (700k): stop right after step 4's commit and push, then do steps 5 and 6.
8. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
