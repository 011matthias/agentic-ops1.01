# Fresh-session prompt — Agent Teams Phase 4: intent-reviewer

Copy-paste the prompt below into a new Claude Code session in this repo (`agentic-ops1`). It is self-contained and references the files the previous sessions left for you.

---

## PROMPT

I want to continue building agent teams in agentic-ops. Today's earlier sessions shipped three specialists across three phases:

- Phase 1: `agnt_comms-critic` (gates `/comd_draft` outputs) + `agnt_done-verifier` (gates `/comd_deploy` outputs). See [docs/2026-05-26 - Agent Teams Phase 1/Mini-Checkpoint-1.md](docs/2026-05-26%20-%20Agent%20Teams%20Phase%201/Mini-Checkpoint-1.md).
- Phase 2: `agnt_make-builder` (Make.com orchestrator specialist). See [docs/2026-05-26 - Agent Teams Phase 2/Mini-Checkpoint-1.md](docs/2026-05-26%20-%20Agent%20Teams%20Phase%202/Mini-Checkpoint-1.md).
- Phase 3: `agnt_n8n-builder` (n8n orchestrator specialist). See [docs/2026-05-26 - Agent Teams Phase 3/Mini-Checkpoint-1.md](docs/2026-05-26%20-%20Agent%20Teams%20Phase%203/Mini-Checkpoint-1.md).

All four agents are uncommitted from those sessions pending review (per `feedback_no_auto_commit`).

This session, build **gap #4 from the original diagnostic: `agnt_intent-reviewer`** — a narrow-scope reviewer that catches `over-literal` / `intent-misalignment` / `strategic-gap` patterns at planning time, before execution.

### Why this gap

Three of the most expensive friction classes in this repo are intent-level, not execution-level. From the friction register:

- **`over-literal`** — taking examples or voice as spec instead of extracting direction. Recurring class: register #5 (Meji Piece 2 four-instance cluster), #15 (Resend email setup with stale tier rule), #102 (named clients in public Upwork profile), #120 (Mailforge cost-anchor drift). The agent treats the user's literal words as the goal instead of asking "what's the underlying intent?"
- **`intent-misalignment`** — built something the user didn't mean. Register #7 (built Track 1 proposal when user's actual convention was Track 2), #123 (info-dumped existing Instantly infra without mapping against the actual pending-campaigns scope). The agent optimized the wrong thing.
- **`strategic-gap`** — didn't question whether to do it before planning how. Register #6 (Meji billing pushback — applied register-1 soft-tone when register-2 polite-firm was the right posture; optimized execution of yielding when the strategy should have been holding). The agent jumped into "how" without auditing "whether".

These three classes share a structural failure mode: the agent's planning phase optimizes for execution efficiency, not directional correctness. There is no second-set-of-eyes between "interpret user input → produce plan" and "execute plan". `agnt_comms-critic` catches this at draft time; `agnt_done-verifier` catches it at deploy time; nothing catches it at PLAN time.

### What to build (decision needed first)

Several open design questions:

1. **Trigger surface — what does this agent gate?** Options, in order of structural strength:
   - **(a) Plan-mode exits.** Before `ExitPlanMode` flushes a plan, route through intent-reviewer. Risk: most planning isn't done in plan-mode (the harness uses informal proposing-then-executing).
   - **(b) User-input classifier.** Run on the user's prompt itself, classify as directive vs exploratory vs mixed, surface the classification + recommended posture. Effectively an early-warning system. Risk: every turn, even trivial ones.
   - **(c) Pre-execution hook on "big" planning artifacts.** Hook fires when the agent writes a plan, design doc, or checkpoint that proposes work direction. Risk: defining "big" is fuzzy.
   - **(d) Explicit `/comd_intent-check` invocation.** User opts in. Risk: only fires when user remembers — doesn't catch the agent's own blind spots.
   - **(e) Internally-invoked by other agents.** build-orchestrator routes the spec through intent-reviewer before Phase 2 runs. Risk: misses non-build planning (proposals, comms strategy, cross-client decisions).

   My recommendation, but redirect me if you disagree: **start with (b) + (e) as v1.** (b) is a thin lightweight pre-turn check that the harness can wire as a PreToolUse on the first tool call of a new turn — analogous to how `stop-b1-gate.py` is a post-turn check; (e) gives the agent a concrete second-eye job inside the build flow. Skip (a) for now (most planning is informal); skip (c) until "big planning artifact" is structurally defined; skip (d) entirely (opt-in defeats the purpose).

2. **Output shape — what does it emit?** The two builder agents emit code-producing build reports; the two critic agents (`agnt_comms-critic`, `agnt_done-verifier`) emit semantic audits. Intent-reviewer is closer to the critic shape: structured findings, no rewrites. Match `agnt_comms-critic`'s pattern: `OK` shape for clean pass, `## Intent findings — N item(s)` for fail-list. Severity HIGH / MEDIUM / LOW. Each finding cites the specific register entry or feedback memory.

