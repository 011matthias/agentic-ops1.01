# Mini-Checkpoint: Web Build Quality Gates

**Date:** 2026-06-11
**Status:** PR #112 merged to main (7886ffd); follow-ups queued
**Type:** mini

---

## Summary
Researched 5 viral Claude Code repos (2 workflows, 15 agents), mined them
against the web-build pipeline, then implemented both adoption tiers on owner
authorization: skill-prose upgrades + 4 new tools + the deploy gauntlet wiring.
Shipped as PR #112, CI green, auto-merged.

## What Was Done
- Repo research: impeccable (37k★, adopt), agency-agents (110k★, mine-only),
  oh-my-claudecode (36k★, cherry-pick), googleworkspace/cli (27k★, best
  client-work candidate, OAuth-gated), CLI-Anything (43k★, plugin OK /
  cli-hub pip package risky: registry shell=True, telemetry, CDN prompts)
- skil_web-build prose: second-order slop test (DoD 1), 4-step font-selection
  procedure, dated/rotating saturation lists (OKLCH cream band; base palette
  now per-site justified choice per owner decision), TEST.md plan-then-evidence
  (new DoD 23), references/design-thresholds.md, rule:web-* ID anchors
- Tools: audit-local-web-aesthetics.py +9 detector classes + --persist/--trend;
  local-web-deploy.py full gauntlet (aesthetics --strict, axe-check.cjs,
  verify-rendered.cjs NEW, pinned npx impeccable advisory; missing dep = exit 1);
  check-skill-map.py NEW (+ post-write-gate wiring + 3 pytest); 
  web-build-signals.py NEW; check-index.py covers .cjs/.mjs
- Verification: 90 pytest green; audit on all 5 sites (2 calibration fixes from
  real output); axe + rendered probes green on live praxis-uslu; hook advisory
  fired on drifted skill; gate chain caught REAL live-origin drift

## Current Status
Main at 7886ffd carries the full gate stack. Live fly.dev origin is one build
behind current source (caught by the new parity gate). The 5 sites score
85-100 on the new audit; Fraunces/Newsreader now WARN as saturation-tier
(BRIEFs lack the required selection trace).

## Next Steps
1. Bundle + redeploy local-web (owner order): fix impeccable nits (01/02/03
   numbered section markers on helmle/meinzer/praxis; meinzer thick-border/
   radius clash), backfill font-selection traces in Fraunces/Newsreader BRIEFs,
   then `uv run tools/local-web-deploy.py` runs the new gauntlet for real
2. /comd_system-dev: burn down check-skill-map backlog (105 pre-existing
   findings, 32 first-party skills, pack-consolidation drift; fix-on-touch
   hook already active)
3. Port the rule-ID->detector pattern to rule_anti_slop's listed enforcement
   candidates (symmetry-collapse / per-category-narration in validate-output.py)
4. gws adoption when Route-2 Gmail/Sheets work recurs — blocked on owner
   Google Cloud project + OAuth; needs an invasive-send PreToolUse gate first

## Files to Read First
- .claude/skills/skil_web-build/SKILL.md (DoD 1/17/23 changed; session entry
  now starts with tools/web-build-signals.py)
- tools/local-web-deploy.py (the gauntlet; deploy = gated floor)
- Workflow research outputs: full repo verdicts in the 2026-06-11 session
  transcript (workflow runs wj4ee5mo7 + wzk6j5zbj)
