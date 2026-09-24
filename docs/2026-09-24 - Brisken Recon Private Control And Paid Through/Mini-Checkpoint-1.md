# Mini-Checkpoint: Brisken Recon Private Control And Paid Through

**Date:** 2026-09-24
**Status:** Item 176 shipped, deployed and verified live. Items 175 and 174 both scoped to one unpasted Lovable prompt. No backend work left in the private-expense area.
**Type:** mini

---

## Summary

`can_mark_private` told every confirmed private row it could still be marked
private; it no longer does, and the route that writes the private flag now
lets an already-private row correct who gets reimbursed. The cold drive that
verified the deploy also found what operator note #75 actually captured: the
doubled "Private (Dirk Neumann)" is the Paid Through cell rendering its value
twice, not the flag.

## What Was Done

- **Item 176 shipped** (PR #1258, merge `43305aea`, deployed to
  `brisken-expense-recon`). `can_mark_private` is `not private and (...)` in
  `resolve_batch_row_cards`; `_paid_by_conflict` skips its company-card
  refusal on a row that is already private. Five route-level tests in
  `tests/test_private_not_reoffered_item_176.py`, both wires regress-checked
  green to red to green. Module suite 3176 passed / 2 skipped.
- **Verified live, read-only.** Both private rows in the estate (September
  0046 Luigi Buchholz, July 0028 Brauhaus Kühler Krug) now read
  `can_mark_private: false`; all 15 `suggested_private` rows across the three
  months still read true, so the flag was narrowed and not flattened.
  September's split moved 28/47 to 27/50 on 77 rows.
- **Cold Chrome drive of September row 0046.** Badge and "Undo private card"
  both still render, which was this change's one real risk. The doubled label
  is two elements in cell index 7: a static
  `div.px-1.text-sm.text-foreground` and the `span` inside the account
  select's `role="combobox"` trigger. One row in 80 doubles, and it is the
  private one.
- **Follow-up shipped** (PR #1260, merge `80dffabb`, docs only).
- **Items 175 and 174 scoped from the published bundle**, both SPA-only, both
  in `docs/lovable-private-reimburse-prompt.md` (not pasted). 175's real half
  is that the `reimburse_to` dialog lives inside the card picker, which
  returns null once the row is private, so there is no way to correct who
  gets reimbursed short of undoing the mark. 174's "From email" is
  `months.origin.intake` on the months list, off `created_by`, rendered in
  the statement badge's cell.

## What Did NOT Work (and why)

- **The item's own diagnosis of 176.** It said the flag "is what renders the
  label the note captured twice". The SPA reads `can_mark_private` in one
  helper whose two callers already escape a private row for other reasons
  (the chip needs `suggested_private`, false there; the picker opens with
  `if (row.private) return null`), so the flip changes nothing on screen.
  Correct fix, wrong stated cause.
- **The first bundle scan, which reported the field absent everywhere.** The
  probe was validated (it found `suggested_private` and `reimburse_to`); the
  corpus was not. Chunk names were harvested with
  `chunk-[A-Za-z0-9_-]*\.js`, which cannot match
  `chunk-expenses._batchId-7cO7KDYP.js` because of the dot, so the one chunk
  holding the grid was never downloaded. A validated probe over an incomplete
  corpus still returns a confident absence.
- **`card_source` as item 174's cause.** That field never produces the string;
  "From email" appears once in the whole bundle, as `months.origin.intake`.

## Current Status

Fly `brisken-expense-recon` serves `43305aea`. September `51a22ad72864` 77
rows, August `074a7b8905d7` 25, July `50622baec444` 54; nothing was written to
Criss's months (the change applies at read time in `build_expense_view`, so no
re-match was needed). brisken platform ops status: unknown plan, last assessed
unknown. comms-log 16 days stale.

## Amendment, after the checkpoint

