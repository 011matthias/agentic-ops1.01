# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fold per-session shard files into the canonical daily session log.

Six concurrent sessions appending to ONE docs/sessions/YYYY-MM-DD.md in a
shared working tree corrupts the file at write time (frontmatter counters
bumped mid-edit, interleaved session blocks). The .gitattributes merge=union
rules only cover commit-time merges, not concurrent working-tree writes.
The fan-out convention:

  each session writes its OWN shard    docs/sessions/YYYY-MM-DD-<sid>.md
  this tool folds shards into          docs/sessions/YYYY-MM-DD.md

Shard discovery: `YYYY-MM-DD-<suffix>.md` where <suffix> is any non-empty
token that is not itself a date and not `context` (the checkpoint commands
use the first 8 chars of the session id, or a short unique slug). Plain
daily files (`YYYY-MM-DD.md`) and the gitignored `*-context.yaml` never
match.

Fold: each shard's BODY is appended verbatim to the canonical file as its
own block behind a fold-marker line:

  <!-- folded: <shardname> sha256:<12-hex of the appended body> -->

Idempotence keys on the CONTENT HASH, not the name: identical content never
folds twice, while a shard recreated under the same name with new content
(the same session checkpoints again after a fold) folds again as a new
block. Shard frontmatter is not copied; its list keys (projects_touched,
work_types) are unioned into the canonical frontmatter and the counters
(sessions, friction_events) are recomputed from the folded body. Shards
fold in (file mtime, name) order. Session headings are kept verbatim;
`repo-sweep.py --normalize-sessions` renumbers them (the nightly sweep does
this automatically after folding).

On --apply, processed shards are DELETED (W1 supersession -- the canonical
file is the surviving record). Default is dry-run.

Usage:
    uv run tools/merge-session-logs.py                    # dry-run, all dates
    uv run tools/merge-session-logs.py --date 2026-07-22  # one date
    uv run tools/merge-session-logs.py --apply            # fold + delete shards

Exit codes: dry-run always 0; --apply exits 1 only on a real fold error.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DATE_PATTERN = r"\d{4}-\d{2}-\d{2}"
SHARD_RE = re.compile(rf"^({DATE_PATTERN})-(.+)\.md$")
MARKER_RE = re.compile(r"^<!-- folded: \S+ sha256:([0-9a-f]{12}) -->$",
                       re.MULTILINE)
LIST_KEYS = ("projects_touched", "work_types")


@dataclass
class FoldResult:
    date: str
    canonical: Path
    folded: list[str] = field(default_factory=list)     # newly appended
    redundant: list[str] = field(default_factory=list)  # already folded / empty
    deleted: list[str] = field(default_factory=list)
    error: str | None = None


def is_shard(name: str) -> bool:
    """Shard = YYYY-MM-DD-<suffix>.md; never the plain daily file, never a
    date-shaped suffix, never the `context` suffix (sibling *-context.yaml
    convention)."""
    m = SHARD_RE.match(name)
    if not m:
        return False
    suffix = m.group(2)
    return not re.fullmatch(DATE_PATTERN, suffix) and suffix != "context"


def discover_shards(sessions_dir: Path) -> dict[str, list[Path]]:
    """date -> shard paths ordered by (mtime, name)."""
    by_date: dict[str, list[Path]] = {}
    if not sessions_dir.is_dir():
        return by_date
    for p in sessions_dir.iterdir():
        if p.is_file() and is_shard(p.name):
            by_date.setdefault(SHARD_RE.match(p.name).group(1), []).append(p)
    for shards in by_date.values():
        shards.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return dict(sorted(by_date.items()))


