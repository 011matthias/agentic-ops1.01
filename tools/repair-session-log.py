# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Repair a session-log day file mangled by concurrent checkpoints.

`checkpoint_scaffold.py finalize` writes the whole frontmatter block and numbers
its entry from its own count of the file it can see. When several sessions
checkpoint on the same day, each one does that against a different snapshot, and
the git merge that follows leaves a day file that is wrong in three ways at once:

1. Frontmatter keys duplicated into the header, one set per session.
2. Stray key blocks (`projects_touched:` ... `---`) stranded between entries,
   where a second frontmatter block landed mid-body.
3. Several entries all numbered `### Session 1`, because each finalize counted
   only the entries it could see.

A fourth appears once a repaired branch is merged forward: git keeps BOTH sides
of an identical entry, so one session appears twice.

None of that is recoverable by re-running finalize, because finalize appends.
This rebuilds the file instead: one frontmatter header with the per-session
values unioned or summed, entries in their existing order, renumbered
sequentially, bodies untouched.

Written 2026-09-09 after the repair was hand-performed five times inside a single
checkpoint, against a day file that reached six sessions. Behaviour is
deliberately conservative: it renumbers headings and rebuilds the header, and it
refuses rather than guesses whenever two entries share a title but differ in
content.

Usage:
    uv run tools/repair-session-log.py docs/sessions/2026-09-09.md
    uv run tools/repair-session-log.py docs/sessions/2026-09-09.md --last "Brisken"
    uv run tools/repair-session-log.py docs/sessions/2026-09-09.md --check

`--last SUBSTR` moves the entry whose title contains SUBSTR to the end, which is
what the local session wants while its own checkpoint has not landed on main yet.
`--check` reports without writing, exit 1 if a repair is needed, so a caller can
gate on it.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

FM_KEY = re.compile(r"^(date|sessions|projects_touched|friction_events|work_types):")
HEAD = re.compile(r"^### Session\s+(\d+)\s+—\s+(.*?)\s*$")


class RepairRefused(Exception):
    """The file needs a decision this tool is not entitled to make."""


def _field(body: list[str], label: str) -> str:
    """Value of a `**Label:** value` line, or '' when absent."""
    for line in body:
        if line.startswith(f"**{label}:**"):
            return line.split("**", 2)[2].lstrip(": ").strip()
    return ""


def parse_entries(text: str) -> list[tuple[str, list[str]]]:
    """Split into (title, body) pairs, dropping every frontmatter fragment.

    Identical duplicates collapse to one. A repeated title with a different body
    raises, because picking a winner would silently discard a session's record.
    """
    lines = text.split("\n")
    heads = [i for i, line in enumerate(lines) if HEAD.match(line)]
    if not heads:
        raise RepairRefused("no '### Session N - Title' entries found")

    entries: list[tuple[str, list[str]]] = []
    seen: dict[str, list[str]] = {}
    for n, start in enumerate(heads):
        title = HEAD.match(lines[start]).group(2)
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        body = [
            line
            for line in lines[start + 1 : end]
            if line.strip() != "---" and not FM_KEY.match(line)
        ]
        while body and not body[-1].strip():
            body.pop()
        if title in seen:
            if seen[title] == body:
                continue
            raise RepairRefused(
                f"two entries titled {title!r} with different bodies; "
                "resolve by hand rather than letting a tool pick"
            )
        seen[title] = body
        entries.append((title, body))
    return entries


