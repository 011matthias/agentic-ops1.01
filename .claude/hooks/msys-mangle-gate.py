#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash) hook: advisory on MSYS-path-mangle-prone argument shapes.

WHY THIS EXISTS
---------------
The Bash tool runs Git Bash (MSYS), whose runtime rewrites arguments that
look POSIX-path-shaped before the program ever sees them. Two documented
failure shapes, three register rows (2026-07-22, and twice on 2026-08-24 --
"memory has now failed on this class three times in one day"):

  * A leading-slash server-relative argument (`/sites/MARKETING/...`)
    arrives as `C:/Program Files/Git/sites/MARKETING/...`. Burned a
    3-iteration cap on 2026-07-09 under a wrong SharePoint hypothesis
    (memory reference_repo_tooling_gotchas).
  * A `<ref>:<path>` pathspec (`git show HEAD:docs/x.md`) is treated as a
    path list and colon-converted, so git sees a mangled ref.

The documented fix (prefix `MSYS_NO_PATHCONV=1`, or use the PowerShell
tool) lived in memory and failed by recall. Per the rule_behaviors
self-annealing ladder (tool > structural gate > memory), the recurrence
earned a decision-time hook. The register rows themselves spec it: "a
PreToolUse Bash guard that flags MSYS-mangle-prone argument shapes
(<ref>:<path> pathspecs, /c/-style paths passed to native Windows
executables) and names MSYS_NO_PATHCONV=1."

ADVISORY, not deny: the mangle heuristics cannot be perfect, a false deny
would block legitimate work, and the remedy is a one-token prefix the agent
can apply in the same turn. The advisory is loud in-context BEFORE the
command runs, which is exactly where the memory kept failing.

DECISION MATRIX
---------------
- Not the Bash tool (PowerShell has no MSYS layer)      -> silent.
- Command already carries MSYS_NO_PATHCONV=1            -> silent.
- git pathspec `<ref>:<path/with/slash>` on a
  pathspec-taking subcommand (show/diff/log/cat-file/
  restore/checkout/grep)                                -> ADVISE.
- Bare argument `/first/second...` whose first segment
  is not a drive letter or a POSIX-internal dir
  (dev, tmp, usr, etc, bin, proc, mnt, home, opt, var,
  sys, run)                                             -> ADVISE.
- Everything else (URLs, /c/-drive forms, /dev/null
  redirects, sed scripts, flags)                        -> silent.

Fail-open per the project hook contract.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# git subcommands that accept <ref>:<path> / <tree-ish>:<path> arguments.
_GIT_PATHSPEC_CMD = re.compile(
    r"\bgit\b[^\n|;&]*?\b(?:show|diff|log|cat-file|restore|checkout|grep)\b",
)
# A token like HEAD:docs/x.md, abc1234:tools/foo.py, origin/main:docs/a.md.
# Requires a slash after the colon so times (12:30), drive letters (C:) and
# scp-style host:port shapes stay silent.
_COLON_PATHSPEC = re.compile(
    r"(?:^|\s)['\"]?([\w~^./-]+:[\w.~^-]*/[^\s'\"]*)"
)

# First path segment of a leading-slash argument that MSYS may legitimately
# resolve (drive letters, MSYS-internal dirs) -- these stay silent.
_SAFE_FIRST_SEGMENTS = {
    "dev", "tmp", "usr", "etc", "bin", "proc", "mnt", "home", "opt",
    "var", "sys", "run",
}
# Bare argument starting with a single slash and containing 2+ segments:
# `/sites/MARKETING/Shared Documents` (the quoted form is caught because we
# scan inside quotes too). Redirect targets are excluded by the (?<![<>])
# guard; doubled slashes (`//server/share`) are UNC-safe in MSYS and skipped.
_LEADING_SLASH_ARG = re.compile(
    r"(?:^|[\s='\"])(?<![<>])(/([A-Za-z][\w.-]*)/\S+)"
)


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} msys-mangle-gate {msg}\n")
    except Exception:
        pass


def mangle_prone(cmd: str) -> list[str]:
    """Return human-readable hits for MSYS-mangle-prone argument shapes."""
    hits: list[str] = []

    if _GIT_PATHSPEC_CMD.search(cmd):
        for m in _COLON_PATHSPEC.finditer(cmd):
            tok = m.group(1)
            # Skip URL-ish tokens (scheme://) and pure Windows drive paths.
            if "://" in tok or re.match(r"^[A-Za-z]:[/\\]", tok):
                continue
            hits.append(f"git pathspec `{tok}`")

    for m in _LEADING_SLASH_ARG.finditer(cmd):
        arg, first = m.group(1), m.group(2)
        if first.lower() in _SAFE_FIRST_SEGMENTS:
            continue
        if len(first) == 1:  # /c/..., /d/... drive form: conversion intended
            continue
        if arg.startswith("//"):
            continue
        hits.append(f"leading-slash arg `{arg}`")

    return hits


def advise(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    # MSYS conversion only exists under the Bash tool.
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd or "MSYS_NO_PATHCONV" in cmd:
        return 0

    hits = mangle_prone(cmd)
    if not hits:
        return 0

    shown = "; ".join(hits[:3])
    log(f"ADVISE {shown}")
    advise(
        f"[MSYS-MANGLE] This Bash command carries argument shapes the MSYS "
        f"layer rewrites before the program sees them: {shown}. Git Bash "
        f"converts leading-slash args to C:/Program Files/Git/... and "
        f"colon pathspecs to Windows path lists (register rows 2026-07-22 "
        f"and 2026-08-24 x2; memory reference_repo_tooling_gotchas). If any "
        f"flagged argument must reach the program literally, prefix the "
        f"command with MSYS_NO_PATHCONV=1 or run it via the PowerShell tool. "
        f"If the conversion is intended (a real POSIX-style path), proceed."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
