# Checkpoint: Meji Media Leak Sweep

**Date:** 2026-07-16
**Status:** All 9 brief items worked; 3 staged awaiting owner yes (B5/invasive), rest resolved or on documented watch.

---

## Summary
Worked the 9 open leaks/risks from the 2026-07-16 intelligence brief autonomously (read-only + internal only): re-verified the P1 sender outage, mapped the OpenAI key exposure, audited DMARC posture on both cold domains, generated and hand-filled the pounds weekly report, and did a full refresh of the stale risk register. Three invasive actions (lead stop-flags, DMARC DNS writes, key rotation) are staged and explicitly gated on the owner.

---

## What Was Done This Session

### Diagnostics (all read-only, per Instantly-gate/B5)
1. Re-pulled Instantly `/api/v2/accounts` — confirmed `gurmej@mejimedia.com` still status `-1` (all 14 other senders healthy). Root cause held: Gurmej's Wednesday login change broke the mailbox auth in Instantly only — separately verified Make's Google OAuth connections (12352178, 13923632) were unaffected (A0-A3 all ran status 1 through the change window).
2. Queried `MejiWeeklyReview` scheduled task (PowerShell, read-only): still `LastTaskResult 3221225786` (0xC000013A) from 07-13; no 07-13 output written; next trigger intact for 07-20 06:17. Classifier blocks me from firing it manually.
3. Swept blueprints of all 12 team scenarios in the production Make org for `ai_api_key` / DS 153173 / OpenAI usage. Exactly two readers found: A1 (8804011) and A3 (8804014), both module 70, raw HTTP POST to `api.openai.com/v1/chat/completions`, key mapped from `{{50.ai_api_key}}` / `{{62.ai_api_key}}`. An existing `openai-gpt-3` connection (12352371) is unused by either live scenario.
4. Checked DMARC TXT records live via DNS for all 7 meji-family domains + `christmasofficeparty.co.uk`. Confirmed `mejievent.com` and `mejixmas.com` are `p=none`; found two more (`mejiai.com`, `banterexp.com`) also `p=none`, and `mejimedia.co` has no SPF/DKIM/DMARC at all (matches the 3 dead legacy `.co` Instantly senders). Verified SPF+DKIM alignment on all `p=none` domains (all pass, so quarantine is safe to stage). Verified Porkbun API read access to `mejixmas.com` DNS (works); `mejievent.com` is out of our Porkbun account scope.
5. Looked up Charlotte Booth and Rebecca Mason in live Instantly leads across both the live P1 campaign (`00fc708d`) and the dormant legacy campaign (`1f40cb36`) — both present in both, confirming the B5 stop-flag ask covers two campaigns per lead.

### Deliverables generated
6. Ran `meji_campaign_health_check.py --client-report` (live Instantly pull) → `context/drafts/weekly-report-2026-07-20.md`. Hand-filled all `{SLOT}` judgment markers (headline win = Four Car Audio booking, watch = sender outage, next-week items) from verified facts already in context/comms-log.md. Left the hours/contacts-per-hour lines as `TBD` — genuinely blocked on this week's `hours-log.json` entry, not fillable from any source. Linted clean (`tools/lint-comms-draft.py`, 0 hits).
7. Rewrote `context/risk-register.md` (stale since 2026-05-12, 65 days). Retired 10 dead entries (transition risks, resolved operational risks) to a one-line summary with git-history pointer. Added 6 new entries reflecting live findings: single-sender fragility (IR-06), login-change-breaks-Instantly-not-Make (OR-06), the OpenAI key exposure + staged rotation plan (OR-07), DMARC posture + staged rollout (IR-07), the HubSpot ROI-visibility gap on Version C (IR-08), the $589.60 bonus settlement risk (CR-03), and the deliberately-deferred temp Super Admin deletion (CR-04).

---

## Key Decisions Made

### Three items left invasive-gated, not executed
- **Choice:** Stop-flagging Charlotte Booth/Rebecca Mason (B5 lead updates), applying the staged DMARC DNS records, and rotating the OpenAI key were all fully investigated/staged but NOT executed.
- **Rationale:** User's brief explicitly named these three as requiring an explicit yes up front (B5) or being invasive (DNS writes, live Make scenario edits touching client-facing sends). No ambiguity here — held the line per `rule_instantly_invasive.md` / `rule_behaviors.md` B5.

### DMARC rollout staged in steps, not a single jump to enforce
- **Choice:** Recommended pct=25 → 50 → 100 over 3 weeks rather than jumping straight to `p=quarantine; pct=100`.
- **Rationale:** No read access to the client-owned `rua` aggregate reports, so staged pct substitutes for the report-review step that would normally catch a live alignment problem before it bites real mail.

### Pounds report used today's data, not held for Monday
- **Choice:** Generated and filled from the 2026-07-16 pull rather than waiting for a fresh 07-20 pull.
- **Rationale:** Task said "due Mon 07-20"; staging it now means it's ready ahead of time. Flagged explicitly to the user that a Monday re-run will overwrite the `{SLOT}` judgment fills, so a final pass is needed before send.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/drafts/weekly-report-2026-07-20.md` | Created | Staged pounds weekly report, judgment slots hand-filled, lint-clean |
| `workspace/clients/meji-media/context/risk-register.md` | Rewritten | Full refresh: 10 stale entries retired, 6 new entries from this session's findings |

