# Mini-Checkpoint: Brisken P1 9693 Load And Item 197 FX Rung

**Date:** 2026-09-24
**Status:** 9693 loaded into August and September; item 197 live at Fly `69de469b`; GL drive blocked on the Lovable paste
**Type:** mini

---

## Summary
Gate A (OpenAI key) opened and Gate B (GL prompt published) stayed closed. The
ordered 9693 load exposed item 197: one printed FX line from a statement priced
every pair in its month. The owner picked the fix, which shipped and deployed
before September's cycle went in.

## What Was Done
- Gates, read-only. A: a body-only mail went through vision at 18:02 UTC, after the 16:21 hold. B: the bundle audit's five controls were all present and all five GL markers absent, in both SPA `main` (b39c8bc) and the live bundle.
- Held mail `20260924T162158-0f4f64aa` (OpenAI USD 10.00, 9693) went into September via `render-ingest`. `n_held` is 0 and every charge row is unchanged.
- Snapshots `vs_9xqGKXeR13lsL9JpXVmwbP`, `vs_JVnq4D86XGYSm0DD2nqvo6` and `vs_eg81MkJmYKvuxK8NKNzPkk`, one before each write.
- August attach (`20260804`): +21 rows, all Cloud Services. It also moved 2838 ANTHROPIC* CLAUDE SUB 104.95 / 108.53 from reconciled to review, which diagnosed as item 197.
- PR #1328: backlog 195 (reread entity re-stamp, code-traced), 196 (attach and intake fail closed on an exhausted key) and 197.
- Owner pick via question: fix 197 first. PR #1329: `_reference_rate_for` order is now daily -> statement/receipts median -> ECB. Tests: `test_fx_rung_item_197.py` goes through `match_month`, and the rung test was rewritten. Restoring the old order by hand turned both red; the file was restored to its sha. Suite 3312 passed / 2 skipped, CI match-accuracy gate green. Deployed `69de469b`, confirmed on `/healthz`.
- September attach (`20260904`): +32 rows, all Cloud Services, no advisory. Five pairs, exactly as predicted from a local parse: SendGrid 89.95, Anthropic 204.09, Afi 66.00, and August's OpenAI 80.04 / 80.12 via the adjacent borrow. August moved only `n_receipts_need_charge` 12 -> 10.
- Cold SPA drive: the 9693 card sections read 19 / USD 6,340.60 (Aug) and 25 / USD 8,178.79 (Sep), equal to the API to the cent. The only non-GET request was the login. Recorded in PR #1332.

## What Did NOT Work (and why)
- **Brief step "re-ingest each held_body_only entry":** `POST /api/inbound/{archive}/re-ingest` only takes attachments and refuses body-only mail (`mail_no_attachment`). `render-ingest` is the route for it.
- **Diagnosing the August move via `flyctl ssh` sqlite and `GET /api/operator/state`:** both were refused by the session's permission classifier (production reads). The cause was found offline instead: a local PDF parse plus the rung code.
- **First hypothesis (the rate-table change missed the judgment cache):** wrong. The FX judgment cache key carries charge/receipt content, card and payment mode, and no rate.
- **SPA drive needles "AFI TECHNOLOGIES" / "SAP SE WALLDORF":** failed on a correct page. Reconciled rows are hidden, and each card renders as a collapsed section. Assert the section headline (count + total) against the API instead.
- **Gate sign-in by Enter / JS click:** typing before hydration leaves Log in disabled. Type until the button enables, then use a real click.

