#!/usr/bin/env python3
"""UserPromptSubmit hook: classify input as exploratory vs directive.

If the prompt looks like brainstorming (>=2 exploratory signals, 0 directive
signals), inject a [GATE] advisory reminding the agent not to treat
brainstorming examples as a hard spec. See rule_behaviors.md "Input
interpretation" gate.

Defensive: any error -> exit 0 silently so a broken hook never blocks the agent.
"""
import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# tools/ on the path for the B1 primer's counter (see b1_primer below).
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tools",
    ),
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

B1_PRIMER = (
    "[B1 PRIMER] stop-b1-gate blocked {n} deferral{s} earlier in THIS session. "
    "That gate is post-hoc: by the time it fires the deferring response is "
    "already written and the turn has to be redone. Before you write this "
    "turn's closing text: any next step that is bounded, reversible, and "
    "yours to take gets DONE now, not offered. No 'want me to', no 'let me "
    "know if', no 'the natural next step would be'. If the build passes, "
    "ship it. If you truly lack the tool or access, write 'LIMITATION: ... "
    "USER ACTION NEEDED: ...' as a statement, not a choice. Only a genuine "
    "high-blast-radius fork (irreversible, outward-facing, or a real "
    "either/or the user must decide) is worth stopping on."
)

EXPLORATORY = [
    r"\bmaybe\b",
    r"\bwhat if\b",
    r"\bthinking about\b",
    r"\bcould we\b",
    r"\bcould you\b",
    r"\bwondering\b",
    r"\bperhaps\b",
    r"\bi('?| a)m thinking\b",
    r"\bnot sure\b",
    r"\bbrainstorm",
]

DIRECTIVE = [
    r"\bdo (this|that|the)\b",
    r"\bfix\b",
    r"\bbuild\b",
    r"\bship\b",
    r"\bdeploy\b",
    r"\brun\b",
    r"\bmake (it|sure|the)\b",
    r"\badd\b",
    r"\bremove\b",
    r"\bdelete\b",
    r"\bcreate\b",
    r"\bimplement\b",
    r"\brestore\b",
    r"\bmerge\b",
    r"\bcommit\b",
    r"\bpush\b",
]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} input-classifier {msg}\n")
    except Exception:
        pass


def emit(additional_context: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }))


def b1_primer() -> str:
    """Pre-generation B1 nudge when a deferral was blocked earlier this
    session. Fires once per recorded block (b1_blocks > b1_primed), so a
    burst gets primed each time rather than nagging on every prompt. Silent
    when nothing is due. Fail-open: any state error -> no primer."""
    if session_state is None:
        return ""
    try:
        due = session_state.b1_priming_due()
        if due <= 0:
            return ""
        n = int(session_state.load().get("b1_blocks", 0))
        session_state.mark_b1_primed()
        log_fire(f"B1-PRIMER blocks={n} due={due}")
        return B1_PRIMER.format(n=n, s="" if n == 1 else "s")
    except Exception:
        return ""


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    blocks = []

    prompt = (event.get("prompt") or "").lower()
    if prompt:
        explor = sum(1 for p in EXPLORATORY if re.search(p, prompt))
        direct = sum(1 for p in DIRECTIVE if re.search(p, prompt))
        if explor >= 2 and direct == 0:
            log_fire(f"GATE explor={explor} direct={direct}")
            blocks.append(
                "[GATE] This prompt reads as exploratory (brainstorming / thinking-aloud), "
                "not directive. Extract INTENT and strategic direction. Restate interpreted "
                "intent before acting. Do not treat any examples in the message as a spec, "
                "and do not start building until you have confirmed the actual goal. "
                "See rule_behaviors.md 'Input interpretation'."
            )

    primer = b1_primer()
    if primer:
        blocks.append(primer)

    # One emit per event: the harness reads a single JSON object, so both
    # advisories share one additionalContext when they fire together.
    if blocks:
        emit("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
