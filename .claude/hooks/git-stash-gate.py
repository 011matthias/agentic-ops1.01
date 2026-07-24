#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash|PowerShell) hook: permission-stop on `git stash` used as
isolation, per rule_branch_isolation_and_shared_ledger.md (G1) SS3.

WHY THIS EXISTS
---------------
The stash store is SHARED state across every checkout and worktree of one
clone: a stash pushed by one project's session can be popped onto another
project's branch. That exact mechanism produced the 2026-06-12 tangle
(finance session stashed p2 lead-gen WIP, it landed on the lead-gen branch,
recovered via `git fsck`), and the rule-layer ban alone did not hold: a
build subagent stashed again on 2026-07-22 (round-2 health pass,
branch-hygiene friction). Layer-1 recurrence-kill per rule_behaviors
self-annealing: a hook fires at decision time; a rule depends on recall.

DECISION MATRIX
---------------
- CREATE (`git stash`, `stash push`, `stash save`, bare-with-flags `-u` etc.,
  plumbing `create`/`store`, unknown subcommand) -> permissionDecision ASK.
  The sanctioned isolation moves are named in the reason: commit the WIP on
  a dedicated branch, or use a worktree. A committed branch cannot be popped
  onto the wrong place.
- DESTROY (`stash drop`, `stash clear`) -> ASK. Destroys WIP that may never
  have been reviewed; the round-1 heal pattern (archive to
  `.scratch/stash-archive-*.patch`, then drop) is named in the reason.
- READ + DRAIN (`stash list`, `show`, `pop`, `apply`, `branch`) -> allow
  silently. Draining an existing stash moves WIP OUT of the shared store,
  which is the direction the rule wants; `stash branch` IS the remediation.

Not a hard block: a user-ordered stash stays possible via the permission
prompt (mirrors instantly-invasive / no-auto-commit ask semantics).

Fail-open per the project hook contract.
"""
from __future__ import annotations

import datetime
import json
import os
import re
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

# `git [global flags] stash [subcommand]`. Global-flag skip covers the
# spellings that put tokens between `git` and `stash` (`git -C path stash`
# was a documented miss risk at design time).
STASH_RX = re.compile(
    r"""
    \bgit
    (?:\s+(?:
        -C\s+\S+ | -c\s+\S+ | --no-pager
        | --git-dir(?:=\S+|\s+\S+) | --work-tree(?:=\S+|\s+\S+)
    ))*
    \s+stash\b
    (?:\s+(?P<sub>[A-Za-z-]+))?
    """,
    re.VERBOSE | re.IGNORECASE,
)

ALLOW_SUBS = {"list", "show", "pop", "apply", "branch"}
DESTROY_SUBS = {"drop", "clear"}

# Quoted / heredoc / comment spans must not trigger (a commit message or an
# echo mentioning `git stash` is not a stash). Same masking family as
# cd-guard; offsets are not reused here so plain masking suffices.
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
            f.write(f"{datetime.datetime.now().isoformat()} git-stash-gate {msg}\n")
    except Exception:
        pass


def classify(view: str) -> tuple[str, str] | None:
    """(kind, sub) for the first ask-class stash command in `view`, or None."""
    for m in STASH_RX.finditer(view):
        sub = (m.group("sub") or "").lower()
        if sub in ALLOW_SUBS:
            continue
        # A leading dash means the "subcommand" is a flag on a bare stash
        # (`git stash -u`) -> create.
        if sub in DESTROY_SUBS:
            return ("destroy", sub)
        return ("create", sub or "(bare)")
    return None


CREATE_REASON = (
    "GIT STASH (create) intercepted: `git stash {sub}`. Per "
    "rule_branch_isolation_and_shared_ledger.md (G1) SS3, stash is BANNED for "
    "isolating WIP: the stash store is shared across every checkout and "
    "worktree of this clone, so a stash pushed here can be popped onto "
    "another project's branch (2026-06-12 fsck recovery; recurred 2026-07-22 "
    "despite the rule). Use instead: (1) commit the WIP on a dedicated "
    "branch (`git switch -c wip/<name>` + commit -- a committed branch "
    "cannot be popped onto the wrong place), (2) a `git worktree add` for "
    "concurrent work, (3) for ledger WIP, a `docs/...` branch. If the user "
    "explicitly ordered a stash, approve this prompt; otherwise cancel and "
    "use a branch."
)

DESTROY_REASON = (
    "GIT STASH ({sub}) intercepted: this destroys stashed WIP that may never "
    "have been reviewed. House pattern (2026-07-22 round-1 heal): archive "
    "first -- `git stash show -p stash@{{N}} > .scratch/stash-archive-N-"
    "<date>.patch` -- then drop. If the archive already exists (or the user "
    "explicitly ordered the drop), approve this prompt."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if not cmd or "stash" not in cmd.lower():
        return 0

    hit = classify(masked(normalize_command(cmd)))
    if hit is None:
        log("ALLOW")
        return 0
    kind, sub = hit

    log(f"ASK kind={kind} sub={sub} cmd={cmd[:100]!r}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-git-stash", "git-stash-gate", f"{kind}:{sub}: {cmd[:240]}",
            )
        except Exception:
            pass

    reason = (DESTROY_REASON if kind == "destroy" else CREATE_REASON).format(sub=sub)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
