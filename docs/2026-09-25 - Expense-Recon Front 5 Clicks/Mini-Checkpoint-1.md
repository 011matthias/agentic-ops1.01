# Mini-Checkpoint: Expense-Recon Front 5 Clicks

**Date:** 2026-09-25
**Status:** Item 222 steps 1-5 + FX self-confirm shipped and live (PR #1469, merge 32c949db, Fly v260 on 1770e574); step 6 open
**Type:** mini

---

## Summary
Front 5 of the five-front parallel round: the FX judge now judges the tool's own evidence, review rows say why they need a click, booked charges leave review, PDF payoffs read payment, and (owner decision) a clean FX pair confirms itself. Every predicted live row moved as predicted after deploy.

## What Was Done
- **Step 1, judge on the tool's evidence:** `FxEvidence` (reference rate/source/converted/gap/band, card verdict, vendor agreement) is sent to `judge_fx_match`. The prompt says "rate is given"; the raw card strings are replaced by the tool's verdict; a missing total is "(unknown)". The cache key carries `FX_JUDGMENT_PROMPT_VERSION` = "2". A look-alike demotion names its rival and gets `review_code: uniqueness_rival`; with card 100, vendor >= 75 and a band match, no model call is made. Offline replay of the 13 live verdicts (27 calls, about USD 0.005): 4 skipped, 9 re-judged, labelled pairs 2/4 -> 3/4 right.
- **Step 2:** `review.cause` / `review.cause_detail` (rival_agrees, model_doubts, merchant_disagrees, no_card_rival, fx_review_zone, probable_date_gap), computed at read time by `attach_review_causes`.
- **Step 3:** posted/already_posted charges are skipped by all three judgment passes; `charge_states` files a booked review row as `unmatched`.
- **Step 4:** `row_type_of` reads the payoff descriptor on a Type-less credit.
- **Step 5:** `rows[].reverses_transaction_id`.
- **Owner decisions (AskUserQuestion):** item 76 revisit YES; `fx_pair_confirmable` is built (central-bank rate, gap <= 1%, card agrees or unknown, vendor >= 75). A p >= 0.85 model verdict lifting a pair: NO.
- **Live after v260 (read-only probe + cold headless-Chrome drive):**
  - July: n_review 13 -> 0, n_unmatched_tx 63 -> 76, n_booked_no_receipt 39 -> 52.
  - August: 6 causes on exactly the predicted rows; 4 payoffs -> payment; n_confirm_matched 4 -> 14.
  - September: 3 probable_date_gap; 2 payoffs -> payment.
  - The SPA headlines match the API (July "0 need review · 76", August "5 · 98", September "0 · 30").
- **Suite:** 3,928 passed after merging fronts 1 and 2. 9 regress proofs, all TEST BITES.
- **Renumber:** front 1 claimed item 221 at merge, so front 5 is backlog **item 222**, Shipped row 142.

## What Did NOT Work (and why)
- **Prompt v2a, showing both the raw card labels and the tool's "cards AGREE":** gpt-4o-mini still wrote "the cards differ" on 7 of 9 pairs, because it re-compared "card-2838" against "CARTAO ...3876" itself. It was fixed by sending only the verdict ("the SAME card paid ..."). The final prompt calls every re-judged pair "same" (p 0.85-0.95), which includes JoseliMariaDos x 0067, a pair the labels call wrong. On 4 labelled points that is net +1, and I stopped tuning.
- **agent-browser `--session recon-front5 --executable-path chrome open`:** it hung past 120 s (as memory `feedback_agent_browser_named_sessions` warns). The drive ran on headless Playwright `channel=chrome` instead (scratchpad `drive_spa.py`).
- **First deploy.py run:** refused because a sibling's docs commit landed seconds after mine (the deploy tree was 1 behind). Re-checking out origin/main in the deploy tree fixed it.

## Current Status
Live on Fly v260 (commit 1770e574 carries 32c949db). The judge's re-judging and the FX self-confirm reach each month only at its next natural re-match: nothing was written to Criss's months. The "Last matched ... 13 to review" line on July is the stored 03:31 re-match record and reads 0 at the next one. The SPA does not render `review.cause` until `docs/lovable-review-cause-prompt.md` is pasted.

## Next Steps
1. Step 6 (continuation prompt below): the candidate-level merchant floor for exact pairs. Measure first on July, August and the six bundles; ship only if 0 labelled-right pairs move.
2. The owner pastes `docs/lovable-review-cause-prompt.md`; run `tools/lovable-bundle-audit.py` after they publish.
3. At August's next natural re-match, check: 10 FX pairs self-confirm (the ones whose category reads ready), the FX verdicts re-judge under v2, and JoseliMariaDos-like "same" answers stay review-only.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 222
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_front5_clicks.py`
- `.scratch/recon-matching-gaps-2026-09-25.md` (main clone), section "Receipt to charge pairing", first gap

---

## Continuation prompt

````
/comd_resume brisken

# FRONT 5, step 6: the candidate-level merchant floor for exact pairs (item 222)

## Where it stands
Item 222 steps 1-5 and the owner-approved FX self-confirm shipped 2026-09-25 (PR #1469, merge 32c949db, Fly v260 on 1770e574), all live and checked per row: the FX judge gets the tool's rate / card verdict / vendor (prompt v2, cache keyed on it); `review.cause` / `cause_detail`; booked charges are not judged and leave n_review (July 13 -> 0); PDF payoffs read `payment`; `reverses_transaction_id`; `fx_pair_confirmable` (August n_confirm_matched 4 -> 14). Owner said NO to letting a p >= 0.85 model verdict lift a pair. Waits on the owner: pasting `docs/lovable-review-cause-prompt.md`. Waits on Criss: nothing (every live effect comes at her months' next natural re-match).

## The one item left
Step 6: an EXACT pair (amount + date, any merchant) with vendor < 0.5 whose receipt names a card is demoted to review with `review_code` and cause `merchant_disagrees` when ANOTHER unmatched receipt of the same amount exists in the pool (item 133 rules 1 and 3); otherwise unchanged. Code: matching/deterministic.py EXACT at the same-currency match (`match_one`, the EXACT branch ~:943-962 on 373b1356, search "Exact amount, date within"); the tip-band merchant floor `_same_currency_band_allowed`; rule (b) rival-merchant demotion (search "rule (b)" / item 133); `no_card_vendor_guard` is the no-card sibling (D5) to mirror. Live shape: exact pairs in Reconciled under vendor 75 waiting for a click, August 4, September 4; labelled wrong instances 0 after the card and D5 guards.
Measure FIRST, before any code ships: `tools/recon-match-attribution.py --live DB --run-id 50622baec444` and `074a7b8905d7` with the live labels (main clone's gitignored `context/expense-reconciliation/expense-reports/csv/by-month/{July,August}-2026_live_*`), plus `--bundle` on the six scorer bundles; DB pulled read-only (flyctl ssh sqlite3 backup + sftp to a WINDOWS-form path); `RECON_MODULE_SRC` = your worktree's src. Do it before and after. If ANY labelled-right pair moves, report it and do not ship. `tools/recon-accuracy-guard.py` against `tools/recon-accuracy-baseline.json` must hold; CI's accuracy job must stay exact (re-record `expected.json` in the same PR only if the move is the intended one).

## How to work
Protocol: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`. Own worktree off origin/main (`git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-front5-step6 C:\Users\neuma_p1qrsic\Repo\agentic-ops1-front5b origin/main`); append, never reflow shared files; after any push, merge origin/main (expect to renumber a backlog item at merge); deploy only via deploy.py from a detached origin/main worktree, refreshing it if a sibling lands first; drive cold with headless Playwright channel=chrome (agent-browser hung 2026-09-25). Rules that do not bend: no live writes on Criss's months without a per-action AskUserQuestion; matching program closed (no threshold / band / window moves); route-level test through the caller plus one regress_check proof per fix; B4. Suite: `uv run --directory <worktree>/workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (3,928 on 2026-09-25, 8-11 min; no xdist). Scratch helpers from this session (my scratchpad, not the repo): the frozen-payload readers were one-offs; re-derive them.

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
