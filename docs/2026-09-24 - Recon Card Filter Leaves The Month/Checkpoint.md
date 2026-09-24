# Checkpoint: Recon Card Filter Leaves The Month

**Date:** 2026-09-24
**Status:** Item 190 backend LIVE (Fly `93c69551`); SPA prompt written, waiting on the owner's paste

---

## Summary

Item 190 moves the card filter out of the month onto `/months` and carries the
pick into the month. It needed a backend change the brief did not expect: the
card roll-up knew only charges and statements, so it could never offer a month
holding only receipts on a card, nor No card.

---

## What Was Done This Session

### Read-only catalogue (step 1)
1. Bundle read (46 files, control `n_unmatched_tx` = 6): `cardTabs.*` is 28 keys,
   not 20. `/cards` (`chunk-CardsStatusScreen`) uses `all` and `aria`; the month
   page uses `emptyExpenses`; `under` and `subcards` are chip-only. "Cards with
   nothing this month" is `wb.filter.card.showEmpty/hideEmpty`, shared with the
   older Matching chip row in `chunk-runs._runId`; `wb.filter.card.empty` is
   strip-only. Item 187's keys are `months.cardFilter.{caption,cards,empty}`.
2. Cold Chrome drive of August: Expenses is `/expenses/{id}`, Matching is its own
   route `/runs/{id}`. The pick is stored per month in localStorage
   `brisken.month.cardTab.v1:{run_id}` (`{"key":"card-1176"}`) and follows between
   tabs. A pick scopes the rows, the boxes and the card's statement line; tab
   badges and the Reconciliation line stay month-wide. "Add another statement for
   this card" opens Attach bank statement with the card preselected. No card's
   tip is a `title` attribute.
3. Keys are one space: `/api/cards/status` `cards[].key` = the month's
   `card_sections[].key` = every row's `card_section`. `""` is no card.

### Backend (PR #1293, owner chose "backend first")
1. `service.receipt_card_counts(view)`: receipts per `card_section` over rows that
   count, decided copies out, the Expenses tab's own count.
2. `build_card_status(store, receipt_cards=...)` gains `cards[].receipt_months[]`
   and top-level `no_card`; the app passes `_expense_page_view` per run. Parallel
   fields, folded like `months`; a month whose count fails is named in
   `unreadable` and keeps its charges.
3. 4 tests in `tests/test_card_status_receipt_months_item_190.py`; regress-checked
   through the app wiring (3 red, restored green); suite 3264 passed / 2 skipped;
   CI green; deployed from a detached worktree with `GIT_COMMIT`.
4. Live after deploy: month sets as predicted plus January for 3876; `no_card` 72
   receipts over six months; call time ~0.07 s to ~2.2 s. Cold drive: `/months`
   and `/cards` render as before, no fallback strings.

### SPA prompt and ledger (PR #1294)
1. `docs/lovable-card-scope-carries-into-month-prompt.md` with an 11-row check
   table, every value read live.
2. Backlog item 190 recorded; item 187 notes its caption and month list are
   superseded; PROMPT-STATUS Not-applied row.

---

## Key Decisions Made

### Backend first
- **Choice:** add receipt presence to `/api/cards/status` before the SPA prompt.
- **Rationale:** without it, card isolation inside September (Criss's working
  month, no statement) would be lost, and No card could not be offered at all.
  Owner's answer to the one question put this session.

### The selection lives in the URL on three routes
- **Choice:** `?card=<key>` (`none` for no card) on `/months`, `/expenses/{id}`,
  `/runs/{id}`; chip picks use history replace; the localStorage key retires.
- **Rationale:** refresh, back and pasted links keep the scope, and Matching is a
  separate route the brief did not know about.

### Rename rather than drop the line vocabulary
- **Choice:** `cardTabs.*` splits into `cardStrip.*` (all, aria, noCard,
  noCard.tip) and `cardScope.*` (the statement line, 22 keys); `under`,
  `subcards`, `wb.filter.card.empty` dropped.