3. **The semantic checks — what are the 4-6 categories?** Draft proposal:
   - **Check I1 — exploratory-as-directive.** If the user's input contains hedging ("maybe", "thinking about", "what if", question-shaped framing) AND the agent's plan treats it as a settled directive, flag.
   - **Check I2 — example-as-spec.** If the user provided an example or voice sample AND the agent's plan reproduces the example literally (instead of extracting direction), flag.
   - **Check I3 — strategic-bypass.** If the user's input is broad enough to admit multiple strategies AND the plan picks one without articulating the trade-off, flag.
   - **Check I4 — re-ask-of-stated.** If the plan includes review questions to the user about items the user has already explicitly defined in the conversation, flag (this directly mirrors register #5's Meji Piece 2 cluster).
   - **Check I5 — paraphrase-drift.** If the user supplied specific terminology and the plan paraphrases it into different terms, flag (sibling to `feedback_anchor_on_clients_words`).
   - **Check I6 — posture-mismatch.** If the conversation context is a pushback / negotiation / holding-the-line situation AND the plan adopts a yielding posture (or vice versa), flag (sibling to `feedback_negotiation_posture`).

### Scope ceiling for this session

ONE agent: `agnt_intent-reviewer`. v1. Pick ONE trigger surface (recommended: simulate via explicit `/comd_intent-check {context}` first; add the structural hook in a later phase once the agent's findings are precise enough to wire automatically). Wire ONE invocation path into something concrete (recommendation: `comd_build-automation.md` Phase 1.5, between spec creation and implementation). Smoke-test against the existing fixture pattern at [tools/fixtures/agnt_comms-critic/](tools/fixtures/agnt_comms-critic/). Same pace as the Phase 1-3 sessions: checkpoint and stop after one agent ships green. Don't build memory-recall-enforcer, don't build proposal-research, don't pre-build hooks. Earn each one.

### What to read first

Read these BEFORE writing any code:

1. [.claude/agents/agnt_comms-critic.md](.claude/agents/agnt_comms-critic.md) — closest structural sibling. Match its strict output-shape contract, hard-rules section, source-list footer.
2. [.claude/rules/rule_behaviors.md](.claude/rules/rule_behaviors.md) §"Input interpretation" + §"Self-annealing (Layer 3 — intent review)" + §"Default posture: question the approach before executing" — the rules that define what intent-review IS. The new agent operationalizes Layer 3 from being a checkpoint-only retrospective into a real-time gate.
3. [docs/friction-register.md](docs/friction-register.md) — search for the specific entries cited above (#5, #6, #7, #15, #102, #120, #123) to ground the agent's checks in real incidents.
4. Memory files under `~/.claude/projects/.../memory/`:
   - `feedback_anchor_on_clients_words.md`
   - `feedback_negotiation_posture.md`
   - `feedback_ask_before_assuming_identity.md`
   These are the semantic ground truth the agent enforces.

### Constraints from prior sessions that apply here

- **Self-annealing layer 1 ladder** — memory → structural. This is the structural step for the intent-class memories.
- **Strict output shape.** Match `agnt_comms-critic`: `OK` or `## Intent findings — N item(s)`. No preamble. Every finding cites a memory or register entry by filename.
- **Scope-creep watch.** Phase 1 had a scope-creep event (polishing a working agent after smoke-test passed — register #131). Phase 2 + Phase 3 held the line. Continue the pattern: after the smoke-test goes green, STOP. Do not pre-wire (b) the harness hook; do not also build (c) or (d); do not generalize to gap #5 or #6.
- **Test fixtures pattern.** Persistent fixtures in `tools/fixtures/{agent-name}/`. Re-runnable across sessions. Two fixtures minimum — one with planted intent violations, one clean baseline. Match the agnt_comms-critic fixture shape.
- **Agent registry doesn't refresh mid-session.** Smoke-test via `general-purpose` agent role-playing the spec — same workaround Phase 1/2/3 used.

### Output by end of session

- `.claude/agents/agnt_intent-reviewer.md` — the new agent
- ONE wiring edit (recommended: insert a Phase 1.5 step in `.claude/commands/comd_build-automation.md` that routes the spec through intent-reviewer before Phase 2). If you pick a different invocation path, document why.
- `tools/fixtures/agnt_intent-reviewer/` — at least 2 fixtures (one with planted intent violations exercising I1–I6, one clean baseline) + README.
- Smoke-test results (agent's output on both fixtures, evaluated against expected behavior).
- Mini-checkpoint at `docs/2026-05-26 - Agent Teams Phase 4/Mini-Checkpoint-1.md` (or tomorrow's date if the session starts after midnight).
- Updated `docs/INDEX.md`.

Don't commit until reviewed. Four agents still uncommitted from earlier today; this adds a fifth.

---

## Notes for me (Matthias) when picking up

- The 2 remaining gaps after this session: **#5 proposal parallel research** (concurrent research fan-out for `/comd_new-proposal`) and **#6 memory-recall enforcer** (still blocked on real-use data from the comms-critic — need 3-5 real `/comd_draft` runs first).
- Gap **#3b per-orchestrator testers** stays deferred. The trigger is: route 2-3 real Make or n8n builds through agnt_make-builder / agnt_n8n-builder, then evaluate whether the generic testing-agent is missing orchestrator-specific verification capability. Don't build until that signal arrives.
- The five uncommitted agents (comms-critic, done-verifier, make-builder, n8n-builder, intent-reviewer-after-this-session) can be reviewed and bundled however you want at commit time — they're cleanly separable per session/phase.
- If you want a different Phase 4 instead (Phase 5 proposal-research, or wait on Phase 4 entirely until you've used the existing agents in anger), just say so before pasting the prompt — this prompt is the recommendation, not a lock.
