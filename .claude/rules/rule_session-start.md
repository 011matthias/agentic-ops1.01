# Session Start

When beginning a new conversation where a client name is mentioned or evident from context:

1. Suggest running `/resume {client}` if not already done
2. Check for unresolved comms items (staleness > 3 days)
3. Reference the last checkpoint's `next_steps` if available
4. Begin tracking session pressure signals (see session-pressure rule)
5. Activate decision boundaries from `rule_behaviors.md` (B1: before asking user, B2: before marking done, B3: before diagnosing, B4: before writing data into deliverables). Boundaries are mandatory, not suggestions.
6. Load ALL memory files (mandatory -- see comd_resume Step 5.5). With 1M context, bulk-load every .md file in the memory directory. Confirm loaded memories in session summary. Skipping = friction event (`missed-feedback-memory`).
   - This replaces selective trigger loading -- load everything (~1,800 tokens, 0.2% of budget)
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
