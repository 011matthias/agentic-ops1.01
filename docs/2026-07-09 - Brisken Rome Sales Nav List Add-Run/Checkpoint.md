# Checkpoint: Brisken Rome Sales Nav List Add-Run

**Date:** 2026-07-09
**Status:** Links handed to user; 11 remaining leads identified; worklist customer-track defect fixed and verified

---

## Summary

Resumed the "TA Cook Rome 26" Sales Nav list build-out. Established that the true
remaining add-set is 11 people (not the briefed 18), because 8 targets were already
in the list. Separately fixed a live data defect in the worklist file: 11 rows falsely
marked `customer` that are CRM leads, which fed Task 1's LinkedIn outreach.

---

## What Was Done This Session

### Sales Nav list work
1. Confirmed CDP attach to Edge :9222; Matthias signed into Sales Nav.
2. Opened 6 search tabs at once (hottest-5 cohort) and **tripped LinkedIn's
   "too many requests" throttle** on Brisken's seat. Backed off, 8-minute cooldown.
3. Established the real mechanism after user correction: search results carry **no**
   Save button. Save-to-list exists only on `/sales/lead/<id>`. The slug route
   `linkedin.com/sales/people/<slug>,NAME_SEARCH` renders a blank shell (dead route),
   so a lead URL cannot be constructed from the master sheet.
4. Read live list membership across **both** pages (page 1 renders 25 rows and hides
   page 2, which holds 9). List holds **34 members**.
5. Deduped: 8 of the 19 briefed targets were already in the list.
6. Handed the user 11 Sales Nav search links (user opens and saves in-seat).

### Worklist data defect (user-reported, then fixed on user order)
7. Verified `sales-nav-add-list-rome2026.md` marked **13** rows `customer`; only 2
   (Equinor) match `brisken_customer: Yes` in the corrected master sheet.
8. Established that `track` is NOT a pure function of `brisken_customer` (`personal`,
   `other`, `GA` cut across every value), scoping the fix to the `customer` track only.
9. Demoted the 11 false-customer rows to `pipeline`; added a provenance stamp.
10. Verified with an assertion against the live sheet: 0 rows now claim `customer`
    without `Yes`. Row count unchanged (129).

### Findings surfaced, deliberately not changed
11. **Inverse defect:** Dan Staniford + Sebastian Ramos (Tradeweb) are
    `brisken_customer: Yes` but sit on the `personal` track.
12. **Ashok Kumar (Accenture)** reads `In CRM`, neither `Yes` nor `Lead-*`. Parked in
    `pipeline` so the file stops asserting he is a client; needs a human read.

---

## Key Decisions Made

### Exclude Adela Dolezalova from the list
- **Choice:** Do not add, despite the session prompt listing her as addable.
- **Rationale:** Her real booth row carries the `stop: X` flag (Trillion Consulting,
  external contractor at Zalando). The worklist scopes to "everyone non-STOP". A
  second, unflagged row created from Doggala's referral made her look addable. That
  duplicate was removed from the sheet later the same day (298 -> 290 rows).

### Demote false customers to `pipeline`, not `other`/`GA`
- **Choice:** The 11 mislabeled rows become `pipeline`.
- **Rationale:** They are CRM leads (`No (Lead - ...)`), so `pipeline` is the truthful
  tier and the highest one they qualify for under the file's own tier order
  (customer > pipeline > personal > other > GA). Demoting further would lose real
  prioritization signal.

### Leave the Tradeweb inverse defect alone
- **Choice:** Flag, do not fix.
- **Rationale:** `personal` appears to encode "Dirk knows them" rather than customer
  status (`Yes`, `In CRM`, `No CRM match` and `Lead-*` all appear under it). Flipping
  them would be guessing at intent, and the harm direction (client tiered as personal
  contact) is mild versus greeting a prospect as a client.

