# Mini-Checkpoint: Recon Strip Count Needs Category

**Date:** 2026-09-24
**Status:** Brisken p1 recon; items 192 and 193 backends live, both Lovable prompts NOT pasted
**Type:** mini

---

## Summary

The number beside each card on the `/months` strip was `n_transactions`: statement lines across all months, credits included, with no label, so 1176's "3" was one charge plus two credits. Asked with a recommendation, the owner picked **expenses needing a category, all months**, with **2838 counting only itself** (item 193). The backend is shipped and deployed as Fly `3f6f1c8d`; the strip prompt waits on paste and Publish, beside item 192's `/cards` prompt.

## What Was Done

- PR #1320 (`3f6f1c8d`). `receipt_card_counts` counts the NEEDS CATEGORY box's own set (`"uncategorized"` in `expenses[].boxes`, which is what `summary.n_uncategorized` counts). `GET /api/cards/status` carries `n_needs_category` per receipt month, per card (its own) and on `no_card`. Also in the PR: the contract doc and `docs/lovable-strip-count-needs-category-prompt.md`.
- Verification. `tests/test_card_status_needs_category_item_193.py` has 3 tests: a route test that holds a month's cards plus No card equal to its `summary.n_uncategorized` and refuses to pass on an empty box; the per-card total; a helper differential. `regress_check` bites on the roll-up entry (route test) and the box predicate (helper test only). Full suite 3306 passed / 2 skipped. After deploy, the endpoint equals the Expenses-page count per card: 2838 3, 3645 1, 3876 10, 0340 3, 1176 2, 9693 3, 4700 0, No card 8. The 30 total equals the months list's Needs category column summed. A cold drive of `/months` shows it still renders, with the old charge numbers until the paste.

## What Did NOT Work (and why)

- **A route-level differential through the category route:** not attempted. `POST /api/runs/{id}/categories` drops strings outside `recognize_category`'s vocabulary, and categorization belongs to another session. The differential went into a helper test.
- **`git show origin/main:<path>` from Git Bash with `MSYS_NO_PATHCONV=1` and a `/c/...` `-C` path:** "not a git repository". Disabling path conversion also stops `/c/Users/...` from resolving.

## Current Status

Two prompts wait on the owner: item 192 (`/cards` overview) and item 193 (strip count). Item 191, a sibling session's nested subcards, looks applied: the Lovable repo has `41dc0f4` "Added nested subcard rows" and the owner's screenshot shows the nesting. Its PROMPT-STATUS row still says not pasted. Context 453k at checkpoint.

## Next Steps

