#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Bash|PowerShell) hook: refuse oversized / escape-fragile Bash
heredocs and redirect to the Write tool.

WHY THIS EXISTS
---------------
Bash heredocs carrying large Python payloads keep failing, and they fail in the
two worst ways: loudly ("unexpected EOF while looking for matching quote",
costing a retry) and SILENTLY (a backslash escape collapses in transit, so the
payload runs with different semantics and the command exits 0 with wrong
results).

  2026-08-22 friction row: "unexpected EOF" on a ~150-line heredoc.
                            Fix logged as `documented`, Resolved=Yes.
  2026-08-24 friction row: recurred. A ~300-line Python payload died the same
                            way, then a heredoc-embedded replace silently
                            failed to match an escaped `\\n`. ~3 calls lost.

The documented fix ("use the Write tool for multi-line Python, keep heredocs to
short ASCII patches") did not hold across sessions -- which is the definition of
a Layer-3 memory fix failing. Per the rule_behaviors self-annealing ladder
(tool > structural gate > memory), a recurrence at this point has earned a hook
that fires at decision time instead of a note that depends on recall.

Confirmed live while building this gate: `cat > f <<'EOF'` containing
`(?<!\\\\)` reached Python as `(?<!\\)`, an unterminated-subpattern crash. The
collapse happens above the shell, so a quoted delimiter does not protect you.

DECISION MATRIX
---------------
- No heredoc opener                         -> silent allow.
- Body > MAX_HEREDOC_LINES (80) lines       -> DENY. Size is the loud failure.
- Well-formed body with a Python triple-
  quoted block (`\"\"\"` / `'''`)               -> DENY. Nested quoting is where
                                                 the tokenizer gives up.
- Well-formed Python-context body holding a
  literal `\\\\`                               -> DENY. The silent-corruption
                                                 shape, evidenced above.
- Anything else (short ASCII patch, commit
  message, PR body)                         -> silent allow.

The triple-quote and backslash rules require a TERMINATED heredoc, so a stray
`<<WORD` inside a quoted string cannot false-deny on them; only the size rule
applies to an unterminated opener, and a >80-line unterminated body is the
"unexpected EOF" bug itself.

Deny rather than ask: the remedy (Write the payload to a file, then run the
file) is always available, lossless, and does not need the user. `HEREDOC_GATE_ALLOW=1`
is the user-ordered escape hatch for a genuinely unavoidable large heredoc.

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

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

MAX_HEREDOC_LINES = 80

# `<<TAG`, `<<'TAG'`, `<<"TAG"`, `<<-TAG`. A here-STRING (`<<<word`) cannot
# match: `<` is not in the tag character class.
_OPENER = re.compile(r"<<-?[ \t]*(?P<q>['\"]?)(?P<tag>[A-Za-z_][\w.-]*)(?P=q)")
_TRIPLE_QUOTE = re.compile(r"\"\"\"|'''")
_PY_INVOKE = re.compile(r"\bpython3?\b|\bpy\b|\buv\s+run\b")


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} heredoc-size-gate {msg}\n")
    except Exception:
        pass


def _body_lines(body: str) -> int:
    if not body:
        return 0
    return body.count("\n") + (0 if body.endswith("\n") else 1)


def heredocs(cmd: str) -> list[dict]:
    """Every heredoc opener in `cmd`, with its body, terminator state and
    whether it feeds a Python interpreter."""
    found = []
    for m in _OPENER.finditer(cmd):
        tag = m.group("tag")
        nl = cmd.find("\n", m.end())
        if nl == -1:
            # Opener with nothing after it on a later line: not a heredoc body.
            continue
        rest = cmd[nl + 1:]
        term = re.search(rf"^[ \t]*{re.escape(tag)}[ \t]*$", rest, re.MULTILINE)
        body = rest[: term.start()] if term else rest
        line_start = cmd.rfind("\n", 0, m.start()) + 1
        prefix = cmd[line_start:m.start()]
        found.append({
            "tag": tag,
            "body": body,
            "lines": _body_lines(body),
            "terminated": term is not None,
            "python": bool(_PY_INVOKE.search(prefix)) or tag.upper().startswith("PY"),
        })
    return found


def classify(cmd: str) -> tuple[str, dict] | None:
    """(kind, heredoc) for the first deny-class heredoc in `cmd`, else None."""
    for hd in heredocs(cmd):
        if hd["lines"] > MAX_HEREDOC_LINES:
            return ("size", hd)
        if not hd["terminated"]:
            continue
        if _TRIPLE_QUOTE.search(hd["body"]):
            return ("triple-quote", hd)
        if hd["python"] and "\\\\" in hd["body"]:
            return ("backslash", hd)
    return None


REMEDY = (
    "Use the Write tool instead: write the payload to a file (the scratchpad "
    "for one-shot work, `.scratch/` inside the repo), then run that file "
    "(`uv run <file>` / `python <file>`). The Write tool carries the bytes "
    "verbatim; a heredoc does not."
)

REASONS = {
    "size": (
        "HEREDOC TOO LARGE ({lines} lines, cap {cap}) intercepted on heredoc "
        "`<<{tag}`. Large heredoc payloads die with 'unexpected EOF while "
        "looking for matching quote' and cost a retry each time (friction "
        "register 2026-08-22 ~150 lines, 2026-08-24 ~300 lines; the documented "
        "'keep heredocs short' fix did not hold across sessions). " + REMEDY
    ),
    "triple-quote": (
        "HEREDOC CONTAINS A PYTHON TRIPLE-QUOTED BLOCK intercepted on heredoc "
        "`<<{tag}` ({lines} lines). Nested triple quotes inside a heredoc are "
        "where the shell tokenizer gives up -- this is the documented "
        "'unexpected EOF' shape. " + REMEDY
    ),
    "backslash": (
        "HEREDOC CARRIES A DOUBLE BACKSLASH into a Python payload, intercepted "
        "on heredoc `<<{tag}` ({lines} lines). Escapes collapse in transit "
        "ABOVE the shell, so a quoted delimiter does not protect them: "
        "`(?<!\\\\\\\\)` arrives as `(?<!\\\\)` and the payload runs with "
        "different semantics, exit 0, wrong result (2026-08-24 register row: a "
        "heredoc-embedded replace silently failed to match). " + REMEDY
    ),
}


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


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

    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if "<<" not in cmd:
        return 0

    hit = classify(cmd)
    if hit is None:
        return 0
    kind, hd = hit

    reason = REASONS[kind].format(
        tag=hd["tag"], lines=hd["lines"], cap=MAX_HEREDOC_LINES
    )

    if os.environ.get("HEREDOC_GATE_ALLOW"):
        log(f"OVERRIDE kind={kind} tag={hd['tag']} lines={hd['lines']}")
        advise(f"OVERRIDE ACTIVE (HEREDOC_GATE_ALLOW=1): {reason}")
        return 0

    log(f"DENY kind={kind} tag={hd['tag']} lines={hd['lines']}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-heredoc-size",
                "heredoc-size-gate",
                f"{kind}: <<{hd['tag']} ({hd['lines']} lines)",
            )
        except Exception:
            pass
    deny(reason)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
