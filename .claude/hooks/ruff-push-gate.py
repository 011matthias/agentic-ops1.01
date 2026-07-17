#!/usr/bin/env python3
"""PreToolUse(Bash): run the CI ruff step locally before a `git push`.

WHY THIS EXISTS
---------------
Between 2026-06-12 and 2026-07-17 the CI `Enforcement hook tests` job was
green on every PR. On 2026-07-16..17 a burst of new Python/test files landed
and five PR CI runs went red on the SAME class of failure -- code that passed
on the author's machine but failed in the clean CI env:

    lead-desk-cockpit  ruff F401 unused `io` + F841 unused `core_r`
    optimize-v2-engine ruff F401 unused `pytest`
    deck-foundation-v2 ruff F401 unused `io`
    optimize-multi-project  (pytest collection: ModuleNotFoundError yaml)

Four of the five were trivial ruff lint errors (E9/F ruleset in ruff.toml) in
newly-added files. The opt-in `.pre-commit-config.yaml` ruff hook WOULD have
caught them, but it is not installed, so the first signal was a red CI run
after the push. Each self-healed with a follow-up commit, but every author ate
a diagnose-and-repush cycle.

Per the self-annealing ladder (rule_behaviors.md Layer 1: tool > rule >
memory), a recurrent + preventable failure gets a structural gate that fires
automatically, not a memory that depends on recall. This is that gate: it runs
the EXACT CI ruff command locally at `git push` time so a lint error is caught
before it leaves the machine, not after CI rejects it. It is the fast half of
the enforcement-hooks CI job; the slow pytest half stays in CI + the on-demand
`tools/preflight-hooks.py --full` runner. See rule_no_auto_commit.md (B6).

WHAT IT DOES
------------
1. Fires only on a `git push` command (normalized view, so `git.exe push` and
   PowerShell call-operator spellings are seen too).
2. Skips silently when the push's diff touches NO `.py` file under the ruff
   scope (`tools/`, `.claude/hooks/`; `tools/tests/` is under `tools/`). A
   docs-only / platform-only push is not this job's concern (the platform has
   its own tsc/eslint CI). When the diff is undeterminable, it does NOT skip
   (bias to running the check).
3. Runs `ruff check tools .claude/hooks tools/tests` -- byte-for-byte the CI
   invocation -- against the repo the push is coming from.
4. ruff clean -> allow silently. ruff FAILS -> permissionDecision="ask" with
   the ruff output inline, so the human sees the exact lint errors and the
   agent fixes them (or approves a known-irrelevant failure, e.g. a sibling
   session's uncommitted WIP in a shared working tree).

Mirrors no-auto-commit-gate.py / instantly-invasive-gate.py: "ask", never a
hard deny. The push is not blocked from the human; it is surfaced. Fixing the
lint and retrying is the intended response.

DEFENSIVE CONTRACT
------------------
Any error, missing/short payload, git failure, ruff-missing, or timeout ->
exit 0, allow. A broken linter gate must NEVER brick a push; a missed lint
error is cheaper than a blocked git workflow (and CI is still the backstop).

OVERRIDE / TEST SEAMS (never set in production)
-----------------------------------------------
  RUFF_PUSH_GATE_ALLOW=1        deliberate bypass -> allow with a stderr note.
  RUFF_PUSH_GATE_FORCE_INSCOPE  "1"/"0" forces the scope decision.
  RUFF_PUSH_GATE_FORCE_RUFF     "pass" / "fail" / "<text>" forces the ruff
                                verdict (text becomes the reported output),
                                so tests never spawn uv/ruff/git.
"""
import json
import os
import re
import subprocess
import sys

# Shared PowerShell/.cmd normalizer (matching view only; fail-open identity),
# same helper the ship gate uses so Windows spellings can't evade the pattern.
try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# `git push` on the normalized view. `git.exe push` -> `git push` post-normalize.
GIT_PUSH = re.compile(r"\bgit\s+push\b", re.IGNORECASE)

# A file is in the ruff scope when it is a .py under tools/ or .claude/hooks/.
# tools/tests/ is a subdir of tools/, so this covers all three CI scope dirs.
PY_SCOPE = re.compile(r"^(?:tools/|\.claude/hooks/).*\.py$")

# The EXACT CI ruff invocation (ci.yml: "Ruff (real-bug ruleset)"). ruff finds
# ruff.toml by walking up from cwd, so the ruleset (E9,F) + per-file-ignores
# match CI regardless of the ruff binary source.
RUFF_ARGS = ["ruff", "check", "tools", ".claude/hooks", "tools/tests"]
RUFF_TIMEOUT = 8  # seconds; under the 10s wired hook timeout so we fail-open cleanly


def log(action: str) -> None:
    try:
        import datetime
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} ruff-push-gate {action}\n")
    except Exception:
        pass


