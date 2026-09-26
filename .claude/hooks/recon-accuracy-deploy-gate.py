#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell): the deploy gate for brisken-expense-recon.

Two jobs:

A. DENY a direct `flyctl deploy` of the app (2026-09-25). `flyctl deploy`
   ships the fly.toml of whatever tree it is pointed at, so a worktree cut
   before the latest merge silently undoes merged code AND platform settings.
   That day the machine was resized to shared-cpu-4x after a CPU-throttle
   outage (#1395) while several sessions deployed from older trees, any of
   which would have shrunk it back to the one-vCPU size that went down. The
   sanctioned path is the module's `deploy.py`, which refuses a stale or
   dirty tree and a fly.toml smaller than the live machine, stamps
   GIT_COMMIT and verifies the result. A tree old enough to be dangerous has
   no deploy.py, so it has no path to a deploy at all.

B. Score the real labelled months before a `deploy.py` run (below), which is
   what this gate did for direct deploys until A replaced them.

WHY THIS EXISTS
---------------
Backlog item 127. Matching accuracy for the Brisken expense-recon matcher was
measured by hand, offline (`uv run tools/scorers/recon-match-accuracy.py ...
--split all`), and nothing ran it before a deploy. CI now scores the committed
synthetic bundles on every PR (expense-recon-tests.yml, `accuracy` job), but
the six REAL labelled months are gitignored client data that exist only on
this machine, so the one place they can gate anything is here, at the moment
of the deploy.

WHAT IT DOES
------------
1. Looks only at what the normalized command RUNS (PowerShell spellings via
   _shell.normalize_command). Text a command merely WRITES is not a deploy:
   a `git commit -m` message, a heredoc a message-writing command consumes,
   and the arguments of mention-only programs (echo, grep, cat, ...) are
   stripped or skipped first, the same distinction deploy-consumer-gate.py
   draws.
2. A `fly deploy` / `flyctl deploy` of brisken-expense-recon (`-a` / `--app
   brisken-expense-recon`, or no app flag while the command or the tool's cwd
   mentions `expense-reconciliation`, the module whose fly.toml names the
   app) -> permissionDecision="deny" with the deploy.py command (job A).
   A deploy of any other app is silent.
3. A run of the module's deploy.py (not `--dry-run`, not an `--image`
   rollback, which ships no new matcher) -> job B:
   runs `uv run tools/recon_accuracy_check.py real --markdown` from the repo
   this hook lives in, with a 100 s budget (the wired timeout is 120 s).
4. exit 0            -> allow, print nothing.
   exit 1            -> permissionDecision="ask" with the tool's output as the
                        reason. The deploy is not blocked outright: the human
                        decides with the table in front of them.
   exit 2 / timeout  -> "ask", saying the score could not be measured.
   the hook's own exception -> allow with one advisory line on stderr
                        (fail-open; a gate that wedges deploys gets deleted).

TEST SEAM (never set in production)
-----------------------------------
  RECON_ACCURACY_GATE_CMD   replaces the check command. A JSON list is run
                            without a shell (`["<python>", "-c", "..."]`);
                            any other string runs through the shell. The
                            seam's exit code and output drive the decision
                            exactly as the real tool's would.
                            Tests: tools/tests/test_recon_accuracy_deploy_gate.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# Shared PowerShell/.cmd normalizer (matching view only; fail-open identity).
try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))
HOOK_LOG = os.path.join(HOOK_DIR, "hook-log.txt")
CHECK = os.path.join("tools", "recon_accuracy_check.py")
APP = "brisken-expense-recon"
MODULE_HINT = "expense-reconciliation"
BUDGET = 100  # seconds; under the 120 s wired timeout so a stall still answers

