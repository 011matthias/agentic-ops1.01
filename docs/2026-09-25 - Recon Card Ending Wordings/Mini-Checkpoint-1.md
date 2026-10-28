# Mini-Checkpoint: Recon Card Ending Wordings

**Date:** 2026-09-25
**Status:** Item 199 shipped, deployed (Fly v224, `a8c1fafb`) and driven
**Type:** mini

---

## Summary
Case 3 of the card-attribution map is closed for wordings: a two-digit card
ending now names its card behind explicit lead phrases in five languages, so
September's GoDaddy (446.99 EUR, "ending with the last two digits: 38") reads
card-2838 instead of card-less and suggested private.

## What Was Done
- `cards._ENDING_LEADS` (EN/PT/DE/FR/ES) compiled into `_SHORT_ENDING` on diacritic-folded text; amount guard `(?![.,]\d)`; second-ending rule (`38 and 49` names nothing). PR #1335 (squash subject still says "item 198"; the files say 199, because #1334 took 198 mid-CI).
- Tests: 19 wordings, 10 negatives, 1 route test in `tests/test_card_short_ending.py`. Suite 3312 -> 3342 passed. `regress_check.py` bites on the route test (old two-word leads) and on `Total final: 38.50` (guard removed).
- `tools/recon-match-attribution.py`: dropped the call to the retired `MatchingConfig.fx_reference_rate` (item 168), which crashed the tool on every bundle.
- Measured: census over 88 live hints, one changes (GoDaddy None -> 38). Attribution over the six ER bundles plus the live July/August bundles, old vs new tree: per-receipt JSON byte-identical. Scorer 70/95, determ_wrong 0.
- Live after v224, diffed row by row against a pre-deploy snapshot: only GoDaddy moved (card-2838, `card_ending: "38"`, Corporate Services, Dirk Neumann - Corp Services, `suggested_private: false`); September `n_suggested_private` 6 -> 5, card-less 28 -> 27, unknown-card groups 8 -> 7; no other month moved. Cold scripted drive (headless Playwright `channel="chrome"`): the row renders "matched on the last two digits (38)" with no private chip, the panel reads "7 receipts name a card the tool does not know yet" without GoDaddy, the only non-GET was the login.

## What Did NOT Work (and why)
- **`recon-match-attribution.py` as shipped on main:** AttributeError `MatchingConfig.fx_reference_rate`, removed by item 168; fixed in #1335.
- **Merging #1335 on its first green CI (twice):** main moved in between (#1334 claimed item 198; #1336 added item 200), GraphQL "Pull Request has merge conflicts"; merged `origin/main` in each time, no rebase, no force-push.
- **`flyctl releases` with its own token discovery:** "no access token available"; passed `~/.fly/config.yml`'s token as `FLY_API_TOKEN` (known issue, fly-hosting memory).
- **Edit tool on `cards.py`'s regex block:** the file mixes literal `\u2022` escapes with real `•` characters, so no old_string form matched; spliced the block with a Python script.

## Current Status
Item 199 is live and verified. `card_ending: ""` on the rendered OpenAI bodies ("credit card ending in 9693", a leftover listed in the 9693 checkpoint) is correct by contract: `card_ending` is set only when two digits named the card, never for a last-4. brisken ops status: unknown plan (no `platform` section).

## Next Steps
1. Item 195: write the red test first (PDF attached with no account id, reread, assert entity).
2. Leftovers from 196/197: sticky `error` on rendered entries, a dead attach job leaving `--2.pdf`, the overlap advisory saying "same account" for two cards.
3. Waits on Dirk: the 0113 (Apple Card) statement export. Nothing waits on the owner: item 200 is closed not built (failed usefulness test, owner 2026-09-25) and item 204's decisions are taken.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 195, 196, 199-202)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cards.py` (`_ENDING_LEADS`, `masked_short_ending`, `names_registry_card_type`)

## Continuation prompt

````
/comd_resume brisken

# Brisken p1 expense-recon: next queue after item 199 (card-ending wordings)