- **Rationale:** keeps every string the strip shows while making the post-paste
  check unambiguous (`cardTabs.` = 0).

---

## What Did NOT Work (and why)

- **Predicting the `/months` month lists from each month's `card_sections`:** it
  missed January for 3876, because a one-card month returns `card_sections: []`
  while its rows still carry `card_section`. The live read after deploy caught it.
- **The brief's "no backend change expected":** neither `/api/cards/status` nor
  `/api/expense-batches` carries per-card receipt presence.
- **Tailing the backgrounded suite's `.output` file:** the command was piped
  through `Select-Object -Last`, so the file is empty until exit.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | Edit | `receipt_card_counts`, receipt side of `build_card_status`, fold |
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/app.py` | Edit | Wire the Expenses page view into `/api/cards/status` |
| `workspace/clients/brisken/automations/expense-reconciliation/tests/test_card_status_receipt_months_item_190.py` | Create | 4 route-level tests |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-scope-carries-into-month-prompt.md` | Create | The SPA half |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` | Edit | Not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | Item 190; item 187 supersession line |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | Item 190 status block (separate client PR) |

---

## Current Status

Fly `brisken-expense-recon` serves `93c69551`. The SPA still shows the in-month
strip and item 187's filter (charges only) until the owner pastes the prompt.
Ops status line from pre-flight: unknown plan (no `platform` section in
`infrastructure.yaml`; FastAPI on Fly, not an ops-metered orchestrator).

---

## Next Steps

1. Owner pastes `docs/lovable-card-scope-carries-into-month-prompt.md`.
2. Then: `uv run tools/lovable-bundle-audit.py` (`cardTabs.` = 0, `cardScope.`,
   `cardStrip.`, `receipt_months`, `no_card` present), then the prompt's §7 table
   cold on both tabs, then mark 190 applied in the backlog and PROMPT-STATUS.
3. If the strip's ~2.2 s load is felt: a per-run cache keyed on the month's
   `updated_at` inside `build_card_status`.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-scope-carries-into-month-prompt.md` (§7 is the drive)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 190

### Open Questions
- Owner: commercial framing for directive-driven surfaces (185, 187, 190) under the October licence.

### Working Notes
- The old Matching chip row (`wb.filter.card`: "Card · All cards · …") did not
  render on August; the prompt removes it conditionally. Check on a one-card month
  (January) after the paste whether it ever renders.
- The top-level `months[]` of `/api/cards/status` sorts by charge span, so
  statement-less months come last there; `/months` must keep its own order.
- April's stored list summary still carries a retired `fx_rate_drift`
  `setup_advisories` entry (item 168 retired the advisory; stored summaries are
  frozen at ingest). Not in scope; seen in `/api/expense-batches`.

### Reference Materials
- PR #1293 (backend), PR #1294 (prompt + ledger)

---

## How to Continue

Paste the continuation prompt below into a fresh session once the owner says the
prompt is live, or continue in this one.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live app before writing turned up the two facts that reshaped the
  item: Matching is its own route, and receipt-only months were unreachable.
  Both came from a cold drive plus one payload read, not from the backlog.
- Verifying the prediction against the deployed endpoint before handover caught
  the January case that a pre-deploy prompt would have shipped wrong.

### Suggestions
- Continuation briefs should name `tools/lovable-bundle-audit.py` for bundle
  reads instead of spelling out a hand crawl; the brief's recipe is what produced
  this session's missed-tool row.

### System Health
- The `warn-hand-rolled-spa-bundle-crawl` pattern keys on curl/grep and misses a
  Python crawl script, so it cannot catch the most likely shape of the miss.
- **Autonomy:** 1 human intervention (the backend-first decision).

---

## Continuation prompt

````markdown
/comd_resume brisken

Brisken p1 expense-recon. One item left open, 190, and it waits on the owner.

## Where it stands (2026-09-24)

Item 190 (owner: "removing the card filter from inside the months since its outside now" and "when using this filter, and a month is clicked on by user he should then only see data from the card that he selected in the filter ... maintain the functionality, but layer it differently").

