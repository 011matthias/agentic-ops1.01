# Checkpoint: Brisken P1 Feedback Wave and Lovable Prompt Audit

**Date:** 2026-09-06
**Status:** Every Lovable prompt applied and verified live; p1 backend and SPA in step for the first time

---

## Summary

Answered the one new reviewer note (the way into a month is invisible), then
audited which Lovable prompts are actually live in the published SPA instead
of trusting the ledger. Four had never been pasted; the owner published them,
and a re-audit confirms all eight are in. Two ledger gaps the audit exposed
are closed.

---

## What Was Done This Session

### The feedback wave
1. Pulled all 31 reviewer notes off the live volume (`GET /feedback.jsonl`).
   Exactly one was new: 2026-08-28 on `/months`, anchored on a row's Created
   cell, "why cant the user enter and view or edit the month". Everything
   earlier was already worked through, including the 08-22 count note.
2. Established it is not a routing bug. `GET /api/runs/{id}` and
   `GET /api/expense-batches/{id}` both answer 200 with real data for all six
   live batches.
3. Read the published bundle to explain it. The month name is the only
   clickable thing in the row and carries `underline-offset-2 hover:underline`,
   so at rest it looks like the plain text beside it; the row has no click
   handler, which is why the Created cell the operator clicked did nothing;
   and the row menu holds Rename and Delete with no Open.
