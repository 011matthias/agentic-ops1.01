# Checkpoint: Brisken Intake Round 2 + Overview

**Date:** 2026-08-21
**Status:** Round 2 + intake overview LIVE and drilled; user feedback run in progress

---

## Summary

Mail-intake round 2 shipped on owner directives (auto-ack yes, retention
start, structural fixes) and the intake-overview backend followed the same
day: PR #552 (guarded Graph auto-ack, held-mail alerts, 10-year retention
sweep, named operator codes) and PR #553 (inbound mail joined to the
expense rows it created), both merged on green CI and live-drilled on
prod. The user is now running a hands-on feedback pass in the tool with
the April 2026 kit (37 receipts pulled off the volume + exact-month Chase
CSV).

---

## What Was Done This Session

### Round 2 (PR #552, suite 1105/2)
1. `web/graph_notify.py`: internal-only Graph sender; sends as
   matthias.silva (app-only), recipient hard-asserted single
   @brisken.com, 50/day cap, `X-Auto-Response-Suppress: All` (Graph
   custom headers must be X-*; Auto-Submitted cannot be set).
2. Auto-ack on ingest success to the REAL sender (never the alias);
   idempotent per archive (`ack_at`); auto-generated/no-reply inbound
   never acked; `intake.auto_ack` toggle (default on).
3. Held-mail alerts to `intake.alert_recipients` (default
   matthias.silva) once per archive (`alert_at`) on every held-status
   write incl. startup reconcile.
4. Boot retention sweep, `intake.retention_years` default 10 (AO §147),
   archive-name-pattern-guarded deletes.
5. Named operator codes: `EXPENSE_RECON_OPERATOR_CODES` code:label
   pairs; label HMAC-signed into the token, stamped on feedback notes;
   legacy shared code still valid. criss + matthias codes generated,
   stored in the local vault, set as Fly secrets.

### Intake overview (PR #553, suite 1106/2)
1. Add summary now names created rows (`documents`); ingest job stamps
   them into archive meta (empty = all duplicates).
2. `GET /api/inbound/log?detail=1` joins entries to expense rows
   ({document_id, vendor, date, total, currency}, `deleted: true` for
   operator-removed rows, `batch_label`); one view build per referenced
   batch, degrade-not-500.

### Live verification (both deploys, from clean merged main)
1. Ack drill: SMTP in 11:21 → ingested → ack in the mailbox 11:22:10Z
   (Graph read; suppress header present; single send, two folder
   copies).
2. Overview drill: fresh mail → log entry showed its created row;
   deleting the row flipped it to `deleted: true`; batch left clean
   (10 rows, 0 TEST).
3. Named-code login live: `operator: criss` returned; legacy code
   returns `operator`.

### Feedback-run kit for the user
1. Corrected the "13 receipts is all" claim after user pushback:
   enumerated ER PDFs (ER-00101 = 29 pages), by-month kits
   (`csv/by-month/01-04-2026_ER-00215/` holds the exact April Chase
   CSV + reference ERs), and the volume's past batches (April 2026 =
   37 receipts, May 2026 = 27 + already reconciled).
2. Pulled the 37 April receipt files off the volume (tar → sftp) to
   `context/expense-reconciliation/receipts-april-2026/`.
3. Handed run recipe: fresh April month (37 receipts + exact-month
   CSV), or attach CSV to the existing April batch, or inspect the
   reconciled May batch.

### Docs / owner handovers
1. Access Policy runbook (5 PowerShell commands for Dirk/IT):
   `workspace/clients/brisken/context/graph-access-policy-runbook.md`.
2. Consolidated Lovable prompt (Email-intake overview page, aliases
   editor, ack/alert/retention settings, folder-zip picker, null-render
   fix) handed in chat; user reports ALL prompts pasted into Lovable.
