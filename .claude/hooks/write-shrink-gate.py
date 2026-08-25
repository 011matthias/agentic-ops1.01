#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse(Write) hook: permission-stop when a Write would silently SHRINK
an existing file past a material threshold.

WHY THIS EXISTS
---------------
Two 2026-08 friction rows, same mechanism, different surfaces:

  2026-08-23 (brisken): a Write to tests/test_expense_report_pdf.py clobbered
    598 lines / 17 tests belonging to a different module. The harness's
    read-before-overwrite check PASSED, because the file had been read before
    a context compaction. Caught only because the suite count dropped
    1168 -> 1153. The row names the structural candidate: "an existence check
    on new-file writes" / a size assertion in the ship chain.

  2026-08-24 (system): a loop-brief rewrite silently deleted 504 lines,
    taking the owner's live open queue with it (unapplied Lovable prompts,
    card-registry data entry, the January 0-of-80 finding). Caught only from
    the commit stat afterwards, and restored in a second commit.

The failure is the same both times: `Write` is whole-file replacement, and a
whole-file replacement authored from a stale or partial mental model deletes
content the author never saw. Nothing in the harness reports the delta, so the
loss is invisible at the moment it happens and surfaces later, if at all --
from a suite count or a commit stat.

A read-before-write check cannot catch this (it passed in both incidents). The
size delta can, because it is computed from the bytes on disk at the instant of
the write, with no dependence on what the agent remembers reading.

DECISION MATRIX
---------------
- Target does not exist / unreadable / not text     -> silent allow (creation
                                                       is file-placement-gate's
                                                       job, not this one).
- File shorter than MIN_FILE_LINES                  -> silent allow.
- Removal below both thresholds                     -> silent allow.
- Removal >= HARD_REMOVED lines, or >= SOFT_REMOVED
  lines AND >= SHRINK_RATIO of the file             -> ASK, quantifying the
                                                       delta and naming the
                                                       structural anchors
                                                       (headings, defs,
                                                       classes) that vanish.

Ask, never deny: a deliberate rewrite or a genuine truncation is legitimate and
stays one keystroke away. The prompt exists so a rewrite is a decision rather
than an accident -- and so the anchors it lists ("## Open queue", "def
test_...") are read BEFORE the content is gone, not reconstructed after.

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

# A file this small cannot lose enough to matter, and short config/stub files
# are rewritten wholesale all the time.
MIN_FILE_LINES = 30
# Any removal this large is material regardless of proportion. Both incidents
# (598 and 504 lines) clear it several times over; a routine section rewrite
# does not.
HARD_REMOVED = 120
# Below the hard floor, removal must ALSO be a large fraction of the file, so
# trimming 45 lines from a 900-line module stays silent.
SOFT_REMOVED = 40
SHRINK_RATIO = 0.30

# Paths where whole-file churn is the normal mode of operation.
EXEMPT_PARTS = (".scratch/", "node_modules/", "/__pycache__/", ".venv/")
EXEMPT_NAMES = (
    "package-lock.json", "uv.lock", "poetry.lock", "yarn.lock",
    "pnpm-lock.yaml", "Cargo.lock",
)

# Structural anchors worth naming when they disappear: markdown headings,
# Python defs/classes, JS/TS function+export declarations. These are what a
# reader would notice missing, and listing them turns "504 lines" into "the
# open queue".
_ANCHOR = re.compile(
    r"^\s*(?:#{1,6}\s+\S.*"
    r"|(?:async\s+)?def\s+\w+"
    r"|class\s+\w+"
    r"|(?:export\s+)?(?:async\s+)?function\s+\w+"
    r"|(?:export\s+)?const\s+\w+\s*=\s*(?:async\s*)?\("
    r")",
)


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} write-shrink-gate {msg}\n")
    except Exception:
        pass


def is_exempt(path: str) -> bool:
    posix = path.replace("\\", "/")
    if os.path.basename(posix) in EXEMPT_NAMES:
        return True
    return any(part in posix for part in EXEMPT_PARTS)


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def anchors(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if _ANCHOR.match(line):
            out.append(line.strip()[:90])
    return out


def lost_anchors(old: str, new: str) -> list[str]:
    """Anchors in `old` that survive nowhere in `new`, order preserved."""
    surviving = set(anchors(new))
    seen, out = set(), []
    for a in anchors(old):
        if a not in surviving and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def should_ask(old_lines: int, new_lines: int) -> bool:
    if old_lines < MIN_FILE_LINES:
        return False
    removed = old_lines - new_lines
    if removed <= 0:
        return False
    if removed >= HARD_REMOVED:
        return True
    return removed >= SOFT_REMOVED and (removed / old_lines) >= SHRINK_RATIO


REASON = (
    "WRITE SHRINKS AN EXISTING FILE: {path} goes {old} -> {new} lines "
    "({removed} removed, {pct}% of the file).\n\n"
    "`Write` is whole-file replacement, so everything not in the new content "
    "is gone. Two 2026-08 incidents lost work exactly here: a 598-line test "
    "module clobbered by a same-named write (the read-before-overwrite check "
    "passed -- the read predated a compaction), and a 504-line loop brief "
    "whose live open queue vanished in a rewrite, both caught only afterwards "
    "from a suite count and a commit stat.\n"
    "{anchor_block}"
    "\nIf you meant to change part of this file, cancel and use Edit -- a "
    "targeted Edit cannot delete what it does not name. If the shrink is "
    "deliberate (a real truncation, a rewrite you intend), approve this "
    "prompt. Before approving, check the list above is content you MEANT to "
    "drop: a file that accumulates state is the exact shape that loses it."
)

ANCHOR_BLOCK = (
    "\nStructure present now and absent from the new content ({n} item{s}):\n"
    "{listing}\n"
)


def ask(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Write":
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    new_content = tool_input.get("content")
    if not path or new_content is None or is_exempt(path):
        return 0

    try:
        if not os.path.isfile(path):
            return 0  # creation, not replacement
        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()
    except Exception:
        return 0  # binary, unreadable, permissions -> not this hook's business

    old_lines = line_count(old_content)
    new_lines = line_count(new_content)
    if not should_ask(old_lines, new_lines):
        return 0

    if os.environ.get("WRITE_SHRINK_GATE_ALLOW"):
        log(f"OVERRIDE {path} {old_lines}->{new_lines}")
        return 0

    removed = old_lines - new_lines
    lost = lost_anchors(old_content, new_content)
    if lost:
        shown = lost[:10]
        listing = "\n".join(f"  - {a}" for a in shown)
        if len(lost) > len(shown):
            listing += f"\n  - ... and {len(lost) - len(shown)} more"
        anchor_block = ANCHOR_BLOCK.format(
            n=len(lost), s="" if len(lost) == 1 else "s", listing=listing
        )
    else:
        anchor_block = ""

    reason = REASON.format(
        path=path.replace("\\", "/"),
        old=old_lines,
        new=new_lines,
        removed=removed,
        pct=round(100 * removed / old_lines),
        anchor_block=anchor_block,
    )

    log(f"ASK {path} {old_lines}->{new_lines} lost_anchors={len(lost)}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-write-shrink",
                "write-shrink-gate",
                f"{os.path.basename(path)}: {old_lines}->{new_lines} lines",
            )
        except Exception:
            pass
    ask(reason)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open per project hook contract
