# Session Pressure

Track session depth using proxy signals. When pressure is elevated, adapt behavior. Thresholds are estimates calibrated for 1M context — adjust if compaction behavior suggests the effective window is smaller.

## Pressure Signals

Instrumented via `.claude/hooks/session-pressure-meter.py` (PostToolUse, all
tools): it counts tool calls and distinct files this session and emits a
band-crossing advisory ONCE per band, so crossing a threshold no longer
depends on the agent's mental count. The meter keys the session boundary off
the hook payload `session_id` (a new id resets the counters; an unchanged id
across a compaction preserves them), so no SessionStart reset hook is needed.
Query the live reading on demand with `uv run tools/session_state.py
--status`. Mental count is the fallback when the meter is unavailable (e.g. a
fresh clone before the SessionStart wiring runs):

| Signal | Moderate | High | Critical |
|--------|----------|------|----------|
| Tool calls made | 80+ | 150+ | 250+ |
| Distinct files read | 30+ | 50+ | 80+ |
| Build-test-fix iterations (total, all cycles) | 4+ | 6+ | 8+ |
| Major operations completed | 2+ | 3+ | 5+ |
| Work-type transitions | 1+ | 2+ | — |

**Major operations:** A complete skil_build-test-fix cycle, a /system-dev round, a full /comd_deploy cycle, or a cross-client context switch.

## Adaptive Behavior

**Moderate pressure:** Suggest `/comd_checkpoint --mini` at the next natural breakpoint. Shift to concise responses — shorter explanations, fewer exploratory reads, targeted file access over broad exploration. State pressure level at natural breakpoints: "Pressure: moderate. Recommend checkpointing at next breakpoint."

**High pressure:** Strongly recommend `/comd_checkpoint` or `/comd_checkpoint --mini` before continuing. State: "Context pressure is high — recommend checkpointing to preserve work details." Prioritize completing current task over starting new ones. Proactively state pressure level in every response.

**Critical pressure:** STOP. Do not start new work. State: "Context pressure is critical — checkpointing now to prevent work loss." Run `/comd_checkpoint --mini` immediately. After checkpoint, suggest the user start a fresh session with `/resume`. Do not start any task that cannot complete in <10 tool calls.

## Pre-Task Scope Estimation

Before starting a large task, evaluate expected scope:

| Task type | Estimated pressure | Recommendation |
|-----------|-------------------|----------------|
| build-automation (1 spec, simple) | Moderate | Checkpoint at end |
| build-automation (1 spec, complex / >4 phases) | High | Plan checkpoint at phase boundary |
| build-automation (2+ specs) | High | Checkpoint after each spec |
| /system-dev full round | High | Checkpoint after each change group |
| Cross-client context switch mid-session | High | Checkpoint before switching |

When starting a task estimated as **High**, state upfront:
> "This task will likely span high context. Planned checkpoints: after [phase X], after [phase Y]."

This sets expectations and prevents work loss if context compresses before completion.

## Compaction Awareness

The PreCompact hook fires an emergency mini-checkpoint, but it has limited time. To reduce reliance on emergency saves:
1. At **High** pressure, proactively write a mini-checkpoint — do not wait for the hook
2. After any major operation at **Moderate+**, state the pressure level
3. When the user starts a broad task at high pressure, suggest splitting: "This task would push us past safe limits. Recommend: checkpoint now, fresh session, then tackle this."

## Natural Breakpoints

Always evaluate pressure at these moments:
- Completing a skil_build-test-fix cycle (success or escalation)
- Build-orchestrator phase boundary (especially after Phase 3.5 or Phase 5)
- User changing topic or switching clients
- Returning from a sub-agent with significant results
- Transitioning work types (e.g., client-dev → system-infra)