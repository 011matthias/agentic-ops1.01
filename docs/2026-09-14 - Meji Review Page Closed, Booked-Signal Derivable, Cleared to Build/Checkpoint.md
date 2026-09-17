# Checkpoint: Meji Review Page Closed, Booked-Signal Derivable, Cleared to Build

**Date:** 2026-09-14
**Status:** All client review-page items closed; cleared to build the Christmas suppression + re-engagement (owner-go gated at the write/send steps).

---

## Summary
Proved the "who has booked" filter is derivable from Meji's own database (no client ask), then Gurmej finished the review page (Version A approved, seed inboxes provided), closing every client blocker. The paid critical path is now the suppression build, then the 3-touch Christmas re-engagement.

---

## What Was Done This Session
### Booked-signal derivation (answering "can we find this ourselves?")
1. Confirmed `enquiries.enquiry_status` has no booked value: closed 7-value set (new / in_contact / cold / hot / ready_to_book / dead / null), top of funnel is `ready_to_book`. A lead that books graduates OUT of `enquiries`.
2. Enumerated the `xmas_2020` schema (51 tables via `information_schema` UNION). Bookings live in `parties` (271 rows) with `leader_email`, financials, and a Stripe `customer_id` (111/271 paid); plus `parties_booked` (180, a BI view), `invoices`, `transactions`, a `hubspot_sync` pair.
3. Suppression is derivable: match campaign-audience emails against `parties.leader_email`. Corrected my own wrong assumption that `parties.converted` is an enquiry link (resolves to neither enquiries table; join on email).

### Family-exclusion results (for billing)
4. Pulled the live A1 (8804011) execution log: since fail-open go-live 2026-09-10 12:02Z, 31 full office-reply runs + 2 family enquiries held to 1 filtered step, zero misfires. Drafted the client-facing results message (value proof ahead of the invoice; no internal-defect detail).

### Review page closed
5. Read the page back 2026-09-14: `version-a` approved (all A/B/C signed off), `seed-inboxes` provided by **Gurmej Pawar** (his name on record for the first time): gurmejpawar@hotmail.com, amrit_kaur44@hotmail.com. Test-inbox set completed with Matthias's Brisken/iCloud/Gmail (Microsoft/Apple/Google spread).

---

## Key Decisions Made
### Booked filter is self-derived, not a client ask
- **Choice:** Drop the "which enquiry_status means booked" question; derive from `parties.leader_email`.
- **Rationale:** The field has no booked value by design; asking would never have produced one. Matches the 09-08 promise "your own system can do that for us."

### Suppression before send (Gurmej's own condition)
- **Choice:** Build the stop-list + booked suppression first; the Christmas re-engagement send waits on it.
- **Rationale:** `christmas-reengagement=go WITH SUPPRESSION BUILT FIRST` was his explicit review-page answer.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/comms-log.md | edit | 2026-09-11 booked-derivation finding; test-inbox resolution; 2026-09-14 review-closed entry (gitignored) |
| workspace/clients/meji-media/status/enquiry-automation.md | edit | Booked-lead suppression blocked → ready; `updated` bumped |
| .scratch/meji-review-0914.json | write | Raw review-page pull (gitignored) |

---

## Current Status
- **meji-media ops:** live Make.com pipeline (A0-A3); `infrastructure.yaml` has no `platform` section (Make orchestrator, expected). Family exclusion live and clean on real traffic since 2026-09-10.
- **Client:** nothing owed. All review-page items answered; comms-log touched today.
- **Cleared to build**, invasive write/send steps gated (B5).

---

## Next Steps
1. **Suppression build, read-only first.** Stop-list from replies + not-interested across the three Christmas campaigns (`00fc708d` Warm Re-engagement, `1f40cb36` Bookers, `f9e61441` Cold 3 Cities); booked-suppression by cross-matching audience emails to `parties.leader_email`. Then **owner go #1** to write the combined set to the Instantly account-wide block list.
2. **Christmas re-engagement send** (after suppression holds): 3-touch, senders `gurmej@mejimedia.com` + two `mejixmas` (NOT `bookings@`; ~180/day). Placement-test to the 5 seed inboxes. **Owner go #2** to activate/send.
3. **Deciders cold sequence** (campaign `c3daf05c`), now that Version A is approved; load/activate is its own owner-go.
4. Hand Gurmej + Jess the family-exclusion results message before billing.
5. Commit the uncommitted `status/enquiry-automation.md` edit on a `client/meji-media/...` branch (currently dirty on main).

---

## Context for Next Session
### Files to Read First
- workspace/clients/meji-media/context/comms-log.md — the 2026-09-14, 2026-09-11 finding, and 2026-09-09 review-page entries
- workspace/clients/meji-media/status/enquiry-automation.md
- workspace/clients/meji-media/context/pilot-routing.md (campaign routing)

### Open Questions
- Which "booked" cut to use for suppression: conservative (any `parties` row) vs paid-only (`customer_id IS NOT NULL`). Conservative needs no client input.
- Email-match misses a lead who enquired and booked under different addresses (seen: "swapped to her work email"); acceptable for v1, HubSpot would be stricter.

### Working Notes
- Read-only DB path: UTIL scenario `s8974201_util_my_sql_parameterized_query`, `by_id` mode concatenates `param1` after `WHERE id =` (SELECT * FROM enquiries), so free-form boolean/UNION/GROUP BY rides along. The `s8842540` count tool and `s8842538` test tool BOTH ignore their inputs (return fixed results) — do not trust; differential-probe.
- Review-page read-back: FORM-encoded POST /api/wimmer-unlock (code=MEJI_DOC_GATE_CODE, site=meji); JSON body 500s. Run via PowerShell `Invoke-WebRequest -SessionVariable` — Git-Bash curl `-o`/`-c` fail to write here (error 23) and MSYS mangles the `from` path.
- `booking_confirmed` / `confirmed` columns are 0 across all 271 `parties` rows (dead columns); do not gate on them.

### Reference Materials
- INSTANTLY_API_KEY, MEJI_DOC_GATE_CODE, MAKE_API_TOKEN in the gitignored context/.env
- A ready-to-paste continuation prompt was handed in the 2026-09-14 chat (suppression build first).

---

## How to Continue
`/resume meji-media`, then start Task 1's read-only compilation and report the proposed stop-list + booked-match before any write. Keep every invasive Instantly action behind an explicit owner go + readiness check.

---

## Strategic Feedback

### What Worked Well This Session
- Instrument-validity discipline paid off twice: the "1473 for every filter" tell exposed the count tool ignoring its WHERE, and differential-probing the parameterized tool made the schema findings trustworthy. Also caught and corrected my own wrong `converted`-is-an-enquiry-link assumption before it reached a claim.

### Suggestions
- The review-page read-back mechanics (form-encoded, PowerShell, curl-write-failure) are now in the comms-log; fold a one-liner into a tooling memory if it recurs a third time, so it is one call next time.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). One B1 open-offer close was caught by the stop-b1-gate and redone; the structural gate contained it, but the generation-side pattern recurs (see friction).