- **Backend LIVE**: PR #1293, Fly `brisken-expense-recon` at `93c69551`. `GET /api/cards/status` carries `cards[].receipt_months[]` (`run_id`, `label`, `batch_type`, `n_expenses`) and `no_card` (`months[]`, `n_expenses` = 72 over six months), counted by `service.receipt_card_counts` over the Expenses page's own payload. `/cards` reads nothing new. Call time went from ~0.07 s to ~2.2 s.
- **SPA prompt written, NOT pasted**: `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-card-scope-carries-into-month-prompt.md` (PR #1294). `?card=<key>` (`none` for no card) on `/months`, `/expenses/{id}`, `/runs/{id}`; a scope line replaces the strip on both tabs; `cardTabs.*` splits into `cardStrip.*` and `cardScope.*`; `under`, `subcards`, `wb.filter.card.empty` dropped.
- Item 190 cost about 240k context end to end (catalogue drive, backend with tests and regress, deploy, two PRs, two cold drives).

## The queue

1. **Item 190 step 4, only after the owner says the prompt is pasted.** Bundle first with `uv run tools/lovable-bundle-audit.py` (never a hand crawl): `cardTabs.` count 0; `cardScope.showing`, `cardScope.showAll`, `cardStrip.noCard`, `months.cardFilter.captionNoCard`, `receipt_months`, `no_card` present. Then the prompt's §7 table cold, on both tabs, asserting the scoped strings and that no fallback took their place: `/months` 1176 lists September and August; August `?card=card-1176` shows "Showing card 1176 · Show all cards", "1 expense · USD 100.00 · Statement 20260804-statements-1176-.pdf · Jul 06, 2026 to Aug 04, 2026 · 3 charges · 0 matched · still open USD 36.00 · 2 receipts · 1 without a charge", tabs "Expenses 1" / "Matching 3 charges", boxes EXPENSES 1 / CATEGORIZED 1 / NEEDS CATEGORY 0 / READY 1; `/runs/074a7b8905d7?card=card-1176` keeps the scope; No card lists September to April; 3876 lists September, August, July, June, May, January; `/expenses/50622baec444?card=card-1176` reads "Nothing on card 1176 in July 2026". Also check a fresh session has no `brisken.month.cardTab.v1:*` localStorage key, and whether the older Matching "Card · All cards" row ever renders (January is the one-card month). Then mark 190 applied in the backlog heading and in PROMPT-STATUS (move the row to Applied), PR, merge.
2. **Only if the owner reports `/months` or `/cards` loading slowly:** a per-run cache in `build_card_status` keyed on the month's `updated_at`.

## Waiting on others, not queue items

- **Dirk**: statements for cards 9693, 0113, 6013 and 8311. Absent data, not a defect.
- **Criss or the owner**: card 3645's `zoho_account` (item 172, should read `CHASE VISA - 2838 - TRAVEL`), and August `0008__Invoice-HMVWDWIL-0029.pdf` / `0027__Invoice-HMVWDWIL-0028.pdf`, both picked 2838 where the charge posted on 3645.
- **Owner**: the commercial framing for new surfaces under the October licence; 185, 187 and 190 all arrived as directives, and 190 took a backend change and a deploy.

## Constraints

- **No live writes on Criss's months or master data.** Read, predict what would move, stop. Never offer a refresh, reset or re-match as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3x3 account table: "not yet, and dont re ask, i will bring this up again when the time is right."
- Categorization and GL-account definition are OUT of scope (owner direction 2026-09-23); that work lives in another session.
- Operator code = local vault entry `Brisken recon operator code matthias` in `~/.passwords.json`, shape `{"code": ..., "notes": ...}` under the entry NAME as the top-level key. Never print it; read it into `$env:RECON_CODE` (or `export RECON_CODE=$(python -c ...)`) and pass the variable.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live.
- September is capped at 160 hours, real hours only. Licence EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog and status files all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/**`) on a `docs/...` branch; client `status/` files on a client branch. Prune merged, clean worktrees at the end; a whole-file diff that vanishes under `tr -d '\r'` is CRLF, not content.
- **Read the published bundle before believing any claim about the screen**, with `uv run tools/lovable-bundle-audit.py` (transitive crawl plus known-present controls). If you must grep a chunk by hand, minified JS is one line, so `grep -oh ... | wc -l`, never `grep -c`. The backlog lags the app: twice this week it said a Lovable prompt was unpasted when it was live.
- **Read `/feedback.jsonl` early** (86 notes as of 2026-09-24). The text field is `comment`; `page` / `selector` / `anchor` say where it was left.
- Live API reads: `POST /api/login` returns a **token** for `Authorization: Bearer` (the cookie alone 401s). Host `https://api.expenses.brisken.com`. `/api/version` does NOT exist. `GET /api/expense-batches`, `/api/expense-batches/{id}`, `/api/runs/{id}`, `/api/cards/status`, `/feedback.jsonl`.
- A month is two SPA routes: Expenses `/expenses/{id}` and Matching `/runs/{id}`. Per-card statement state is on the **Matching** route.
- Browser drives: Playwright MCP attaches to the user's busy Edge on :9222 and times out. Use `agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"` in SEPARATE foreground calls (`open`, `snapshot -i`, `fill`, `click --wait-nav`, `eval`, `close`). `open` backgrounds itself on the first call and the next call in the session works; refs from a stale snapshot expire, so re-snapshot before filling. Login is `textbox "Access code"` then the `Log in` button, and a cold open of a month route lands on the gate and returns to the month after login. **Element matchers use `String.startsWith`, never a regex assembled in a PowerShell string**; put eval JS in a scratch file and pass `"$(cat file)"`.
- Python heredocs containing triple quotes or double backslashes, and heredocs over 80 lines, are blocked by hooks: write the script with the Write tool and run the file. A backgrounded command piped through `tail` / `Select-Object -Last` writes nothing to its `.output` file until it exits; wait for the notification.
- If a backend change does prove necessary: route-level test through the caller, then `uv run tools/regress_check.py --test "uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q tests/test_x.py" --file C:\...\src\...\y.py --replace "<wired call>" --with "<disabled>"`, reading its post-restore line and not only the BITE line. Full suite: `$env:PATH = "C:\Program Files\Git\usr\bin;$env:PATH"` then `uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q` (7-9 min; 3264 passed / 2 skipped on 2026-09-24; without Git's openssl on PATH, 7 `test_smtp_starttls.py` tests fail for environmental reasons). CI ruffs the subtree: `uv run --no-project --with ruff ruff check tools .claude/hooks tools/tests workspace/clients/brisken/automations/expense-reconciliation/src workspace/clients/brisken/automations/expense-reconciliation/tests`.
- Commit, push, open the PR autonomously. **`gh pr checks <N> --watch` and `gh pr merge` as SEPARATE calls**; chained, the no-auto-commit gate cannot see the verdict and asks. Confirm with `gh pr view <N> --json state,mergeCommit`. Deploy only if code changed: `flyctl deploy <module dir> --config <module dir>\fly.toml -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<40-char merge SHA>` from a clean detached `origin/main` worktree (pre-authorized), `access_token:` from `~/.fly/config.yml` into `$env:FLY_API_TOKEN`. After any deploy: a live API probe AND a cold real-Chrome read-back of the changed value.
- In the same PR, update the backlog item's heading and status.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137); building the attribution instrument plus item 169 end to end cost about 280k on 2026-09-23, and item 173 on top of it another 70k. On 2026-09-24 items 171 and 173b together cost about 250k; item 176 plus the bundle read, six PRs, a deploy, a cold drive and the note-86 scoping cost about 175k; items 108 and 185 together, both shipped and deployed with five PRs, two cold drives and a checkpoint, cost about 230k; the footnote fix plus item 187 end to end, four PRs and three cold drives, cost about 145k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries you registered.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green. If work continues after the checkpoint, amend it rather than leaving stale numbers standing.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
