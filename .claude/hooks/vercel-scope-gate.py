#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell): scope guard for the shared akkton Vercel session.

The Vercel CLI on this machine periodically holds Nicolas's (akkton) session,
whose scope contains projects beyond unpauseai.com (lydar-app, webvorschau-ka).
Vercel personal sessions cannot be project-scoped at the provider, so this gate
enforces the boundary locally: agent-issued Vercel commands may touch ONLY the
platform project (unpauseai.com) or the user's own scope. Anything that names,
or could fall through to, another akkton project forces a permission stop.

Decision layers (target-based, not verb-based):

  A. Foreign-project tripwire: any Vercel-signal command naming lydar /
     webvorschau (name, project id, or domain) -> ask. Always.
  B. Own-scope pass: --scope matthias-neumanns-projects (the user's own
     account) -> allow.
  B2. Explicit non-platform target (allowlist posture): after the own-scope
     pass, any `--project <name>` that is not `platform`, or any `prj_<id>`
     that is not the platform id -> ask. This is rigid against UNKNOWN /
     future akkton projects, not just the named denylist, and it overrides a
     platform-linked cwd (an explicit --project wins over the .vercel link, so
     the cwd check in D must not be trusted when a foreign project is named
     outright). Fires for reads too: touching another project's env/data by
     explicit id is off limits. The user's own scope is already exempted at B.
  C. Platform pass: an explicit platform marker (--project platform, the
     platform project id, unpauseai.com, /projects/platform API path) -> allow.
  D. Unscoped mutation fail-toward-ask: deploy/promote/rollback/env/rm/alias/
     link and mutating api.vercel.com calls with NO platform marker resolve
     the target from the invocation directory's .vercel/project.json; if that
     does not resolve to the platform project id -> ask.
  E. Everything else with a Vercel signal (reads: ls, whoami, teams, inspect,
     GET api calls) -> allow. Listing is not contamination; acting is.

Non-blocking: permissionDecision="ask" so a genuinely intended cross-project
action can still proceed via the prompt (mirrors instantly-invasive-gate).
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

PLATFORM_PROJECT_ID = "prj_xMUV3AVgiAq9uXC9YaX0tMxQdAvl"
OWN_SCOPE = "matthias-neumanns-projects"

VERCEL_SIGNAL = re.compile(r"(?i)\bvercel\b|api\.vercel\.com")
FOREIGN = re.compile(
    r"(?i)lydar|webvorschau|prj_Zk3VdKvdg4GGG9rz|app\.lydar\.com\.br"
)
PLATFORM_MARKER = re.compile(
    r"(?i)--project[ =]+platform\b"
    rf"|{PLATFORM_PROJECT_ID}"
    r"|unpauseai\.com"
    r"|/projects/platform\b"
)
API_MUTATING = re.compile(
    r"(?i)(?:-X\s*|--request\s+|method\s*=\s*[\"'])(?:POST|PUT|PATCH|DELETE)"
)


def log(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} vercel-scope-gate {action}\n")
    except Exception:
        pass


def _cwd_is_platform_linked(cmd: str) -> bool:
    """Resolve the invocation directory's .vercel/project.json (cwd, or a
    `cd <dir>` / `--cwd <dir>` target in the command) to the platform id."""
    candidates = [Path(os.getcwd())]
    for m in re.finditer(r"(?:\bcd\s+|--cwd[ =])[\"']?([^\s\"';&|]+)", cmd):
        candidates.append(Path(m.group(1)))
    for base in candidates:
        for probe in (base, base / "platform"):
            pj = probe / ".vercel" / "project.json"
            try:
                if pj.is_file():
                    data = json.loads(pj.read_text(encoding="utf-8"))
                    if data.get("projectId") == PLATFORM_PROJECT_ID:
                        return True
            except Exception:
                continue
    return False


def _ask(cmd: str, detail: str) -> None:
    log(f"ASK:{detail[:70]}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-vercel-scope", "vercel-scope-gate", cmd[:240],
            )
        except Exception:
            pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"VERCEL SCOPE BOUNDARY ({detail}). The CLI may hold the shared "
                "akkton session, whose scope includes projects beyond "
                "unpauseai.com (lydar-app, webvorschau-ka). Agent-issued Vercel "
                "actions are restricted to the platform project (unpauseai.com) "
                "or the user's own scope to prevent cross-project contamination. "
                "If this cross-project action is genuinely intended, approve it; "
                "otherwise cancel and retarget the platform project explicitly."
            ),
        }
    }))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd:
        sys.exit(0)

    view = normalize_command(cmd)
    if not VERCEL_SIGNAL.search(view):
        sys.exit(0)

    # A. foreign-project tripwire
    if FOREIGN.search(view):
        _ask(cmd, "command names a non-platform akkton project")

    # B. user's own scope
    if OWN_SCOPE in view:
        log("allow:own-scope")
        sys.exit(0)

    # B2. explicit NON-platform project target -> ask (allowlist posture).
    # Rigid against unknown/future akkton projects, not just the A denylist.
    # An explicit --project overrides the .vercel link, so this must fire even
    # from a platform-linked cwd (before D's cwd allow). Own scope already
    # exited at B, so a user's own non-platform project is unaffected.
    pm = re.search(r"(?i)--project[ =]+([^\s\"';&|]+)", view)
    if pm and pm.group(1).lower() not in ("platform", PLATFORM_PROJECT_ID.lower()):
        _ask(cmd, "explicit non-platform project target (--project)")
    for pid in re.findall(r"(?i)prj_[A-Za-z0-9]+", view):
        if pid != PLATFORM_PROJECT_ID:
            _ask(cmd, "explicit non-platform project id")

    # C. explicit platform target
    if PLATFORM_MARKER.search(view):
        log("allow:platform-marker")
        sys.exit(0)

    # D. mutation with unresolved target
    is_api_call = "api.vercel.com" in view or re.search(r"\bvercel\s+api\b", view)
    if is_api_call:
        if API_MUTATING.search(view):
            _ask(cmd, "mutating Vercel API call with no platform marker")
        log("allow:api-read")
        sys.exit(0)
    if re.search(
        r"(?i)\bvercel\b[^|;&]*\b(?:deploy|promote|rollback|rm|remove|env|alias|link|dns|domains|redeploy|rename)\b"
        r"|\bvercel\b[^|;&]*--prod\b",
        view,
    ):
        if _cwd_is_platform_linked(cmd):
            log("allow:cwd-linked-platform")
            sys.exit(0)
        _ask(cmd, "target-sensitive vercel command with unresolved project target")

    # E. reads and neutral commands
    log("allow:read")
    sys.exit(0)


if __name__ == "__main__":
    main()