### Search-tabs-only mechanism
- **Choice:** Agent opens search tabs; user clicks through to the lead page and saves.
- **Rationale:** User pick. The alternative (agent reads the result href and navigates
  to the lead page) doubles requests on a seat LinkedIn had just throttled, and edges
  past the brief's "do not scrape results".

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/lead-generation/targeting/sales-nav-add-list-rome2026.md` | Modified | 11 rows re-tracked `customer` -> `pipeline`; provenance stamp added. **Gitignored** (`workspace/clients/*/context/`), so no commit. |
| `.scratch/paced_search_tabs.py` | Created | Paced Sales Nav tab opener (1 tab / 75s) with a title-based throttle tripwire. Scoped to the corrected 11. |
| `.scratch/probe_lead_url.py` | Created, then deleted | One-off probe of the slug->lead-page route. Discarded per W1. |
| `.scratch/resolve_leads.py` | Created, then deleted | One-off read-only tab inspector. Discarded per W1. |
| `~/.claude/.../memory/project_brisken_rome_salesnav_list.md` | Created | List id, page-2 gotcha, Dolezalova STOP, lead-page-only Save, throttle threshold. |
| `~/.claude/.../memory/MEMORY.md` | Modified | Index pointer for the above. |

---

## Current Status

11 Sales Nav search links are in the user's hands; they open and save in-seat. Two
tabs (Landrø, Cuello) are already open in Edge from a run that was stopped. Nothing
is running against the LinkedIn seat.

The worklist file is corrected and verified. It is gitignored, so there is nothing to
commit or ship.

No orchestrator/platform work this session; no `infrastructure.yaml` touch, no MCP
scenario calls, no deploys.

---

## Next Steps

1. **Decide on Maria Moeller.** She is in the 11 links but no longer exists in the
   master sheet (removed when it went 298 -> 290 rows). She was Doggala's referral
   (his manager), never a booth attendee. If the deletion was intentional the set is
   10, not 11. Recommendation: skip her until the deletion's intent is known.
2. **Ashok Kumar (Accenture):** resolve `In CRM` to a real status. Currently parked in
   `pipeline`.
3. **Tradeweb inverse mislabel:** decide whether Dan Staniford and Sebastian Ramos
   should move from `personal` to `customer`.
4. Finish saving the 11 (10) leads into "TA Cook Rome 26".
5. Task 1's owner: the customer-track defect they were tracking is now fixed in the
   worklist file. Their checklist item can close, but the fix is data-only; any
   outreach copy already drafted off the stale tracks still needs a pass.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/targeting/sales-nav-add-list-rome2026.md`
- `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx`
- `.scratch/read_list.py` — reads live list membership (run BEFORE computing any "remaining" set)
- `.scratch/paced_search_tabs.py`

### Open Questions
- Was the removal of the two referral rows (Dolezalova dup + Maria Moeller) deliberate,
  or a side effect of regenerating the sheet from attendees only? Nothing in the comms
  log records the referral or its removal.
- Does `In CRM` mean anything actionable, or is it a null state? It appears under
  `pipeline`, `personal` and `GA` tracks.
- Is `personal` intended to outrank `customer` for contacts Dirk knows personally?

### Working Notes

**The list is paginated and page 1 lies.** `linkedin.com/sales/lists/people/7477347207906676736`
renders exactly 25 rows with no cue that more exist; the remaining 9 sit on `?page=2`.
`read_list.py` reads only the rendered page. Reading one page under-counts and will
regenerate the duplicate-tab problem.

**Already in the list (do not re-open):** Zucknick, Herrera La Grotta, Bonizzoni,
Favalli, Ermakov, Giesinger, Doggala (shown as "Lokesh R."), Badoux.

**The 11 handed over:** Landrø (VW), Cuello (JTI), Bakatselos (Coca-Cola Hellenic),
Oizumi (Hitachi), Ito (NYK), Hellmann + Korinsek (Wiener Städtische), Galera (SLB),
Snersrud (Norsk Hydro), Haegemans (Sanofi), Moeller (Zalando — see Next Steps 1).

**Company overlap is not duplication.** Several of the 11 work at companies already
represented by a *different* person: NYK via Asako Tateno Teruki, Norsk Hydro via Hege
Lundemo Larsen, SLB via Bettina Kiner Jørgensen, Coca-Cola HBC via Nikos Fragkos, JTI
via Jean-Baptiste Disdet, Sanofi via Badoux. Matching on company would wrongly skip all six.

**Failed approaches:**
- `linkedin.com/sales/people/<slug>,NAME_SEARCH` — dead route, renders a 1.9 KB shell
  with an empty body. Waited 25s; not a render race.
- Constructing a lead URL from the master sheet — impossible. Only 8 of 19 have a
  public `/in/` slug, and the lead id is not derivable from it.
- Opening 6 search tabs simultaneously — trips LinkedIn's rate limiter. Pace at ~75s.

**Rate-limit signature:** an in-page banner reading "You've made too many requests in
too short a time. Please try again later." It renders on the lead/search page itself,
so a tab that "opened successfully" can still be throttled. `paced_search_tabs.py`
tripwires on the tab title losing "Sales Navigator".

### Reference Materials
- List: `https://www.linkedin.com/sales/lists/people/7477347207906676736`
- Memory: `project_brisken_rome_salesnav_list.md`
- Worklist source of truth for STOP semantics: worklist header, line 3
  ("Everyone non-STOP from the Rome master sheet")

---

## How to Continue

Run `.scratch/read_list.py` against an open list tab **and** read `?page=2` before
computing any remaining set. Then either hand the user the search links or run
`.scratch/paced_search_tabs.py --gap=75`. Never open more than one tab at a time.
Resolve the Moeller question first; it may drop the set to 10.

---

## Strategic Feedback

### What Worked Well This Session
- The user's "stop" twice, with a one-line reason each time, was far cheaper than
  letting a 22-minute background run finish and then unpicking the damage. Short
  interrupt + reason is the highest-leverage correction pattern available.
- Handing over links instead of driving the seat was the right call and the user
  reached it faster than the agent did.

### Suggestions
- The session brief (`.scratch/rome-salesnav-continuation-prompt.md`) named
  `read_list.py` and said the list already held ~25-32 leads, but it also stated the
  remaining set as a fixed list of 18. The fixed list was trusted over the tool. A brief
  that says "compute the remaining set with `read_list.py`" and omits the enumeration
  would have prevented the duplicates outright.
- The brief's "5-6 at a time" pacing is wrong. Six trips the limiter. Change it to one.

### System Health
- Autonomy score: 3 human interventions this session.
- **Structural gap:** nothing in the repo enforces "read live list membership before
  computing a remaining set". The paced opener now hardcodes the corrected 11, which is
  a snapshot, not a gate. A `--dedupe-against-list` flag that calls `read_list.py`
  (both pages) and filters before opening would make the failure impossible rather
  than remembered.
- **Rule coverage:** `rule_behaviors.md` B2 says "enumerate ALL targets before
  starting". It fired for the *targets* (the 19) but not for the *exclusions* (who is
  already done). B2's enumeration clause is written for the additive set only.
- The `.scratch` prompt file is ephemeral but carried authoritative-looking scope (a
  numbered lead list). Ephemeral briefs that assert scope should point at the query,
  not cache its result.
