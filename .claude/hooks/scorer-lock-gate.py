#!/usr/bin/env python3
"""PreToolUse(Write|Edit) hook: scorers are locked against agent edits.

Backs tools/scorers/README.md (the /comd_optimize hill-climb loop, Karpathy
auto-research pattern). The loop's integrity rests on ONE property: the agent
that mutates the asset cannot also move the goalposts. This gate makes that
structural:

  DENY     Write/Edit on an EXISTING tools/scorers/*.py (goalpost-moving)
  DENY     Write/Edit on tools/scorers/PINS.json (the committed name->hash
           pin registry; re-pin only via `uv run tools/pin_scorer.py pin`
           under the same SCORER_LOCK_ALLOW seam)
  ADVISE   creating a NEW tools/scorers/*.py (allowed - that is how scorers
           get authored - but reminds: PR review is the honesty sign-off,
           register in tools/INDEX.md)
  ADVISE   any scorer write while SCORER_LOCK_ALLOW=1 (user-approved
           maintenance seam; the override is surfaced, never silent)
  PASS     everything else (README.md under scorers/, all other paths,
           out-of-repo writes)

Only Write/Edit tool calls are visible here; a shell-redirect rewrite of a
scorer bypasses the gate and is a friction event (`scorer-lock-bypass`), same
class as a skipped B-gate. Mirrors file-placement-gate.py conventions: path
normalization hardening, test seams, defensive exit 0 (never bricks a write).
"""
from __future__ import annotations

import json
import os
import re
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))  # .../agentic-ops1

# --- test seams: never set in production -----------------------------------
# Used by tools/tests/test_scorer_lock_gate.py.
_ENV_REPO = os.environ.get("SCORER_LOCK_GATE_REPO")
if _ENV_REPO:
    REPO = _ENV_REPO

REPO_POSIX = REPO.replace("\\", "/").rstrip("/")
REPO_POSIX_LOWER = REPO_POSIX.lower()

SCORER_RE = re.compile(r"^tools/scorers/(.+\.py|PINS\.json)$", re.IGNORECASE)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def advise(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }))


def rel_to_repo(abspath: str) -> str | None:
    """Repo-relative posix path, or None when the target is outside the repo."""
    p = abspath.replace("\\", "/")
    # Collapse ../ and ./ BEFORE the repo-prefix check: a traversal path
    # (<repo>/x/../../tools/scorers/page-weight.py) would otherwise miss
    # SCORER_RE while the OS resolves it to the real locked scorer.
    p = os.path.normpath(p).replace("\\", "/")
    if not p.lower().startswith(REPO_POSIX_LOWER + "/"):
        return None
    rel = p[len(REPO_POSIX) + 1:]
    # Redundant separators / "." are gone via normpath; any residual ".."
    # after normalization traverses out of a resolvable path - untrusted.
    segs = [seg for seg in rel.split("/") if seg not in ("", ".")]
    if ".." in segs:
        return None
    return "/".join(segs)


def rel_to_git_root(abspath: str) -> str | None:
    """Fallback for targets OUTSIDE the gate's own repo: if the target sits
    inside ANY git-rooted tree (a `.git` dir, or the `.git` pointer FILE a
    `git worktree` carries), return the path relative to that root.

    Closes the 2026-07-17 tamper-test bypass (register `skipped-gate`): an
    Edit to tools/scorers/*.py in a sibling worktree resolved outside
    REPO_POSIX and passed, although the worktree commits into the same
    repository. A path with no git root around it (e.g. C:/elsewhere/...)
    still returns None and passes."""
    p = os.path.normpath(abspath.replace("\\", "/")).replace("\\", "/")
    d = os.path.dirname(p)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            root = d.replace("\\", "/").rstrip("/")
            return p[len(root) + 1:]
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") not in ("Write", "Edit"):
        return 0

    raw_path = (event.get("tool_input") or {}).get("file_path", "") or ""
    if not raw_path:
        return 0

    abspath = raw_path.replace("\\", "/")
    # Resolve relative targets against the repo root.
    if not (len(abspath) >= 2 and abspath[1] == ":") and not abspath.startswith("/"):
        abspath = f"{REPO_POSIX}/{abspath.lstrip('/')}"

    rel = rel_to_repo(abspath)
    if rel is None:
        # Outside the gate's own repo: a git worktree / second clone of this
        # repo is still the locked surface (its commits land in the same
        # repository). Key on the target's OWN git root.
        rel = rel_to_git_root(abspath)
    if not rel or not SCORER_RE.match(rel):
        return 0

    if os.environ.get("SCORER_LOCK_ALLOW"):
        advise(
            f"[scorer-lock] OVERRIDE ACTIVE (SCORER_LOCK_ALLOW=1): agent write "
            f"to {rel} permitted. This seam is for user-approved scorer "
            "maintenance only; confirm the user asked for this edit."
        )
        return 0

    # Existing-vs-new check on the RESOLVED target itself (not a REPO join):
    # for a worktree/second-clone target the file lives under that root.
    target = os.path.normpath(abspath.replace("\\", "/"))
    if rel.lower().endswith("pins.json"):
        deny(
            f"[scorer-lock] {rel} is the scorer pin registry and is never "
            "edited directly. Re-pin via `uv run tools/pin_scorer.py pin "
            "<name>` under SCORER_LOCK_ALLOW=1 after a user-approved scorer "
            "change; the PINS diff ships in the PR for review."
        )
        return 0
    if os.path.isfile(target):
        deny(
            f"[scorer-lock] {rel} is a locked scorer (tools/scorers/README.md). "
            "The optimize loop's metric may not be edited by the agent that "
            "optimizes against it - that is goalpost-moving. If the user "
            "explicitly asked for a scorer change, re-run the edit with "
            "SCORER_LOCK_ALLOW=1 set, or hand the change to the user."
        )
        return 0

    advise(
        f"[scorer-lock] New scorer {rel}: creation is allowed. Before first "
        "use: declare `# direction: minimize|maximize`, end stdout with "
        "`SCORE: <number>`, register it in tools/INDEX.md, and ship it via PR "
        "- the PR review is the honesty sign-off. It locks the moment it "
        "exists."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # defensive: never brick a write
