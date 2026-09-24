# Mini-Checkpoint: Card Attribution Learners

**Date:** 2026-09-24
**Status:** items 171 and 173 (both halves) shipped and deployed; card-attribution queue continues at items 175/176
**Type:** mini

---

## Summary

Closed both open card-attribution learner defects. The sign-off learner can now
see the card the statement named (item 171), and the ingest stamp obeys the
single-card gate the read-time half already held (item 173, second half). Both
merged and deployed to Fly; live rows are unchanged by design, because neither
path can fire without a new month or a sign-off.

## What Was Done

- **Item 172 shipped** (PR #1244, `60900fe5`): the previous session's unpushed
  commit, recording that card `3645`'s `zoho_account` should read
  `CHASE VISA - 2838 - TRAVEL`, read from Zoho's own chart. Not written; that
  is Criss's or the owner's.
- **Item 171 shipped** (PR #1247, `f059fccc`): `commit_to_memory` passes
  `settled_cards=export_settled_cards(run, decisions)` into the resolution it
  hands the card learner, so `settled_charge` (listed in
  `_CARD_OBSERVATION_SOURCES` since item 111) is reachable at last. Six
  route-level tests through `POST /api/runs/{id}/publish`, regress-checked.
- **Item 173 second half shipped** (PR #1252, `5ebfedfb`): the rule moved to
  `MerchantRegistry.vouches_one_card` off a new `MerchantMatch.cards_seen`, and
  `drop_unvouched_remembered_cards` now clears an unvouched stamp in all three
  ingest paths (`cli.generate_expenses`, the add job, the quarantine restore),
  each before the entity stamping. Nine tests, both wiring points
  regress-checked.
- **Main was red** from a sibling's unused `pathlib.Path` import in
  `test_receipt_render_178.py` (#1245); fixed inside PR #1247.
- Corrected `project_brisken_expense_recon_merchant_registry`: CI **does** run
  this subtree's pytest (`expense-recon-tests.yml`); only the ruff half of the
  old claim still holds.

## What Did NOT Work (and why)

- **Narrowing item 171's settled map to confirmed-only pairs.** The obvious
  choice, since every other learner in `commit_to_memory` is confirmed-only.
  Measured against both live statement months first: the narrow map teaches
  nothing in July (its one row is Amazon, absent from the registry) and only
  `Anthropic -> 3645` in August, which would enter one of the three vendors
  item 154 forbids guessing into `cards_seen` as a single-card merchant. The
  full reconciled bucket sees Anthropic on both cards and pins neither.
- **Gating item 173b at one call site.** `ExpenseMemory.apply` has three
  callers, not one; the route test kept failing against a gate wired only into
  `cli.generate_expenses`, because the SPA's add-receipts job is a separate
  path. Enumerating the callers first (B2.1) would have found it.
- **`flyctl` in this shell.** It reports "no access token available" despite a
  valid `~/.fly/config.yml`; passing `FLY_API_TOKEN` from that file works, and
  must be re-set per call.
- **`flyctl ssh sftp get` of the 1.9 MB live DB.** Hung at 64 KB twice. The
  measurement ran on the machine instead, via a base64'd script through
  `ssh console -C`, against a read-only `/tmp` copy.

## Current Status

Fly `brisken-expense-recon` serves `5ebfedfb`. Verified after deploy: operator
login 200, and September / August / July read back 77 / 25 / 54 rows with
26 / 2 / 15 card-less. Cold-seat Chrome drive of `expenses.brisken.com`
(login form, then September) renders 77 rows, 19 "No legal entity yet",
zero fallback strings. Identical to the pre-deploy read, which is the correct
expectation: item 171 fires only at a publish on a statement month, item 173b
only at the ingest of a new one.

Brisken platform ops status: unknown plan, last assessed unknown.

**Close-out (amended after the checkpoint's own PR landed).** The ledger
shipped as #1254 (`67fd96b7`) and the p1 status roll-up as #1255
(`afb51c32`); this session's five worktrees are pruned and its `bg_watch`
entries cleared (the remaining `workflow-wf-67f7bc1f` watch belongs to a
sibling). Nothing uncommitted, nothing half-deployed.

One friction worth naming, because it cost a second CI round on both ledger
PRs: **#1254 went `dirty` between opening and merging**, when a sibling landed
its own 2026-09-24 checkpoint (#1253) touching `docs/INDEX.md`,
`docs/sessions/2026-09-24.md` and `p1-expense-reconciliation.md`. GitHub
reported `mergeable_state: dirty` only at the merge attempt, and `gh pr merge`
refused. The remedy is already in the continuation prompt's How-to-work
section: on a shared-clone day, merge `origin/main` again immediately before
merging a ledger PR rather than only before pushing it, and read
`mergeable_state`, not just the check list. Four sessions were live in this
clone today, so the window is wide, not exceptional.

## Next Steps

1. **Item 175** — a private expense asks which card paid, not who owes the
   money back (note #74). Card/person attribution, unclaimed.
2. **Item 176** — the private control is offered again on a row already marked
   private (note #75). Same area, unclaimed.
3. **Item 108** — cards 9693 and 1176 have never had a statement loaded, which
   is why September's OpenAI receipts cannot attribute from a charge at all.
   Not code; needs the statements.
4. Owner / Criss: write card `3645`'s `zoho_account` (item 172), and resolve
   the two August rows where her card pick contradicts the statement she
   confirmed.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 171, 173,
  175, 176)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/merchant_registry.py`
  (`vouches_one_card`, `drop_unvouched_remembered_cards`)
- `tools/recon-attribution-replay.py` (the instrument, before and after any
  attribution change)

---

## Continuation prompt (next session)

/comd_resume brisken

Continue the card-attribution work on Brisken p1 expense-recon: which card paid a receipt, and through the card which legal entity and which person. Categorization is OUT of scope by owner direction 2026-09-23 ("no working on expense category definition anymore it is bein worked on in different session"); items 179, 180, 181, 183 and 184 belong to that other session, and item 170 is closed. Everything below was read live on 2026-09-24; do not re-derive it, but re-read anything you are about to change.

## Where it stands

Shipped and deployed this session, Fly `brisken-expense-recon` now serves merge SHA `5ebfedfb`:

- **Item 172** (PR #1244, `60900fe5`): the answer only. Card `3645`'s `zoho_account` should read `CHASE VISA - 2838 - TRAVEL`, byte-identical to `3876`, `card-0340` and `card-2838`, read from Zoho's own `chartofaccounts`: Corporate Services (`822741658`) has exactly ONE Chase Visa credit-card account. NOT written; a `PUT /api/settings` on Criss's live master data is hers or the owner's. No live rows point at 3645 except Criss's own override.
- **Item 171** (PR #1247, `f059fccc`): `commit_to_memory` now passes `settled_cards=export_settled_cards(run, decisions)` into the resolution it hands `registry_card_upserts_from_expense_run`, so `settled_charge` (in `_CARD_OBSERVATION_SOURCES` since item 111) is reachable. Six route-level tests in `tests/test_settled_charge_learner_item_171.py`, all through `POST /api/runs/{id}/publish`; regress-checked.
- **Item 173, second half** (PR #1252, `5ebfedfb`): the single-card rule moved into `MerchantRegistry.vouches_one_card`, reached off a new `MerchantMatch.cards_seen` instead of a raw settings dict; `service.merchant_vouches_one_card` delegates to it. `merchant_registry.drop_unvouched_remembered_cards` clears an unvouched ingest stamp and is wired into **all three** `ExpenseMemory.apply` callers — `cli.generate_expenses`, `service.add_receipts_to_expense_batch` (the SPA add job and mail intake), and the quarantine restore — each BEFORE the entity stamping, because the card resolves the company and the person too. Nine tests in `tests/test_remembered_card_ingest_gate_item_173.py`; both wiring points regress-checked. The restore path shares the helper and has no biting test of its own.

**Two findings worth keeping.**

The item-171 settled map is the **effective reconciled bucket, not confirmed-only**, and that was measured, not assumed. Confining it to pairs Criss confirmed by hand teaches nothing in July (its one row is Amazon, absent from the registry) and only `Anthropic -> 3645` in August, entering one of the three vendors item 154 forbids guessing into `cards_seen` as a false single-card merchant. The full bucket sees Anthropic on both cards and the upsert pins neither. The asymmetry generalises: under-observing that learner invents facts, over-observing it only makes it say nothing.

Three existing tests were relying on the ungated ingest stamp and went red under item 173b (`test_card_fix_per_row.py::test_publishing_remembers_the_fix_and_next_month_takes_it`, `test_entity_from_settled_charge_item_111.py::test_the_settled_charge_outranks_a_card_remembered_from_an_earlier_month`, `test_private_expense.py::test_a_remembered_card_does_not_block_the_private_card`). All three set up cards and no registry, so the card could only have reached the next month through the ingest door. Each now puts its brand in the registry; a bare entry is the vouch.

**Live state, read after the deploy** (operator login + `GET /api/expense-batches/{id}`): September `51a22ad72864` 77 rows, 26 card-less, 25 no-entity, 19 OpenAI rows whose cards are `-` / `3645` / `card-9693`; August `074a7b8905d7` 25 rows, 2 card-less; July `50622baec444` 54 rows, 15 card-less. Unchanged by both items on purpose: item 171 fires only at a publish on a statement month and item 173b only at the ingest of a new one, and no month has ever been published by Criss.

Nothing is in flight.

## The queue, in order

**1. Item 176 — the private control is offered again on a row already private.** The smallest and cleanest. Backend, one predicate: `can_mark_private` is false once `private` is true. Proven on September row 0046 (`processed-D61F3B74-...jpeg`, Luigi Buchholz, 11.80 EUR): `private: true`, `person_source: "private"`, `reimburse_to: "Dirk Neumann"` AND `can_mark_private: true`, which is what renders the doubled "Private (Dirk Neumann)Private (Dirk Neumann)" the operator's note captured. Estate-wide 2 of 2 private rows carry it, and 47 of September's 75 read false, so the flag is not simply always on. Leave the un-mark path alone; it is a different control.

**2. Item 175 — a private expense asks which card paid, not who owes the money back.** Operator (PT): *"No privado, deve haver quem deve reembolsar a despesa"*. The data model already holds it: September's private row carries `reimburse_to` and `reimburse_to_prefill` "Dirk Neumann" and `person_source: "private"`. A UI-shape item: when `private` is set the row should ask for `reimburse_to` and offer the card picker second or not at all. Scale today: `private` 1, `suggested_private` 5, `can_mark_private` 28 of 75. The SPA half needs a Lovable prompt; check whether 176's backend fix changes the shape first.

**3. Item 174 — "From email" on a month that was never sent a statement** (note #73, owner). Adjacent, unclaimed, in the same grid.

**4. Item 108, not code and larger than all of it.** Cards **9693 and 1176 have never had a statement loaded**, which is why September's OpenAI receipts cannot attribute from a charge at all. Needs the statements, not a fix.

**5. Waiting on Criss or the owner.** Writing card `3645`'s `zoho_account` (item 172). And two August rows where her card pick contradicts the statement she confirmed: `0008__Invoice-HMVWDWIL-0029.pdf` and `0027__Invoice-HMVWDWIL-0028.pdf` (she picked 2838; the confirmed charge posted on 3645). The instrument reports these separately from the chain's score.

## Ruled out, do not re-run

- **Confirmed-only narrowing of item 171's settled map** (measured this session; see above).
- **Item 169 fact 1** (narrowing `_card_keys` so a printed number naming no registry card stops blocking the fallbacks): measured ZERO rows across all seven batches, 198 receipts.
- **Item 169 fact 3 as diagnosed** ("keyed on a company the failing row does not have"): the key already matched. September's batch entity is `''`, every card-less row carries `''`, `lookup('', 'OPENAI')` returns `{'card_key': '3645'}`.
- **Item 169 fact 4** (two-digit prose, "ending with the last two digits: 38"): exactly one row.
- Reading the card's last-4 off the scan as free text: 2 in 5 right, invented "1234" three times (item 28).
- Sender / mailbox / `submitted_by` as person, card or entity (owner ruling, item 40); the one exception is `reimburse_to` on a confirmed private expense (item 41).
- Learning a generic tender word (`Visa`, `EC-Karte`) as a card alias (owner ruling 2026-08-21).
- Guessing a merchant's card for anthropic, lovable or openai (item 154) — now enforced on both the memory and the ingest paths.
- One-word or subset-scored merchant aliases as fuzzy keys: 8 of 8 wrong (item 117).
- Matcher tuning levers below the S1 floors, and a matching round three without a freshly labelled month.
- Reading July or August expenses from `GET /api/runs/{id}`: returns zero, serves charges instead.
- **Anything about expense CATEGORY or GL-account definition** (owner direction 2026-09-23).

## Constraints

- **No live writes on Criss's months or master data.** Read, predict what would move at the next re-match, and stop. Never offer a refresh, reset or re-match as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3×3 account table: "not yet, and dont re ask, i will bring this up again when the time is right."
- Operator code = local vault entry "Brisken recon operator code matthias" (`~/.passwords.json`, currently plaintext); never print it, pass it through a shell variable.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live.
- September is capped at 160 hours, real hours only. Licence EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/**`) on a `docs/...` branch; client `status/` files on a client branch.
- **The instrument, first and last.** `RECON_MODULE_SRC=<tree>\...\src uv run --directory <module> --extra dev --extra web python tools/recon-attribution-replay.py --live DB [--learning DB] --run-id ID [--labels CSV] [--held-out] [--what-if NAME]`. It refuses to run if `expense_recon` did not import from that tree. Labels live in the main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/`. **Prove a probe before believing a negative**: a category score once read "0 right, 0 wrong, 35 silent" only because the override key is `(document_id, line_index)` and the join used the document alone. A confident zero is the dangerous direction.
- **Enumerate the callers before wiring a gate** (B2.1). Item 173b cost an extra debug cycle because `ExpenseMemory.apply` has three callers and the gate went into one; the route test then failed for a reason that looked like the gate not working.
- **flyctl needs its token handed to it in this shell.** `flyctl` reports "no access token available" despite a valid `~/.fly/config.yml`; read `access_token:` out of that file into `$env:FLY_API_TOKEN` at the start of every PowerShell call.
- Read-only live DB copy: `flyctl ssh sftp get` of the 1.9 MB `recon-web.sqlite` HUNG at 64 KB twice. Run the measurement ON the machine instead: write the script locally, `[Convert]::ToBase64String`, then `flyctl ssh console --pty=false -a brisken-expense-recon -C "python -c \"import base64; exec(compile(base64.b64decode('<b64>').decode(),'m','exec'))\""`, reading a `/tmp` copy you made with `sqlite3.backup`, never `/data` directly. The container has no `sqlite3` binary. The trailing "Error: The handle is invalid." on Windows is the terminal restore, not a failure.
- Zoho Books read: refresh token in the gitignored brisken `context/.env` (`ZOHO_BOOKS_REFRESH_TOKEN` + `ZOHO_CLIENT_ID`/`SECRET`, DC `com`). Scope is `expenses.CREATE expenses.READ contacts.READ accountants.READ` — `settings.READ` is GONE, so `/books/v3/organizations` 401s and org ids must come from the repo (`coa_gate.py`: Corporate Services `822741658`, Cloud Services `697686691`). `chartofaccounts` works.
- Every backend fix: a route-level test through the caller the fix changed, then `uv run tools/regress_check.py --test "uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q tests/test_x.py" --file C:\...\src\...\y.py --replace "<wired call>" --with "<disabled>"`. Windows paths, single-line literals. **The `--replace` literal must match exactly once**; if a call appears twice, give each site a distinguishing trailing comment (`# grid` / `# export`) rather than mutating the wrong line.
- Python heredocs containing triple quotes, and heredocs over 80 lines, are blocked by hooks: write the script with the Write tool and run the file.
- Full module suite before the PR: `uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q` (7-8 min; read 3171 passed / 2 skipped on 2026-09-24). **CI DOES run this subtree** (`.github/workflows/expense-recon-tests.yml`, path-filtered); only ruff's scope still excludes it, so `uv run tools/preflight-hooks.py` before pushing.
- Commit, push, open the PR autonomously; wait for CI with `gh pr checks <N>` (read `mergeable_state` too — a conflicted PR never gets checks), merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<the real 40-char merge SHA>` from a clean detached `origin/main` worktree (pre-authorized). Read the SHA with `git rev-parse`. `gh pr merge` exits 1 on its local-checkout step while still merging; confirm with `gh pr view <N> --json state`.
- After the deploy: a live API probe AND a cold real-Chrome read-back. `/api/version` does NOT exist on this app; `POST /api/login` with the operator code returns a **token**, which you must send as `Authorization: Bearer` — the cookie alone 401s — then `GET /api/expense-batches/{id}`. The SPA consumer is **`brisken-reconcile-dash.lovable.app`, which redirects to `expenses.brisken.com`**, NOT the Fly origin (its root serves the unauthenticated JSON). Playwright MCP attaches to the user's busy Edge on :9222 and times out — use `agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"`, in SEPARATE foreground calls (`open`, `snapshot -i`, `fill`, `click --wait-nav`, `eval`); a drive buried inside a compound command is not seen by the deploy gate, and `open` backgrounds itself on the first call.
- In the same PR, update the backlog item's heading and status.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137); building the attribution instrument plus item 169 end to end cost about 280k on 2026-09-23, and item 173 on top of it another 70k. On 2026-09-24 items 171 and 173b together, with a live measurement, two deploys and a browser drive, cost about 250k (150k to 400k). Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green. If work continues after the checkpoint, amend it rather than leaving stale numbers standing.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
