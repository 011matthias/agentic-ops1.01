# Checkpoint: Brisken Recon Intake Dedupe + Held-Mail Diagnosis

**Date:** 2026-08-25
**Status:** Five PRs merged and deployed (Fly v91 → v93); every Lovable prompt now applied

---

## Summary

Answered why mailed receipts were being held (body-only mail from any sender
outside `@brisken.com`, and `intake.known_senders` is empty), then built
arrival-time duplicate detection so a receipt the tool already holds never
enters a month twice. Along the way shipped the two living-month
prerequisites, and corrected a wrong report about which Lovable prompts were
live after the owner said all three were applied and measurement proved him
right.

---

## What Was Done This Session

### The living month, prerequisites (#620 Fly v91, #621 Fly v92)

1. **PR 2a** — transaction ids derive from what a statement row SAYS, not
   where it sits. `assign_content_ids` in `ingest/_common.py`, called by all
   three parsers at the end of a parse (a post-pass, because sign
   canonicalization has to run first). Closed the defect where an appended
   statement re-pointed every operator decision onto a different charge.
2. **The find the plan missed:** `sheet_writeback._anchor_row` recovered the
   spreadsheet row by taking the positional id apart, so a content id would
   have silently written NOTHING into Criss's workbook. The row now travels
   in `Transaction.source_row`.
3. **PR 2b-1** — `service.rematch_month` extracted from
   `execute_statement_attach` (behavior-neutral, proven by the existing
   suite), plus `web/judgment_cache.py` so a re-match never re-buys an LLM
   verdict. Keyed by call content AND the answering model.

### Held-mail diagnosis (read-only)

4. Nothing was held; `n_held` was 0. What looked held were six `pooled` mails
   waiting for months that do not exist. The mails that HAD been held were
   four `guest@example.org` drills.
5. Mechanism: `is_known_sender` recognises `@brisken.com` plus
   `intake.known_senders`, and that list is EMPTY in production — the key is
   absent from the live settings object entirely. A known sender's body-only
   mail auto-renders; everyone else holds.
6. Consequence: Dirk's `dirk_.neumann@icloud.com` is outside the tenant, so
   every body-only forward from it holds and goes unacked.
7. Seven of eight refusals are `noauth@flyio.net` / `abuse@flyio.net`
   probing for an open relay since the port went public. All correctly 550'd.

### Arrival-time duplicate detection (#624 Fly v93, #625 notes)

8. New `duplicate` status (kind `resting`), stamped BEFORE the body-only
   branch so a re-sent body-only receipt no longer spends a vision call.
   Row points at the mail that already holds the receipt.
9. Attachments hash `sha1(bytes)[:16]` — the SAME shape the receipt pool
   uses, so the two layers cannot disagree about "the same file". Body-only
   mail hashes its whitespace-collapsed, casefolded body.
10. `POST /api/inbound/{archive}/not-a-duplicate` as the deny-by-default
    escape hatch; dismiss widened; `n_duplicates` + `duplicate_of` surfaced.

### Prompt-state correction (#626)

11. Owner reported the three outstanding prompts applied. Measured: all three
    ARE. `/months` renders a real list (backlog item 32, the blocker,
    CLOSED); the stale "Accepted senders" editor is gone (item 31 CLOSED);
    Status cells render backend `status_label`.
12. Two false negatives in `prompt_ledger.py` recorded in PROMPT-STATUS.md.

---

## Key Decisions Made

### The judgment cache keys on content and model, not the id pair
- **Choice:** diverged from the approved plan's `(transaction_id, document_id)`.
- **Rationale:** a reviewer can correct a receipt's amount after the pair was
  judged; an id key hands back the verdict the model gave for the OLD
  numbers. The model is in the key too, so a move to a stronger model
  re-judges instead of serving stale verdicts.

### Only a mail that ENTERED the workflow owns its content
- **Choice:** `ingested` / `replayed` / `pooled` / the transient routing
  states claim fingerprints. A dismissed or still-held copy does not.
- **Rationale:** if the first copy was judged junk or never cleared a hold,
  the tool does NOT hold that receipt, and calling the next copy a duplicate
  would hide a receipt nobody ingested.

### The Hostinger triple is resolved in the month, not the mailbox
- **Choice:** did not dismiss the two duplicate mails.
- **Rationale:** dismiss is terminal; deleting an expense row is a soft
  delete. Verified the three rendered PDFs are NOT byte-identical
  (`d23a0751` / `682fb280` / `219d0419`) because each carries its own mail's
  metadata, so all three WILL become expenses when July opens and the
  add-time pool dedupe cannot catch them. Criss deletes two reversibly; the
  intake log keeps the honest record that three mails arrived.

### `has_statement` is nine call sites in three classes, not one switch
- **Choice:** triaged and recorded rather than lifted.
- **Rationale:** three must open, two only mean anything once a re-match
  follows, and four expense-edit overlay routes must stay closed because the
  attach BAKES edits into the snapshot receipts.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `ingest/_common.py`, `statement_{csv,xlsx,pdf}.py` | edit | content-derived transaction identity |
