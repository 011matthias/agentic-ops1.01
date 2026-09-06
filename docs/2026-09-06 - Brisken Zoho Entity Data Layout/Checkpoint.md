# Checkpoint: Brisken Zoho Entity Data Layout

**Date:** 2026-09-06
**Status:** Enumeration + incorporation plan delivered; owner-side data entry pending

---

## Summary

Read-only live enumeration of Brisken's Zoho Books for the expense-recon
tool: laid out the 8 legal entities (3 actively booking), answered 4 of the
5 open card-entity gaps (backlog item 26) from the chart of accounts, and
recommended a 4-move incorporation plan that keeps the no-Zoho-ties ruling
intact (data crosses once into app settings; no connection).

---

## What Was Done This Session

### Enumeration (all read-only, verified live)
1. Queried Zoho Books via fresh probe (`.scratch/zoho_books_probe.py`):
   org roster, per-org chart of accounts, bank/credit-card accounts,
   currencies, taxes, expense/bill recency + top vendors.
2. Cross-checked the live app (`GET /api/cards`, `GET /api/settings`):
   registry still has 5 cards with only 2838 entity-set; `entity_options`
   = Cloud Services + Corporate Services.
3. Wrote the full mapping to gitignored
   `workspace/clients/brisken/context/expense-reconciliation/zoho-entity-card-map.md`
   (entities, card->entity fills, seed sources) so nothing is re-derived.

### Recommendation (delivered in conversation)
1. Four incorporation moves, ranked: card-entity data entry (now, free);
   Consulting-entity question; optional merchant-memory re-seed; account-list
   rename gated on the GL-codes-vs-categories decision.

---

## Key Decisions Made

### Incorporation = one-time data crossing, never a connection
- **Choice:** All Zoho value enters as plain operator data in app settings;
  item 23 (no Zoho ties) stays fully intact.
- **Rationale:** Layer 3's own framing ("validate against the operator's
  account list") anticipates exactly this; the owner ruling bans connection,
  not knowledge.

### Report altitude (owner correction)
- **Choice:** Owner-facing layouts carry entity/card names and actions only;
  raw identifiers (org_ids etc.) live in the context reference file.
- **Rationale:** Owner: "i dont want any org id or that type of hyper
  specific data that brings no value." Extended
  `feedback_reviews_in_plain_language` to cover data layouts.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/expense-reconciliation/zoho-entity-card-map.md` | Created (gitignored) | Entity roster + card->entity map + seed sources; the re-derivation killer |
| `.scratch/zoho_books_probe.py` | Created (gitignored) | Reusable read-only Books probe (orgs/COA/expenses/bills) |
| memory `feedback_reviews_in_plain_language.md` | Updated | Data-layout altitude extension (2026-09-06 correction) |

---

## Current Status

Entities: 3 of 8 orgs actively booking (Corporate Services, Cloud Services,
Consulting); tool knows the first two. Card registry: 4 of 5 blanks
answerable from Zoho (0113 -> Corporate Services; 6013/9693/8311 -> Cloud
Services); 0340 + 3645 unresolvable from Zoho (need Criss/Dirk). All app
writes are owner-side (session sandboxed from live-app mutations).
Ops status: platform plan/volume unknown per `infrastructure.yaml` (line
from pre-flight; no orchestrator platform section for the Fly app).

---

## Next Steps

1. Owner: enter the four card entities in the cards editor (values in the
   context map file / this checkpoint).
2. Ask Criss/Dirk: 0340 + 3645 identity; whether Consulting's cards
   (Wise 1160, Chase 1176) are ever in recon scope.
3. Owner/Criss table question (already in backlog item 23): GL codes in the
   monthly documents, or categories only — decides layers 2-4 scope.
4. Optional, opportunistic: merchant-memory re-seed with newer posting
   history (+ Consulting if added); local pull -> replay path, no app code.
5. p2 status files are 22-77d stale (7 files flagged by pre-flight) — needs
   a lead-gen session sweep, out of this session's scope.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/expense-reconciliation/zoho-entity-card-map.md`
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 23 + 26)

### Open Questions
- Does Criss's recon ever cover Consulting cards? (gates provisioning a third entity)
- GL codes vs categories-only in the monthly documents (gates item 23 layers 2-4)
- 0340 / 3645 card identity (not in any Zoho org's chart)

### Working Notes
- Zoho Books scopes verified working today: accountants.READ, settings.READ,
  expenses.READ, bills.READ. No contacts.READ (vendor module unreadable;
  vendor names come off expense/bill rows — sufficient).
- Corporate Services posting history is current through today; Consulting
  through 2026-08-05 (bills 2026-08-30); GmbH dormant since 2024-12;
  Tech LTDA dead since 2021; Holding/DN/TEST empty or near-empty.
- Bank accounts + tax rates judged NOT worth incorporating (journal export
  lost its destination with output-is-a-document; only dormant GmbH has taxes).
- FX rates: no usable feed under current scopes; stays operator input.
- Deliberately skipped: p1 status-file bump (no element changed state;
  enumeration only, and ledger edits ride a docs PR while client files
  belong on client branches).

### Reference Materials
- Memory: `project_brisken_zoho_books`, `project_brisken_expense_recon_master_data`,
  `project_brisken_expense_recon_usability_loop`

---

## How to Continue

`/resume brisken`, read the context map file, then hand the owner the card
entity values if not yet entered; any build work follows the p1 loop brief
(fresh worktree, B6 bands).

---

## Strategic Feedback

### What Worked Well This Session
- Enumerate-before-propose (B7/E1) end to end: live Zoho + live app registry
  queried before any recommendation, so the item-26 answer is grounded, not
  remembered — and the 13-day-old memory's gap list turned out still current.

### Suggestions
- The card registry's `zoho_account` labels already name their COA account
  verbatim; when layer 2 renames the field, carry the label through unchanged
  so the item-26 style cross-reference stays possible without Zoho access.

### System Health
- Autonomy: 1 human intervention (altitude correction on the layout) — the
  correction class (presentation register) now has two hits with memory-only
  fixes; if a third lands, consider a rule-layer line in rule_behaviors
  input-interpretation instead.
