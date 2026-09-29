# Checkpoint: Expense-Recon Item 239 Gemini Reader

**Date:** 2026-09-29
**Status:** Item 239 LIVE (Fly v276): Gemini 3.8 Flash reads every new receipt. Item 240 (re-read the stored receipts, preview then apply) specified, not started.

---

## Summary
Dirk's request to read receipts with Gemini went from scoping to production in one session: scoped, key made billed and unexposed, reader built behind a switch, measured blind against OpenAI on 251 stored documents, switched on. The owner then ordered the 335 stored receipts re-read the same way, preview first; that is item 240, handed to a fresh session.

---

## What Was Done This Session

### Scope and key (2026-09-27/28)
1. Scope from a 9-agent workflow (`wf_ebece896-543`): the seam is `LLMClient.extract_receipt`; 210 of 224 July-September receipts are PDFs, and text-layer PDFs are read as text by `gpt-4o-mini`, never by the vision model.
2. Key probed by differential calls: free tier on 09-27 (every Pro model `-FreeTier` quota, limit 0), billed on 09-28 after Dirk showed project `1Expense` on Tier 1 Prepay (Pro answers 200).
3. Owner ruled no rotation, "just unexpose it": 37 copies redacted from this session's and nine workflow agents' logs, a probe leftover `%TEMP%\vx.json` deleted (Google's 404 page had echoed a `?key=` URL), git proven clean; the sweep used the `.env` as positive control, which caught two broken search runs.

### Build, measure, switch (item 239)
1. PR #1533 (`f66f364b`): `llm/gemini.py` GeminiReader (stdlib REST, key in `x-goog-api-key`), hooked into `extract_receipt` behind `EXPENSE_RECON_GEMINI_READS` = `images` / `all`; same prompt, fences, schema, cache; falls back to OpenAI on any failure; priced; `/healthz.receipt_reader`; doctor check. 26 tests, suite 4144 / 2 skipped, two regress proofs.
2. A/B on item 223's 251 inputs and its two stored OpenAI passes: Gemini Flash x2 (USD 3.82), Pro x1 on 39 disputed docs (USD 1.16), 46 stable disagreements to four blind checker agents. Key fields Gemini 15 / OpenAI 3; text-layer PDFs 8-0; document kind OpenAI 5 / Gemini 2; Pro agreed with Flash 26 of 31.
3. PR #1534 (`73e2fec8`): `fly.toml` `EXPENSE_RECON_GEMINI_READS = "all"`. After the owner's `flyctl auth login`: secret via `flyctl secrets import --stage` on stdin, `deploy.py` v276 on `222cb158` VERIFIED, `/healthz` receipt_reader key_set true, cold read-only SPA drive of `/months`. PR #1536 records it LIVE.

### Checkpoint-time structural fixes
1. `block-merge-chained-after-any-command` replaces the warn rule (disabled): a `gh pr merge` starting a command after `;`, `&&`, `||`, `then` or `do` is refused; tested on this session's PR #1533 call and two older shapes, a standalone merge and a harmless commit pass.
2. `warn-secret-literal-in-command`: a literal Google / OpenAI key or a `?key=` URL in a command warns; a header or an `.env` read passes.

---

## Key Decisions Made

### Build, test, then switch
- **Choice:** owner picked it over switching straight away or testing only.
- **Rationale:** the research favoured Gemini on degraded photos, but nothing had tested these models on Brisken's receipts, and most of them are text PDFs.

### Flash, reading everything
- **Choice:** `gemini-3.8-flash`, reads `all`, Google's default thinking.
- **Rationale:** it won on both paths; Pro added nothing at 3-4x the price.

### Re-read the stored receipts: preview, then apply
- **Choice:** owner picked a preview that writes nothing, shown per month, then apply month by month; Criss's edits and confirmations stay on top.
- **Rationale:** a re-read can reopen confirmed matches and swap duplicate copies; the owner sees that before anything moves.

---

## What Did NOT Work (and why)
- **Deploying on 09-28 morning:** `flyctl auth whoami` rejected the token in `~/.fly/config.yml`; unblocked only by the owner's `flyctl auth login`.
- **In-VM synthetic read on production (`flyctl ssh console`):** refused by the auto-mode classifier; not retried.
- **`responseFormat` with `mimeType: "application/json"`:** HTTP 400; the enum `APPLICATION_JSON` works.
- **First key sweep:** `grep` under `timeout 500` over `Repo` returned nothing silently; then `timeout rg` failed because `rg` is a shell function (use the VS Code `rg.exe`).
- **Costing Flash from one probe:** USD 1.25 estimated per pass, 1.98 real (about 1,650 output tokens per document with thinking); Pro was narrowed to the disputed documents.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `expense-reconciliation/src/expense_recon/llm/gemini.py` | created | the Gemini reader, switch parsing, `/healthz` status |
| `.../llm/client.py`, `cli.py`, `doctor.py`, `llm/cost.py`, `web/app.py` | edited | hook, builder wiring, doctor check, prices, health field |
| `.../tests/test_gemini_reader_item_239.py` | created | 26 route- and caller-level tests |
| `.../fly.toml` | edited | `EXPENSE_RECON_GEMINI_READS = "all"` |
| `.../docs/api-contract.md`, `docs/operating.md` | edited | health field; how to switch the reader |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edited | item 239, Shipped rows 158-159, status row |
| `.claude/patterns/block-merge-chained-after-any-command.md`, `warn-secret-literal-in-command.md` | created | structural fixes for this session's friction |
| `.claude/patterns/warn-merge-chained-after-any-command.md` | edited | disabled, superseded by the block |

---

## Current Status
New receipts are read by Gemini in production; stored readings are unchanged. brisken ops status: platform unknown plan (pre-flight). Nothing waits on Criss.

---

## Next Steps
1. Item 240 in a fresh session: the continuation prompt is in `Mini-Checkpoint-2.md` beside this file.
2. Watch the first Gemini-read arrivals; the log line "receipt reader ... could not read ... reading it with OpenAI" marks a fallback.

---

## Context for Next Session

### Files to Read First
- `Mini-Checkpoint-2.md` (this folder), the item 240 continuation prompt
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 223 (step 7) and 239

### Open Questions
- Read each stored receipt twice and change a field only when both Gemini passes agree? Decide by measurement in item 240.

### Working Notes
- The A/B harness and results live in the primary clone's gitignored `.scratch/ab239-gemini/`; `scored.json` holds every adjudicated disagreement with the document's value.
- Gemini leans to `document_kind: invoice` for charge confirmations and NFC-e till receipts; watch the kept copy of the next invoice + receipt pair.
- Invoice-number spacing (`HMVWDWIL 0029` vs `HMVWDWIL0029`) does not move a duplicate key: `reference_key` compares alphanumerics and `reference_keys` reads all three number fields.

### Reference Materials
- https://ai.google.dev/gemini-api/docs/pricing, https://ai.google.dev/gemini-api/terms, https://ai.google.dev/gemini-api/docs/billing

---

## How to Continue
Paste the continuation prompt from `Mini-Checkpoint-2.md` into a fresh Claude Code chat.

---

## Strategic Feedback

### What Worked Well This Session
- A positive control on every negative: the `.env` as the known hit exposed two silent search failures, and item 238 as the known backlog item exposed an MSYS-mangled `git show` that read "0" for the wrong reason.
- Reusing item 223's frozen inputs and stored OpenAI passes made the A/B exact (same files, routing and prompt, gated by fingerprint) and saved half its cost; blind A/B labels kept the checkers honest.

### Suggestions
- The iteration-loop HARD LIMIT counts three `tools/regress_check.py` runs as a fix-then-test loop; they are verification, not fixes. Exempt `regress_check.py` from the streak counter.

### System Health
- Three of four friction rows repeat known classes whose fixes were warnings that fire after the fact; two are now a block and a pre-command warn. Autonomy: 2 human interventions (Dirk's billing screenshot; the Fly login), plus 3 owner decisions asked on purpose.
