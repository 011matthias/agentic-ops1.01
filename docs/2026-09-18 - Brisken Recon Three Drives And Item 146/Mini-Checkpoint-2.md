# Mini-Checkpoint: Brisken Recon Three Drives And Item 146

**Date:** 2026-09-18
**Status:** Queue empty. Items 109, 130 (five of six sections), 144 and 146 all closed; one Lovable prompt out; no new feedback notes
**Type:** mini

---

## Summary
The three Applied rows carrying a named unverified half were driven: two closed
outright, the third split into five verified sections and one genuinely absent
screen that now has its own prompt. Item 144 turned out to be already published
and was caught by the re-crawl rule rather than by being told. Item 146 shipped
and deployed on Fly v181, and driving its consumer proved the fix has no visible
effect on Criss's screen, which the item as filed and two of my own PR bodies had
claimed it did.

## What Was Done

- **Item 109 (charge-category) CLOSED on screen, EN and PT.** August's
  Charges-without-a-receipt view renders 205 `button[role=combobox]` and 89
  visible Guess chips; the LOVABLE 15.00 row of Aug 31 carries a 176x32 px picker
  reading "Meals & Entertainment" with the chip beside it, which is the prompt's
  check 1 word for word. PT reads "PALPITE" and "Sem categoria ainda".
- **Item 130 (error codes): five of six sections applied AND wired.**
  `chunk-runs._runId` holds 16 `toast.error(errorText(e, t))` call sites and zero
  remaining `.message)`; no chunk anywhere still shows a caught error's raw
  message. The row chips render NEAR MISS in EN and QUASE IGUAL in PT on one row.
  Its §6 is absent: the not-found and crash screens are client React components
  in the entry chunk with English written into the JSX. Prompt
  `docs/lovable-error-page-lang-prompt.md` written, copy only, no backend gate.
- **Item 144 CLOSED.** The re-crawl found its two signatures already live, minutes
  before the prompt would have gone to the owner a second time in two sessions.
  Driven on July's Tricarico row in both languages.