FLY_DEPLOY = re.compile(r"\bfly(?:ctl)?\s+deploy\b", re.IGNORECASE)
# The sanctioned path: the module's deploy.py as a path argument.
DEPLOY_SCRIPT = re.compile(r"(?:^|[\s\"'/\\])deploy\.py(?=[\"'\s]|$)", re.IGNORECASE)
SCRIPT_RUNNERS = frozenset({"uv", "python", "python3", "py"})
ENV_ASSIGN = re.compile(r"^\w+=\S*$")
SANCTIONED = (
    "git -C <repo> fetch origin\n"
    "git -C <repo> worktree add --detach <tree> origin/main   "
    "(or refresh one: git -C <tree> checkout --detach origin/main)\n"
    "uv run <tree>/workspace/clients/brisken/automations/"
    "expense-reconciliation/deploy.py   [--dry-run | --image <ref>]"
)
APP_FLAG = re.compile(
    r"(?:^|\s)(?:-a|--app)(?:\s+|=)[\"']?([\w.-]+)", re.IGNORECASE
)
# Commands whose payload is prose (written down, not run), and the flags whose
# value is always prose. Same shapes as deploy-consumer-gate.py.
PROSE_COMMANDS = r"(?:git\s+(?:commit|tag)|gh\s+(?:pr|issue|release)\s+\w+)"
PROSE_FLAGS = r"(?:-m|--message|--body|--title|--notes|--description)"
# Programs that only read or print text: a deploy named in their arguments
# is a mention, not a run.
MENTION_PROGRAMS = frozenset({
    "ls", "dir", "cat", "type", "head", "tail", "less", "grep", "egrep", "rg",
    "find", "echo", "printf", "wc", "which", "where", "sed", "awk",
    "get-childitem", "gci", "get-content", "gc", "select-string", "sls",
    "test-path", "write-output", "write-host",
})
SEGMENT_SPLIT = re.compile(r"\n|;|&&|\|\||\|")


def log(action: str) -> None:
    try:
        import datetime
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.datetime.now().isoformat()} "
                f"recon-accuracy-deploy-gate {action}\n"
            )
    except Exception:
        pass


def strip_authored_prose(cmd: str) -> str:
    """Drop text the command WRITES, keep text it RUNS."""
    out = re.sub(
        PROSE_COMMANDS + r"[^\n]*?<<-?\s*['\"]?(\w+)['\"]?\s*\n.*?\n\1\b",
        " ", cmd, flags=re.DOTALL | re.IGNORECASE,
    )
    out = re.sub(PROSE_FLAGS + r"\s+'[^']*'", " ", out)
    out = re.sub(PROSE_FLAGS + r'\s+"[^"]*"', " ", out)
    return out


def deploy_segments(view: str) -> list[str]:
    """The command segments that actually run a fly deploy."""
    out: list[str] = []
    for seg in SEGMENT_SPLIT.split(view):
        seg = seg.strip().lstrip("({ \t").strip()
        if not seg or not FLY_DEPLOY.search(seg):
            continue
        first = seg.split()[0].lower()
        if first in MENTION_PROGRAMS:
            continue
        out.append(seg)
    return out


def _program(seg: str) -> str:
    """The program a segment runs, past `VAR=value` prefixes and PowerShell's
    `&` call operator (which _shell keeps before a bare program name)."""
    for tok in seg.split():
        if tok != "&" and not ENV_ASSIGN.match(tok):
            return tok.strip("\"'").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return ""


def script_segments(view: str) -> list[str]:
    """The command segments that RUN deploy.py (not ones that mention it)."""
    out: list[str] = []
    for seg in SEGMENT_SPLIT.split(view):
        seg = seg.strip().lstrip("({ \t").strip()
        if not seg or not DEPLOY_SCRIPT.search(seg):
            continue
        prog = _program(seg)
        if prog in SCRIPT_RUNNERS or prog.endswith("deploy.py"):
            out.append(seg)
    return out


def targets_recon(segments: list[str], original: str, cwd: str | None) -> bool:
    """Is one of the deploy segments a deploy of brisken-expense-recon?"""
    hay = (original + " " + (cwd or "")).replace("\\", "/").lower()
    for seg in segments:
        m = APP_FLAG.search(seg)
        if m:
            if m.group(1).lower() == APP:
                return True
            continue  # names another app explicitly
        if MODULE_HINT in hay:
            return True
    return False


