#!/usr/bin/env python3
"""PreToolUse(Write|Edit) hook: branch-isolation advisory (G1).

Backs rule_branch_isolation_and_shared_ledger.md §2 ("one project per
branch; branch BEFORE the first edit"). When a Write/Edit targets a
TRACKED file under workspace/clients/{X}/** and the current branch is not
a branch for that client, emit a loud advisory naming the correct move
(cut/switch to client/{X}/... first). The 2026-06-12 stash tangle and the
2026-07-22 dirty-main pile (a 611-line client tool + 18 client files
accumulated directly on main) are the named recurrences this gate kills.

ADVISORY, not deny: legitimate cross-cutting flows exist (system-wide
refactors touching client trees, sanctioned per-client branch families
like brisken's leadgen/task-N session branches), so the gate informs the
decision instead of blocking it. Gitignored targets (the client context/
home, comms logs) are skipped — they never commit, so branch identity
does not matter for them.

Branch families that PASS for client X:
  client/{X}/...   (canonical, CLAUDE.md git workflow)
  {X}/...          (legacy style, e.g. brisken/recon-*)
  plus per-client extra prefixes in EXTRA_CLIENT_BRANCH_PREFIXES
  (brisken: leadgen/ — the Rome lead-gen session branches, see memory
  project_brisken_rome_leadgen_task_branches).

Defensive: any error, git unavailable, detached HEAD, or out-of-repo
target -> exit 0 silently. NEVER blocks a write.
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys

try:
    import json
except Exception:  # pragma: no cover
    sys.exit(0)

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK_LOG = os.path.join(HOOK_DIR, "hook-log.txt")

# --- test seams: never set in production -----------------------------------
# Force the branch (skips the git call), mirroring NO_AUTO_COMMIT_GATE_BRANCH.
_ENV_BRANCH = os.environ.get("BRANCH_ISOLATION_GATE_BRANCH")
# Force the gitignore verdict: "1" = treat target as gitignored.
_ENV_IGNORED = os.environ.get("BRANCH_ISOLATION_GATE_IGNORED")

CLIENT_PATH_RE = re.compile(r"(?:^|/)workspace/clients/([^/]+)/", re.IGNORECASE)

# Sanctioned per-client branch families beyond client/{X}/ and {X}/.
EXTRA_CLIENT_BRANCH_PREFIXES = {
    "brisken": ("leadgen/",),
}


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.datetime.now().isoformat()} branch-isolation-gate {msg}\n"
            )
    except Exception:
        pass


def normalize(path: str) -> str:
    """Git-Bash /c/Users -> C:/Users; backslashes -> forward slashes."""
    if not path:
        return path
    if len(path) >= 3 and path[0] == "/" and path[2] == "/" and path[1].isalpha():
        path = f"{path[1].upper()}:{path[2:]}"
    return path.replace("\\", "/")


def _git(args: list[str], cwd: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, timeout=5,
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def current_branch(cwd: str) -> str | None:
    if _ENV_BRANCH:
        return _ENV_BRANCH
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def is_gitignored(abspath: str, cwd: str) -> bool:
    if _ENV_IGNORED is not None:
        return _ENV_IGNORED == "1"
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", abspath],
            cwd=cwd, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def branch_matches_client(branch: str, client: str) -> bool:
    b = branch.lower()
    c = client.lower()
    if b.startswith(f"client/{c}/") or b == f"client/{c}":
        return True
    if b.startswith(f"{c}/"):
        return True
    return any(
        b.startswith(p) for p in EXTRA_CLIENT_BRANCH_PREFIXES.get(c, ())
    )


def advise(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }))


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
    abspath = normalize(raw_path)

    m = CLIENT_PATH_RE.search(abspath)
    if not m:
        return 0
    client = m.group(1)

    # Directory containing the target — lets `git -C` resolve the RIGHT
    # repo/worktree (a write into an isolation worktree is judged against
    # that worktree's own branch, not the main tree's).
    target_dir = abspath.rsplit("/", 1)[0] if "/" in abspath else "."
    if not os.path.isdir(target_dir):
        # New file in a new dir — walk up to the nearest existing parent.
        probe = target_dir
        while probe and not os.path.isdir(probe):
            if "/" not in probe:
                probe = "."
                break
            probe = probe.rsplit("/", 1)[0]
        target_dir = probe or "."

    # Gitignored targets (client context/, comms logs) never commit;
    # branch identity is irrelevant to them.
    if is_gitignored(abspath, target_dir):
        return 0

    branch = current_branch(target_dir)
    if not branch or branch == "HEAD":  # git down or detached HEAD
        return 0

    if branch_matches_client(branch, client):
        return 0

    log_fire(f"ADVISE client={client} branch={branch} {abspath}")
    if branch in ("main", "master"):
        advise(
            f"[BRANCH-ISOLATION G1] You are editing a tracked '{client}' client "
            f"file while on '{branch}'. Client work commits only to a "
            f"client/{client}/... branch, cut BEFORE the first edit "
            f"(rule_branch_isolation_and_shared_ledger §2; the 2026-07-22 "
            f"dirty-main pile is the recurrence this gate exists for). Cut the "
            f"branch now — in a shared tree, prefer an isolated worktree: "
            f"git worktree add ../ao1-{client} -b client/{client}/<desc> origin/main"
        )
    else:
        advise(
            f"[BRANCH-ISOLATION G1] Target is a tracked '{client}' client file "
            f"but the current branch is '{branch}' (different project). Never "
            f"edit project-X files on a project-Y branch "
            f"(rule_branch_isolation_and_shared_ledger §2). Switch/cut "
            f"client/{client}/<desc> first, or if this is a deliberate "
            f"cross-cutting change, say so explicitly in the commit that ships it."
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never block a write
        try:
            log_fire(f"ERROR {type(exc).__name__}")
        except Exception:
            pass
        sys.exit(0)
