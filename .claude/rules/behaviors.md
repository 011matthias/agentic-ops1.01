# Core Behaviors

**Self-annealing:** After every fix or build → ask "how do I prevent this error category?" If preventable AND recurrent → operationalize via `meta-builder` skill (read DECISION-TREE.md first). Dedup check before creating. Check in with user. If too niche → document in checkpoint instead.

**Outcome verification:** Successful execution ≠ correct data. Define expected outcomes BEFORE executing. Verify actual outcomes AFTER (field by field). Use proxy indicators (transfer bytes, operation counts) when direct reads aren't possible.

**Build escalation:** First 3 iterations → autonomous fix via `build-test-fix` FIX-PATTERNS. After 3 same-category failures → escalate with full diagnosis. Novel errors → escalate immediately. Never retry the same fix twice.

**Test fixtures persist.** Namespaced `UTIL -` or `TEST -`. Documented in `context/test-fixtures.md`. Reused across sessions, never deleted.

**Strategic feedback:** At every `/checkpoint` surface: (1) what worked well (specific), (2) one actionable suggestion, (3) one system health observation. Direct, constructive, with examples.

**AI models (code-first only):** Single source of truth in `app/config.py`: `settings.get_ai_model("operation")`. Override via env: `AI_MODEL_{OPERATION}=provider/model`. Default: `openai/gpt-4o-mini`. Make.com/n8n configure AI in their respective modules.

**Always automate.** Never ask "manual or automated?" — always choose the automated path. The system is moving toward full automation.

**Autonomous-first diagnostics:** Before asking the user to check, verify, or do anything: (1) check `context/test-fixtures.md` for fixtures that can read/write the target system, (2) check `tools/` for scripts that can perform the operation (e.g., `make-api.py`), (3) exhaust the AUTONOMOUS-DIAGNOSTICS skill module. Only escalate to the user after all autonomous paths have been attempted and documented.

**Friction self-detection:** When the user corrects your approach, provides info you could have found autonomously, or performs a task you could have automated — that is a friction event. Types: `agent-deferred` (asked user to do something automatable), `missed-tool` (tool existed but wasn't used), `redundant-escalation` (escalated when autonomous fix was available). Log at `/checkpoint`.

**Session continuity:** Checkpoints preserve context that compaction destroys. At natural breakpoints (task completion, topic change, build cycle end), evaluate session pressure and suggest checkpointing proactively. Mini-checkpoints (`/checkpoint --mini`) are preferred over no checkpoint. See session-pressure rule for signals.
