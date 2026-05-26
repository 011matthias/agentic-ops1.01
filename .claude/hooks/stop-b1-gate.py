#!/usr/bin/env python3
"""Stop hook: B1 deferral catch -- block ONLY when the final response defers.

Prior version blocked *every* stop unconditionally (no classifier): 279 blocks
in 12 days per hook-log.txt, a 100% false-positive rate that forced an extra
turn on every single stop. That per-turn tax was the dominant friction source.

This version reads the transcript, extracts the last assistant message, and
blocks only when that message contains a deferral / closing-offer / ask-
permission-to-ship pattern (the actual B1 violation in rule_behaviors.md and
feedback_no_closing_offers.md). A clean response is allowed to stop silently.

Decision is logged (BLOCK matched=... | ALLOW:clean | ALLOW:<failopen-reason>)
so the false-positive rate can be measured from hook-log.txt going forward.

Defensive contract (unchanged): ANY error, missing transcript, or unparseable
content -> exit 0, allow the stop. A broken classifier must never block; a
missed deferral is cheaper than taxing every clean turn.
"""
import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

# Deferral / closing-offer / ask-permission-to-ship phrasings. Narrow on
# purpose: a bare question or a genuine fork ("which approach do you prefer?")
# must NOT match -- only the shapes where the agent offers to do, or asks
# permission to do, an action it can take autonomously.
DEFERRAL_PATTERNS = [
    r"\b(do you )?want me to\b",
    r"\bwould you like me to\b",
    r"\bshould i (go ahead|proceed|continue|push|merge|deploy|commit|create|ship|run|start|build|fix|add|update|draft|send)\b",
    r"\bshall i\b",
    r"\bif you(?:'?d| would)? (?:want|like|prefer)\b",
    r"\blet me know if you(?:'?d| would| want| 'd like)?\b",
    r"\bjust (?:say the word|let me know)\b",
    r"\bsay the word\b",
    r"\bhappy to .{0,45}\bif you\b",
    r"\bi can .{0,60}\bif you(?:'?d| want| like| need)\b",
    r"\bready to (?:deploy|ship|merge|push|proceed)\b\??$",
    r"\b(?:can|could) you (?:run|verify|check|confirm|test|push|merge|deploy)\b",
    r"\bplease (?:run|verify|check|confirm) \b",
    r"\blmk if\b",
    # === New: soft "natural next move" shapes (register #108 brisken 2026-05-25) ===
    # "If you want, the natural next move is to..." — the if-you-want trailer
    # caught the existing pattern, but the structural shape ("natural next
    # move / obvious next step / from here you could") is a deferral even
    # without the if-you-want trailer. Catch the shape itself.
    r"\b(?:the )?(?:natural|obvious|logical|sensible) next (?:move|step|thing) (?:is|would be)\b",
    r"\bfrom here (?:you could|we could|i could)\b",
    r"\bnext (?:move|step) (?:is|would be) (?:to )?(?:drive|run|build|ship|deploy|merge|push|send|draft|fix|add|update)\b",
    # === New: multi-option closing menu (register #125 meji 2026-05-25) ===
    # "Want me to (a) X, (b) Y, (c) hold" — already caught by "want me to",
    # but the menu shape "(a) ... (b) ... (c) ..." in a closing paragraph is
    # the same anti-pattern in disguise. Triggers ONLY when paired with
    # action verbs (avoid false-fire on user-facing genuine forks).
    r"\([abc]\)\s+(?:draft|start|build|run|deploy|merge|push|send|fix|add|update|hold)\b.{0,80}\([abc]\)",
    # === New: passive-queue / queued-for-resolution (register #83 system 2026-05-11) ===
    # "I'll retry when X resolves" / "queued for when Y unlocks" — the
    # passive-queue anti-pattern. The fix is active retry (background loop,
    # Monitor), not waiting for user re-prompt.
    r"\b(?:queued|waiting|will retry|will resume) (?:for )?(?:when|until|once) .{0,40}(?:resolve|unlock|finish|complete|recover)",
    r"\bi'?ll (?:retry|resume|continue) (?:when|once|after) .{0,40}(?:resolve|unlock|free|available)",
]
COMPILED = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in DEFERRAL_PATTERNS]

REASON = (
    "[B1] Your final response contains a deferral pattern ({snippet!r}). "
    "Before stopping: is this asking the user to do / check / run / confirm "
    "something you can do yourself, or offering an autonomous next step "
    "instead of taking it? If the action is autonomous and bounded, do it "
    "now instead of offering. If the build passes, ship without asking. If "
    "you genuinely lack a tool, frame it as 'LIMITATION: ... USER ACTION "
    "NEEDED: ...' not as a choice. If this is a genuine high-blast-radius "
    "fork or a real question (not a routine continuation), rephrase so it "
    "reads as a decision point, acknowledge briefly, and stop."
)


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} stop-b1-gate {msg}\n")
    except Exception:
        pass


def last_assistant_text(transcript_path: str) -> str:
    """Return concatenated text of the final assistant message, or ''.

    Transcript is JSONL; each line an event. Assistant turns have
    type=='assistant' with message.content a list of blocks; text lives in
    blocks where type=='text'. Robust to schema drift: any failure -> ''.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    last = None
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message") if isinstance(obj, dict) else None
                role = obj.get("type") or (msg or {}).get("role")
                if role == "assistant" and isinstance(msg, dict):
                    last = msg
    except Exception:
        return ""
    if not last:
        return ""
    content = last.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts)
    return ""


def strip_code(text: str) -> str:
    """Drop code AND short double-quoted example spans so the classifier
    cannot match its OWN trigger phrases when they are quoted as examples in
    prose.

    Backticked/fenced code was already neutralized. The remaining blind spot
    (2026-05-19 register, deferred into F2): a status report that lists
    "Want me to" / "Should I deploy" as test-case examples false-blocked the
    stop. A genuine deferral is the agent's live closing offer, never a
    double-quote of one, so stripping short double-quoted spans is
    high-precision. Single quotes are deliberately NOT stripped -- English
    contractions/possessives ("don't", "user's") would mis-pair and blank
    real text. Curly double-quotes are covered too. Span length is capped at
    80 chars so a substantive quoted sentence is left intact (fail-open: a
    missed deferral is cheaper than taxing a clean turn -- the existing
    contract)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r'"[^"\n]{1,80}"', " ", text)
    text = re.sub(r"[“][^“”\n]{1,80}[”]", " ", text)
    return text


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    # Continuation of a prior hook-block: never re-fire (avoids loop + tax).
    if event.get("stop_hook_active"):
        return 0

    text = last_assistant_text(event.get("transcript_path", ""))
    if not text.strip():
        # Fail-open: no readable final message -> allow the stop. Do NOT
        # reinstate the unconditional block.
        log_fire("ALLOW:no-transcript")
        return 0

    scan = strip_code(text)
    # Only the closing region tends to carry the deferral; scanning the whole
    # message is fine but bias the snippet to the tail for a useful citation.
    for rx in COMPILED:
        m = rx.search(scan)
        if m:
            start = max(0, m.start() - 30)
            snippet = scan[start:m.end() + 40].strip().replace("\n", " ")
            log_fire(f"BLOCK matched={rx.pattern!r} snippet={snippet[:80]!r}")
            print(json.dumps({
                "decision": "block",
                "reason": REASON.format(snippet=snippet[:120]),
            }))
            return 0

    log_fire("ALLOW:clean")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