- **Item 146 SHIPPED + DEPLOYED** (PR #1086, Fly v181, read back with `flyctl
  releases`). July now reads 13/13, 14/14, 7/7, 0/0; August unmoved. It was three
  live counters, not the two the item recorded: `n_suggested_private` was 7
  against 9 and nobody had noticed.
- PRs #1084, #1086, #1087, all CI-green and merged. Suite 2479 passed / 2 skipped.

## What Did NOT Work (and why)

- **Two claims about Criss's screen that were never checked.** The item-146 entry
  said the strip "sits beside MISSING ENTITY ... so Criss can see 15 and 13 at
  once", and I carried that into PR #1086's body and the Shipped row before
  verifying it. Driving the deployed consumer showed the tiles read 14 and 7 from
  `summary`, and the strip's sub-line reads "2 need a card · 9 look private" off
  the hint groups. A bundle read settled it: across all 44 chunks every read of
  the four counters is `i.summary.<field>` and none is `card_review`. The fix is
  right at the payload level and its user-visible effect today is zero.
  Corrected in PR #1087.
- **`body.innerText` as a probe for a chip.** Returned 0 for "Guess" while the
  chip was on screen, because CSS uppercases it and `innerText` returns the
  RENDERED text, "GUESS". Third blind-instrument variety in three sessions, after
  the backtick-blind crawler and the `select`-vs-combobox probe, and this one was
  mine. The probe was re-run against a known state and the count moved.
- **`brisken.lang: "pt-BR"`.** The app ignores it and renders English; the value
  it reads is `"pt"`. Cost one wasted drive before the localStorage dump showed it.

## Current Status

Live: Fly **v181**. Bundle 44 chunks / 1,174 KB, i18n chunk `chunk-x-CLnyiug6.js`,
the fourth rehash in about 26 hours. July `summary`/`card_review` agree on all
four counters; August already did. 69 feedback notes, last 2026-09-17 15:19, none
new. `platform:` section of `infrastructure.yaml` still carries no plan or ops
figures for brisken.

Two p2 status files are stale and were left alone as out of scope for a p1
session: `p2-product-decks.md` (57d) and `p2-targeting.md` (58d).

## Next Steps

1. Paste `docs/lovable-error-page-lang-prompt.md` (item 130 §6), then drive the
   404 route and a forced crash in PT.
2. Brisken comms-log is 10 days stale.
3. Owner/Criss: quotes for #104; operations #119-#128; cost-center data #118;
   Dirk's statement for card 9693 (#108); #129's UI prompt, which nobody has
   written; Criss setting the Tricarico invoice's company by hand.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
  (the second 2026-09-18 audit header and the four rows under it)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 109, 130,
  144, 146 and Shipped row 87)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-error-page-lang-prompt.md`

---

## Continuation Prompt

````markdown
/comd_resume brisken

Continue the Brisken expense-recon (p1) defect loop. Read first: `docs/2026-09-18 - Brisken Recon Three Drives And Item 146/Mini-Checkpoint-2.md`, then `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (the SECOND 2026-09-18 audit header and the four rows under it), then items 130 and 146 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_usability_loop`, `project_brisken_expense_recon_voids_audit`, `project_brisken_recon_matching_program`, `feedback_recon_no_live_writes_criss_acts`, `project_brisken_retainer_600_licence`, `feedback_continuation_prompt_carries_loop`, `feedback_end_iterations_with_remaining_items`.

## Where it stands

- **The queue is empty and nothing is half-done.** 2026-09-18 shipped three PRs, all CI-green and merged: **#1084** (the item 109 and 130 drives, PROMPT-STATUS's second 2026-09-18 audit, and the new error-screen prompt), **#1086** (item 146's backend fix), **#1087** (the v181 verification and a correction). Live on **Fly v181**; read the version back with `flyctl releases`, never infer it.
- **Item 109 CLOSED on screen, EN and PT.** August's Charges-without-a-receipt view renders 205 `button[role=combobox]` and 89 visible Guess chips; the LOVABLE 15.00 row of Aug 31 carries a 176x32 px picker reading "Meals & Entertainment" with the chip beside it. The 2026-09-17 negative was two blind probes at once: a native-`select` count on a page of Radix comboboxes, and a case-sensitive `innerText` match for `Guess` against a chip CSS uppercases to `GUESS`.
- **Item 130: five of six sections applied AND WIRED.** `chunk-runs._runId` holds 16 `toast.error(errorText(e, t))` call sites and zero remaining `.message)`; no chunk anywhere still shows a caught error's raw message. Row chips drive as NEAR MISS / QUASE IGUAL on one row. **Its §6 is the one thing still out**: the not-found and crash screens are client React components in the entry chunk (`index-*.js`, the TanStack root `errorComponent` and `notFoundComponent`) with English written straight into the JSX. Driven cold in PT, `/this-route-does-not-exist-xyz` renders "404 / Page not found / ... / Go home" while the rest of the app is Portuguese. **The prompt's own check 4 could never have passed**: `/runs/does-not-exist-abc123` is the SPA's own missing-run screen with its own pre-existing Portuguese string, and it issues no API refusal, so no `code` reaches `errorText` there.
- **Item 144 CLOSED.** It was already published; the re-crawl found `expx.review.reason.needs_entity_settled_outside` and "paga fora do sistema de cartões" live minutes before the prompt would have gone to the owner a second time in two sessions. Driven on July's Tricarico row in EN and PT.
- **Item 146 SHIPPED + DEPLOYED.** `build_card_review` takes `copy_docs` and its four box-twin counters skip decided copies. July now reads 13/13, 14/14, 7/7, 0/0; August was already agreeing. It was THREE live counters, not the two the item recorded: `n_suggested_private` was 7 against 9 and nobody had noticed. **Its user-visible effect is zero**, which the item as filed had wrong: across all 44 chunks every read of those counters is `i.summary.<field>` and none is `card_review`, so the number beside MISSING ENTITY was always the right one. A contract fix, not a screen fix.
- Bundle baseline 2026-09-18 later: **44 chunks / 1,174 KB**, i18n chunk `chunk-x-CLnyiug6.js`. Four rehashes in about 26 hours.
- **69 feedback notes, last 2026-09-17 15:19 UTC, none new.**
- Owner ruling standing: covered-class defects only until the EUR 600 licence is signed; new function is quoted separately, though the owner reversed that for items 107 and 109 and for the audit items 104, 123, 125-128.
- Waiting on the owner or Criss: paste item 130 §6's prompt; quotes for #104; operations #119-#128; cost-center data #118; Dirk's statement for card 9693 (#108); #129's UI prompt, which nobody has written; Criss setting the Tricarico invoice's company by hand; comms-log is 10 days stale.

## Queue, in order

1. **Verify item 130 §6 once the owner pastes `docs/lovable-error-page-lang-prompt.md`.** Its checking list: `/this-route-does-not-exist-xyz` in PT reads "Página não encontrada" and "Voltar ao início"; `document.documentElement.lang` is `pt-BR` there; the crash screen reads "Esta página não carregou" / "Tentar de novo"; with no stored language it falls back to English rather than blank; and "Page not found" still hits in the bundle, because English is kept.
2. **If the owner has not pasted it, there is no code work queued.** Do NOT invent an item. Re-read `GET /feedback.jsonl` (69 lines, last #69) and take a new note if one has arrived; a new note outranks everything here. Otherwise say the loop is idle and list what waits on the owner.
3. Two p2 status files are stale and out of scope for a p1 session, but worth naming if the session widens: `p2-product-decks.md` (57d), `p2-targeting.md` (58d).

Before each item: `gh pr list -R 011matthias/agentic-ops1.01 --state open`, `git worktree list`, and a grep of recently modified transcripts in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/*.jsonl` for the item number (skip a claimed item), and read `GET /feedback.jsonl` for new notes.

## How to work

- **Re-crawl the bundle before any action predicated on a prompt NOT being applied**, handing one to the owner most of all. This fired for real on 2026-09-18: item 144's prompt was in the Not-applied table and already live. It works only because PROMPT-STATUS phrases it as a rule about ACTIONS rather than a fact about audits.
- **A probe that cannot see the thing returns a confident negative.** Four varieties so far: a crawler accepting only quoted imports (this build writes dynamic imports with BACKTICKS); an equality fixture with no decided copies; a `select` probe on Radix comboboxes; and a case-sensitive `innerText` match against CSS-uppercased chip text. Before trusting an absence, run the probe against a state you already know and check the output CHANGES with the state.
- **Verify what a claim says about the SCREEN by reading the bundle, not by reasoning from the payload.** Item 146's "Criss can see 15 and 13 at once" was false: grep the chunk cache for the field name and look at what precedes it (`i.summary.` vs `card_review`). Every read of a counter is a literal field name in the minified source.
- **The API host is `https://brisken-expense-recon.fly.dev`.** `expenses.brisken.com` serves only the SPA. Use `expenses.brisken.com` for the bundle crawl and the browser drive, the Fly host for API reads. **Python's default urllib User-Agent is refused by Cloudflare** in front of the API (`403 error code: 1010`, before any auth); send a browser UA on every request.
- Live reads: `python <scratch>/api.py GET /api/path "<python expr on d>"` (bearer from `POST /api/login` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env`, held in memory only). `MSYS_NO_PATHCONV=1` for every `/api/...` arg in Git Bash. Windows Python cannot open `/c/...` paths: pass `C:\...` forms. Months list `GET /api/expense-batches`, a month `GET /api/expense-batches/{id}`, its run `GET /api/runs/{id}`.
- **Bundle crawl:** fetch `/` then follow asset references recursively, accepting BACKTICK as well as quoted delimiters, and cache the chunks so later greps cost nothing. Prove the crawler with a control string you know is live (`wb.chargeCat.guess`, `warn.amountMismatch`) before trusting any ABSENT.
- **Browser drive:** headless Playwright `channel="chrome"` via `uv run` with PEP 723 inline deps (plain `python` has no playwright). Log in from the gate, then set localStorage **`brisken.lang` = `"pt"`** (NOT `"pt-BR"`, which the app ignores) AFTER login, then navigate. **Dismiss the feedback widget first**: `[data-fb-widget] [role=dialog]` intercepts every pointer event until its "Got it" / "Entendi" button is clicked. The month page opens on the receipt-chasing panel, not a row grid: switch views with a JS `.click()` on the section pill, matching its text and EXCLUDING buttons starting with "Confirm"/"Confirmar" (the Matched pill and "Confirm all matched" both match a loose regex, and an earlier session hit exactly that). Decided rows hide behind `button[role=switch]`. `?view=` params are stripped on load. **Assert visibility, not presence**: check `offsetParent` and a non-zero rect, because `textContent` finds things `innerText` and the reader do not.
- Parallel builder subagents work well: one git worktree off origin/main per item (`client/brisken/p1-item-<N>-<slug>`), a `general-purpose` Agent per worktree in the background with a self-contained brief, `uv run tools/bg_watch.py watch` per builder. Review the diff of the load-bearing functions yourself, merge origin/main, push, PR, wait for CI, merge on green, deploy, verify. **Send a builder back with SendMessage when its result trades one wrong outcome for another.**
- No writes to Criss's live months; reads only. Never probe publish live. `GET /runs/{id}/expense-report.pdf` WRITES render outcomes: never fetch it live. Never print or save the operator code or a token; tell every subagent the same.
- Never `git stash`. Stage explicit paths. Never `git checkout --` to restore a backup (it restores from HEAD); use a `cp` backup and a `cp` restore. A bare `cd` is blocked by a hook: use `( cd X && ... )` or `git -C`. **Patch CRLF sources in BYTE mode** (`read_bytes`/`write_bytes`).
- Every backend fix: a route-level test through the caller, then prove it bites by hand (copy aside, disable at the WIRING point not the helper, targeted pytest, read the FAILED lines, `cp` restore, assert byte-identical by hash). `tools/regress_check.py` reports "RED (no pytest summary line)" even when the mutated suite is green, so its verdict cannot distinguish a biting test from a dead one. Python heredocs with triple quotes are blocked by a hook: write scripts with the Write tool. Do not import a pytest fixture from another test module (CI ruff F811). **A fixture must contain every row class the real month contains**, or an equality assertion passes while being false, which is how item 146 survived item 144's own test. Full module suite in the FOREGROUND before the PR: `uv run --directory <module> --extra dev --extra web pytest -q -p no:cacheprovider` (no `-n`; about 5 min, 2479 tests as of v181). Deploy with `flyctl deploy . -a brisken-expense-recon --remote-only` from the module dir of a clean detached origin/main worktree (pre-authorized).
- After a deploy: a live API probe of the changed field on BOTH months, then a cold consumer drive. Say plainly what the drive covered rather than the bare word "verified", and **check whether the consumer reads the field at all** before claiming a screen changed.
- In the same PR, update the backlog item's heading/status and its Shipped row (newest-first; highest on main is **87** after item 146), plus `status/p1-expense-reconciliation.md`. SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence ("Do NOT add Supabase or any database", EN + PT-BR strings, a checking list), saved as `docs/lovable-<slug>-prompt.md` with a Not-applied PROMPT-STATUS row.
- **Merge races are the tax.** Siblings merge repeatedly; every PR needs main merged once or twice, and CI builds the MERGE. For the backlog Shipped table keep origin/main's rows first and renumber yours above main's highest (match rows by content, never by index); for api-contract and PROMPT-STATUS keep main's section first and append yours. **When you append a superseding section, fix the superseded sentences in place too.**

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while that session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `--root <that worktree>` BEFORE the `finalize` subcommand (it is a global flag); write the checkpoint prose after `finalize` or rename your file to the number it prints; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green. Keep the topic free of colons and other characters Windows paths reject.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
````
