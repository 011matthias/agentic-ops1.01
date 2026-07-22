# Checkpoint: Brisken Expense-Recon WS3 Matching + API Twins

**Date:** 2026-07-22
**Status:** WS3 (PR #317) and the `/api` mutation twins (PR #318) both merged AND deployed to Fly (machine v29). The "LLM improves, not copies" plan is now complete through WS3.

---

## Summary

Built WS3 (matching) of the expense-recon plan: the card is now a real matching
signal, which kills the ADOBE/ANTHROPIC FX-false-pairs on the real month (4 -> 0).
Then, on the owner's "can we delete the Fly UI since Lovable owns it now" question,
established that the SPA could not finish a review through `/api` and shipped the
missing JSON mutation twins plus an authorization fix. Owner then ruled the app
**operator-role-only**, which retires the user-role question entirely.

---

## What Was Done This Session

### WS3 / PR #317 (merged 815b656, deployed)
1. **Root cause found, and it was not what the plan assumed.** Card scoping has
   existed since 2026-06-16 but keyed on `account_id`. The statement **PDF** parser
   puts the per-card cycle marker there so it worked on that path; the **CSV/xlsx**
   parsers put the whole ACCOUNT there, so all 134 rows of the real export read as
   `chase-2838-family` while the rows span four cards (2838 x78, 3876 x23, 3645 x22,
   0340 x11). Scoping was a silent no-op on exactly the path Criss uploads through.
   The "wrinkle to resolve first" in the brief was therefore not a prerequisite to
   the feature; it *was* the feature.
2. **Per-row card.** Optional `card` column-map key -> new `Transaction.card_last4`;
   `_tx_card_keys` prefers it and falls back to `account_id`, so the PDF path and any
   cardless source stay byte-for-byte. `account_id` / `transaction_id` untouched, so
   the store and reviewer dispositions keep their keys. Added to `_common.OPTIONAL_KEYS`,
   both tabular parsers, and `inspect.guess_column_map` (tight patterns; `Card Member`
   is deliberately NOT claimed) so hosted uploads auto-map it.
3. **`Match.card_score`** on every match: 1.0 agree / 0.0 disagree / 0.5 either side
   silent (unknown must not sort below a contradiction). Tie-break after reference,
   before vendor; in `_ties`; rendered in the workbench; `blend_card_weight` ships 0.0
   so `test_match_score.py` is untouched.
4. **FX judgment sees both cards** (`tx_card`, `receipt_payment_mode` into the prompt +
   `LLMClient` protocol + OpenAI + Mock), for the case scoping deliberately declines.
5. **Optional second-chance pass** over unmatched (`matching.llm_second_pass_unmatched`,
   default OFF), bounded by entity / card / date window / top-K / call budget; only
   moves ids `unmatched -> judgment_required`, never into `matches`.
6. **Bug found en route:** `_apply_judgment` rebuilt each Match around the verdict and
   dropped the matcher's sub-scores, so every FX row reached the workbench scoring
   0/100 on amount, date, vendor and card. Now carried through.

### API twins / PR #318 (merged b57cc71, deployed)
7. **Route surface enumerated properly** (not by heuristic): 7 mutations already spoke
   JSON and were simply never mounted under `/api` (decisions, confirm-matched,
   categories, manual-match, forget, commit-memory, feedback) -> one decorator each.
   Only four were genuinely browser-shaped and now branch on `_wants_json`:
   publish, unpublish, memory/reset, and the intake chain (`/api/intakes` returns the
   new `intake_id`; `/api/intakes/{id}/run` returns `{job_id}`).
8. **Authorization fix.** `_OPERATOR_RULES` are `^`-anchored PATH regexes, so
   `^/runs/[^/]+/publish$` does not match `/api/runs/x/publish`.
   `path_requires_operator` now matches every rule against both the raw path and the
   `/api`-stripped path (union, so `/api`-only rules still fire). Proven non-theatrical
   by reverting the matcher: 5 escalations reappear.

### Deploy + live verification
9. Deployed both PRs (`flyctl deploy` from clean detached `origin/main` worktrees,
   owner matneumann07@gmail.com). Machine v29, healthz 200, 1/1 checks.
10. Live-verified the twins by their **response body**, not just status: `POST
    /api/runs/{missing}/publish` -> `{"error":"run not found"}` and
    `/api/intakes/{missing}/run` -> `{"error":"upload not found"}`. The old image would
    have returned FastAPI's generic `{"detail":"Not Found"}`, so this distinguishes new
    code from a mere restart. Unauthenticated -> 401 JSON on both.

---

## Key Decisions Made

### Card identity goes in a new field, not into `account_id`
- **Choice:** add `Transaction.card_last4` rather than mirroring the PDF parser's
  `account_id = card`.
- **Rationale:** `transaction_id` is `f"{account_id}:{row}"` and the store, manual
  matches and dispositions key on it. Overloading `account_id` would churn ids for
  every re-uploaded statement. The new field is additive and opt-in.

### `blend_card_weight` ships 0.0
- **Choice:** card is a tie-break + transparency field, not a scored component.
- **Rationale:** a non-zero weight needs the 0.55/0.30/0.15 blend renormalized and
  `test_match_score.py` rewritten. Left tunable for the optimize loop.

### Operator-only role model (owner, 2026-07-22)
- **Choice:** "there should only be an operator role." Do NOT provision
  `EXPENSE_RECON_ACCESS_CODE`.
- **Rationale/consequence:** the user role cannot be minted, so the whole two-role
  apparatus is inert and the escalation PR #318 fixed is unreachable by construction
  (defensive depth only, never urgent). The single operator code is the entire
  security boundary. The dead role code folds into the HTML-UI deletion pass, not a
  standalone refactor.

### Do not delete the HTML UI yet
- **Choice:** ship the API twins first; keep the pages.
- **Rationale:** the SPA has no production URL decided and Criss's canonical review
  surface is still the Fly workbench. Deleting before parity removes her working tool.
  The deletion itself stays cheap (8 GET pages, ~2,455 lines of templates, 4 static
  files, plus collapsing `_wants_json`).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../matching/types.py` | Modified | `Transaction.card_last4`, `Match.card_score` |
| `.../matching/deterministic.py` | Modified | `_tx_card_keys`, `_card_score`, 3-tuple `_signal`, card in `_ties`/`sort_key`, `blend_card_weight`, scoping keyed on card keys |
| `.../matching/judgment.py` | Modified | card args into `judge_fx_match`; `judge_unmatched` + shortlist + score enrichment |
| `.../llm/client.py` | Modified | FX prompt carries both cards; protocol/OpenAI/Mock signatures; `last_fx_cards` |
| `.../ingest/_common.py`, `statement_csv.py`, `statement_xlsx.py` | Modified | optional `card` column -> `card_last4` |
| `.../inspect.py` | Modified | `card` header heuristic (hosted uploads auto-map) |
| `.../cli.py` | Modified | `_apply_unmatched_judgment`; sub-scores preserved in `_apply_judgment`; module-level `MatchingConfig`/`replace` |
| `.../web/app.py` | Modified | 11 `/api` mutation mounts, `_wants_json`, `_not_found`, JSON branches |
| `.../web/auth.py` | Modified | `path_requires_operator` canonicalizes the `/api` prefix |
| `.../web/serialize.py`, `service.py`, `templates/workbench.html` | Modified | `card_score` round-trip + `card_pct` display |
| `.../tests/test_second_chance_unmatched.py` | Created | 10 tests: bucket move, claim-once, bounds, budget |
| `.../tests/test_web_api_twins.py` | Created | 23 tests incl. the escalation matrix |
| `.../tests/test_matching_precision.py`, `test_fx_judgment_llm.py`, `test_match_tuning.py`, `test_statement_csv.py`, `test_inspect.py` | Modified | card signal, FX card args, sub-score preservation, ingest, heuristic |
| `.../README.md` | Modified | document the `card` key + `matching` block |
| `context/.../01-05-2026_ER-00216/run.json` | Modified (gitignored) | map `card` + `type` so the local repro exercises WS3 |
| PR #317, #318 | Merged + deployed | the above |

Ledger writes (this checkpoint, session log, INDEX, context YAML, friction register)
are LOCAL only — the shared working tree has sibling-session uncommitted ledger edits;
committing would entangle them (G1). Batch onto a `docs/...` PR later.

---

## Current Status

- **Both PRs merged AND deployed.** `brisken-expense-recon.fly.dev`, machine v29,
  healthz 200, image `deployment-01KY3F51K3Q2VSVN8QAXDVR74S` superseded by the #318 build.
- **Backend is feature-complete for a full SPA review loop.** Every mutation the review
  workflow needs now has an `/api` JSON endpoint.
- **Suite 766 passed, 2 skipped** (717 baseline -> +26 WS3 -> +23 twins). No new ruff
  findings in touched files. CI green on all 6 jobs for both PRs.
- Platform: expense-recon runs on **Fly** (not Make/n8n) — no infra reconciliation needed.
- WS4 (hosted LLM default-on) was already delivered in PR1; the plan is complete.

---

## Next Steps

1. **Lovable SPA: wire the newly-exposed mutations** (`brisken-expense-review`,
   TanStack Start). This is the only thing between here and retiring the Fly UI.
2. **Decide the SPA production URL** (Lovable URL vs `recon.brisken.com`) — still open
   from 2026-07-21. CORS-add + GoDaddy DNS are agent-doable; the domain attach happens
   in Lovable (user).
3. **Then delete the HTML UI** in one pass: 8 GET pages, templates, static, the
   `_wants_json` branches, and the now-dead role plumbing.
4. **Passive:** on Criss's next upload confirm her statement CSV carries a `Card`
   header (auto-mapped now) and that `Category Decision` reads mostly "kept ER".

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/plan-out-how-we-playful-boole.md` — WS1-WS4, all now shipped
- `src/expense_recon/web/app.py` — the `/api` twin mounts + `_wants_json`
- `src/expense_recon/web/auth.py` — `path_requires_operator` canonicalization
- `src/expense_recon/matching/deterministic.py` — `_card_score` / `_tx_card_keys`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- SPA production URL (Lovable vs `recon.brisken.com`).
- Whether the second-chance unmatched pass should be switched on for Brisken; it ships
  OFF and rescued nothing on the 01-05 month (spent its 12-call budget, no confident
  verdict), which is the correct conservative outcome but not evidence it helps.

### Working Notes (do not re-derive)
- **The real export has four cards**: 2838 x78, 3876 x23, 3645 x22, 0340 x11. Every
  ER-00216 receipt carries payment mode `1 - CorpServ 2838/1672 (Chase)`.
  ADOBE/ANTHROPIC are all on 3645/3876.
- **Deterministic before/after on the real month:** software charge paired with an ER
  receipt 4 -> 0; judgment 18 -> 16; unmatched tx 115 -> 117; unmatched rec 1 -> 3.
  Judgment drops by 2 not 4 because two freed receipts were re-assigned to their
  correct-card charges. Reconciliation guarantee asserted in the harness both runs.
- **Scoping deliberately declines** when the receipt's card is absent from the statement
  entirely (single-card export, partial download): the receipt is left UNSCOPED so a
  real match is never excluded on evidence we do not have. That residual case is what
  the FX-prompt card args cover.
- **Live FX probe (honest result):** the model rejects the 4 pairs with OR without the
  cards. Supplying them drops confidence 0.30 -> 0.20 and makes the card the stated
  reason; a genuine same-card travel pair (DB Bahn) still accepts at 0.85. So the card
  args strengthen the rejection, they did not flip it. Full LLM run 144 calls, $0.011.
- **`_OPERATOR_RULES` are PATH regexes.** Any future `/api` twin inherits its rule from
  the canonicalization — do NOT add duplicate `/api/...` regexes.
- **Prod secrets:** only `EXPENSE_RECON_OPERATOR_CODE` (mn040307), `AUTH_SECRET`,
  `OPENAI_API_KEY`. No user code, by owner directive.
- Local repro: `run.json` in `01-05-2026_ER-00216/` now maps `card` + `type`.

### Reference Materials
- Live app: https://brisken-expense-recon.fly.dev (operator code vault "Expense Recon App")
- PR #317, #318 on `011matthias/agentic-ops1.01`
- SPA repo: `011matthias/brisken-expense-review`

---

## How to Continue

`/comd_resume brisken`, read the plan + this checkpoint. The backend work is done;
the next move is Lovable-side (wire the mutations, pick a URL), then the UI deletion.
Fly deploys are Band-3 and need an explicit order.

---

## Strategic Feedback

### What Worked Well This Session
- Grounding every claim against the real artifact before building. Reading the actual
  handler bodies (rather than trusting my own route-shape classification) cut the twins
  work from an imagined 17 endpoints to 7 one-line mounts plus 4 real ones.
- Reverting the auth matcher to watch the tests go red. That converted "I added a
  security fix" into "here are the 5 escalations it prevents", and it is the only
  reason the fix is known to be load-bearing rather than decorative.

### Suggestions
- The single operator code is now the entire security boundary on a tool holding
  Brisken bank statements. Worth a deliberate decision on rotation and on whether
  `/api/login` should rate-limit, independent of the role question.

### System Health
- `stop-b1-gate` fired twice and was right both times; the offer-instead-of-execute
  disposition persists even with the rule loaded. It is now a recurring class across
  four sessions — the hook holds, the habit does not improve.
- Autonomy score: 4 human interventions this session (elevated — run /comd_system-dev
  to close gaps).
