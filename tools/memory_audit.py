# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Audit the auto-memory store: reads, index integrity, duplicates, staleness.

WHY THIS EXISTS
---------------
The memory store only grows (143 files / 1.1 MB on 2026-09-17), and
rule_session-start already had to retire "load every memory" because the
store outgrew it. Nothing said which memories are recalled, which contradict
or repeat each other, or which still describe "pending" work from months ago.
`session-pressure-meter.py` now records every memory-file read
(tools/telemetry_store.py); this joins those reads with the store and the
MEMORY.md index. Ported from ECC's config-gc memory channel, mechanism only.

BUCKETS (candidates for /comd_system-dev; this tool never deletes or edits)
  Retire  an index line whose file is gone, or a memory unread across at least
          30 days of telemetry AND untouched for 90+ days
  Merge   a likely duplicate: slug or index title closely matching another
  Verify  a file with no MEMORY.md line (never surfaced, so never recalled),
          or a memory 60+ days old that still says pending / open / next week
  Keep    everything else

Under 30 days of read telemetry, no read-based Retire is issued and the output
says so.

USAGE
  uv run tools/memory_audit.py [--memory-dir DIR] [--format text|json]
  Default store: ~/.claude/projects/<this repo's slug>/memory (override with
  AGENTIC_OPS_MEMORY_DIR).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telemetry_store  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MIN_READ_COVERAGE_DAYS = 30
RETIRE_AGE_DAYS = 90
STALE_DAYS = 60
DUP_RATIO = 0.85
_INDEX_LINE = re.compile(r"^\s*-\s*\[(?P<title>[^\]]+)\]\((?P<file>[^)]+\.md)\)")
_TYPE_PREFIX = re.compile(r"^(feedback|project|reference|user)[_-]", re.IGNORECASE)
_OPEN_WORK = re.compile(
    r"\b(pending|awaiting|in progress|still open|open item|todo|next week|tomorrow|"
    r"yesterday|last week|this week|next month|not yet)\b",
    re.IGNORECASE,
)


def default_memory_dir() -> Path:
    import os
    env = os.environ.get("AGENTIC_OPS_MEMORY_DIR")
    if env:
        return Path(env)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(REPO))
    projects = Path.home() / ".claude" / "projects"
    if projects.is_dir():
        for p in projects.iterdir():
            if p.name.lower() == slug.lower():
                return p / "memory"
    return projects / slug / "memory"


