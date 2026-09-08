# Checkpoint: Brisken P1 Drop Cap And Create-UI Retirement

**Date:** 2026-09-08
**Status:** Drop v1 LIVE (owner-published); cap raise deployed; delta prompt (cap copy + create-UI removal + nav + Open-month) with owner

---

## Summary

Closed yesterday's open consumer drive (browser tooling healed by
`agent-browser install`), then a three-round day driven by the owner:
per-ingest cap 80 → 500 with an honest overflow ledger (#716,
Fly-deployed), the ruling that month creation leaves the UI entirely
(#717, item 46), and the evening discovery that the owner had already
published drop v1 mid-day — the prompt doc was reworked into a DELTA
(#718). Two new workfields seeded: cost centers (Dirk) and
US-substantiation report compliance (items 47/48).

---

## What Was Done This Session

### The open verification from 2026-09-08 morning

1. `agent-browser install` (fresh Chrome 152) fixed both browser paths;
   TEST- drop materialized June 2026 (`created_by: drop`,
   `month_source: receipt`), published SPA driven COLD through the
   login gate (months list + batch page, real values, no fallbacks),
   fixture deleted, live state 3 months / pool 0. Status row shipped
   via #713; memory index compacted 20.7 → 17.4 KB on the harness
   directive (127 entries, none dropped).

### Item 45 — cap raise + honest overflow (#716, deployed)

1. `FOLDER_MAX_FILES` 80 → 500; a >cap month group in a drop now
   ledgers its overflow `rejected`/`upload-cap` (with `limit`) BEFORE
   the ingest call — pre-fix the ingest truncated silently while rows
   read `filed`. Suite 1508 → 1510; both guards mutation-proven; live
   probe: 85 one-byte files through one POST, all ledgered, zero
   vision cost.

### Item 46 — month creation leaves the UI (#717, docs only)

1. Owner rebutted the "create flow survives" analysis (a 4-reader
   workflow had grounded it in code); decision round ruled: NO
   statement-first creation, "Add a statement" stays inside month
   pages, the button + `/expenses/new` company arm die, pooled rows
   get a one-click "Open {month}" (existing create route,
   label-only). Create route survives as plumbing only.

### The v1-live correction (#718)

1. Owner: "you do realize receipts page is already present?" Evening
   bundle audit (46 chunks) confirmed v1 published mid-day
   (`chunk-receipts` reads `n_filed`/`n_needs_month`; Recibos strings
   in i18n) while `upload-cap` has zero hits and "Start a new
   month"/`expenses/new` persist. Prompt doc reworked into the delta;
   v1 moved to PROMPT-STATUS Applied; publish-signal lesson pinned.

---

## Key Decisions Made

### Month creation is not a user concept any more (owner)

- **Choice:** Months come only from injection (mail, drop, Open-month
  release); no statement-first creation.
- **Rationale:** One routing brain, no ceremony. Accepted consequence,
  named pre-greenlight: a zero-receipt month at statement time needs
  one receipt dropped first (drop-page month override, ~10 seconds).

### Overflow is ledgered, not silently truncated

- **Choice:** Pre-slice the month group in `route_dropped_receipts`
  rather than trusting the ingest's internal cap.
- **Rationale:** A "filed" row for a skipped file is a ledger lie; the
  cap itself stays as the per-call vision/zip bound.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| web/service.py | edit | `FOLDER_MAX_FILES` 500 (#716) |
| web/intake_mail.py | edit | drop overflow pre-slice + ledger rows (#716) |
| tests/test_receipts_drop.py | edit | 2 new tests, both RED-proven (#716) |
| docs/api-contract.md | edit | upload-cap + limit + chunking contract (#716) |
| docs/lovable-receipts-drop-prompt.md | rewrite | amended twice, then reworked to DELTA (#716/#717/#718) |
| docs/PROMPT-STATUS.md | edit | v1 → Applied; delta row; publish-signal lesson (#718) |
| status/p1-expense-reconciliation.md | edit | consumer drive + items 45/46 + v1-live (#713/#716/#717/#718) |
| status/p1-improvement-backlog.md | edit | items 45 + 46 (#716/#717/#718) |

---

## Current Status

Backend live on Fly (cap 500, overflow ledger); SPA runs drop v1
(page, needs-month picker, badge strings) — the DELTA (cap copy,
chunking, create-UI removal, nav redesign, Open-month release) is with
the owner as one paste. Live data state: 3 real months, pool 0.
brisken platform: unknown plan (no platform section in
infrastructure.yaml for the fastapi orchestrator).

---

## Next Steps

1. **After the owner pastes the delta:** bundle re-audit (`upload-cap`,
   label-only `/api/expense-batches` POST from the intake chunk, no
   `expenses/new`/"Start a new month" references) AND a browser drive
   for the chrome halves (nav, button death); flip PROMPT-STATUS.
2. **Item 47 (new workfield):** cost centers — Dirk wants cost
   attribution to projects/purposes (Nicolas Brazil, Lidar, tool work,
   marketing). Session prompt handed 2026-09-08; design round first.
3. **Item 48 (new workfield):** US-substantiation report compliance —
   verify against primary IRS sources, scope strictly to what the tool
   outputs. Session prompt handed 2026-09-08; research gate first.
4. Card-list reply from Dirk cc Criss (2026-09-07 ask) → operator-API
   entry + live person-resolution verify; then items 27 / 23-strings /
   24 / overlay routes.
5. p2 status files 47-79d stale (6 files) — refresh when a p2 session
   opens.

---

## Context for Next Session

### Files to Read First

- workspace/clients/brisken/status/p1-improvement-backlog.md (items
  44-48)
- workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-receipts-drop-prompt.md
  (the DELTA + the v1-applied record)
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md

### Open Questions

- GL-codes-vs-categories in the deliverable documents (item 23 tail)
  and the Consulting entity's cards — both owner-side, unchanged.

### Working Notes

- Bundle audits need httpx (urllib's default UA gets 403 from the
  Lovable host). Recipe: fetch index, regex `/assets/*.js`, follow
  chunk refs transitively, grep decisive FIELD NAMES.
- The drop path's cap slice imports `FOLDER_MAX_FILES` per call, so a
  test can monkeypatch `expense_recon.web.service.FOLDER_MAX_FILES`
  and every enforcement site follows.
- `gh pr merge --auto` fails on this repo ("Auto merge is not
  allowed"); watch checks with `gh pr checks N --watch`, then plain
  squash-merge on green.
- Fly deploy trap unchanged: positional build context =
  the expense-reconciliation DIRECTORY.

### Reference Materials

- https://brisken-expense-recon.fly.dev (API),
  https://brisken-reconcile-dash.lovable.app (SPA)
- PRs #713 #716 #717 #718 (all merged)

---

## How to Continue

`/resume brisken` → if the owner published the delta, run next-step 1
(re-audit + drive); otherwise pick up item 47 or 48 with their handed
prompts.

---

## Strategic Feedback

### What Worked Well This Session

- The decision round before building (AskUserQuestion with a
  recommendation + consequences) caught a real disagreement early; the
  owner's ruling reversed my keep-the-button position and the build
  that followed was docs-only instead of a wrong backend feature.
- Mutation-proofing both halves of #716 took ~4 minutes with
  `regress_check.py` and turned "the cap is raised" into an
  evidence-backed claim.

### Suggestions

- PROMPT-STATUS should carry a "publish signal" convention now pinned
  in its header: any operator report describing live behavior a prompt
  would have introduced triggers an immediate bundle re-audit, not one
  at the next session boundary. Consider a tools/ probe that diffs the
  published chunk manifest against the last audited hash set so a
  publish is detected mechanically.

### System Health

- Autonomy: 2 human interventions (the item-46 ruling, which was the
  owner's to make; the v1-live correction, which was a real catch of
  my stale-audit assertion).
- Browser tooling is healthy again post-`agent-browser install`; the
  morning drive, the evening drive and the login-gated cold entry all
  ran clean in named sessions.