## Where it stands (2026-09-25)
- SHIPPED this session: item 199, a two-digit card ending printed in other words names its card (PR #1335, Fly v224, commit a8c1fafb; the squash subject says "item 198" because #1334 took 198 while CI ran, the files say 199). `cards._ENDING_LEADS` holds explicit lead phrases in EN/PT/DE/FR/ES; a new wording is one line there. September's GoDaddy now reads card-2838, verified in the payload and by a cold browser drive.
- Also fixed: `tools/recon-match-attribution.py` crashed on every bundle (it called the retired `MatchingConfig.fx_reference_rate`); it runs again.
- Not a bug, do not chase: `card_ending: ""` on the OpenAI bodies that print "credit card ending in 9693". `card_ending` is set only when two digits named the card, never for a last-4 (docs/api-contract.md, "Two printed card digits name a card").
- Sibling-owned, not this loop's, do not build: items 201, 196 and 202 (the GL session) and the private-card-list fold into `cards.classify_payment_evidence`. Also shipped the same night: item 203 (private only on positive evidence, #1340); item 204 (the case-9 backbone) is planned with its owner decisions taken.
- Closed, do not reopen: item 200 (vendor card history), not built on the failed usefulness test (owner 2026-09-25). A shared two-digit ending (76, 13) therefore stays a contest for review.
- Waits on Dirk: the 0113 (Apple Card) statement export. Nothing waits on the owner.
- Waits on Criss: nothing new. No writes to her months, and do not offer any.

## Queue, in order
1. Item 195: a statement re-read can re-stamp a PDF's charges with the entity "card" (code-traced, no live case). Red test first: PDF attached with no account id, reread, assert entity.
2. Leftovers from items 196/197: the sticky `error` on rendered entries, a dead attach job leaving its file (`--2.pdf`), the overlap advisory saying "same account" for two different cards (1176 vs 9693 files). The item-196 build touches the attach path: merge main first and re-read these three before starting.

## How to work

**Worktree, cut fresh:**
- `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin`
- `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-<item-slug> C:\Users\neuma_p1qrsic\Repo\agentic-ops1-<slug> origin/main`
- Never edit, commit or stash in the main checkout: several sibling sessions sit on it. Never `git stash` anywhere.
- A hook refuses `cd X && ...`; use `git -C`, `uv run --directory` and absolute paths.

**Shared files:**
- Sibling sessions edit `cards.py`, `web/service.py`, `docs/api-contract.md`, the backlog and the status file, often within the same hour.
- Append at the END of the relevant block; never renumber or reflow.
- Before the first push, `git rebase origin/main` is fine (commit first). After any push, only `git merge origin/main`: never rebase, never force-push.
- Merge main before claiming a backlog item number or a Shipped row number, then take the next free one. Expect a collision anyway (this session lost 198 to #1334 during CI): make the merge loop merge the moment checks go green, and re-merge main on "Pull Request has merge conflicts".

**Live reads only:**
- API `https://brisken-expense-recon.fly.dev`: `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it). Bearer token in `Authorization`.
- Months: January `4ceaeb461386`, April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`. Month counts sit under the view's `summary` (`summary.n_suggested_private`).
- SPA: `https://brisken-reconcile-dash.lovable.app` redirects to `expenses.brisken.com`; its API is `api.expenses.brisken.com`.
- No writes to Criss's months or settings. Never fetch `GET /runs/{id}/expense-report.pdf` live.

**Suite:** `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (about 10 minutes; 3342 passed, 2 skipped at a8c1fafb). Background it and register `uv run tools/bg_watch.py watch --label "recon suite" --eta 12`. Heredocs with triple quotes are blocked: write scripts with the Write tool. `cards.py` mixes literal `\u` escapes with real characters, so the Edit tool can fail on it; splice with a short Python script when it does.

**Ruff:** `uv run --no-project --with ruff ruff check src tests` from the module dir. A `tools/` change also needs `uv run tools/preflight-hooks.py`.

**Ship:** commit with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01`, CI in a background loop (`gh pr checks <n> --json name,bucket`, plus `gh api repos/011matthias/agentic-ops1.01/pulls/<n> --jq .mergeable_state` for "dirty"), merge on green with `gh pr merge --squash --delete-branch`.

**Deploy** (pre-authorized):
1. `flyctl releases -a brisken-expense-recon`: a sibling's deploy may already carry your commit. If flyctl says "no access token available", export `FLY_API_TOKEN` from `~/.fly/config.yml`'s `access_token:` without printing it.
2. `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-<slug> origin/main`, confirm your merge is an ancestor of HEAD there.
3. `M=C:/Users/neuma_p1qrsic/Repo/agentic-ops1-deploy-<slug>/workspace/clients/brisken/automations/expense-reconciliation`, then `MSYS_NO_PATHCONV=1 flyctl deploy "$M" --config "$M/fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)"`.
4. Prove it with `/healthz` `server.commit`, then remove that worktree.

**Verify behaviour, not the deploy:** snapshot the live rows before the deploy and diff after, row by row, across every month; then a cold browser read-back with headless Python Playwright `channel="chrome"` (click `input#code`, `keyboard.type` the code, press Log in via JS `click()`, wait for localStorage `erc-token`), asserting the changed field renders and that the only non-GET request was the login. Name a scripted drive as such in the closing text. The Playwright MCP is wired to the owner's Edge on :9222 and times out; do not use it.

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
