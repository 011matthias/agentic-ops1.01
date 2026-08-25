# Mini-Checkpoint: Brisken Mail Intake Live

**Date:** 2026-08-21
**Status:** Mail intake LIVE end-to-end; UI verified; loop back to reactive
**Type:** mini

---

## Summary

The p1 mail intake (`any-name@expenses.brisken.com`) is live and proven at
every hop: PR #548 deployed, dedicated IPv4 149.248.221.114, MX/SPF/DMARC
public, security drill PASS (relay 550 / spoof 550 / allowlisted 250),
M365→MX delivery proven with one authorized Graph send (9s mail-to-ingest),
and the published Lovable UI verified live (submitted-by chip, Email intake
settings section, held strip absent at n_held 0).

## What Was Done

- Verified the published Lovable mail-intake UI via agent-browser: chip
  "From: matthias.silva@brisken.com" on the injected TEST row in batch
  05d3db59b225; Settings shows "Email intake" (domain line + accepted-senders
  editor); no held strip.
- Gap found: Lovable skipped the aliases editor from the prompt. Closed via
  API instead: `PUT /api/settings` intake.aliases = dirk→Dirk Neumann,
  criss→Cristiane Cavalcanti, matthias→Matthias Silva (read-back verified).
- Cleanup: TEST ui-probe receipt deleted (batch back to 10 rows), browser
  session closed. Inbound log keeps 3 test mails as `ingested` custody
  records by design.
- Ledger: status-LIVE PR #549 merged 09:24Z; memory
  `project_brisken_expense_recon_mail_intake` updated to fully-proven state.

## Current Status

p1 receipt-first loop reactive; mail intake operational awaiting first real
faculty mail. Criss's July run still pending (walkthrough email sent
2026-08-19). Sender allowlist = default @brisken.com; aliases configured.

## Next Steps

1. On first real inbound faculty mail: confirm ingest + submitted_by, then
   watch for held_body_only (Uber-style forwards) → round 2 = body→PDF
   rendering.
2. On Criss's July run: pull run down, field diff + triage double-click
   notes → next loop round.
3. Owner decisions outstanding: retention/system-of-record ruling, auto-ack
   carve-out, Zoho export person column, faculty announcement of
   receipts@expenses.brisken.com.
4. Optional Lovable re-prompt: add the aliases editor to Settings (one
   line; functionally not needed — API path works).

## Files to Read First

- workspace/clients/brisken/status/p1-expense-reconciliation.md
- docs/lovable-mail-intake-prompt.md