def render(date: str, entries: list[tuple[str, list[str]]]) -> str:
    """One frontmatter header plus sequentially numbered entries."""
    friction = 0
    for _, body in entries:
        m = re.match(r"(\d+)", _field(body, "Friction"))
        if m:
            friction += int(m.group(1))

    projects: list[str] = []
    types: list[str] = []
    for _, body in entries:
        for proj in _field(body, "Projects").split(","):
            proj = proj.strip()
            if proj and proj not in projects:
                projects.append(proj)
        work = _field(body, "Type")
        if work and work not in types:
            types.append(work)

    out = [
        "---",
        f"date: {date}",
        f"sessions: {len(entries)}",
        f"projects_touched: [{', '.join(projects)}]",
        f"friction_events: {friction}",
        f"work_types: [{', '.join(types)}]",
        "---",
        "",
    ]
    for n, (title, body) in enumerate(entries, 1):
        out.append(f"### Session {n} — {title}")
        out.extend(body)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def damage(text: str) -> list[str]:
    """Structural faults only. Empty list means the file is sound.

    Deliberately blind to whitespace and to header values that merely differ from
    what the entries would derive. A checker that fires on a healthy file trains
    the reader to ignore it, which is how the 2026-09-09 preflight-subset row
    went wrong: a gate that is a strict superset of the real problem is worse
    than none, because it is trusted.
    """
    lines = text.split("\n")
    faults: list[str] = []

    closes = [i for i, line in enumerate(lines) if line.strip() == "---"]
    header_end = closes[1] if len(closes) >= 2 and closes[0] == 0 else 0

    seen_keys: set[str] = set()
    for line in lines[1:header_end]:
        m = FM_KEY.match(line)
        if m and m.group(1) in seen_keys:
            faults.append(f"duplicate frontmatter key in header: {m.group(1)}")
        elif m:
            seen_keys.add(m.group(1))

    for i, line in enumerate(lines[header_end + 1 :], start=header_end + 1):
        if FM_KEY.match(line):
            faults.append(f"frontmatter key stranded in the body at line {i + 1}")
            break

    numbers, titles = [], []
    for line in lines:
        m = HEAD.match(line)
        if m:
            numbers.append(int(m.group(1)))
            titles.append(m.group(2))
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        faults.append(f"session numbers are not sequential: {numbers}")
    dupes = {t for t in titles if titles.count(t) > 1}
    if dupes:
        faults.append(f"repeated entry title(s): {', '.join(sorted(dupes))}")

    return faults


def repair(text: str, date: str, last: str | None = None) -> str:
    entries = parse_entries(text)
    if last:
        matches = [e for e in entries if last in e[0]]
        if len(matches) != 1:
            raise RepairRefused(
                f"--last {last!r} matched {len(matches)} entries, need exactly 1"
            )
        entries.remove(matches[0])
        entries.append(matches[0])
    return render(date, entries)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", help="docs/sessions/YYYY-MM-DD.md")
    ap.add_argument(
        "--date",
        default=None,
        help="date for the frontmatter; defaults to the filename stem",
    )
    ap.add_argument(
        "--last",
        default=None,
        help="move the entry whose title contains this substring to the end",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="report without writing; exit 1 if a repair is needed",
    )
    args = ap.parse_args()

    path = pathlib.Path(args.path)
    if not path.is_file():
        print(f"[repair-session-log] no such file: {path}", file=sys.stderr)
        return 2

    date = args.date or path.stem
    original = path.read_text(encoding="utf-8")

    faults = damage(original)
    reorder = False
    if args.last and not args.check:
        try:
            titles = [t for t, _ in parse_entries(original)]
        except RepairRefused:
            titles = []
        reorder = bool(titles) and args.last not in titles[-1]

    if not faults and not reorder:
        print(f"[repair-session-log] already sound: {path.name}")
        return 0

    if args.check:
        print(f"[repair-session-log] REPAIR NEEDED: {path.name}")
        for fault in faults:
            print(f"  - {fault}")
        return 1

    try:
        fixed = repair(original, date, args.last)
    except RepairRefused as exc:
        print(f"[repair-session-log] REFUSED: {exc}", file=sys.stderr)
        return 3

    entries = parse_entries(fixed)
    for fault in faults:
        print(f"  fixed: {fault}")
    path.write_text(fixed, encoding="utf-8")
    print(f"[repair-session-log] repaired {path.name}: {len(entries)} entries")
    for n, (title, _) in enumerate(entries, 1):
        print(f"  {n}. {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
