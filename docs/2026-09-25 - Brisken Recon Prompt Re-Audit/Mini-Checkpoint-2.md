# Mini-Checkpoint: Brisken Recon Prompt Re-Audit (2)

**Date:** 2026-09-25
**Status:** 3281 listed as Dirk's placeholder (live); item 214 ruled by the owner, not built; item 213 open
**Type:** mini

---

## Summary
The owner pasted item 208 Follow-up 1, held the case-9 status prompt for item 213, and ordered 3281 set as Dirk's placeholder; the entry went in through the tool's own Settings tab. Two owner rounds then redesigned the card strip (item 214): it asks only where no payment info is printed, and its dropdown lists cards only.

## What Was Done
- Follow-up 1 bundle-verified (`D(e,{allowPrivate:!0})` on "Cards by number" only) and driven: September's 3281 group offered "Private card of..." and the Reimburse-to input (Assign never pressed).
- Owner-ordered write, scripted drive of Settings > Private cards: one guarded `PUT /api/settings` (body exactly `{"private_cards": {"3281": {"person": "Dirk Neumann", "note": "Placeholder set by the owner 2026-09-25; card owner not confirmed", "active": true}}}`), reply `applied: ["private_cards"]`, row survives reload, September badge reads "Private card: reimburse Dirk Neumann (from the private card list)". Pre/post snapshot diff over all 7 months: only September `0024__` moved (private / `private_card_list` / Dirk Neumann); September counts private 1->2, suggested 4->3, needs person 17->16, needs entity 17->16.
- Found: the strip's Reimburse-to never pre-fills (SPA renders `CardReviewStrip` without `expenses`); wrote Follow-up 2, then withdrew it unpasted when the owner's ruling removed the option (#1403).
- Found: private rows (list AND row-confirmed) stay in `card_review.unresolved_hints`; verified for July `0028__`, September `0024__` and `0046__`. Recorded as item 214; owner ruled it (two questions + "private card registry").
- PRs #1398 and #1403 merged (docs only). Backend was slow for ~20 min after a sibling's 01:29 UTC deploy while a September job ran (login 27 s, settings >90 s); recovered.

## What Did NOT Work (and why)
- **"3281 no longer waits on the strip" read from the page text:** the strip was collapsed behind "Review", so the check was blind; the API showed the group still listed. That is how item 214 surfaced.
- **Clicking a no-number strip group by locator:** `textContent` joins without spaces, and a JS-set attribute was lost when the strip re-rendered after Escape; settled from the bundle instead (the other sections call `D(e,{})`).

## Current Status
- `settings.private_cards` = 3281 -> Dirk Neumann (placeholder, editable in Settings > Private cards: edit, switch Active off, remove).
- Item 214 ruled, not built. Item 213 open. Case-9 status prompt held by the owner until 213 amends it.

## Next Steps
1. Item 213 (check it is unclaimed first).
2. Item 214 (backend, then one Lovable prompt).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 213 and 214
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`card_review` ~7130; `waits_for_statement` reason ~7401)

---

## Continuation prompt

````markdown
/comd_resume brisken

# Brisken p1 expense-recon: item 213 (compress the "waits for statement" reason), then item 214 (the card strip redesign)

## Where it stands