1. After the owner publishes: bundle-audit and cold-drive 193, then 192, then record 191. The continuation prompt below carries the check values.
2. Only if the owner reports slow loads: a per-run cache in `build_card_status`.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-strip-count-needs-category-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-cards-overview-prompt.md`

## Continuation prompt

````markdown
/comd_resume brisken

Brisken p1 expense-recon. Three Lovable prompts wait on the owner's paste and Publish; nothing else is open.

## Where it stands (2026-09-24)

- **Item 193, the months strip's chip number means "needs category"** (owner: the numbers "have to be consistent in their meaning"; picked "All needs category items", 2838 counting only itself). Backend LIVE: PR #1320, Fly `3f6f1c8d`. `GET /api/cards/status` carries `n_needs_category` per receipt month, per card (its own) and on `no_card`, counted from the NEEDS CATEGORY box's own set (`"uncategorized"` in `expenses[].boxes`). SPA prompt `docs/lovable-strip-count-needs-category-prompt.md`, NOT pasted.
- **Item 192, /cards becomes an overview** (owner: "this should just be an overview and not another gate to inside the months"). Backend LIVE: PR #1312, Fly `45d4c494`: `expenses[].without_charge`; per card `n_receipts` / `n_receipts_without_charge` / `n_receipts_no_statement`; per receipt month `n_without_charge` + `statement`; `no_card.n_without_charge`; the footnote now says the fold holds cards with no receipt either (until the paste, the live page still folds 9693 with 16 receipts away). SPA prompt `docs/lovable-cards-overview-prompt.md`, NOT pasted.
- **Item 191 (sibling session's, nested subcards)** looks applied: the Lovable repo `011matthias/brisken-expense-review` has `41dc0f4` "Added nested subcard rows", and the owner's screenshot shows 3645 / 3876 / 0340 opening under 2838. Its PROMPT-STATUS row still says not pasted.
- **Item 190 APPLIED** this session (PRs #1300, #1307): published and all eleven §7 checks driven cold.

## The queue

1. **Each prompt, only after the owner says it is pasted AND published.** A paste can sit unpublished (it did for 190): shallow-clone the Lovable repo and grep its `src`, AND audit the live bundle with a wrapper over `tools/lovable-bundle-audit.py`'s `fetch_corpus` + `CONTROLS` (keep the controls; a scratch wrapper is at the previous session's scratchpad pattern). Then the prompt's check table, cold:
   - **193:** strip 2838 **3**, 1176 **2**, 4700 ● **0**, No card **8**, All with no number; subcards 3645 **1**, 3876 **10**, 0340 **3**; behind "Show 4 cards" 9693 **3**, 0113 / 6013 / 8311 **0**; tooltip "10 expenses need a category, across all months" (PT "10 despesas precisam de categoria, em todos os meses"); 3645 singular "1 expense needs a category, across all months". Bundle: `cardStrip.count.one`, `cardStrip.count.many`, `n_needs_category`.
   - **192:** `/cards` has no strip, no card panel, rows do nothing on click; row order 2838, 3645, 3876, 0340, 9693, 1176, 4700 ●, No card; 2838 "No statement for: September 2026, June 2026, May 2026", Receipts 41, Without a charge 12, Credits 2; 3876 Receipts 95, Without a charge 39, tooltip ending "32 of them are in months with no statement for this card."; 9693 in the table with 16 / 16; No card 72 / 62; fold "Show 3 cards". Bundle: `cardsPage.col.noCharge`, `cardsPage.noStatementFor`, `cardsPage.noCharge.waiting`.
   - **191:** record it applied if the bundle and a drive confirm (its own prompt's check table).
   Then mark each applied in the backlog heading and PROMPT-STATUS (move the row to Applied), PR, merge. Live values drift as Criss works: re-read `/api/cards/status` before asserting a mismatch.
2. **Only if the owner reports `/months` or `/cards` loading slowly:** a per-run cache in `build_card_status` keyed on the month's `updated_at` (the call is ~2.2 s).

## Waiting on others, not queue items

- **Dirk**: statements for cards 9693, 0113, 6013 and 8311.
- **Criss or the owner**: card 3645's `zoho_account` (item 172, should read `CHASE VISA - 2838 - TRAVEL`), and August `0008__Invoice-HMVWDWIL-0029.pdf` / `0027__Invoice-HMVWDWIL-0028.pdf`, both picked 2838 where the charge posted on 3645.
- **Owner**: the commercial framing for new surfaces under the October licence; 185, 187, 190, 192 and 193 all arrived as directives.

## Constraints

- **No live writes on Criss's months or master data.** Read, predict what would move, stop. Never offer a refresh, reset or re-match as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3x3 account table.
- Categorization and GL-account definition are OUT of scope (owner direction 2026-09-23); that work lives in another session.
- Operator code = local vault entry `Brisken recon operator code matthias` in `~/.passwords.json`, shape `{"code": ..., "notes": ...}` under the entry NAME as the top-level key. Never print it; read it into a variable and pass the variable.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live.
- September is capped at 160 hours, real hours only. Licence EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog and status files all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/**`) on a `docs/...` branch; client `status/` files on a client branch. Prune merged, clean worktrees at the end. Avoid `sed -i` on CRLF files; check `git show --numstat` for a whole-file diff.
- **Read the published bundle before believing any claim about the screen**, and the Lovable repo's `main` too (a shallow clone into the scratchpad; reading its source is fine, running it locally is denied by the auto-mode classifier). Minified JS is one line: count occurrences, never `grep -c`.
- **Read `/feedback.jsonl` early** (86 notes as of 2026-09-24). The text field is `comment`; `page` / `selector` / `anchor` say where it was left.
- Live API reads: `POST /api/login` returns a **token** for `Authorization: Bearer`. Host `https://api.expenses.brisken.com`. `/api/version` does NOT exist. `GET /api/expense-batches`, `/api/expense-batches/{id}`, `/api/runs/{id}`, `/api/cards/status`, `/feedback.jsonl`.
- A month is two SPA routes: Expenses `/expenses/{id}` and Matching `/runs/{id}`.
- Browser drives: `agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"` in SEPARATE foreground calls. Login is `textbox "Access code"` then `button "Log in"`. **Click by a fresh `snapshot -i` ref**: a CSS selector with a leading slash (`a[href^="/expenses/..."]`) from Git Bash reports Done and does nothing, and refs go stale after any navigation. Put eval JS in a scratch file and pass `"$(cat file)"`. To prove a localStorage cleanup, seed the key first; a fresh session having none proves nothing.
- Python heredocs over 80 lines or with triple quotes are blocked: write the script with the Write tool. A backgrounded command's `.output` file: wait for the notification, then Read it.
- Backend changes: a route-level test through the caller, then `uv run <worktree>\tools\regress_check.py --test "uv run --directory <module> --extra dev --extra web pytest -q -p no:warnings tests/test_x.py" --file <module>\src\...\y.py --replace "<wired call>" --with "<disabled>"` (PowerShell: no `Set-Location`, absolute paths). Full suite to a file in the background (`*> suite.txt`, 7-8 min; 3306 passed / 2 skipped on 2026-09-24), with `$env:PATH = "C:\Program Files\Git\usr\bin;$env:PATH"`. CI ruff: `uv run --no-project --with ruff ruff check tools .claude/hooks tools/tests workspace/clients/brisken/automations/expense-reconciliation/src workspace/clients/brisken/automations/expense-reconciliation/tests`.
- Commit, push, open the PR autonomously. `gh pr checks <N> --watch` and `gh pr merge` as SEPARATE calls. Deploy only if code changed, from a clean detached `origin/main` worktree at the merge SHA: `flyctl deploy <module dir> --config <module dir>\fly.toml -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<40-char SHA>`, `access_token:` from `~/.fly/config.yml` into `$env:FLY_API_TOKEN`. After any deploy: a live API probe AND a cold real-Chrome read-back. Keep the ship chain inside one turn: do not close a turn on "I'll merge once CI is green".
- In the same PR, update the backlog item's heading and status.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137); building the attribution instrument plus item 169 end to end cost about 280k on 2026-09-23, and item 173 on top of it another 70k. On 2026-09-24 items 171 and 173b together cost about 250k; item 176 plus the bundle read, six PRs, a deploy, a cold drive and the note-86 scoping cost about 175k; items 108 and 185 together, both shipped and deployed with five PRs, two cold drives and a checkpoint, cost about 230k; the footnote fix plus item 187 end to end, four PRs and three cold drives, cost about 145k. Item 190's step 4 (bundle, eleven-row cold drive, two status PRs) cost about 60k; item 192's backend plus prompt with a deploy cost about 105k; item 193's the same shape about 65k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries you registered.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green. If work continues after the checkpoint, amend it rather than leaving stale numbers standing.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
