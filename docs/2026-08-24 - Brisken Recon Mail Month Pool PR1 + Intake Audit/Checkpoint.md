# Checkpoint: Brisken Recon Mail Month Pool PR1 + Intake Audit

**Date:** 2026-08-24
**Status:** PR 1 shipped + deployed (Fly v87); 6 real receipts recovered into the pool, waiting on two months that do not exist

---

## Summary

Shipped PR 1 of the owner-approved living-month plan: emailed receipts now file
by the month printed ON the receipt and rest in a pool until that month is
opened, instead of landing in whichever batch happened to be open. An owner
question mid-session ("Dirk sent way more than 2, make sure they are there")
turned into a full intake audit that recovered six held receipts and exposed
three defects that make the mailbox unauditable.

---

## What Was Done This Session

### PR 1: the mail pool (#599, #601, #602 — Fly v87)

1. `route_archived` rewritten: CAS `received → routing`, full `parse_receipt_file`
   extraction at ARRIVAL, month stamped from the earliest plausible printed date,
   then routed under `_POOL_LOCK` into the month's open batch or the new `pooled`
   status.
2. `claim_pooled` as the pull half, firing on batch create, rename into a month,
   the startup sweep, and the replay endpoint.
3. `pool_deleted_batch` replaces `mark_batch_deleted`: month-stamped mail returns
   to the pool on delete, so re-creating the month re-claims it (supersedes the
   item-19 re-ingest ruling for stamped mail).
4. Repair paths re-routed: `replay_held` month-routes with a lazy stamp for legacy
   mail, `render_ingest` renders then routes instead of refusing when no month is
   open, `reconcile_interrupted` resolves `routing`→held / `claiming`→pooled,
   `dismiss_archive` widened to pooled.
5. Surface: `pool_month`, `receipt_month_source`, `mixed_months`,
   `pool_month_state`, `n_pooled`, `pooled_back`, `month` + `advisory`, `claimed`.
   All parallel fields; contract updated.

### Live intake audit (owner-triggered)

6. Reconciled the volume against the log: 19 archives = 19 log rows, nothing
   unaccounted for. Confirmed the receive path healthy end to end (MX →
   dedicated IPv4 149.248.221.114 → listener bound on 2525 → accepts any
   local-part at the domain, refuses relay).
7. Recovered all 6 held mails via render-ingest. `n_held` reached 0 for the
   first time; all six landed in the pool with `receipt_month_source: receipt`.
8. Logged the three intake defects as backlog item 30.

---

## Key Decisions Made

### Month identity is the operator's label, and a month-less label never claims
- **Choice:** reuse `batch_period.month_from_label`, which refuses day-bearing
  labels, so the DEFAULT full-date batch label can never receive mailed receipts.
- **Rationale:** the alternative (inferring a month from batch dates) guesses on
  the one field that decides whether a charge can ever match. The create response
  carries an advisory instead, and renaming is the documented fix path.

### A failed claim returns to the pool, not to a held status
- **Choice:** CAS `held_failed → pooled` after a failed claim.
- **Rationale:** the pool is the truthful resting place for a receipt whose month
  exists; held would imply a human is needed when a retry is all that is wanted.

