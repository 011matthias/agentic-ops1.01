#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell): score the real labelled months before a
`flyctl deploy` of brisken-expense-recon.

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
1. Fires only when the normalized command RUNS `fly deploy` / `flyctl deploy`
   (PowerShell spellings via _shell.normalize_command). Text a command merely
   WRITES is not a deploy: a `git commit -m` message, a heredoc a
   message-writing command consumes, and the arguments of mention-only
   programs (echo, grep, cat, ...) are stripped or skipped first, the same
   distinction deploy-consumer-gate.py draws.
2. ... AND the app is brisken-expense-recon: `-a` / `--app brisken-expense-recon`,
   or no app flag while the command or the tool's cwd mentions
   `expense-reconciliation` (the module dir whose fly.toml names the app).
   A deploy of any other app is silent.
3. Runs `uv run tools/recon_accuracy_check.py real --markdown` from the repo
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


def decide(payload: dict) -> None:
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd:
        return
    view = strip_authored_prose(normalize_command(cmd))
    segments = deploy_segments(view)
    if not segments:
        return
    if not targets_recon(segments, cmd, payload.get("cwd")):
        log("allow: fly deploy of another app")
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
