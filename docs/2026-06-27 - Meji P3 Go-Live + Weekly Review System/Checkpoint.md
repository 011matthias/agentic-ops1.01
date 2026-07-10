# Checkpoint: Meji P3 Go-Live + Weekly Review System

**Date:** 2026-06-27
**Status:** P3 live (sending); weekly-review system built, verified, and scheduled (local).

---

## Summary
Took Meji Piece 3 (Christmas cold) live after the NeverBounce token was restored, then built a repeatable weekly campaign-management blueprint + engine for all three live pieces (P1/P2/P3) and scheduled it as a local Monday task.

---

## What Was Done This Session

### P3 go-live (Christmas cold)
1. Re-ran the resumable NeverBounce stage on the 206 token-errored leads: recovered 159 clean (132 valid + 27 catchall), dropped ~70 genuine-bad across two passes, 18 persistent NB timeouts held OUT of the fresh mailboxes.
2. Final verified list = **529 NB-clean**, full 3-city coverage (Birmingham 240, Leicester 231, Wolverhampton 58).
3. Patched campaign `f9e61441` `owned_by` (was NULL → UI 404 fix); `custom_variables` auto-derives from loaded leads.
4. Loaded the 529 (per-lead `venue_phrase`/`theme` confirmed attaching), ran the B5 readiness audit (21/21 PASS, GO), activated. Status 1, mailboxes 30/day each, 50/day combined.
5. Updated `pilot-routing.md` with the live P3 row + build section.

