# Mini-Checkpoint: Brisken P1 Private Card List

**Date:** 2026-09-25
**Status:** Item 208 SHIPPED, deployed (Fly `1b4be9d3`), census and cold drive verified; SPA half written, not pasted
**Type:** mini

---

## Summary
The private-card list (owner direction 2026-09-24, cases 2 + 4 of the card-attribution map) is live: `settings["private_cards"]` as its own key, read live, one decision order through `cards.classify_payment_evidence`, `expenses[].private_source`, the strip's `private_to`, the undo opt-out and the card-pick exit. The list starts empty, so zero live rows moved; the Lovable prompt that lets anyone add an entry is written and waits on the owner.

## What Was Done
- PR #1363 (merge `1b4be9d3`, squash title still says "item 207"; the docs say **208** because sibling #1359 took 207 and #1362 took Shipped row 123 while CI ran, so the item is 208 and the Shipped row 124). Deployed to Fly from a detached origin/main worktree; `/healthz` `server.commit` `1b4be9d3`.
- Backend: `cards.PrivateCard`, `private_card_digits`, `private_cards_from_setting`, `normalize_private_cards_setting`, `private_company_collision`, `private_card_for`, `classify_payment_evidence`; `service.resolve_batch_row_cards(private_cards=)` with the order row decisions > month hint assignments (`expense.card_hints` / `expense.private_hints`) > listed number > case 6 evidence > wait; `_private_reimbursements` now takes the card resolution (moved the month report, the CSV, `completeness_counts` and both neighbouring-month pools off `field_overrides`); `service.private_opt_out_needed`; `store.SETTINGS_DEFAULTS/WRITABLE_KEYS` gain `private_cards`; app.py settings PUT (both collision directions), `_paid_by_conflict` lets a per-row pick win over a non-`row` private source, the private route stores `"0"` on undo of a list/month-derived row, `validate_expense_field` accepts `"0"`.
- Tests: `tests/test_private_card_list.py` (54, route-level), `test_view_contract.py` pin of `private_source`, `test_settings_put_contract.py` sample. Suite 3531 passed / 2 skipped (15 min). Two regress checks BITE (resolver list branch; strip `private_to`).
- Docs: contract section "Whose money paid: the decision order, and the private-card list"; backlog item 208 + Shipped row 124; item 175 heading and `docs/lovable-private-reimburse-prompt.md` header corrected to "applied by bundle 2026-09-24, not driven"; `docs/lovable-private-card-list-prompt.md` + PROMPT-STATUS Not-applied row; status file paragraph.
- Verified: before/after census over all 7 months (305 rows): `suggested_private`, `private`, `reimburse_to` identical on every row, `n_suggested_private` / `n_private` identical per month, every row carries `private_source` agreeing with `private`, settings carries `private_cards: {}`. Cold scripted Playwright drive (headless Chrome, from the login gate) of September PASSED: Luigi Buchholz "Private card: reimburse Dirk Neumann", DB Fernverkehr 3281 "Suggested private expense", only non-GET the login.

