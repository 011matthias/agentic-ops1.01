# Mini-Checkpoint: Brisken Recon Body-Only Mail

**Date:** 2026-08-21
**Status:** Round 5 of the 8-PR feedback wave shipped, deployed, acceptance-tested live
**Type:** mini

---

## Summary

Body-only mail handling (theme C2, note 12) shipped as PR #563 and
deployed: held mail with no attachment gains view-body / render-as-PDF /
dismiss actions, with the render going through the normal vision +
quarantine pipeline. The live acceptance test on Dirk's real held mail
passed: rendered, ingested, and set aside by the quarantine as a
non-receipt (restorable in the strip) — judgment surfaced, not data
vanished.

## What Was Done

- `web/body_render.py`: HTML-to-text extraction + byte-deterministic
  Pillow image-PDF render (dates pinned to the archive stamp — the
  adversarial review showed wall-clock stamps broke digest dedupe and
  would have let retries double-ingest a mail).
- Three endpoints: GET `/api/inbound/{archive}/body` (sanitized text,
  never the raw archive), POST `.../render-ingest` (normal pipeline;
  transient `rendering` status via CAS makes render/dismiss/replay
  mutually exclusive; retry allowed after failure), POST `.../dismiss`
  (terminal; held strip can reach zero).
- Replay rescues body-only mail stranded as `received` by a router
  crash; `reconcile_interrupted` flips killed renders to retryable;
  container installs fonts-dejavu-core (Pillow's default font renders
  German umlauts/euro as tofu); page cap 4 = vision's read cap.
- Suite 1199/2 (+11 tests); calibrate OK; PR #563 CI-green merged;
  deployed; live-verified.
- Acceptance (live): Dirk's OpenAI credit-reload forward → body view
  200 (1,596 chars readable) → render-ingest → `ingested`, January
  batch, n_held 0; rendered PDF in the set-aside strip (reason
  "other", restorable). Booking credit top-ups = Criss/Dirk call.
- Friction candidates both discarded as gates-working: pre-publish flag
  on a markdown-only ledger push (CI gates the merge), iteration-3x
  flag on three DISTINCT staged live-verification probes (not a
  fix-retry loop). One self-detected B4 near-miss: PR number written
  into the backlog before the PR existed; verified correct at creation
  (#563), no harm — watch the pattern.

## Current Status

Feedback wave: rounds 1-5 of 8 shipped (#555/#556/#559/#561/#563).
Four Lovable prompts wait on the owner (cards, zoho-decoupling,
cards-r3, intake-quickwins, body-only = five actually; all listed in
the status file). Remaining rounds: memory validate/adjust, language +
receipt visibility, Cards R4 (owner answers pending, backlog item 10).

## Next Steps

1. Memory validate/adjust round (PUT/DELETE /api/memory/categories,
   `validated_at` migration, reset confirm) — design in the plan file.
2. Backlog item 18 (async endpoints acquire the batch lock on the event
   loop) rides the next code round.
3. DOM-probe the SPA when the owner publishes any Lovable prompt.
4. Owner items: Cards R4 answers (item 10), item 19 ruling (re-ingest
   for attachment mail after a month delete), set-aside restore call on
   Dirk's rendered credit notice.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md
- workspace/clients/brisken/status/p1-improvement-backlog.md
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (Theme D design)
