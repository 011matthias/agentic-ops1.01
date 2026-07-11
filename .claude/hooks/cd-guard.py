#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash|PowerShell) hook: detect and block `cd <subdir> && ...`
patterns that leak the cwd change to subsequent shell calls and to hooks.

WHY THIS EXISTS
---------------
Friction register has 4 entries for the same class:
  2026-05-18 #20 (local-web)  -- vercel link in wrong dir
  2026-05-20 #9  (platform)   -- subsequent hooks failed
  2026-05-25 #109 (brisken)   -- PreToolUse hooks couldn't find .claude/hooks
  2026-05-19 #100 (system)    -- same-day regression of #82

The Bash tool keeps shell cwd across calls. Once `cd path && cmd` runs, the
next call (and every PostToolUse / PreToolUse hook that resolves relative
`.claude/hooks/X.py`) starts in `path/`, not repo root. The fix recommended
in 2+ checkpoints: rewrite `cd X && Y` into `( cd X && Y )` (subshell --
cwd change is local) or replace it with absolute/cwd-flag equivalents
(`git -C`, `npm --prefix`, `--cwd`, `uv run --directory`).

DECISION
--------
BLOCK with a clear, scriptable correction message. The hook does NOT silently
rewrite the command: the agent must learn the pattern, not have it papered
over. The block reason names the three idiomatic fixes so the agent can
choose the right one without re-deriving.

EXEMPTIONS
----------
- `cd -` (return to previous dir) is harmless.
- `cd && cmd` with no path (no-op) is harmless.
- A bare `cd path` with nothing after is sometimes intentional (rare; we
  still block it because it leaks state to the next call).
- `( cd path && cmd )` -- already a subshell, allow.
- `pushd / popd` -- allow (explicit caller manages the stack).
- Commands inside heredocs / quoted strings / comments -- allow (not a real
  cd invocation; matches gate-skip-detector's publish_residue logic).

POWERSHELL ARM (2026-07-10)
---------------------------
The PowerShell tool persists cwd across calls exactly like Bash, but the
original hook only matched tool_name == "Bash" and the literal `cd ` token.
`Set-Location platform` ran unguarded (recorded live bypass, settings
allowlist history). The PS arm detects `Set-Location | chdir | sl | cd`
(+ `-Path`/`-LiteralPath`), masks PS here-strings (`@'...'@` / @"..."@)
and `<#...#>` block comments before scanning, and exempts `Push-Location`
(pushd parity: reversible via Pop-Location, and it IS the recommended
remediation). PS parentheses do NOT scope a location change, so the
subshell exemption stays Bash-only. Accepted gaps, documented: the
no-space cmd-isms `cd..` / `cd\\`, and backtick line continuation.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# Match `cd <path>` at start, or after `&&`, `||`, `;`, `|`, newline.
# Capture the path for the correction message.
# Exclude `cd -` (return to prev dir), `cd ~` alone, `cd $HOME`, and any cd
# that's already inside a `( ... )` subshell on the same line.
CD_RX = re.compile(
    r"""
    (?:^|[;&|]|\n|\&\&|\|\|)        # statement boundary
    \s*
    cd\s+                            # cd literal + space
    (?!-\s)                          # NOT `cd -`
    (?!~\s*$)                        # NOT `cd ~` alone
    (?!\$HOME\s*$)                   # NOT `cd $HOME` alone
    (?P<path>[^\s;&|]+)              # the path argument
    (?:\s+\&\&|\s*\n|\s+;|\s*$)      # followed by && or stmt boundary (chained)
    """,
    re.VERBOSE,
)

# Strip quoted/heredoc spans so a cd inside a heredoc body or quoted PR/git
# message doesn't trigger. Mirrors gate-skip-detector's residue trick.
_QUOTED = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'")
_HEREDOC = re.compile(r"<<-?\s*'?\w+'?.*?^\s*\w+\s*$", re.DOTALL | re.MULTILINE)
# Comment lines (treat `# ...` to end-of-line as comment; ok for bash too).
_COMMENT = re.compile(r"#[^\n]*")

# --- PowerShell arm ---------------------------------------------------------
# Location-changing verbs. `Push-Location` is deliberately absent (pushd
# parity; it is the remediation the block message recommends). The trailing
# boundary is a LOOKAHEAD, not a consuming group: `Set-Location platform;`
# has no space before `;` (the recorded live-bypass shape).
PS_CD_RX = re.compile(
    r"""
    (?:^|[;&|]|\n)                       # statement boundary
    \s*
    (?:set-location|chdir|sl|cd)\b       # location-changing verb
    (?:\s+-(?:literalpath|path))?        # optional -Path / -LiteralPath
    \s+
    (?!-(?:[\s;&|]|$))                   # NOT `cd -`
    (?P<path>[^\s;&|]+)                  # the path argument
    (?=[\s;&|]|$)                        # statement boundary (non-consuming)
    """,
    re.VERBOSE | re.IGNORECASE,
)
# PS here-strings: @' ... '@ / @" ... "@ (closing delimiter at line start).
_PS_HERESTRING = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.DOTALL)
# PS block comments: <# ... #>
_PS_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} cd-guard {msg}\n")
    except Exception:
        pass


def _mask_len(m: "re.Match") -> str:
    return "X" * len(m.group(0))


def _space_len(m: "re.Match") -> str:
    return " " * len(m.group(0))


