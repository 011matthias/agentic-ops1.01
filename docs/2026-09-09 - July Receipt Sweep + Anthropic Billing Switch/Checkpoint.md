# Checkpoint: July Receipt Sweep + Anthropic Billing Switch

**Date:** 2026-09-09
**Status:** July receipt gap closed as far as our access allows; two owner-side unlocks remain

---

## Summary

Criss asked for the July 2026 receipts missing from the expense-recon tool. The
month went from 8 receipts to 32 (EUR 18,087.84 / USD 15,230.03) by pulling from
Zoho Expense, both Brisken mailboxes over Graph, and Matthias's personal iCloud.
Everything else we can reach was searched with a validated probe and is
exhausted; the rest sits behind a Zoho Expense account lockout and Criss's
mailbox.

---

## What Was Done This Session

### July receipt sweep

1. **Zoho Expense, 8 receipts.** Only 2 of 8 orgs are readable; CLOUD SERVICES
   held the German meal and supermarket photos (Brauhaus x2, Aposto x2,
   Enchilada, Lidl, Erste Fracht, Normandie Seine).
2. **Both Brisken mailboxes, 8 receipts.** 405 messages with attachments in the
   window across every folder and child folder, filtered to 46 receipt-shaped
   subjects, then read for card and amount before selecting. Google Workspace
   x2, Anthropic x3, GitHub, Eleven Labs, Network Solutions.
3. **Network Solutions arrived as HTML with no attachment**, rendered to PDF via
   Chrome headless. That whole class had been invisible to every prior scan.
4. **Matthias's iCloud + Outlook, 9 Anthropic receipts** from the billing switch
   forward, uploaded with no month override so the drop entrance routed each to
   its own month: 1 to June (batch it created itself), 6 to July, 2 to August.

### Sources ruled out, each with a working control

- **Zoho Books**: asked for the receipt *file* of all 111 July expense rows
  rather than reading `has_attachment`. 3 returned a file, 108 returned
  "Receipt not attached", and Hostinger ran as the control in the same pass and
  did return its file.
- **Books document inbox**, all 8 orgs: 46 July uploads, all AP bills.
- **SharePoint**, 11 ADMIN sites, 8,263 files inventoried: bank and card
  statements, no card receipts. The one July bundle
  (`ADMIN GMBH/10_Finance/40 07-2026.zip`) is the GmbH month-end pack.
- **Zoho Expense orgs**: re-probed endpoint by endpoint with CLOUD SERVICES and
  GmbH answering OK in the same run, so the 6018 lockout is proven, not assumed.

---

## Key Decisions Made

### Upload only what matches a charge or the July card

- **Choice:** Selected 7 of 52 downloaded mail attachments; the rest were
  reported, not uploaded.
- **Rationale:** An earlier load of 18 bank-transfer AP bills had to be removed
  from the July grid. A receipt with no matching charge is noise in a
  reconciliation view.

### Hold back the three pre-switch Anthropic receipts

- **Choice:** 04-23 and 05-23 (personal Mastercard 3964) and 06-05 (Karlsruhe
  personal billing address) stay out. Owner confirmed via AskUserQuestion.
- **Rationale:** Booking personal spend as a Brisken expense is the exact error
  the reconciliation exists to catch.

### Correct the EUR claim rather than leave it standing

- **Choice:** Reversed the "Anthropic 214.20 was read as EUR and is USD" line in
  both the status file and the client-facing README.
- **Rationale:** Anthropic denominates the subscription in euro and usage
  credits in dollars. The tool was right; the note would have sent Criss hunting
  a bug that does not exist.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit x2 | Sweep record, then the EUR correction |
| `workspace/clients/brisken/context/zoho-receipts-july-2026/README-july-receipt-gap.md` | rewrite + correct | Source-by-source map for Criss, replacing the "not collected" guess |
| `.../zoho-receipts-july-2026/uploaded-2026-09-09/` | add 21 files | Byte-verified copies of every uploaded receipt |
| `workspace/clients/brisken/context/.env` | append | `ZOHO_EXPENSE_REFRESH_TOKEN` (gitignored) |

Live state, not files: July batch `50622baec444` 8 to 32 receipts; June batch
`a5f97a85b1d0` created; August `074a7b8905d7` 29 to 31.

---

## Current Status

PRs #772 and #773 merged, main clean. brisken platform: unknown plan, last
assessed unrecorded; comms-log 1 day old.

Ten of the twenty July Anthropic charges now have a receipt. About 93 of the
original 109 chase rows are still uncovered, and both remaining routes need a
human with admin rights.

---

## Next Steps

