# Mini-Checkpoint: Attribution Measured Card Entity Person And Category

**Date:** 2026-09-23
**Status:** measured and recorded; nothing built, by decision
**Type:** mini

---

## Summary

The owner asked for a prompt to improve the matching and fallback logic in the
two areas that work least well: which card (and through it which legal entity
and which person) paid a receipt, and which category an expense gets. The
session measured both across all three live months read-only, found that the
card is the single root cause of three empty columns, and handed over a
continuation prompt grounded in that measurement rather than in the backlog's
older snapshots.

## What Was Done

- **Measured the live estate read-only** (154 receipts, 226 charges, July
  `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`). Card
  sources: hint 77, settled charge 21, hand pick 11, registry 2, learned 0,
  **none 43**. Entity-less 40, person-less 41, and every one of those rows is
  a card-less row in every month. Of the 43, 25 print no payment method at all
  and 18 print something unresolvable. Categorization: 94 of 154 receipts rest
  on the model, 33 carry an override (21 on a repeat vendor), exactly one row
  reads `learned`, 15 have none; 138 of 174 receiptless charges are a guess off
  the bank descriptor; memory holds 108 rules, 102 seeded, 0 validated.
- **Corrected the record.** The live registry now holds 33 merchants (item M1
  measured 28) including Anthropic and Lovable, both with `aliases: []`, so
  M1's registry default never fires for them and three September rows read
  Utilities & Premises off the line text. The gap is the alias list, not the
  entry. Also corrected the item-163 element row, which still read "pending PR;
  not deployed" after the merge, the deploy and the SPA paste.
- **Recorded items 169 and 170** in the backlog: the four points where the card
  chain refuses evidence it holds (the printed-digits guard at
  `service.py:6533`, the learner that never sees `settled_charge`, the
  company-keyed `card_key` recall, the two-digit rule missing prose), and the
  raw-vendor memory key that keeps a correction from reaching a merchant's
  other spellings. PR #1214.
- **Established that no instrument judges either area.** `labels.csv` in all
  eight bundles carries pair labels only, and the item-115 category replay was
  a scratch script that never reached the repo. Named the three truths that are
  free and unused: the statement's own Card column on every confirmed pair, and
  `payment_mode` plus `zoho_category` per receipt in the six ER-PDF bundles.
- **Two pattern rules** from this session's own failures:
  `warn-padded-commit-sha` (a SHA ending in eight zeros is padded, not real)
  and `warn-spa-write-button-click` (gate a Save/Commit/Refresh click on proof
  that the published bundle carries the new build).