def split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    """(frontmatter lines or None, body). Malformed frontmatter -> (None, text)."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def parse_list(val: str) -> list[str]:
    return [x.strip() for x in val.strip().strip("[]").split(",") if x.strip()]


def body_hash(block: str) -> str:
    return hashlib.sha256(block.encode("utf-8")).hexdigest()[:12]


def new_canonical(date: str) -> str:
    """Frontmatter shape of the existing daily files (comd_checkpoint)."""
    return (f"---\ndate: {date}\nsessions: 0\nprojects_touched: []\n"
            f"friction_events: 0\nwork_types: []\n---\n")


def recompute_counters(front: list[str], body: str,
                       merged_lists: dict[str, list[str]]) -> list[str]:
    """sessions/friction_events from the body; union the shard list keys.
    Mirrors repo-sweep.py normalize_session_frontmatter semantics."""
    sessions = len(re.findall(r"^### Session ", body, flags=re.MULTILINE))
    friction = sum(int(m.group(1)) for m in
                   re.finditer(r"^\*\*Friction:\*\*\s*(\d+)", body,
                               flags=re.MULTILINE))
    out: list[str] = []
    for ln in front:
        m = re.match(r"^(\w+):\s*(.*)$", ln)
        key = m.group(1) if m else None
        if key == "sessions":
            out.append(f"sessions: {sessions}")
        elif key == "friction_events":
            out.append(f"friction_events: {friction}")
        elif key in LIST_KEYS:
            vals = parse_list(m.group(2))
            for item in merged_lists.get(key, []):
                if item not in vals:
                    vals.append(item)
            out.append(f"{key}: [{', '.join(vals)}]")
        else:
            out.append(ln)
    return out


def fold_date(sessions_dir: Path, date: str, shards: list[Path],
              apply: bool) -> FoldResult:
    canonical = sessions_dir / f"{date}.md"
    result = FoldResult(date=date, canonical=canonical)
    try:
        text = (canonical.read_text(encoding="utf-8") if canonical.exists()
                else new_canonical(date))
        existing_hashes = set(MARKER_RE.findall(text))
        front, body = split_frontmatter(text)
        merged_lists: dict[str, list[str]] = {k: [] for k in LIST_KEYS}
        appended = False

        for shard in shards:
            sfront, sbody = split_frontmatter(shard.read_text(encoding="utf-8"))
            for ln in sfront or []:
                m = re.match(r"^(\w+):\s*(.*)$", ln)
                if m and m.group(1) in LIST_KEYS:
                    for item in parse_list(m.group(2)):
                        if item not in merged_lists[m.group(1)]:
                            merged_lists[m.group(1)].append(item)
            block = sbody.strip("\n")
            if not block:
                result.redundant.append(shard.name)
                continue
            digest = body_hash(block)
            if digest in existing_hashes:
                result.redundant.append(shard.name)
                continue
            marker = f"<!-- folded: {shard.name} sha256:{digest} -->"
            body = body.rstrip("\n") + f"\n\n{marker}\n{block}\n"
            existing_hashes.add(digest)
            appended = True
            result.folded.append(shard.name)

        if apply:
            if appended:
                if front is not None:
                    front = recompute_counters(front, body, merged_lists)
                    out_text = ("\n".join(["---", *front, "---"]) + "\n\n"
                                + body.strip("\n") + "\n")
                else:
                    out_text = body.strip("\n") + "\n"
                canonical.write_text(out_text, encoding="utf-8", newline="\n")
            # delete only after a successful write (or nothing to write)
            for shard in shards:
                if shard.name in result.folded or shard.name in result.redundant:
                    shard.unlink()
                    result.deleted.append(shard.name)
    except Exception as ex:  # per-date isolation; other dates still fold
        result.error = f"{type(ex).__name__}: {ex}"
    return result


def run_fold(sessions_dir: Path | str, date: str | None = None,
             apply: bool = False) -> list[FoldResult]:
    sessions_dir = Path(sessions_dir)
    by_date = discover_shards(sessions_dir)
    if date is not None:
        by_date = {date: by_date[date]} if date in by_date else {}
    return [fold_date(sessions_dir, d, shards, apply)
            for d, shards in by_date.items()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", metavar="YYYY-MM-DD",
                    help="fold only this date (default: all dates with shards)")
    ap.add_argument("--apply", action="store_true",
                    help="write the fold + delete shards (default: dry-run)")
    ap.add_argument("--sessions-dir", metavar="DIR",
                    help="override the docs/sessions location (tests)")
    args = ap.parse_args()

    if args.date and not re.fullmatch(DATE_PATTERN, args.date):
        ap.error(f"--date must be YYYY-MM-DD, got {args.date!r}")

    sessions_dir = (Path(args.sessions_dir) if args.sessions_dir
                    else Path(__file__).resolve().parents[1] / "docs" / "sessions")

    results = run_fold(sessions_dir, date=args.date, apply=args.apply)
    had_error = False
    if not results:
        print("no shards found")
    for r in results:
        if r.error:
            had_error = True
            print(f"{r.date}: ERROR {r.error}")
            continue
        verb = "folded" if args.apply else "would fold"
        for name in r.folded:
            print(f"{r.date}: {verb} {name} -> {r.canonical.name}")
        for name in r.redundant:
            state = "deleted" if args.apply else "would delete"
            print(f"{r.date}: {name} already folded or empty; shard {state}")
    if not args.apply:
        print("Mode: DRY-RUN (re-run with --apply to write)")
    return 1 if (args.apply and had_error) else 0


if __name__ == "__main__":
    sys.exit(main())
