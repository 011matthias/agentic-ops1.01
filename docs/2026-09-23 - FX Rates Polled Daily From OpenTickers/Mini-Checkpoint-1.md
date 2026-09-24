# Mini-Checkpoint: FX Rates Polled Daily From OpenTickers

**Date:** 2026-09-23
**Status:** Shipped and live (PR #1203, Fly release stamped 131fd5d2); SPA half pending; one owner decision open
**Type:** mini

---

## Summary
Dirk's feedback note #79 (12:34 UTC, anchored on Settings > FX reference rates: "fx rates should be polled daily via open tickers API") is built, merged and deployed: the app polls OpenTickers daily, backfilled the live months once, and the matcher reads the rate for each purchase's own day above the ECB monthly average. The two typed Settings rates still win, so July and August did not move (census before/after: 0 of 18 + 2 FX blocks changed); clearing them is the open owner decision.

## What Was Done
- Read the app's feedback store first (82 notes; the backlog had stopped at #72). #79 is this item; #73-#82 listed in the backlog's Open section; the sibling session's PR #1202 itemized #76/#78/#80/#81 as items 163-166 the same afternoon, so this item is 167.
- Verified the OpenTickers key live (401 without, 200 with; `/historical` 200 and `X-RateLimit-Limit: 50000`, so a paid tier, not the advertised free 100/day). Key in `context/.env` `OPENTICKERS_API_KEY` + Fly secret; dashboard login in the vault "OpenTickers Brisken".
- Built `web/fx_daily_rates.py` (boot + 24 h poll thread, one-time backfill from the month before the earliest month, ECB record preferred else median, fail-open), store tables `fx_daily_rates` + `fx_daily_rates_meta`, `MatchingConfig.fx_daily_rates` + `daily_rate` (charge-day cross through EUR, nearest day within 4, earlier on a tie), rung `opentickers_day` between the self-derived rates and `ecb_month` with the 2% band, `rematch_month` refreshing the table from the store on every re-match, `GET /api/settings.fx_daily_rates` (derived), `POST /api/fx/poll`.
- Tests: `tests/test_fx_daily_rates.py` (20); regress_check on the re-match wiring (4 route tests red unwired); full suite 2967 passed; CI green twice (before and after the merge of main).
- Deployed from a detached `origin/main` worktree; live proof: `/healthz` commit = 131fd5d2, `POST /api/fx/poll` 200 `ok: true`, settings block `n_days 45`, `first_day 2026-07-22`, `last_day 2026-09-22`, latest EUR:USD 1.146300 / BRL:USD 0.195195; typed rates unchanged; cold SPA drive of Settings > FX reference rates rendered both typed pairs with no fallback strings.
- Docs: `api-contract.md` section, `docs/lovable-fx-daily-rates-prompt.md` (FX tab card + "Poll now" + `daily rate, {day}` label), `PROMPT-STATUS.md` Not-applied row, backlog item 167 + shipped row 115 + the notes block, status roll-up, memories `reference_brisken_opentickers_fx_api` (new) + usability-loop.

## What Did NOT Work (and why)
- **Bash heredocs carrying the edit scripts:** the heredoc gate blocks >80 lines, nested triple quotes and double backslashes (six firings); the scripts went to Write-tool files and ran with `python <file>`.
- **Exact-match anchors on the recon sources read with `newline=""`:** 0 matches because the working copies are CRLF (`git ls-files --eol`: i/lf w/crlf); normalize `\r\n` to `\n` before matching and restore on write.
- **`re.sub` with a replacement string containing the text `\r\n`:** `re` unescaped it into real CR/LF and wrote a broken header; a function replacement (`lambda m: ...`) carries the text verbatim.
- **`MSYS_NO_PATHCONV=1 python /c/.../script.py`:** the flag also stops converting the script's own path, so Python got `C:\c\Users\...` and could not open it; leave conversion on for script paths.
- **Keep-both resolution of the store DDL conflict:** the closing `);` of my second table lived in the shared tail, so the joined block read `value TEXT NOT NULL -- Item 163 ... CREATE TABLE`, `sqlite3.OperationalError: near "CREATE"`; a merged DDL has to be executed, not just cleared of markers.
- **Playwright MCP for the consumer drive:** bound to the user's Edge CDP :9222, `initializeServer: Timeout 30000ms`; `agent-browser --session fx923 --executable-path Chrome` worked (the SPA `open` was time-boxed with `timeout 60`, state read with `snapshot` in the foreground).
- **First `flyctl deploy` without `--build-arg GIT_COMMIT=<sha>`:** the health stamp would have been empty, so a second deploy carried the arg (Dockerfile ARG is `GIT_COMMIT`).
- **First `gh pr merge` after CI green:** GraphQL "Pull Request has merge conflicts" because `main` moved (PR #1202) during CI; merged `origin/main` into the branch, resolved two files, CI again, then merged. The second `gh pr merge` exited 1 with "'main' is already used by worktree" while the merge had succeeded (`gh pr view` state MERGED); the known false-FAIL.
- **Numbering the backlog item before checking `origin/main`:** the sibling took 163-166 in the same hour; renumbered to 167 at merge time.

## Current Status
Live on `brisken-expense-recon` (Fly, commit 131fd5d2, deployed 13:52 UTC). The daily table holds 45 days (the provider's EUR->USD/BRL history starts 2026-07-22; earlier days read the ECB month). July `50622baec444` and August `074a7b8905d7` unchanged (typed rates win). September has no statement yet, so nothing there reads a rate. brisken platform: unknown plan (no `platform` section; the p1 app is a Fly-hosted FastAPI tool, not a workflow-engine op count). p2 status files `p2-product-decks.md` (62d) and `p2-targeting.md` (63d) are stale and untouched this session.

## Next Steps
1. Owner decision: clear the two typed Settings rates (EUR:USD 1.162275, BRL:USD 0.192448; one `PUT /api/settings`) so every month reads the daily rate for its purchase days on its next re-match. Recommendation: yes, since the owner asked for the poll himself and the typed rates make it inert on every live pair; note July's charges before 07-22 would read the ECB July average, not a daily rate.
2. Paste `docs/lovable-fx-daily-rates-prompt.md` into Lovable, publish, bundle-verify (`fx_daily_rates`, `/api/fx/poll`, `wb.fx.source.dailyRate`, `set.fxDaily.*`), move the PROMPT-STATUS row to Applied.
3. Itemize feedback notes #73, #74, #75, #77, #82 (verbatim in the backlog's Open section).
4. Carried over from the 2026-09-23 posting-engine checkpoint: Criss's 2 date-guard exceptions + 3 account refusals, the production Zoho tier, category mapping sign-off, vendor contacts, per-org card routing.
5. Refresh or delete the stale `p2-product-decks.md` / `p2-targeting.md` status files (owner call; not this workstream).

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (item 167; the notes block at the top of Open)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/fx_daily_rates.py
- workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md ("FX rates polled daily from OpenTickers")
- workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-fx-daily-rates-prompt.md