### Weekly-review system (the main build)
6. **Blueprint** `weekly-review-blueprint.md` — 9 layers (A config-drift audit, B health, C metrics+trend, D reply triage, E diagnosis, F levers, G capacity/forecast, H ROI, I record). A–D auto, E–I agent pass.
7. **Engine** — rebuilt `meji_campaign_health_check.py` into the full analyzer (stdlib-only, throttled for Instantly's 20/min cap): adds P3, windowed analytics, config-drift audit (status/owned_by/mailbox-cross-wire/double-send/flags), week-over-week trend, reply triage via `/emails?email_type=received` (uses Instantly `ai_interest`, buckets OOO/auto + own-domain). Modes `--write-review`, `--deep`, `--scheduled`.
8. Repointed `meji_weekly_report_data.py` to the current 4 campaigns (was on dead Christmas-Bookers/Banter IDs).
9. **Scheduler** — registered local Windows task `MejiWeeklyReview` (Mon ~06:17, `--scheduled`, StartWhenAvailable). CI deliberately ruled out (engine embeds client IDs/mailboxes → can't go in the public repo).
10. Saved memory `project_meji_weekly_review_system.md` + index pointer.

---

## Key Decisions Made

### Keep NB-errored leads, re-verify rather than drop
- **Choice:** Retain API-errored leads as `error_unverified`, re-verify after token restore; never discard on an API error.
- **Rationale:** The token lapse had errored an entire city (all Wolverhampton); the original drop-on-error logic would have launched a "3-city" campaign with zero Wolverhampton. 18 persistent NB-timeout leads were excluded from the fresh mailboxes (the P2B bounce lesson).

### Scheduler = local Windows task, not GitHub Actions CI
- **Choice:** Local `MejiWeeklyReview` task on the owner's machine.
- **Rationale:** The engine embeds client campaign IDs + mailboxes (correctly gitignored). Public CI would either leak that or need a config-in-secret refactor. Local task keeps everything private; trend works because local history persists. User chose this from a 3-way fork.

### Reply triage is semi-automated, not count-only
- **Choice:** Pull actual reply bodies via `/emails?email_type=received`, surface `ai_interest`, auto-bucket OOO/auto + own-domain, leave the rest for human classification.
- **Rationale:** The API reply *count* hid two hot P1 leads (magda@bst-elec "looking for a venue", creativecastles "interested again, what's the theme"). The count is where "P2 not converting" was misdiagnosable; the bodies are where the truth is.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `…/context/analysis-scripts/meji_p3_instantly_load.py` | Modified | Resumable NB stage; load filters to nb=clean only |
| `…/context/pilot-routing.md` | Modified | P3 live row + build section |
| `…/context/weekly-review-blueprint.md` | Created | The 9-layer weekly structure (source of truth for the process) |
| `…/context/analysis-scripts/meji_campaign_health_check.py` | Rebuilt | Weekly review engine (audit + health + metrics + trend + triage) |
| `…/context/analysis-scripts/meji_weekly_report_data.py` | Modified | Repointed to current 4 campaigns |
| `…/context/weekly-reviews/2026-06-26.md` + `.json` | Created (generated) | First weekly review + trend spine baseline |
| Windows task `MejiWeeklyReview` | Created | Monday ~06:17 local scheduled run |
| `memory/project_meji_weekly_review_system.md` + `MEMORY.md` | Created | Recall pointer (the Windows task is machine-state, not in repo) |
| `.github/workflows/meji-weekly-review.yml` | Created then deleted | CI cron abandoned (gitignored-script/public-repo wall) |

All weekly-review artifacts live in gitignored `context/` (client data, public repo). Zero tracked files added.

---

## Current Status
- **P3:** live, status 1, 529 leads, sending on the UK window from the 2 mejixmas mailboxes.
- **Weekly system:** built + verified end-to-end (live run, negative drift-test, the Windows task executed and regenerated the doc with exit 0). First scheduled run: Mon 2026-06-29 06:17.
- **First review (2026-06-26) already flagged:** P2B windowed bounce 6.3% (over the 5% line), P2A 4.2% (watch), both 0% reply → targeting review; P1 2.6% reply with 2 opps + 2 hot leads to action.
- **Make ops:** known seasonal risk (20k/mo vs September peak) — tracked in blueprint layer G, no platform section in infrastructure.yaml.

---

## Next Steps
1. **Action the P1 hot leads** surfaced by triage: magda@bst-elec.com + creativecastles@outlook.com (ticket-price/theme questions, awaiting reply).
2. **NeverBounce the next P2A loads** (bounce 4.2% watch) and decide on P2B (6.3%, over the line — drip-load rule applies).
3. **Optional:** enable the Monday email by pasting `RESEND_API_KEY=re_...` into `context/.env` (user-gated; key is a GH secret / transcript-only, security-blocked from auto-retrieval — recommend rotating a fresh one).
4. **Next Monday:** complete layers E–I in the auto-written review, then write Gurmej's report from it.
5. The staged ROI-bottleneck strategic message for Gurmej (`next-outbound-deliverables.md`) — P3-live-same-day is now a proof point for it.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/context/weekly-review-blueprint.md` (the process I abide by)
- `workspace/clients/meji-media/context/pilot-routing.md` (live campaign/mailbox routing)
- `workspace/clients/meji-media/context/weekly-reviews/2026-06-26.md` (latest review)

### Open Questions
- RESEND key for the Monday email: rotate fresh vs grant a permission rule to pull the old one from the transcript? (User's call; email is optional.)
- P2B at 6.3% windowed bounce while active: monitor for an auto-pause, or pre-emptively reduce loads?

### Working Notes
- **Instantly rate limit is 20 req/min** — the engine self-throttles (>=3.2s spacing + 35s backoff on 429). A deep run (with cross-campaign dedup) takes ~2.5 min; shallow ~70s.
- **`/emails` endpoint:** `email_type=received` filters server-side to replies (`ue_type=2`); fields include `body`, `content_preview`, `from_address_email`, `ai_interest_value`. This is the layer-D source.
- **Brand-new campaign (0 sends):** windowed AND lifetime analytics return `[]`; pull status from the campaign config object (`/campaigns/{id}`), not analytics.
- **Trend** reads the prior week's `.json` spine from `context/weekly-reviews/`; first run = no deltas (handled).
- CI was abandoned because the engine can't be tracked (client data) and a fresh CI checkout lacks the gitignored `context/.env`.

### Reference Materials
- Plan file: `C:\Users\neuma_p1qrsic\.claude\plans\linear-cooking-lightning.md`
- `docs/INTEGRATIONS.md` (RESEND key provenance: GH secret + 2026-06-06 transcript)

---

## How to Continue
The weekly system is autonomous from Monday. To run it now: `uv run --directory workspace/clients/meji-media/context/analysis-scripts meji_campaign_health_check.py --write-review` (add `--deep` for the dedup pass). Inspect the task with `Get-ScheduledTask MejiWeeklyReview`. P3 is sending; watch P2B's bounce.

---

## Strategic Feedback

### What Worked Well This Session
- The "research first, then ask the 3-way fork" flow on the scheduler: surfacing the public-repo/client-data wall as a real decision (CI-in-secret / local task / manual) rather than silently picking, let you choose the private path fast.
- Verifying behavior, not config: the negative drift-test (feeding the audit a broken config to confirm it FAILs) and triggering the Windows task to confirm it actually regenerates the doc caught more than a config read would.

### Suggestions
- Decide the RESEND-email question once (rotate a key into `context/.env`) so the Monday automation is complete; right now it writes the doc but can't notify.

### System Health
- **Recurring B1 turn-end deferral reflex** fired again (the "if you want, add the key" framing, stop-b1-gate caught it). This is a long-running cluster (2026-05-26 → now); the gate holds every time but the generation-time phrasing reflex persists. Candidate for a `/system-dev` look at the generation side, not just the gate.
- **New transferable lesson:** before planning a CI/scheduled job that runs a script, verify the script is git-tracked and won't leak client data; a gitignored `context/` script can't run in public CI. Cost a built-then-deleted workflow file this session.

---

## Friction Self-Audit
- Autonomy score: 2 human interventions this session (not elevated). Both clustered on the optional Monday-email key.
- Gates: B1 fired repeatedly (tool/CLI checks before asking; stop-b1-gate caught one slip), B2 strong (negative drift-test, task-execution test, no-leakage check), B5 fired on the P3 load+activate (scope-of-effects + readiness audit). skipped: 0.
