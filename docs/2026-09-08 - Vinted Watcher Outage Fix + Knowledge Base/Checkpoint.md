# Checkpoint: Vinted Watcher Outage Fix + Knowledge Base

**Date:** 2026-09-08
**Status:** Watcher live on v2 session-hardening; knowledge base merged; outcome data reset clean

---

## Summary

Diagnosed and fixed the watcher's 46h silent outage (24h anonymous JWT +
a refresh path that could never mint a new token), hardened session and
outcome-data handling (v2, PR #712), reset 400 fabricated gone rows, and
consolidated all project knowledge into workspace/projects/vinted-reselling/.
Owner-approved improvement prompt for the next round is stored and ready.

---

## What Was Done This Session

### Outage diagnosis + service restoration
1. Root-caused via live probe: `access_token_web` is a 24h JWT; the homepage
   reissues a token ONLY to a cookie-less request, so v1's refresh (GET with
   stale jar) was a no-op; every cycle 401'd into a 1h backoff loop while the
   detached vbs kept the task green for 46h.
2. Restored service same hour (cleared cookie jar + wedged backoff flag).
3. Ultracode workflow audit (42 agents): 38 findings, 32 survived
   adversarial verify; key extra defects folded into the fix.

### v2 hardening (merged as 49605f86, PR #712)
1. Clean-slate jar clear before refresh; proactive renewal 45 min pre-expiry.
2. 401 (10 min backoff) split from 403/429 (60 min escalating to 6h,
   Retry-After honored); SessionWall aborts the whole cycle; non-JSON 200 = wall.
3. recheck_gone: proven-session precondition, login-wall redirect aborts the
   pass, >40% gone batches discarded, gone_source provenance, re-sighted
   listings clear their verdict.
4. Liveness: stall push alert after 45 min (6h re-nag), drill-tested against
   the real ntfy topic; run-hidden.vbs now waits and propagates exit codes.
5. In-place schema migration (garment_class, is_kid, gone_source); kids
   month-size detection ("24-36 Monate / 92" class leaked 15 alerts) + kids
   excluded from comp medians.
6. 33 offline tests on a mock transport reproducing the probed no-reissue
   behavior; regress_check proved green->red->green on the jar-clear.

### Data repair
1. All 400 gone rows reset (backup data/vinted.db.bak-2026-09-08): 15 batches
   of exactly 25, 100% gone-rate, 0 sold flags = fabricated by dead-session
   rechecks. Zero trusted outcome rows existed; clean restart under provenance.

### Knowledge base (same PR)
1. README.md rewritten as folder hub; STRATEGY.md (leverage ranking,
   economics, calibration plan); api-notes.md (verified API surface, session
   mechanics, incident record); improvement-prompt.md (owner-approved 8-point
   next round); status/watcher.md brought current.

