#!/usr/bin/env python3
"""PreToolUse(Write|Edit) hook: scorers are locked against agent edits.

Backs tools/scorers/README.md (the /comd_optimize hill-climb loop, Karpathy
auto-research pattern). The loop's integrity rests on ONE property: the agent
that mutates the asset cannot also move the goalposts. This gate makes that
structural:

  DENY     Write/Edit on an EXISTING tools/scorers/*.py (goalpost-moving)
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

SCORER_RE = re.compile(r"^tools/scorers/.+\.py$", re.IGNORECASE)


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
    if not p.lower().startswith(REPO_POSIX_LOWER + "/"):
        return None
    rel = p[len(REPO_POSIX) + 1:]
    # Collapse redundant separators / "." segments so `tools//scorers/x.py`
    # and `tools/./scorers/x.py` cannot dodge the match (mirrors the
    # file-placement-gate double-slash hardening).
    return "/".join(seg for seg in rel.split("/") if seg not in ("", "."))


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
    if not rel or not SCORER_RE.match(rel):
        return 0

    if os.environ.get("SCORER_LOCK_ALLOW"):
        advise(
            f"[scorer-lock] OVERRIDE ACTIVE (SCORER_LOCK_ALLOW=1): agent write "
            f"to {rel} permitted. This seam is for user-approved scorer "
            "maintenance only; confirm the user asked for this edit."
        )
        return 0

    target = os.path.join(REPO, *rel.split("/"))
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
