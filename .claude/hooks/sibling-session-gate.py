#!/usr/bin/env python3
"""SessionStart: warn when a LIVE sibling session shares this working tree.

Multiple Claude sessions on ONE clone share HEAD, the index, and the stash;
concurrent commits + edits collide (session-log frontmatter bumped mid-edit,
drafts landing in the wrong place, cherry-pick recoveries). The failure was
named SIX times across 2026-07-09..07-11 ("sibling-guard still unbuilt, 6th
occurrence"). The FIX (feedback_worktree_for_concurrent_sessions) is a git
worktree per session -- each worktree has its own index, so no collision. This
gate is the DETECTOR: it registers this session's heartbeat and, when another
live session is already working in the SAME working tree, prints a one-time
advisory recommending worktree isolation.

Keyed on the working-tree root (via session_registry), so sessions ALREADY
isolated in separate worktrees never trip it -- that is the whole point: they
are safe, and the advisory would be noise.

Output: plain text to stdout ONLY when a sibling is found (silent otherwise),
matching the other SessionStart hooks (friction-watch, project_status).

Defensive: any error -> exit 0, no output. Must never break session start.
"""
import json
import os
import sys

# Import the shared registry from tools/ (repo-root-relative), same pattern as
# session-pressure-meter.py importing session_state.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)

try:
    import session_registry  # noqa: E402
except Exception:
    sys.exit(0)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    session_id = payload.get("session_id", "") or ""
    cwd = payload.get("cwd") or os.getcwd()

    try:
        root = session_registry.find_worktree_root(cwd)
        if not root:
            return 0
        # Read siblings BEFORE writing our own heartbeat (we filter self by id
        # regardless, but this keeps the check order obvious).
        sibs = session_registry.live_siblings(session_id, root=root)
        session_registry.heartbeat(session_id, cwd=cwd, root=root)
        if not sibs:
            return 0

        lines = []
        for s in sibs[:5]:
            mins = max(0, int(s.get("age_seconds", 0)) // 60)
            branch = s.get("branch") or "?"
            sid = (s.get("session_id") or "")[:8]
            pid = s.get("pid", "?")
            lines.append(f"  - session {sid} on branch '{branch}', active {mins}m ago (pid {pid})")

        print(
            "[SIBLING-SESSION] Another live Claude session is sharing this "
            f"working tree:\n{root}\n" + "\n".join(lines) + "\n"
            "This clone shares HEAD, the index, and the stash, so concurrent "
            "commits and edits collide (session-log frontmatter bumped mid-edit, "
            "wrong-target writes, cherry-pick recoveries). Isolate this session "
            "in its own git worktree (feedback_worktree_for_concurrent_sessions):\n"
            "  git worktree add -b <branch> ../agentic-ops1-<name> origin/main\n"
            "If you stay in this shared tree: commit with explicit pathspecs only "
            "(never `git add -A`), and expect index contention with the sibling."
        )
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
