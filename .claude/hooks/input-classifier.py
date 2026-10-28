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
    "either/or the user must decide) is worth stopping on -- and when one "
    "IS genuine, do its read-only half first (find out what the records "
    "actually say) and put the remainder as a decision with a recommendation "
    "via AskUserQuestion. 'Say the word and I'll ...' is an offer, not a "
    "decision point; it is what got blocked on 2026-08-23 and again on "
    "2026-08-24."
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


HEADER_PRIMER = (
    "[SESSION HEADER] This prompt names a scope, which is exactly the case "
    "rule_session-start step 7 makes the header mandatory for. Before other "
    "work: output the session header block (scope, skills, open specs, comms "
    "age, memories loaded BY NAME) and call `python tools/rename-chat.py "
    "\"{{scope}}--{{task-desc}}\"`. Four sessions skipped it (2026-09-09, 09-15, "
    "09-16, 09-17), each self-caught only at checkpoint; the header is what "
    "makes a memory-loading gap visible while the session can still act on it."
)

# A scope word in the first prompt is what makes scope "evident" per
# rule_session-start. Kept to the live clients and the system scopes rather
# than any capitalised word, so an unrelated prompt stays silent.
SCOPE_WORDS = re.compile(
    r"\b(brisken|meji|meji-media|wimmer|warme|volabyg|jochen|vinted|upwork|"
    r"unpauseai|platform|local-web|openclaw|recon|lead desk|onepilot)\b",
    re.I,
)


def header_primer(prompt: str) -> str:
    """Fire once per session, on a prompt whose scope is evident. Silent
    otherwise; silent for the rest of the session once claimed."""
    if session_state is None or not prompt or not SCOPE_WORDS.search(prompt):
        return ""
    try:
        if not session_state.mark_once("session_header_primed"):
            return ""
    except Exception:
        return ""
    log_fire("HEADER-PRIMER")
    return HEADER_PRIMER


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    if session_state is not None:
        session_state.bind_session(event)

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

    header = header_primer(event.get("prompt") or "")
    if header:
        blocks.append(header)

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
