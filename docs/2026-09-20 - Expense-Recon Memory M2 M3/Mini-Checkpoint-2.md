# Mini-Checkpoint: Expense-Recon Memory M2 M3

**Date:** 2026-09-20
**Status:** M2 shipped and live (Fly v189); M3 read done and derived, write parked by the owner; M4 not started
**Type:** mini

---

## Summary

The MEMORY session's second iteration shipped note item M2 (a merchant's card,
learned from exclusive spend) and completed note item M3's owner-authorised
read of two years of Zoho Books. The owner reviewed the derived seed row by row
and parked the write; the reason is a measurement, not a preference, and it is
recorded as backlog item 156.

## What Was Done

**M2, backlog item 154, PR #1110, merge `90dc5c3b`, Fly v189.**

- Measured first on the live months: 128 rows, 60 display vendors, **34 on
  exactly one card, 5 on several, 21 on none**. The five are the AI vendors and
  the spellings around them, the same exceptions M1 found for categories.
- Registry gains `card_key`, `card_key_learned`, `cards_seen` (parallel, absent
  until set). `card_source: "merchant"` is the last link of the item-87 chain,
  under the same guard as `learned`; `can_mark_private` stays true on it.
- Sign-off learns it: `cards_seen` accumulates the month's resolved cards per
  merchant, a key is written only while exactly one card has been seen, a second
  card drops a LEARNED key, an editor-typed key is never touched, and a row
  carried by `merchant` teaches nothing so a lent card cannot harden into a fact.
- Wired on every surface holding live settings (grid, CSV, month PDF listing +
  card pass + card sections, cost-center roll-up, refresh preview). Deliberately
  not `rematch_month`, and `merchant` is kept out of `CARD_SCOPE_SOURCES`, so no
  pair moves and the accuracy gate is untouched.
- 10 route-level tests; three wires proven red under mutation. Suite 2575 ->
  2601 passed / 2 skipped after merging two siblings.
- Verified live: card resolution on July, August and September is byte-identical
  pre and post deploy (no live row moves, as designed, since no live registry
  merchant carries a card), plus a cold scripted Playwright drive of July's
  Expenses page (57 rows, cards rendering, no fallback, no writes but the login).
- Also recorded M1 (PR #1094, Fly v184) in the backlog heading and Shipped row
  100, which its own PR had left pending.

**M3, backlog item 156, PR #1118, merge `a1854310`.** One read-only pass over
Zoho Books, 2024-09 to 2026-09, seven real orgs: 2,355 expenses + 1,179 bills,
174 distinct vendors. Derived 91 registry candidates, 32 genuinely new (company,
vendor) rules and a per-merchant card observation. Nothing applied.

## What Did NOT Work (and why)

- **`regress_check.py` on the CSV export wire:** returned the doubtful
  `RED (no pytest summary line)` even though the mutation did bite. Re-done by
  hand with a `cp` backup, which showed the real failure (the CSV falls back to
  `(paid-through - assign)` / `(entity - assign)`, 1 failed / 9 passed) and
  restored cleanly. The tool's verdict was right; only its parse of the output
  was not.
- **The first M3 dedup count (95 new rules) was wrong.** It compared the WRITE
  endpoint's field name `legal_entity_id` against read rows, and `GET
  /api/memory` names that same value `entity` on `categories[]`. The write name
  reads None on all 103 live rows, so every existing rule counted as new. Caught
  by printing one row's keys instead of trusting the field name; the real number
  is 32. Instrument-validity, exactly the shape rule_behaviors B2 names.
- **Backlog numbering raced twice.** 152 was claimed by TRACEABILITY's T3 and
  then 153 by T1 while the M2 branch was in flight, so the item and its two
  Shipped rows were renumbered twice (ending at item 154, rows 100 and 101). The
  merge itself stayed clean because both sides were appends.

## Current Status

M2 is live on Fly v189 and changes no live row today: the 28 registry merchants
carry no card, so the new chain link is silent until an entry gains one, either
by hand in Settings or by a month publishing with a registry merchant on a
single card. Its Lovable half (`docs/lovable-merchant-card-prompt.md`) is
written and NOT applied.

M3's raw pull and derived candidates sit in the gitignored
`workspace/clients/brisken/context/expense-reconciliation/`
(`zoho-books-24mo.json`, `zoho-seed-candidates.json`) with the dry-run/apply
script beside them in the session scratchpad. The owner's decision is "nothing
yet", and backlog item 156 carries the three findings that drove it, including
the blocking one: the 24 months use **52 distinct Zoho expense accounts** and
the account -> category map inferred from the 103 seeded rows covers only 20,
leaving 30% of rows (all ad spend, all travel) unruled.

brisken platform: unknown plan, ~?/? ops/mo, last assessed ?. The comms log is
12 days stale. Two p2 status files are stale (p2-product-decks 59d,
p2-targeting 60d); they belong to the lead-gen workstream, not this session.

## Next Steps

1. **M4** (the queue's last item): a free-text `profile` on each registry entry,
   read by the categorizer as nonce-fenced untrusted context, shown on the
   Memory page, edited in Settings; then judge backlog item 118 (a cost-center
   pick teaches nothing) and either close it as a one-line addition to
   `registry_upserts_from_expense_run` or leave it open with the reason.
2. Hand the owner the M2 Lovable prompt to paste, so the Settings editor can
   carry `card_key` / `card_key_learned` / `cards_seen` (a save that omits them
   erases accumulated observation).
3. Waiting on the owner, unchanged: the OpenAI / Anthropic / Lovable registry
   write (do NOT re-ask), Dirk's 3x3 account table, and now the M3 seed.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 118, 154, 156
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`,
  the M2 section "A merchant's spend is often on ONE card"
- `.../src/expense_recon/merchant_registry.py` and `web/service.py`
  `resolve_batch_row_cards` + `registry_card_upserts_from_expense_run`
- `.../docs/lovable-merchant-card-prompt.md` (not applied)
