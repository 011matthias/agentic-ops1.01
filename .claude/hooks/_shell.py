#!/usr/bin/env python3
"""Shared command-normalization helper for the command-interception hooks.

WHY THIS EXISTS
---------------
The gates' regexes match the executable token as a bare word
(`\\bvercel\\s+deploy\\b`). On this Windows machine the PowerShell tool runs
the same actions in spellings the patterns never see. Two recorded live
bypasses (settings.local.json permission history, 2026-07-10 audit):

    & "$nodeDir\\vercel.cmd" deploy --prod --yes --cwd platform
    Set-Location platform

The first evades every ship pattern because after `vercel` comes `.cmd`,
not whitespace, and the call operator + quoted path hide the token.

CONTRACT
--------
`normalize_command(cmd)` returns a MATCHING VIEW ONLY. Consumers pass the
view to their pattern matchers and keep the ORIGINAL string for logging,
fingerprints, reasons, and offset math. Three ordered transforms:

  1. Strip PowerShell call / dot-source operators (`& `, `. `) -- only when
     followed by a quote, `$`, or a path-shaped token, so a bash background
     `&` (`foo & bar`) is never touched.
  2. Reduce program-path tokens ending in .cmd/.exe/.bat/.ps1 to their
     basename stem, dropping surrounding quotes:
     `"C:\\Program Files\\x\\vercel.cmd"` -> `vercel`;  `git.exe` -> `git`.
     `.sh` is deliberately NOT reduced (`vercel-force-deploy.sh` is itself
     a ship pattern).
  3. Backslash -> forward slash, so path-shaped patterns
     (`\\.claude/hooks/`, `tests?[\\\\/]`) hit Windows spellings.

cd-guard does NOT use this helper: its residue machinery is offset-sensitive
(length-preserving masking is load-bearing there); it carries a dedicated
PowerShell arm instead.

Idempotent, pure, stdlib-only. The `_` prefix keeps this file out of the
hook-registry disk scan (see tools/tests/test_hooks_registry.py), matching
the `_scope.py` precedent.
"""
from __future__ import annotations

import re

# `& "..."` / `. $prog` / `& C:\x\y.cmd` at start or after a statement-ish
# boundary. The lookahead is strict on purpose: quote, variable, a token
# containing a path separator, or a token ending in an executable extension.
_CALL_OP = re.compile(
    r"(?:^|(?<=[;&|(\n\t ]))"
    r"[&.][ \t]+"
    r"(?=[\"'$]|\S*[\\/]|\S+\.(?:cmd|exe|bat|ps1)\b)"
)

# Whole-token quoted program path: "C:\path with spaces\vercel.cmd" -> vercel
_EXE_QUOTED = re.compile(
    r"([\"'])(?:[^\"'\n]*[\\/])?([\w.+-]+)\.(?:cmd|exe|bat|ps1)\1",
    re.IGNORECASE,
)

# Bare program path token: $nodeDir\vercel.cmd -> vercel ; git.exe -> git
_EXE_BARE = re.compile(
    r"(?:[^\s\"';|&]*[\\/])?([\w.+-]+)\.(?:cmd|exe|bat|ps1)\b",
    re.IGNORECASE,
)


def normalize_command(cmd: str) -> str:
    """Return the matching view of `cmd` (see module docstring). Never raises."""
    try:
        view = _CALL_OP.sub("", cmd)
        view = _EXE_QUOTED.sub(r"\2", view)
        view = _EXE_BARE.sub(r"\1", view)
        return view.replace("\\", "/")
    except Exception:
        return cmd