The feedback store held **86 notes** against the backlog's 82. Notes #83, #84
and #85 are all category / GL-account and belong to the other session. **#86
(2026-09-24 00:05, `/months`, owner) was unitemized and is squarely
card-attribution**: a card-first status view across months. Recorded as **item
185** (PR #1264, merge `67555199`) with a live scoping pass: `coverage[]`
already carries `n_transactions`, `n_reconciled`, `n_unmatched_tx`, `n_review`,
`n_refunds`, `unreconciled_by_ccy`, `period_start/end`, `statements`,
`statement_ids` per card per month, so what is missing is the axis, not the
numbers. Across all 7 batches only 3 carry `coverage[]` (April 10, August 10,
July 9); September, June, May and January carry none.

**The same pass corrected item 108.** It said cards 9693 and 1176 have never
had a statement loaded. **1176 has one**: August holds
`20260804-statements-1176-.pdf` and the card reads `n_tx: 3`,
`n_unmatched_tx: 1`, period 2026-07-06 to 08-04. Its coverage row still says
`statements: 0` while an unattributed row (`?`, `known: false`) in the same
month holds `statements: 1`, so the file landed without being linked to the
card whose charges it produced. That link is what is left, and the client must
not be asked for a file that already exists. 9693 is the real half: `n_tx: 0`
everywhere, as are 0113, 6013 and 8311.

## Next Steps

1. **Item 185** is the one real build left in this area: aggregate the existing
   `coverage[]` across batches by `card_key` behind one route, then the SPA
   page. New surface, so quote-separately under the licence's defect scope.
2. **Item 108, the 1176 half**: find why August's 1176 statement is attached to
   the unattributed `?` coverage row instead of `card-1176`. Do not ask the
   client for the file. 9693 still needs a statement that does not exist.
3. Hand the owner `docs/lovable-private-reimburse-prompt.md` (items 175, 174
   and the Paid Through duplicate). No backend work left there.
4. Waiting on Criss or the owner: writing card 3645's `zoho_account` (item
   172), and the two August rows where her card pick contradicts the
   confirmed statement charge.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 174,
  175, 176)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-private-reimburse-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`resolve_batch_row_cards`)

---

## Continuation prompt (next session)

The text below is the prompt handed to the next session, verbatim.

/comd_resume brisken

Continue the card-attribution work on Brisken p1 expense-recon: which card paid a receipt, and through the card which legal entity and which person. Categorization is OUT of scope by owner direction 2026-09-23 ("no working on expense category definition anymore it is bein worked on in different session"); items 179-184 and feedback notes #83, #84, #85 belong to that other session. Everything below was read live on 2026-09-24; do not re-derive it, but re-read anything you are about to change.

## Where it stands

Fly `brisken-expense-recon` serves merge SHA `43305aea`.

