# Checkpoint: Brisken P1 Prompts Verified Alias Live

**Date:** 2026-09-07
**Status:** Owner-side items closed; travel routing live; awaiting card list from client

---

## Summary

Closed every owner-side item the 2026-09-06 program left open: verified all
four pasted Lovable prompts against the published bundle (PR #698), set the
travel alias and passed the full TEST- alias drill live (PR #699), and sent
the two client mails (travel-address announce; complete card-list ask) via
Graph, verified in Sent Items. The workstream's next input is Brisken's
card list.

---

## What Was Done This Session

### Bundle verification (PR #698)

1. Fetched the published SPA's index + 45 JS chunks (937 KB) and grepped the
   decisive field names for all four pending prompts (R1 person/private,
   months origin+refusals, R3 trips, R4 settled-by): all present in the
   right chunks.
2. For the two whole-object-replace erasure gates, read the settings chunk's
   save-payload code: card rows save `person: t.person`, intake save carries
   `travel_alias` — both entry gates cleared. PROMPT-STATUS Not-applied table
   empty; item-40 person-entry gate marked cleared in the backlog.

### Travel alias + drill (PR #699)

1. User picked `travel` via AskUserQuestion; set `intake.travel_alias`
   through the operator API (pre-edit settings snapshot, round-trip re-read,
   person aliases untouched).
2. Full TEST- drill against the live app: SMTP to `mx.expenses.brisken.com`
   (bare domain has no A record), mail rested as `pool_kind: travel` with NO
   month minted despite auto-materialize ON, exactly-one-trip suggestion,
   join-trip `created_batch: true` with the vision-read 23.50 EUR receipt
   (absent from the months screen), batch delete `pooled_back: 1`, fixtures
   removed to zero (0 trips, 3 months, pool 0).

### Client comms (sent + logged)

1. Two mails sent via Graph app-only sendMail as matthias.silva, verified in
   Sent Items (`isDraft: false`, 11:31:06Z): travel-address announce to
   Dirk; complete card-list ask to Dirk cc Criss
   (cristiane.cavalcanti@brisken.com, address verified from her own intake
   submissions). Both drafts passed the comms-critic (3 findings fixed on
   the first card draft; the user then reframed the ask entirely, re-audited
   OK). Logged verbatim in comms-log.md; draft files deleted.

### Residuals watch

1. Item-43 check on the live app: no stuck archives, pool 0; refusals split
   reads `n_refused: 38, n_probes: 38, n_refused_ours: 0` — every refusal is
   a scanner probe.

---

## Key Decisions Made

### Card ask = complete inventory, not gap-fill

- **Choice:** The client mail asks for the COMPLETE list of all Brisken
  credit cards (digits + plastic twin, company, person), not the backlog's
  three known gaps.
- **Rationale:** User directive: registry completeness IS the
  business-vs-private classifier — on-list books as company spend, unknown
  triggers the live suggested-private flow (item 41, v103). A gap-fill ask
  would leave unknown-unknown cards misclassified as private.

### Travel alias `travel`

- **Choice:** travel@expenses.brisken.com, set via operator API immediately
  after §5 bundle verification.
- **Rationale:** Obvious to Dirk's staff; no collision with person aliases
  (criss/dirk/matthias); §5 verification made SPA-save erasure impossible.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| automations/expense-reconciliation/docs/PROMPT-STATUS.md | edit (PR #698) | 4 rows to Applied; Not-applied emptied; 2026-09-07 audit method note |
| status/p1-expense-reconciliation.md | edit (PRs #698/#699) | prompts-applied note, R3/R4 rows, alias+drill result |
| status/p1-improvement-backlog.md | edit (PR #698) | item-40 person-entry gate CLEARED note |
| status/p1-recon-loop-prompt.md | edit (PR #699) | rank-1 owner-side applies DONE; collect list updated |
| context/comms-log.md (gitignored) | append | both sent mails verbatim; frontmatter 2026-09-07/outbound |
| context/drafts/2026-09-07-*.md (gitignored) | create+delete | staged drafts, removed after send per sent-drafts convention |
| memory: project_brisken_expense_recon_usability_loop.md + MEMORY.md | edit | prompts verified, alias live, drill gotchas (MX, per-event log rows) |

---

## Current Status

Live app v106: R1-R4 + R2 flip + travel routing all live; 3 month batches
(July/August/September, `created_by: intake`), 0 trips, pool 0, held 0.
Every Lovable prompt applied and bundle-verified. Both client mails sent
2026-09-07. brisken platform: unknown plan, ~?/? ops/mo (infrastructure.yaml
has no platform section for the fastapi orchestrator — feasibility
assessment pending).

---

## Next Steps

1. When Dirk/Criss reply with the card list: enter it via the operator API
   (cards registry: digits incl. plastic twins, entity, person), then verify
   a batch resolves persons through the chain.
2. If Dirk confirms 0113/8311 are his (Zoho labels already name him), enter
   those two persons even before the full list lands.
3. Reactive code rounds resume on evidence: item 27 (wrong day in right
   month), item 23 remaining Zoho string layers (gated on the GL-codes
   call), item 24, overlay routes.
4. p2 status files are 23-78d stale (7 files); refresh when a p2 session
   next opens — out of scope for this p1 session.

---

## Context for Next Session

### Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md (post-program
  ranking; rank-1 now DONE)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 26/40,
  27, 23, 24)
- workspace/clients/brisken/context/comms-log.md (the two sent asks)

### Open Questions

- The GL-codes-vs-categories call (Dirk/Criss): decides how much of item 23
  layers 2-4 is rename vs removal.
- Whether Criss's recon ever covers the Consulting entity's cards (Wise
  1160 / Chase 1176).

### Working Notes

- Bundle audit method: fetch live index → collect `/assets/*.js` refs
  recursively → grep decisive FIELD NAMES (not display copy); for
  whole-object-replace gates, read the save-payload construction in the
  chunk. Script pattern in scratchpad `bundle_probe.py` (ephemeral).
- `expenses.brisken.com` has NO A record; SMTP drills connect to
  `mx.expenses.brisken.com`.
- The inbound log is per-EVENT: one archive can show 2+ rows (seen on the
  drill mail and on Dirk's 09-06 mail). Count archives, not rows, in any
  verification.
- Operator API helper for drills: scratchpad `recon_api.py` (login +
  bearer call wrapper; ephemeral, trivially re-derivable).
- Graph send verification: Sent Items `isDraft eq false` filter;
  `$orderby` values must be URL-encoded (a raw space in the query string
  raises InvalidURL in urllib).

### Reference Materials

- https://brisken-reconcile-dash.lovable.app (published SPA)
- https://brisken-expense-recon.fly.dev (API)
- PRs #698, #699 (merged on green CI)

---

## How to Continue

`/resume brisken` → the card-list reply is the trigger: enter data via
operator API or Settings > Cards, verify person resolution on a live batch,
then pick up the reactive backlog (items 27/23/24/overlays) on evidence.

---

## Strategic Feedback

### What Worked Well This Session

- The comms-critic caught an unqueried-source miss (Zoho labels already
  name Dirk on 0113/8311) that turned a blank question into a confirm —
  exactly the B1-class catch the agent missed at write time.
- Verifying the two whole-object-replace gates by reading the save-payload
  code (not just field presence) made "safe to type data in" a proven
  claim instead of an inferred one.

### Suggestions

- The inbound log's per-event duplicate rows will keep confusing count-based
  checks (cost one investigation today). Worth an `n_archives` or
  archive-grouped view in a future backend round; noted in memory until
  then.

### System Health

- Autonomy: 2 human interventions (card-ask reframe; drafts-split
  preference) — both genuine direction calls, not gap-fills.
- stop-b1-gate blocked two closing-text deferrals ("say the word and that's
  a draft"; "cc Criss if you like") even though the [B1 PRIMER] fired at
  session start — containment worked twice, the write-time habit still
  lags. Same class as the 2026-08-25 pair.
- Register at 206 KB with nothing archivable (all resolved rows inside the
  14-day window); 24/24 hooks intact at session start.