| `matching/types.py`, `web/serialize.py`, `output/sheet_writeback.py` | edit | `source_row` decoupled from the id |
| `web/service.py` | edit | `rematch_month` extracted; judgments merged at commit |
| `web/judgment_cache.py` | new | content+model-keyed judgment memo |
| `web/intake_mail.py` | edit | `duplicate` status, fingerprints, ownership index, `unmark_duplicate` |
| `web/app.py` | edit | `n_duplicates`, `not-a-duplicate` endpoint |
| `tests/test_{transaction_content_id,rematch_judgment_cache,intake_dedupe}.py` | new | 55 tests |
| `docs/api-contract.md` | edit | living-month + duplicate field tables |
| `docs/PROMPT-STATUS.md` | edit | all applied; two audit traps recorded |
| `status/p1-{expense-reconciliation,improvement-backlog,recon-loop-prompt}.md` | edit | items 29/31/32/33 |

---

## Current Status

Fly **v93**, healthz 200. Suite **1312 passed / 2 skipped**, calibrate exit 0,
ruff clean. Live: `n_held` 0, `n_pooled` 10, `n_duplicates` 0, `n_refused` 8.

`platform:` ops status unknown for brisken (no plan/ops figures in
`infrastructure.yaml`).

Every Lovable prompt is applied. Because the SPA renders backend
`status_label`, the new `duplicate` status displays correct prose with no
follow-up prompt.

---

## Next Steps

1. **PR 2b-2**: triage the nine `has_statement` sites by class, wire receipt
   arrivals to `rematch_month`, make the statement upload append-capable
   with content-id dedupe and a `statements[]` parallel field.
2. **Owner:** Settings → Email intake → "People we recognise" → add
   `dirk_.neumann@icloud.com`. Until then his body-only forwards hold unacked.
3. **Criss/owner:** three identical Hostinger H_46243348 mails are pooled for
   July 2026; delete two rows once that month opens.
4. Owner: card registry entities for 0113 / 6013 / 9693 / 8311 + the missing
   0340 card (the live MISSING ENTITY count).
5. Decide whether a partial-vs-full sign-inference disagreement deserves a
   visible warning.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the brief)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 29, 33)
- `automations/expense-reconciliation/docs/api-contract.md`
- `C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md`

### Open Questions
- Do the four expense-edit overlay routes stay closed once the month stays
  open, or does the bake become idempotent enough to reopen them?
- Does a sign-inference disagreement between a partial and a full statement
  upload warrant a visible warning?
- Brisken comms-log is 4 days stale; any unlogged conversations?

### Working Notes
- **This session's enforcement layer was ~200 commits stale**: the primary
  clone has ZERO hooks wired and SessionStart still said "intact (20/20)".
  Work in `agentic-ops1-recon` off a fresh `origin/main` branch.
- `prompt_ledger.py` has two known-stale rows: it scores `[x]` on a FOUND
  needle, so "STALE editor must be GONE" passes as `[ ]`; and its refusals
  needle is `"refus"` while the app says **"turned away"**. Read
  PROMPT-STATUS.md before trusting a run.
- `regress_check.py` needs a WINDOWS-style inner path (`C:/Users/...`), and
  multi-line `--replace` literals never match (sources are CRLF) — use a
  single-line anchor.
- The playwright probes need `channel="chrome"`; a fresh uv env pulls a
  headless shell that is not installed.
- State-changing calls to the live app are blocked by the sandbox classifier.
  Reads are fine. Hand write actions over.

### Reference Materials
- PRs #620, #621, #624, #625, #626
- `%TEMP%/claude/recon-probe/`: `verify_pr2a.py`, `held_why.py`,
  `inbound_detail.py`, `would_dedupe.py`, `verify_three.py`

---

## How to Continue

Read the loop brief, then start PR 2b-2 with the guard triage rather than a
blanket lift.

---

## Strategic Feedback

### What Worked Well This Session
- `regress_check.py` rejected three first-draft tests that would have shipped
  green without testing anything: one asserting a hardcoded id string, one
  injecting its fixture before the read instead of mid-flight, and the
  earlier separator test. Writing the test and then proving it red catches a
  different class of defect than the suite does.
- Checking the rendered-PDF hashes instead of reasoning about them. The
  intuition ("body rendering was made deterministic, so the pool dedupe will
  catch them") was wrong, and one read-only command settled it.

### Suggestions
- `prompt_ledger.py`'s needles come from prompt drafts. Needles should be
  lifted from the live DOM after a publish, or the ledger keeps reporting
  shipped features as missing. An inverted row in a positive checklist should
  be reworded to a positive assertion ("only the working editor is present").

### System Health
- The split-PR rhythm held again across a large plan item.
- **Autonomy: 2 human interventions** — one interrupt, one factual correction
  about prompt state that was right.