## Current Status
Both 9693 cycles are loaded and verified. Item 197 is live. August's two Anthropic rows return to reconciled at the month's next natural re-match (no agent re-match: Criss's month). The GL prompt `docs/lovable-gl-accounts-prompt.md` is still not pasted, so the GL drive has not run. The review copy `CoA BRISKEN - 6 accounts for Dirk to decide 260924.xlsx` is still open in Excel (`~$` lock present, sha `eed95ea3...` unchanged), so it was not deleted.

## Next Steps
1. Gate B: when the owner has pasted and published the GL prompt, re-run the bundle audit with the five markers, then do the brief's step 2 (cold July, the `TEST - GL drive` batch, section-6 rows 2-6 in EN and PT, purge, mark applied).
2. Item 196: owner decision, whether an attach lands its deterministic rows when the model is down or keeps failing whole.
3. Item 195: write the red test first (PDF attached with no account id, reread, assert entity).
4. Small leftovers from items 196/197: the sticky `error` on rendered entries, a dead attach job leaving its file (`--2.pdf`), the overlap advisory saying "same account" for two cards, and `card_ending` empty on rendered OpenAI bodies.
5. Delete the review xlsx once the `~$` lock is gone and the sha still matches.
6. 0113 statement: Dirk's export (owner side). 8311/6013 stay dormant.

## Files to Read First
- workspace/clients/brisken/status/p1-expense-reconciliation.md (top paragraph)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 195-197)
- workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-gl-accounts-prompt.md

## Continuation prompt

````
resume brisken

Continue Brisken p1 expense-recon. Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake and the hard stop
- `git fetch origin` first; shared clone with live siblings; work in a worktree off origin/main.
- Live Fly = `69de469b` (PR #1329, item 197). Module suite 3312 passed / 2 skipped there (no `-n`).
- Gate B (GL prompt published): the Lovable repo `main` AND the live bundle both carry `category_vocabulary`, `accountsFor`, `category_refused`, `gl.refusal.`, `gl.picker.search`. `tools/lovable-bundle-audit.py` hardcodes an older NEW set: run a scratch copy with these five swapped in (controls untouched). Repo-only = pasted, not published = closed.
- **HARD STOP:** if Gate B is closed, report it and end the session. No code, no probes beyond these reads.

## 1. ESTABLISHED (2026-09-24). Do not re-derive.
- 9693 loaded: August holds `20260804` (21 rows), September holds `20260904` (32 rows), all Cloud Services, both verified via API and a cold SPA drive. Never attach either file again, and never reread a month holding a PDF.
- Item 197 live: the charge-day rate outranks a statement's printed-FX median. August's ANTHROPIC* CLAUDE SUB 104.95 / 108.53 sit in review until August's next natural re-match. Do not trigger one.
- The OpenAI key is funded. Held body-only mail comes back via `render-ingest`, never `re-ingest`.
- Backlog 195 (reread entity re-stamp, needs a red test first) and 196 (fail-closed on an exhausted key, owner decision) are open.

## 2. This session, in order (only if Gate B is open)
1. Cold-drive July: unchanged, eight buckets, no `gl.` string.
2. Create a batch labelled exactly `TEST - GL drive` via `POST /api/expense-batches`. Add one synthetic Corporate Services receipt and one with no company by DIRECT upload (`POST /api/expense-batches/{id}/receipts`), never by mail. Check rows 2 to 6 of the prompt's section 6 in EN and PT. Never Publish it.
3. Purge in the same session: `POST /api/runs/{id}/delete` with `{"confirm": "TEST - GL drive"}`, then prove it gone (`GET /api/runs/{id}` 404, absent from `/months`).
4. Mark the prompt applied (PROMPT-STATUS + status file), PR, merge.

## 3. Hazards
- Never inject July. Do not write to production orgs. No agent writes on Criss's months.
- Deploy with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)` from a clean detached origin/main worktree; verify `/healthz` commit.
- SPA drive: headless `channel="chrome"` Python Playwright. On the gate, type the code until Log in enables, then click. Month workbenches render each card as a collapsed section and hide reconciled rows, so assert the section headline against the API, not vendor names.
- Force-push is gated. Heredocs: no Python triple-quoted blocks, nothing >80 lines. Bash mangles leading-slash args: prefix MSYS_NO_PATHCONV=1.
- The review xlsx `CoA BRISKEN - 6 accounts for Dirk to decide 260924.xlsx`: delete only when the `~$` lock is gone AND sha256 is still `eed95ea3785b1bd7caabde8d8151ec1e0efe57ba9d3e16e7832adb3c8b350789`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````
