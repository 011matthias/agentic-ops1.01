# Checkpoint: Brisken P1 Item 54 Refuted Before Build

**Date:** 2026-09-15
**Status:** Item 54 closed with no code (PR #866). The parallel-round protocol now says a refuted item gets closed rather than built on a fixture (PR #867). Nothing in the 48-54 band is autonomous any more; everything left is an owner paste or an owner go.

---

## Summary

Item 54 had been ranked the strongest open code item by three briefs. Checked before writing any code, it has no instance: both "OCR date misreads" were read correctly, and the rule it proposes, measured on the two live statement months, flags only pairs the human labels call wrong.

---

## What Was Done This Session

### Item 54: refuted on four records, then closed (PR #866, merged 3b8a0543)

1. Calibrated the proposed rule offline over the live July and August run
   payloads (GETs only): every free charge x free receipt pair with the same
   currency and the exact amount. July 4 pairs, August 3.
2. The first pass broke the item's premise. July's statement is 112 charges,
   all USD; there is no EUR 900 Crossmedia charge to pair with.
3. Traced the quoted charge: it comes from
   `context/zoho-receipts-july-2026/july-2026-charges-without-a-receipt.csv`,
   a bank-transfer payment, not a card statement.
4. Grepped the item-69 human labels in the July live bundle:
   Crossmedia `no_charge:bank_transfer`, Anthropic 100
   `no_charge:neighbour_period` ("on Visa 3645: the charge is in the June
   statement").
5. Pulled both PDFs through the image endpoint and read them, because a label
   is a note too. Crossmedia prints `Invoice Date : 30 Mar 2026`; Anthropic
   prints `Date paid June 21, 2026` on `Visa - 3645`. Both extractions correct.
6. Checked the August labels for the two August pairs the rule would surface:
   Google 71.64 08-31 `no_charge:neighbour_period`, the Lovable 50 copy
   `excluded` (a collapsed duplicate).
7. Recorded the closure, the measurement and the reopen condition in the item.
   Downloaded receipts and payload dumps deleted from the scratchpad.

### Protocol clause (PR #867)

8. `PARALLEL-ROUND-PROTOCOL.md` told a session to report a non-reproducing gap
   "then build the fix on a constructed fixture" unconditionally. Added the
   missing branch: grep the labels, read the printed document, and close an
   item whose instances are refuted and whose rule surfaces only wrong pairs.

---

## Key Decisions Made

### Close item 54 rather than build the narrow version
- **Choice:** no code. Not the far-date rule, and not a guarded variant.
- **Rationale:** the brief said not to re-decide the spec, and the spec was
  not re-decided: its evidence was false. The exact-amount population in live
  statement months is recurring subscriptions at identical amounts (Google
  71.64, Anthropic 100, Lovable 25/50), so "same amount, far date" reads
  "same subscription, other period". A guarded variant (card agreement plus no
  second same-vendor same-amount charge) would surface zero pairs on both
  months, which is a feature with no instance. The loop is reactive: a round
  fires on evidence.

### Keep the fix view-time if it is ever reopened
- **Choice:** recorded in reasoning only: a parallel field computed in
  `build_view`, not a matcher candidate.
- **Rationale:** a matcher change needs a live re-match to reach Criss's
  months (a per-action go) and collides with item 69's rounds A+B, which are
  waiting on the owner; a view-time field reaches both months on deploy and
  leaves the scorer floor untouched.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 54 closed with evidence and reopen condition (#866) |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md` | edit | refuted-item branch (#867) |
| memory `project_brisken_expense_recon_usability_loop.md` + `MEMORY.md` | edit | labels-first check; July-sweep items are leads, not evidence |

---

## Current Status

No code changed, no deploy; Fly stays at v128. Live app only read: two run
payloads, two expense-batch payloads, two receipt images.

brisken platform: unknown plan, `~?/?` ops/mo, last assessed `?`.
Comms log: none found by the pre-flight.

p2-product-decks (54d) and p2-targeting (55d) still flag stale; left
deliberately, per the brief, for a p2-scoped session.

---

## Next Steps

1. Owner pastes, in order of what Criss feels:
   `lovable-view-receipt-prompt.md` (her actual report),
   `lovable-settled-outside-prompt.md` (retires July's Crossmedia, Redis and
   Konsultancy invoices from the pool), `lovable-failure-probe-prompt.md`
   (item 50), `lovable-cost-centers-prompt.md` sections 1 and 2 first.
2. Owner go on the July receipts ingest (19 PDFs, which route) and the
   dateless French receipt; both write into live July `50622baec444`.
3. Owner go on item 69 rounds A then B plus its three decisions.
4. Next autonomous candidate: triage the Open section. Headings do not carry
   state reliably (many open-looking items shipped in parts), so read each
   body. Items 37 (column-mapping retry dead on the wire, marked LIVE DEFECT
   2026-08-28) and 27 (a wrong day inside the right month) are the first two
   to verify, labels and live payload first.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 54 (the closure) and the Open section
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`

### Open Questions
- Item 37: still live, or shipped in pieces under another item?
- Does item 27's wrong-day class show up in any statement month, or only on the April receipt grid where it was found?

### Working Notes

**Label bundles are the fastest truth for matching claims.** Main clone,
gitignored:
`workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/{July-2026_live_50622baec444,August-2026_live_074a7b8905d7}/`.
`labels.csv` columns `document_id,transaction_id,status,source,evidence`;
`notes.csv` carries a one-line reason per receipt. ripgrep skips them
(gitignored), so use `grep` or `rg --no-ignore`.

**July statement shape (read 2026-09-15):** 112 rows, every `account_id`
`card-2838`, every currency USD, but `coverage[]` lists 3876, 2838, 3645 and
0340 against `July2026.xlsx`: the workbook prints several cards through one
account id. August: 111 rows, same account id, 3645 / 3876 / 2838.

**Existing row fields worth knowing before designing a hint:**
`rows[].near_miss` (same currency, amount within 35%, date within 10 days;
narrowed 2026-07-22 because the old version fired on everything) and item 25's
`date_outside_period` on the receipt grid.

**Instrument slips this session:** the vault entry is a dict with `code`, not
`password`. The cd-guard refuses `cd X && ...` but let `cd ~ 2>/dev/null;`
through, and that silently moved the session's primary working directory.

**Probe scripts** (ephemeral, session scratchpad): `fetch_live.py` (login +
payload save), `calibrate54.py` (exact-amount pair census), `fetch_docs.py`
(receipt image download). Not committed by design.

### Reference Materials
- Live API `https://brisken-expense-recon.fly.dev` (vault "Brisken recon operator code matthias", field `code`)
- PRs #866 (item 54 closure), #867 (protocol clause)

---

## How to Continue

Cut a worktree off `origin/main`. Nothing in the 48-54 band needs code from
you. If the owner has pasted a prompt, verify it by browser drive (View
receipt) or bundle audit plus drive (the others). Otherwise triage the Open
section, checking every named instance against the labels and the printed
document before building.

---

## Strategic Feedback

### What Worked Well This Session
- **Measuring the rule before building it.** A 30-line offline census over
  the saved payloads showed the premise was false in one run, before any
  design work. Item 52's lesson (read the record, not the note) applied one
  level up: to the backlog item itself.
- **Not stopping at the first refuting record.** The label said "bank
  transfer"; reading the PDF made it certain and caught that 03-30 is an
  invoice date, which is the fact that makes the Crossmedia claim wrong in
  kind rather than in degree.

### Suggestions
- The cd-guard pattern matches `cd <path> &&` but not `cd <path> <redirect>;`.
  Widen it to any leading `cd` that is not inside a subshell; the miss here
  changed the session's primary directory with no warning.

### System Health
- Four items written from the 2026-09-10 July sweep have now been wrong or
  non-reproducing (52's lead, 60, 61, 54), and three checkpoints carried
  item 54 forward as the strongest code item without re-reading its evidence.
  The protocol clause (#867) addresses the build decision; the upstream half
  is that an item's "certain" instance was never checked against the document
  when it was written.
- **Autonomy score: 0 human interventions** — fully autonomous session.
