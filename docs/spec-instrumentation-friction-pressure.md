# Spec: Session Instrumentation — Friction Candidate-Capture + Pressure Rigor

Status: DRAFT (awaiting owner review before build)
Created: 2026-06-03
Scope: system (`.claude/hooks/`, `tools/`, `wire-hooks.py`, `rule_session-pressure.md`, `comd_checkpoint.md`)
Delete on: implementation complete (per `rule_no_file_bloat` supersession discipline)

## Problem (shared root)

Two systems both depend on **agent recall** where they should depend on
**instrumentation**:

1. **Friction noticing.** `gate-skip-detector.py` already *detects* three
   signal classes and tags them `friction-event:gate-skip-{kind}` — but the
   tag lands in freeform `hook-log.txt` and `/comd_checkpoint`'s Friction
   Self-Audit never reads it. It re-derives friction by re-reading the
   conversation. Detections evaporate.
2. **Session pressure.** `rule_session-pressure.md` says outright: *"Mental
   count — no runtime state file needed."* The thresholds (80/150/250 tool
   calls, 30/50/80 files) cannot be tracked reliably by mental count. The
   only real backstop is the reactive PreCompact emergency checkpoint.

The fix for both is the same shape: **a PostToolUse meter maintains
session state; the harness emits an advisory when a band/signal crosses;
classification stays a judgment step.** Detection auto, judgment manual.

## Design principle (non-negotiable)

- **Detection is automated. Classification is not.** The candidate buffer
  holds *candidates*, never auto-promoted register rows. This is the guard
  against the noise / false-precision failure mode: the valuable friction
  categories (`verification-theater`, `over-literal`, `strategic-gap`) are
  not mechanically detectable and must stay reflective. We only auto-capture
  the detectable subset, and a human/agent promotes or discards at checkpoint.

---

## Part A — Friction candidate-capture

### A1. Unified session-state file (shared with Part B)

One JSON file, session-scoped, in tempdir (transient working state — NOT
committed, per `rule_no_file_bloat`):

`{tempdir}/agentic-ops-session-state.json`

```json
{
  "session_started": "<iso8601>",
  "tool_calls": 0,
  "distinct_files": [],          // Read/Edit/Write file_path args, deduped
  "bash_iterations": 0,          // near-identical Bash cmds (fix-loop proxy)
  "pressure_band_emitted": null, // "moderate"|"high"|"critical"
  "candidates": [                // friction candidates (Part A)
    {
      "ts": "<iso8601>",
      "signal": "gate-skip-pre-publish",
      "source_hook": "gate-skip-detector",
      "context": "<=300 chars raw"
    }
  ]
}
```

Rationale for one file, not three: `gate-skip-detector.py` already owns a
30-entry Bash ring buffer in tempdir. Rather than spawn parallel state files,
consolidate. A new all-tools PostToolUse hook owns this file; gate-skip-detector
reads/writes the `candidates` and `bash_iterations` keys through a shared helper.

### A2. Shared helper: `tools/session_state.py`

A tiny importable module (NOT a hook) so every hook writes the same schema:

- `load()` / `save(state)` — atomic read/modify/write with file lock fallback
- `add_candidate(signal, source, context)` — append, dedup identical
  (signal, context) within the session
- `bump_tool(tool_name, file_path=None)` — increment counters, track files
- `reset()` — called on SessionStart (new, non-compact)

Defensive: every function swallows errors and no-ops (hooks must never break
the tool call). Mirrors gate-skip-detector's `except: pass` discipline.

### A3. Signals captured (detectable subset only)

| Signal | Source hook | Already detected? |
|---|---|---|
| `gate-skip-pre-publish` | gate-skip-detector | Yes — route to buffer |
| `gate-skip-live-system` | gate-skip-detector | Yes — route to buffer |
| `gate-skip-iteration-3x` | gate-skip-detector | Yes — route to buffer |
| `gate-fired-no-auto-commit` | no-auto-commit-gate | No — add `add_candidate` call when it returns `ask` |
| `gate-fired-instantly-invasive` | instantly-invasive-gate | No — add `add_candidate` call when it returns `ask` |

That's the whole list. No "process failed" catch-all — that axis was
rejected in design review (would miss `verification-theater`, where the
process *succeeds*, and flood the register with transient/first-pass noise).

### A4. Reconciliation at `/comd_checkpoint` (the judgment step)

Add to the **Friction Self-Audit** section of `comd_checkpoint.md` (currently
line ~52, which only reviews the conversation):

> **0. Drain the candidate buffer.** Run `uv run tools/session_state.py
> --list-candidates`. For each candidate: classify (assign type, name which
> gate B1–B6 applies, run the existing regression grep) and promote to a
> register row, OR discard with a one-line reason if it was a true-positive
> gate doing its job (not friction). Then `--clear-candidates`.

A candidate is NOT automatically friction. A no-auto-commit gate firing
*correctly* (agent paused, asked, user authorized) is the system working —
discard. A gate firing because the agent tried to ship unprompted *is*
friction — promote. The buffer surfaces the event; the agent judges it.

