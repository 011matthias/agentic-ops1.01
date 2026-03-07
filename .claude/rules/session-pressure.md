# Session Pressure

Track session depth using proxy signals. When pressure is elevated, adapt behavior.

## Pressure Signals

Mental count — no runtime state file needed:

| Signal | Moderate | High |
|--------|----------|------|
| Tool calls made | 60+ | 100+ |
| Distinct files read | 25+ | 40+ |
| Build-test-fix iterations (total, all cycles) | 4+ | 6+ |
| Major operations completed | 2+ | 3+ |
| Work-type transitions | 1+ | — |

**Major operations:** A complete build-test-fix cycle, a /system-dev round, a full /deploy cycle, or a cross-client context switch.

## Adaptive Behavior

**Moderate pressure:** Suggest `/checkpoint --mini` at the next natural breakpoint. Shift to concise responses — shorter explanations, fewer exploratory reads, targeted file access over broad exploration.

**High pressure:** Strongly recommend `/checkpoint` or `/checkpoint --mini` before continuing. State: "Context pressure is high — recommend checkpointing to preserve work details." Prioritize completing current task over starting new ones.

## Natural Breakpoints

Always evaluate pressure at these moments:
- Completing a build-test-fix cycle (success or escalation)
- Build-orchestrator phase boundary (especially after Phase 3.5 or Phase 5)
- User changing topic or switching clients
- Returning from a sub-agent with significant results
- Transitioning work types (e.g., client-dev → system-infra)