- **The private-card list is in use.** Item 208 + Follow-up 1 are published and driven. First entry, owner order 2026-09-25: **3281 -> Dirk Neumann, a PLACEHOLDER** (note "Placeholder set by the owner 2026-09-25; card owner not confirmed"), saved through Settings > Private cards. API diff over all 7 months: only September `0024__` (DB Fernverkehr) moved, to private / `private_card_list` / Dirk Neumann. Docs: PRs #1386, #1398, #1403 (all docs only; no deploy this session).
- **Item 213 (owner note #87, 2026-09-25 01:12 UTC):** "NO NEED FOR THIS MUCH VOLUME AI SLOP. TONE IT DOWN; COMPRESS WHATEVER, THIS LOOKS TREMENDOUSLY BAD", anchored on September row `0010__rendered-body.pdf`. The line is item 204 build 5's `waits_for_statement` reason (`src/expense_recon/web/service.py` ~7401, PR #1372): all 19 such September rows read 404 characters naming all nine company cards; July 10 (229-291), August 1 (260). The owner is HOLDING `docs/lovable-case9-status-prompt.md` until this lands, because its line 35 interpolates `{cards}` with the same full list.
- **Item 214, owner-RULED 2026-09-25, not built.** Read the item in `workspace/clients/brisken/status/p1-improvement-backlog.md` (owner words verbatim + our reading + build shape). In short: (1) a receipt whose PRINTED number resolves (company card or private list) leaves the strip; a receipt with no payment info keeps "Assign to card...", even when already private by hand (July `0028__`, September `0046__` stay; September `0024__` leaves); (2) the dropdown holds cards only: company cards + private-list cards ("3281 · Dirk Neumann (private)"), no "Private card of...", no "New card..."; picking a private card makes the rows private for its person; (3) a suggested-private group shows only private cards until the reviewer says it is not private; (4) "private card registry" (read as the private list's name and the dropdown's source; unconfirmed). Today `card_review` (~7130) groups every hinted row without a company card and never reads `private`. Follow-up 2 (the strip pre-fill) was withdrawn unpasted.

## Queue

1. **Item 213.** First check it is unclaimed (`gh pr list --state open`, the item heading); the case-9 build-5 session was active on item 204 follow-ups earlier. Fix: name the cards only when one or two are waiting, otherwise "No card on this receipt, and no statement is loaded for its date yet."; keep `review.waits_for_statements`; amend `docs/lovable-case9-status-prompt.md` line 35 the same way (EN + PT) and tell the owner the held prompt is ready. Shorten, never drop the instruction a reason gives, if you touch `suggested_private` (233 chars) too. Predict by recomputing the reason over the GET payload (19 + 10 + 1 rows), update the tests that pin the old sentence, suite, ship, deploy, re-read, cold-drive September row `0010__` read-only.
2. **Item 214.** Budget ~150k+. Backend: `card_review` drops a row whose printed number resolves to the private list (settle rule 1 for `private_source: month` from the ruling, or ask); keep no-number rows; the strip route accepts a private-card pick for a no-number hint (e.g. `{"hint", "private_card": "3281"}` -> the month's private hint with that card's person; no `learn`, there are no digits); refuse a digits key the list does not hold; a "not private" dismissal for a suggested group (check what item 203 already offers first). Keep `private_to` accepted (the published SPA sends it). Then one Lovable prompt: dropdown items from `cards` + `settings.private_cards`, both actions removed, the suggested-private filter with its "Not private" control. Contract + tests + census + drive as usual.

## Waits on the owner or Criss

- Confirm or replace the 3281 placeholder (Settings > Private cards).
- Paste `docs/lovable-case9-status-prompt.md` once item 213 amends it (held).
- Optional owner call carried from case 6: PayPal / PIX / boleto / cheque stay no private evidence.

## How to work

- Worktree, cut fresh off origin/main: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/<slug> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-<name> origin/main`. Never edit, commit or stash in the main checkout (several sibling sessions sit on it). Never `git stash`. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths. With `MSYS_NO_PATHCONV=1`, give `git -C` a WINDOWS path.
- Shared files (`cards.py`, `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog, the status file): append at the END of the relevant block; never renumber. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`, and commit before merging. List open PRs before STARTING a queue item and again right before pushing.
- Live reads only: API `https://brisken-expense-recon.fly.dev`, `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it). Months: April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`, January `4ceaeb461386`. No writes to Criss's months or to settings unless the owner orders that exact write (the 3281 entry was such an order). Never fetch `GET /runs/{id}/expense-report.pdf` live. `GET /api/settings` can take 75 s+; use 180-300 s timeouts; if every read crawls, check `flyctl logs` for a running job before blaming your code. Feedback store: `GET /feedback.jsonl` (bearer); 87 notes at 01:16 UTC.
- Bundle crawl: Chrome User-Agent; follow `assets/x.js` (incl. `__vite__mapDeps`) and `./x.js`; believe an absence only when the controls `can_mark_private`, `__private_card__`, `ready_to_post`, `unresolved_hints` hit. SPA source: `gh api repos/011matthias/brisken-expense-review/contents/<path>?ref=<sha>`.
- Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (~15 min); background it and register `uv run tools/bg_watch.py watch --label "recon suite" --eta 15`. Heredocs with triple quotes are blocked: write scripts with the Write tool. Ruff: `uv run --no-project --with ruff ruff check src tests` from the module dir. Regress: `uv run tools/regress_check.py --test "<cmd with WINDOWS paths>" --cwd <module> --file <src> --replace "<wired>" --with "<disabled>"`; never mutate concurrently with the background suite.
- Ship: commit with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01`, poll `gh pr checks <n> --json name,bucket` (read `mergeable_state` too: `dirty` means merge main first), `gh pr merge --squash --delete-branch` on green. Deploy (pre-authorized): detached origin/main worktree, `M=C:/.../expense-reconciliation`, `MW=$(cygpath -w "$M")`, `FLY_API_TOKEN` from `~/.fly/config.yml`, `flyctl deploy "$MW" --config "$MW\fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)"`; prove with `/healthz` `server.commit`; remove the worktree. Verify behaviour: a read-only census over all months (snapshot before, diff after), then a cold headless Playwright drive (`channel="chrome"`, click `input#code`, wait ~2 s for hydration, type the code, JS-click Log in, wait for localStorage `erc-token`, remove `[data-fb-widget] [role=dialog]`, open `/expenses/<id>`; the card strip is collapsed behind a "Review" button, EXPAND IT before asserting anything about groups; settings tabs are force-mounted, so wait on visible text, not `text=` selectors), asserting the changed field renders and the only non-GET is the login (or exactly the ordered write, guarded by body). Name a scripted drive as such.

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
````
