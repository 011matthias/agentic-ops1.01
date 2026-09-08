# Session Start

When beginning a new conversation where a client name is mentioned or evident from context:

1. Suggest running `/resume {client}` if not already done
2. Check for unresolved comms items (staleness > 3 days)
3. Reference the last checkpoint's `next_steps` if available
4. Begin tracking session pressure signals (see session-pressure rule)
5. Activate decision boundaries from `rule_behaviors.md` (B1: before asking user, B2: before marking done, B3: before diagnosing, B4: before writing data into deliverables). Boundaries are mandatory, not suggestions.
6. Load memory via the index, then targeted files (mandatory -- see comd_resume Step 5.5). Skipping = friction event (`missed-feedback-memory`).
   - `MEMORY.md` (17 KB, ~4k tokens) is the index and arrives in context automatically. READ IT as the roster: one line per memory, each naming what the file holds.
   - Then read the FULL file for every memory whose index line touches this session's scope (the client, the surface, the tools in play), plus any the work surfaces later. A one-line hook is a pointer, never the fact: never act on the index line alone, and never cite one as if it were the memory.
   - Do NOT bulk-load the directory. The store is 128 files / 659 KB (~165k tokens, measured 2026-09-08) and grows weekly; the retired "load everything, ~1,800 tokens, 0.2% of budget" line was ~90x under reality and made the step unfollowable as written, so it was silently skipped instead (register row 2026-09-08, infrastructure-deferred). Index-plus-targeted is what working sessions already do.
   - When scope is broad or unknown, grep the store (`--no-ignore`) for the system/tool at hand rather than loading it whole.
   - Platform work: also read `workspace/projects/platform/context/brand.md` for canonical names

7. **Output session header** as the FIRST block of every session (after `/resume` or when scope is evident). Mandatory — skipping = friction event (`missed-session-header`):
   ```
   ---
   **[{SCOPE}] {task-desc}**
   Scope: {project} · {orchestrator}
   Skills: {skills loaded by name}
   Open: {N spec(s) in build/test} | Comms: {N days stale or "current"}
   Memories: {list of applied feedback memory filenames}
   ---
   ```
   Then call `python tools/rename-chat.py "{scope}--{task-desc}"` to auto-rename the chat. For system-dev sessions: scope = `sys`. For cross-client work: scope = `sys`. See Scope Codes table in `comd_resume.md`.

8. **Confirm loaded memories by name** in the session header `Memories:` line. Listing them by file name (e.g., `feedback_no_em_dashes.md`) makes loading gaps immediately visible.

This ensures continuity between sessions and prevents context loss.
