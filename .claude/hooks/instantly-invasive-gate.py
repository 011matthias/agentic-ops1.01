#!/usr/bin/env python3
"""PreToolUse(Bash): tripwire for invasive Instantly API calls.

Enforces rule_instantly_invasive.md (B5). A mutating call to api.instantly.ai
must never run silently. This hook detects state-changing calls and forces a
permission stop ("ask"), so the user is in the loop on every invasive action
even if the agent missed the scope-of-effects protocol.

Detection has four layers (register #11 2026-06-08 + #177 2026-06-09: the
string-only scan missed every invasive op run INSIDE a python loader, because
`api.instantly.ai` was in the script file, not the Bash command string -- the
highest-blast-radius step, campaign activate = real emails, ran unguarded):

  A. `api.instantly.ai` literally in the command (curl, `python -c`, heredoc).
     Read paths (/leads/list, /campaigns/analytics, /analytics) and any call
     with no mutating method pass; a mutating method to any other path -> ask.
  B. A known invasive loader script (`*instantly*load*.py`) classified by its
     `--stage`: mutating stages (create/load/activate/import/archive/...) ask,
     read-only stages (preview/audit/...) pass, anything unrecognised on a
     loader fails toward ask. Loaders are judged by stage, not by content,
     because the file always contains mutating code for its OTHER stages.
  C. python/uv running a NON-loader .py whose CONTENTS reference
     `api.instantly.ai` together with a mutating method -> ask. Test/fixture
     files and the hook layer are excluded (they reference the API as data).
  D. fail-toward-ask: a python invocation carrying an Instantly signal whose
     target script could not be inspected. Never blanket-asks arbitrary python.

Non-blocking by design uses permissionDecision="ask" (not deny) so a genuinely
user-requested + confirmed action can still proceed via the prompt.
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

# Optional shared session-state store (tools/, repo-root-relative). Used ONLY
# to persist a friction candidate when this gate fires "ask" -- a pure
# side-effect that never alters the gate's decision.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
READ_PATHS = ("/leads/list", "/campaigns/analytics", "/analytics")

# Mutating-method signal. Covers curl (-X/--request), requests/httpx/aiohttp
# client idioms, and the urllib `Request(..., method="POST")` kwarg. Also covers
# a curl body flag (-d/--data*/-F/--form) with no explicit -X: curl sends those
# as an implicit POST, so `curl --data '{}' .../pause` was slipping through
# unguarded (register #11/#177 follow-up 2026-06-18, the highest-blast-radius
# gate). Does NOT include the loaders' internal `api("POST", "/leads/list")`
# helper idiom: that would false-fire on read-only census scripts that POST to
# /leads/list, and loaders are judged by --stage (layer B) not by content anyway.
MUTATING_METHOD = re.compile(
    r"""(?ix)
    (?:-X\s*|--request\s+)(?:POST|PUT|PATCH|DELETE)\b
    | \b(?:requests|httpx|session|client|aiohttp)\s*\.\s*(?:post|put|patch|delete)\b
    | \bmethod\s*=\s*["'](?:POST|PUT|PATCH|DELETE)["']
    | (?:^|\s)(?:-d|--data(?:-raw|-binary|-urlencode)?|-F|--form)\b
    """
)
MUTATING_STAGES = {
    "create", "load", "activate", "import", "archive",
    "resume", "pause", "delete", "start", "stop", "send",
}
READONLY_STAGES = {
    "preview", "audit", "verify", "check", "dry-run", "dryrun",
    "list", "status", "count", "report", "inspect", "plan", "show",
}
LOADER_RE = re.compile(r"[\w./\\-]*instantly[\w./\\-]*load[\w./\\-]*\.py", re.IGNORECASE)
STAGE_RE = re.compile(r"--stage[ =]+([a-z0-9_-]+)", re.IGNORECASE)
PY_INVOKE = re.compile(r"\b(?:python3?|uv\s+run)\b")
INSTANTLY_TOKEN = re.compile(r"instantly", re.IGNORECASE)
PY_PATH_RE = re.compile(r"""[^\s"']+\.py\b""")


def log(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} instantly-invasive-gate {action}\n")
    except Exception:
        pass


def _py_targets(cmd: str) -> list[str]:
    """Candidate .py script paths invoked in the command (drop flags)."""
    return [t for t in PY_PATH_RE.findall(cmd) if not t.startswith("-")]


def _resolve(p: str):
    """Resolve a script path arg to an existing file: as-is, then relative to
    the shell cwd, then relative to the repo root. None if not found."""
    repo = Path(__file__).resolve().parents[2]
    for cand in (Path(p), Path(os.getcwd()) / p, repo / p):
        try:
            if cand.is_file():
                return cand
        except Exception:
            pass
    return None


def _is_test_or_hook(rp: Path) -> bool:
    """Test/fixture files and the hook layer reference api.instantly.ai as DATA
    (test payloads, the gate's own patterns), not as a runtime action."""
    lowparts = {part.lower() for part in rp.parts}
    return (
        rp.name.lower().startswith("test_")
        or "tests" in lowparts
        or "fixtures" in lowparts
        or ".claude" in lowparts
    )


def _ask(cmd: str, detail: str) -> None:
    log(f"ASK:{detail[:70]}")
    # Side-effect only: persist a friction candidate for the checkpoint drain.
    # Must never affect the decision.
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-instantly-invasive", "instantly-invasive-gate", cmd[:240],
            )
        except Exception:
            pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"INVASIVE INSTANTLY ACTION detected ({detail}). Per "
                "rule_instantly_invasive.md (B5): this must NOT run unless the user "
                "specifically asked for this exact action AND was first given a "
                "plain-language scope-of-effects explanation (what changes, who it "
                "touches in the real world, what is irreversible, reputation/credit/"
                "deliverability impact) and gave a clear yes. If that protocol was "
                "not completed, cancel and follow it first."
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

    # --- Layer A: api.instantly.ai literally in the command string ---
    if "api.instantly.ai" in cmd:
        is_read_path = any(p in cmd for p in READ_PATHS)
        if is_read_path or not MUTATING_METHOD.search(cmd):
            log("allow:read")
            sys.exit(0)
        _ask(cmd, "inline state-changing api.instantly.ai request")

    # --- Layer B: known invasive loader script, classified by --stage ---
    if LOADER_RE.search(cmd):
        sm = STAGE_RE.search(cmd)
        stage = sm.group(1).lower() if sm else None
        if stage in MUTATING_STAGES:
            _ask(cmd, f"Instantly loader mutating stage --stage {stage}")
        if stage in READONLY_STAGES:
            log(f"allow:loader-readonly:{stage}")
            sys.exit(0)
        # A known loader with an absent / unrecognised stage -> fail toward ask
        # (this is the highest-blast-radius gate; bias to a one-click prompt).
        _ask(cmd, f"Instantly loader with unclassified stage ({stage!r})")

    # --- Layer C: python/uv running a non-loader .py that touches the API ---
    if PY_INVOKE.search(cmd):
        targets = _py_targets(cmd)
        inspected_any = False
        for t in targets:
            rp = _resolve(t)
            if rp is None:
                continue
            inspected_any = True
            if _is_test_or_hook(rp):
                continue
            try:
                text = rp.read_text(encoding="utf-8", errors="ignore")[:200_000]
            except Exception:
                continue
            if "api.instantly.ai" in text and MUTATING_METHOD.search(text):
                _ask(cmd, f"script {rp.name} contains a state-changing api.instantly.ai call")
        # --- Layer D: fail-toward-ask ONLY with an uninspectable Instantly signal ---
        if targets and not inspected_any and INSTANTLY_TOKEN.search(cmd):
            _ask(cmd, "Instantly-related script could not be inspected before running")

    log("allow:no-signal")
    sys.exit(0)


if __name__ == "__main__":
    main()
