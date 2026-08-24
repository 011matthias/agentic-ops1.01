#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash|PowerShell) hook: permission-stop on git commands that
overwrite the WORKING TREE when the targeted paths carry uncommitted work.

WHY THIS EXISTS
---------------
2026-08-24 friction row (brisken): `git checkout -- <path>` was appended to a
regression-test command intending to restore a hand-made backup. The backup
had never been committed, so git did the only thing it can do -- reverted the
file to HEAD -- and destroyed both the prior session's uncommitted work and
that session's rewrite of intake_mail.py. Rebuilt from the transcript at the
cost of a full re-verify cycle. The register's recurrence-kill names this
hook: "a git checkout/restore guard hook on dirty tracked paths, mirroring
git-stash-gate.py".

The shape is the same as the stash gate's DESTROY arm. `git checkout -- x`,
`git restore x`, `git reset --hard` and `git clean -f` all silently discard
work that exists in no other place: uncommitted edits are not in the object
store, so there is no `git fsck` recovery the way there was for the
2026-06-12 stash tangle. The only recovery is a transcript rebuild.

DECISION MATRIX
---------------
- Command has no worktree-overwriting git form        -> silent allow.
- Targeted paths are provably CLEAN (git status
  reports nothing for them)                           -> silent allow. There
                                                         is nothing to lose,
                                                         and scripted resets
                                                         of a clean tree are
                                                         routine.
- Targeted paths are DIRTY, or the state cannot be
  determined                                          -> ASK, listing the
                                                         exact files at risk
                                                         and the archive-first
                                                         remedy.
- `git restore --staged` with no --worktree/--source   -> silent allow. That
                                                         form unstages; it
                                                         does not touch the
                                                         working tree.

Undeterminable state asks rather than allows, mirroring post-action-gate's
`pr_touches_platform` contract: precision is an improvement, never a new blind
spot. A genuine error (no git, subprocess blew up) still fails open per the
project hook contract -- a broken hook must never wedge the agent.

Ask rather than deny: a user-ordered discard stays one keystroke away, exactly
like git-stash-gate and instantly-invasive-gate.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import subprocess
import sys

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
GIT_TIMEOUT_SEC = 6  # hook budget is 10s; leave headroom.

# `git [global flags] <subcommand> ...`. The global-flag skip mirrors
# git-stash-gate: `git -C <path> checkout -- x` must not evade the match.
_GIT_PREFIX = r"""
    \bgit
    (?:\s+(?:
        -C\s+\S+ | -c\s+\S+ | --no-pager
        | --git-dir(?:=\S+|\s+\S+) | --work-tree(?:=\S+|\s+\S+)
    ))*
    \s+
"""
_VERBS = re.compile(
    _GIT_PREFIX + r"(?P<verb>checkout|restore|reset|clean|switch)\b(?P<rest>[^\n;&|]*)",
    re.VERBOSE | re.IGNORECASE,
)

# Quoted / heredoc / comment spans must not trigger: a commit message or an
# echo that mentions `git checkout --` is not a checkout. Same masking family
# as cd-guard and git-stash-gate.
_QUOTED = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'")
_HEREDOC = re.compile(r"<<-?\s*'?\w+'?.*?^\s*\w+\s*$", re.DOTALL | re.MULTILINE)
_COMMENT = re.compile(r"#[^\n]*")
_PS_HERESTRING = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.DOTALL)
_PS_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)


def masked(cmd: str) -> str:
    r = _PS_HERESTRING.sub(" ", cmd)
    r = _PS_BLOCK_COMMENT.sub(" ", r)
    r = _HEREDOC.sub(" ", r)
    r = _QUOTED.sub(" ", r)
    r = _COMMENT.sub(" ", r)
    return r


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} git-restore-gate {msg}\n")
    except Exception:
        pass


def _tokens(rest: str) -> list[str]:
    """Best-effort argument split. Masking already removed quoted spans, so a
    shlex failure means an odd fragment; fall back to whitespace."""
    try:
        return shlex.split(rest)
    except ValueError:
        return rest.split()


def _paths_after_ddash(toks: list[str]) -> list[str] | None:
    """Everything after a literal `--`, or None when there is no `--`."""
    if "--" not in toks:
        return None
    return [t for t in toks[toks.index("--") + 1:] if t]