Not modified by me (parallel session / user, noted not reverted): `workspace/clients/meji-media/context/.env` gained a `BOOKINGS_MAILBOX_PASSWORD` line — confirms the approved second-inbox build (bookings@christmasofficeparty.co.uk) landed during this session.

---

## Current Status

All 9 brief items closed to either "resolved," "staged pending owner yes," or "on documented watch, not chased." No client-facing sends occurred. No Make/Instantly mutations occurred (everything was GET or read-style POST). Platform: no `platform:` section in meji-media's `infrastructure.yaml` (Make.com-only client) — ops-audit not applicable this session.

---

## Next Steps

1. **Owner decision — B5 stop-flags:** Charlotte Booth + Rebecca Mason, both campaigns (`00fc708d` live + `1f40cb36` legacy). Two reversible lead updates, no sends. Say yes to execute.
2. **Owner decision — DMARC DNS:** apply staged `p=quarantine; pct=25` to `mejixmas.com` via our Porkbun API on yes; `mejievent.com` needs Gurmej to apply it or grant API access (LIMITATION noted, his action).
3. **Owner decision — OpenAI key rotation:** needs a fresh key from the key owner, then I execute the staged swap-to-connection plan in OR-07 (2 live scenario edits, each behavior-verified per OR-02 lesson).
4. **P1 sender:** if still `-1` tomorrow (07-17), send the soft nudge per the brief; log to comms-log when it flips to 1.
5. **Weekly-review task:** run `Start-ScheduledTask MejiWeeklyReview` manually if you haven't (classifier blocks me); verify `weekly-reviews/2026-07-20.*` + `LastTaskResult 0` land after Monday.
6. **Pounds report:** before sending, re-check the `TBD` hours lines once `hours-log.json` has this week's entry; if pulling fresh Monday data, re-fill the `{SLOT}` judgment lines from the new pull.
7. Post-07-20 Make reset: report back whether the 20k-op cap was hit; only plan-bump if the NEXT cycle also lands at/over cap.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/risk-register.md` (fully refreshed, canonical state)
- `workspace/clients/meji-media/context/drafts/weekly-report-2026-07-20.md` (staged, needs hours fill + owner send)
- `workspace/clients/meji-media/context/comms-log.md` (2026-07-16 entries — source of truth for what's already resolved)

### Open Questions
- Whether Gurmej also self-serves the 14 lookalikes in HubSpot or wants us to run them (do not chase, let it surface — per IR-08).
- Whether to include the dormant legacy campaign (`1f40cb36`) in the Charlotte/Rebecca stop-flag action — recommended yes (same action, prevents accidental resume) but user hasn't confirmed scope.

### Working Notes
- Instantly API calls need a non-default `User-Agent` header (e.g. `meji-ops/1.0`) — the bare `Bearer` request 403s otherwise. This is the same class as the previously-memoried Resend User-Agent issue; worth a dedicated memory (see Strategic Feedback below) rather than rediscovering per script.
- Make blueprint sweep technique: `GET /api/v2/scenarios/{id}/blueprint` per scenario id, then grep the raw JSON text for the target field name + connection type — fast and reliable for "which scenarios touch X" questions across a whole team.
- DMARC alignment check (SPF `include:_spf.google.com` + live `google._domainkey` selector) is a fast pre-flight before recommending any `p=quarantine`/`p=reject` step; do this before staging on any future domain.

### Reference Materials
- `workspace/clients/meji-media/context/pilot-routing.md` — campaign UUID → piece mapping (used to confirm Charlotte/Rebecca campaign identity)
- `workspace/clients/meji-media/context/analysis-scripts/meji_campaign_health_check.py` — the weekly report generator, `--client-report` mode

---

## How to Continue
Open a fresh session with `/resume meji-media`. The three gated decisions (stop-flags, DMARC, key rotation) are the live fork — get an explicit yes/no on each before doing anything else invasive. Everything else from the 07-16 brief is closed or on watch.

---

## Strategic Feedback

### What Worked Well This Session
- Framing all 9 items as a todo list up front made the read-only/gated split mechanical to execute — nothing invasive got touched, and every gated item had its investigation already done by the time the owner needs to decide.

### Suggestions
- Save a feedback memory on the Instantly `User-Agent` 403 requirement — this is the second time (after the Resend discovery) that a non-default UA has been needed for an external API in this repo, and it's cheap to codify so future scripts don't rediscover it via a stack trace.

### System Health
- **Friction:** stop-b1-gate caught a deferral-shaped closing ("...say if you want it included" for the legacy-campaign scope question) in the first attempt at the final summary; reframed to explicit decision points in the same turn. Regression — this is the most-logged friction class in `docs/friction-register.md` (matches 2026-07-13, 2026-05-19, 2026-05-26, 2026-07-11 x2 entries); the hook catches reliably every time, but the generation reflex toward soft offers is unchanged session over session. Worth eventually promoting to a pre-generation self-check rather than a post-hoc catch (per the 2026-05-26 register entry's suggested fix).
- **Gates:** B1:6 (checked live API/task-state/blueprint/DNS/Porkbun/leads before any user-facing question) B2:5 (verified sender status, task result, key readers, DMARC records, and lint pass before reporting each as done) B3:1 (read the full 403 traceback, checked own script vs a known-working prior script before concluding UA was the cause) skipped:1 (the B1 closing-deferral above, caught by the hook, not by the user)
- Autonomy score: 1 human intervention this session (the stop-hook catch, self-corrected same turn — no user redirect was needed).
