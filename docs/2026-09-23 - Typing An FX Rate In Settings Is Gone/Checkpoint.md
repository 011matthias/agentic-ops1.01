# Checkpoint: Typing An FX Rate In Settings Is Gone

**Date:** 2026-09-23
**Status:** Shipped and deployed (PR #1210, Fly `cf54561a`). SPA half written, not pasted.

---

## Summary

Owner directive on reading the daily-poll ship: *"no more typing them in
settings you can remove that function entirely, we will only rely on these
daily rates API stuff."* Backlog item 168. Every rate the matcher uses is now
either read off the client's own statement and receipts or fetched from a
central bank. Live and verified by a read-only census: August's two FX blocks
moved from `settings` to `ecb_month`, July's eighteen now show no reference
rate until that month next re-matches on its own.

---

## What Was Done This Session

### The retirement

1. The `fx_reference_rates` settings key: `GET` drops it, `PUT` accepts it and
   reports it in `ignored`, `RunStore` deletes it from the stored row on open.
   A 400 would break the published SPA, which keeps sending the key on every
   FX-tab save until its removal prompt is applied.
2. The matcher's `configured` rung, `MatchingConfig.fx_reference_rates` and
   `fx_reference_rate()`. Order is now `statement` → `receipts` →
   `opentickers_day` → `ecb_month`.
3. The per-rate validation in the PUT, `apply_master_data`'s rate copying,
   item 132's `fx_rate_drift` advisory and its four tests.
4. The key stays PARSEABLE and is dropped (`_RETIRED_TUNABLES`): every month
   created before today has it frozen in its config and the shipped scorer
   asset carries it, so refusing it would make both unloadable.

### The addition the removal needed

5. `rematch_month` now calls `top_up_ecb_rates`, fetching only the months a
   stored table does not already carry. Without it the removal was unsafe;
   see Key Decisions.

### Two quieter reads, found by grepping the key rather than reading the diff

6. `fx_daily_rates.needed_currencies` widened the poll's currency list from
   the typed pairs, dead once the key is stripped. It follows the cards and
   the months now, which is what it actually tracked.
7. The settings route still carried a comment saying the typed rates win.

---

## Key Decisions Made

### Measure the live configs before designing the removal

- **Choice:** Read every live month's `runs.config` in-container before
  writing code, rather than inferring from the code path.
- **Rationale:** `apply_ecb_rates` ran at month creation and statement attach
  only. July 2026 was created 2026-09-07, before item 82 shipped, and never
  re-attached, so it held the typed rates and **no ECB table at all**; August
  and April hold both, January/May/June/September neither. Removing the rung
  alone would have left July's 18 cross-currency pairs with no rate anywhere,
  blanking the FX panel and the month report's USD figures. This is what put
  `top_up_ecb_rates` into the same change.

### Merge the two Lovable prompts into one

- **Choice:** Rewrite `docs/lovable-fx-daily-rates-prompt.md` wholesale rather
  than hand over two prompts.
- **Rationale:** The original was never pasted (PROMPT-STATUS: "Written
  2026-09-23, not pasted") and told Lovable to *keep* the typed editor the
  owner had just retired. Two prompts would have had the owner paste a
  contradiction.

### Take the band change rather than special-case it

- **Choice:** Let a typed rate's 3% clean band give way to a central-bank
  rate's 2% (`fx_ecb_match_pct`).
- **Rationale:** Item 90 measured that trade as a net gain (July 32 right
  against 30) and the owner took it. July's SUPERMEC SAO JOSE at +2.93% now
  defers to judgment instead of auto-pairing; it is pinned in
  `test_fx_breakdown.py` so the change is visible rather than incidental.

---

## What Did NOT Work (and why)

- **Trusting the green suite as proof the fix was wired:** 3045 tests passed
  with `top_up_ecb_rates` covered only as a helper. `regress_check` cut its
  call in `rematch_month` and every test stayed green, so the suite could not
  tell a shipped fix from an unwired one.
- **The re-read and month-creation paths as provers:** both call
  `apply_ecb_rates` themselves (`read_statement_upload`, `create_expense_batch`),
  so both stay green with the wire cut. Adding a receipt is the only re-match
  path that fetches nothing of its own.
- **Driving the stored-row migration through the API:** the settings GET
  strips the retired key whether or not the row still holds it, so an
  API-level test reports success on an unwired migration. That difference is
  the whole claim (gone, not hidden), so the test reads
  `RunStore.get_settings`, which returns the row as stored.
- **`regress_check` run from the primary clone:** it operated on a tree
  without the change and returned a green baseline of 21 passed. Only the
  "literal matched 0 times" error exposed it; had the line existed in both
  trees the run would have reported a meaningless pass.
- **`uv run ruff` inside the module venv:** ruff is not installed there
  ("program not found"), and the `$?` read after a pipe reported 0 anyway.
  `uvx ruff check --select E9,F src tests` is the working form.
- **`recon_accuracy_check.py ci` with no arguments:** argparse requires
  `--fixtures` and `--expected`; the canonical invocation is in
  `.github/workflows/expense-recon-tests.yml`.
- **flyctl's own config discovery:** "no access token available" in both Bash
  and PowerShell although `~/.fly/config.yml` holds a 665-char token. Passing
  it as `FLY_API_TOKEN` to the child process deploys normally.
- **The SPA consumer drive:** `agent-browser` on the default session hung past
  300s on `open`; the retry with a dedicated Chrome was declined by the user,
  so no browser drive was run for this deploy. Verification is API-level only
  (see Current Status).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `matching/deterministic.py` | edit | Rung ladder without `configured`; `_RETIRED_TUNABLES` |
| `web/store.py` | edit | `RETIRED_SETTINGS_KEYS`, `_drop_retired_settings` on open |
| `web/service.py` | edit | `top_up_ecb_rates` + its call in `rematch_month`; drift advisory deleted |
| `web/app.py` | edit | Retired key exempted from the 400, stripped on GET; stale comment |
| `web/fx_daily_rates.py` | edit | Poll's currency list stops reading the retired key |
| `output/single_currency.py` | edit | Typed-rate labels removed |
| 15 test modules | edit | Retirement pinned; 2 new caller-level tests |
| `docs/lovable-fx-daily-rates-prompt.md` | rewrite | One prompt: editor out, read-only panel in |
| `docs/api-contract.md`, `docs/PROMPT-STATUS.md` | edit | Contract section; ledger row refreshed |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edit | Item 168 + Shipped row 116 |

---

## Current Status

Live on `cf54561a`, verified read-only before and after:

| | before | after |
|---|---|---|
| July (112 rows) | 18 FX blocks `settings` | no reference rate |
| August (114 rows) | 2 FX blocks `settings` | 2 `ecb_month` |
| match rate | 27.7 / 7.9 | 27.7 / 7.9 (unchanged) |

`GET /api/settings` no longer carries `fx_reference_rates`; the poll is
healthy at 46 days through 2026-09-23, six pairs. Nothing was re-matched on
Criss's months, so July's panels stay blank until it re-matches on its own,
which is when `top_up_ecb_rates` gives it a table.

**Verification is API-level only.** The deploy's consumer gate is NOT closed:
no browser drive was run. The SPA half is also unpasted, so the FX tab still
renders the typed-rate editor and August's panel shows the raw `ecb_month`
string rather than a label.

ops: platform unknown plan, last assessed unknown. comms-log 15 days stale.

---

## Next Steps

1. Paste the Lovable prompt (in the session reply, and
   `docs/lovable-fx-daily-rates-prompt.md`), publish, then drive the SPA cold
   and move the PROMPT-STATUS row to Applied.
2. Drive the workbench once to close this deploy's consumer gate, or accept
   it as open and say so.
3. Itemize feedback notes #73, #74, #75, #77, #82 from the backlog's Open
   section.
4. Refresh or delete the stale `p2-product-decks.md` (62d) and
   `p2-targeting.md` (63d).
5. Carried: Criss's 2 date-guard exceptions and 3 account refusals; confirm
   the production Zoho tier before native-currency posting.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 168)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-fx-daily-rates-prompt.md`

### Open Questions
- Should a daily rate outrank a receipts-derived median? Unmeasured: no
  labelled bundle carries daily rates, so the rung order keeps item 82's
  evidence for now.
- Why did flyctl stop reading its own config? The workaround holds but the
  cause is unknown, and a token that cannot be discovered may also be near
  expiry.

### Working Notes
- The census script is `scratchpad/fx_census.py` (read-only; login via
  `EXPENSE_RECON_OPERATOR_CODE` in the brisken `.env`). Before/after JSON at
  `census_before_168.json` / `census_after_168.json`.
- Live run ids: July `50622baec444`, August `074a7b8905d7`, September
  `51a22ad72864`.
- OpenTickers genuinely has no EUR→USD/BRL history before ~2026-07-22, probed
  directly. The backfill is not truncating.

### Reference Materials
- PR #1210; merge `cf54561a`. Phase 1 was PR #1203, Fly `131fd5d2`.

---

## How to Continue

The backend is done and live. The remaining work is the screen: paste the
prompt, publish, drive it cold, then close the PROMPT-STATUS row.

---

## Strategic Feedback

### What Worked Well This Session

- Reading the live `runs.config` before designing the removal. It refuted the
  inference the change was about to rest on and put `top_up_ecb_rates` into
  the same PR instead of into a follow-up bug report from Criss.
- Grepping the retired key across `src` and `tests` after the first suite,
  which found two reads the diff review had missed.

### Suggestions

- Grep for the symbol being removed **before** launching a seven-minute
  suite, not after. Both failures in the first run (`test_fx_ladder.py`, the
  unused `Decimal`) were findable in five seconds, and the suite cycle cost
  more than the rest of the fix.

### System Health

- `tools/regress_check.py` earned its keep: it caught two load-bearing wires
  with no caller-level test, one of which the entire 3045-test suite could
  not distinguish from unwired code. This is the 2026-08-24 fix-bites row's
  structural fix holding.
- The same tool silently accepts a `--file` outside the current worktree and
  reports a green baseline against a tree that lacks the change. Worth a
  guard: refuse when the mutation literal is absent AND the file is not under
  the repo the test command runs in.
- Autonomy: 2 human interventions (checkpoint authorization; the browser
  drive declined).
