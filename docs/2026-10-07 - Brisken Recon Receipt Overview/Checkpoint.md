# Checkpoint: Brisken Recon Receipt Overview

**Date:** 2026-10-07
**Status:** Backend live (Fly on `501edf7d`); SPA prompt written in two parts, not yet pasted

---

## Summary

Dirk wants users to see and filter every receipt in one place, so the recon
SPA's Email intake page becomes "Receipt overview" (backlog item 248). The
backend that lists every receipt in the tool is deployed and verified on
production; the TanStack Table page is a two-part Lovable prompt carrying the
full component code, proven on a scratch clone and waiting for the owner's paste.

---

## What Was Done This Session

### Backend (PR #1587, Fly on `501edf7d`)
1. `web/receipt_overview.py` + `GET /api/receipts/overview`: one row per
   receipt from every month's and trip's Expenses page payload, plus set-aside
   files and mail that is held, waiting for its month, parked as a duplicate,
   dismissed or removed after filing. Statuses come from each month's own
   verdicts; mail joins by provenance archive, then (batch, document), then
   arrival second; a removed document is matched by file name so a month move
   does not read as a deletion.
2. Memoized with `CardStatusMemo` under the card roll-up key plus a mail key
   (log stat + every archive `meta.json`).
3. `tests/test_receipt_overview.py` (11, two through the app);
   `regress_check.py` proved both wirings bite; full module suite 4181 passed /
   2 skipped; CI green including the module `test` job.
4. Live read after deploy (one GET): 363 receipts, 184 email / 179 upload,
   every row dated, 2.5 s. Cold drive of the published SPA: unchanged Email
   intake page + months list, 0 writes.

### SPA (Lovable prompt, PRs #1587 + #1593)
1. `docs/lovable-receipt-overview-prompt.md`, generated from the verified clone
   so the code is byte-identical: part 1 = packages (TanStack Table 8.21.3,
   match-sorter-utils 8.19.4), API type, EN + PT `rov.*` keys; part 2 =
   `ReceiptOverviewTable.tsx` + Receipts/Emails tabs in `InboundLogScreen` +
   nav label + route title. Both handed in four-backtick fences.
2. Proven on a scratch SPA clone (node-server build) against a LOCAL copy of
   the 2026-10-07 08:19 backup: 21/21 Playwright checks (counts, fuzzy search
   with no stray rows, typo search, every filter kind, reset, viewer, Emails
   tab, reload persistence, 400 px, nothing cut off, 0 non-GET).

### Ledger
1. Backlog items 248 (this) and 249 (signature-image duplicate finding);
   Shipped row 164; `api-contract.md` section; PROMPT-STATUS row (backend gate
   met, two pastes); `status/p1-expense-reconciliation.md` line.

---

## Key Decisions Made

### TanStack Table v8, not v9
- **Choice:** pin `@tanstack/react-table@8.21.3` + `@tanstack/match-sorter-utils@8.19.4`.
- **Rationale:** v9 (npm `latest` 9.2.6) replaced the API with
  `tableFeatures`/`useTable`; shadcn data tables and Lovable's own edits are v8.

### Receipt rows, mail log kept as a tab
- **Choice:** the page leads with one row per receipt; the old per-mail log
  moves unchanged to an "Emails" tab.
- **Rationale:** held mail, refusals, retry and dismiss only make sense per
  mail, and Criss already works them there.

### Search tightened beyond match-sorter's MATCHES
- **Choice:** per word: substring / word start / acronym; letters-in-order only
  within a spread of `ceil(1.5*(len-1))+1`; one edit for words of 5+ letters.
- **Rationale:** plain MATCHES let "anthr pbc" hit unrelated mails (letters
  scattered across a long subject).

### Upload arrival = stored file time
- **Choice:** `received_from: "stored_file"` with the file's mtime.
- **Rationale:** no upload records a per-file arrival; the stored write time is
  the only honest one, labelled as such on hover.

### Wrap, never truncate
- **Choice:** `break-words` in every cell, status badges allowed to wrap.
- **Rationale:** the owner's same-day directive (item 247, "100% visibility of
  all the content"); the table also sits in the `overflow-x-auto` box item
  247's `fit-tables` measures against.

---

## What Did NOT Work (and why)

- **Plain match-sorter MATCHES as the fuzzy threshold:** "anthr pbc" returned
  Microsoft and Uber mails, because a..n..t..h..r occurs in order across a
  long subject; the drive's stray-row check went red.
- **Deleting the feedback hint's DOM node in the drive (older memory advice):**
  React later threw `removeChild ... not a child of this node` and the page
  showed "This page didn't load"; seeding `erc-fb-hint-seen` fixed it.