def run_check() -> tuple[object, str]:
    """(exit code | 'timeout' | 'error', combined output)."""
    seam = os.environ.get("RECON_ACCURACY_GATE_CMD")
    shell = False
    if seam:
        if seam.lstrip().startswith("["):
            argv: object = json.loads(seam)
        else:
            argv, shell = seam, True
    else:
        argv = ["uv", "run", CHECK, "real", "--markdown"]
    try:
        out = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True,
            timeout=BUDGET, shell=shell,
        )
    except subprocess.TimeoutExpired:
        return "timeout", ""
    except Exception as exc:  # noqa: BLE001 - reported as unmeasurable, never raised
        return "error", f"{type(exc).__name__}: {exc}"
    combined = (out.stdout or "") + (out.stderr or "")
    return out.returncode, combined.strip()


def ask(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def decide(payload: dict) -> None:
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd:
        return
    view = strip_authored_prose(normalize_command(cmd))
    segments = deploy_segments(view)
    if segments:
        if not targets_recon(segments, cmd, payload.get("cwd")):
            log("allow: fly deploy of another app")
            return
        log("DENY: direct flyctl deploy of the recon app")
        deny(
            f"DIRECT `flyctl deploy` OF {APP} IS BLOCKED. flyctl ships the "
            "fly.toml of whatever tree it is pointed at, so a tree cut before "
            "the latest merge undoes merged code and the machine size (on "
            "2026-09-25 that would have shrunk the machine back to the "
            "one-vCPU size whose CPU throttling took the app down). Deploy "
            "through the module's deploy.py from a tree that IS origin/main:\n\n"
            f"{SANCTIONED}\n\n"
            "It refuses a stale or dirty tree and a fly.toml smaller than the "
            "live machine, stamps GIT_COMMIT, then verifies /healthz and the "
            "machine size. If your tree has no deploy.py it predates this "
            "rule: refresh it, do not work around it."
        )
        return

    scripts = script_segments(view)
    if not scripts or not targets_recon(scripts, cmd, payload.get("cwd")):
        return
    if all(re.search(r"--dry-run|--image\b", s) for s in scripts):
        log("allow: deploy.py dry run / image rollback")
        return

    code, output = run_check()
    if code == 0:
        log("allow: real-bundle accuracy at or above baseline")
        return
    snippet = output[-3500:] if output else "(no output)"
    if code == 1:
        log("ASK: real-bundle accuracy below baseline")
        ask(
            "RECON MATCH ACCURACY IS BELOW ITS BASELINE. Before this deploy of "
            f"{APP}, `uv run tools/recon_accuracy_check.py real` scored the six "
            "real labelled months against tools/recon-accuracy-baseline.json "
            "and at least one split dropped (composite down, or more wrong "
            "deterministic matches, or a broken invariant):\n\n"
            f"{snippet}\n\n"
            "Deploying ships a matcher that mis-files or defers more of "
            "Criss's receipts than the one running now. Fix the matcher, or if "
            "the drop is deliberate re-record the baseline with `... real "
            "--write-baseline` and say why in the PR. Approve only to deploy "
            "anyway."
        )
        return
    what = (
        f"timed out after {BUDGET} s" if code == "timeout"
        else f"could not start ({output})" if code == "error"
        else f"exited {code}"
    )
    log(f"ASK: real-bundle accuracy unmeasurable ({what})")
    ask(
        f"RECON MATCH ACCURACY COULD NOT BE MEASURED before this deploy of "
        f"{APP}: `uv run tools/recon_accuracy_check.py real` {what}. Usually "
        "the six real labelled bundles are absent from this machine "
        "(gitignored client context) or the scorer's inputs failed to load.\n\n"
        f"{snippet}\n\n"
        "No verdict either way. Run the check by hand and fix its input, or "
        "approve to deploy without the accuracy read."
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    try:
        decide(payload)
    except Exception as exc:  # noqa: BLE001 - fail-open by contract
        log(f"allow: hook error {type(exc).__name__}: {exc}")
        sys.stderr.write(
            "[recon-accuracy-deploy-gate] skipped: hook error "
            f"{type(exc).__name__}: {exc}\n"
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
