# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check-skill-map.py — skill routing tables vs reality.

A modular skill (SKILL.md spine + modules/ + references/ + components/) routes
by file path. A dead pointer means the agent loads the wrong module — or no
module — mid-build, invisible until a deliverable ships missing a gate. This
is the same failure class check-index.py kills for tools/, applied to the
skill layer (drift-check pattern from googleworkspace/cli, adopted 2026-06-11).

Three checks per skill:
  1. forward  — every backtick path named in the skill's .md files resolves
                (relative to the skill dir, the repo root, or the local-web
                project root). Placeholdered paths ({slug}, *, …) are skipped.
  2. reverse  — every modules/ references/ components/ *.md under the skill
                dir is referenced by name at least once in SKILL.md.
  3. rule IDs — every `<!-- rule:... -->` anchor is unique across the skill
                (one home per rule; a duplicate ID is documented drift).

Usage:
  uv run tools/check-skill-map.py                       # all .claude/skills/*
  uv run tools/check-skill-map.py PATH [...]            # skill(s) owning PATH(s)
  uv run tools/check-skill-map.py --format json         # post-write-gate contract

Exit 0 clean, 1 with findings, 2 on usage/env error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / ".claude" / "skills"
RESOLUTION_ROOTS = [REPO, REPO / "workspace" / "projects" / "local-web"]

BACKTICK = re.compile(r"`([^`\n]+)`")
RULE_ID = re.compile(r"<!--\s*rule:([a-z0-9-]+)\s*-->")
PLACEHOLDER = re.compile(r"[{}*<>$|]|\.\.\.|…")
PATH_SUFFIXES = (".md", ".py", ".cjs", ".mjs", ".sh", ".css", ".astro", ".yaml", ".yml", ".json", ".toml")
SKILL_DIRS = ("modules", "references", "components")
# Namespaces that resolve per-client / per-project at runtime (workspace/
# clients/{client}/context/... etc.) or against a user's home — conventions,
# not repo paths. Validating them would be all false positives.
SKIP_PREFIXES = ("context/", "handover/", "docs/client/", "app/", "src/",
                 ".agents/", "~", "prospects/", "node_modules/")
# Default scan scope is first-party skills only: vendored third-party skills
# (marketing pack etc.) follow their own internal conventions.
FIRST_PARTY_PREFIX = "skil_"


def looks_like_path(s: str) -> bool:
    s = s.strip()
    if not s or " " in s or s.startswith(("http", "--", "-", "/")):
        return False
    if s.startswith(SKIP_PREFIXES):
        return False
    if PLACEHOLDER.search(s):
        return False
    return "/" in s and s.lower().endswith(PATH_SUFFIXES)


def skill_md_files(skill_dir: Path) -> list[Path]:
    return sorted(p for p in skill_dir.rglob("*.md") if p.is_file())


def audit_skill(skill_dir: Path) -> list[dict]:
    hits: list[dict] = []
    spine = skill_dir / "SKILL.md"
    spine_text = spine.read_text(encoding="utf-8") if spine.is_file() else ""
    if not spine_text:
        return [{"line": 0, "category": "no-spine", "severity": "HIGH",
                 "message": f"{skill_dir.name}: no SKILL.md", "snippet": str(skill_dir)}]

    # 1. forward: named paths resolve
    for md in skill_md_files(skill_dir):
        text = md.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for cand in BACKTICK.findall(line):
                cand = cand.strip()
                if not looks_like_path(cand):
                    continue
                roots = [md.parent, skill_dir, *RESOLUTION_ROOTS]
                if not any((r / cand).exists() for r in roots):
                    hits.append({
                        "line": i, "category": "dead-pointer", "severity": "HIGH",
                        "message": f"{md.relative_to(skill_dir)}: `{cand}` resolves nowhere",
                        "snippet": line.strip()[:120],
                    })

    # 2. reverse: every module/reference/component reachable from the spine
    for sub in SKILL_DIRS:
        for f in sorted((skill_dir / sub).glob("*.md")) if (skill_dir / sub).is_dir() else []:
            if f.name not in spine_text:
                hits.append({
                    "line": 0, "category": "unreachable-module", "severity": "MEDIUM",
                    "message": f"{sub}/{f.name} exists but SKILL.md never references it",
                    "snippet": f"{skill_dir.name}/{sub}/{f.name}",
                })

    # 3. rule-ID uniqueness across the skill (one home per rule)
    seen: dict[str, str] = {}
    for md in skill_md_files(skill_dir):
        for rid in RULE_ID.findall(md.read_text(encoding="utf-8")):
            rel = str(md.relative_to(skill_dir))
            if rid in seen and seen[rid] != rel:
                hits.append({
                    "line": 0, "category": "duplicate-rule-id", "severity": "HIGH",
                    "message": f"rule:{rid} anchored in BOTH {seen[rid]} and {rel} (one home per rule)",
                    "snippet": rid,
                })
            seen.setdefault(rid, rel)
    return hits


def owning_skill(path: Path) -> Path | None:
    try:
        rel = path.resolve().relative_to(SKILLS.resolve())
    except ValueError:
        return None
    return SKILLS / rel.parts[0] if rel.parts else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="file(s) under a skill dir; default = all skills")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    if not SKILLS.is_dir():
        print(f"no skills dir at {SKILLS}", file=sys.stderr)
        return 2

    if args.paths:
        skill_dirs = sorted({s for p in args.paths if (s := owning_skill(Path(p)))})
        if not skill_dirs:
            # path outside .claude/skills — out of scope, clean exit
            if args.format == "json":
                json.dump({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}, sys.stdout)
            return 0
    else:
        skill_dirs = sorted(p for p in SKILLS.iterdir()
                            if p.is_dir() and p.name.startswith(FIRST_PARTY_PREFIX))

    hits: list[dict] = []
    for sd in skill_dirs:
        hits += audit_skill(sd)

    if args.format == "json":
        by_cat: dict[str, int] = {}
        by_sev: dict[str, int] = {}
        for h in hits:
            by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
            by_sev[h["severity"]] = by_sev.get(h["severity"], 0) + 1
        json.dump({"total": len(hits), "hits": hits, "by_category": by_cat,
                   "by_severity": by_sev}, sys.stdout)
    else:
        if hits:
            print(f"[check-skill-map] {len(hits)} finding(s) across {len(skill_dirs)} skill(s):")
            for h in hits:
                print(f"  [{h['severity']}] [{h['category']}] {h['message']}")
        else:
            print(f"[check-skill-map] OK: {len(skill_dirs)} skill(s), no dead pointers, "
                  f"no unreachable modules, no duplicate rule IDs")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
