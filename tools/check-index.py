# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Assert every tools/*.py, *.sh, *.cjs, *.mjs has a row in tools/INDEX.md.

Closes the recurring "tool added without an INDEX entry" friction (register
#74, #133): tools/INDEX.md is auto-loaded at session start to reduce missed-tool
friction, but nothing enforced that a NEW tool actually gets listed. This does.

A tool counts as listed if its filename appears backtick-prefixed as a WHOLE
name inside a table row (the manifest convention is
`| `<name> [args]` | <when to use> |`): the name must directly follow a
backtick and be followed by a closing backtick or whitespace (args), on a
line starting with `|`. A prose mention outside a table (e.g. a removed-tools
note) or a prefix of a longer name does not count.

Scanned directories: tools/ itself plus tools/scorers/. The scorers
subdirectory is included because the scorer contract (tools/scorers/README.md
clause 7) requires every scorer to be registered in INDEX.md, and nothing
enforced it - iterdir() over tools/ alone never descends, so a new scorer
could ship unregistered and the operator would never learn it exists. Its
scorers appear inside one prose cell rather than one row each, which the
backtick test handles unchanged.

Client scan (layout plan W1-18): every workspace/clients/*/automations/tools/
dir holding *.py, *.mjs, *.js or *.cjs needs a README.md beside it with one
row per script in the same format, because a client's tools travel with its
git subtree and tools/INDEX.md does not.

Exit 0 if every tool is listed; exit 1 with the missing list otherwise.
Run: uv run tools/check-index.py
"""
from __future__ import annotations

import re
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


def _freshness_caveat(tools_dir: Path) -> None:
    """One stderr line when this checkout is behind origin/main: the scan sees
    only the WORKING TREE, so a tool added upstream is invisible here (stale-
    checkout blind spot, register 2026-07-22). Only fires for the real repo
    (test runs pass tmp dirs); fail-open on any error."""
    if tools_dir != TOOLS:
        return
    try:
        import importlib.util
        p = TOOLS / "repo_freshness.py"
        spec = importlib.util.spec_from_file_location("repo_freshness", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.warn_if_stale("check-index scan", repo=TOOLS.parent)
    except Exception:
        pass


def _unlisted(names: list[str], index_text: str) -> list[str]:
    # Whole-name match within a table row only: `<name>` or `<name> args`.
    # The old backtick-prefix substring test accepted a prefix of a longer
    # name and mentions anywhere in prose (even a removed-tools note).
    table_rows = [ln for ln in index_text.splitlines() if ln.lstrip().startswith("|")]

    def _listed(name: str) -> bool:
        pat = re.compile(r"`" + re.escape(name) + r"(?=[`\s])")
        return any(pat.search(row) for row in table_rows)

    return [n for n in names if not _listed(n)]


CLIENT_SUFFIXES = (".py", ".mjs", ".js", ".cjs")


def _client_problems(clients_dir: Path | None) -> list[str]:
    """`<client>/automations/tools/<script>` entries with no README.md row."""
    if clients_dir is None or not clients_dir.is_dir():
        return []
    problems = []
    for tdir in sorted(clients_dir.glob("*/automations/tools")):
        scripts = sorted(p.name for p in tdir.iterdir() if p.is_file() and p.suffix in CLIENT_SUFFIXES)
        if not scripts:
            continue
        readme = tdir / "README.md"
        rel = tdir.relative_to(clients_dir.parent.parent) if clients_dir.parent.parent in tdir.parents else tdir
        if not readme.is_file():
            problems.append(f"{rel.as_posix()}/README.md missing ({len(scripts)} scripts)")
            continue
        problems += [f"{rel.as_posix()}/{s}" for s in _unlisted(scripts, readme.read_text(encoding="utf-8"))]
    return problems


def main(tools_dir: Path = TOOLS, index_path: Path = INDEX, clients_dir: Path | None = None) -> int:
    if clients_dir is None and tools_dir == TOOLS:
        clients_dir = TOOLS.parent / "workspace" / "clients"
    if not index_path.is_file():
        print(f"[check-index] MISSING: {index_path}", file=sys.stderr)
        return 1
    _freshness_caveat(tools_dir)
    index_text = index_path.read_text(encoding="utf-8")
    tools = sorted(
        {p.name for p in _scannable(tools_dir)}
        | {p.name for p in _scannable(tools_dir / "scorers")}
    )
    missing = _unlisted(tools, index_text)
    client_missing = _client_problems(clients_dir)
    if client_missing:
        print("[check-index] client automations/tools/ scripts with no README.md row:", file=sys.stderr)
        for m in client_missing:
            print(f"  - {m}", file=sys.stderr)
        print("Add automations/tools/README.md with: | `<script> [args]` | <when to use> |", file=sys.stderr)
        if not missing:
            return 1
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