## What Did NOT Work (and why)
- **Bundle crawl with urllib's default User-Agent:** `expenses.brisken.com` answers 403; a Chrome UA passes. And a crawl whose import regex only follows `./x.js` / `/assets/x.js` found 20 files with `can_mark_private` 0 hits (a blind instrument); Vite's `__vite__mapDeps` names chunks as `assets/x.js`, so the regex must accept that prefix (43 files, all controls hit).
- **Patching a script with a Bash heredoc holding triple quotes:** the heredoc-size gate blocks it (third session in a row); use the Edit tool on the file.
- **Claiming the backlog number and the Shipped row before merge:** both were taken by siblings during CI (207 by #1359, row 123 by #1362), costing two merge-conflict rounds; the squash title kept the old number.

## Current Status
Item 208 live on Fly `1b4be9d3` (v230). The list is empty by design; nothing on screen changes until the owner pastes `docs/lovable-private-card-list-prompt.md` and someone lists a card. The `n_needs_person` 26 -> 23 in September and the five invoice rows whose `card_source` moved to `hint` are sibling #1362 (item 204 step 2, v229, deployed after my before-census), not this item. Ops status line: `brisken` platform unknown plan (no `platform` section in infrastructure.yaml).

## Next Steps
1. When the owner publishes the prompt: bundle-audit (`private_cards`, `private_to`, `private_source`, `set.tabs.privateCards`, `expx.cards.strip.privateOf`, `expx.private.fromList`) and cold-drive the three surfaces; move the PROMPT-STATUS row to Applied.
2. Nothing else in this item's queue. Sibling-owned items (204 case 9 builds, 206, 207) stay with their sessions.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("Whose money paid: the decision order, and the private-card list")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-private-card-list-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 208, Shipped row 124)

---

## Continuation prompt (verbatim, for the next session)

/comd_resume brisken

# Brisken p1 expense-recon: after the private-card list (item 208)

## Where it stands

- **Item 208, the private-card list, is LIVE** (PR #1363, merge `1b4be9d3`, Fly v230; the squash title says "item 207" but the backlog item is 208 and the Shipped row 124, renumbered after siblings took 207 and row 123 mid-CI). `settings["private_cards"]` (`{last4: {person, note, active}}`, its own key, read live, never snapshotted, `private_card_is_company_card` refused from both sides), one decision order through `cards.classify_payment_evidence(hint, cards, private_cards, hints)` (Brisken number or type, then a listed number = private, then case 6's evidence = suggested, then wait) reached by `service.resolve_batch_row_cards(private_cards=)`, `expenses[].private_source` (`"row"` | `"month"` | `"private_card_list"` | `""`, pinned in `tests/test_view_contract.py`), the strip's `{"hint", "private_to"}` assignment (month record `expense.private_hints`; with `learn` also the list), undo on a list/month-derived row stores `private: "0"` (opt-out), a per-row `card_key` wins over a listed number. Every consumer of `private` / `reimburse_to` reads the resolution (`_private_reimbursements(card_res)`). Contract: `docs/api-contract.md` "Whose money paid: the decision order, and the private-card list". Tests: `tests/test_private_card_list.py` (54).
- **Live effect: zero rows moved** (the list is empty; nobody here knows who owns 3281; the tool never seeds it). Census over all 7 months and a cold drive of September verified after deploy.
- **SPA half NOT pasted:** `docs/lovable-private-card-list-prompt.md` (PROMPT-STATUS Not-applied row). Until the owner pastes it nobody can add an entry.
- Item 175's prompt (`docs/lovable-private-reimburse-prompt.md`) is applied by bundle (2026-09-24), not driven; its header and backlog heading now say so.

## Queue

1. When the owner publishes the private-card-list prompt: crawl the bundle transitively (a Chrome User-Agent is required, `expenses.brisken.com` 403s urllib's default; follow `assets/x.js` names from `__vite__mapDeps` as well as `./x.js`; believe an absence only when `can_mark_private`, `__private_card__`, `ready_to_post`, `unresolved_hints` hit), assert `private_cards`, `private_to`, `private_source`, `set.tabs.privateCards`, `expx.cards.strip.privateOf`, `expx.private.fromList`, then cold-drive the Settings tab (no Save), the strip option (no Assign) and September's badge; move the PROMPT-STATUS row to Applied. Read-only: no test private card in live settings (the list is read live by every month).
2. Nothing else from this brief. Items 204 (case 9 builds), 206 and 207 belong to sibling sessions; do not claim them.

## Waits on the owner or Criss

- Paste and publish `docs/lovable-private-card-list-prompt.md`.
- List the first private card (3281's owner is unknown to us).
- Optional owner call carried from case 6: PayPal / PIX / boleto / cheque stay no private evidence (no live receipt affected).

## How to work

- Worktree, cut fresh off origin/main: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/<slug> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-<name> origin/main`. Never edit, commit or stash in the main checkout (several sibling sessions sit on it). Never `git stash`. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths.
- Shared files (`cards.py`, `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog, the status file): append at the END of the relevant block; never renumber. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`. **Claim a backlog item number and a Shipped row number only after `git merge origin/main`, and re-check `gh pr list --state open` right before pushing: two siblings took 207 and row 123 during one CI run on 2026-09-25.**
- Live reads only: API `https://brisken-expense-recon.fly.dev`, `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it). Months: April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`, January `4ceaeb461386`. No writes to Criss's months or to settings. Never fetch `GET /runs/{id}/expense-report.pdf` live.
- Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (~15 min); background it and register `uv run tools/bg_watch.py watch --label "recon suite" --eta 15`. Heredocs with triple quotes are blocked: write scripts with the Write tool. Ruff: `uv run --no-project --with ruff ruff check src tests` from the module dir. Regress: `uv run tools/regress_check.py --test "<cmd with WINDOWS paths>" --cwd <module> --file <src> --replace "<wired>" --with "<disabled>"`; never mutate concurrently with the background suite.
- Ship: commit with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01`, poll `gh pr checks <n> --json name,bucket` (read `mergeable_state` too: `dirty` means merge main first), `gh pr merge --squash --delete-branch` on green. Deploy (pre-authorized): detached origin/main worktree, `M=C:/.../expense-reconciliation`, `MW=$(cygpath -w "$M")`, `FLY_API_TOKEN` from `~/.fly/config.yml`, `flyctl deploy "$MW" --config "$MW\fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)"`; prove with `/healthz` `server.commit`; remove the worktree. Verify behaviour: a read-only census over all months, then a cold headless Playwright drive (`channel="chrome"`, click `input#code`, wait ~2 s for hydration, type the code, JS-click Log in, wait for localStorage `erc-token`, remove `[data-fb-widget] [role=dialog]`, open `/expenses/<id>`), asserting the changed field renders and the only non-GET is the login. Name a scripted drive as such.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k; the private-card list (item 208, resolver + settings + strip + docs + prompt + census + drive) cost about 340k (160k to 500k). Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