4. Shipped `docs/lovable-months-open-prompt.md` and backlog item 34 (PR #652).

### The prompt audit
5. Built a bundle audit that needs no browser: fetch every JS chunk the
   published app can load (45 chunks, 936 KB) and grep the lot. A string
   rendered from an i18n key still lives in a chunk, so this sees copy the DOM
   only shows after a click.
6. Made the decisive signature the API FIELD NAME the renderer has to read
   (`seen_undefined`, `n_duplicate_copies`, `is_extra`, `coverage`,
   `period_suggestion`), because a renderer cannot show a field it never
   names. Display copy alone produced two wrong reads, both corrected.
7. Found four prompts never pasted (coverage, duplicates, card definition,
   months open) and four already in (the 2026-08-28/29 batch: attach dialog,
   card strip, Zoho copy, month suggestion).
8. Moved the 08-28/29 four out of gitignored scratch into `docs/` beside every
   other prompt, each banner-marked with its evidence (PR #659). They were the
   record of what production was asked to do and a rollback would have had
   nothing to re-apply.
9. Owner published the remaining four. Re-audit on 2026-09-06 confirms every
   one is live; the not-applied list is empty for the first time (PR #675).

### Ledger repair
10. Backlog item 34 closed against the bundle evidence.
11. The card-screen round (PR #651, `seen_undefined`) had **no shipped row at
    all**, nine days after it deployed. Added as shipped row 30.
12. `PROMPT-STATUS.md` carries both audits, the method, and the two signatures
    that misled the first pass.

---

## Key Decisions Made

### Audit by field name, not by display copy
- **Choice:** A prompt counts as applied when the bundle references the API
  field its renderer must read. Display strings are corroboration.
- **Rationale:** Two display strings gave wrong answers on the first pass.
  `"Not a duplicate"` is `wb.dups.notDup` from the workbench panel that
  predates the duplicates prompt. `"Card account id"` survives on purpose as
  the Other-account free-text label, so its presence is not evidence the
  attach-dialog prompt is missing. A field name has no such twin.

### Keep the pasted prompts in `docs/`
- **Choice:** The four scratch prompts move into the tracked docs home.
- **Rationale:** They are the record of what production was asked to do. A
  Lovable rollback with the only copy in gitignored scratch has nothing to
  re-apply.

### Do not rewrite the historical "remaining Lovable half" rows
- **Choice:** A standing note in `p1-expense-reconciliation.md` names
  `PROMPT-STATUS.md` as the current-state authority.
- **Rationale:** Those rows are records of their round. Rewriting a dozen of
  them to say "applied" would destroy the record and invite drift the moment
  the next gap opens.

### Leave PR #657 unrecorded
- **Choice:** Flagged as a next step rather than reconstructed.
- **Rationale:** It is another session's round; its shipped row carries detail
  I would be inferring from a checkpoint summary rather than knowing (B4).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/docs/lovable-months-open-prompt.md` | created | The SPA fix for the 2026-08-28 note |
| `automations/expense-reconciliation/docs/lovable-{attach-dialog,card-strip,zoho-copy,month-suggestion}-prompt.md` | created | The 08-28/29 four, adopted out of scratch, banner-marked applied |
| `automations/expense-reconciliation/docs/PROMPT-STATUS.md` | edited | Both audits, the method, the two misleading signatures, empty not-applied list |
| `status/p1-improvement-backlog.md` | edited | Item 34 opened then closed; shipped row 30 (the card screen); coverage SPA half no longer outstanding |
| `status/p1-expense-reconciliation.md` | edited | `updated: 2026-09-06`; standing note naming PROMPT-STATUS as the authority |

---

## Current Status

brisken platform: unknown plan, ~?/? ops/mo. Last assessed: ?.

Backend and SPA are in step. All eight outstanding prompts are live, verified
by field name against the published bundle. p1 status files are current
(0d). The p1 backlog's open items are the ones nobody has decided yet, not a
delivery queue.

Seven p2 status files are stale (22 to 77 days), unchanged from the 2026-08-29
flag. Out of scope here; p1 was the whole session.

---

## Next Steps

1. Add the shipped row for PR #657 (the decision-free trio, items 35/36/37).
   It is the only round in the loop history with no entry.
2. A p2 session should update or prune the seven stale status files (W1 §4:
   delete beats nursing).
3. Next feedback wave. The channel is the in-app widget; pull with
   `GET /feedback.jsonl` and read the newest `ts`.
4. The friction register stays above 200 KB after this archive pass; the
   remainder is unresolved rows, which the archiver never moves. If it keeps
   growing, the split has to be by something other than resolution.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`

### Open Questions
- Does the months row now open on a click anywhere, or only via the name and
  the new Open item? The bundle proves the class changed and `months.open` is
  wired to a menu item; a row-level handler is harder to read out of minified
  code and was not confirmed.
- PR #657's shipped row: reconstruct from the PR diff, or ask the session that
  built it?

### Working Notes
- **The audit is a shell script, not a tool.** Fetch `/`, extract
  `/assets/*.js`, follow the chunk names each bundle imports, concatenate,
  grep. Chunk hashes change on every publish, so re-derive the list rather
  than reusing a path. Kept in scratch on purpose; it is thirty lines and the
  method is written into PROMPT-STATUS.
- **`copy 2 of 2` reads 0 hits even though the duplicates prompt is applied.**
  That badge text is interpolated, so the literal never appears. The `expx.dup.*`
  keys and `is_extra` are the signals that hold.
- **An HTTP client that is not pinned to IPv4 can fail here while `curl -4`
  succeeds.** Both probes now pass `local_address="0.0.0.0"`. The failure
  surfaces as `WinError 10051`, which reads like a dead network and is not.
- The live app's auth is a bearer token from `POST /api/login` with the vault
  operator code, not a cookie. The batch list is `GET /api/expense-batches`.

### Reference Materials
- `https://brisken-reconcile-dash.lovable.app` (SPA), `https://brisken-expense-recon.fly.dev` (API)
- `.scratch/lovable-prompts-2026-08-28/` (now superseded by the `docs/` copies)

---

## How to Continue

`/resume brisken`, then read the backlog. Nothing is blocked on us: the
delivery queue is empty and the next input is either a feedback note or an
owner decision on the parked design questions.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the shipped bundle instead of driving a browser. The Playwright MCP
  has no browser on CDP 9222 and `agent-browser` hung, and neither mattered:
  the answer was a grep over static assets, available in one call and
  reproducible by anyone.
- Choosing the field name as the signature. Both wrong answers this session
  came from display copy, and both were caught by the same discipline that
  produced the right one.

### Suggestions
- Fold the shipped row into the round's own PR. PR #651's row went missing
  precisely because the pattern is "ship the code, then a separate docs PR for
  the ledger", and the second half is the one that gets dropped when the
  session turns. The duplicates round survived only because its follow-up PR
  happened to run before the interruption.

### System Health
- The gitignored-scratch habit for owner-facing artifacts is a durability
  hole. Four prompts that were pasted into production existed in exactly one
  place that git does not track, for nine days.
- Autonomy: 1 human intervention (a nudge to retry after a network outage).
