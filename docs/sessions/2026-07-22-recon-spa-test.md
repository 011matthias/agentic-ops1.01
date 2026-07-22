# 2026-07-22 — Brisken expense-recon: first hands-on SPA test (end to end, as Criss)

Scope: brisken p1 · session `brisken--recon-spa-first-hands-on-test`
Surface tested: `brisken-reconcile-dash.lovable.app` (SPA) against Fly v33 API-only backend.
Data: Criss's real April 2026 artifacts from the labelled month-bundle
(`Chase2838_Activity20260401_20260430_20260716.CSV` + `ER-00215-criss-upload.pdf`,
gitignored context). Full flow driven through the real UI: login → upload → run →
review (reject/confirm/search/expand) → disposition → duplicate resolve → all 3
exports. Publish left unexercised (gate requires all 94 rows decided; see F1).
Test run: `8074aa2bf7d9` ("2838 2026-07-22"), unpublished, left in place — no
delete-run control exists (F9). No fixes applied mid-test by design.

Run outcome (source: `GET /api/runs/8074aa2bf7d9` summary): 94 transactions,
36 receipts, 0 auto-reconciled, 34 review, 60 unmatched tx, 2 unmatched receipts,
6 "parse errors", 1 duplicate group, refunds 0, LLM cost $0.2254, invariant OK,
`has_coa: false`, `writeback_available: false`. Header chip: "Blocked · MATCH RATE 0.0%".

## (a) Bugs

- **B1 — Hosted matching config gap: 0 auto-reconciled on data that local no-LLM
  reconciles 29/36.** All three dashboard runs (mine, Criss's 07-20, the 07-21
  134-tx run) show 0 matched / 0.0%. The local loop on identical files gets 20
  clean + 9 review via the FX reference-rate path (`match-tuning-tier1.json`),
  which the hosted run never loads; Chase CSV has no PDF FX originals, so every
  BRL/EUR receipt degrades to DCC-band/LLM candidates (best 85%, most 10-30%).
  The $0.23 LLM pass only produced review-grade candidates. Criss's read: "it
  matches nothing."
- **B2 — COA layer silently disengaged (`has_coa: false`).** Card id "2838" (the
  natural thing to type) doesn't resolve to a provisioned entity, so the COA gate
  never engages: export shows `(uncategorized - assign)`, balancing line says
  `card account unmapped`, `zoho_account` = generic 8-category labels. No warning
  anywhere that COA mapping is absent. `/data/cards.json` still unauthored.
- **B3 — Zoho journal exports receipt-currency amounts unconverted.** The one
  confirmed FX match (9.18 USD charge ↔ 47.50 BRL receipt) exports BRL line items
  into the USD journal: debits sum 46.00 + credit "Card: 2838" 46.00. Imported
  as-is → posts ~5x the true amount. Also two 0.00-debit junk lines, line sum
  46.00 ≠ printed receipt total 47.50, Reference# = internal tid `2838:91`.
- **B4 — First-visit coach-mark blocks the Actions column.** The "Leave feedback
  anywhere" popover sits over Disposition + Confirm/Reject on the first rows;
  clicks silently die until "Got it" (reproduced: two Reject clicks no-oped).
  The "Edit with Lovable" badge also overlaps the expanded row's Reclassify
  control — and ships on the production client URL at all.
- **B5 — Contradictory row signals.** "NEAR MISS" chip on rows with "No
  candidates" (ANTHROPIC, GOOGLE). Expanded FX panel shows "Card 100%" while its
  own text says "the card numbers do not match" (neutral-when-absent rendered as
  100%?).
- **B6 — "Confirm all matched" is a silent no-op** when nothing is auto-matched
  (fires POST, no dialog, no "0 rows confirmed" feedback) — and conversely has no
  confirmation prompt for when it WOULD bulk-confirm.
- **B7 — "6 parse errors" mislabels severity**: 1 is an informational
  sign-convention note (parser did the right thing), 5 are unattached receipt
  images. Nothing is an error in the user's sense.

## (b) Friction

- **F1 — Publish = decide the 34 review rows one by one, with no bulk action.**
  CORRECTED during the fix pass (this entry first claimed all 94 rows).
  `n_undecided` counts only rows the tool is HOLDING A RECEIPT for (effective
  bucket reconciled or review) that are still pending: 34 on this run, matching
  `n_review` 34. The 60 receiptless unmatched rows do NOT block publish, so the
  real cost is ~34 decisions per month, not ~90. Still no bulk path, and the
  Guide's "when every charge is decided" wording is what made the wider reading
  plausible. Backend half fixed by PR #395 (bulk confirm/reject over a named set).
- **F2 — "Blocked" chip is inert.** No click-through to what blocks; only hint is
  the disabled Publish button's hover title ("Resolve the blockers above").
- **F3 — In-flight runs are invisible.** The processing page invites leaving the
  tab, but the run appears NOWHERE (no dashboard row) until complete. Re-opening
  mid-run looks like the upload vanished → invites re-upload.
- **F4 — Processing shows internal stage tokens** ("receipt-images",
  "categorizing", "judging"), no progress/ETA (~4 min total with AI on).
- **F5 — Confirmed FX match immediately wears a red "AMOUNT MISMATCH" chip** —
  the normal cross-currency case gets flagged after she does the right thing.
