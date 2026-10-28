# Mini-Checkpoint: Brisken Recon Prompt Re-Audit

**Date:** 2026-09-25
**Status:** Queue item 1 closed (by a sibling, #1375); four stale PROMPT-STATUS rows moved (#1386); owner note #87 recorded as item 213, not built
**Type:** mini

---

## Summary
The owner published the private-card-list prompt. A sibling running the same continuation prompt audited it first (#1375: applied in part, the strip's "Private card of..." never renders, Follow-up 1 written). This session's crawl also found four "not pasted" prompts already live and a fresh owner note (#87) on the item-204 reason text.

## What Was Done
- Bundle crawl (44 files, 1,271 KB; controls `can_mark_private`, `__private_card__`, `ready_to_post`, `unresolved_hints` hit): all six item-208 keys present. Source read confirmed the defect #1375 recorded: `ExpensesReviewGrid.tsx:3893` calls `renderUnit(u, {})` for "Cards by number", so `allowPrivate` is never true.
- Scripted cold Playwright drive of the published SPA (channel chrome, only non-GET `POST /api/login`): Settings > Private cards tab sits after Cards, empty state, Add/Save, help line, PT strings; September's private row badge carries no suffix (`private_source: "row"`); September's 3281 group Assign select lists the nine company cards + "New card..." and no "Private card of...".
- Census over all 7 months (GET only): `private_cards` `{}`; `private_source` non-empty only as `row` (July 1, September 1); seven numbered non-ambiguous strip groups exist that Follow-up 1 will light up: April 1340/78/2598/4167, June 3976, July 2544/9129/3076, September 3281.
- PR #1386 (merge `032cbb50`): PROMPT-STATUS moves merchant-profile (M4), chase-section-label (161), roster-mismatch (38), fx-daily-rates (167+168) to Applied, each with its decisive check (profile kept by the whole-map Merchants save; old chase copy in no file; roster add sends `[...travelers, person]`; `fx_reference_rates` in no file). 162, 180/181, 209, 204 no-card guard and case-9 status read 0 and stay.
- Same PR: owner note #87 (2026-09-25 01:12 UTC) recorded as backlog item 213 with a live measurement.

## What Did NOT Work (and why)
- **Doing queue item 1 in parallel with a sibling:** #1375 had already shipped the same audit 6 minutes before this session found it; the "re-list open PRs before pushing" lesson held only because it was checked before writing anything. Check `gh pr list --state open` BEFORE starting a queue item, not only before pushing.
- **`git merge origin/main` with an uncommitted edit in the worktree:** git aborted ("Merge with strategy ort failed") because upstream had changed the same backlog file; the commit then landed on the old base. Commit first, then merge.

## Current Status
- Item 208 SPA: applied in part. Settings tab and badge live; strip option dead until Follow-up 1 (in `docs/lovable-private-card-list-prompt.md`) is pasted.
- Item 213 (note #87): open. The `waits_for_statement` reason (`web/service.py` ~7401, #1372) reads 404 characters naming all nine cards on all 19 such September rows (July 10 at 229-291, August 1 at 260). The case-9 build-5 session is still active on item 204 follow-ups (#1388, #1389 open at 01:25 UTC).
- platform/comms: `pre` reported no ops data and no comms-log path for brisken.

## Next Steps
1. Item 213, if the case-9 build-5 session has not claimed it (check open PRs and the item's heading first).
2. Owner: paste Follow-up 1 of `docs/lovable-private-card-list-prompt.md`; then bundle-audit `allowPrivate: true` and cold-drive September's 3281 group (option present, no Assign).
3. Owner: before pasting `docs/lovable-case9-status-prompt.md`, it needs the item-213 amendment (its `{cards}` repeats the nine-card list).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 213
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` ~7385-7410
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-case9-status-prompt.md` line 35

---

## Continuation prompt

````markdown
/comd_resume brisken

# Brisken p1 expense-recon: note #87, the "waits for statement" reason (item 213)

## Where it stands

- **Item 208 SPA is applied in part** (owner published 2026-09-25; audited by sibling PR #1375). Settings > Private cards and the badge suffix are live and were cold-driven; the strip's "Private card of..." renders nowhere because the published `ExpensesReviewGrid.tsx:3893` calls `renderUnit(u, {})` for "Cards by number". Follow-up 1 (pass `{ allowPrivate: true }` there only) sits in `docs/lovable-private-card-list-prompt.md`, not pasted. Seven live groups will show the option once it lands: April 1340/78/2598/4167, June 3976, July 2544/9129/3076, September 3281.
- **PR #1386 (merge `032cbb50`)**: four prompts the Not-applied table still listed are live and now sit in Applied (merchant-profile M4, chase-section-label 161, roster-mismatch 38, fx-daily-rates 167+168). Still not applied: 162, 180/181, 209, 204 no-card guard, case-9 status, 208 Follow-up 1.
- **Owner note #87** (2026-09-25 01:12 UTC, September Expenses, row `0010__rendered-body.pdf`): "NO NEED FOR THIS MUCH VOLUME AI SLOP. TONE IT DOWN; COMPRESS WHATEVER, THIS LOOKS TREMENDOUSLY BAD". Recorded as backlog item 213. The anchored line is item 204 build 5's `waits_for_statement` reason (`src/expense_recon/web/service.py` ~7401, PR #1372): all 19 such September rows read the same 404 characters naming all nine company cards; July 10 rows (229-291), August 1 (260).

## Queue

1. **Item 213.** FIRST check it is unclaimed: `gh pr list --repo 011matthias/agentic-ops1.01 --state open` and the item's heading in `workspace/clients/brisken/status/p1-improvement-backlog.md`; the case-9 build-5 session was active on item 204 follow-ups at 01:25 UTC (#1388, #1389). If claimed, stop and report. If free: name the cards only when one or two are waiting, otherwise "No card on this receipt, and no statement is loaded for its date yet."; keep `review.waits_for_statements` as is; amend `docs/lovable-case9-status-prompt.md` line 35 (`{cards}`) the same way in EN and PT; consider the next-longest reasons the note's "COMPRESS WHATEVER" reaches (`suggested_private` 233 characters, `date_outside_period` 191, `needs_entity_settled_outside` 173) but only shorten wording, never drop the instruction a reason gives. Tests pinning the old sentence will need updating; predict the live change by recomputing the reason over the GET payload (19 + 10 + 1 rows), deploy, re-read, cold-drive September's row 0010 (read-only).
2. When the owner publishes 208 Follow-up 1: bundle-audit (`allowPrivate:!0` or `allowPrivate:true` near `expx.cards.strip.sec.numbered`), then cold-drive September's 3281 group: the Assign select ends with "Private card of..." (no Assign), and "No card number on the receipt" groups have none. Move the Follow-up 1 row to Applied.

## Waits on the owner or Criss

- Paste 208 Follow-up 1; list the first private card (3281's owner unknown).
- Hold `docs/lovable-case9-status-prompt.md` until item 213 amends its `{cards}` string.
- Optional owner call carried from case 6: PayPal / PIX / boleto / cheque stay no private evidence.

## How to work

- Worktree, cut fresh off origin/main: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/<slug> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-<name> origin/main`. Never edit, commit or stash in the main checkout (several sibling sessions sit on it). Never `git stash`. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths.
- Shared files (`cards.py`, `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog, the status file): append at the END of the relevant block; never renumber. Before the first push `git rebase origin/main` is fine; after any push only `git merge origin/main`, and commit before merging (an uncommitted edit to a file upstream changed aborts the merge). **List open PRs before STARTING a queue item and again right before pushing: on 2026-09-25 a sibling shipped this prompt's item 1 six minutes before this session reached it.**
- Live reads only: API `https://brisken-expense-recon.fly.dev`, `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it). Months: April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`, January `4ceaeb461386`. No writes to Criss's months or to settings. Never fetch `GET /runs/{id}/expense-report.pdf` live. Feedback store: `GET /feedback.jsonl` (bearer); 87 notes at 01:16 UTC; diff against #87.
- Bundle crawl: Chrome User-Agent (`expenses.brisken.com` 403s urllib's default); follow `assets/x.js` (incl. `__vite__mapDeps`) and `./x.js`; believe an absence only when the controls `can_mark_private`, `__private_card__`, `ready_to_post`, `unresolved_hints` hit. The SPA source is readable at `gh api repos/011matthias/brisken-expense-review/contents/<path>?ref=<sha>`.
- Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (~15 min); background it and register `uv run tools/bg_watch.py watch --label "recon suite" --eta 15`. Heredocs with triple quotes are blocked: write scripts with the Write tool. Ruff: `uv run --no-project --with ruff ruff check src tests` from the module dir. Regress: `uv run tools/regress_check.py --test "<cmd with WINDOWS paths>" --cwd <module> --file <src> --replace "<wired>" --with "<disabled>"`; never mutate concurrently with the background suite.
- Ship: commit with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01`, poll `gh pr checks <n> --json name,bucket` (read `mergeable_state` too: `dirty` means merge main first), `gh pr merge --squash --delete-branch` on green. Deploy (pre-authorized): detached origin/main worktree, `M=C:/.../expense-reconciliation`, `MW=$(cygpath -w "$M")`, `FLY_API_TOKEN` from `~/.fly/config.yml`, `flyctl deploy "$MW" --config "$MW\fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)"`; prove with `/healthz` `server.commit`; remove the worktree. Verify behaviour: a read-only census over all months, then a cold headless Playwright drive (`channel="chrome"`, click `input#code`, wait ~2 s for hydration, type the code, JS-click Log in, wait for localStorage `erc-token`, remove `[data-fb-widget] [role=dialog]`, open `/expenses/<id>`; the card strip is collapsed behind a "Review" button; settings tabs are force-mounted, so wait on visible text, not `text=` selectors), asserting the changed field renders and the only non-GET is the login. Name a scripted drive as such.

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