# Flags that make `git checkout` a BRANCH operation, so its positional
# argument is a ref rather than a pathspec.
_BRANCH_FLAGS = {"-b", "-B", "-t", "--track", "--no-track", "--orphan", "--detach"}


def classify(view: str, cwd: str = ".") -> tuple[str, list[str], str] | None:
    """(kind, paths, spelling) for the first worktree-overwriting git form.

    `paths` is the pathspec to probe; an EMPTY list means "the whole tree".
    Returns None when nothing in `view` overwrites the working tree.

    `cwd` disambiguates the separator-less `git checkout <arg>` form: branch
    names in this repo routinely contain slashes (`client/brisken/...`), so a
    slash cannot distinguish a ref from a path. Existence on disk can.
    """
    for m in _VERBS.finditer(view):
        verb = m.group("verb").lower()
        rest = m.group("rest") or ""
        toks = _tokens(rest)
        flags = {t for t in toks if t.startswith("-")}
        spelling = f"git {verb}{(' ' + rest.strip()) if rest.strip() else ''}".strip()

        if verb == "reset":
            if "--hard" in flags:
                # `git reset --hard [ref] [-- paths]`: discards every
                # uncommitted change under the pathspec (whole tree if none).
                return ("reset-hard", _paths_after_ddash(toks) or [], spelling)
            continue

        if verb == "clean":
            # -f / --force is required for clean to delete anything, so an
            # unforced clean (or a -n dry run) is harmless.
            if any(f == "--force" or (f.startswith("-") and not f.startswith("--") and "f" in f)
                   for f in flags):
                if "-n" in flags or "--dry-run" in flags:
                    continue
                paths = [t for t in toks if not t.startswith("-")]
                return ("clean", paths, spelling)
            continue

        if verb == "switch":
            # Only the discard forms overwrite the tree.
            if "-f" in flags or "--force" in flags or "--discard-changes" in flags:
                return ("switch-force", [], spelling)
            continue

        if verb == "restore":
            staged = "--staged" in flags or "-S" in flags
            worktree = "--worktree" in flags or "-W" in flags
            # `--staged` ALONE only rewrites the index -- the working tree is
            # untouched, so there is nothing to lose.
            if staged and not worktree:
                continue
            explicit = _paths_after_ddash(toks)
            paths = explicit if explicit is not None else [
                t for t in toks if not t.startswith("-")
            ]
            return ("restore", paths, spelling)

        # verb == "checkout"
        explicit = _paths_after_ddash(toks)
        if explicit is not None:
            # `git checkout [ref] -- <paths>`: unambiguously a file restore.
            return ("checkout-paths", explicit, spelling)
        forced = "-f" in flags or "--force" in flags
        if flags & _BRANCH_FLAGS:
            # `git checkout -b <new>` and friends create/switch a branch; the
            # positional is a ref. Only the force spelling can discard work.
            if forced:
                return ("checkout-force", [], spelling)
            continue
        positional = [t for t in toks if not t.startswith("-")]
        if positional == ["."]:
            return ("checkout-paths", ["."], spelling)
        if positional and all(
            os.path.exists(os.path.join(cwd, p.replace("\\", os.sep)))
            for p in positional
        ):
            # `git checkout src/foo.py` -- a pathspec checkout without the
            # `--` separator. Existence on disk is what separates it from
            # `git checkout client/brisken/deckgen-native`, which is a branch.
            return ("checkout-paths", positional, spelling)
        if forced:
            return ("checkout-force", [], spelling)
        continue
    return None


def dirty_paths(paths: list[str], kind: str, cwd: str) -> list[str] | None:
    """Porcelain entries for `paths` (whole tree when empty), or None when the
    state could not be determined.

    Test seam: GIT_RESTORE_GATE_STATUS supplies porcelain lines directly (the
    literal 'ERROR' forces the undeterminable branch), so the decision matrix
    is testable without building throwaway repositories.
    """
    seam = os.environ.get("GIT_RESTORE_GATE_STATUS")
    if seam is not None:
        if seam.strip() == "ERROR":
            return None
        return _risk_set(
            [ln.rstrip() for ln in seam.splitlines() if ln.strip()], kind
        )

    argv = ["git", "status", "--porcelain"]
    if kind != "clean":
        # `git clean` only ever removes UNTRACKED files, so its risk set is
        # exactly the untracked entries; every other form can also clobber
        # tracked modifications.
        argv.append("--untracked-files=normal")
    if paths:
        argv.append("--")
        argv.extend(paths)
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=GIT_TIMEOUT_SEC, cwd=cwd
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return _risk_set(
        [ln.rstrip() for ln in proc.stdout.splitlines() if ln.strip()], kind
    )


