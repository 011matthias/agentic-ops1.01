#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell): count personal data in a push before it leaves.

WHY THIS EXISTS
---------------
The repo is public (owner decision 2026-09-16). The 2026-10-28 layout audit
found 579 consumer addresses in a WW export, named Rome rosters and
checkpoint bodies quoting private addresses, all world-readable, and the only
content scanner (gitleaks in CI) knows credentials, not people, and runs
after the push is public. This gate runs tools/pii_scan.py over the lines the
push ADDS (layout plan W1-14).

WHAT IT DOES
------------
1. Fires only on `git push` (normalized view, like ruff-push-gate).
2. Resolves the push range as upstream...HEAD, falling back to origin/main.
3. Runs pii_scan.scan_range: COUNTS per file, never values.
4. Clean -> allow silently. Hits -> permissionDecision="ask" listing each path
   with its detector counts and the remedies.

"ask", never "deny" (client-ops guard, PLAN.md 2026-10-28): an urgent client
fix must still be able to leave the machine on the owner's approval.

DEFENSIVE CONTRACT
------------------
Any error, unresolvable range, import failure or timeout -> exit 0, allow. A
broken scanner must never brick a push; CI reports the same scan afterwards.

OVERRIDE (never set in production)
----------------------------------
  PII_PUSH_GATE_ALLOW=1   deliberate bypass -> allow with a stderr note.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
GIT_PUSH = re.compile(r"\bgit\s+push\b", re.IGNORECASE)
TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
DIFF_TIMEOUT = 6  # seconds; under the 10 s wired hook timeout


def log(action: str) -> None:
    try:
        import datetime
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} pii-push-gate {action}\n")
    except Exception:
        pass


def _git(args, cwd=None):
    try:
        return subprocess.run(["git", *args], capture_output=True, timeout=5, cwd=cwd,
                              encoding="utf-8", errors="replace")
    except Exception:
        return None


def push_range(cwd: str | None) -> str | None:
    """upstream...HEAD, or origin/main...HEAD for a first push; None if neither."""
    up = _git(["rev-parse", "--abbrev-ref", "@{u}"], cwd=cwd)
    if up and up.returncode == 0 and up.stdout.strip() and "@{u}" not in up.stdout:
        return f"{up.stdout.strip()}...HEAD"
    for cand in ("origin/main", "main", "origin/master", "master"):
        chk = _git(["rev-parse", "--verify", "--quiet", cand], cwd=cwd)
        if chk and chk.returncode == 0:
            return f"{cand}...HEAD"
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd or not GIT_PUSH.search(normalize_command(cmd)):
        sys.exit(0)
    if os.environ.get("PII_PUSH_GATE_ALLOW"):
        log("allow: PII_PUSH_GATE_ALLOW override")
        sys.stderr.write("[pii-push-gate] bypassed via PII_PUSH_GATE_ALLOW.\n")
        sys.exit(0)
    try:
        sys.path.insert(0, str(TOOLS))
        import pii_scan
        top = _git(["rev-parse", "--show-toplevel"])
        if not top or top.returncode != 0 or not top.stdout.strip():
            sys.exit(0)
        root = Path(top.stdout.strip())
        rng = push_range(str(root))
        hits = pii_scan.scan_range(root, rng, timeout=DIFF_TIMEOUT) if rng else None
    except SystemExit:
        raise
    except Exception as exc:
        log(f"allow: scan error {type(exc).__name__} -> fail-open")
        sys.exit(0)
    if hits is None:
        log("allow: range undeterminable -> fail-open")
        sys.exit(0)
    if not hits:
        log("allow: clean")
        sys.exit(0)

    listing = "\n".join("  " + line for line in pii_scan.format_hits(hits)[:25])
    log(f"ASK: {len(hits)} file(s) with personal data")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "PERSONAL DATA IN THIS PUSH (counts only, values not shown). "
                "The repo is public, so these lines become world-readable:\n\n"
                f"{listing}\n\n"
                "Move real data to the client's gitignored context/ and push a "
                "pointer instead. If the data is synthetic or already public, "
                "add a `pii-allow: <reason>` line to the file. Approve only if "
                "this push must leave as it is."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