- Verified the item-163 SPA paste in both languages and moved its
  PROMPT-STATUS row to Applied (PR #1208, merged earlier in the session).

## What Did NOT Work (and why)

- **A five-reader, five-skeptic grounding workflow on Fable.** The five readers
  finished; four skeptics and the synthesizer died on the model's usage limit,
  so the run returned a null brief. Resuming the same script on Opus replayed
  the readers from cache and cost nothing to recover, but the lesson is that a
  long fan-out on a limited model returns partial work that reads like a
  finished result unless the failure list is read.
- **Editing the backlog on the docs branch.** The branch-isolation gate caught
  it at the first Edit. The fix was a patch archive, a fresh
  `client/brisken/...` worktree and a three-way apply, because `origin/main` had
  moved five commits by then and the straight apply failed on context.
- **Trusting the backlog's own numbers as current.** The skeptic that did
  survive refuted two of them: July's line-source mix had moved since the
  2026-09-17 snapshot, and the registry had grown from 28 merchants to 33 with
  Anthropic and Lovable added. Both were correct citations of a stale
  measurement.

## Current Status

Items 169 and 170 are recorded, not built, and both are gated on an instrument
that has to be written first. PR #1214 carries the measurement. Nothing is
deployed by this session and nothing is in flight.

## Next Steps

1. Build the committed replay instrument (card, entity, person and category per
   row against the free labels), prove it with a fabricated rule, and commit it.
2. Item 169, the four refused-evidence points in the card chain, each measured
   before it is changed.
3. Item 170, keying learned rules on the registry canonical rather than the raw
   vendor string.
4. Items 164, 165 and 166 (the rest of the learning-loop wave) and the
   unitemized notes #73, #74, #75, #77, #82.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md`, the section
  "Attribution and categorization, measured before the next round (2026-09-23)"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py:6488-6603`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorize.py:297-522`

---

## Continuation prompt

/comd_resume brisken

Work on the two matching areas the owner named as working least well: **which card paid a receipt** (and through the card, which legal entity and which person), and **which category an expense gets**. Measure before you build. Everything below was read live, read-only, on 2026-09-23 and is the grounding; do not re-derive it, but do re-read anything you are about to change.

## Where it stands

Item 163 (a memory save previews, records and undoes) shipped, deployed and its SPA half applied, PR #1202 merge `dedd7260`, Fly commit `dedd726002e4`, SPA PR #1208. Item 167 (daily FX rates) and item 168 (typed rates retired) shipped in sibling sessions. The measurement below is recorded in the backlog under "Attribution and categorization, measured before the next round (2026-09-23)" as items 169 and 170 (PR #1214).

Nothing is in flight. No month has ever been published by Criss, so the learning loop has never run on a real sign-off.

## The measured picture (live, 2026-09-23, read-only)

July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`. 154 receipts, 226 charges, September has no statement. Receipts come from `GET /api/expense-batches/{id}`; `GET /api/runs/{id}` returns ZERO expenses for July and August and serves their charges instead.

| | July | Aug | Sep | total |
|---|---|---|---|---|
| receipts | 54 | 25 | 75 | 154 |
| card from a printed hint | 19 | 12 | 46 | 77 |
| card from the settled charge (item 111) | 19 | 2 | 0 | 21 |
| card picked by hand | 1 | 9 | 1 | 11 |
| card from the merchant registry (item 154) | 0 | 0 | 2 | 2 |
| card from memory (`learned`) | 0 | 0 | 0 | 0 |
| **no card** | 15 | 2 | 26 | **43** |
| no legal entity | 14 | 1 | 25 | 40 |
| no person | 14 | 2 | 25 | 41 |

**The card is the root of three columns at once.** Every entity-less and person-less row is a card-less row, in every month (July 14 of 14, August 1 of 1, September 25 of 25). Fix the card and the other two follow; work on entity or person directly and you are working on nothing.

Of the 43 card-less receipts, **25 print no payment method at all** (12 of them September OpenAI, all submitted by Dirk, USD 80-82) and **18 print something the registry cannot resolve**: `DEBIT`, `VISA`, `VISA CREDIT`, `EC-Karte`, `girocard`, `Bar`, `Cash`, `Link`, `Wire Transfer`, `Cartao Credito 30 Dias`, `saved payment method`, `PAYE`, and digit runs naming no registered card (`...2544`, `0501-1462-9129`, `DEBIT-MASTERCARD ***** ***** ***** 3281`). One is a GoDaddy receipt reading *"We have billed your Visa card ending with the last two digits: 38"* where exactly one registry card ends in 38, so the note-#60 two-digit rule does not match that phrasing.

22 of the 43 have a carded sibling of the same vendor somewhere, but the vendors that fail are the multi-card ones: `openai` resolves to card-9693 eight times and 3645 once, `lovable labs incorporated` to four cards, `anthropic, pbc` to four. `expenses[].customer` (bill-to) is empty on **154 of 154** rows, so no company signal survives a missing card.

**Categorization.** Of 154 receipts: 94 rest on the model (`LINE` or `VENDOR`), 33 carry a reviewer override, 8 come from the registry, **1 reads `learned`**, 15 have no category. 21 of the 33 overrides sit on a vendor appearing in another row or month, so the correction had a second row to reach and did not. Of 174 receiptless charges, **138 are a model guess off the bank descriptor** (88 distinct descriptions). Memory holds 108 category rules, 102 still the 2026-08-06 Zoho seed, **0 validated**; `vendor_alias` and `merchant_fx` are empty; `merchant_entity` holds 1 row and `field_correction` 2.

**A correction to the record you will otherwise trust.** `GET /api/settings` now returns **33** merchants (item M1 measured 28), including `Anthropic`, `Lovable Labs`, `Lovable Labs Incorporated`, `Brave Software, Inc.` and `ZOHO Corp.`, each with category Software & Subscriptions and **`aliases: []`**. So M1's registry default never fires for them: three September rows spelled `anthropic, pbc @anthropic` read Utilities & Premises off the line text "Auto-recharge credits", and September produced zero registry-sourced lines. The gap is the alias list, not the entry.

## The card chain as it is

One resolver, `web/service.py:6370 resolve_batch_row_cards`, called with different inputs per surface: the Expenses payload passes `settled_cards`, `settled_outside` and `merchants` (`:7360-7365`); the matcher bake (`:13170`) and the sign-off card learner (`:5207-5212`) pass none of the three.

Order, in code (`:6488-6603`): batch `card_hints` exact-string assignment, then `resolve_card` on digit tokens (`cards.py:782-885`) including the two-digit ending rule (`cards.py:166-199`), then the per-row `card_key` override (`:6529`, source `override`), then the settled charge (`:6533`, `settled_charge`), then the learned `card_key` (`:6541`, `learned`), then the merchant registry (`:6543`, `merchant`), else `none`. Entity: override, else `card.entity`, else `r.legal_entity_id`, else none (`:6554-6562`). Person: confirmed private `reimburse_to`, else `card.person`, else none (`:6563-6569`).

Only `override|hint|learned` scope matching (`CARD_SCOPE_SOURCES`, `matching/deterministic.py:1714`); `settled_charge` and `merchant` never reach the matcher, by design.

## The category chain as it is

Entry `categorize.py:297 categorize_receipts_with_registry`. Order: reviewer override (applied in the view overlay, `service.py:1391-1426`), registry default stamped on every line (`categorize.py:369-403`), a person-taught rule over a readable line read (`:460-493`), the model line read (`:682-719`, below confidence 0.6 it becomes REVIEW), then on a no-line receipt any recall including unvalidated seed (`:495-522`), then the vendor guess, then review. The M1 predicate that gives the ACCOUNT to the (company, vendor) rule while the registry keeps the CATEGORY is `categorize.py:425-431`.

Receiptless charges are pseudo-receipts with empty line items (`categorize_charges.py:67-80`), so they never reach the line tier; `card_last4` and `raw_text` are dropped on the way in.

## The work, in order

**Phase 0, the instrument, before any fix.** Nothing anywhere judges a card, an entity, a person or a category. `labels.csv` in all eight bundles carries only `document_id,transaction_id,status,source,evidence` (a pair label). The item-115 category replay was a scratch script over a `/data` copy and never reached the repo, so its numbers cannot be reproduced today. Three truths are free and unused:

1. the statement's own `Card` column on every `confirmed` pair (37 July + 9 August rows), joinable from `labels.csv` with no judgement at all;
2. `expense_field_overrides` (fields include `card_key`, `legal_entity`, `private`, `reimburse_to`, `paid_through`) and `decision_history` in a read-only copy of the live DB, which is Criss's own answer where she gave one;
3. `payment_mode` and `zoho_category` printed per receipt in the six ER-PDF bundles (~218 rows) by Criss at filing time.

Build one committed tool that replays a month's stored readings through the current code and prints what each row would get for card, entity, person and category, segmented by source, against those labels. Prove the instrument before trusting it: fabricate one rule and watch the count move, the way item 115 did (10 lines moved, 4 flagged). Commit it; the last one was lost and this is the second time the work starts by rebuilding it.

**Phase 1, item 169, the card chain's refused evidence.** Four facts, each measurable with the Phase 0 tool before it is touched:

1. **A printed number that resolves nothing blocks every fallback.** `service.py:6533` guards the settled-charge, learned and merchant steps with `not _card_keys(hint)`. The comment's reason ("memory never overrides a number the document shows") is right for a number that names a card and wrong for one that names none. Count the live rows whose hint carries digits resolving to no registry card, and what the settled charge would have given them.
2. **The card learner cannot see the evidence it is allowed to learn from.** `_CARD_OBSERVATION_SOURCES` (`service.py:4885`) includes `settled_charge`, but the `card_res` handed to `registry_card_upserts_from_expense_run` (`:5207-5212`) is resolved without `settled_cards`. 21 live rows carry that source and teach nothing. Latent until a month is published; cheap to fix; say plainly that its live effect today is zero.
3. **The learned `card_key` is keyed on a company the failing row does not have.** `learning/consult.py:209-226` is an exact `(legal_entity_id, vendor_norm)` lookup with no company-less fallback, while the rows that need a card are exactly the rows with no entity. Categories got that fallback in item 115 (rule 2); field corrections did not.
4. **The two-digit ending rule misses prose.** `cards.py:166-199` against "ending with the last two digits: 38". One live row, one exact class, cheap.

Not code and larger than all four: cards 9693 and 1176 have never had a statement loaded (item 108), which is why September's OpenAI receipts cannot attribute. Name it; do not try to code around it.

**Phase 2, item 170, a correction that reaches the vendor's other spellings.** Memory recalls and captures on the raw normalized `detected_vendor` (`categorize.py:571-573`, `capture.py:350-355`), never on the registry canonical that `registry_upserts_from_expense_run` already computes (`service.py:4824-4829`). Three spellings of Anthropic therefore hold three independent rules. Keying learned rules on the canonical merchant when the registry resolves the vendor, falling back to raw, is note #80's "norms across multiple vendors" in the only form the record supports: the registry's curated alias graph, not a fuzzy key. Measure it on both months before shipping; item 117 measured a fuzzy key as 8 wrong canonicals out of 8 probes.

The alias gap on the four AI merchants is a live settings write, which is the owner's. Measure and report what filling the alias lists would move, in rows; prepare the exact `PUT /api/settings` diff; do not send it, and do not re-raise adding OpenAI or the 3x3 account table.

## Ruled out, do not re-run

- Reading the card's last-4 off the scan as free text: 2 in 5 right, invented "1234" three times, identical on re-read (item 28). The shipped path hands the extractor the registry's last-4 list and asks which it sees.
- Sender, mailbox or `submitted_by` as person, card or entity (owner ruling, item 40); the single exception is `reimburse_to` on a confirmed private expense (item 41), never generalized.
- Learning a generic tender word (`Visa`, `EC-Karte`, `Cartao de credito`) as a card alias: refused at the settings edge and inert at read time (owner ruling 2026-08-21). Per-month assignments only.
- Guessing a merchant's card for anthropic, lovable or openai: they are the only multi-card vendors, so the guess is available exactly where it is wrong (item 154).
- One-word or subset-scored merchant aliases as fuzzy keys: 8 of 8 probe vendors resolved to a wrong canonical (item 117).
- Loosening the learned-category lookup from exact descriptor match to fuzzy: cross-wires merchants.
- Applying the 24-month Zoho-derived categories as-is: relabels Slack, Supabase, Perplexity, GoDaddy and others as Marketing & Advertising; 20 of 52 accounts mapped; `N Neumann` matches `M Neumann` at 100; owner applied nothing 2026-09-19 (item 156).
- Letting a per-company learned row outrank the registry for the CATEGORY: retired by M1; only the ACCOUNT varies by company.
- Matcher tuning levers `fx_date_window_days` below 5, `fx_base_amount_match_pct` 0.005, `fx_reference_match_pct` 0.015 (the S1 optimize run), and a matching round three without a freshly labelled month.
- Reference tokens shared between a statement description and a receipt's numbers as a promoting signal, and masked card fragments inside descriptions: one such pair across nine datasets, already exact; no fragment exists (X1).
- Reading July or August expenses from `GET /api/runs/{id}`: it returns zero.

## Constraints

- **No live writes on Criss's months.** Read, predict which rows would move at the next re-match, and stop. Never offer a refresh, a reset, a re-match or any other write to July or August as a question.
- **Do not re-raise** writing OpenAI, Anthropic or Lovable into the live registry, or Dirk's 3x3 account table: "not yet, and dont re ask, i will bring this up again when the time is right." He raises it.
- The operator code is the local vault entry "Brisken recon operator code matthias"; never print it. The OpenAI key is vault "OpenAI Brisken" and bills Dirk, so keep any test set to the smallest that answers the question.
- `GET /runs/{id}/expense-report.pdf` WRITES render outcomes into the run; never fetch it live. `reconciliation-report.pdf` is read-only.
- Prove the published bundle carries the new build before driving any SPA control whose OLD behaviour is a write. On 2026-09-23 a verification click on "Save corrections to memory" fired the old immediate-save path and wrote to the live September month; it was undone with the feature being verified, but the rule stands.
- September is capped at 160 hours, real hours only. The licence is EUR 600/month from October, scoped by defect class.

## How to work

- One git worktree off `origin/main` per item, branch `client/brisken/p1-item-<N>-<slug>`. Never `git stash`. Stage explicit paths. Siblings edit the backlog all day: merge `origin/main` before pushing, never rebase a pushed branch. Ledger files (`docs/INDEX.md`, `docs/friction-register.md`, `docs/sessions/*`, checkpoint folders) go on a `docs/...` branch, never on a client branch.
- Match live data exactly, no substring card checks. The months list is `GET /api/expense-batches`; readiness is `GET /api/runs/{id}` `.summary`; sign-in lands on the new-batch screen and the months list is its own route `/months`. Windows Python cannot open `/c/...` paths: pass `C:\...` forms.
- A read-only live DB copy: `flyctl ssh console --pty=false -C "sh -c '...sqlite3 backup to /tmp...'"`, then `MSYS_NO_PATHCONV=1 flyctl ssh sftp get /tmp/<f> 'C:\...\scratchpad\<f>'` with a single-quoted Windows target, then delete the `/tmp` copies. The trailing "Error: The handle is invalid." on Windows is the terminal restore, not a failure. The auto-mode classifier refused `flyctl ssh console` once on 2026-09-21; the fallback is a direct `sftp get` of `/data/recon-web.sqlite`, a live-file copy rather than a consistent one.
- `RECON_MODULE_SRC=<tree>\...\src uv run tools/recon-match-attribution.py --live DB --learning L --files DIR --run-id ID --labels CSV` replays a hosted month with no model call; it refuses to run if `expense_recon` did not import from that tree. Labels live in the main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/`. The scorer's module path is pinned to its own repo, so scoring a branch means running that worktree's copy.
- Every backend fix: a route-level test through the caller the fix changed, then `uv run tools/regress_check.py --test "uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q tests/test_x.py" --file C:\...\src\...\y.py --replace "<wired call>" --with "<disabled>"`. Windows paths only, single-line literals, never nested inside `uv run --no-project --with pytest`. "BASELINE IS RED (no pytest summary line)" is an instrument fault, not evidence: reproduce by hand with a cp backup and a cp restore.
- Python heredocs containing triple quotes are blocked by a hook: write the script with the Write tool and run the file. Do not import a pytest fixture from another test module (CI ruff F811). Full module suite before the PR: `uv run --directory C:\...\expense-reconciliation --extra dev --extra web pytest -q` (about 4.5 min, no `-n`; it read 2,977 passed / 2 skipped on 2026-09-23 before three sibling PRs landed, so read the count rather than quoting this one).
- Commit, push and open the PR autonomously; wait for CI with `gh run list --branch <b>` filtered by head SHA, merge on green, then `flyctl deploy . -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=<the real 40-char merge SHA>` from a clean detached `origin/main` worktree (pre-authorized). Read the SHA with `git rev-parse`; never pad or invent one. After the deploy, a live API probe of the changed field and a cold real-Chrome read-back.
- In the same PR, update the backlog item's heading and status. SPA work goes out as a Lovable prompt in the reply inside a FOUR-backtick fence with EN and PT-BR strings and a "checking it landed" list, saved as `docs/lovable-<slug>-prompt.md` with a Not-applied row in `docs/PROMPT-STATUS.md`.

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
