# Mini-Checkpoint: Attribution Instrument And The Card Memory That Never Arrived

**Date:** 2026-09-23
**Status:** Items 169 + 173 shipped and deployed; 171 and 172 open; 170 closed by owner direction
**Type:** mini

---

## Summary

Built the instrument the attribution work had been missing since it started
(`tools/recon-attribution-replay.py`), then shipped the one thing it said was
worth rows: a remembered card is read live instead of off the stamp ingest
left, which gives 12 live September rows a card, a company and a person. Three
of the four facts item 169 predicted turned out to be worth zero, one, and the
wrong diagnosis; the instrument is what separated them.

## What Was Done

- **`tools/recon-attribution-replay.py`** (PR #1220, merge `ee5b45c4`). Replays
  a hosted month through `build_expense_view` itself, so its rows are the rows
  Criss sees. Scores card / entity / person / category by link against the
  statement's own `Card` column on confirmed pairs, and against the reviewer's
  own fixes **held out**. `--what-if` re-runs with one link changed and diffs.
  Proven before trusted: a fabricated hint rule for a hint exactly one row
  prints moved the count by exactly one, in all three coupled columns.
- **Item 169 fixed and deployed.** `service.fill_remembered_cards`, wired into
  the grid and the CSV export (Cards R3), and through the export into the month
  report. Live after deploy: September card-less **26 -> 14**, no entity
  **25 -> 13**, no person **25 -> 13**, 12 rows sourced `learned`; July and
  August unmoved. Verified by API read AND a cold-Chrome SPA drive (the company
  cell renders "Corporate Services from card Credit Card Chase Visa - 3645 ·
  Dirk Neumann", 13 of 19 OpenAI rows show 3645, zero show a fallback).
- **Item 170 measured, then CLOSED** by owner direction the same day (PR
  #1224): no further work on expense category definition. The measurement
  (canonical keying worth 7 live rows; the registry CATEGORY frozen at
  ingest the same way the card was) is kept as record only.
- **Item 171 filed** (the sign-off learner cannot see `settled_charge`; 24 rows
  waiting, zero live effect). Written and deliberately reverted: it writes
  durable memory and had no bite test.
- **Item 172 filed** (PR #1221): card `3645`'s registry entry holds
  `zoho_account: "Credit Card - 2838"`, another card's label in an account
  field. Found by the post-deploy consumer drive.

## What Did NOT Work (and why)

- **Item 169 fact 1** (narrowing `_card_keys` so a printed number naming no
  card stops blocking the fallbacks): moves **zero rows across all seven
  batches, 198 receipts**. The three July rows it would unblock (`...2544`,
  `0501-1462-9129`, `Cartao Credito 30 Dias`) have no matched charge and no
  remembered card, so nothing sits behind the guard; September has no
  statement. The patch was proven live (`{'2544'}` -> `()`) before the zero was
  believed.
- **Item 169 fact 3 as diagnosed** ("the learned `card_key` is keyed on a
  company the failing row does not have"): the key already matched. September's
  batch entity is `''`, every card-less row carries `''`, the rule is keyed
  `('', 'openai')`, and `lookup('', 'OPENAI')` returns `{'card_key': '3645'}`.
  The real cause was the ingest-time freeze beside it.
- **Measuring the alias fill by patching settings**: reported 0 rows, and a
  control that rewrote EVERY merchant's category to one value also reported 0.
  The probe is blind by construction, and the blindness is the finding:
  `categorize_receipts_with_registry` runs only when receipts are ADDED, so the
  registry CATEGORY is frozen at ingest exactly as the card was.
- **First held-out category score** (0 right / 0 wrong / 35 silent): the
  override key is `(document_id, line_index)` and I joined on document alone. A
  structurally blind probe returning a confident "the chain produces nothing".
- **Playwright MCP for the consumer drive**: attaches to the user's busy Edge
  on :9222 and timed out at 30s. agent-browser on a cold Chrome seat worked.

## Current Status

Item 169 is live on Fly (`ee5b45c4`, machine `7843d54b579598`), verified
through both the API and the SPA. No live writes were made to Criss's months.
`brisken` platform ops status: unknown plan (no `platform` section in
`infrastructure.yaml`), comms-log absent.

Two brisken status files are stale and were not touched (they belong to p2, not
this session): `p2-product-decks.md` (62d), `p2-targeting.md` (63d).

## Next Steps

**Categorization is OUT of scope** from 2026-09-23 (owner: "no working on
expense category definition anymore"). Item 170 is CLOSED, not paused, and the
prepared alias `PUT /api/settings` diff is not to be sent. The card half
continues.

1. **Item 171** — pass `settled_cards` into the sign-off learner's resolution,
   with a statement-attached month, a publish, and a regress-checked bite test.
   24 rows waiting; zero live effect until a month is signed off.
2. **Item 172 (owner's)** — card 3645's `zoho_account` holds another card's
   label; the real Zoho chart account has to come from him.
3. **Criss's** — the two August rows where her card pick contradicts the
   statement she confirmed (0008 and 0027 Invoice-HMVWDWIL).
4. **Owner's, open question** — should a remembered card be gated on
   single-card vendors the way the merchant registry is? The live
   `openai -> 3645` rule came from one pick, and OpenAI is one of the three
   multi-card vendors item 154 refuses to guess for.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 169-172)
- `tools/recon-attribution-replay.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`fill_remembered_cards`, `resolve_batch_row_cards`)

---

## Addendum: item 173 reversed the 12 rows, on purpose (same day)

Everything above about item 169's **12 filled rows is superseded**. The
instrument's next read said the fix reached further without being right: all 12
rows were OpenAI, and OpenAI's hard evidence is card-9693 eight times against
3645 once, so Criss's single correction had taught the minority card by 8 to 1.
Ten vendors carry evidence on more than one card.

Owner ruling the same day: gate it. **Item 173 shipped and deployed** (PR
#1228, merge `46130b06`): `service.merchant_vouches_one_card` applies a
remembered card only to a brand the registry vouches is paid on ONE card, and
a brand it cannot resolve is not vouched. September is back to card-less 26,
no entity 25, no person 25. Verified live by API and a cold-Chrome drive: the
OpenAI rows render "No legal entity yet / Pick the card that paid" -- an
honest prompt -- and the single row still showing 3645 is Criss's own explicit
override, which correctly still stands.

Item 169's structural fix is unaffected and still worth having: a correction is
no longer frozen at ingest, so the day a single-card brand is corrected, every
existing month takes it.

The continuation prompt below predates this. Read its numbers as the
pre-gate state; the live state is the one in this addendum, and the
authoritative record is backlog items 169 and 173. One item it does not carry:
`ExpenseMemory.apply` still stamps a remembered card at INGEST without the
gate, which is the same ruling's unbuilt second half.

---

## Continuation Prompt

/comd_resume brisken

Continue the card-attribution work on Brisken p1 expense-recon: **which card paid a receipt, and through the card which legal entity and which person**. Categorization is OUT of scope by owner direction 2026-09-23 ("no working on expense category definition anymore"); item 170 is closed, not paused, and the prepared alias `PUT /api/settings` diff is not to be sent. Everything below was read live, read-only, on 2026-09-23; do not re-derive it, but re-read anything you are about to change.

## Where it stands

Shipped this session:

- **The instrument**, `tools/recon-attribution-replay.py` (PR #1220, merge `ee5b45c4`). It replays a hosted month through `build_expense_view` itself, so its rows are the rows Criss sees, and scores card / entity / person by link against the statement's own `Card` column on confirmed pairs and against the reviewer's own fixes **held out**. `--what-if NAME` re-runs with one link changed and diffs; `--what-if sanity:HINT=card-key` is its own proof. Use it before and after every change below.
- **Item 169** (same PR), deployed to Fly `ee5b45c4`, machine `7843d54b579598`. `service.fill_remembered_cards` reads the remembered card LIVE instead of off the stamp ingest left, wired into the grid and the CSV export (Cards R3) and through the export into the month report. Live effect: September card-less **26 → 14**, no legal entity **25 → 13**, no person **25 → 13**, 12 rows sourced `learned`. July and August unmoved. Verified by API read and a cold-Chrome SPA drive.
- **Item 172 filed** (PR #1221), **item 170 closed** (PR #1224), status roll-up and mini-checkpoint (PRs #1222, #1223).

Nothing is in flight. No month has ever been published by Criss, so the learning loop has still never run on a real sign-off.

## The measured picture after the deploy (live, 2026-09-23)

July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`.

| | July | Aug | Sep |
|---|---|---|---|
| receipts | 54 | 25 | 75 |
| card from a printed hint | 19 | 12 | 46 |
| card from the settled charge (item 111) | 19 | 2 | 0 |
| card picked by hand (`override`) | 1 | 9 | 1 |
| card from the merchant registry (item 154) | 0 | 0 | 2 |
| **card from memory (`learned`)** | 0 | 0 | **12** |
| **no card** | 15 | 2 | **14** |
| no legal entity | 14 | 1 | 13 |
| no person | 14 | 2 | 13 |

**The card is still the root of three columns at once**: every entity-less and person-less row is a card-less row. Of the 31 remaining card-less rows, 25 print no payment method at all and 18 print something the registry cannot resolve (`DEBIT`, `VISA`, `EC-Karte`, `girocard`, `Bar`, `Cash`, `Link`, `Wire Transfer`, `Cartao Credito 30 Dias`, `...2544`, `0501-1462-9129`, `DEBIT-MASTERCARD ***** ***** ***** 3281`).

Held out against the reviewer's own card picks: **2 right, 1 wrong, 9 silent** of 12.

## The queue, in order

**1. Item 171 — the sign-off card learner cannot see the statement's own answer.** `_CARD_OBSERVATION_SOURCES` has listed `settled_charge` since item 111, so `commit_to_memory` was always meant to learn the card the STATEMENT named for a settled pair. It cannot: the `card_res` it hands `registry_card_upserts_from_expense_run` is resolved WITHOUT `settled_cards`, the only input that can produce that source, so the branch is unreachable. 24 rows across the seven live batches carry it and would teach pairs like `MARTINO SUPERMERCADO → 3876` (5 rows), `Hostinger → card-2838`, `Typora → card-2838`. Anthropic appears on two cards (2838 ×5, 3645 ×1), which the upsert already refuses to pin, so that guard is in place.

The fix is about three lines (`month_charge_states(run, decisions or {})`, then `settled_charge_cards(...)` into the resolution). It was written and **deliberately reverted** this session, and the reason is the whole instruction for next time: this is the writer of DURABLE memory, and a change there with no regress-checked bite test is the wrong kind of cheap. Build it with a statement-attached month and a publish, assert the registry gains the card, and run `tools/regress_check.py` on it before merging. Live effect today is zero (no month has been signed off), so there is no rush and no excuse.

**2. Item 172 — card 3645 posts to another card's name (owner's).** The twelve newly-carded September rows render `Paid through: Credit Card - 2838`, because card `3645`'s registry entry holds `zoho_account: "Credit Card - 2838"` — another card's LABEL in an account field. No other registry row does that. Master data, not code; it predates the change. A `PUT /api/settings` on Criss's live data is the owner's, and the correct account has to come from Zoho's chart rather than be guessed. Twelve live rows carry it now.

**3. Two August rows where the reviewer's card pick contradicts the statement (Criss's).** `0008__Invoice-HMVWDWIL-0029.pdf` and `0027__Invoice-HMVWDWIL-0028.pdf`: she picked card 2838, and the charge she confirmed posted on 3645. The instrument reports these separately from the chain's score, because obeying her is not a chain error. Her call, not a bug and not ours to change.

**4. An open design question raised by item 169, for the owner.** The live rule `('', 'openai') → 3645` came from one reviewer pick, and OpenAI is one of the three multi-card vendors item 154 refuses to guess for. Item 169 did not change what is learned or its rank; it made an existing rule reach consistently instead of by accident of ingest order, and the settled charge still outranks it. If remembered cards should be gated on single-card vendors the way the merchant registry is, that is its own item and his decision.

Not code and larger than any of the above: cards **9693 and 1176 have never had a statement loaded** (item 108), which is why September's OpenAI receipts could never attribute from a charge. Name it; do not code around it.

## Ruled out, do not re-run

- **Item 169 fact 1** (narrowing `_card_keys` so a printed number naming no registry card stops blocking the fallbacks): measured **zero rows across all seven batches, 198 receipts**. The three July rows it would unblock have no matched charge and no remembered card; September has no statement. The patch was proven live (`{'2544'}` → `()`) before the zero was believed.
- **Item 169 fact 3 as diagnosed** ("keyed on a company the failing row does not have"): the key already matched. September's batch entity is `''`, every card-less row carries `''`, and `lookup('', 'OPENAI')` returns `{'card_key': '3645'}`. No company-less fallback is needed.
- **Item 169 fact 4** (the two-digit prose rule, `cards.py:166-199`, against "billed your Visa card ending with the last two digits: 38"): exactly one row, September `0051__rendered-body.pdf`. The two receipts printing "ending with ...2838" both resolve.
- Reading the card's last-4 off the scan as free text: 2 in 5 right, invented "1234" three times (item 28).
- Sender, mailbox or `submitted_by` as person, card or entity (owner ruling, item 40); the one exception is `reimburse_to` on a confirmed private expense (item 41).
- Learning a generic tender word (`Visa`, `EC-Karte`, `Cartao de credito`) as a card alias: refused at the settings edge, inert at read time (owner ruling 2026-08-21).
- Guessing a merchant's card for anthropic, lovable or openai: the only multi-card vendors, so the guess is available exactly where it is wrong (item 154).
- One-word or subset-scored merchant aliases as fuzzy keys: 8 of 8 probe vendors resolved to a wrong canonical (item 117).
- Matcher tuning levers `fx_date_window_days` below 5, `fx_base_amount_match_pct` 0.005, `fx_reference_match_pct` 0.015 (the S1 optimize run), and a matching round three without a freshly labelled month.
- Reference tokens shared between a statement description and a receipt's numbers as a promoting signal (X1).
- Reading July or August expenses from `GET /api/runs/{id}`: it returns zero, and serves charges instead.
- **Anything about expense CATEGORY definition** (owner direction 2026-09-23).

## Constraints

- **No live writes on Criss's months.** Read, predict which rows would move at the next re-match, and stop. Never offer a refresh, reset or re-match on July, August or September as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3×3 account table: "not yet, and dont re ask, i will bring this up again when the time is right."
- The operator code is the local vault entry "Brisken recon operator code matthias" (`~/.passwords.json`); never print it. Pass it through a shell variable so it never reaches the transcript. The OpenAI key is vault "OpenAI Brisken" and bills Dirk.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live. `reconciliation-report.pdf` is read-only.
- Prove the published bundle carries the new build before driving any SPA control whose OLD behaviour is a write.
- September is capped at 160 hours, real hours only. The licence is EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/INDEX.md`, `docs/friction-register.md`, `docs/sessions/*`, checkpoint folders) go on a `docs/...` branch; client `status/` files go on a client branch.
- **The instrument, first and last.** `RECON_MODULE_SRC=<tree>\...\src uv run --directory <module> --extra dev --extra web python tools/recon-attribution-replay.py --live DB [--learning DB] --run-id ID [--labels CSV] [--held-out] [--what-if NAME]`. It refuses to run if `expense_recon` did not import from that tree, so scoring a branch means pointing it at that worktree. Labels live in the main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/`. **Prove a probe before believing a negative**: this session's first category score read "0 right, 0 wrong, 35 silent" purely because the override key is `(document_id, line_index)` and the join used the document alone, and a card comparison reported `card-0340` as wrong against a statement printing `340`. A confident zero is the dangerous direction.
- A read-only live DB copy: the container has no `sqlite3`, so use python — `flyctl ssh console --pty=false -a brisken-expense-recon -C "python -c \"import sqlite3; ...backup to /tmp...\""`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get /tmp/<f> 'C:\...\scratchpad\<f>'` with a single-quoted Windows target, then delete the `/tmp` copies. The trailing "Error: The handle is invalid." on Windows is the terminal restore, not a failure.
- Every backend fix: a route-level test through the caller the fix changed, then `uv run tools/regress_check.py --test "uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q tests/test_x.py" --file C:\...\src\...\y.py --replace "<wired call>" --with "<disabled>"`. Windows paths only, single-line literals. **The `--replace` literal must match exactly once**; if a call appears twice, give each site a distinguishing trailing comment (`# grid` / `# export`, as `inherit_card_from_copies` already does) rather than mutating the wrong line.
- Python heredocs containing triple quotes, and heredocs over 80 lines, are blocked by hooks: write the script with the Write tool and run the file.
- Full module suite before the PR: `uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q` (about 7 min; read 3060 passed / 2 skipped on 2026-09-23). CI DOES run this subtree (`.github/workflows/expense-recon-tests.yml`), contrary to the line still sitting in `project_brisken_expense_recon_merchant_registry.md` — that memory line is stale and worth correcting.
- Commit, push and open the PR autonomously; wait for CI with `gh pr checks <N>` (read `mergeable_state` too — a conflicted PR never gets checks), merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<the real 40-char merge SHA>` from a clean detached `origin/main` worktree (pre-authorized). Read the SHA with `git rev-parse`; never pad or invent one.
- After the deploy: a live API probe of the changed field AND a cold real-Chrome read-back. `/api/version` does NOT exist on this app (that is unpauseai.com); log in via `POST /api/login` with the operator code and read `GET /api/expense-batches/{id}`. Playwright MCP attaches to the user's busy Edge on :9222 and times out; use `agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"`, and query in the FOREGROUND (`eval`, `fill`, `click`) because `open` backgrounds itself.
- In the same PR, update the backlog item's heading and status.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); building the attribution instrument plus item 169 end to end cost about 280k on 2026-09-23 (160k to 440k). Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
