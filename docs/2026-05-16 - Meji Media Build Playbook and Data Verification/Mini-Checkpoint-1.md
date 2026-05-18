# Mini-Checkpoint: Instantly API Unlock + Campaign Map + Invasive Gate

**Date:** 2026-05-16
**Status:** Instantly API live and fully scoped. Warm audiences identified by campaign ID. Analytics work paused for fresh session.
**Type:** mini

Delta since `Checkpoint.md` (same folder — read that first for the full session).

---

## Summary

Instantly V2 API key created, fixed (missing `=` separator in .env), validated live, all 6 needed scopes confirmed 200. Discovered the warm "audiences" are campaigns not lead-lists (0 lead-lists exist) and pulled the full campaign map with IDs. Built and registered the invasive-action safety gate (rule + hook). Stopped at: getting exact warm-audience lead counts.

## What Was Done

- **Instantly API key:** stored in `workspace/clients/meji-media/context/.env` as `INSTANTLY_API_KEY` (gitignored — whole `context/` dir is ignored, verified). User pasted it; the `=` separator was dropped on paste, fixed programmatically.
- **Key validated (live, HTTP 200):** scopes all working — campaigns, accounts, lead-lists, leads/list, emails, campaigns/analytics. Key does NOT need recreating.
- **Campaign map (the warm DB is campaigns, NOT lead-lists — 0 lead-lists exist):**
  - `Meji Media - Christmas Bookers` — id `1f40cb36-c62c-4569-95bd-692709512c9c` — status 1 (active) → **D1 target**
  - `Banter reactivation - Booked` — id `c83adc69-298f-4be5-94b7-41bf60f4248e` — status 3 (completed) → **D2 target**
  - `MejiAI | Construction, HVAC, Plumbers, Electricians` — id `d5db8ea5-085c-4e7b-99a6-a3b5c59be6cc` — status -2 (paused, PARKED)
  - `Meji Media | Corporate Events | Big Companies in UK` — id `245913f7-2345-40c8-ad7d-93a2edf6fd28` — status -2 (paused)
  - `Event Management Companies | Chatbots | Vayne` — id `486e263f-b9ce-4647-b44c-0acdfc36e751` — status 2 (paused)
- **Invasive-action gate built:** `.claude/rules/rule_instantly_invasive.md` (B5, always-loaded) + `.claude/hooks/instantly-invasive-gate.py` (PreToolUse:Bash, pipe-tested 4 cases) + registered in `.claude/settings.json` (validated, all prior hooks preserved). Read-only Instantly = autonomous; any state-changing call = scope-of-effects-in-plain-language + explicit user confirmation, hook forces a permission stop.

## Current Status

- API unlock proven. The playbook's `[M]` manual Instantly layer is now largely `[A]` automatable.
- **Playbook correction pending:** D1/D2 step 1 is "pull campaign leads via API", NOT "export a lead-list" (`seven-deliverables-playbook.md` + `christmas-warm-rebuild-plan.md` still say audience/lead-list export).
- Stopped at the iteration hard-cap (3 read-only discovery calls — blunt-instrument cap-hit on non-fix exploration; noted, not a real fix loop).

## Next Steps (resume here)

1. **`GET https://api.instantly.ai/api/v2/campaigns/analytics`** per campaign for the two warm IDs above — gets leads_count / contacted / sent in one call (the `leads/list` endpoint is cursor-paginated with NO total, so don't paginate; use analytics). This same call establishes the D7 weekly-report payload shape — nail it once.
2. Update `seven-deliverables-playbook.md` + `christmas-warm-rebuild-plan.md`: warm DB = campaign leads (with the IDs above), not lead-lists; mark which `[M]` steps are now `[A]`.
3. Then D1: pull Christmas Bookers leads, MySQL-enrich, 4-segment split, recognition-first sequence copy.
4. Still user-side: send the 2 Upwork messages + `reply-to-gurmej-2026-05-16.md`; log comms entry 13.

## Files to Read First

- docs/sessions/2026-05-16-context.yaml
- docs/2026-05-16 - Meji Media Build Playbook and Data Verification/Checkpoint.md (full session)
- docs/2026-05-16 - Meji Media Build Playbook and Data Verification/Mini-Checkpoint-1.md (this, the delta)
- workspace/clients/meji-media/context/seven-deliverables-playbook.md
- workspace/clients/meji-media/context/christmas-warm-rebuild-plan.md
- .claude/rules/rule_instantly_invasive.md (B5 — invasive Instantly protocol now in force)

**Key auth note:** `INSTANTLY_API_KEY` is in `workspace/clients/meji-media/context/.env` (gitignored). Read it with `grep '^INSTANTLY_API_KEY=' <path> | cut -d= -f2-`. Read-only API calls are autonomous; any mutating call triggers the B5 gate (scope-of-effects + explicit confirmation).
