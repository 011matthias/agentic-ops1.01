#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PostToolUse(all tools) + Stop hook: a deploy is not verified until the
CONSUMER of the changed payload has been driven.

WHY THIS EXISTS
---------------
2026-08-24 friction row (brisken, B2): "Deployed v86 and declared it verified
on /healthz plus API reads, without driving the SPA that consumes the changed
payload -- the exact class of the 2026-08-22 blank-page incident. The consumer
check happened only later and found the SPA renders the new `pooled` status as
'Arriving' with a blank Month, so six real receipts misreport indefinitely."

Both halves of that sentence matter. The server was fine: `/healthz` returned
200 and the API returned the new field, so every check that was run passed. The
defect lived entirely in the consumer, which had never been asked to render the
new payload. A `WebFetch` of an SPA route returns the shell, not the rendered
state, so fetching harder would not have caught it either.

B2 already says "test the behavior, not the config". It did not hold, twice, in
three days -- the documented fix is the one that keeps failing. What is missing
is not the instruction but the coupling: nothing connected "you deployed a
payload change" to "you have not yet driven the thing that reads it", so the
gap was invisible until a human found it.

This hook makes that coupling structural. A deploy opens a marker; only a real
browser drive closes it; and while it is open, a Stop that CLAIMS verification
is blocked with the specific thing still unchecked.

TWO DEPLOY CLASSES
------------------
An app deploy (fly / railway / wrangler) puts a client-side renderer between
the API and the truth, so only a browser drive can close it. A server-rendered
deploy (vercel) is closed by a fetch of the shipped URL, which is what
rule_behaviors already mandates and what genuinely sees the markup. Keeping
these apart is what keeps the gate off the repo's most frequent ship: a guard
that cries wolf on every platform deploy gets approved reflexively, and then it
protects nothing.

DECISION MATRIX
---------------
PostToolUse:
  - fly / railway / wrangler deploy       -> open marker (kind=browser).
  - vercel deploy / force-deploy          -> open marker (kind=fetch).
  - Browser drive (Playwright MCP,
    agent-browser, a playwright run)      -> close either marker.
  - WebFetch / curl / wget / /healthz     -> closes a `fetch` marker; on a
                                             `browser` marker it does NOT
                                             close, and says so. That
                                             substitution IS the incident.
  - Anything else                         -> silent.

Stop:
  - Marker open AND the final message
    claims verified / live / confirmed    -> BLOCK once, naming what is
                                             unchecked.
  - Anything else                         -> silent allow.

The Stop arm honors `stop_hook_active`, so it costs exactly one turn and can
never wedge a session -- the same containment shape as stop-b1-gate. A deploy
whose surface genuinely has no browser consumer (a worker, a pure API) passes
by saying what the verification actually covered instead of the bare word, or
by re-stopping.

Fail-open per the project hook contract: any error exits 0.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import tempfile
import time

try:
    from _shell import normalize_command
except Exception:
    def normalize_command(c: str) -> str:
        return c

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
# Env seam so the suite can exercise the marker lifecycle without touching the
# developer's live session state (mirrors AGENTIC_OPS_SESSION_STATE).
MARKER_FILE = os.environ.get("DEPLOY_CONSUMER_MARKER") or os.path.join(
    tempfile.gettempdir(), "agentic-ops-deploy-consumer.txt"
)
# A marker older than this is assumed dead (machine left on, session over) so a
# forgotten deploy can never nag or block indefinitely. Mirrors the
# platform-not-live marker TTL in post-action-gate.
MARKER_TTL_SEC = 6 * 3600

# Deploys whose consumer is an APP: a client-side renderer stands between the
# API and the truth, so only a browser drive proves the payload renders.
BROWSER_DEPLOY_PATTERNS = [
    r"\bfly(?:ctl)?\s+deploy\b",
    r"\brailway\s+up\b",
    r"\bwrangler\s+deploy\b",
]
# Deploys whose consumer is a SERVER-RENDERED page. rule_behaviors already
# mandates the no-slash URL fetch for these, and that fetch genuinely sees the
# shipped markup, so a fetch closes them. Splitting the two classes is what
# keeps this gate off the repo's most frequent deploy: a guard that cries wolf
# on every platform ship gets approved reflexively and then protects nothing.
FETCH_DEPLOY_PATTERNS = [
    r"\bvercel\s+(?:deploy\b|--prod\b)",
    r"vercel-force-deploy",
]