- **Port 8765 for the local API:** already bound on this box (WinError 10048);
  8791 used.
- **Item numbers 246/247:** taken by sibling sessions mid-build; renumbered to
  248/249 at merge.
- **First PR #1593 push:** conflicted on PROMPT-STATUS (sibling rows), so CI
  never started ("no checks reported") until main was merged in.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/receipt_overview.py` | Created | Pure builder for the overview |
| `.../src/expense_recon/web/app.py` | Edited | Route, memo, mail version key |
| `.../tests/test_receipt_overview.py` | Created | 11 tests |
| `.../docs/lovable-receipt-overview-prompt.md` | Created | Two-part SPA prompt |
| `.../docs/PROMPT-STATUS.md` | Edited | Not-applied row |
| `.../docs/api-contract.md` | Edited | Endpoint contract |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edited | Items 248, 249; Shipped 164 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited | Status line |
| `.claude/patterns/warn-recon-drive-dom-remove.md` | Created | Warn on drives deleting the hint node |

---

## Current Status

Backend live and verified on production. SPA not pasted, so the live app still
reads "Email intake". brisken platform: unknown plan (no `platform` section in
`infrastructure.yaml`).

---

## Next Steps

1. Owner pastes part 1, waits for Lovable to finish, pastes part 2, publishes.
2. After publish: bundle check (`/api/receipts/overview`, `rov.status.no_charge`,
   `data-receipt-overview`), then a cold replayed drive (one overview GET,
   `route.fulfill`, non-GETs aborted): h1 and nav read "Receipt overview",
   footer count = `n_receipts`, a status pill narrows to its `by_status` count,
   Emails tab still lists mails. Then move the PROMPT-STATUS row to Applied.
3. Item 249: owner call on the fix direction (drop signature-sized inline
   images from the arrival duplicate key, or require the receipt-bearing part
   to match).
4. Remove worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-rcptov` after step 2
   (its `.scratch` holds the 215 MB backup copy and the SPA clone used for it).
5. Stale status files `pre` flagged, not touched here: `p1-recon-loop-prompt.md`
   (22d), `p2-lead-gen-general.md` (22d), `p2-lovable-rebuild.md` (27d),
   `p2-rome.md` (22d).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-receipt-overview-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/receipt_overview.py`

### Open Questions
- Item 249 fix direction (owner).
- Whether uploads should start recording a per-file arrival (who + when) so
  "Received" stops relying on file mtime; not asked, not built.

### Working Notes
- Local bench: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-rcptov\.scratch\` holds
  `d/` (backup), `w/` (working copy with `runs.work_dir` repointed locally;
  without that every upload has no arrival date and `can_view` is false),
  `bench/serve_api.py` (port 8791), `bench/drive.py` (21 checks),
  `bench/make_prompt.py` (regenerates the prompt from `spa/`), `spa/` (clone
  at `6ed5015` + the change, `API_BASE` restored to production).
- Backup 08:19 counts: 378 rows = 243 matched, 58 duplicate, 26 no charge, 16
  waiting for statement, 16 dismissed, 8 set aside, 6 removed, 3 private, 2
  held. Live at 10:10 UTC: 363 (duplicates resolved and rows removed since).
- The arrival duplicate check matched `20260928T153502-57fec943` (Uber) and
  `20260928T084822-268b80cf` (Microsoft) to `20260914T054343-f6020d50`
  (Anthropic) on a shared 15,481-byte `image.png`.
- Restart the node server after every rebuild: it keeps serving the old chunk
  hashes and the page hangs on the new ones.

### Reference Materials
- PRs #1587 (backend + prompt), #1588 (deploy record), #1593 (prompt split)
- `.scratch/bench/shots/` in the rcptov worktree (desktop, phone, filter screenshots)

---

## How to Continue

Wait for the owner's publish, then run Next Steps 2 with the replay pattern
from `feedback_recon_drive_replay_payloads`.

---

## Strategic Feedback

### What Worked Well This Session
- Building the SPA in a real clone against a local backup copy and generating
  the prompt from those exact files: the drive caught three real defects
  (columns clipped at 1440 px, loose fuzzy matches, truncation against the
  visibility rule) before anything reached Lovable or the live machine.

### Suggestions
- The session header was missed again (fourth row today across sessions).
  The prompt-time reminder evidently does not fire on every first prompt;
  a Stop-hook that blocks once when a client session has run 20+ tool calls
  with no `**[` header block in the transcript would make it structural.

### System Health
- Sibling sessions claimed backlog numbers and PROMPT-STATUS rows twice
  during this one task; the re-list-before-push habit caught both, but the
  ledger is a contention point for every parallel recon session.
- Autonomy: 0 human interventions (fully autonomous session).
