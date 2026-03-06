# Core Behaviors

**Self-annealing:** After every fix or build → ask "how do I prevent this error category?" If preventable AND recurrent → operationalize via `meta-builder` skill (read DECISION-TREE.md first). Dedup check before creating. Check in with user. If too niche → document in checkpoint instead.

**Outcome verification:** Successful execution ≠ correct data. Define expected outcomes BEFORE executing. Verify actual outcomes AFTER (field by field). Use proxy indicators (transfer bytes, operation counts) when direct reads aren't possible.

**Build escalation:** First 3 iterations → autonomous fix via `build-test-fix` FIX-PATTERNS. After 3 same-category failures → escalate with full diagnosis. Novel errors → escalate immediately. Never retry the same fix twice.

**Test fixtures persist.** Namespaced `UTIL -` or `TEST -`. Documented in `context/test-fixtures.md`. Reused across sessions, never deleted.

**Strategic feedback:** At every `/checkpoint` surface: (1) what worked well (specific), (2) one actionable suggestion, (3) one system health observation. Direct, constructive, with examples.

**AI models (code-first only):** Single source of truth in `app/config.py`: `settings.get_ai_model("operation")`. Override via env: `AI_MODEL_{OPERATION}=provider/model`. Default: `openai/gpt-4o-mini`. Make.com/n8n configure AI in their respective modules.

**Always automate.** Never ask "manual or automated?" — always choose the automated path. The system is moving toward full automation.
