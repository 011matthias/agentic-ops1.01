# Mini-Checkpoint: FX Consumer Gate Closed

**Date:** 2026-09-23
**Status:** Item 168 shipped, deployed `cf54561a`, and now driven in a browser. Gate closed.
**Type:** mini

---

## Summary

The earlier checkpoint for item 168 left the deploy's consumer gate open: no
browser had rendered the changed field. It is now driven and closed. The
August FX rows render the fetched ECB rate `1.15931` on screen, with no
retired `· Settings` label and no fallback string in its place.

## What Was Done

- Drove the live SPA at `expenses.brisken.com/runs/074a7b8905d7` and read page
  state back: `214.20 EUR x 1.15931 = 248.32 USD · difference -1.00 USD
  (-0.40%)` and `32.00 EUR x 1.15931 = 37.10 USD · difference +0.38 USD
  (+1.03%)`. Both are the rows the census showed moving to `ecb_month`.
- Asserted the negatives too: `· Settings` and `Configurações` absent, and
  none of `Arriving` / `Unknown` / `undefined` / `NaN` / `[object Object]`
  present. The render is the new value, not a fallback wearing its place.
- Added two tooling facts to memory: flyctl's lost token discovery
  (`project_brisken_expense_recon_fly_hosting`) and `regress_check`'s
  CWD-relative `--file` (`reference_repo_tooling_gotchas`).

## What Did NOT Work (and why)

- **`agent-browser`, three ways:** default session hung past 300s on `open`;
  a dedicated `--executable-path` Chrome hung past 180s; `--cdp 9333` against
  an already-running cold Chrome hung past 120s. All three were moved to the
  background having asserted nothing.
- **Raw CDP with the default Origin header:** Chrome answers `403 Forbidden,
  Rejected an incoming WebSocket connection from the http://127.0.0.1:9333
  origin`. `websocket.create_connection(..., suppress_origin=True)` connects.
- **Reading the FX source string from the summary line:** `ecb_month` is not
  in the collapsed row text; it sits behind "Show FX details". The rendered
  rate is the assertion that carries, and it matches the API exactly.
- **`python -c` with a `.replace('/', '\\')` on a Windows path:** the escape
  collapses in the shell and dies on an unterminated string literal. Use a
  heredoc or a script file.

## Current Status

Backend live on `cf54561a` and verified end to end: API census before and
after, plus a browser drive of the changed field. PRs #1210 (retirement) and
#1212 (checkpoint) merged; origin/main has since moved to `f3ecd6bc`.

The SPA half is still unpasted, so the Settings FX tab still renders the
typed-rate editor. That editor now saves nothing: the backend reports the key
in `ignored`. ops: platform unknown plan, last assessed unknown. comms-log 15
days stale.

## Next Steps

1. Paste the rewritten `docs/lovable-fx-daily-rates-prompt.md` into Lovable,
   publish, drive cold, move the PROMPT-STATUS row to Applied.
2. Itemize feedback notes #73, #74, #75, #77, #82.
3. Refresh or delete `p2-product-decks.md` (62d) and `p2-targeting.md` (63d).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-fx-daily-rates-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 168)
- `docs/2026-09-23 - Typing An FX Rate In Settings Is Gone/Checkpoint.md`
