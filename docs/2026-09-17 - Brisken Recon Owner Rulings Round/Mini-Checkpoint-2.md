# Mini-Checkpoint: Brisken Recon Owner Rulings Round

**Date:** 2026-09-17
**Status:** All eight owner questions answered and acted on; five PRs merged and deployed (Fly v175); five Lovable prompts wait on the owner's paste

---

## Summary

The notes #65-#69 queue was already claimed by a sibling session (worktree cut five minutes before this session read it), so this session put the nine open owner/Criss questions to the owner as plain-language choices instead, then executed every ruling. Two live changes, four builds merged and deployed, and one verification-integrity bug in the repo's own tooling fixed on the way.

## What Was Done

**The rulings (owner, via AskUserQuestion, in his words):**

- Item 1 / backlog 140, duplicates: "duplicates should be shown next to each other for easier comparison" -> build. Prompt written, PR #1046.
- Item 2 / note #61, Account picks: remove the box. PR #1044, deployed.
- Item 3 / backlog 105, the two July invoices: "you move them to where they belong, no need for manual work here" -> restored live.
- Item 6 / backlog 121, alerts: Criss + Matthias. One settings write.
- Item 8 / backlog 138, cost centers: cards inside cost centers. PR #1043.
- Item 9 / backlog 138, month page: build now. PR #1049, backend deployed; SPA waits on the paste.
- Company on the two restored invoices: left to Criss (a second question, after the permission classifier refused the write as outside the restore order).
- Items 4 (June refresh), 5 (Pressmaster 96.00) and 7 (LOVABLE cards differ) needed no decision: Criss's clicks, and 5 was already done by her.

**Live changes on the owner's order (July, Criss's month):** AWS USD 3,352.59 and Tricarico BRL 27,203.34 restored from the set-aside list; Tricarico recorded `settled_outside {how: bank_transfer}` because the invoice prints "Payment Method: Wire Transfer". `intake.alert_recipients` set to Criss + Matthias, every other intake key verified unchanged.

**Merged and deployed:** #1042 (rulings recorded), #1043 (cards inside cost centers), #1044 (Account picks gone), #1046 (compare-copies prompt), #1049 (card_sections backend), #1052 (both PDFs fit A4), #1055 (regress_check CRLF), #1058 (em-dashes out of the PDFs). Fly v168 -> v175.

**Found and fixed on the way:**

- Both PDFs drew tables wider than the printable A4 width (month listing 732 pt, charge table 672 pt against a 503.9 pt frame), so columns were cut off the paper on every month report since item 24. Now 503 pt, portrait, no column dropped (backlog item 143).
- `tools/regress_check.py` wrote mutated sources with `write_text` on a CRLF checkout, doubling every line ending; 15 of 185 `tools/` files then stopped parsing, so pytest went red at collection and the tool printed TEST BITES. Every Windows regress proof recorded before PR #1055 proves nothing.
- The PDFs printed em-dashes in their titles ("Reconciliation — August 2026"), banned by rule_deliverables (backlog item 145).

## What Did NOT Work (and why)

- **Setting the company on the two restored invoices:** the permission classifier refused the write, correctly: the owner ordered a restore, not a company change. Asked instead; he left it to Criss.
- **Playwright login by filling the first `input` right after `domcontentloaded`:** the gate had not hydrated, so `erc-token` never appeared and the drive timed out at 30 s. Wait for `networkidle` plus 2 s, then fill `input[type=password]`.
- **`pypdf` `visitor_text` `tm[4]` as a column-extent check:** returned 0.0 on most pages, so it proved nothing about clipping. Rasterize and look at the page instead.

## Current Status

Fly v175 is live and carries every merge above. July now holds 52 expenses (2 set aside, 1 settled outside). August's `card_sections` read 3645/3876/2838/1176/9693/No card and add up to the page totals (20 expenses, EUR 668.00, USD 2,033.86). The live August reconciliation report is 75 pages with every table inside the page edges and zero em-dashes. platform: unknown plan, ~?/? ops/mo, last assessed ?.

One July row moved that nothing confirmed: the 2026-07-12 NOBRE ATACAREJO USD 65.23 charge on 3876 (yellow, already booked) dropped from `review` to `unmatched`, so Supermercado Fenix `0059__20260711` is now a receipt without a charge. The two restored receipts had no candidate near that amount, so the likelier cause is that July had not been re-matched since today's matcher deploys; unverified.

## Next Steps

1. Paste the five waiting Lovable prompts from this round: `lovable-card-tabs-prompt.md`, `lovable-duplicates-side-by-side-prompt.md`, `lovable-remove-account-picks-prompt.md` (plus the sibling round's `lovable-private-card-in-picker-prompt.md`, `lovable-one-download-each-prompt.md`, `lovable-booked-hint-names-workbook-prompt.md`), then run each prompt's bundle audit and cold drive.
2. Re-run any regress proof that was recorded on Windows before PR #1055 and mattered.
3. Decide whether the 65.23 / Fenix pairing is a matcher defect worth an item, once someone re-matches a month deliberately.
4. Criss: restore-company on the two July invoices, the "refresh master data" click on June, and her call on August's LOVABLE 25.00 cards-differ row.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 105, 121, 138, 140, 143, 145
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied table, 12 rows)
- `tools/regress_check.py` (the CRLF fix and the new BROKEN MUTATION / UNATTRIBUTED verdicts)
