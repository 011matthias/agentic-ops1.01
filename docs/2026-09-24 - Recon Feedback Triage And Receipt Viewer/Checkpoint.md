# Checkpoint: Recon Feedback Triage And Receipt Viewer

**Date:** 2026-09-24
**Status:** Item 178 backend shipped and deployed; SPA half written, not pasted

---

## Summary

Read the recon feedback store, found eight notes with no backlog item, and filed them against live reads rather than transcribing them. One of the eight turned out to be the same request asked three times since July, and its cause was a payload defect rather than a UI gap, so the backend half was built, shipped and deployed the same session.

---

## What Was Done This Session

### The feedback store, fully itemized
1. Read `/feedback.jsonl`: 85 notes against the backlog's 82. Three new (#83-#85), five older with no item (#73, #74, #75, #77, #82).
2. Filed all eight as items 174-181 (PR #1229). Each written against a live read of the September month and `/api/settings`, which changed three of them: #75 read as not reproducing, #73's premise held but pointed at a label rather than a pipeline bug, and #74's field already existed.
3. Corrected item 176 the same session (PR #1231) after the user asked to see the older notes: it *does* reproduce, via `can_mark_private`, which stays true on a row already marked private (2 of 2 private rows across the estate; 47 of September's 75 read false, so the flag discriminates).
4. Item 178 and 181 gained measurements (PR #1233); note #35 was audited against live July and deliberately not filed, since its symptom is gone.

### Item 178: the receipt nobody could read
1. Traced the cause off the published bundles and the live payload: `/image` served the stored file with its own media type, 70 of 75 September receipts are PDFs, and the SPA's only `createObjectURL` is its download helper. Downloading was the only thing the payload allowed.
2. Built `src/expense_recon/receipt_render.py` and added `?as=png` / `?page=N` / `X-Receipt-Pages` to the existing route, with a stored-bytes fallback on render failure. Shipped PR #1245, deployed to Fly, `/healthz` stamp `264a4bc6`.
3. Wrote `docs/lovable-receipt-viewer-prompt.md` for the SPA half and handed it over as pasteable text.

### The drive that corrected the prompt
1. Drove the live September month over the user's open Chrome on CDP `:9333` after `agent-browser` hung twice.
2. Closed the outstanding deploy consumer gate: 77 rows, no error text, no fallback strings.
3. Measured that the page has **zero** `<img>` elements and makes **zero** requests to `/receipts/`, so the prompt's "replace the dead View receipt control" was wrong; corrected and re-handed (PR #1248).

---

## Key Decisions Made

### File the category notes as record, not as queued work
- **Choice:** Items 179-181 (notes #83-#85) are marked FILED AS RECORD.
- **Rationale:** They were left 17:48-18:09 CEST; the direction closing item 170 ("no working on expense category definition anymore") landed at 19:02, about an hour later. Whether it reaches notes written before it is the owner's call, not an inference for a backlog file.

### Serve a raster rather than teach the front end to render PDFs
- **Choice:** `?as=png` on the server; the viewer becomes an `<img>`.
- **Rationale:** A PDF.js dependency in a Lovable-owned SPA is a bigger surface than one query parameter, and the server already carries `pypdfium2` for vision ingest. It also makes the change useful to any future consumer, not just this SPA.

### Photos pass through untouched even under `?as=png`
- **Choice:** `as=png` promises *displayable*, not literally PNG.
- **Rationale:** Re-encoding a JPEG costs quality and time for no gain; the 5 photo receipts already display.

---

## What Did NOT Work (and why)

- **`agent-browser`, twice:** hung past 150s and 180s, bare and with `--executable-path` pointing at Chrome. Both had to be killed with TaskStop. Playwright MCP was also down (`CONNECT_TIMEOUT` at session start), so the first attempt at the consumer drive produced a stated LIMITATION instead of a drive.
- **`/json/new` over GET:** Chrome 153 answers `405 Method Not Allowed`; tab creation needs PUT.
- **`dict(r.headers)` in the live verification probe:** `HTTPMessage` is case-insensitive and `dict()` throws that away, so every content-type lookup read `None` and the probe reported "0 of 77 PDFs served as PNG" on a deploy that was working correctly. A confident negative from a blind instrument.
- **Two blank PDF pages of equal size as a paging fixture:** they rasterize to identical PNG bytes, so `test_second_page_differs_from_the_first` failed for the right reason. Fixed by giving each page its own size.
- **First draft of the route patch:** called `logger.warning` where the module defines `log`, a NameError reachable only on the render-failure path, and left `import mimetypes` unused after the refactor. Both caught by lint before commit.
- **Python-in-heredoc, three times:** the heredoc gate blocked each one (triple quotes twice, a double backslash once). The Write tool is the documented route and was reached for only after the block each time.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/receipt_render.py` | created | page count + PDF page rasterization |
| `src/expense_recon/web/app.py` | modified | `?as=png` / `?page=N` / `X-Receipt-Pages` on the receipt route |
| `tests/test_receipt_render_178.py` | created | 13 tests, 3 caller-level |
| `docs/lovable-receipt-viewer-prompt.md` | created + corrected | the SPA half, with the CDP measurements |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | modified | items 174-181, item 176 correction, 178/181 measurements |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | modified | roll-up for 09-23/24 |
| `.claude/patterns/warn-cdp-before-browser-limitation.md` | created | stop-event rule: scan CDP ports before declaring no browser |
| `.claude/patterns/warn-hand-prompt-as-text.md` | created | stop-event rule: hand a Lovable prompt as text, not a path |

---

## Current Status

Item 178's backend is live on Fly (`264a4bc6`), verified against all 77 real September receipts. The month page renders correctly post-deploy. Criss still cannot read a receipt, because the viewer is the SPA half and that prompt has not been pasted into Lovable.

Every feedback note #73-#85 now has an item. Items 164/165/166 (the learning loop) and 179/180/181 (the GL vocabulary) remain open, the latter three filed as record behind the item-170 category stop.

brisken platform: unknown plan, `~?/?` ops/mo, last assessed `?` — `infrastructure.yaml` has no platform section for this client, so a feasibility assessment is outstanding.

---

## Next Steps

1. Paste `docs/lovable-receipt-viewer-prompt.md` into Lovable, publish, then drive the September month and confirm a click on the receipt cell produces a `/receipts/.../image?as=png` request. That request is the check that cannot pass by accident.
2. Decide whether the item-170 category stop reaches notes #83-#85, which were written an hour before it. Items 179-181 are parked on that answer.
3. Item 181 is shippable the moment the five cloud-vendor GL accounts exist: all five Software & Subscriptions merchants carry none, and live July shows the fallback posting the category name as the account.
4. Surface the MEGA CENTER / MEGA CENTRE mis-mapping to the owner: both Professional Services merchants post to `E100010 - Travel Expense`.
5. Run `/comd_ops-audit brisken` or record the platform section; the ops status line cannot be produced today.
6. Two status files are stale: `p2-product-decks.md` (63d) and `p2-targeting.md` (64d).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 174-181 at the bottom of Open)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-receipt-viewer-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md` (the live-read recipes)

### Open Questions
- Does "no working on expense category definition anymore" cover notes #83-#85, written an hour earlier?
- Which Zoho GL accounts do the five cloud vendors book to?
- Is MEGA CENTER on a travel account deliberately, or a registry mis-entry?

### Working Notes
- Login recipe and the `$UA` / `$API` / `$AUTH` shape are in `docs/operating.md`; the operator code is in the gitignored `context/.env`.
- The month view API is `GET /api/expense-batches/{run_id}`, not `/api/runs/{id}/review` (that 404s). `/api/runs/{id}` returns the same object.
- September is `51a22ad72864`, July `50622baec444`, May `86929f2a909a`.
- CDP drive recipe that worked: `PUT http://127.0.0.1:9333/json/new?<url>`, then the websocket from `webSocketDebuggerUrl`, `Page.enable` + `Runtime.enable`, `Runtime.evaluate` with `returnByValue`. The cold seat already held a session, so no login was needed. Close the tab with `/json/close/{id}`.
- Feedback-store demography, if it comes up again: all 85 notes originate on German networks, 49 on one `/64` that carries both the `matthias` and the shared `operator` logins. `operator` is a shared code, so the store cannot attribute a note to a person; the backlog's owner-vs-operator labels are inferred at filing time.

### Reference Materials
- PRs #1229, #1231, #1233, #1245, #1248
- Live app `https://brisken-expense-recon.fly.dev`, SPA `https://expenses.brisken.com`

---

## How to Continue

The backend is done and proven. The next move is the paste, and it is the user's: nothing in this repo can write to the Lovable project. After the paste, drive the month and assert the network request, not the appearance of a modal.

---

## Strategic Feedback

### What Worked Well This Session
- Filing each note against a live read instead of transcribing it changed the content of three of eight items, and killed one wrong diagnosis before it became work.
- `regress_check.py` on the route wiring caught what a green suite would have hidden: it named the 3 tests that actually run through the caller.

### Suggestions
- The backlog cites some notes by number and whole waves by prose, so "has this note been answered" is not mechanically answerable. That ambiguity is why #73-#82 sat unread for three days. A note-id column, or a rule that every note gets a numbered citation even when a wave covers it, would make the next audit a grep instead of a judgement call.

### System Health
- Two gates caught what discipline did not: `stop-b1-gate` on a closing offer and `deploy-consumer-gate` on an unqualified "verified" after a deploy. Both are recurrences of 2026-09-21 rows whose fix was `documented` and did not hold; the structural half is what works.
- **Autonomy: 2 human interventions** (hand the prompt over as text; the browser is open, use it). Both were memory-recall failures with the memory present in the index, and both are now pattern rules.