1. **Zoho Expense admin enables our API user** in BRISKEN, LLC (Corporate
   Services) and BRISKEN Tech LTDA. Corporate Services holds 107 of the 108 July
   charges; Tech LTDA is the Brazilian spend. The download-and-upload path is
   proven end to end by the eight from Cloud Services.
2. **Decide Criss's mailbox**: widen the Graph allowlist to
   `Cristiane.Cavalcanti@brisken.com`, or have her forward July into the tool's
   mail intake. Ten vendors (Lovable, Perplexity, OpenRouter, Supabase, Vercel,
   Resend, Adobe, Wix, SaaS Rise, PressMaster) send only to her.
3. **Normandie Seine row** needs a human glance: no date, reads 6.60 where Zoho
   Expense records 2026-07-05 / 6.00.
4. **Two July set-aside items** still need one Restore click each (AWS 3,352.59
   USD, Rodrigo Tanure 5,364.00 USD).
5. **Rotate whatever `tok.txt` holds** and delete the two branches carrying it.
6. Refresh four stale p2 status files (48 to 80 days): `p2-lead-gen-general`,
   `p2-product-decks`, `p2-rome`, `p2-targeting`.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/zoho-receipts-july-2026/README-july-receipt-gap.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Will the Expense lockout be lifted, or do the ~40 photographed receipts have
  to come out by hand?
- Does widening the Graph allowlist to Criss need Dirk's sign-off, or is it ours
  to make?

### Working Notes

**The probes that mattered, and why.** Every "it is not there" verdict this
session was re-tested against a case whose answer was already known, because the
first pass got two of them wrong. Books `has_attachment` agreed with the file
endpoint in the end (3 and 3), but that was luck: the flag was never evidence.
The Zoho Expense 6018 is real and uniform across `/expenses`,
`/expensereports`, `/users/me` and `/trips`, with two orgs answering normally in
the same run.

**The Zoho Expense `date` field is the filing date, not the transaction date.**
Late-filed August rows (OpenAI, Microsoft, Eleven Labs) look like July
candidates until the PDF is read; all of them turned out genuinely August
(Microsoft G177387448 is dated 08/11). Widening the window to 2026-06-20 through
2026-08-10 pulled 76 receipts, of which only the same 8 were July.

**Anthropic bills in two currencies**, which is not a bug: subscription in euro
(107.10, 147.18, 180.00, 214.20 EUR), usage credits in dollars. EUR 214.20 is
the 245.19 USD posting; EUR 180.00 is the 206.32.

**Where the receipts actually go.** Dirk forwards to
`Cristiane.Cavalcanti@brisken.com`; GitHub and Regus bill her directly. That one
`toRecipients` read explained the whole 59-charge gap.

**Scripts worth reusing** (all in `.scratch/`, ephemeral):
`recon-july/graph_receipt_pull.py` (mailbox sweep, scan or download),
`recon-july/books_receipts.py` (per-expense receipt probe with control),
`recon-july/ze_wide.py` (Expense pull), `anthropic-receipts/pull_anthropic.py`
(iCloud IMAP + Graph).

### Reference Materials
- July batch `50622baec444`, June `a5f97a85b1d0`, August `074a7b8905d7`
- `https://api.expenses.brisken.com`, operator code in `context/.env`

---

## How to Continue

The mechanical work is done and shipped. Next session is unblocking, not
building: chase the Expense org enablement and the Criss mailbox decision. If
either lands, the pull scripts above run as-is against the newly readable
source.

---

## Strategic Feedback

### What Worked Well This Session
- Re-testing every negative against a known-good control. The Books probe, the
  Expense org probe and the currency check each changed or confirmed a claim
  that would otherwise have shipped on assumption.
- Reading the card last-4 and billing address off the PDFs turned "May or June"
  into a dated, evidenced switch, which made the include/exclude line defensible
  instead of arbitrary.

### Suggestions
- The instrument-validity sub-clause already exists in `rule_behaviors`, and it
  still did not fire on the `has_attachment` flag or the metadata-only mailbox
  scan. The gap is that both felt like reads rather than probes. Worth adding a
  named trigger: **any negative that closes a search** gets a control, not just
  API filters and endpoints.

### System Health
- Autonomy: 2 human interventions. One was a correction that materially changed
  the outcome ("try harder"), which is the expensive kind.
- The `.scratch/recon-july` tree now holds 30+ one-off scripts and 25 MB of JSON
  dumps. It is gitignored so it costs nothing in the repo, but W1 §2 says print
  the finding rather than save the dump; several of these were saved because the
  next script needed them, which is legitimate, and several were not.
