# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the Brisken recon notifier from a checkout that updates itself.

WHY THIS EXISTS
---------------
`tools/brisken-recon-notify.py` is the only thing that turns the app's
state into an alarm anybody sees. It ran from the developer's shared
working tree, which nothing updates automatically, so the code it executed
was whatever that tree happened to hold.

That is not theoretical. Item 113 (PR #1026) added re-match FAILURE alerts
to the notifier and landed on `main` at 2026-09-17 17:10. The shared tree's
last pull before that was 2026-09-17 12:47 and its next was 2026-09-21
10:19, so for about 89 hours the scheduled task ran a notifier with no
`diff_rematch_failures` in it: a whole alarm class shipped, green in CI,
and silently absent from the only path that mails anybody. Nothing noticed,
because nothing looks. The clone-wide "283 commits behind" figure in
`docs/operating.md` overstates and understates this at once; the notifier
file itself has changed only five times, and the number that matters is
whether one of those five landed since the last pull.

WHY NOT JUST PULL THE SHARED TREE
---------------------------------
Several sessions work in it at once. A `git pull` on a schedule would move
HEAD under an in-flight edit, which is how you corrupt somebody else's
work, and the tree is routinely dirty. So the notifier gets its own clone
instead.

WHAT THIS CANNOT DISTURB
------------------------
This script runs no git command against the shared tree. It updates only
the repository it lives in (`Path(__file__).parent.parent`), which is the
dedicated clone; that clone has its own `.git`, so it shares no HEAD, no
index, no stash, no refs and no objects with anything.

It does read two files from the shared tree, and both are gitignored, so
touching them cannot dirty a tree or collide with a commit:

  * the Graph credentials (`workspace/clients/brisken/context/.env`), read
    only, so the secret keeps exactly one copy on this machine;
  * the notifier's own state file, which is read and written, and which
    must be the SAME file the old arrangement used. A fresh state means
    every existing run, intake, feedback note and re-match reads as new and
    is announced at once, so a migration that "worked" would arrive as a
    mail storm. Preferring an existing state file over a new one is what
    prevents that, and it is why the state is resolved by looking for one
    rather than by deriving a path.

THE UPDATE IS FAST-FORWARD ONLY, AND NEVER FATAL
------------------------------------------------
`fetch` + `merge --ff-only`. On a clone nobody edits this always succeeds;
if it ever does not, something is in that clone that should not be, and
overwriting it would destroy the evidence. A failed update is logged and
the run proceeds on the last good commit, because a notifier that refuses
to alarm until its git is healthy has turned a maintenance problem into an
outage.

Missing credentials ARE fatal, deliberately: a notifier that cannot send
must not exit 0. `LastTaskResult` is the only signal the scheduler shows,
and the failure being fixed here is alarms going quiet without anybody
knowing.

This is the small fix. Backlog item 121 (move the notifier into the app, so
it does not depend on one laptop at all) is the real one.

USAGE
-----
    uv run tools/brisken-recon-notify-run.py --once
    uv run tools/brisken-recon-notify-run.py --once --dry-run
    uv run tools/brisken-recon-notify-run.py --once --no-update

Everything after this script's own flags is passed to the notifier.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CLONE = Path(__file__).resolve().parent.parent
NOTIFIER = "tools/brisken-recon-notify.py"
ENV_REL = Path("workspace") / "clients" / "brisken" / "context" / ".env"
STATE_REL = Path(".scratch") / "recon-notify-state.json"
LOG_REL = Path(".scratch") / "recon-notify-runs.log"
LOG_KEEP = 500


def _homes() -> list[Path]:
    """Where the gitignored credentials and state might live, best first.

    The clone itself comes first so a self-contained setup (somebody copies
    the `.env` in) needs no configuration; the shared working tree is the
    fallback, and is where both actually live today.
    """
    homes: list[Path] = []
    override = os.environ.get("RECON_NOTIFY_HOME", "").strip()
    if override:
        homes.append(Path(override))
    homes.append(CLONE)
    homes.append(CLONE.parent / "agentic-ops1")
    seen: set[Path] = set()
    unique = []
    for home in homes:
        resolved = home.resolve() if home.exists() else home
        if resolved not in seen:
            seen.add(resolved)
            unique.append(home)
    return unique


def resolve_env_file() -> Path | None:
    """The Graph credentials. One copy on this machine, read where it is."""
    override = os.environ.get("RECON_NOTIFY_ENV_FILE", "").strip()
    if override:
        candidate = Path(override)
        return candidate if candidate.is_file() else None
    for home in _homes():
        candidate = home / ENV_REL
        if candidate.is_file():
            return candidate
    return None


def resolve_state_file() -> Path:
    """The notifier's memory of what it has already announced.

    An EXISTING file always wins over a new path. A state file that does
    not exist is not a clean slate, it is an instruction to announce the
    entire history at once, so "no state here, make one" is the wrong
    answer whenever a real one is reachable.
    """
    override = os.environ.get("RECON_NOTIFY_STATE", "").strip()
    if override:
        return Path(override)
    for home in _homes():
        candidate = home / STATE_REL
        if candidate.is_file():
            return candidate
    return CLONE / STATE_REL


def _git(*args: str, cwd: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out


def current_commit(clone: Path) -> str:
    ok, out = _git("rev-parse", "HEAD", cwd=clone)
    return out.split()[0] if ok and out else ""


def update_clone(clone: Path) -> tuple[bool, str]:
    """Fast-forward the clone to `origin/main`. Never destructive.

    Returns (updated_cleanly, detail). A false here is logged and ignored
    by the caller: running slightly stale beats not running.
    """
    ok, out = _git("fetch", "--quiet", "origin", "main", cwd=clone)
    if not ok:
        return False, f"fetch failed: {out[:300]}"
    ok, out = _git("merge", "--ff-only", "origin/main", cwd=clone)
    if not ok:
        return False, f"ff-only merge failed: {out[:300]}"
    return True, out.splitlines()[0] if out else "up to date"


def append_log(path: Path, line: str) -> None:
    """A trail, so "did it run, and from which commit" is answerable later.

    Bounded, because an unbounded log on a machine nobody watches is its
    own small fault. A log that cannot be written never fails the run.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            path.read_text(encoding="utf-8").splitlines()
            if path.is_file() else []
        )
        existing.append(line)
        path.write_text(
            "\n".join(existing[-LOG_KEEP:]) + "\n", encoding="utf-8"
        )
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the notifier's own checkout, then run it.",
    )
    parser.add_argument(
        "--no-update", action="store_true",
        help="run without fetching (for a hand test on a pinned commit)",
    )
    parser.add_argument(
        "--print-plan", action="store_true",
        help="resolve paths and print what would run; run nothing",
    )
    args, passthrough = parser.parse_known_args(argv)

    env_file = resolve_env_file()
    state_file = resolve_state_file()
    log_file = (
        state_file.parent / LOG_REL.name
        if state_file.parent.name == ".scratch"
        else CLONE / LOG_REL
    )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    update_note = "skipped"
    if not args.no_update:
        ok, detail = update_clone(CLONE)
        update_note = detail if ok else f"STALE ({detail})"
    commit = current_commit(CLONE)

    if args.print_plan:
        print(f"clone      {CLONE}")
        print(f"commit     {commit or '(unknown)'}")
        print(f"update     {update_note}")
        print(f"env-file   {env_file or '(NOT FOUND)'}")
        print(f"state      {state_file}"
              f"{'' if state_file.is_file() else '  (would be created)'}")
        print(f"log        {log_file}")
        return 0 if env_file else 2

    if env_file is None:
        # Fatal on purpose. A notifier that cannot authenticate sends
        # nothing, and exiting 0 would make that look like a quiet day.
        msg = (
            "no Graph credentials found: looked for "
            + ", ".join(str(h / ENV_REL) for h in _homes())
        )
        append_log(log_file, f"{stamp} commit={commit[:8]} FAILED {msg}")
        print(f"brisken-recon-notify-run: {msg}", file=sys.stderr)
        return 2

    cmd = [
        "uv", "run", "--directory", str(CLONE), NOTIFIER,
        "--env-file", str(env_file),
        "--state", str(state_file),
        *passthrough,
    ]
    try:
        proc = subprocess.run(cmd, timeout=900)
        code = proc.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        append_log(
            log_file,
            f"{stamp} commit={commit[:8]} FAILED {type(exc).__name__}: {exc}",
        )
        print(f"brisken-recon-notify-run: {exc}", file=sys.stderr)
        return 3

    append_log(
        log_file,
        f"{stamp} commit={commit[:8]} update={update_note} exit={code}",
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
