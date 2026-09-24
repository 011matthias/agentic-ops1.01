# Mini-Checkpoint: Brisken Recon Private Card List Gate

**Date:** 2026-09-25
**Status:** Nothing built. The private-card-list item (cases 2 + 4 of the card-attribution map) is unblocked and its continuation prompt is below, ready to paste.
**Type:** mini

---

## Summary

The owner's private-card-list build prompt was run and stopped at its own precondition: the card-type item it builds on was still uncommitted in a sibling worktree. By the end of the session all three changes it rests on had merged and gone live (items 198, 199 and case 6 / item 203), and the prompt was rewritten so step 4 of the decision order reuses case 6's `positive_non_brisken_evidence` instead of writing a second classifier.

## What Was Done

- Precondition check, 2026-09-24 23:29 CEST: no card-type classifier on origin/main (`69de469b`); sibling worktree `agentic-ops1-cardtype` held it uncommitted. Stopped as the prompt ordered; removed this session's clean worktree `agentic-ops1-privcards` and branch `client/brisken/p1-private-card-list` so the prompt's "cut fresh" commands work on re-run.
- Item 175's Lovable prompt (`docs/lovable-private-reimburse-prompt.md`) re-checked: PROMPT-STATUS row says "Applied by bundle, 2026-09-24; not driven", and a transitive crawl of the published SPA (43 files) confirmed it: `expx.reimburse.edit`, `expx.private.editTitle`, "Receipts by email" present, "From email" 0 hits, controls `expx.reimburse.undo` / `expx.privateCard.mark` / `ready_to_post` present. Handed the text to the owner marked do-not-paste.
- Found case 6 in flight (`agentic-ops1-evidence`, commit `4db10da9`) adding `cards.positive_non_brisken_evidence(hint, cards) -> reason | None` and switching `resolve_batch_row_cards`'s `suggested_private` to it, which rewrites steps 4 and 7 of the owner's decision order. Revised the continuation prompt: step 3 (the list) sits in front of that function; out-of-scope drops case 6 and the two-digit wording miss; the precondition names all three dependencies.
- Confirmed at ~00:20 CEST: #1334 (`59354b9b`), #1335 (`a8c1fafb`) and #1340 (`f744680b`, case 6 = item 203) all merged and ancestors of the live commit `d059856a`; `positive_non_brisken_evidence` at `cards.py:346` on main, called at `service.py:6791`. No sibling worktree holds uncommitted `cards.py` / `service.py` edits.

## What Did NOT Work (and why)

