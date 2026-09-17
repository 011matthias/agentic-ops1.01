# Checkpoint: Vinted Demand Signals Read

**Date:** 2026-09-17
**Status:** Analysis delivered; no code or live-listing changes

---

## Summary

The owner asked for an SMS setup with multiple numbers; the real goal turned out to be extra Vinted accounts, which was declined (Vinted's own help page allows one account per member and deletes the rest). The session then produced the first demand-side read of the watcher DB: 233 confirmed sales and 7,505 first-hour heart counts show that price relative to the market median drives both hearts and sales.

---

## What Was Done This Session

### SMS request, then redirect
1. Enumerated existing telephony (E1): no SMS/telephony provider in the repo, vault (28 entries), or env files, matching the 2026-09-15 voice-line sweep.
2. Live-checked providers: Twilio DE local/mobile numbers are business-only (Handelsregister/Gewerbe + German address); seven.io inbound numbers from EUR 19.90/mo + 9.90 setup and target businesses/freelancers; sipgate local numbers cannot receive SMS from mobile networks. Verified SMS Gateway for Android (Apache 2.0): `simNumber` selects the sending SIM, `sms:received` webhooks carry `recipient` + `simNumber`.
3. Owner redirected: the goal was more than one Vinted account. Fetched vinted.com/help/1436 ("members can only have one account"; extra accounts must be deleted; post-ban accounts banned). Declined to build number infrastructure for that; nothing bought or created.

### Vinted demand-signal analysis (read-only)
1. Queried the live watcher DB read-only (`mode=ro`): 110,436 listings, 233 `buyer_item_status:SUCCESS` sales vs 673 rechecked-alive, 36,857 favourite events, 1,275 price events, 2,217 promoted rows.
2. Controlled the three confounded results against price band (title length, size-in-title, promoted) and checked premium women's denim observation length and seed rows.
3. Delivered the interpretation to the owner; recorded the numbers in memory `reference_vinted_watcher_corpus_limits.md` and the watcher status file.
4. Background agent compacted `MEMORY.md` from 21,349 to 16,944 bytes, 142 entries kept (verified by `wc -c`, entry count, topic-file count, no duplicate links).

---

## Key Decisions Made

### No SMS number farm for multiple Vinted accounts
- **Choice:** Decline; offer Vinted Pro (unverified whether it coexists with a personal account on Vinted's own pages) or improving the existing account.
- **Rationale:** Phone verification is Vinted's one-account enforcement; device/network linking would tie new accounts to the main one, whose reviews and live listings are the actual risk.

### Report group comparisons, not absolute rates
- **Choice:** Present sold rates as between-group contrasts only.
- **Rationale:** The recheck visits cheap alert candidates first, so every absolute sold rate runs high.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/projects/vinted-reselling/status/watcher.md` | Edit | New section "Erste Nachfrage-Auswertung"; "Jung + gefragt" row: heart sign now evidenced |
| `~/.claude/.../memory/reference_vinted_watcher_corpus_limits.md` | Edit | Demand-signal findings + what stays unanswerable |
| `~/.claude/.../memory/MEMORY.md` | Edit | Index hook update; compacted under the size limit |
| `.scratch/vinted/demand_signals.py` (gitignored) | Create | Re-runnable analysis for when sales reach a few hundred |

---

## Current Status

- Findings (full numbers in the status file section): sold 49% under 50% of median vs 9-12% above 75%; early heart converts only on price (88% vs 40% under 50%, 1 of 108 above 75%); promoted 25% vs 7% sold at/above market (n=91); short titles and no size in title carry more first-hour hearts at the same price band (correlation); knitwear 64% sold, jackets 30%, pants 11%; condition irrelevant; cut listings 0/32.
- Not answerable from this data: search position (views hidden, newest-first polling), upload hour (watcher off at night), time to sale (recheck cadence), our own closet (brands outside tracked cells).
- vinted-reselling: no `infrastructure.yaml`, no comms log (internal project).

---

## Next Steps

1. Re-run `uv run .scratch/vinted/demand_signals.py` once sales pass ~500; the brand and title splits are thin today.
2. Use the search-bar suggestions endpoint (recorded by a parallel session in the corpus-limits memory) as the buyer-vocabulary source for listing keywords.
3. Test short plain titles (size only in the size field) on the next batch against the 70-character formula in `listing-reference.md`.
4. Consider gating the "Jung + gefragt" heart boost to candidates already under the deal gate, since hearts above 75% of median did not convert.

---

## Context for Next Session

### Files to Read First
- `workspace/projects/vinted-reselling/status/watcher.md` (section "Erste Nachfrage-Auswertung")
- memory `reference_vinted_watcher_corpus_limits.md`

### Open Questions
- Can a Vinted Pro account coexist with a personal one? Third-party guides say yes; Vinted's help/1436 does not mention it.

### Working Notes
- Sold population = `sold_flag=1` plus rows with `last_seen - first_seen >= 12h` and no `gone_at`; 404-deleted rows excluded. Price position cells = `brand_norm x garment_class x cond_tier`, n >= 30.
- `posted_at` is NULL on all rows since #889 (webp photo URLs carry no epoch), so first-hour heart analysis only covers rows captured before 2026-09-16 10:00Z; it will not grow.
- Hour-of-day heart and upload counts mirror laptop uptime; do not report them as market timing.
- Title-length effect vanishes above 110% of median; likely reseller-vs-casual selection.

### Reference Materials
- https://www.vinted.com/help/1436 (multiple accounts)
- https://www.twilio.com/en-us/guidelines/de/regulatory
- https://docs.sms-gate.app/features/webhooks/

---

## How to Continue

For any Vinted pricing or listing question, start from the status-file section and the memory numbers; re-run the scratch script rather than re-deriving queries.

---

## Strategic Feedback

### What Worked Well This Session
- Checking whether the three strongest correlations survived a price-band control before reporting them: the promoted "no effect" headline flipped to "helps only above market" under the control.

### Suggestions
- On an infrastructure request with an unstated end use (numbers, accounts, proxies), ask what it is for in the first question, before provider research. Two research rounds here were spent on SMS before the goal surfaced.

### System Health
- The corpus-limits memory said the DB "cannot answer what gets traction"; sold detection had quietly made that false since 09-11. Memories that assert a capability limit need a trigger to re-test once data accrues.
- Autonomy: 1 human intervention (redirect from SMS setup to the Vinted-accounts goal).