- **F6 — Dead-feeling controls on candidate-less rows**: Reject enabled (rejecting
  what?), Confirm disabled, disposition silently defaults "Business".
- **F7 — English-only UI** for a PT-speaking key user (old HTML UI was EN/PT);
  long English FX rationales.
- **F8 — Start button below the fold** on a laptop-height viewport; nothing
  anchors/stickies the submit.
- **F9 — Run labels are opaque + no rename/delete.** "2838 2026-07-22" vs "2838
  2026-07-20": her April run and my test run are distinguishable only by created
  date; a botched/test run lives on the dashboard forever.
- **F10 — Receipts-source dropdown defaults CSV** while her artifact is the ER
  PDF (backend sniffs .pdf anyway, so it's misleading rather than harmful).

## (c) Gaps vs how Criss actually works

- **G1 — Production memory is empty.** Memory page: no learned categories, no
  aliases, no FX. The Zoho posting-history seed (`memory seed-zoho`) never ran
  hosted → ANTHROPIC categorizes to generic "Software & Subscriptions"
  (LLM VENDOR guess) instead of the standing "Other Infra and IT Costs for Cloud
  Business" (Nicolas's instruction, her tip #2). `is_learned: false` everywhere.
- **G2 — The fill-color channel can't reach the tool via the flow she was shown.**
  Chase CSV carries no colors; `n_already_posted` 0, `n_subscription` 0. The
  xlsx color-ingest + writeback path exists (PR #228) but nothing in the UI says
  "upload your per-card xlsx and you get posted-row skip + your own sheet back".
  `writeback_available: false` on CSV runs — her pictured output (her sheet with
  column E rewritten) is unreachable from the artifact she uploads; the 37-column
  reconciled.csv is not her sheet.
- **G3 — Receiptless subscriptions (her core pain) get the worst UX**: 60 rows,
  "No candidates" + NEAR MISS noise + generic category + per-row decisions, no
  "recurring subscription" concept in the CSV flow.
- **G4 — Zoho Expense pull is still manual glue** (download ER PDF, upload here) —
  Dirk note #3 confirmed as a real gap; receipts already live in Zoho Expense.
- **G5 — Dirk's 4 notes, evidence-checked**: (ii) settings/master-data CONFIRMED —
  Settings holds only the export-approved toggle + memory wipe; no cards, COA,
  FX rates; B2 shows master-data absence causes real correctness holes, not just
  preference. (iii) auto-pull CONFIRMED (G4). (i) "flow is backwards" NUANCED:
  statement-first matches her own truth-source, but her working object is the
  per-card lifetime sheet, not a raw bank export. (iv) "spec not reflected"
  gains evidence: publish gate/disposition/duplicates exist, but memory seed,
  master data, writeback are absent from the tested flow. Spec-vs-build
  reconciliation (already chosen next step) stands.

## What held up

Upload→run→review loop is solid; stage feedback exists; search/filter instant;
expanded-row FX rationale is genuinely good; reject/confirm/disposition/duplicate
decisions all persist correctly (verified via API after each UI action); all 3
exports 200 with correct content types; invariant holds; login throttle produced
zero false positives across 3 successful logins; feedback widget everywhere.

## Session notes

- Notifier safety pre-checked: `EXPENSE_RECON_NOTIFY_USER` unset (user/machine/
  proc) → publish pings could only reach the dev inbox. Criss cannot be emailed
  by this test.
- Agent friction (own): default agent-browser session got hijacked mid-poll by a
  sibling Claude session (tab navigated to apollo.io). Recovered in a named
  `--session recon-test`. Rule of thumb going forward: ALWAYS use a named
  agent-browser session when siblings are live (feedback_worktree analog for
  browser state).
- Screenshots in session scratchpad (`recon-test/01..06*.png`), ephemeral.

## Fix pass (same day, PR #395 merged)

Backend, all verified against the same real April files:

- **B1 fixed + PROVEN.** Master data (`fx_reference_rates`, `card_entities`,
  `card_accounts`) now lives in stored settings, is applied at run creation and
  snapshotted into the run config; the CLI accepts inline `matching` tunables so
  the rates reach the matcher AND land in `run.local.json`. Proof: the real April
  pair now reconciles **29/36 (30.9%)**, up from 0, with rates passed inline the
  way the hosted surface passes them.
- **B2 fixed.** Entity resolves from `card_entities` (matching on trailing
  digits, so a typed `2838` works), and an unresolved chart now says so.
- **B3 fixed.** The journal posts in the STATEMENT currency: the charged amount
  is allocated across the receipt's lines, so debits equal the bank's number to
  the cent. Zero-value debit rows dropped; the receipt's own figure kept in Notes.
- **B5 / B7 fixed.** Near-miss requires actual nearness; parse issues carry their
  severity, so an advisory note is no longer counted or coloured as an error.
- **F1 backend half fixed.** `POST /api/runs/{id}/decisions/bulk`.
- **Latent bug found while fixing:** `statement_advisory` was written at run
  creation but never rebuilt in `build_view`, so it had never once reached the
  review screen. Now carried.

Suite 758 green (was 727); `calibrate` exit 0, invariant OK.

Still open: the SPA half (overlay swallowing clicks, inert Blocked chip, no bulk
UI, no settings screen for the new master data, EN-only), G1 memory seed, G2
xlsx/writeback discoverability, and the spec-vs-build reconciliation.