### Rendered the six held mails, did NOT create the months they need
- **Choice:** render-ingest all six (owner-authorized), then stop.
- **Rationale:** `create_expense_batch` refuses an empty batch, so opening
  August/July would mean seeding a fabricated receipt into Criss's live month.
  Pooling is a correct, reversible resting state; inventing a month is a
  workflow decision that is hers.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/intake_mail.py` | rewrite | month routing, pool, claim, repair paths |
| `src/expense_recon/web/app.py` | edit | claim triggers, log counts, advisories, startup sweep |
| `tests/test_intake_mail.py` | rewrite + add | 68 tests, every new one proven red first |
| `tests/test_web_run_management.py` | edit | rename response gained `month` |
| `docs/api-contract.md` | edit | month-pool field table |
| `docs/lovable-month-pool-prompt.md` | new | SPA half (NOT yet applied) |
| `status/p1-improvement-backlog.md` | edit | item 29 (PR 2/3 design), item 30 (intake trust), Shipped row 25 |
| `status/p1-expense-reconciliation.md` | edit | element row + live pool state |
| `status/p1-recon-loop-prompt.md` | rewrite | fresh-chat brief, three ranked directions |

---

## Current Status

PR 1 is live on Fly v87, verified by API reads, a full TEST-namespaced lifecycle
drill on the deployed app, and a Playwright pass against the live SPA. Suite
1237 passed / 2 skipped; calibrate green; ruff clean.

`platform:` infrastructure.yaml unreadable by the pre-flight (pyyaml unavailable
in that runner) — not a state signal, tooling only.

Six real receipts sit in the pool: 2026-08 (Monetico/CIC, two OpenAI purchases,
OpenAI credits) and 2026-07 (Hostinger, AWS billing statement). They join
automatically once those months exist.

---

## Next Steps

1. **Owner:** apply `docs/lovable-month-pool-prompt.md` in Lovable. The live SPA
   currently renders pooled rows as "Arriving" with a blank Month, so six real
   receipts are misreporting themselves to Criss.
2. **Owner/Criss:** create "August 2026" and "July 2026" batches — the six pooled
   mails claim themselves, no per-mail action.
3. **Build:** backlog item 30 (intake trust) — ack allowlist for known personal
   addresses, log refused RCPTs, reconsider auto-rendering body-only mail.
4. **Build:** PR 2 (backlog item 29) — stable content-derived transaction ids,
   append-able statements, the month staying open, incremental re-match.
5. Tell Dirk that anything sent before 2026-08-21 09:17 had no MX to reach.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the brief)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 29, 30)
- `C:\Users\neuma_p1qrsic\.claude\plans\fizzy-seeking-lagoon.md` (approved plan)

### Open Questions
- How many receipts did Dirk send from `dirk_.neumann@icloud.com`, and when? A
  date range settles whether the losses predate the mailbox.
- Should body-only mail auto-render at arrival? All six held mails this session
  were body-only, which suggests it is the normal shape, not the exception.
- Does Criss have a convention for when a month batch is opened? That decides
  whether pre-creating months is helpful or intrusive.

### Working Notes
- The volume is the system of record, not `log.jsonl`. `flyctl ssh console -C
  "ls -1 /data/inbound"` is the authoritative count; the log carries MORE rows
  than archives (a claim or replay appends its own), which is exactly what made
  `n_pooled` count 2 for one mail before #601.
- Graph app-only creds read from `agentic-ops1/workspace/clients/brisken/context/.env`.
  Graph URLs must be `urllib.parse.quote(path, safe="/?$&=,")` or `$orderby`
  spaces raise "URL can't contain control characters".
- Dirk's Sent Items hold exactly 4 mails to the intake, all present in the app,
  and zero bounces — his WORK account is fully accounted for. The iCloud address
  is the unexplained channel.
- A branch cut from a pre-squash feature branch conflicts with main after the
  squash merge; cherry-pick onto `origin/main` instead (cost PR #600).

### Reference Materials
- PRs #599, #601, #602 · Fly release v87
- `docs/api-contract.md` "The month pool: fields added 2026-08-24"

---

## How to Continue

Open a fresh session, paste `p1-recon-loop-prompt.md`, and pick direction 2 or 3.
Direction 1 is owner-side and blocks nothing technically, but leaves six real
receipts misreported in the UI until it is applied.

---

## Strategic Feedback

### What Worked Well This Session
- Proving every new test red by temporarily regressing the real source caught
  what green-on-first-write would have hidden, eight times.
- The live TEST drill on the deployed app found a defect the whole test suite
  missed (`n_pooled` counting log rows, #601). Drills earn their cost.
- Reconciling the Fly volume against the app's own log, rather than trusting the
  log, is what made the "where are Dirk's emails" question answerable at all.

### Suggestions
- Add a `git checkout -- <path>` / `git restore` guard hook for paths with
  uncommitted changes, mirroring the existing `git-stash-gate.py`. One stray
  restore destroyed a whole uncommitted file this session.

### System Health
- The heredoc-with-Python-payload failure recurred twice more despite two prior
  register rows and a documented fix; the memory-layer fix is not holding and
  wants a structural answer.
- Autonomy: 4 human interventions (elevated — one interrupt, one Stop-gate B1
  block, one tool rejection, one redirect).
