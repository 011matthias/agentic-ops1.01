---
project: upwork-independence
workstream: u7-subcontracting
group: uwi
spec:
state: not-started
updated: 2026-09-05
general_ref: status/uwi-general.md
---

# uwi / u7 — Subcontracted delivery

The load-bearing GTM-v2 assumption with ZERO physical counterpart: the entire
B2B scale-up (110-client serviceable cap) rests on subcontracting delivery at
~EUR20/hr with ~1.5h/client/mo oversight (~4x leverage) — and no subcontractor
relationships, vetting artifacts, delegation SOPs, or oversight tooling exist
anywhere. Starts when u5's kit exists (the kit IS the contractor runbook).
The leverage assumption is treated as UNVALIDATED until the trial milestone
passes.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Sourcing | not-started | Where subcontractors come from (near-shore/EU per the EUR20/hr assumption) | Sourcing shortlist when u5 lands | u5 kit | — |
| Vetting checklist | not-started | Skills + trial-task design | With sourcing | u5 | — |
| Trial task | not-started | One PAID delegation of a full kitted cycle at client 6-8; preconditions: u5 kit + >=1 clean paid kitted delivery cycle; Jochen = first sourcing candidate; second contractor identified before any pass (two-contractor floor). Parameters plan-set by `../context/monetization-strategy.md` 2026-09-05 | After vetting | u5 | — |
| Leverage validation milestone | not-started | Pass = oversight <=2.25 h/client/mo (stress-guard x1.5 bound) held over 3 clean cycles, quality client-invisible. 2.25-3.0 = NOT passed: gtm-v3 re-model first, nothing above the solo ceiling unlocks. >=3.0 (2x miss) = fail + gtm-v3 trigger (span-of-control cost) | After trial | trial | gtm-v2 SUMMARY sensitivities; strategy doc u7 section |
| Delegation SOP | not-started | Per-tier runbook derived from u5 playbooks; contractor-safe (nothing gitignored/operator-head-only) | With trial | u5 | — |

## Open decisions / gates

- Blocked on u5 delivery-kit extraction (hard dependency).
- Contractor engagement terms — owner call at sourcing time.

## Pointers

- The assumption under test: `docs/optimize/upwork-independence-gtm-v2/SUMMARY.md`
  ("validate against an actual subcontracted delivery arrangement before
  assuming 62.5 serviceable clients").
- Stress-tested bounds: rate x1.3, oversight x1.5 still clears the pessimistic
  floor (gtm-stress-guard-v2), so moderate misses are survivable; a 2x miss is
  a gtm-v3 trigger.
