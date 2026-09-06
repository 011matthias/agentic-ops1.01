# Checkpoint: Brisken Expense Tool Owner Program

**Date:** 2026-09-06
**Status:** Program captured and merged; round 1 (person-on-card + private-expense suggestion) is next

---

## Summary

The owner directed four product changes for the expense tool, asked-and-answered rulings included; all four are captured as backlog items 38-41 with a four-round build plan (PRs #672 + #674, merged). Earlier in the session (2026-08-29 half): tool access handed over and the access email to Dirk + Criss sent via Graph and verified.

---

## What Was Done This Session

### Access handover (2026-08-29)

1. Verified the live surfaces (SPA login page up, `/healthz` ok) and both operator codes against `/api/login` (200) before handing anything over.
2. Sent the access email to dirk.neumann + cristiane.cavalcanti via Graph as matthias.silva (draft validated, send 202, Sent Items isDraft=false, Drafts empty), logged verbatim in comms-log.
3. Owner ruling captured: NO separate logins; both use the shared operator code. The named per-person codes (2026-08-21) stay minted but undistributed; the "owner distributes per-person codes" open item is retired.

### Owner program capture (2026-09-06)

1. Asked the four gating product questions (travel identification, trip unit, reconciliation scope, person source); rulings recorded near-verbatim in the backlog.
2. Items 38-41 written into `p1-improvement-backlog.md` with design consequences and the round plan; loop brief re-ranked so the program leads (PR #672, then #674 for item 41).
3. The 2026-08-24 "pre-creating months intrudes" ruling marked SUPERSEDED by item 39, in both files, with the interim behavior stated (pool still waits until the round deploys).

---

## Key Decisions Made

### Company/travel split is declared, not inferred (item 38)

- **Choice:** Batch type chosen at creation; mail routes by address (receipts@ = company, a travel alias = travel). Trips are named + date-ranged with a VARIABLE traveler roster. Both functions reconcile against statements.
- **Rationale:** Owner rulings 2026-09-06. Deterministic split, no AI judgment; "both reconcile" makes the cross-batch match pool the deep design half.

### Mail materializes the month (item 39)

- **Choice:** A pooled receipt with a confidently-known printed month auto-creates the batch and ingests + categorizes. Supersedes the 2026-08-24 anti-pre-creation ruling.
- **Rationale:** Owner: "turned into expenses without having to start a reconciliation." The pool's month-routing half stays; wrong-year OCR bounds the auto-create window.

### Person attribution rides the card (item 40)

- **Choice:** Cards gain a `person`; the existing card chain resolves it for mailed AND manual receipts. Sender identity stays provenance, never attribution.
- **Rationale:** Owner, near-verbatim: "each card is attributed to a name and therefore every expense can be attributed to a person. Even the ones injected via email."

### Unknown payment methods suggest a private expense (item 41)

- **Choice:** A hint resolving to no registered card is SUGGESTED (never stamped) as a private expense; confirmed rows carry `reimburse_to` (the one bounded exception to card-only attribution) and report as a per-person reimbursements section.
- **Rationale:** Owner directive; deny-by-default preserved, operator confirms.

### Shared login for Dirk + Criss

- **Choice:** Both under the shared operator code; no per-person codes distributed.
- **Rationale:** Owner: "they do not need separate logins."

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/status/p1-improvement-backlog.md | edit | Items 38-41 with rulings + round plan (PRs #672, #674) |
| workspace/clients/brisken/status/p1-recon-loop-prompt.md | edit | Program leads the ranking; supersession noted (PRs #672, #674) |
| workspace/clients/brisken/status/p1-expense-reconciliation.md | edit | Program element rows added (this checkpoint's PR) |
| workspace/clients/brisken/context/comms-log.md | append | 2026-08-29 access email logged verbatim (gitignored) |

---

## Current Status

Program captured and merged; nothing of it is built yet. Live app unchanged (Fly, SPA all-prompts-applied state per the loop brief). brisken platform: unknown plan, ~?/? ops/mo, last assessed ? (pre-flight could not read a `platform` section). p2 status files are 22-77d stale (untouched this session, flagged by the sweep).

---

## Next Steps

1. Build round 1: item 40 (cards gain `person`, chain resolves it, view fields, review count) + item 41 (`suggested_private` state, `reimburse_to`, reimbursements report section). House loop: worktree, RED-proven tests, adversarial review, suite + calibrate, deploy, Lovable prompt.
2. Round 2: item 39 auto-materialization (window-bounded, `created_by: "intake"`, ack wording). Resolve the Hostinger triplicate dismissals (item 33 owner yes) before it deploys.
3. Round 3: trip entity + declared-type creation + travel alias routing. Round 4: cross-batch match pool + trip report.
4. Owner-side: card registry data entry (persons for all cards, entities for 0113/6013/9693/8311, create 0340) — item 26, now gating attribution coverage; pick the travel alias name when round 3 lands.
5. A p2-scoped session should bring the six stale p2 status files current or delete shipped ones (W1 §4); not blind-bumped here.

---

## Context for Next Session

### Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md (the paste-in brief; program ranked first)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 38-41 carry the rulings + design)

### Open Questions

- Round 3 design call: does a travel receipt auto-join the single open trip whose date range covers it, or always rest for manual claim? (deny-by-default is the house pattern)
- Item 23 residue rides along when cheap: user-visible "Zoho" string sweep.

### Working Notes

- Trips + "both reconcile" means the match pool spans batch types; the invariant to build is a global receipt claim (no receipt settles two charges across two batches). Everything else in the split is surface.
- `reimburse_to` pre-fills from `submitted_by` on mail but is operator-confirmed; do not generalize sender-based attribution beyond item 41.
- The named operator codes (criss/matthias, vault) remain valid on the live app but are deliberately undistributed after the shared-code ruling.

### Reference Materials

- PRs: #672 (items 38-40), #674 (item 41); merged 2026-09-06.
- App: brisken-reconcile-dash.lovable.app (SPA), brisken-expense-recon.fly.dev (API).

---

## How to Continue

`/comd_resume brisken`, read the loop brief, cut a worktree off origin/main, build round 1 per the backlog's item 38 round plan.

---

## Strategic Feedback

### What Worked Well This Session

- Asking the four product questions BEFORE writing the design meant the backlog items carry rulings, not guesses; the trips/reconciliation answer ("both reconcile") changed the architecture and would have invalidated a guessed design.
- The supersession of the 2026-08-24 pre-creation ruling was caught by reading the loop brief before editing; recording it in place prevents the retired ruling from being re-cited next round.

### Suggestions

- The p2 status-file staleness (six files, 22-77d) recurs at every checkpoint sweep; a p2 session should either bring them current or delete the shipped ones rather than letting the sweep flag them indefinitely.

### System Health

- Autonomy: 2 human interventions (the shared-code correction; the four product rulings, which were genuinely the owner's to make).
- One stop-b1-gate block (2026-08-29 turn): closing text offered the Dirk named-code Fly secret as "say the word" instead of acting or framing the LIMITATION; on redo the classifier blocked the write and it became a clean LIMITATION. Ninth agent-deferred row of this class; the structural gate holds, the authoring habit is the residual.
