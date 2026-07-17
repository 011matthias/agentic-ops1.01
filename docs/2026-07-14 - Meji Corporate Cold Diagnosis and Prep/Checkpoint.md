# Checkpoint: Meji Corporate Cold Diagnosis and Prep

**Date:** 2026-07-14
**Status:** A/B diagnosed + September prep verified load-ready; nothing sent, all gates intact

---

## Summary
Logged the Jul 09-13 Gurmej thread into the comms-log (with corrections),
answered the Make credit-trend question, drafted the Version C nudge, then
diagnosed why corporate cold A/B underperformed and executed the approved
"Hold + prep for September" work, including fixing a real M&M-exclusion gap
in the sourcing pipeline.

---

## What Was Done This Session

### Comms (logged + corrected)
1. Transcribed the Jul 09->13 Upwork thread from the screenshot into
   `comms-log.md`. Four corrections vs. the prior log: added Gurmej's Jul 13
   reply "Ok keep me posted please"; replaced the logged Make-message draft
   with the shorter as-sent version; added the Jul 11 implementation report
   verbatim as Block 29; corrected the Block 28 date 07-08 -> 07-09 (Upwork
   header "Thursday, Jul 09", times 17:53/18:09 unchanged).

### Make credits (diagnosed, not touched)
2. Live `organizations_get` on prod org 5473701: 16,051/20,000 used (~80%),
   ~698/day, resets 2026-07-20 10:44, auto-purchase off, 7-day grace.
3. Established the top-up isn't needed this cycle (grace bridges the ~1-day
   gap to the reset). Verified there is NO billing tool in the Make MCP/API
   (top-up = web-UI action only), so it can't be executed programmatically.
4. Trend answer: at ~698/day you're ~5% over the monthly cap, up ~8% vs the
   prior cycle; if Jul 20 -> Aug 20 lands at/over cap again, raise the plan
   (20k -> 40k) before September rather than reacting mid-peak.

### Version C + A/B explainers
5. Explained Version C = the "Top-Tier Named Accounts" track (~100 hand-picked
   companies, 2-3 contacts each, per-account personalized 3-email sequence,
   aimed at the 5-10 multi-event clients at PS20k+/yr).
6. Explained A/B/C run simultaneously and additively; C is a replacement ONLY
   for the ~100 named accounts (carved out of A/B so no company is double-hit).

### Corporate cold diagnosis (plan mode) + prep (executed)
7. Live health check: A (P2A) is `Completed` (ran out, 0 replies); B (P2B) is
   `Paused` deliberately by Gurmej's 2026-07-07 order, NOT bounce-paused now
   (bounce 0%). Root causes: targeting (old broad list = public-sector/
   education, all wrong-fit nos), Mimecast gateway (~91% bounce on deciders),
   off-season, structural cold-vs-warm gap.
8. Approved plan = "Hold + prep for September." Confirmed the pipeline
   `meji_p2_batch_2026-07-01.py` is already at band 50-2,000 with the
   deliverability gate wired; free `--search` probe ran clean (300 candidates).
9. **Fixed a real gap:** the batch never applied the M&M past-customer
   exclusion. Wired it into `format_leads()` against `p2-mm-exclude-domains.json`
   and verified: it caught 1 past M&M customer that had leaked into the July
   load-ready list.

---

## Key Decisions Made

### Hold + prep for September (not relaunch now, not strategic reweight yet)
- **Choice:** Leave A completed / B paused; do read-only/build prep so
  September is load-ready; defer any strategic reweight (toward Version C +
  warm) to the end-September judgment gate.
- **Rationale:** Relaunching in July burns reworked copy on a proven-weak
  window; the fix is already approved and staged; the honest test is in-season.

### Do NOT execute the Make top-up
- **Choice:** No top-up this cycle.
- **Rationale:** Not needed (grace bridges the reset) AND not tool-executable
  (no Make billing API). A billing plan bump is the durable fix if the trend
  holds next cycle.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/meji-media/context/comms-log.md | Modified | Logged Jul 09-13 thread; as-sent Make msg; Gurmej reply; Block 29; date fix; MAKE OPS item + live credit finding |
| workspace/clients/meji-media/context/analysis-scripts/meji_p2_batch_2026-07-01.py | Modified | Wired M&M past-customer exclusion into `format_leads()` (+ MM_EXCLUDE const, `mm_exclude_domains()`, drop-count report) |
| workspace/clients/meji-media/context/pilot-routing.md | Modified | Recorded September prep load-ready state + 2 open pre-load items |
| .claude/plans/a-and-b-still-swirling-dusk.md | Created | Plan file (diagnosis + Hold-and-prep, approved) |

