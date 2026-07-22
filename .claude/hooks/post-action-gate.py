#!/usr/bin/env python3
"""PostToolUse(Bash|PowerShell) hook: inject ship-gate / B2 / hard-limit advisories.

Pattern-matches the executed command:
  git push|commit / gh pr ...        -> [SHIP GATE] reminder
  npm run build / pytest / uv run    -> [B2] verification reminder
  3 consecutive build/test commands  -> [HARD LIMIT] (3-iteration cap)
  PR merge that touched platform/    -> [MERGE-NOT-LIVE] + a not-live marker

The not-live marker persists in a temp file: it re-surfaces as
[PLATFORM NOT LIVE] on every later ship-class command and is cleared by a
vercel-force-deploy run. Merges that touched no platform/ path say nothing,
which is what turns the old fire-on-every-merge advisory into a marker.

The 3-in-a-row counter persists in a temp file. The counter increments only
on REAL fix-then-test loops -- the same command (or near-identical, fuzzy by
fingerprint) repeated -- not on a sweep of DIFFERENT verification commands
hitting the build-test pattern set. This mirrors the gate-skip-detector
READONLY exemption and closes the 2026-05-26 false-positive: a behavioral
test sweep of 4 different inputs to a new hook tripped HARD LIMIT 3/3
even though each input was a distinct test, not a fix-retry.

See rule_behaviors.md 'Ship gate' and 'Build escalation'.

Defensive: any error -> exit 0 silently.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

# Shared PowerShell/.cmd normalizer (matching view only; fail-open identity).
try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
COUNTER_FILE = os.path.join(tempfile.gettempdir(), "agentic-ops-build-counter.txt")
# Platform-merge-is-not-live marker: set when a merged PR actually touched
# platform/ paths, cleared when vercel-force-deploy.sh runs. See the
# rule_behaviors 'Platform-merge-is-not-live' sub-clause.
PLATFORM_FLAG_FILE = os.path.join(tempfile.gettempdir(), "agentic-ops-platform-not-live.txt")
# A marker older than this is assumed dead (machine left on, session over) and
# stops nagging, so a forgotten flag can never nag indefinitely.
PLATFORM_FLAG_TTL_SEC = 12 * 3600
PLATFORM_PREFIXES = ("platform/",)
GH_TIMEOUT_SEC = 6  # hook budget is 10s; leave headroom.

SHIP_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+commit\b",
    r"\bgh\s+pr\s+(create|merge|edit)\b",
    r"\btools/gh-merge\.sh\b",   # the safe `gh pr merge` wrapper IS a merge
    r"\bvercel\s+(deploy|--prod)\b",
]
BUILD_TEST_PATTERNS = [
    r"\bnpm\s+run\s+build\b",
    r"\bnpm\s+test\b",
    r"\bpytest\b",
    r"\buv\s+run\s+(pytest|python)\b",
    r"\bnpm\s+run\s+typecheck\b",
    r"\btsc\b",
    r"\bgo\s+test\b",
    r"\bcargo\s+(build|test)\b",
]
# Commands that LOOK like build/test (match BUILD_TEST_PATTERNS) but are
# really read-only / behavioral verification / hook tests. These never count
# toward the streak — mirrors gate-skip-detector READONLY_PATTERNS so a sweep
# of validators or hook-tests doesn't false-fire iteration-3x.
EXEMPT_PATTERNS = [
    r"\.claude/hooks/[\w.-]+\.py",          # invoking a hook directly = hook test
    r"\btools/(?:validate|wire-hooks|friction-watch|spec-staleness|safe-edit|gh-merge|rename-chat)\b",
    r"--check\b", r"--dry-run\b", r"--list\b", r"--help\b", r"-h\b",
    r"\bpy_compile\b",
    r"\bjson\.tool\b", r"\bjson\.load\b",
    r"echo\s+'?\{",                         # piping a JSON event into a hook = hook test
]


def is_exempt(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in EXEMPT_PATTERNS)


def fingerprint(cmd: str) -> str:
    norm = re.sub(r"\s+", " ", cmd.strip())[:200]
    return hashlib.sha1(norm.encode("utf-8", errors="ignore")).hexdigest()[:12]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} post-action-gate {msg}\n")
    except Exception:
        pass


def read_state() -> tuple[int, str]:
    """Counter file now stores 'count\\tlast_fingerprint'. Backwards-compatible
    with the older int-only format."""
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        return 0, ""
    if not raw:
        return 0, ""
    if "\t" in raw:
        n_str, fp = raw.split("\t", 1)
        try:
            return int(n_str), fp
        except ValueError:
            return 0, ""
    try:
        return int(raw), ""
    except ValueError:
        return 0, ""


def write_state(n: int, fp: str) -> None:
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(f"{n}\t{fp}")
    except Exception:
        pass


def read_platform_flag() -> str | None:
    """Return the pending not-live label, or None when nothing is pending.

    Stored as 'epoch\\tlabel'. A marker past PLATFORM_FLAG_TTL_SEC is treated
    as absent (and left on disk; the next write overwrites it)."""
    try:
        with open(PLATFORM_FLAG_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        return None
    if "\t" not in raw:
        return None
    ts_str, label = raw.split("\t", 1)
    try:
        ts = float(ts_str)
    except ValueError:
        return None
    if time.time() - ts > PLATFORM_FLAG_TTL_SEC:
        return None
    return label or None


def write_platform_flag(label: str) -> None:
    try:
        with open(PLATFORM_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.time()}\t{label}")
    except Exception:
        pass


def clear_platform_flag() -> None:
    try:
        os.remove(PLATFORM_FLAG_FILE)
    except Exception:
        pass


def merged_pr_number(view: str) -> str | None:
    """PR number from `gh pr merge N` or the `tools/gh-merge.sh N` wrapper.

    None when the number is omitted (gh resolves the PR from the current
    branch); the caller degrades to an unnumbered label."""
    m = re.search(
        r"\b(?:gh\s+pr\s+merge|gh-merge\.sh)\s+(?:--?\S+\s+)*(\d+)\b", view
    )
    return m.group(1) if m else None


def pr_touches_platform(pr: str | None) -> bool | None:
    """True / False when the PR's file list is readable; None when it is not.

    None means undeterminable (no gh, offline, timeout, PR not resolvable from
    the current branch). Callers must treat None as 'assume it did' so the
    advisory still fires; precision is an improvement, never a new blind spot.

    Test seam: POST_ACTION_GATE_PR_FILES (newline-separated paths, or the
    literal 'ERROR' to force the undeterminable branch) bypasses the gh call.
    """
    seam = os.environ.get("POST_ACTION_GATE_PR_FILES")
    if seam is not None:
        if seam.strip() == "ERROR":
            return None
        paths = [ln.strip() for ln in seam.splitlines() if ln.strip()]
        return any(p.startswith(PLATFORM_PREFIXES) for p in paths) if paths else None
    argv = ["gh", "pr", "view"]
    if pr:
        argv.append(pr)
    argv += ["--json", "files", "-q", ".files[].path"]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=GH_TIMEOUT_SEC,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    paths = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not paths:
        return None
    return any(p.startswith(PLATFORM_PREFIXES) for p in paths)


def emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


def matches_any(cmd: str, patterns) -> bool:
    return any(re.search(p, cmd) for p in patterns)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0

    # Match on the normalized view (PowerShell call-operator / .cmd stems /
    # backslash paths); keep the ORIGINAL for fingerprints + logging.
    view = normalize_command(cmd)
    is_ship = matches_any(view, SHIP_PATTERNS)
    is_build = matches_any(view, BUILD_TEST_PATTERNS)

    advisories = []

    # The force-deploy is what makes a merged platform page live, so it is what
    # clears the marker. Checked before the ship arm; a force-deploy is not
    # itself ship-class, so the two can never fight over one command.
    if re.search(r"vercel-force-deploy", view):
        pending = read_platform_flag()
        clear_platform_flag()
        if pending:
            log_fire(f"PLATFORM-LIVE cleared pending={pending}")
            advisories.append(
                f"[PLATFORM DEPLOY] Force-deploy ran; the not-live marker for {pending} "
                "is cleared. Close the deploy verification gate before declaring "
                "anything live: fetch the no-slash URL and confirm the NEW build is "
                "served, not the prior one."
            )

    if is_ship:
        log_fire(f"SHIP cmd={cmd[:80]}")
        advisories.append(
            "[SHIP GATE] You just ran a ship-class command (push/commit/PR/deploy). "
            "If the build passed, continue the chain in this turn: commit -> push -> PR -> "
            "merge. Do NOT pause to ask 'should I merge?' / 'want me to push?' -- those are "
            "ship-gate violations. Only pause for force-push to main, prod data deletion, or "
            "no-undo actions. After deploy, run the deploy verification gate (WebFetch the URL, "
            "check 200 + key content)."
        )
        # Platform-merge-is-not-live (rule_behaviors sub-clause; register
        # 2026-07-14 jochen + 06-09 volabyg): the Vercel git integration lags,
        # so a merge is NOT a deploy. The advisory is scoped to merges that
        # actually touched platform/ paths, and it sets a marker that survives
        # until the force-deploy clears it.
        is_merge = bool(re.search(r"\bgh\s+pr\s+merge\b", view)) or "gh-merge" in view
        if is_merge:
            pr = merged_pr_number(view)
            touched = pr_touches_platform(pr)
            if touched is not False:
                label = f"PR #{pr}" if pr else "the merged PR"
                lead = (
                    f"{label} merged platform/ paths."
                    if touched
                    else f"{label} may have merged platform/ paths; the PR file list "
                         "could not be read, so this assumes it did."
                )
                write_platform_flag(label)
                log_fire(f"MERGE-NOT-LIVE {label} touched={touched}")
                advisories.append(
                    f"[MERGE-NOT-LIVE] {lead} The page "
                    "is NOT live yet. Vercel's git integration lags (23h-stale prod, "
                    "2026-06-09). Run tools/vercel-force-deploy.sh from a clean "
                    "origin/main worktree, then re-fetch the no-slash URL and confirm "
                    "the new build before declaring anything live. A 404/stale page "
                    "right after a merge means 'not force-deployed yet', not 'CDN "
                    "cache'."
                )
        else:
            # Any later ship-class command while a platform merge is still
            # un-deployed re-surfaces the marker, so 'not live' persists
            # instead of scrolling away with the merge turn.
            pending = read_platform_flag()
            if pending:
                advisories.append(
                    f"[PLATFORM NOT LIVE] {pending} merged platform/ paths and "
                    "tools/vercel-force-deploy.sh has not run since. Nothing on "
                    "unpauseai.com reflects that merge yet."
                )

    if is_build:
        if is_exempt(view):
            # A hook test or read-only verification: emit the B2 nudge but
            # do NOT advance the streak (would false-fire HARD LIMIT during
            # behavioral test sweeps). Reset to zero so a real loop after
            # exempt commands starts fresh.
            prev_n, _ = read_state()
            if prev_n != 0:
                write_state(0, "")
            log_fire(f"B2 EXEMPT cmd={cmd[:80]}")
            advisories.append(
                "[B2] Verification command (exempt from streak). Before declaring "
                "done: did you VERIFY behavior, not just config? Name the specific "
                "test performed. 'Compiles' != 'works'. See rule_behaviors.md B2 gate."
            )
        else:
            fp = fingerprint(cmd)
            prev_n, prev_fp = read_state()
            # Streak only advances when the fingerprint matches the prior
            # build/test command. Different command = fresh streak of 1.
            n = (prev_n + 1) if fp == prev_fp else 1
            write_state(n, fp)
            log_fire(f"B2 cmd={cmd[:80]} streak={n} fp={fp}")
            advisories.append(
                f"[B2] Build/test command executed (streak: {n}/3). Before declaring done: "
                "did you VERIFY behavior, not just config? Name the specific test performed "
                "(e.g., 'triggered webhook and got 200 with expected payload'). 'Compiles' != "
                "'works'. See rule_behaviors.md B2 gate."
            )
            if n >= 3:
                advisories.append(
                    "[HARD LIMIT] You have run the SAME build/test command 3 times in a row. "
                    "This is a fix-then-test loop. STOP fixing. Escalate per ITERATION-LOOP.md "
                    "Hard Gate: summarize what you tried, the current failure mode, and what "
                    "you'd try next. Do not run another fix-then-test until the user weighs in."
                )
    else:
        prev_n, _ = read_state()
        if prev_n != 0:
            write_state(0, "")

    if advisories:
        emit("\n\n".join(advisories))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
