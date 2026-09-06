# Mini-Checkpoint: Brisken P1 Program Prompts And Round-0

**Date:** 2026-09-06
**Status:** Program integrated; round-0 executed; four parallel round prompts handed
**Type:** mini

---

## Summary

Merged the three 2026-09-06 analyses (Zoho incorporation ranking, manual-input
audit, owner program items 38-41) into one execution program, ran round-0, and
handed the user four paste-ready prompts that run rounds R1-R4 in four
parallel chats (own worktree/branch/PR each, merge order R1-R4).

## What Was Done

- Round-0 card data entry via authorized operator-API write (user approved in
  AskUserQuestion): entities on 0113 (Corporate Services) + 6013/9693/8311
  (Cloud Services), card-0340 created. All 6 cards verified field-by-field on
  `/api/cards` re-read; 2838's legacy entity untouched. Values from the
  gitignored `context/expense-reconciliation/zoho-entity-card-map.md`
  (status column updated in place).
- Capture PR #681 (auto-merge armed): new backlog item 42 (refusals split,
  rides R2 chat), item 39 R2 rollout protocol (flag default-off, arrival-only
  ensure-month, explicit operator backfill, stranded-archive re-pool sweep,
  staged flip) + create-month-button subsumption, item 35 assigned R1-first-
  commit, item 40 person-timing rule (normalize_cards_setting drops `person`
  today; entry post-R1-deploy after SPA prompt verified), item 26 entity half
  done, loop-brief refresh (live state, 1400/2 baseline, parallel-4-chat
  execution model).
- Four round prompts composed and handed in-chat (R1 person+private-expense+
  item-35 grouping; R2 auto-materialize+item-42; R3 trips; R4 cross-batch
  settlement). Design pressure-tested by two plan agents; key traps baked in:
  no unattended boot backfill, receipt_claims table under _BATCH_ADD_LOCK for
  R4, stale-SPA whole-map-replace erasure.
- Owner question list handed for relay (persons per card, 0340/3645/1672
  entities, Consulting coverage, travel alias name, GL-codes call).

## Current Status

App unchanged since #657 (v101+); nothing deployed this session (settings
data write only). Backlog items 38-42 + binding protocols on main once #681
merges. Pool still waits (23 mails) until R2 deploys and the operator
backfills. brisken platform: unknown plan (standing).

## Next Steps

1. User pastes the four round prompts into four fresh chats; merge order
   R1 → R2 → R3 → R4 (each chat rebases before merge).
2. User relays the owner question list to Dirk/Criss; answers unblock person
   entry (post-R1), the R2 flip (Hostinger dismissals), R3 deploy (alias).
3. Post-R1 deploy + verified SPA prompt: enter persons in Settings > Cards.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md (execution model)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 38-42)
- .claude/plans/i-need-you-to-breezy-parasol.md (the approved session plan)
