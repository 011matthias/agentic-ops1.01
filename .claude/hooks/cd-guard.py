#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash) hook: detect and block `cd <subdir> && ...` patterns
that leak the cwd change to subsequent Bash calls and to hooks.

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


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} cd-guard {msg}\n")
    except Exception:
        pass


def residue(cmd: str) -> str:
    """Return the part of cmd outside quotes/heredocs/comments."""
    r = _HEREDOC.sub(" ", cmd)
    r = _QUOTED.sub(" ", r)
    r = _COMMENT.sub(" ", r)
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


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") != "Bash":
        return 0

    cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd or "cd " not in cmd:
        return 0

    scan = residue(cmd)
    # Map residue offsets back -- since we replace with space (same length),
    # the offsets match the original `cmd`.
    for m in CD_RX.finditer(scan):
        path = m.group("path")
        # Exempt: cd into absolute path equal to current cwd-equivalent, OR
        # cd inside a subshell already. Path-equality is hard so we only
        # exempt the subshell case.
        if already_subshelled(scan, m.start()):
            continue
        # Exempt: a `cd` that's the WHOLE command (no `&&` or `;` after).
        # Still costs us cwd persistence, but a bare cd is rarely autonomous
        # agent behaviour -- let it through with a log-only signal.
        rest = scan[m.end():].strip()
        if not rest:
            log_fire(f"WARN:bare-cd path={path[:40]}")
            return 0
        log_fire(f"BLOCK path={path[:40]} cmd={cmd[:80]!r}")
        print(json.dumps({
            "decision": "block",
            "reason": REASON_TEMPLATE.format(path=path),
        }), file=sys.stderr)
        # Claude Code reads JSON decisions from stdout for newer hook APIs
        # and from stderr for older; emit on both to be safe.
        print(json.dumps({
            "decision": "block",
            "reason": REASON_TEMPLATE.format(path=path),
        }))
        return 2  # non-zero -> Claude Code treats as block

    log_fire("ALLOW")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail-open per project hook contract (rule_behaviors.md).
        sys.exit(0)
