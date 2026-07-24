#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Strip em-dashes from prose in markdown files.

Two grammatical forms, two substitutions (2026-07-22 blind-spot fix — the
spaced-only strip let tight `word—word` and `&mdash;` ship unstripped):

  spaced  ` — ` / ` -- ` / ` &mdash; `  ->  `; `  (semicolon joins clauses)
  tight   `word—word` / `word&mdash;word` -> `, ` (semicolon would be wrong
          punctuation mid-clause: `well—fast` reads as `well, fast`)

Tight `word--word` is deliberately NOT auto-stripped (too likely to be a
CLI flag, filename, or identifier); the validators flag it for human review.

Skips fenced code blocks (``` ... ```) so legitimate dash usage in code
stays intact. Skips indented code blocks (4+ leading spaces, non-list lines).
Idempotent: a second run makes zero replacements.

Usage:
    uv run tools/strip-em-dash.py FILE [FILE ...]

Reports per-file count of replacements + any remaining em-dashes after.
"""
import re
import sys
from pathlib import Path

SPACED = re.compile(r" (?:—|&mdash;|--) ")
TIGHT = re.compile(r"(?<=\w)(?:—|&mdash;)(?=\w)")


def strip_em_dashes(path: Path) -> tuple[int, int]:
    """Return (replacements_made, remaining_em_dashes)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    in_fence = False
    out: list[str] = []
    replacements = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # Skip indented code (4+ leading spaces, but not list items)
        if line.startswith("    ") and not stripped.startswith(("-", "*", "+")):
            out.append(line)
            continue
        # Spaced forms (` — ` / ` -- ` / ` &mdash; `) -> `; `;
        # tight forms (`word—word` / `word&mdash;word`) -> `, `.
        new_line, n_spaced = SPACED.subn("; ", line)
        new_line, n_tight = TIGHT.subn(", ", new_line)
        replacements += n_spaced + n_tight
        out.append(new_line)

    new_text = "".join(out)
    path.write_text(new_text, encoding="utf-8")

    # Count remaining em-dashes (these survived because they were inside code
    # or in a mixed-spacing shape neither pattern covers).
    remaining = new_text.count("—") + new_text.count("&mdash;")
    return replacements, remaining


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} FILE [FILE ...]", file=sys.stderr)
        return 2

    total_replacements = 0
    total_remaining = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"SKIP (not a file): {path}", file=sys.stderr)
            continue
        rep, rem = strip_em_dashes(path)
        total_replacements += rep
        total_remaining += rem
        print(f"  {path}: replaced {rep}, remaining {rem}")

    print()
    print(f"Total: replaced {total_replacements}, {total_remaining} em-dashes remain (in code or non-prose context)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
