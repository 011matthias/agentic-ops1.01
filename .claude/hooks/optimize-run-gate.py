#!/usr/bin/env python3
"""PreToolUse(Write|Edit + Bash|PowerShell) hook: optimize-run file ACL.

Backs rule_optimize_loop.md. During an ACTIVE /comd_optimize run (state file
.claude/optimize/run.json written only by tools/optimize_run.py), the
manifest's asset globs are the ONLY agent-writable repo surface — the
instructions (RUN.md), the journal (results.tsv), the guards, the scorers,
and the enforcement machinery itself are all locked. Reference basis:
karpathy/autoresearch discussion #322 — prompt-level bans fail; only
code-level ACLs hold (Crucible pattern).

Write|Edit arm:
  PASS   no active run (single isfile check) / out-of-repo / .scratch/ .tmp/
  ASK    state file exists but is unparseable (corrupt state must not become
         the unlock vector, and a hard deny would brick the repo)
  DENY   locked surface: run state, RUN.md, results.tsv, guard files,
         tools/scorers/**, PINS.json, .claude/hooks/**, wire-hooks.py,
         optimize_run.py, pin_scorer.py, comd_optimize.md,
         rule_optimize_loop.md   [machinery is HOOK-HARDCODED so a tampered
         state file cannot unlock it; run-specifics come from the state]
  DENY   any other in-repo path (outside declared asset scope)
  PASS   asset-glob match
  OPTIMIZE_SCOPE_ALLOW=1 (user-order-only) downgrades DENY->ADVISE, surfaced.

Bash|PowerShell arm (on _shell.normalize_command view):
  DENY   ALWAYS (run or no run): write-shaped command targeting
         tools/scorers/*.py or PINS.json — closes the shell-redirect bypass
         acknowledged in scorer-lock-gate.py (SCORER_LOCK_ALLOW seam honored)
  DENY   during a run: write-shaped command targeting any locked path;
         git checkout/restore/apply naming a locked pathspec (restoring an
         old scorer/manifest version is goalpost-moving)
  PASS   everything else; ambiguity passes (fail-open). The HARD guarantee
         against tampering is not this scan: optimize_run.py re-verifies
         scorer/manifest/journal hashes every round, and test_scorer_pins.py
         blocks a drifted pin from merging. Interpreter escapes
         (`python -c "open(...)"`) are a documented residual for the same
         reason.

Test seams (never set in production): OPTIMIZE_RUN_STATE, OPTIMIZE_RUN_GATE_REPO.
Defensive exit 0 wrapper: never bricks a tool call on hook crash.
"""
from __future__ import annotations

import json
import os
import re
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))
_ENV_REPO = os.environ.get("OPTIMIZE_RUN_GATE_REPO")
if _ENV_REPO:
    REPO = _ENV_REPO
REPO_POSIX = REPO.replace("\\", "/").rstrip("/")
REPO_POSIX_LOWER = REPO_POSIX.lower()

STATE_PATH = os.environ.get("OPTIMIZE_RUN_STATE") or os.path.join(
    REPO, ".claude", "optimize", "run.json")

sys.path.insert(0, HOOK_DIR)
from _globs import matches_any  # noqa: E402
from _shell import normalize_command  # noqa: E402

# Locked regardless of what the (tamperable) state file says. Prefixes end
# with "/"; exact files are full rel paths. All lowercase for comparison.
MACHINERY_LOCKED = (
    ".claude/hooks/",
    ".claude/optimize/",
    "tools/scorers/",
    "tools/wire-hooks.py",
    "tools/optimize_run.py",
    "tools/pin_scorer.py",
    ".claude/commands/comd_optimize.md",
    ".claude/rules/rule_optimize_loop.md",
)

SCORER_TARGET_RE = re.compile(
    r"tools/scorers/[^\s\"';|&)]*(\.py|pins\.json)\b", re.IGNORECASE)