def _frontmatter_block(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def _field(block: str, key: str) -> str:
    m = re.search(rf"^\s*{key}:\s*(.+)$", block, re.MULTILINE)
    if not m:
        return ""
    v = m.group(1).strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v


def _norm_slug(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _TYPE_PREFIX.sub("", stem.lower())).strip()


def load_store(mem_dir: Path) -> tuple[list[dict], list[dict], int]:
    files = []
    for p in sorted(mem_dir.glob("*.md")):
        if p.name == "MEMORY.md":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        block = _frontmatter_block(text)
        modified = telemetry_store.parse_ts(_field(block, "modified"))
        mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        files.append({
            "file": p.name, "bytes": p.stat().st_size,
            "type": _field(block, "type"), "description": _field(block, "description"),
            "updated": max(filter(None, [modified, mtime])),
            "body": text,
        })
    index_lines = []
    total_lines = 0
    index = mem_dir / "MEMORY.md"
    if index.is_file():
        for line in index.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                total_lines += 1
            m = _INDEX_LINE.match(line)
            if m:
                index_lines.append({"title": m.group("title"), "file": m.group("file").strip()})
    return files, index_lines, total_lines


def _distinguishing(a: str, b: str) -> float:
    """Similarity of what DIFFERS between two names. Shared leading and
    trailing tokens are dropped first: on 2026-09-17 a raw slug ratio scored
    project_brisken_expense_recon_mail_intake vs ..._master_data at 0.82
    purely on the shared prefix. One name adding a single token to the other
    (`x` vs `x-v2`, `x-notes`) counts as a duplicate."""
    ta, tb = a.split(), b.split()
    while ta and tb and ta[0] == tb[0]:
        ta, tb = ta[1:], tb[1:]
    while ta and tb and ta[-1] == tb[-1]:
        ta, tb = ta[:-1], tb[:-1]
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 1.0 if len(ta or tb) <= 1 else 0.0
    return difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()


def _ratio(a: str, b: str) -> float:
    sm = difflib.SequenceMatcher(None, a, b)
    if sm.real_quick_ratio() < DUP_RATIO or sm.quick_ratio() < DUP_RATIO:
        return 0.0
    return sm.ratio()


def duplicates(files: list[dict], index_lines: list[dict]) -> dict[str, tuple[str, float]]:
    titles = {e["file"]: re.sub(r"[^a-z0-9]+", " ", e["title"].lower()).strip()
              for e in index_lines}
    best: dict[str, tuple[str, float]] = {}
    for i, a in enumerate(files):
        for b in files[i + 1:]:
            score = _distinguishing(_norm_slug(a["file"][:-3]), _norm_slug(b["file"][:-3]))
            ta, tb = titles.get(a["file"]), titles.get(b["file"])
            if ta and tb:
                score = max(score, _distinguishing(ta, tb))
            if a["description"] and b["description"]:
                score = max(score, _ratio(a["description"].lower(), b["description"].lower()))
            if score < DUP_RATIO:
                continue
            score = round(score, 2)
            for x, y in ((a, b), (b, a)):
                if score > best.get(x["file"], ("", 0.0))[1]:
                    best[x["file"]] = (y["file"], score)
    return best


def audit(mem_dir: Path) -> dict:
    files, index_lines, index_total = load_store(mem_dir)
    store = mem_dir.parent.name
    now = datetime.now(timezone.utc)
    reads = [r for r in telemetry_store.read(telemetry_store.MEMORY_READS)
             if str(r.get("store", "")).lower() == store.lower()]
    coverage = 0.0
    if reads:
        oldest = min(filter(None, (telemetry_store.parse_ts(r.get("ts")) for r in reads)), default=None)
        coverage = (now - oldest).total_seconds() / 86400 if oldest else 0.0
    last_read: dict[str, datetime] = {}
    r30, r90 = Counter(), Counter()
    for r in reads:
        ts = telemetry_store.parse_ts(r.get("ts"))
        f = r.get("file")
        if not ts or not f:
            continue
        if f not in last_read or ts > last_read[f]:
            last_read[f] = ts
        if now - ts <= timedelta(days=90):
            r90[f] += 1
        if now - ts <= timedelta(days=30):
            r30[f] += 1

    indexed = {e["file"] for e in index_lines}
    on_disk = {f["file"] for f in files}
    dups = duplicates(files, index_lines)
    reads_ok = coverage >= MIN_READ_COVERAGE_DAYS
    rows = []
    for e in index_lines:
        if e["file"] not in on_disk:
            rows.append({"bucket": "Retire", "file": e["file"],
                         "reason": f"MEMORY.md line '{e['title']}' points at a missing file",
                         "evidence": "index line without file"})
    for f in files:
        age = (now - f["updated"]).days
        lr = last_read.get(f["file"])
        evidence = (f"reads 30d/90d {r30[f['file']]}/{r90[f['file']]}, last read "
                    f"{lr.date().isoformat() if lr else 'never recorded'}, "
                    f"updated {f['updated'].date().isoformat()} ({age}d), {f['bytes']} B")
        bucket, reason = "Keep", ""
        if f["file"] in dups:
            other, score = dups[f["file"]]
            bucket, reason = "Merge", f"likely duplicate of {other} ({score})"
        elif f["file"] not in indexed:
            bucket, reason = "Verify", "no MEMORY.md line, so it is never surfaced for recall"
        elif (f["type"] in ("project", "") and age >= STALE_DAYS
              and _OPEN_WORK.search(f["description"] + "\n" + f["body"][:1500])):
            # Project memories track work in flight; in a feedback or reference
            # memory "pending" is part of a rule, not an open item.
            word = _OPEN_WORK.search(f["description"] + "\n" + f["body"][:1500]).group(0)
            bucket, reason = "Verify", f"{age}d old and still says '{word}'"
        elif reads_ok and r90[f["file"]] == 0 and age >= RETIRE_AGE_DAYS:
            bucket, reason = "Retire", (f"0 reads in {min(round(coverage), 90)}d of telemetry, "
                                        f"untouched {age}d")
        rows.append({"bucket": bucket, "file": f["file"], "type": f["type"],
                     "reason": reason, "evidence": evidence,
                     "reads_30d": r30[f["file"]], "reads_90d": r90[f["file"]],
                     "last_read": lr.isoformat() if lr else None})
    order = {"Retire": 0, "Merge": 1, "Verify": 2, "Keep": 3}
    rows.sort(key=lambda r: (order[r["bucket"]], r["file"]))
    return {
        "meta": {
            "memory_dir": str(mem_dir), "files": len(files),
            "index_entries": len(index_lines), "index_nonblank_lines": index_total,
            "bytes": sum(f["bytes"] for f in files),
            "read_telemetry_days": round(coverage, 1), "reads_total": len(reads),
            "read_based_retire_enabled": reads_ok,
        },
        "rows": rows,
    }


def render(result: dict) -> str:
    m = result["meta"]
    rows = result["rows"]
    out = [
        f"MEMORY AUDIT  {m['memory_dir']}",
        f"store: {m['files']} files, {m['bytes'] // 1024} KB; MEMORY.md: {m['index_entries']} "
        f"index entries on {m['index_nonblank_lines']} non-blank lines "
        f"({m['files'] - m['index_entries']:+d} files vs entries)",
        f"read telemetry: {m['reads_total']} read(s) over {m['read_telemetry_days']} day(s)",
    ]
    if not m["read_based_retire_enabled"]:
        out.append(f"  NOTE: under {MIN_READ_COVERAGE_DAYS} days of read telemetry, so no "
                   "read-based Retire. 'never recorded' means not measured yet, not unused.")
    counts = Counter(r["bucket"] for r in rows)
    out.append("buckets: " + ", ".join(f"{b} {counts.get(b, 0)}" for b in ("Retire", "Merge", "Verify", "Keep")))
    for bucket in ("Retire", "Merge", "Verify"):
        group = [r for r in rows if r["bucket"] == bucket]
        if not group:
            continue
        out.append(f"\n{bucket.upper()}")
        for r in group:
            out.append(f"  {r['file']}: {r['reason']}")
            out.append(f"      {r['evidence']}")
    out.append(f"\nKEEP: {counts.get('Keep', 0)} memories")
    out.append("\nNothing was changed. /comd_system-dev decides; merging means reading both "
               "files and keeping the newer truth, never deleting the longer one.")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memory-dir", type=Path)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)
    mem_dir = args.memory_dir or default_memory_dir()
    if not mem_dir.is_dir():
        print(f"memory store not found: {mem_dir}", file=sys.stderr)
        return 1
    result = audit(mem_dir)
    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