def _git(args, cwd=None):
    """Run a git command, return CompletedProcess or None on failure."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=5, cwd=cwd,
        )
    except Exception:
        return None


def repo_root() -> str | None:
    """Toplevel of the git repo the push is coming from (the current cwd)."""
    out = _git(["rev-parse", "--show-toplevel"])
    if out and out.returncode == 0 and out.stdout.strip():
        return out.stdout.strip()
    return None


def pushed_files(cwd: str | None) -> list[str] | None:
    """Files in the commits about to be pushed (upstream..HEAD).

    Falls back through @{u} -> origin/main -> main so a first push (no upstream
    yet) still resolves a sensible base. Returns None when undeterminable (not
    a repo / all bases missing), which the caller treats as in-scope.
    """
    base = None
    up = _git(["rev-parse", "--abbrev-ref", "@{u}"], cwd=cwd)
    if up and up.returncode == 0 and up.stdout.strip() and "@{u}" not in up.stdout:
        base = up.stdout.strip()
    else:
        for cand in ("origin/main", "main", "origin/master", "master"):
            chk = _git(["rev-parse", "--verify", "--quiet", cand], cwd=cwd)
            if chk and chk.returncode == 0:
                base = cand
                break
    if not base:
        return None
    diff = _git(["diff", "--name-only", f"{base}...HEAD"], cwd=cwd)
    if not diff or diff.returncode != 0:
        return None
    return [f for f in diff.stdout.splitlines() if f.strip()]


def push_in_scope(cwd: str | None) -> bool:
    """True if the push touches a .py under the ruff scope, or is undeterminable."""
    forced = os.environ.get("RUFF_PUSH_GATE_FORCE_INSCOPE")
    if forced in ("0", "1"):
        return forced == "1"
    files = pushed_files(cwd)
    if files is None:
        return True  # bias to running the check when we cannot tell
    return any(PY_SCOPE.match(f.replace("\\", "/")) for f in files)


def run_ruff(cwd: str | None):
    """Return (ok, output) or None (undeterminable -> fail-open).

    ok is True when ruff exits 0. output carries the ruff findings for the
    reason text. Prefers the exact-CI uv invocation; a bare `ruff` on PATH is
    used only as a same-ruleset fast path.
    """
    forced = os.environ.get("RUFF_PUSH_GATE_FORCE_RUFF")
    if forced is not None:
        if forced == "pass":
            return (True, "")
        if forced == "fail":
            return (False, "F401 [*] `io` imported but unused (forced test failure)")
        return (False, forced)
    # Exact CI parity: `uv run --no-project --with ruff ruff check ...`.
    cmd = ["uv", "run", "--no-project", "--with", "ruff", *RUFF_ARGS]
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=RUFF_TIMEOUT,
        )
    except Exception:
        return None  # uv/ruff missing or slow -> fail-open, CI is the backstop
    combined = (out.stdout or "") + (out.stderr or "")
    return (out.returncode == 0, combined.strip())


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd:
        sys.exit(0)

    view = normalize_command(cmd)
    if not GIT_PUSH.search(view):
        sys.exit(0)  # not a push -> not our concern

    if os.environ.get("RUFF_PUSH_GATE_ALLOW"):
        log("allow: RUFF_PUSH_GATE_ALLOW override")
        sys.stderr.write("[ruff-push-gate] bypassed via RUFF_PUSH_GATE_ALLOW.\n")
        sys.exit(0)

    root = repo_root()  # None outside a repo; git/ruff then run in inherited cwd
    if not push_in_scope(root):
        log("allow: push touches no .py in ruff scope")
        sys.exit(0)

    verdict = run_ruff(root)
    if verdict is None:
        log("allow: ruff undeterminable (uv/ruff unavailable or timed out) -> fail-open")
        sys.exit(0)
    ok, output = verdict
    if ok:
        log("allow: ruff clean")
        sys.exit(0)

    # ruff failed -> surface the exact errors and ask. Same primitive as the
    # ship gate: the human decides, but the intended response is to FIX the lint.
    log("ASK: ruff failed on git push")
    snippet = output[:1500] if output else "(ruff reported errors but produced no output)"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "RUFF WOULD FAIL THIS PUSH IN CI. The `Enforcement hook tests` "
                "job runs `ruff check tools .claude/hooks tools/tests` (ruleset "
                "E9,F from ruff.toml); it is currently failing on the working "
                "tree:\n\n"
                f"{snippet}\n\n"
                "Per rule_no_auto_commit.md (B6), pushing this ships a red PR. "
                "FIX the lint errors above (unused imports/vars are the common "
                "case), then push again. Run `uv run tools/preflight-hooks.py` "
                "for the full local CI-parity check (ruff + INDEX + pytest). If "
                "this failure is unrelated to your change (e.g. a sibling "
                "session's uncommitted file in a shared working tree), approve "
                "to push anyway, or set RUFF_PUSH_GATE_ALLOW=1 for a deliberate "
                "one-off bypass."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