# Write-shaped shell constructs. Each regex captures a "clause" whose
# path-ish tokens are candidate write targets.
_REDIRECT_RE = re.compile(r"(?:^|[^>])>{1,2}\s*([^\s;|&)]+)")
_TEE_RE = re.compile(r"\btee\b((?:\s+-\S+)*(?:\s+[^\s;|&]+)+)", re.IGNORECASE)
_SED_I_RE = re.compile(r"\bsed\b[^;|&\n]*\s-i\S*\b([^;|&\n]*)", re.IGNORECASE)
_PS_WRITE_RE = re.compile(
    r"\b(?:set-content|out-file|add-content|new-item|copy-item|move-item|"
    r"remove-item)\b([^;|&\n]*)", re.IGNORECASE)
_RM_RE = re.compile(r"\b(?:rm|del|unlink)\b([^;|&\n]*)", re.IGNORECASE)
_CP_MV_RE = re.compile(r"\b(?:cp|mv)\b((?:\s+-\S+)*(?:\s+[^\s;|&]+)+)",
                       re.IGNORECASE)
_GIT_RESTORE_RE = re.compile(
    r"\bgit\b[^;|&\n]*\b(?:checkout|restore|apply)\b([^;|&\n]*)", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\s\"';|&()]+")


def decision(kind: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
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


def rel_to_repo(path: str) -> str | None:
    p = path.replace("\\", "/")
    if not (len(p) >= 2 and p[1] == ":") and not p.startswith("/"):
        p = f"{REPO_POSIX}/{p.lstrip('/')}"
    if not p.lower().startswith(REPO_POSIX_LOWER + "/"):
        return None
    rel = p[len(REPO_POSIX) + 1:]
    return "/".join(seg for seg in rel.split("/") if seg not in ("", "."))


def load_state() -> dict | None | str:
    """dict = active run; None = no run; 'corrupt' = unparseable state."""
    if not os.path.isfile(STATE_PATH):
        return None
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict) or "tag" not in state:
            return "corrupt"
        return state
    except Exception:
        return "corrupt"


def is_locked(rel: str, state: dict) -> bool:
    low = rel.lower()
    for m in MACHINERY_LOCKED:
        if low == m.rstrip("/") or (m.endswith("/") and low.startswith(m)):
            return True
    for entry in state.get("locked", []):
        e = str(entry).replace("\\", "/").lstrip("/").lower()
        if low == e or (e.endswith("/") and low.startswith(e)):
            return True
    return False


def scope_allow() -> bool:
    return bool(os.environ.get("OPTIMIZE_SCOPE_ALLOW"))


def handle_file_write(rel: str | None, state: dict) -> int:
    if rel is None:
        return 0
    low = rel.lower()
    if low.startswith((".scratch/", ".tmp/")):
        return 0
    tag = state.get("tag", "?")
    if is_locked(rel, state):
        msg = (
            f"[optimize-run] {rel} is LOCKED during active optimize run "
            f"'{tag}' (rule_optimize_loop.md: instructions, journal, guards, "
            "scorers, and the enforcement machinery are not agent-writable "
            "while a run is live). Legitimate outs: finish/abort the run "
            "(`uv run tools/optimize_run.py stop`) or a user-ordered "
            "OPTIMIZE_SCOPE_ALLOW=1 override."
        )
    elif matches_any(state.get("assets", []), rel):
        return 0
    else:
        msg = (
            f"[optimize-run] {rel} is outside the declared asset scope of "
            f"active optimize run '{tag}'. The manifest's asset globs are the "
            "only writable surface during a run. Outs: `uv run tools/"
            "optimize_run.py stop`, or a user-ordered OPTIMIZE_SCOPE_ALLOW=1."
        )
    if scope_allow():
        advise("OVERRIDE ACTIVE (OPTIMIZE_SCOPE_ALLOW=1): " + msg +
               " Confirm the user ordered this specific edit.")
        return 0
    decision("deny", msg)
    return 0


