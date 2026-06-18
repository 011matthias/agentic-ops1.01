#!/usr/bin/env python3
"""PreToolUse(Write) hook: deterministic file-placement floor.

Backs rule_file_placement.md (W2). Classifies the write target by path and
name pattern and HARD-DENIES the three unambiguous placement violations,
warns on an ambiguous one, and passes everything else through silently:

  DENY     new file at the repo root not in the config/doc allowlist
  DENY     a never-commit pattern (secrets/tokens) into a TRACKED path
  DENY     a scratch pattern into a non-gitignored path (incl. root)
  ADVISORY write into an unknown top-level directory (no established home)
  PASS     edits to existing files; writes already in a known home

WHY DENY AND NOT JUST WARN: the .gitignore already carries reactive
root-clutter patches (/test.pdf, /after-*.jpeg, ...) added after stray
artifacts hit the root. Advisory depends on agent recall, which is the
thing that kept failing; the deny floor removes the recall dependency for
the clear-cut cases. The rule + skill carry the nuance the path-pattern
gate can't read.

Mechanism: emits a PreToolUse JSON `permissionDecision: "deny"` with the
redirect reason (deny is the most-restrictive decision and wins over the
auto-approve-protected `allow` that fires earlier in the same chain).
Advisory uses `additionalContext`. Out-of-repo writes (the memory dir,
home-dir Bewerbungen, openclaw-sandbox) are never touched.

Defensive: any error -> exit 0 silently. NEVER bricks a write.
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
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))  # .../agentic-ops1
HOOK_LOG = os.path.join(HOOK_DIR, "hook-log.txt")

# --- test seam: force a target path / repo without the live harness -------
# Never set in production; used by tools/tests/test_file_placement_gate.py.
_ENV_REPO = os.environ.get("FILE_PLACEMENT_GATE_REPO")
if _ENV_REPO:
    REPO = _ENV_REPO

REPO_POSIX = REPO.replace("\\", "/").rstrip("/")
REPO_POSIX_LOWER = REPO_POSIX.lower()

# Files that legitimately live at the repo root. A NEW root file not here
# is denied; edits to these pass through.
ROOT_ALLOWLIST = {
    "claude.md", "readme.md", "delivery-guide.md", ".gitignore", ".mcp.json",
    "pytest.ini", "ruff.toml", ".pre-commit-config.yaml", "skills-lock.json",
    ".python-version", ".editorconfig", ".gitattributes", "license",
    "license.md", "skills.lock.json",
}

# Top-level dirs with an established home (W2 §2). A write under any other
# top-level dir is ambiguous -> advisory.
KNOWN_TOP_DIRS = {
    "workspace", "platform", "docs", "tools", "scripts", "api-docs",
    ".claude", ".scratch", ".tmp", ".github", ".agents", ".vscode",
    ".serena", ".playwright-mcp", "internal", "node_modules",
}

# Gitignored prefixes — static fallback when `git check-ignore` is
# unavailable. Kept loose; git is the authority when present.
STATIC_IGNORED_PREFIXES = (
    ".scratch/", ".tmp/", "api-docs/", ".playwright-mcp/", "scripts/.",
    "internal/", ".serena/", ".pytest_cache/", ".ruff_cache/",
)

SCRATCH_RE = re.compile(
    r"(^scratch[-_.])|(^tmp[-_.])|(^temp[-_.])|(^debug[-_.])|(^snapshot[-_.])"
    r"|(^state-\d)|([-_]dump\.)|([-_]debug\.)|(\.tmp$)|(\.bak$)",
    re.IGNORECASE,
)
NEVERCOMMIT_RE = re.compile(
    r"(\.env$)|(\.env\.)|(^client_secrets\.json$)|(^token\.json$)|(\.pem$)"
    r"|(\.key$)|(secret.*\.json$)|(credential.*\.json$)",
    re.IGNORECASE,
)


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} file-placement-gate {msg}\n")
    except Exception:
        pass


def normalize(path: str) -> str:
    """Git-Bash /c/Users -> C:/Users; backslashes -> forward slashes."""
    if not path:
        return path
    if len(path) >= 3 and path[0] == "/" and path[2] == "/" and path[1].isalpha():
        path = f"{path[1].upper()}:{path[2:]}"
    return path.replace("\\", "/")


def rel_to_repo(abspath_posix: str) -> str | None:
    """Return the repo-relative POSIX path, or None if outside the repo."""
    low = abspath_posix.lower()
    if low == REPO_POSIX_LOWER:
        return ""
    prefix = REPO_POSIX_LOWER + "/"
    if not low.startswith(prefix):
        return None
    return abspath_posix[len(prefix):]


def is_gitignored(abspath_posix: str, rel: str) -> bool:
    """True if the path is gitignored. Authoritative via git; static fallback."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", abspath_posix],
            cwd=REPO, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if proc.returncode in (0, 1):
            return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    rl = rel.lower()
    return any(rl.startswith(p) for p in STATIC_IGNORED_PREFIXES)


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


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    # Only gate file CREATION. Edits operate on files already in a home.
    if event.get("tool_name") != "Write":
        return 0

    raw_path = (event.get("tool_input") or {}).get("file_path", "") or ""
    if not raw_path:
        return 0
    abspath = normalize(raw_path)

    # Resolve relative targets against the repo root.
    if not (len(abspath) >= 2 and abspath[1] == ":") and not abspath.startswith("/"):
        abspath = f"{REPO_POSIX}/{abspath.lstrip('/')}"

    rel = rel_to_repo(abspath)
    if rel is None:
        return 0  # outside this repo (memory dir, home dir, sandbox) — not our scope
    if rel == "":
        return 0  # writing the repo dir itself — unreachable, defensive

    fname = rel.rsplit("/", 1)[-1].lower()
    parts = rel.split("/")
    top = parts[0].lower()
    is_root_level = len(parts) == 1

    # Already in the scratch home -> always fine.
    if top == ".scratch":
        return 0

    ignored = None  # lazy

    def _ignored() -> bool:
        nonlocal ignored
        if ignored is None:
            ignored = is_gitignored(abspath, rel)
        return ignored

    # 1. Never-commit pattern into a tracked path -> DENY.
    if NEVERCOMMIT_RE.search(fname):
        if _ignored():
            return 0  # correctly hidden in a gitignored area
        log_fire(f"DENY never-commit-tracked {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' looks like never-commit content "
            f"(secret/token/key) and '{rel}' is a TRACKED path. Write it to a "
            f"gitignored location (workspace/clients/{{client}}/context/ for "
            f"client secrets, or .scratch/ for throwaway), or do not write it. "
            f"Never commit credentials. See rule_file_placement.md §6."
        )
        return 0

    # 2. Scratch pattern into a non-gitignored path -> DENY.
    if SCRATCH_RE.search(fname):
        if _ignored():
            return 0
        log_fire(f"DENY scratch-tracked {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' is an ephemeral/scratch name and "
            f"'{rel}' is not gitignored. Ephemeral artifacts go to .scratch/ "
            f"(gitignored), never a tracked path. First apply W1: if this is a "
            f"finding you can print or distill into one line, write nothing. "
            f"Otherwise write to .scratch/{fname}. See rule_file_placement.md §2."
        )
        return 0

    # 3. New file at repo root not in the allowlist.
    if is_root_level:
        if fname in ROOT_ALLOWLIST:
            return 0
        if _ignored():
            # already-ignored root artifact (e.g. /after-*.jpeg shot tooling) —
            # tolerate but nudge toward the scratch home.
            advise(
                f"[PLACEMENT] '{fname}' is being written to the repo root. It is "
                f"gitignored, so it won't be committed, but new ephemeral writes "
                f"should go to .scratch/ (W2 §5)."
            )
            return 0
        log_fire(f"DENY root-write {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' would be a NEW file at the repo "
            f"root. Root is reserved for config + top-level docs (CLAUDE.md, "
            f"README.md, .gitignore, pytest.ini, ...). Route it by kind: a tool "
            f"-> tools/, a doc -> docs/, a deliverable -> the client's "
            f"deliverables/ or platform/public/, an ephemeral artifact -> "
            f".scratch/. See the home map in rule_file_placement.md §2."
        )
        return 0

    # 4. Unknown top-level directory -> ADVISORY (no established home).
    if top not in KNOWN_TOP_DIRS and not _ignored():
        log_fire(f"ADVISE unknown-top {rel}")
        advise(
            f"[PLACEMENT] '{rel}' is under a top-level directory ('{top}/') with "
            f"no established home in rule_file_placement.md §2. Confirm this is "
            f"the right place, route to an existing home, or use .scratch/ if "
            f"it's ephemeral. Don't create a new tracked top-level dir for an "
            f"orphan file."
        )
        return 0

    return 0  # in a known home — pass through silently


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never hard-fail a write
        try:
            log_fire(f"ERROR {type(exc).__name__}")
        except Exception:
            pass
        sys.exit(0)
