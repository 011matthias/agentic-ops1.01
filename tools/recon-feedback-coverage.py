#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Which operator notes in the recon app's feedback.jsonl the backlog never filed.

The recon app appends every in-app note to `feedback.jsonl` and assigns no
number of its own; "note #34" throughout the backlog and the code comments
means the 34th note in that file. Nothing surfaced the notes automatically, so
they were read newest-first and the tail went unactioned for days at a time:

  - note #34 (Criss reporting a date misread) sat five days while backlog item
    27 was parked in writing "until Criss reports one"
  - 2026-09-17: a round answered from the 8 newest of 63 notes; the owner had
    to ask "is that all the feedback that was left?", which surfaced #52, #53,
    #62, #63
  - 2026-09-20: note #70 unfiled since 09-18, found at close-out

Run this at the START of a recon round (project_brisken_expense_recon_usability_loop
already says to read the notes first; this makes "did I cover all of them"
checkable instead of remembered).

The live file needs auth, so pass a local copy:

    uv run tools/recon-feedback-coverage.py --feedback .scratch/feedback.jsonl

Exit codes: 0 every note is filed, 1 some are not, 2 the inputs disagree
(see --help on the numbering check).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BACKLOG = REPO / "workspace" / "clients" / "brisken" / "status" / "p1-improvement-backlog.md"

# `note #34`, `notes #52, #53`, `notes #54-#60`, `note #61 and #62`. Keyed on the
# word so bare `#881` (a PR number) is never mistaken for a note reference.
NOTE_REF = re.compile(
    r"\bnotes?\s+((?:#\d+(?:\s*(?:,|/|&|-|and|to|through|–)\s*#?\d+)*))", re.I)
NUMBER = re.compile(r"\d+")
RANGE_SEP = re.compile(r"#(\d+)\s*(?:-|to|through|–)\s*#?(\d+)")


def read_notes(path: Path) -> list[dict]:
    """Parse feedback.jsonl exactly as the app's _read_feedback does: skip blank
    and malformed lines, keep order, keep only objects. Numbering is 1-based
    over what survives, so a malformed line must not shift the numbers."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def referenced(text: str) -> set[int]:
    """Every note number the backlog cites, ranges expanded."""
    out: set[int] = set()
    for m in NOTE_REF.finditer(text):
        blob = m.group(1)
        for a, b in RANGE_SEP.findall(blob):
            lo, hi = int(a), int(b)
            if lo <= hi and hi - lo <= 200:
                out.update(range(lo, hi + 1))
        out.update(int(n) for n in NUMBER.findall(blob))
    return out


def describe(n: int, note: dict, width: int = 96) -> str:
    comment = " ".join(str(note.get("comment", "")).split())
    where = note.get("section") or note.get("title") or note.get("page") or ""
    who = note.get("operator") or note.get("role") or "?"
    ts = str(note.get("ts", ""))[:16]
    head = f"  #{n:<4} {ts}  {who}"
    if where:
        head += f"  [{' '.join(str(where).split())[:40]}]"
    return f"{head}\n       {comment[:width]}" if comment else head


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feedback", required=True, type=Path,
                    help="local copy of the app's feedback.jsonl")
    ap.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    ap.add_argument("--since", type=int, default=0,
                    help="ignore notes at or below this number")
    ap.add_argument("--quiet", action="store_true", help="counts only")
    args = ap.parse_args(argv)

    for p in (args.feedback, args.backlog):
        if not p.exists():
            print(f"not found: {p}", file=sys.stderr)
            return 2

    notes = read_notes(args.feedback)
    refs = referenced(args.backlog.read_text(encoding="utf-8"))
    total = len(notes)

    # Instrument check. Numbering is file position, so a citation above the
    # note count means the feedback copy is stale or the convention has moved.
    # Reporting "all filed" off a short file is the failure this guards.
    if refs and max(refs) > total:
        print(
            f"INPUTS DISAGREE: the backlog cites note #{max(refs)} but "
            f"{args.feedback} holds only {total} notes. The copy is probably "
            "stale, or note numbers no longer mean file position. Re-download "
            "the file before trusting any coverage number.",
            file=sys.stderr,
        )
        return 2

    unfiled = [n for n in range(args.since + 1, total + 1) if n not in refs]
    print(f"{total} notes in {args.feedback.name}; "
          f"{total - len(unfiled)} filed, {len(unfiled)} not")
    if unfiled and not args.quiet:
        print("\nnot referenced anywhere in the backlog:")
        for n in unfiled:
            print(describe(n, notes[n - 1]))
    return 1 if unfiled else 0


if __name__ == "__main__":
    sys.exit(main())