# What actually renders the payload. A browser drive is the ONLY thing that
# exercises the consumer; everything else reads the server.
BROWSER_TOOL_PREFIXES = ("mcp__playwright__browser_",)
BROWSER_CMD_PATTERNS = [
    r"\bagent-browser\b",
    r"\bplaywright\b",
    r"\bpytest\b.{0,80}\b(e2e|browser|playwright)\b",
]
# Named explicitly so the contract is testable: these look like verification
# and are exactly what the incident ran instead of driving the consumer.
NON_CONSUMER_PATTERNS = [r"\bcurl\b", r"/healthz\b", r"\bwget\b"]

CLAIM_PATTERNS = [
    r"\bverified\b",
    r"\bis (?:now )?live\b",
    r"\bnow live\b",
    r"\bconfirmed (?:working|live|good|deployed)\b",
    r"\bdeploy(?:ed|ment)? (?:is )?(?:verified|confirmed|clean|good|healthy)\b",
    r"\bworking in production\b",
    r"\bshipped and (?:verified|confirmed)\b",
]
COMPILED_CLAIMS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in CLAIM_PATTERNS]


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} deploy-consumer-gate {msg}\n")
    except Exception:
        pass


def read_marker() -> tuple[str, str] | None:
    """(kind, label) for the pending deploy, or None when nothing is open or
    the marker has expired. `kind` is "browser" or "fetch"."""
    try:
        with open(MARKER_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        return None
    parts = raw.split("\t")
    if len(parts) != 3:
        return None
    ts_str, kind, label = parts
    try:
        ts = float(ts_str)
    except ValueError:
        return None
    if time.time() - ts > MARKER_TTL_SEC:
        return None
    if kind not in ("browser", "fetch") or not label:
        return None
    return kind, label


def write_marker(kind: str, label: str) -> None:
    try:
        with open(MARKER_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.time()}\t{kind}\t{label}")
    except Exception:
        pass


def clear_marker() -> None:
    try:
        os.remove(MARKER_FILE)
    except Exception:
        pass


def deploy_label(view: str) -> str:
    """A human-readable target for the advisory: the app name when the command
    carries one, else the deploy verb itself."""
    m = re.search(r"-a\s+(\S+)|--app[= ](\S+)", view)
    if m:
        return m.group(1) or m.group(2)
    m = re.search(r"\b(fly(?:ctl)?\s+deploy|vercel[\w-]*|railway\s+up|wrangler\s+deploy)", view)
    return m.group(1) if m else "the deploy"


def matches_any(text: str, patterns) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def emit_post(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


DEPLOY_ADVISORY = (
    "[CONSUMER NOT DRIVEN] {label} deployed. A deploy is verified when the "
    "thing that CONSUMES the changed payload has rendered it -- not when "
    "/healthz returns 200 and the API returns the new field. On 2026-08-24 "
    "exactly those two checks passed while the SPA rendered the new `pooled` "
    "status as 'Arriving' with a blank Month, and six real receipts "
    "misreported until a human found it. WebFetch of an SPA route returns the "
    "shell, not the rendered state, so it does not close this either.\n"
    "Close it by driving the consumer: Playwright MCP (browser_navigate then "
    "browser_snapshot on the route that shows the changed field) or "
    "agent-browser. Assert the NEW value renders, and that no fallback string "
    "('Arriving', '--', 'Unknown', a blank cell) took its place."
)

FETCH_DEPLOY_ADVISORY = (
    "[VERIFY THE SHIPPED PAGE] {label} deployed. This surface is "
    "server-rendered, so a fetch of the no-slash URL genuinely sees the "
    "shipped markup and closes this check. Confirm the NEW build is served "
    "rather than the prior one; a stale page right after a merge means 'not "
    "force-deployed yet', not 'CDN cache'."
)

NON_CONSUMER_ADVISORY = (
    "[STILL NOT DRIVEN] That was a server-side check, and {label} is still "
    "waiting on its consumer. /healthz, curl and API reads all passed on "
    "2026-08-24 while the SPA showed 'Arriving' with a blank Month. This "
    "check does not close the pending consumer drive."
)

CONSUMER_CLEARED = (
    "[CONSUMER DRIVEN] Browser drive observed; the pending consumer check for "
    "{label} is closed. Confirm the assertion was on the CHANGED field's "
    "rendered value, not just that the page loaded."
)

STOP_REASON = (
    "[CONSUMER NOT DRIVEN] This response claims verification ({snippet!r}) but "
    "{label} was deployed in this session and no browser drive has run since. "
    "Server-side checks (/healthz, API reads, curl, WebFetch) do not exercise "
    "the consumer -- that is precisely the 2026-08-24 defect, where every "
    "server check passed while the SPA rendered the new status as 'Arriving' "
    "with a blank Month for six real receipts.\n\n"
    "Do one of these before stopping: (1) drive the consumer -- Playwright MCP "
    "browser_navigate + browser_snapshot on the route showing the changed "
    "field, and assert the NEW value renders rather than a fallback; or (2) if "
    "the deployed surface genuinely has no browser consumer, say so explicitly "
    "and state what the verification actually covered, instead of the "
    "unqualified word 'verified'."
)


def last_assistant_text(transcript_path: str) -> str:
    """Concatenated text of the final assistant message, or ''. Same JSONL
    walk as stop-b1-gate; any failure -> '' (fail-open)."""
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
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def strip_code(text: str) -> str:
    """Drop code spans so a quoted example of the word cannot self-trigger."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def _close(reason: str, pending: tuple[str, str]) -> int:
    clear_marker()
    log(f"CLEAR {reason} pending={pending}")
    emit_post(CONSUMER_CLEARED.format(label=pending[1]))
    return 0


def _server_check(pending: tuple[str, str], reason: str) -> int:
    """A server-side check. Closes a server-rendered deploy; for an app deploy
    it is the incident's own move, so say so at the moment it happens rather
    than letting it accumulate into a sense that verification has been done."""
    kind, label = pending
    if kind == "fetch":
        return _close(reason, pending)
    log(f"NON-CONSUMER {reason} pending={label}")
    emit_post(NON_CONSUMER_ADVISORY.format(label=label))
    return 0


def handle_post(event: dict) -> int:
    tool = event.get("tool_name") or ""
    pending = read_marker()

    if tool.startswith(BROWSER_TOOL_PREFIXES):
        return _close(f"tool={tool}", pending) if pending else 0

    if tool == "WebFetch":
        return _server_check(pending, "tool=WebFetch") if pending else 0

    if tool not in ("Bash", "PowerShell"):
        return 0
    cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0
    view = normalize_command(cmd)

    if matches_any(view, BROWSER_CMD_PATTERNS):
        return _close(f"cmd={cmd[:60]}", pending) if pending else 0

    for kind, patterns in (("browser", BROWSER_DEPLOY_PATTERNS),
                           ("fetch", FETCH_DEPLOY_PATTERNS)):
        if matches_any(view, patterns):
            label = deploy_label(view)
            write_marker(kind, label)
            log(f"OPEN kind={kind} label={label} cmd={cmd[:60]}")
            emit_post(
                (DEPLOY_ADVISORY if kind == "browser" else FETCH_DEPLOY_ADVISORY)
                .format(label=label)
            )
            return 0

    if matches_any(view, NON_CONSUMER_PATTERNS):
        return _server_check(pending, f"cmd={cmd[:60]}") if pending else 0
    return 0


def handle_stop(event: dict) -> int:
    # Continuation of a prior hook-block: never re-fire (one turn, not a wedge).
    if event.get("stop_hook_active"):
        return 0
    pending = read_marker()
    if not pending:
        return 0
    text = last_assistant_text(event.get("transcript_path", ""))
    if not text.strip():
        log("ALLOW:no-transcript")
        return 0
    scan = strip_code(text)
    for rx in COMPILED_CLAIMS:
        m = rx.search(scan)
        if m:
            start = max(0, m.start() - 40)
            snippet = scan[start:m.end() + 40].strip().replace("\n", " ")
            log(f"BLOCK pending={pending} matched={rx.pattern!r}")
            print(json.dumps({
                "decision": "block",
                "reason": STOP_REASON.format(snippet=snippet[:120], label=pending[1]),
            }))
            return 0
    log(f"ALLOW:no-claim pending={pending}")
    return 0


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0

    if os.environ.get("DEPLOY_CONSUMER_GATE_OFF"):
        return 0

    # Route by event shape. A PostToolUse payload always carries tool_name; a
    # Stop payload never does. hook_event_name is honored first when present.
    kind = event.get("hook_event_name")
    if kind == "Stop" or (kind is None and not event.get("tool_name")):
        return handle_stop(event)
    return handle_post(event)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