def shell_write_targets(view: str) -> list[str]:
    """Candidate write-target tokens from the normalized command view."""
    targets: list[str] = []
    targets += _REDIRECT_RE.findall(view)
    for m in _TEE_RE.finditer(view):
        targets += [t for t in _TOKEN_RE.findall(m.group(1))
                    if not t.startswith("-")]
    for rx in (_SED_I_RE, _PS_WRITE_RE, _RM_RE):
        for m in rx.finditer(view):
            targets += [t for t in _TOKEN_RE.findall(m.group(1))
                        if not t.startswith("-") and
                        ("/" in t or t.lower().endswith(
                            (".py", ".json", ".tsv", ".md")))]
    for m in _CP_MV_RE.finditer(view):
        toks = [t for t in _TOKEN_RE.findall(m.group(1))
                if not t.startswith("-")]
        if toks:
            targets.append(toks[-1])  # destination
    return targets


def handle_shell(cmd: str, state: dict | None | str) -> int:
    view = normalize_command(cmd)
    targets = shell_write_targets(view)
    rels = [r for r in (rel_to_repo(t.strip("'\"")) for t in targets) if r]

    # Always-on scorer surface (independent of any run).
    scorer_hits = [r for r in rels if SCORER_TARGET_RE.match(r.lower())]
    if scorer_hits:
        if os.environ.get("SCORER_LOCK_ALLOW"):
            advise(
                f"OVERRIDE ACTIVE (SCORER_LOCK_ALLOW=1): shell write to "
                f"{scorer_hits[0]} permitted for user-approved scorer "
                "maintenance. Re-pin via tools/pin_scorer.py afterwards."
            )
        else:
            decision("deny", (
                f"[optimize-run] shell write to locked scorer surface "
                f"{scorer_hits[0]} (tools/scorers/ is never agent-writable "
                "by shell; Write/Edit + scorer-lock-gate govern authoring, "
                "pin_scorer.py governs pins)."
            ))
            return 0

    if not isinstance(state, dict):
        if state == "corrupt" and rels:
            decision("ask", (
                "[optimize-run] optimize run state (.claude/optimize/run.json) "
                "exists but is unparseable; repo writes need human consent "
                "until it is repaired or removed via "
                "`uv run tools/optimize_run.py stop`."
            ))
        return 0

    tag = state.get("tag", "?")
    locked_hits = [r for r in rels if is_locked(r, state)]
    for m in _GIT_RESTORE_RE.finditer(view):
        for t in _TOKEN_RE.findall(m.group(1)):
            r = rel_to_repo(t.strip("'\""))
            if r and is_locked(r, state):
                locked_hits.append(r)
    if locked_hits:
        msg = (
            f"[optimize-run] shell command writes/restores locked path "
            f"{locked_hits[0]} during active optimize run '{tag}'. Outs: "
            "`uv run tools/optimize_run.py stop` or user-ordered "
            "OPTIMIZE_SCOPE_ALLOW=1."
        )
        if scope_allow():
            advise("OVERRIDE ACTIVE (OPTIMIZE_SCOPE_ALLOW=1): " + msg)
        else:
            decision("deny", msg)
    return 0


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}

    if tool in ("Bash", "PowerShell"):
        cmd = tool_input.get("command", "") or ""
        if not cmd:
            return 0
        return handle_shell(cmd, load_state())

    if tool not in ("Write", "Edit"):
        return 0

    raw_path = tool_input.get("file_path", "") or ""
    if not raw_path:
        return 0
    state = load_state()
    if state is None:
        return 0
    rel = rel_to_repo(raw_path)
    if state == "corrupt":
        if rel is not None:
            decision("ask", (
                "[optimize-run] optimize run state (.claude/optimize/run.json) "
                "exists but is unparseable. Corrupt state must not unlock the "
                "run: repo writes need human consent until the state is "
                "repaired or the run is closed "
                "(`uv run tools/optimize_run.py stop`)."
            ))
        return 0
    return handle_file_write(rel, state)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # defensive: never brick a tool call