### Earlier in this conversation (2026-09-05..07, context)
1. Feasibility probe GO; watcher v1 built + scheduled task; thresholds
   tightened to 0.55/8/8 EUR (PR #673); optimize-loop verdict: right tool,
   needs ~2 weeks of trusted gone-data first.

---

## Key Decisions Made

### Reset ALL gone rows rather than salvage
- **Choice:** gone_at=NULL, sold_flag=0 across the board.
- **Rationale:** v1 recorded no provenance; every batch showed the systemic
  100%-gone signature; salvage was indistinguishable from contamination.

### Clean-slate homepage GET over /oauth/token refresh grant
- **Choice:** jar-clear + homepage GET is the production refresh path.
- **Rationale:** simpler, probed working; the oauth grant (also verified
  working, 90-day refresh token) documented in api-notes.md as fallback.

### Alert-quality work deferred to the stored prompt
- **Choice:** owner rates current alerts as weak; the 8-point improvement
  round (fake detection, feedback loop, S/M/L sizes, women's jeans, DE-first,
  data-driven brand rules, schema, hashtag reference) runs as its own session
  via improvement-prompt.md, with pre-authorized access.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| workspace/projects/vinted-reselling/watcher/vinted_watcher.py | rewrite (session/recheck/liveness) | v2 hardening |
| workspace/projects/vinted-reselling/watcher/run-hidden.vbs | rewrite | honest exit codes |
| tools/tests/test_vinted_watcher_session.py | new | 33-test offline regression suite |
| .github/workflows/ci.yml | edit | hooks job gains httpx+pyyaml |
| workspace/projects/vinted-reselling/{README,STRATEGY,api-notes,improvement-prompt}.md | new/rewrite | knowledge base |
| workspace/projects/vinted-reselling/status/watcher.md | update | status roll-up |
| data/vinted.db (gitignored, machine-local) | repair | gone-reset + backup |

---

## Current Status

Task VintedWatcher runs v2 every 5 min (verified live: in-place migration
ran, 93 listings collected, health OK, token expiry 2026-09-09T11:38Z).
DB: 28.5k listings, 416 alerts cumulative, 0 gone (clean restart).
vinted-reselling has no infrastructure.yaml (standalone Windows-task
project; not orchestrator-based) and no comms-log (internal, no client).

---

## Next Steps

1. Owner pastes improvement-prompt.md into a fresh session (precondition
   PR #712 is merged - done).
2. Let trusted gone_source data accumulate ~2 weeks, then build the
   backtest scorer as its own PR and run /comd_optimize (STRATEGY.md).
3. Watch first days of v2: gone-rate per recheck batch should be well under
   40%; stall alert should stay silent while the PC is on.

---

## Context for Next Session

### Files to Read First
- workspace/projects/vinted-reselling/README.md (hub)
- workspace/projects/vinted-reselling/api-notes.md (session mechanics - the
  no-reissue asymmetry is the thing you must not re-learn the hard way)
- workspace/projects/vinted-reselling/status/watcher.md

### Open Questions
- Which country/shipping fields does the catalog API expose? (UNVERIFIED;
  needed for the DE-first filter in the improvement round.)
- Do search_tracking_params / content_source / item_box carry usable ranking
  signal? (Unexamined.)
- Fly.io move: how does Vinted treat datacenter IPs? (Untested; only matters
  if PC uptime becomes limiting.)

### Working Notes
- A sibling session's friction row (2026-09-08, system) shows Vinted
  PUBLISHING work happened elsewhere: wardrobe feed is
  /api/v2/wardrobe/{uid}/items, NOT /users/{uid}/items (that one returns
  empty for own closet and caused duplicate listings). Coordinate before
  touching listing-side automation.
- ntfy topic: context/.env (NTFY_TOPIC=vinted-nm-awjbg7e6nuxr). Owner had
  not yet confirmed phone subscription as of 09-06.
- The interrupted regress_check rerun (jar-clear mutation) was declined by
  the owner mid-fix; suite bite was already proven on the first run pre-rework.

### Reference Materials
- PR #712 (fix + knowledge base), PR #671 (v1), PR #673 (thresholds)
- Workflow audit run wf_535ccc92-9b1 (journal in session subagents dir)

---

## How to Continue

`/comd_resume vinted-reselling`, read the three files above. For the
improvement round: paste improvement-prompt.md content as the session prompt.

---

## Strategic Feedback

### What Worked Well This Session
- Live mechanism probes before fixing: the 4-scenario auth probe turned "it
  stopped" into a proven root cause + proven fix in one pass, and the mock
  transport in the test suite encodes exactly that server behavior.
- The 100%-gone-per-batch signature was caught by querying distribution
  shape, not just counts - shape questions find systemic corruption.

### Suggestions
- The B2 sub-clause "fix-bites-the-caller" held well here; what was missing
  on 09-06 was a liveness requirement at BIRTH of any scheduled automation.
  Consider a rule/checklist item: no new scheduled task ships without a
  stall-detection path that alerts a human (the stall alert existed only
  after the outage).

### System Health
- Autonomy: 3 human interventions (outage report by owner - the detection
  gap now closed structurally; one declined tool call; one ship order).
  Elevated but explained by the outage; the structural fix (stall alert +
  honest exit codes) removes the owner-as-monitoring dependency.
- Gates: B1:2 B2:6 B3:1 skipped:1 (the skip: v1's recovery path shipped
  untested on 09-06 - now the register row).