- **Reading a prompt's paste status off the backlog heading and the prompt doc's header:** both still say "not pasted" for item 175, while PROMPT-STATUS (and the live bundle) say applied. The first closing message told the owner it was pending. PROMPT-STATUS plus a bundle crawl is the instrument; the doc header and backlog heading are corrected in the private-card-list PR.
- **The first revised prompt (written after #1334 merged):** stale within about fifteen minutes. It still called step 4 "item 41, unchanged" and step 7 "case 6 is next", while a sibling had already committed case 6. Check `git worktree list` for in-flight edits to the same files before writing a prompt's decision logic, not only origin/main.

## Current Status

Precondition met; the live build `d059856a` carries items 198, 199 and 203. origin/main is two code merges ahead of live (#1355 item 195 statement re-read keeps its company; #1356 items 201/205 GL account names), neither on the private path. Item 175's stale "not pasted" labels remain until the build PR. The private-card list starts empty; nobody here knows who owns 3281.

## Next Steps

1. Paste the continuation prompt below into a fresh session; it builds the list, the strip route, the Lovable prompt, deploys and cold-drives.
2. Owner / Criss: fill the private-card list once it ships (3281 first); paste the Lovable prompt the build produces.
3. Drive item 175's "Change who is reimbursed" dialog on September's private row (published, never opened).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cards.py` (`positive_non_brisken_evidence` ~346, `registry_card_types` ~285, `masked_short_ending` ~470)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`resolve_batch_row_cards`, suggestion at ~6791)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (item 175 row)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_private_needs_evidence.py` (golden rows for the refactor)

---

## Continuation prompt

Same as the prompt handed in chat, with "Where it stands" and precondition item 3 refreshed at checkpoint time (all three dependencies now merged and live; case 6 is PR #1340 / item 203).

````
/comd_resume brisken

# Brisken p1 expense-recon: a private-card list on top of the case-6 decision order (cases 2 + 4 of the card-attribution map)

## Where it stands

Nothing of this item is built. Two earlier runs (2026-09-24 23:29 and 2026-09-25 ~00:05 CEST) stopped before building because the code it sits on was still moving. By ~00:20 CEST on 2026-09-25 all three dependencies were merged and in the live build (`/healthz` `server.commit` `d059856a`):
- **Item 198** (card type is not a private signal): PR #1334, `59354b9b`.
- **Item 199** (a two-digit card ending printed in other words names its card): PR #1335, `a8c1fafb`.
- **Case 6 = item 203** (private is suggested only on positive evidence): PR #1340, `f744680b`, branch `client/brisken/p1-private-needs-evidence`. Adds `cards.positive_non_brisken_evidence(hint, cards) -> str | None` (reasons `number`, `ending`, `cash`, `network`, `kind`, `issuer`; conflict means wait), `payment_words`, `CASH_WORDS`, `NON_BRISKEN_ISSUERS`, `NEUTRAL_PAYMENT_NAMES`, `registry_issuers`; `service.resolve_batch_row_cards` computes `suggested_private` from `positive_non_brisken_evidence(hint, cards) is not None`. Supersedes item 41's trigger.

origin/main was two code merges ahead of live at that time (#1355 item 195, #1356 items 201/205), neither on the private path. Item numbers up to 205 are taken; merge main before claiming yours. The worktree `agentic-ops1-privcards` and branch `client/brisken/p1-private-card-list` do not exist, so the "cut fresh" commands below work as written.

Item 175's Lovable prompt (`docs/lovable-private-reimburse-prompt.md`) IS applied: PROMPT-STATUS row "Applied by bundle, 2026-09-24; not driven", re-confirmed by a transitive crawl of the published SPA at ~23:40 CEST (43 files; `expx.reimburse.edit`, `expx.private.editTitle`, "Receipts by email" present; "From email" 0 hits; controls `expx.reimburse.undo`, `expx.privateCard.mark`, `ready_to_post` present). Two labels still say otherwise and are corrected in THIS item's PR: the prompt doc's header ("NOT PASTED") and backlog item 175's heading ("not pasted").

## Owner direction, 2026-09-24 (verbatim)

"fuze items 2 and 4 together, fix a) by setting up private card memory/registry and b) any credit card types or numbers that dont belong to brisken will then be suggested as private expenses - making item 2 the alternative to item 1 (after the changes in the prompt above)"

Case map (2026-09-24):
- **Case 1:** the receipt prints a Brisken card number, or (since item 198) a card type Brisken has ("VISA CREDIT"). A type waits for the statement or vendor memory and is never labelled private.
- **Case 2:** a card number that is not Brisken's. Live: 3281, 2598, 1340, 4167, 3976, `...2544`, `0501-1462-9129`.
- **Case 4:** a card type Brisken does not have (girocard, EC-Karte, DEBIT).
- **Gap (a):** a personal card that recurs (3281) has to be confirmed private by hand every month; nothing records "3281 is Dirk's private card".

## Precondition

All three must be merged on origin/main AND contained in the live build (`git merge-base --is-ancestor <commit> <healthz server.commit>`):
1. Item 198, PR #1334 (`59354b9b`): `registry_card_types`, `names_registry_card_type` in `cards.py`.
2. Item 199, PR #1335 (`a8c1fafb`): the two-digit ending read in other words (`cards.masked_short_ending` and its tests).
3. Case 6 = item 203, PR #1340 (`f744680b`): `cards.positive_non_brisken_evidence`, wired into `service.resolve_batch_row_cards`.

If any has been reverted or is no longer in the live build, stop and report which one; do not re-implement it here. The "before" census must be taken on a live build that carries all three.

## What to build

### 1. One decision order, with the private-card list as its new step 3

Case 6 already made "is this positive evidence of a non-Brisken card" ONE function, `positive_non_brisken_evidence`. Do NOT write a second classifier. Put the private-card lookup in `cards.py` beside it, e.g. `private_card_for(hint, cards, private_cards) -> PrivateCard | None`, or a thin `classify_payment_evidence(hint, cards, private_cards)` that consults the list and then delegates to `positive_non_brisken_evidence`. Whichever you pick, `service.resolve_batch_row_cards` reaches both the private-card answer and the suggestion through ONE entry point, not a second set of scattered conditions.

Row-level decisions still outrank everything exactly as today: a per-row card pick, a row Criss confirmed private, a settled-outside disposition. Below them, first match wins:

1. A printed number that names a Brisken card → that card (unchanged).
2. A Brisken card type with no number → no private label; the statement, remembered card and merchant card decide (item 198, unchanged).
3. A printed number on the PRIVATE-CARD LIST → private, reimburse the listed person (NEW, section 2).
4. `positive_non_brisken_evidence` returns a reason → suggested private (case 6, unchanged).
5-7. Everything else exactly as case 6 left it: not a card, nothing printed, and any phrase with no positive evidence wait for the statement charge, vendor memory and Criss's assignment.

A number always outranks a type word in the same hint: "DEBIT-MASTERCARD 3281" is decided by 3281, so step 3 is read before step 4's `number` reason. A two-digit ending is never looked up on the list (section 2 refuses two-digit entries); a two-digit ending that two Brisken cards share (76: 3876/1176; 13: 0113/6013) stays unguessed and is NOT private.

For every row not on the private-card list this is a pure refactor. Measure all seven months before and after: no row may change (the list starts empty).

### 2. The private-card list

**Where it lives.**
- New top-level settings key `private_cards`: `{ "<last 4 digits>": {"person": str, "note": str, "active": bool} }`.
- Whole-key replace on `PUT /api/settings`, like `cards` and `merchants`, validated by a new `normalize_private_cards_setting`.
- It must be a SEPARATE key, not a flag on `settings["cards"]`:
  - every company-card consumer iterates `cards` (matcher card scope, coverage rows, the months strip, the Cards overview, statement linking, `/api/cards`);
  - the SPA's Cards editor replaces that whole map on save, so a new field there would be erased by the published app.
- `store.set_settings` merges top-level keys shallowly, so a new key survives saves of the others. Prove it with a test that PUTs `cards` after `private_cards` exist.

**Validation** (400 with a `code`):
- Digits: the last 4 of a 3+ digit run, read with the same `_card_keys` extraction the matcher uses. Store 4 digits and keep a leading zero.
- `person` is required and trimmed.
- Digits that any ACTIVE company card carries are refused (`private_card_is_company_card`). A company-card PUT that would add digits already on the private list is refused the same way. This is the "company card OR private card, never both" rule the per-row routes already enforce.
- A two-digit ending is never accepted: money owed to a person needs the full last 4.

**Read it live.** Read the list from settings at view time, the way item 169 made the remembered card live and M2 made the merchant registry live. Never snapshot it into the batch. An entry then reaches every existing month at once, with no refresh and no write to any month.

**What a matching row reads:**

| Field | Value |
|---|---|
| `private` | `true` |
| `reimburse_to` | the listed person |
| `person_source` | `"private"` |
| `suggested_private` | `false` |
| `can_mark_private` | `false` |
| `private_source` (NEW, parallel) | `"row"` when Criss confirmed it, `"private_card_list"` for this path, `""` otherwise |

Document `private_source` in `docs/api-contract.md` and pin it in `tests/test_view_contract.py`.

**It must behave on every surface exactly like a row Criss confirmed private:** the month report's "Reimbursements owed" section, the CSV (`(private expense)`, `Private ({person})`), `n_private`, the boxes, and the card strip (it leaves `unresolved_hints`, because the card is no longer unknown).

Enumerate every consumer of `private` / `reimburse_to` (`rg -n "reimburse_to|\"private\"" src`) and confirm each reads the resolution rather than `field_overrides` directly. One that reads overrides directly is a bug to fix in this PR. If that consumer lives in `matching/`, do not edit it: report it in the PR and in the backlog item.

**Row exits** (both must work and be tested):
- **Undo:** `POST .../private` with `{"private": false}` on a list-derived row stores an explicit per-row opt-out, so the list no longer applies to that row. Today's clear-both behaviour would be undone by the list immediately.
- **Company-card pick:** a per-row `card_key` wins over a list-derived private and is NOT refused with `private_card`. That refusal stays for rows Criss confirmed herself.

**Guard:** a printed number on the list never takes a card from the settled charge, remembered card or merchant card. Today's printed-number guard already blocks those for any printed number; keep it and pin it with a test.

### 3. Two ways onto the list, both explicit (no silent learning)

- **Settings:** a new Settings panel edits the list (Lovable, section 4).
- **The unknown-card strip:** `POST /api/expense-batches/{id}/cards` assignments accept `{"hint": ..., "private_to": "<person>"}` in place of `"card"`. Exactly one of the two is allowed; 400 otherwise.
  - With `"learn": false` the assignment applies to this month only. Record it in the batch config beside `expense.card_hints`.
  - With `"learn": true` (the existing "Remember for future months" switch) it also writes the hint's last 4 digits into `settings["private_cards"]`.
  - When learning, refuse `private_to` on a hint with no digits (a generic word names no card) and on digits a company card carries.
  - The response says what was written and where, in the item-163 shape if card learning has one.
- **Confirming private on a single row does NOT write the list.** The owner ruled on 2026-09-24 that only corrections are memorized, and a per-row confirmation is a decision about that row. The strip's remember switch is the explicit "this card is X's" instruction.
- The 2026-08-22 ruling "personal tenders are never learned" was about tender WORDS. A card number on the list is an explicit owner-directed registry under this 2026-09-24 direction. Record that supersession in the backlog item.

### 4. SPA half: write the Lovable prompt, do not skip it

Without it nobody can add an entry, so the backend alone moves nothing. Write `docs/lovable-private-card-list-prompt.md` and add a Not-applied row in `docs/PROMPT-STATUS.md`. It covers:

- **Settings:** a "Private cards" panel (last 4 digits, reimburse to, note, active; add, edit, remove) saving `PUT /api/settings {"private_cards": {...}}` as a whole-key replace, and showing the 400 codes in plain words.
- **The unknown-card strip:** on a "Cards by number" group whose digits are not a Brisken card, the Assign dropdown gains "Private card of..." with a person input prefilled from the rows' `reimburse_to_prefill`. It sends `private_to`; the Remember switch keeps its meaning.
- **The row:** when `private_source` is `"private_card_list"`, the private badge adds "(from the private card list)". Its undo control calls the existing route.

Also:
- EN and PT-BR strings, no em-dashes, exact JSON shapes, a do-not-change list, and checks.
- Item 175 (`docs/lovable-private-reimburse-prompt.md`) is APPLIED, so the live private badge already carries three controls: the badge `expx.private.badge`, the "Change who is reimbursed" button `expx.reimburse.edit` (opens the shared private dialog, titled `expx.private.editTitle`), and the undo `expx.reimburse.undo`. On `suggested_private` rows the "Paid with a private card" option already sits FIRST in the card picker. Write this prompt against that live shape, anchored on the current bundle (crawl every `/assets/*.js` transitively and assert control fields before believing any absence), and say what the edit button does on a list-derived row (it edits the row, not the list).
- If case 6 shipped its own Lovable prompt (check PROMPT-STATUS), read it first and write this one to work in either paste order.
- Check the prompt's header against the live SPA's `API_BASE` (`https://api.expenses.brisken.com`).
- Hand the whole prompt back in the reply in a FOUR-backtick fence labelled "Paste into Lovable:".

## Live facts (read-only 2026-09-24; re-measure on the live build that carries items 198, 199 and case 6)

- **Case 2 rows on 2026-09-24**, all `suggested_private: true`:
  - April: `VISA ***2598`; LANCHERIA ONLINE `COMPRA CREDITO VISA ********1340`; MEGA CENTER `VISA CREDIT xxxxxxxxxxxx4167`; ERICK SPORTS `Mastercard xxxx.xxxx.xxxx.78` (two digits, no Brisken card ends in 78)
  - June: Supermercado Fenix `CARTAO: XXXXXXXXXXXX3976`
  - July: Google LLC `...2544` and `0501-1462-9129`
  - September: DB Fernverkehr `DEBIT-MASTERCARD ***** ***** ***** 3281`
- **Case 4 rows:** girocard (September, Katja Harms), EC-Karte (August, Moghul Mahal), DEBIT (July, Credit Agricole).
- Case 6 changes which rows are suggested private (phrases with no positive evidence stop being suggested), so these lists are leads, not the baseline. The baseline is your own census on the current live build.
- **Nobody here knows who owns 3281** or any other number. Do not seed the list: it starts EMPTY, and Criss or the owner fills it.
- **June's Fenix `3976` is probably an OCR slip of 3876** (Fenix is only ever paid on 3876). Build nothing for it, and do not use it as a stand-in for a real private card anywhere.
- **Google's two numbers may not be card numbers at all.** Under the owner's rule they stay suggested private; a per-row card pick already corrects them. Out of scope.
- **Expected live effect on deploy: ZERO rows move** (the list is empty), and `n_suggested_private` is identical per month before and after. The new fields appear: `private_source` on rows, `private_cards: {}` in settings.

## Out of scope

Cash wording; vendor memory before sign-off; the matcher (`matching/`); numbers that are not cards; a person directory (persons stay free text, as `reimburse_to` is today); anything case 6 or item 199 decided (do not re-tune their vocabularies here).

## How to work

**Worktree, cut fresh:**
- `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin`
- `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-private-card-list C:\Users\neuma_p1qrsic\Repo\agentic-ops1-privcards origin/main`
- Never edit, commit or stash in the main checkout: several sibling sessions sit on it. Never `git stash` anywhere.
- A hook refuses `cd X && ...`; use `git -C`, `uv run --directory` and absolute paths.

**Shared files:**
- Sibling sessions may edit `cards.py`, `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog and the status file.
- Append at the END of the relevant block; never renumber or reflow.
- Before the first push, `git rebase origin/main` is fine (commit first). After any push, only `git merge origin/main`: never rebase, never force-push.
- Merge main before claiming a backlog item number or a Shipped row number, then take the next free one.

**Live reads only:**
- API `https://brisken-expense-recon.fly.dev`: `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it).
- Months list: `GET /api/expense-batches` (key `batch_id`). April `0603bb0e6f38`, May `86929f2a909a`, June `a5f97a85b1d0`, July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`, January `4ceaeb461386`.
- No writes to Criss's months or to settings. That includes no TEST private card in live settings: the list is read live by every month. Do not offer any such write.
- Never fetch `GET /runs/{id}/expense-report.pdf` live.

**Tests** (route-level through the FastAPI app). Cover:
- a listed 3281 turns a `DEBIT-MASTERCARD ... 3281` row private, with the person and `private_source`, and the row reaches the report's reimbursements section and the CSV;
- an inactive entry falls back to case 6's suggestion;
- both collision refusals;
- `private_to` with learn true (writes settings) and learn false (batch only);
- both row exits;
- the shallow-merge survival;
- a golden table proving the refactor leaves every other branch of the order unchanged (reuse case 6's `tests/test_private_needs_evidence.py` cases as the golden rows where they fit).

**Regress check:** one `uv run tools/regress_check.py --test "<cmd>" --cwd <module dir> --file <src> --replace "<wired>" --with "<disabled>"` each on the resolver wiring and the strip route, watched going red. Run it from the worktree that holds the change, with WINDOWS paths in `--test`. On a doubtful "RED (no pytest summary line)", mutate by hand with a `cp` backup; restore with `cp`, never `git checkout --`.

**Suite:** `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (7-12 minutes). Background it and register `uv run tools/bg_watch.py watch --label "recon suite" --eta 12`. Heredocs with triple quotes are blocked: write scripts with the Write tool.

**Ruff:** `uv run --no-project --with ruff ruff check src tests` from the module dir.

**Docs, same PR:**
- `docs/api-contract.md`: a section "Whose money paid: the decision order" stating the steps (with case 6's `positive_non_brisken_evidence` as step 4), the list, the exits and the supersessions; if case 6 already wrote a decision-order section, extend it rather than adding a second;
- `status/p1-improvement-backlog.md`: a new item plus a Shipped row; also correct item 175's heading from "not pasted" to applied (by bundle, 2026-09-24, not driven);
- `docs/lovable-private-reimburse-prompt.md`: replace the "NOT PASTED" header line with the applied status, matching its PROMPT-STATUS row;
- `status/p1-expense-reconciliation.md`: one row.

**Ship:** commit with explicit pathspecs, push, then `gh pr create --repo 011matthias/agentic-ops1.01`. The body carries the suite count before and after, the regress lines and the per-month before/after table. Wait for CI in a background loop (`gh pr checks <n> --json name,bucket`); `expense-recon-tests.yml` runs the module suite. Merge on green with `gh pr merge --squash --delete-branch`.

**Deploy** (pre-authorized):
1. Check `flyctl releases -a brisken-expense-recon`: a sibling's deploy may already carry your commit.
2. If not, `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-privcards origin/main` and confirm your merge in `git log -1` there.
3. `M=C:/Users/neuma_p1qrsic/Repo/agentic-ops1-deploy-privcards/workspace/clients/brisken/automations/expense-reconciliation`, then `MW=$(cygpath -w "$M")` and `flyctl deploy "$MW" --config "$MW\fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)"` (flyctl needs Windows paths; do NOT prefix MSYS_NO_PATHCONV=1 on the path args). If flyctl says "no access token available", pass `FLY_API_TOKEN` read from `~/.fly/config.yml`.
4. Prove it with `/healthz` `server.commit`, then remove that worktree.

**Verify behaviour, not the deploy:**
- Re-run the read-only census over all seven months: `suggested_private` and `n_suggested_private` are identical per row and per month, every row carries `private_source`, and `GET /api/settings` carries `private_cards`.
- Then a cold browser read-back, using either:
  - headless Playwright `channel="chrome"`: click `input#code`, `keyboard.type` the code, press the Log in button via JS `click()`, wait for localStorage `erc-token`, dismiss "Leave feedback anywhere" with JS `click()`;
  - or `agent-browser --session recon-privcards` (never the default session).
- Open September's Expenses view and assert:
  - the Luigi Buchholz row still reads "Private card: reimburse Dirk Neumann";
  - the DB Fernverkehr 3281 row still shows "Suggested private expense"; assign this card to dirk just as a placeholder for input inside this function
  - the only non-GET request was the login.
- Name a scripted drive as such in the closing text.

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