(Regenerated intermediate data via the read-only probe/format runs:
`p2-firstbatch-2026-07-01-candidates.json`, `p2-final-leads.json`. These
scripts + data live under gitignored `context/`, so no commit.)

---

## Current Status
- **A (P2A):** Completed, list depleted, 0 replies. **B (P2B):** Paused
  deliberately since 2026-07-07 (bounce 0%, clean).
- **September pipeline:** load-ready on the parts that matter (ICP 50-2,000,
  Mimecast MX gate, NeverBounce, M&M exclusion now wired). Nothing sent.
- **Ops (Make prod org 5473701):** Core plan, ~16,051/20,000 ops/mo (~80%,
  YELLOW). Resets 2026-07-20; auto-purchase off. No top-up this cycle.
- **Version C nudge:** drafted + comms-critic-cleared, ready for the user to
  send on Upwork (not sent, no draft file created).

---

## Next Steps
1. Send the Version C nudge to Gurmej (drafted this session).
2. After the 2026-07-20 reset: check whether the cap was actually brushed;
   if Jul 20 -> Aug 20 also lands at/over cap, raise the Make plan (20k->40k)
   before September.
3. Gurmej owes his 15-20 dream-account names for Version C (nudge ~2026-07-16
   if not arrived).
4. Before the September load: widen the sourcing geography (batch is London+SE;
   corporate scope is UK-wide) and re-pull `p2-mm-exclude-domains.json` fresh +
   run the Apollo reveal + NeverBounce just before load (data freshness).
5. Weekly report corporate section switches to pounds from the next edition.

---

## Context for Next Session

### Files to Read First
- workspace/clients/meji-media/context/comms-log.md (frontmatter + top entries)
- workspace/clients/meji-media/context/pilot-routing.md (the 2026-07-07 section
  now carries the September-prep state)
- workspace/clients/meji-media/context/analysis-scripts/meji_p2_batch_2026-07-01.py
- .claude/plans/a-and-b-still-swirling-dusk.md

### Open Questions
- September geography: UK-wide in one pull vs staged regional batches (a
  deliverability-ramp choice, decide at load time).
- Whether the end-September gate reweights corporate toward Version C + warm
  if in-season broad A/B still underperforms (flagged, revisit then).

### Working Notes
- The current P2B pause is DELIBERATE (Gurmej 07-07), distinct from the earlier
  2026-06-19 bounce auto-pause (fixed + resumed at a 25/day drip). Do not
  conflate them.
- The July batch pipeline is scoped London+SE as a controlled first batch, not
  the full UK-wide September pull. Band 50-2,000 is already set (line 49).
- M&M exclusion only works post-reveal (domain unknown at search), so it lives
  in `format_leads()`, not `search()`. Exact-domain match (no subdomain
  matching), same limitation as the existing enrich mechanism.
- Make top-up is a web-UI billing action; no API path exists. Documented in
  the comms-log MAKE OPS item so a future session doesn't retry it via MCP.

### Reference Materials
- Plan: `.claude/plans/a-and-b-still-swirling-dusk.md`
- Approved copy: `context/p2/piece2-cold-copy-v2-2026-07-08-CLIENT.md`
- M&M list: `context/p2/p2-mm-exclude-domains.json` (1,183 domains, re-pull before load)

---

## How to Continue
Send the Version C nudge. Watch the Make cap after Jul 20. When Gurmej's
15-20 names land, build the agent-side half-list and hold the joint session.
The September relaunch runs the (now M&M-safe) pipeline UK-wide, fresh reveal +
NeverBounce at load time, then B5 readiness check, then activate on Gurmej's go.

---

## Strategic Feedback

### What Worked Well This Session
- The screenshot -> comms-log transcription convention caught four real
  drift points (as-sent vs draft, missing reply, missing Block, date error)
  that would otherwise have compounded.
- Plan mode forced a clean diagnosis before the prep, which surfaced the M&M
  gap instead of just rebuilding blindly.

### Suggestions
- When a client-account action (top-up, plan change) is raised as a "pending
  decision," verify tool-doability at that moment rather than carrying it as
  an open item; it collapses the decision faster (see friction below).

### System Health
- The Make MCP has no billing surface; any credit/plan action is inherently
  user-side. Worth a one-line note in the Make skill so it isn't re-attempted.
- Autonomy score: 2 human interventions this session.