### A5. Relationship to `friction-watch.py`

Complementary, different stages. `friction-watch.py` is a meta-watcher over
the **register** (post-classification: concentration, recurrence, staleness).
Candidate-capture is **pre-classification**, feeding the register. No overlap.

---

## Part B — Session-pressure rigor

### B1. New hook: `session-pressure-meter.py` (PostToolUse, matcher `""`)

All-tools (not just Bash). On each call: `session_state.bump_tool(tool, path)`.
Then check thresholds from `rule_session-pressure.md` table:

| Band | Tool calls | Distinct files |
|---|---|---|
| moderate | 80+ | 30+ |
| high | 150+ | 50+ |
| critical | 250+ | 80+ |

When a band is first crossed (dedup via `pressure_band_emitted` so it fires
**once per band**, not every call), emit `additionalContext`:

```
[PRESSURE: HIGH] 152 tool calls, 54 distinct files this session.
rule_session-pressure: strongly recommend /comd_checkpoint before continuing.
```

This converts the rule from "agent must remember to count" (Layer 3, recall)
to "harness reports the band at decision time" (Layer 1, structural). Critical
band's advisory instructs immediate `/comd_checkpoint --mini`.

### B2. Reset on session start

Add to the existing SessionStart hook block (the `wire-hooks.py --ensure`
step runs there already): on a non-compact start, call
`session_state.reset()`. On a `compact` restart, preserve counts (the session
continues). The existing `matcher: "compact"` vs `matcher: ""` split in
`settings.json` already distinguishes these.

### B3. On-demand query + header/checkpoint integration

- `tools/session_state.py --status` → prints current band + counts, for the
  agent to query on demand.
- `rule_session-start.md` session header `Open:` line gains a pressure read
  when a meter exists.
- PreCompact emergency checkpoint stays as the last-resort backstop (reactive).

### B4. Rule edit: `rule_session-pressure.md`

Change the opening from *"Mental count — no runtime state file needed"* to:
*"Instrumented via `session-pressure-meter.py`; the meter emits a band-crossing
advisory once per band. Mental count is the fallback when the meter is
unavailable (e.g. a fresh clone before SessionStart wiring runs)."*

---

## Wiring (both parts) — `tools/wire-hooks.py`

`CANONICAL_HOOKS` is an exact-match contract (`_intact` compares
`present == CANONICAL_HOOKS`). New hooks MUST be added there or `--ensure`
wipes them. Deltas:

1. Add `session-pressure-meter.py` under `PostToolUse` matcher `""` (new block).
2. Count moves **11 → 12 hooks**. Update every "11" literal in `wire-hooks.py`
   (docstring line 5, the `_loud`/print strings at ~243/258/273) and the
   SessionStart success message.
3. `session_state.py` and the `--list-candidates/--clear-candidates/--status`
   CLI go in `tools/` with a `tools/INDEX.md` entry.
4. No change to `no-auto-commit-gate.py` / `instantly-invasive-gate.py`
   control flow — only an `add_candidate(...)` side-effect call on the
   `ask`-decision branch (must not alter the returned decision).

## Build order

1. `tools/session_state.py` + CLI + INDEX entry (foundation, both parts).
2. `session-pressure-meter.py` + wire (Part B — self-contained, testable first).
3. Route gate-skip-detector's 3 existing tags through `add_candidate`.
4. Add `add_candidate` to the two PreToolUse gates.
5. `comd_checkpoint.md` reconciliation step (A4).
6. `rule_session-pressure.md` edit (B4).
7. Smoke fixtures under `tools/fixtures/session-state/` (mirror the
   no-auto-commit-gate fixture pattern): assert band emission once-per-band,
   candidate dedup, reset-on-start.

## Verification (B2 — behavior, not config)

- Drive a synthetic transcript past each band; assert exactly one advisory
  per band crossing (not per call).
- Fire each of the 5 signals; assert a candidate row with correct schema; run
  `--list-candidates`; assert `--clear-candidates` empties it.
- Confirm `wire-hooks.py --check` reports 12/12 after wiring.
- Confirm the two gates' decisions are byte-identical before/after the
  `add_candidate` side-effect (the capture must not change gate behavior).

## Open questions for owner

1. Tempdir vs `docs/sessions/` for the state file. Recommend tempdir
   (transient; committing it violates no-file-bloat). Candidates that matter
   survive as promoted register rows.
2. Should `critical` pressure *hard-block* new non-checkpoint work via a Stop
   hook, or stay advisory? Recommend advisory first; escalate to a soft gate
   only if a critical-band overrun recurs (don't build the gate from zero
   incidents).
3. Consolidate gate-skip-detector's existing Bash ring buffer into
   `session-state.json` now, or leave it parallel and only add the new keys?
   Recommend consolidate (one session-state file) to prevent the exact hook
   sprawl this spec is trying to avoid.