3. Status row updated (PRs #552/#553); memory
   `project_brisken_expense_recon_mail_intake` fully updated.

---

## Key Decisions Made

### Auto-ack ships enabled, internal-only
- **Choice:** Default on, recipients restricted in code to @brisken.com,
  loop-guarded, capped; activation not gated on a further owner yes.
- **Rationale:** Owner said "auto ack is a good idea" for exactly this
  feature; blast radius is internal colleagues who just mailed us.

### Retention defaults to 10 years in code
- **Choice:** `retention_years=10` (AO §147) rather than waiting for a
  ruling; owner-adjustable in settings.
- **Rationale:** Owner said "retention also good to start"; the archive
  is the system of record, so the conservative statutory floor is the
  only safe default.

### Zoho-export person column DROPPED
- **Choice:** Attribution stays in-app; no person column in the Books CSV.
- **Rationale:** Owner: "No need for zoho since we can inject via email."

### Named codes instead of multi-user
- **Choice:** Per-person revocable codes with signed labels; no user
  accounts, no per-user data.
- **Rationale:** Fixes the shared-boundary problem the smallest way while
  the multi-user restructure stays dropped.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| src/expense_recon/web/graph_notify.py | create | guarded internal-only Graph sender |
| src/expense_recon/web/intake_mail.py | edit | acks, alerts, retention, documents stamping, config |
| src/expense_recon/web/auth.py | edit | named operator codes, signed labels |
| src/expense_recon/web/app.py | edit | login labels, feedback attribution, retention at boot, log?detail=1 join |
| src/expense_recon/web/service.py | edit | add summary names created documents |
| tests/test_intake_mail.py, tests/test_web_auth.py | edit | 10 new tests (suite 1106/2) |
| workspace/clients/brisken/status/p1-expense-reconciliation.md | edit | round-2 + overview rows |
| context/graph-access-policy-runbook.md | create | owner PowerShell runbook (gitignored) |
| context/expense-reconciliation/receipts-april-2026/ | create | 37 April receipts pulled from volume (gitignored) |

---

## Current Status

Mail intake fully live end-to-end: receive → custody → ingest →
provenance → ack, held → alert → retry, overview join deployed. Dirk's
first organic mail sits `held_body_only` (forwarded, attachment-less) —
the evidence case for body→PDF rendering. User is mid feedback-run with
the April kit; all Lovable prompts pasted (publish state unconfirmed).
Brisken platform ops status: unknown plan (no `platform` section in
infrastructure.yaml — orchestrator is FastAPI/Fly, not applicable).
p2 status files stale 29-61d (not this session's scope; needs a p2
session sweep).

---

## Next Steps

1. Harvest the user's feedback run: `GET /feedback.jsonl` notes +
   run diff → triage into p1-improvement-backlog → next build round.
2. Body→PDF rendering round (Dirk's held mail is the test case).
3. Owner actions pending: run the Access Policy runbook, distribute the
   vault codes (criss/matthias), announce receipts@expenses.brisken.com,
   confirm Lovable publish.
4. On Criss's July run: pull run down, field diff + double-click notes.
5. p2 status-file staleness sweep in the next p2-scoped session.

---

## Context for Next Session

### Files to Read First
- workspace/clients/brisken/status/p1-expense-reconciliation.md
- workspace/clients/brisken/status/p1-improvement-backlog.md

### Open Questions
- Is July closed in Zoho on Criss's side (walkthrough email fallback:
  newest open month)?
- Which vendors get multi_category flags (Criss)?
- Did the pasted Lovable prompts get published (merge ≠ live)?

### Working Notes
- Graph custom headers via sendMail MUST start with X-; Auto-Submitted
  cannot be set, X-Auto-Response-Suppress: All is the loop control and
  is honored org-internally (verified live on the ack).
- `GET /users/{mbx}/messages` spans folders: a sent-to-self ack shows
  twice (Sent Items + Inbox copies) — not a double send.
- flyctl sftp get on Windows: run with MSYS_NO_PATHCONV=1 and a
  relative local path; `flyctl ssh console -C` prints "The handle is
  invalid" after output on Windows — harmless, output already complete.
- Volume batches: April 7d2fea33d39a (37 receipts, no statement), May
  13b5605012f9 (27, reconciled), AGENT-DIAG 05d3db59b225 (test).
- Older log entries predate `documents` stamping and render without an
  expense list; only post-#553 mail carries the join.

### Reference Materials
- PRs #552, #553 (both merged 2026-08-21)
- docs/2026-08-21 - Brisken Mail Intake Live/Mini-Checkpoint-2.md

---

## How to Continue

`/comd_resume brisken` → read the two status files → check
feedback.jsonl for the user's run notes → triage → next round.

---

## Strategic Feedback

### What Worked Well This Session
- Owner-directive-to-live in one pass, twice: both PRs went build →
  adversarially-tested suite → green CI → deploy → live behavioral drill
  (real SMTP mail, Graph-read ack verification) inside the session, so
  "live" claims are all behavior-verified, not config-verified.

### Suggestions
- The B7 miss ("13 receipts is all") happened because a data-ceiling
  claim was made from one directory listing. A cheap structural aid: a
  `context/expense-reconciliation/README.md` one-liner mapping where
  month kits, volume batches, and loose samples live, so the next
  "what data do we have" question starts from the map, not a guess.

### System Health
- Autonomy: 3 human interventions (documents-intent correction; two
  pushbacks on the receipts ceiling). Elevated for a build session but
  all three were interpretation, not execution, failures.
- stop-b1-gate fired 3x on closing-text phrasing this session; two were
  choice-framing on the user's own manual run (arguably correct stops,
  rephrased), one was a real deferral (alias-editor re-prompt +
  checkpoint offer) that then got executed. The primer loop worked.