def _risk_set(entries: list[str], kind: str) -> list[str]:
    """Narrow porcelain entries to what THIS command can actually destroy.

    `git clean` only ever removes untracked files, so a tracked modification
    is not in its risk set -- prompting on one would tax the routine
    "clean the build junk" call and teach the gate to be ignored.
    """
    if kind == "clean":
        return [e for e in entries if e.startswith("??")]
    return entries


REMEDY = (
    "Archive first, then discard: `git diff -- <path> > "
    ".scratch/pre-restore-<name>-<date>.patch` for tracked edits, or copy the "
    "file aside for untracked ones. If you meant to restore a backup YOU made, "
    "use `cp`/`mv` from that backup -- git restores from HEAD/the index, never "
    "from your backup file, which is exactly how the 2026-08-24 incident "
    "destroyed intake_mail.py. If the work is worth keeping at all, commit it "
    "on a branch first (uncommitted work is in no object store, so there is no "
    "`git fsck` recovery)."
)

REASONS = {
    "checkout-paths": (
        "GIT CHECKOUT of a DIRTY path intercepted: `{spelling}`. This "
        "overwrites the working-tree copy from HEAD/the index and discards "
        "{n} uncommitted change(s) permanently:\n{listing}\n\n" + REMEDY
    ),
    "restore": (
        "GIT RESTORE of a DIRTY path intercepted: `{spelling}`. This "
        "overwrites the working-tree copy and discards {n} uncommitted "
        "change(s) permanently:\n{listing}\n\n" + REMEDY
    ),
    "reset-hard": (
        "GIT RESET --HARD intercepted: `{spelling}`. This discards {n} "
        "uncommitted change(s) across the pathspec permanently:\n{listing}"
        "\n\n" + REMEDY
    ),
    "clean": (
        "GIT CLEAN (forced) intercepted: `{spelling}`. This DELETES {n} "
        "untracked file(s), which by definition exist nowhere else:\n{listing}"
        "\n\n" + REMEDY
    ),
    "checkout-force": (
        "GIT CHECKOUT --FORCE intercepted: `{spelling}`. The force flag "
        "discards {n} uncommitted change(s) instead of refusing the "
        "switch:\n{listing}\n\n" + REMEDY
    ),
    "switch-force": (
        "GIT SWITCH (force/discard) intercepted: `{spelling}`. This discards "
        "{n} uncommitted change(s) instead of refusing the switch:\n{listing}"
        "\n\n" + REMEDY
    ),
}

UNKNOWN_SUFFIX = (
    "\n\nThe working-tree state could NOT be read (no git, a timeout, or a "
    "pathspec git rejected), so this assumes there is work at risk rather "
    "than assuming there is not."
)


def ask(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd or "git" not in cmd:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    view = masked(normalize_command(cmd))
    hit = classify(view, cwd)
    if hit is None:
        return 0
    kind, paths, spelling = hit

    entries = dirty_paths(paths, kind, cwd)

    if entries is not None and not entries:
        # Provably clean: nothing to lose, stay out of the way.
        log(f"ALLOW:clean kind={kind} paths={paths}")
        return 0

    if entries is None:
        listing, n, suffix = "  (unreadable)", "an unknown number of", UNKNOWN_SUFFIX
    else:
        shown = entries[:12]
        listing = "\n".join(f"  {e}" for e in shown)
        if len(entries) > len(shown):
            listing += f"\n  ... and {len(entries) - len(shown)} more"
        n, suffix = str(len(entries)), ""

    reason = REASONS[kind].format(spelling=spelling[:160], n=n, listing=listing) + suffix

    log(f"ASK kind={kind} paths={paths} dirty={n}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-git-restore",
                "git-restore-gate",
                f"{kind}: {spelling[:80]} ({n} at risk)",
            )
        except Exception:
            pass
    ask(reason)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
