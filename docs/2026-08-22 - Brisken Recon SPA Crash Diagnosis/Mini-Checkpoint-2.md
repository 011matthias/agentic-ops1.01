# Mini-Checkpoint: Brisken Recon SPA Crash Diagnosis

**Date:** 2026-08-22
**Status:** Root cause found and fix prompt handed; blocked on an owner Lovable publish

---

## Summary

Criss's reviewer SPA broke on "This page didn't load" when the owner
created expenses and again when opening a month. Two independent
failures were diagnosed from outside the app: a hosting-level 404 on
route chunks (fixed, live) and a backend-to-SPA contract mismatch on
`parse_issues` (fix prompt handed, not yet published). No engine code
changed; the batch and its expenses were intact on Fly throughout.

## What Was Done

- Ruled the backend out first: `/healthz` 200, machine started, full Fly
  log clean, the generate-expenses job (`3e13fb3d13f4`) polled to done
  and the batch (`ae61e122a505`) served 200. The later stop/start is
  normal scale-to-zero, not a crash.
- **Failure 1 (fixed, live).** Enumerated every asset the published
  bundle references: 5 of 42 returned 404, and always the same ones -
  the chunks whose filenames start with `_` (`_batchId`, `_runId`,
  `_intakeId`) plus `new-*`. Route-derived names the host refuses to
  serve, so every republish reproduced them with fresh hashes. Handed a
  `chunkFileNames: "assets/chunk-[name]-[hash].js"` Vite override;
  proved it by building Lovable's own repo locally (46 assets emitted,
  zero unsafe names, and two silently colliding routes - `expenses.index`
  vs `expenses.new` - separated as a side effect). The fixed build is
  live: all 42 referenced files now serve 200.
- **Failure 2 (open).** The owner's console (React error #31, keys
  `{file, line, message, severity}`) pinned the second cause exactly:
  `ExpensesReviewGrid.tsx` renders `data.parse_issues.map(s => <li>{s}</li>)`
  while `api.ts` types the field `string[]`; the backend has emitted
  objects since 2026-07-22 (`service.py:2745` and `:4300`). Rendering an
  object throws and the root error boundary eats the whole batch page.
  Latent since the 2026-08-21 SPA commit that added the block; it only
  fires on a batch that HAS parse issues, which the new batch is.
  Confirmed the neighbours are genuinely strings (`upload_issues`,
  folder-ingest `issues`), so this is the only mismatch of its kind.
- Handed the fix prompt (type `ParseIssue[]`, render `message` with
  `file:line` muted and error-severity toning, string-tolerant fallback).

## Current Status

Backend healthy and untouched. SPA hosting bug fixed and live; the
`parse_issues` crash is still live on the batch page until the owner
publishes the handed prompt. Brisken ops status: platform plan unknown,
`/ops-audit brisken` not run this session. Feedback wave stays at rounds
1-7 of 8 shipped; Cards R4 still owner-gated. Of the 5 outstanding
Lovable prompts, 3 are now pasted (per the owner's screenshots).

## Next Steps

1. Owner publishes the `parse_issues` fix in Lovable; then verify the
   batch page renders against the real batch `ae61e122a505` (probe the
   route, then a DOM check), not just that the build shipped.
2. Add a contract test on the backend side so a `parse_issues`-class
   shape change cannot reach the SPA silently again (the SPA has no
   type-check against the live API).
3. Resume the wave: Cards R4 on the owner's item-10 answers; backlog
   items 18/19/20 ride the next code round.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md
- workspace/clients/brisken/status/p1-improvement-backlog.md
- docs/2026-08-21 - Brisken Recon Language Receipt Round/Mini-Checkpoint-1.md