- **Item 176 SHIPPED, deployed, verified** (PR #1258, merge `43305aea`). `can_mark_private` is `not private and (...)` in `resolve_batch_row_cards`, and `_paid_by_conflict` skips its company-card refusal on a row that is already private. That second half is load-bearing: the private route reads the same flag before it writes, so without it a correction of who gets reimbursed would have been refused with "this expense was paid with the company card", about a row no company card paid. Five route-level tests in `tests/test_private_not_reoffered_item_176.py`, both wires regress-checked. Suite 3176 / 2. Live: September 0046 and July 0028 (the estate's only two private rows) read `can_mark_private: false`; all 15 `suggested_private` rows across the three months still read true.
- **Item 176 follow-up** (PR #1260, merge `80dffabb`): the doubled "Private (Dirk Neumann)" is the **Paid Through cell**, not the flag. Two elements in cell index 7 carrying the same value: a static `div.px-1.text-sm.text-foreground` and the `span` inside the account select's `role="combobox"` trigger. One row in 80 doubles, and it is the private one.
- **Items 175 and 174 scoped, SPA-only, no backend work left.** Both in `docs/lovable-private-reimburse-prompt.md` (NOT pasted), together with the Paid Through fix.
- **Item 185 recorded** from feedback note #86 (PR #1264, merge `67555199`), and **item 108 corrected in the same PR**.
- Status roll-up PR #1262 (`d8803a78`); checkpoint PR #1261 (`3e122eac`).

**How to read the SPA without a browser.** The published bundle is the cheapest instrument for any "what does the screen actually do" question, and it settled three of this session's four findings. Fetch `https://expenses.brisken.com/`, harvest asset names with a pattern that **allows dots** (the grid chunk is `chunk-expenses._batchId-<hash>.js`, and a `chunk-[A-Za-z0-9_-]*\.js` pattern silently misses it), download every chunk, then grep with `grep -o ... | wc -l` (minified JS is one line, so `grep -c` always answers 1). Validate the corpus by requiring a field the page must read before trusting any absence.

## The queue, in order

**1. Item 185 -- a card-first status view across months** (feedback note #86, owner, 2026-09-24 00:05, `/months`). The one real build left in this area. *"I don't know which month it is on ... being able to select which card I'm trying to find and then see what the status is on that card would be pretty useful."* Most of the arithmetic exists: `coverage[]` on a batch already carries, per card, `card_key`, `label`, `known`, `digits`, `entity`, `n_transactions`, `n_reconciled`, `n_unmatched_tx`, `n_review`, `n_refunds`, `period_start`, `period_end`, `statements`, `statement_ids`, `unreconciled_by_ccy`. Missing is the axis: one route that aggregates those across batches keyed by `card_key`, then an SPA page. Measured over all 7 batches: 9 cards defined in Settings; only April (10 entries), August (10) and July (9) carry `coverage[]` at all; September, June, May and January carry none, and that blankness is itself the answer to "which cards are missing" for those months. Two coverage rows are not cards (`digits:4700`, `?`, both `known: false`) and belong in the view. This is a NEW SURFACE, not a defect fix, so it is quote-separately under the licence's defect-class scope: raise that with the owner before building.

**2. Item 108, the 1176 half.** August holds `20260804-statements-1176-.pdf` and `card-1176` reads `n_tx: 3`, `n_unmatched_tx: 1`, period 2026-07-06 to 08-04, yet its coverage row reads `statements: 0` while an unattributed row (`?`, `known: false`) in the same month holds `statements: 1`. The file landed without being linked to the card whose charges it produced. **Do not ask the client for a 1176 statement; it exists.** Card 9693 is the real remaining gap: `n_tx: 0`, `statements: 0` in every month that has coverage, as are 0113, 6013 and 8311.

**3. The Lovable prompt paste** (owner action): `docs/lovable-private-reimburse-prompt.md` covers item 175 sections 1-3, item 174 section 4, and the Paid Through duplicate section 5. Its section 1 is the half that matters and is not cosmetic: the `reimburse_to` dialog is rendered inside the card picker, which returns `null` once `row.private` is true, so there is today no way in the SPA to correct who gets reimbursed short of undoing the private mark. Item 176 is what makes that correction possible at all.

**4. Waiting on Criss or the owner.** Writing card `3645`'s `zoho_account` (item 172: it should read `CHASE VISA - 2838 - TRAVEL`, byte-identical to `3876`, `card-0340` and `card-2838`, read from Zoho's own `chartofaccounts`; a `PUT /api/settings` on her live master data is hers or the owner's). And two August rows where her card pick contradicts the statement she confirmed: `0008__Invoice-HMVWDWIL-0029.pdf` and `0027__Invoice-HMVWDWIL-0028.pdf` (she picked 2838; the confirmed charge posted on 3645).

## Ruled out, do not re-run

- **`can_mark_private` as the cause of the doubled label** (the published bundle reads it in one helper whose two callers already escape a private row; the cause is the Paid Through cell).
- **`card_source` as the source of "From email"** (that string appears exactly once in the whole bundle, as `months.origin.intake` on the months list, off `created_by`).
- **Asking the client for a card-1176 statement** (August already has one).
- **Confirmed-only narrowing of item 171's settled map** (measured 2026-09-24: teaches nothing in July and only `Anthropic -> 3645` in August, which item 154 forbids).
- **Item 169 fact 1** (narrowing `_card_keys`): ZERO rows across all seven batches, 198 receipts.
- **Item 169 fact 3 as diagnosed**: the key already matched. **Item 169 fact 4** (two-digit prose): exactly one row.
- Reading the card's last-4 off the scan as free text: 2 in 5 right, invented "1234" three times (item 28).
- Sender / mailbox / `submitted_by` as person, card or entity (owner ruling, item 40); the one exception is `reimburse_to` on a confirmed private expense (item 41).
- Learning a generic tender word (`Visa`, `EC-Karte`) as a card alias (owner ruling 2026-08-21).
- Guessing a merchant's card for anthropic, lovable or openai (item 154), enforced on both the memory and the ingest paths.
- One-word or subset-scored merchant aliases as fuzzy keys: 8 of 8 wrong (item 117).
- Matcher tuning levers below the S1 floors, and a matching round three without a freshly labelled month.
- Reading July or August expenses from `GET /api/runs/{id}`: returns zero, serves charges instead.
- **Anything about expense CATEGORY or GL-account definition** (owner direction 2026-09-23).

## Constraints

- **No live writes on Criss's months or master data.** Read, predict what would move at the next re-match, and stop. Never offer a refresh, reset or re-match as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3x3 account table: "not yet, and dont re ask, i will bring this up again when the time is right."
- Operator code = local vault entry "Brisken recon operator code matthias" (`~/.passwords.json`, currently plaintext); never print it, pass it through a shell variable.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live.
- September is capped at 160 hours, real hours only. Licence EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/**`) on a `docs/...` branch; client `status/` files on a client branch.
- **Read `/feedback.jsonl` early.** The backlog lags the store: it stopped at #82 while the app held 86. The note record's text field is `comment`, and `page` / `selector` / `anchor` say where it was left. Notes #83-#85 are the other session's.
- **The instrument, first and last.** `RECON_MODULE_SRC=<tree>\...\src uv run --directory <module> --extra dev --extra web python tools/recon-attribution-replay.py --live DB [--learning DB] --run-id ID [--labels CSV] [--held-out] [--what-if NAME]`. It refuses to run if `expense_recon` did not import from that tree. Labels live in the main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/`. **Prove a probe before believing a negative.**
- **Enumerate the callers before wiring a gate** (B2.1). `ExpenseMemory.apply` has three.
- **flyctl needs its token handed to it in this shell.** Read `access_token:` out of `~/.fly/config.yml` into `$env:FLY_API_TOKEN` at the start of every PowerShell call.
- Read-only live DB copy: `flyctl ssh sftp get` of `recon-web.sqlite` HUNG at 64 KB twice. Run the measurement ON the machine instead (`flyctl ssh console --pty=false -C "python -c ..."` over a base64 payload, reading a `/tmp` copy made with `sqlite3.backup`, never `/data`). The container has no `sqlite3` binary. Most read-only questions are answerable from the API instead, which is cheaper.
- Zoho Books read: refresh token in the gitignored brisken `context/.env`. Scope is `expenses.CREATE expenses.READ contacts.READ accountants.READ`; `settings.READ` is GONE, so the organizations route 401s and org ids come from `coa_gate.py` (Corporate Services `822741658`, Cloud Services `697686691`). `chartofaccounts` works.
- Every backend fix: a route-level test through the caller the fix changed, then `uv run tools/regress_check.py --test "uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q tests/test_x.py" --file C:\...\src\...\y.py --replace "<wired call>" --with "<disabled>"`. Windows paths, single-line literals, `--replace` must match exactly once.
- Python heredocs containing triple quotes, and heredocs over 80 lines, are blocked by hooks: write the script with the Write tool and run the file. The same applies to appending long prose to a file.
- Full module suite before the PR: `uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q` (7-8 min; 3176 passed / 2 skipped on 2026-09-24). **CI DOES run this subtree**; only ruff's scope excludes it, so `uv run tools/preflight-hooks.py` before pushing.
- Commit, push, open the PR autonomously; wait with `gh pr checks <N> --watch` (read `mergeStateStatus` too; `UNKNOWN` usually resolves to `CLEAN` on a re-read, `DIRTY` means a sibling landed and you must merge `origin/main`), merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<the real 40-char merge SHA>` from a clean detached `origin/main` worktree (pre-authorized). `gh pr merge` prints nothing useful on success; confirm with `gh pr view <N> --json state,mergeCommit`.
- After the deploy: a live API probe AND a cold real-Chrome read-back. `/api/version` does NOT exist; the login route returns a **token** to send as `Authorization: Bearer` (the cookie alone 401s), then `GET /api/expense-batches/{id}`. The SPA consumer is **`expenses.brisken.com`**, NOT the Fly origin. Playwright MCP attaches to the user's busy Edge on :9222 and times out; use `agent-browser --session <name> --executable-path "C:\Program Files\Google\Chrome\Application\chrome.exe"` in SEPARATE foreground calls (`open`, `snapshot -i`, `fill`, `click --wait-nav`, `eval`). `open` backgrounds itself on the first call; the next call in the same session works. Post-login lands on the new-batch screen, and the month route is `/expenses/{id}`. An `eval` that returns just the row you care about beats a snapshot of an 80-row grid.
- In the same PR, update the backlog item's heading and status.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137); building the attribution instrument plus item 169 end to end cost about 280k on 2026-09-23, and item 173 on top of it another 70k. On 2026-09-24 items 171 and 173b together cost about 250k; item 176 plus the bundle read, four PRs, a deploy, a cold drive and the note-86 scoping cost about 155k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green. If work continues after the checkpoint, amend it rather than leaving stale numbers standing.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
