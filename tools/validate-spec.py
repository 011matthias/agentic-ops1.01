# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""validate-spec.py — frontmatter + stage/folder check for a single spec file.

Why this exists
---------------
CLAUDE.md lists required spec frontmatter (id, name, type, stage, orchestrator,
version, created, updated, trigger, systems, last_changes, next_steps).
skil_spec-cleanup audits this on demand. There's no gate between the moment a
spec is written and the audit -- a malformed spec exists in the codebase until
someone runs cleanup. This tool is the per-file shape of the audit so the
post-write-gate can run it on every spec write.

Checks
------
  1) frontmatter present + parseable
  2) every required key present
  3) `stage:` value matches the folder (`stage: build` -> `2-build/`)
  4) `needs_fixes:` true marker surfaces as MEDIUM (signal, not block)

JSON contract matches the rest of validate-*: {total, hits[], by_category,
by_severity}. Hook reads JSON; exit 0 either way.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_KEYS = {
    "id", "name", "type", "stage", "orchestrator", "version",
    "created", "updated", "trigger", "systems", "last_changes", "next_steps",
}
STAGE_TO_FOLDER = {
    "spec": "1-spec",
    "build": "2-build",
    "test": "3-test",
    "live": "4-live",
    "deprecated": "_archive",
}
VALID_STAGES = set(STAGE_TO_FOLDER.keys())


def parse_frontmatter(text: str) -> tuple[dict, bool]:
    if not text.startswith("---"):
        return {}, False
    end = text.find("\n---", 4)
    if end < 0:
        return {}, False
    fm: dict = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            fm[key] = val
    return fm, True


def folder_from_path(p: Path) -> str | None:
    """Return the stage-folder segment from a spec path
    (e.g. 1-spec / 2-build / 3-test / 4-live / _archive), or None if the
    file isn't under one of those."""
    parts = p.as_posix().split("/")
    for part in parts:
        if part in {"1-spec", "2-build", "3-test", "4-live", "_archive", "_checklists"}:
            return part
    return None


def check(path: Path) -> dict:
    hits: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"total": 0, "hits": [], "by_category": {}, "by_severity": {}}

    fm, had_fm = parse_frontmatter(text)
    folder = folder_from_path(path)

    # Skip non-spec adjuncts that happen to live in spec/ dirs.
    if path.name == "README.md" or folder in {"_checklists", "_archive"}:
        return {"total": 0, "hits": [], "by_category": {}, "by_severity": {}}

    if folder is None:
        # Not in a recognized stage folder -> nothing to validate here.
        return {"total": 0, "hits": [], "by_category": {}, "by_severity": {}}

    if not had_fm:
        hits.append({
            "line": 1, "category": "spec-frontmatter-missing", "severity": "HIGH",
            "message": "Spec has no YAML frontmatter. Required: " + ", ".join(sorted(REQUIRED_KEYS)),
            "snippet": path.name,
        })
    else:
        missing = REQUIRED_KEYS - set(fm.keys())
        if missing:
            hits.append({
                "line": 1, "category": "spec-frontmatter-incomplete", "severity": "HIGH",
                "message": "Missing required frontmatter keys: " + ", ".join(sorted(missing)),
                "snippet": "frontmatter",
            })
        stage = fm.get("stage", "").strip().strip('"').strip("'").lower()
        if stage and stage not in VALID_STAGES:
            hits.append({
                "line": 1, "category": "spec-stage-invalid", "severity": "MEDIUM",
                "message": f"`stage: {stage}` is not one of {sorted(VALID_STAGES)}",
                "snippet": f"stage: {stage}",
            })
        elif stage:
            expected = STAGE_TO_FOLDER[stage]
            if folder != expected:
                hits.append({
                    "line": 1, "category": "spec-stage-folder-mismatch", "severity": "HIGH",
                    "message": (
                        f"`stage: {stage}` but file is in `{folder}/`. "
                        f"Either move the file to `{expected}/` or update `stage:` to match the folder."
                    ),
                    "snippet": f"folder={folder} stage={stage}",
                })
        if str(fm.get("needs_fixes", "")).lower() == "true":
            hits.append({
                "line": 1, "category": "spec-needs-fixes", "severity": "MEDIUM",
                "message": "Spec is flagged needs_fixes: true — bug or gap is open.",
                "snippet": "needs_fixes: true",
            })

    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for h in hits:
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
        by_sev[h["severity"]] = by_sev.get(h["severity"], 0) + 1
    return {"total": len(hits), "hits": hits, "by_category": by_cat, "by_severity": by_sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()
    p = Path(args.file)
    if not p.exists():
        print(f"ERROR: not found: {p}", file=sys.stderr)
        return 2
    payload = check(p)
    if args.format == "json":
        print(json.dumps(payload))
        return 0
    if payload["total"] == 0:
        print(f"OK: {p}")
        return 0
    print(f"\n## {p}")
    print(f"  Total: {payload['total']}")
    for h in payload["hits"]:
        print(f"  L{h['line']:4d}  [{h['severity']}] [{h['category']}] {h['message']}")
        print(f"        -> {h['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
