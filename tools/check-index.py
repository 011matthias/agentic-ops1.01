# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Assert every tools/*.py, *.sh, *.cjs, *.mjs has a row in tools/INDEX.md.

Closes the recurring "tool added without an INDEX entry" friction (register
#74, #133): tools/INDEX.md is auto-loaded at session start to reduce missed-tool
friction, but nothing enforced that a NEW tool actually gets listed. This does.

A tool counts as listed if its filename appears backtick-prefixed in the index
(the manifest convention is `| `<name> [args]` | <when to use> |`).

Scanned directories: tools/ itself plus tools/scorers/. The scorers
subdirectory is included because the scorer contract (tools/scorers/README.md
clause 7) requires every scorer to be registered in INDEX.md, and nothing
enforced it - iterdir() over tools/ alone never descends, so a new scorer
could ship unregistered and the operator would never learn it exists. Its
scorers appear inside one prose cell rather than one row each, which the
backtick test handles unchanged.

Exit 0 if every tool is listed; exit 1 with the missing list otherwise.
Run: uv run tools/check-index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
INDEX = TOOLS / "INDEX.md"

# Tools intentionally not indexed. Keep empty; add with a reason if ever needed.
EXEMPT: set[str] = set()


def _scannable(d: Path) -> list[Path]:
    if not d.is_dir():
        return []
    return [
        p for p in d.iterdir()
        if p.is_file() and p.suffix in (".py", ".sh", ".cjs", ".mjs")
        and p.name not in EXEMPT
    ]


def main(tools_dir: Path = TOOLS, index_path: Path = INDEX) -> int:
    if not index_path.is_file():
        print(f"[check-index] MISSING: {index_path}", file=sys.stderr)
        return 1
    index_text = index_path.read_text(encoding="utf-8")
    tools = sorted(
        {p.name for p in _scannable(tools_dir)}
        | {p.name for p in _scannable(tools_dir / "scorers")}
    )
    missing = [t for t in tools if f"`{t}" not in index_text]
    if missing:
        print("[check-index] tools/ scripts with no tools/INDEX.md row:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print(
            "Add a one-line row to tools/INDEX.md: | `<tool> [args]` | <when to use> |",
            file=sys.stderr,
        )
        return 1
    print(f"[check-index] OK: all {len(tools)} tools listed in INDEX.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