def residue(cmd: str) -> str:
    """Length-preserving residue for cd-detection.

    Heredoc and comment spans become spaces; QUOTED spans become 'X' filler
    (masked, NOT deleted). Length-preserving and masking are both load-bearing:
      1. Offsets map 1:1 back to `cmd`, so `already_subshelled` and the block
         reason index the original text correctly.
      2. A quoted path token still EXISTS after masking. The old code deleted
         quoted spans, turning `cd "$WT" && ...` into `cd   && ...` (no path
         token left to match), so EVERY quoted-path cd slipped through -- the
         exact mechanism of register #16 (`cd "$WT"` on its own line bricked
         the whole hook layer). Masking keeps the token so CD_RX still fires,
         while `echo "cd foo && bar"` stays exempt (the `cd` is inside the
         masked span, so no `cd ` boundary survives in the residue)."""
    r = _HEREDOC.sub(_space_len, cmd)
    r = _QUOTED.sub(_mask_len, r)
    r = _COMMENT.sub(_space_len, r)
    return r


def ps_residue(cmd: str) -> str:
    """Length-preserving residue for the PowerShell arm. Here-string bodies
    and block comments become spaces FIRST (they may span lines and contain
    quotes), then the shared quote-mask / line-comment passes apply."""
    r = _PS_HERESTRING.sub(_space_len, cmd)
    r = _PS_BLOCK_COMMENT.sub(_space_len, r)
    r = _QUOTED.sub(_mask_len, r)
    r = _COMMENT.sub(_space_len, r)
    return r


def already_subshelled(cmd: str, match_start: int) -> bool:
    """True if the cd at `match_start` is already inside `(...)` on the
    same logical statement."""
    # walk backwards to find unmatched `(` before the next `)`
    depth = 0
    i = match_start - 1
    while i >= 0:
        c = cmd[i]
        if c == ")":
            depth += 1
        elif c == "(":
            if depth == 0:
                return True
            depth -= 1
        elif c == "\n":
            return False
        i -= 1
    return False


REASON_TEMPLATE = (
    "[cd-guard] Refused: `cd {path} && ...` persists the shell cwd across "
    "subsequent Bash calls AND across PreToolUse / PostToolUse hooks that "
    "resolve relative `.claude/hooks/*.py` paths. This pattern has caused "
    "4 documented friction events (register entries 2026-05-18 #20, "
    "2026-05-20 #9, 2026-05-25 #109, 2026-05-19 #100). Pick ONE fix:\n"
    "  (1) Subshell:    ( cd {path} && <command> )\n"
    "  (2) Tool flag:   git -C {path} <cmd>  |  npm --prefix {path} <cmd>  "
    "|  uv run --directory {path} <cmd>  |  vercel --cwd {path} <cmd>\n"
    "  (3) Absolute paths: invoke with the full path, no cd needed.\n"
    "Then resubmit the corrected command."
)

PS_REASON_TEMPLATE = (
    "[cd-guard] Refused: changing the location to `{path}` persists the "
    "PowerShell cwd across subsequent PowerShell calls AND across hooks that "
    "resolve relative `.claude/hooks/*.py` paths (same drift class as the "
    "4 documented Bash incidents). Pick ONE fix:\n"
    "  (1) Scoped stack:  Push-Location {path}; <command>; Pop-Location\n"
    "  (2) Tool flag:     git -C {path} <cmd>  |  npm --prefix {path} <cmd>  "
    "|  uv run --directory {path} <cmd>  |  vercel --cwd {path} <cmd>\n"
    "  (3) Absolute paths: invoke with the full path, no location change.\n"
    "Then resubmit the corrected command."
)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool = event.get("tool_name")
    if tool not in ("Bash", "PowerShell"):
        return 0

    cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0

    if tool == "Bash":
        if "cd " not in cmd:
            return 0
        scan = residue(cmd)
        rx, reason_tpl, subshell_exempt = CD_RX, REASON_TEMPLATE, True
    else:
        scan = ps_residue(cmd)
        rx, reason_tpl, subshell_exempt = PS_CD_RX, PS_REASON_TEMPLATE, False

    # residue is length-preserving, so match offsets index straight into `cmd`.
    for m in rx.finditer(scan):
        # Use the ORIGINAL text for the exemption test + reason -- the matched
        # `path` group may be the masked 'X' filler of a quoted span.
        path = cmd[m.start("path"):m.end("path")]
        bare = path.strip("\"'")
        # Home / previous-dir navigation is a stable absolute target, not
        # relative drift -- exempt it (covers quoted forms like `cd "$HOME"`,
        # `cd ~/Repo`, and the PowerShell `$env:USERPROFILE` spellings). This
        # is the authoritative exemption; the inline regex lookaheads only
        # cover the bare unquoted forms.
        bl = bare.lower()
        if bl in ("~", "-", "$home", "$env:userprofile") or bl.startswith(
            ("~/", "~\\", "$home/", "$home\\",
             "$env:userprofile/", "$env:userprofile\\")
        ):
            continue
        # PS parentheses do NOT scope Set-Location -- subshell exemption is
        # a Bash-only semantic.
        if subshell_exempt and already_subshelled(scan, m.start()):
            continue
        # A bare `cd <path>` (whole command, nothing chained after) is blocked
        # too: it persists the cwd into the NEXT shell call and every hook
        # resolved against it, which is the same drift. The safe escapes
        # (`cd -`, `cd ~`, `cd $HOME`, absolute paths, `( cd .. && .. )`
        # subshells, `Push-Location`) are all exempted above or by the regex.
        log_fire(f"BLOCK tool={tool} path={path[:40]} cmd={cmd[:80]!r}")
        decision = {"decision": "block", "reason": reason_tpl.format(path=path)}
        # Claude Code reads JSON decisions from stdout for newer hook APIs
        # and from stderr for older; emit on both to be safe.
        print(json.dumps(decision), file=sys.stderr)
        print(json.dumps(decision))
        return 2  # non-zero -> Claude Code treats as block

    log_fire("ALLOW")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail-open per project hook contract (rule_behaviors.md).
        sys.exit(0)
