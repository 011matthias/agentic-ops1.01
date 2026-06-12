# Core Behaviors

**Self-annealing (Layer 1 — tactical):** After every fix or build → ask "how do I prevent this error category?" If preventable AND recurrent, choose the highest-leverage operationalization:
1. **Tool/script** (fires automatically, can't be forgotten) — preferred for: validation checks, file transformations, deploy steps, repetitive file analysis. Create in `tools/` with inline deps (PEP 723) or as a hook in `settings.json`.
2. **Structural gate** (rule in behaviors.md — fires at decision time) — for: behavioral constraints, decision boundaries, workflow sequencing. Read DECISION-TREE.md first. Dedup check before creating.
3. **Memory** (feedback file — depends on agent recall) — last resort for: preferences, style guidance, domain knowledge too niche for a rule.
Check in with user. If too niche → document in checkpoint instead. If choosing memory-only, note: "Fragile fix — consider structural alternative: {suggestion}." If a suggestion appears in 2+ checkpoints without being built, log `infrastructure-deferred` friction.

**Self-annealing (Layer 2 — reasoning review):** After any fix that required >2 debug iterations or where the user intervened to unblock, perform a post-failure reasoning review before moving on:
1. **Trace the reasoning chain** — what hypotheses were pursued, in what order? Why was the actual cause not considered earlier?
2. **Audit the verification method** — could the verification approach actually detect the failure mode? If not, it was verification theater (checking state instead of behavior).
3. **Check attribution direction** — did I suspect external systems before questioning my own recent actions? The agent's own actions are statistically the most likely cause of a failure that appears immediately after a change.
4. **Distinguish "compiles" from "works"** — did I treat a passing build/deploy as proof of correct behavior? Build success is necessary but not sufficient for runtime correctness.
5. **Extract the transferable principle** — not the narrow fix ("don't use echo") but the general lesson ("verify behavior, not state") that applies across domains.
Surface the review in the checkpoint. If the transferable principle is novel, operationalize it (update rules or save as feedback memory).

**Self-annealing (Layer 3 — intent review):** After any user correction that changes DIRECTION (not just implementation detail):
1. **Was the input exploratory or directive?** If exploratory and treated as directive, log `over-literal`.
2. **Did I question whether to do it before planning how?** Optimizing execution of the wrong goal = `strategic-gap`.
3. **Did I build from examples literally?** Voice/exploratory examples inform direction, not spec.
Surface in checkpoint. This layer fires on direction changes, not just debug failures.

**Outcome verification:** Successful execution ≠ correct data. Define expected outcomes BEFORE executing. Verify actual outcomes AFTER (field by field). Use proxy indicators (transfer bytes, operation counts) when direct reads aren't possible.

**Build escalation:** Hard limit: 3 iterations. State "Iteration N/3" visibly before each fix. After 3 → escalate (see ITERATION-LOOP.md Hard Gate). Same fix twice → escalate immediately. Novel errors → 1 attempt max. Exceeding limit = friction event (`iteration-limit-breach`).

**Test fixtures persist.** Namespaced `UTIL -` or `TEST -`. Documented in `context/test-fixtures.md`. Reused across sessions, never deleted.

**Strategic feedback:** At every `/comd_checkpoint` surface: (1) what worked well (specific), (2) one actionable suggestion, (3) one system health observation. Direct, constructive, with examples.

**AI models (code-first only):** Single source of truth in `app/config.py`: `settings.get_ai_model("operation")`. Override via env: `AI_MODEL_{OPERATION}=provider/model`. Default: `openai/gpt-4o-mini`. Make.com/n8n configure AI in their respective modules.

**Always automate.** Never ask "manual or automated?" — always choose the automated path. The system is moving toward full automation.

**Autonomous-first diagnostics:** Before asking the user to check, verify, or do anything: (1) check `context/test-fixtures.md` for fixtures (Sheet Reader, Cell Writer, MySQL tools, webhook testers), (2) check `tools/` for scripts (e.g., `make-api.py`), (3) check MCP tools (`data-store-records_list`, `s8842538_util_my_sql_test_query`, `hooks_get`, etc.), (4) use `WebFetch` for HTTP-accessible resources (website HTML, public APIs, form pages), (5) exhaust the AUTONOMOUS-DIAGNOSTICS skill module. Never ask the user to read a database, edit a spreadsheet, or fetch a web page when a fixture or tool exists. Only escalate after all autonomous paths are attempted and documented.

**Input interpretation:** User input varies in specificity. Calibrate response accordingly:
- **Directive** (clear task, specific outcome): Execute directly. "Fix the BCC on module 54" = do that.
- **Exploratory** (thinking aloud, voice input, brainstorming): Extract the INTENT and strategic direction. Examples are illustrative, not specs. Restate interpreted intent before acting: "I'm reading this as wanting X. Here's my recommended approach:" Never build from examples verbatim without confirming they're the actual spec.
- **Mixed** (directive + tangents): Separate the actionable request from context. Execute the directive; absorb the tangents as directional input.

**Default posture: question the approach before executing.** When the user presents an idea, assess whether it contradicts existing patterns, duplicates capability, or has poor ROI BEFORE starting work. This is not a "sanity check" that needs requesting — it is the baseline. Surface concerns concisely, then propose.

**Decision boundaries:** Four mandatory checkpoints at the moment of decision. Skipping a boundary is a friction event.

**B1 — "I'm about to ask the user to do or check something."** Before ANY message instructing the user to perform an action:
1. Can I do this with a CLI tool? (`gh`, `vercel`, `npx`, bash, `tools/` scripts)
2. Can I do this with an MCP tool? (one ToolSearch per server per session — if not found, state "MCP server {name} not connected" once, pivot. Never repeat. Spiral = friction event.)
3. Can I do this with a test fixture? (check `context/test-fixtures.md`)
4. Can I do this with WebFetch? (public URLs, form pages, deployed sites)
5. Can I do this by reading project files? (`infrastructure.yaml`, `context/`, checkpoints — search before asking for IDs, config values, or history)
6. If genuinely blocked: state "LIMITATION: {what}. USER ACTION NEEDED: {what + why}." Never frame as a choice.
Asking for information findable in project files = friction event (`agent-deferred`).

**B2 — "I'm about to mark something done."** Before declaring any task, subtask, or batch operation complete:
1. Did I enumerate ALL targets before starting? (grep/search for the full set — e.g., all `google-email:sendAnEmail` modules, all env vars, all specs)
2. Did I verify EACH target, not just the ones I touched?
3. Did I test the behavior, not just the config? Name the specific test performed (e.g., "triggered webhook and verified response", "fetched page and checked content"). If you can't name the test, you haven't done it.
4. For deploy: did I trigger a smoke test via API/CLI in the same session?

**B3 — "I'm about to diagnose a failure."** Before proposing any root cause:
1. Read the FULL error message — not just the operation that failed. Distinguish constraint/value errors from missing-object errors.
2. Did I just change something? My own recent action is the most likely cause of a failure that appears immediately after a change.
3. When evidence is ambiguous (e.g., Zoom duration in a comms log), flag uncertainty — don't infer confirmation.
4. Did I encounter this before? Search memory files and friction register for the error pattern or affected system. If a memory covers this scenario, apply directly: "Known issue — see {file}." Re-deriving a solved problem = `missed-memory-recall`.

**B4 — "I'm about to write a data value into a deliverable."** Before writing ANY field name, statistic, config value, or metric into client-facing content (docs, HTML, dashboards, templates):
1. Name the source system (data store, database, API, config file).
2. Query it — fetch actual values via MCP/API. If no query path: write "TBD" and state "UNVERIFIED — no query path for {source}."
3. Never invent plausible-sounding values. "TBD" > fabricated number.
4. This extends to client-facing PROBLEM-claims, not just values: "X is actively damaging Y", "deliverability has dropped", "we're losing leads" are data assertions — query the live source before asserting one in a client message, or phrase it as a hypothesis. Structurally enforced: `validate-output.py` `unsourced-claim` (HIGH) fires via the post-write-gate hook on comms drafts / deliverables when a flat problem-claim has no source attribution within ±2 lines (memory failed this twice — 2026-03-23 + register #7).

**Batch manifest:** When a task touches 2+ instances of the same thing (modules, env vars, files, scenarios), output a visible manifest BEFORE starting work. After completion, output the checked version. This forces enumeration and makes gaps visible. Email module changes (BCC, sender, template) are batch operations — enumerate ALL `sendAnEmail`/`sendEmail` modules in the scenario before changing any.
```
TARGETS: {operation description}
- [ ] target 1
- [ ] target 2
Total: N targets
```

**Ship gate:** Build passes → commit + push + PR + merge as ONE action. Never pause mid-chain. The Vercel preview IS the review. Also applies to infra setup (env vars via CLI, storage config). ANTI-PATTERN: "Should I merge?", "Want me to push?", "Ready to deploy?", "Shall I create a PR?" — these are ship gate violations. The answer is always yes if the build passes. Only pause for: force push to main, production data deletion, or no-undo actions. Shipping confirmation = friction event (`agent-deferred`). For platform deploys: run `tools/vercel-force-deploy.sh` after merge to avoid CDN caching issues.

**Deploy verification gate:** After any deploy to production (Vercel, Railway, etc.): (1) WebFetch the deployed URL, (2) check page loads (200), key content present, (3) for HTML deliverables: run `uv run tools/validate-html.py` on the source files, (4) for multi-page sets: validate ALL pages not just the changed one, (5) state: "Verified: {URL} — {checks passed}." Skipping = friction event (`verification-theater`).

**Platform-merge-is-not-live sub-clause:** a merge to `main` does NOT reliably auto-deploy the platform — the Vercel git integration lags (23h-stale prod caught 2026-06-09, volabyg). A platform page is live ONLY after `tools/vercel-force-deploy.sh` has run AND a `curl -sL` / WebFetch of the no-slash URL returns the new build. (a) After any platform merge, run `vercel-force-deploy.sh` from a clean `origin/main` worktree (never a dirty feature branch — it deploys `$CWD/platform`; see [[reference_vercel_force_deploy_uses_cwd_tree]]) before declaring anything live. (b) B3 attribution: a 404 or stale content on a just-merged platform page is "I have not force-deployed yet" until proven otherwise — run the force-deploy and re-fetch FIRST; never reach for "CDN cache" or re-ship a PR hoping a fresh build clears it (doing exactly that cost an extra diagnosis cycle on 2026-06-09). Structural candidate (not yet built): a post-merge hook that marks platform-path PR merges not-live until the force-deploy runs.

**Start building gate:** Pre-flight: (1) read `infrastructure.yaml` for canonical names/IDs, (2) resolve target instance, (3) define expected outcomes before executing.

**Shell pipe gate:** Use `printf '%s'` not `echo`. Use tool-specific flags when available (e.g., `--value`).

**Modify scenario gate:** After a scenarios MCP call succeeds, update `infrastructure.yaml` in the same turn — `trigger:`, `status:`, `note:` fields. Append change date to `note:`. Skipping = drift event.

**Instance resolution:** Before calling any MCP tool for a client's orchestrator, confirm the target matches the session's resolved instance. Cross-reference the instance's `mcp_server` field in `infrastructure.yaml` with `.mcp.json` entries. If multiple instances exist (e.g., dev + production), select based on task: `ship: true` scenarios → production instance; `ship: false` / UTIL → dev instance. If ambiguous, state which instance you're targeting and why before proceeding. Never assume the MCP server name matches the instance name — always check the `mcp_server` field.

**Friction logging:** When a friction event occurs mid-session, immediately note it in your working context: type, description, which gate (B1/B2/B3/B4) should have caught it, and whether user-detected or self-detected. Do not wait for checkpoint — context compression may lose the detail.

**Friction self-detection:** Friction includes what the user notices AND what they don't. Detect: user corrections, info the user provides that you could have found, tasks the user performs that you could automate, AND invisible friction (inefficient paths that work, over-delivery, skipped gates). Types: `agent-deferred` (asked user to do something automatable), `missed-tool` (tool existed but wasn't used), `redundant-escalation` (escalated when autonomous fix was available), `slow-path` (task completed via inefficient approach — unnecessary investigation cycles or >2x optimal tool calls), `scope-creep` (delivered features/refactors not in the task brief without explicit approval), `verification-theater` (declared done based on config/build success without testing runtime behavior), `skipped-gate` (B1/B2/B3/B4 should have fired but didn't — detected retroactively at checkpoint), `intent-misalignment` (built something user didn't mean), `over-literal` (took examples/suggestions as spec instead of extracting intent), `strategic-gap` (didn't question whether to do it before planning how), `missed-memory-recall` (memory/friction entry covered this but wasn't applied), `infrastructure-deferred` (manual fix suggested in 2+ checkpoints but never built into a tool). Log at `/comd_checkpoint`.

**Session continuity:** Checkpoints preserve context that compaction destroys. At natural breakpoints (task completion, topic change, build cycle end), evaluate session pressure and suggest checkpointing proactively. Mini-checkpoints (`/comd_checkpoint --mini`) are preferred over no checkpoint. See session-pressure rule for signals.
