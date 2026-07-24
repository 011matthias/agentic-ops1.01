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
  1. forward  — every backtick path AND every markdown-link target
                (`[text](../x/Y.md)`) named in the skill's .md files resolves
                (relative to the containing file's dir, the skill dir, the repo
                root, or the local-web project root). Placeholdered paths
                ({slug}, *, …) are skipped.
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
# Inline markdown links + images: `[text](target)` / `![alt](target)`, with an
# optional <…> wrapper and an optional "title" after the target. Reference-style
# links (`[text][ref]`) are not inline pointers and are out of scope.
MD_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>\n]*>|[^)\s]+)")
RULE_ID = re.compile(r"<!--\s*rule:([a-z0-9-]+)\s*-->")
PLACEHOLDER = re.compile(r"[{}*<>$|]|\.\.\.|…")
URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
PATH_SUFFIXES = (".md", ".py", ".cjs", ".mjs", ".sh", ".css", ".astro", ".yaml", ".yml", ".json", ".toml")
# Link targets may also point at shipped assets (a diagram in a skill's
# references/). A broken image is the same drift class as a broken module link,
# so image suffixes are checked too — they just never appear in backticks.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
SKILL_DIRS = ("modules", "references", "components")
# Namespaces that resolve per-client / per-project at runtime (workspace/
# clients/{client}/context/... etc.) or against a user's home — conventions,
# not repo paths. Validating them would be all false positives.
SKIP_PREFIXES = ("context/", "handover/", "docs/client/", "app/", "src/",
                 ".agents/", "~", "prospects/", "node_modules/")
# Default scan scope is first-party skills only: vendored third-party skills
# (marketing pack etc.) follow their own internal conventions.
FIRST_PARTY_PREFIX = "skil_"

# A consolidation pack (make-pack / n8n-pack / trigger-pack) routes into the
# modules of its stub skills via a cross-skill link (../make-mcp-tools-expert/
# modules/NAME.md). The stub's OWN SKILL.md does not name those modules, so the
# reverse check would false-positive without this. We collect every basename any
# spine references this way; a genuine orphan, referenced by no spine anywhere,
# still fires.
CROSS_SKILL_MODULE_REF = re.compile(r"/(?:modules|references|components)/([A-Za-z0-9._-]+\.md)")

# Vendored Claude Code guide docs (skil_meta-builder): documentation ABOUT how to
# build skills/hooks/plugins. Their backtick paths are illustrative examples
# (`@docs/file.md`, `commands/hello.md`, `foo/CLAUDE.md`), never repo pointers, so
# the forward check skips them. The reverse check still flags them if unwired.
EXAMPLE_PATH_DOCS = {
    "MEMORY-GUIDE.md", "PLUGINS-GUIDE.md", "SKILL-GUIDE.md", "HOOKS-GUIDE.md",
    "MCP-GUIDE.md", "SETTINGS-GUIDE.md", "OUTPUT-STYLES-GUIDE.md",
    "COMMAND-GUIDE.md", "AGENT-GUIDE.md", "DECISION-TREE.md",
}

# Repo paths a skill CREATES on demand rather than ships. They are genuine
# pointers (the skill reads and writes them by exactly this path), so weakening
# them into prose would lose signal; they simply do not exist at rest, so
# resolution is the wrong test. Keep this list tiny and literal: an entry here
# is a promise that some skill's documented procedure creates the file.
RUNTIME_CREATED = {
    ".claude/queue/pending.md",   # skil_prompt-queue creates on first drain/add
    ".claude/queue/done.md",      # skil_prompt-queue creates on first archive
}


def looks_like_path(s: str) -> bool:
    s = s.strip()
    # `@`-prefixed tokens are Claude import-syntax examples (`@docs/file.md`),
    # never a repo file on disk.
    if not s or " " in s or s.startswith(("http", "--", "-", "/", "@")):
        return False
    if s.startswith(SKIP_PREFIXES):
        return False
    if PLACEHOLDER.search(s):
        return False
    return "/" in s and s.lower().endswith(PATH_SUFFIXES)


def link_target_path(raw: str) -> str | None:
    """Normalize one markdown-link target to a repo-checkable relative path, or
    None when it is not a file pointer at all.

    Not pointers: external schemes (http:, https:, mailto:, tel:, …), pure
    anchors (`#section`), site-absolute targets (`/docs/x`), `@`-import
    examples, placeholdered paths, the runtime-namespace SKIP_PREFIXES, and
    anything without a known file suffix. Fragments and queries are stripped
    before resolution so `FILE.md#section` tests as `FILE.md`."""
    t = raw.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1].strip()
    if not t or t.startswith("#"):          # pure anchor — in-page, not a file
        return None
    if URL_SCHEME.match(t):                 # http/https/mailto/tel/data/…
        return None
    t = t.split("#", 1)[0].split("?", 1)[0]  # drop fragment + query
    if not t or t.startswith(("/", "@", "-")):
        return None
    if t.startswith(SKIP_PREFIXES) or PLACEHOLDER.search(t):
        return None
    return t if t.lower().endswith(PATH_SUFFIXES + IMAGE_SUFFIXES) else None


def line_pointers(line: str) -> list[tuple[str, bool]]:
    """Every file pointer on one line as (path, link_only), first-seen order,
    deduped.

    `link_only` is True for a markdown-link target and drives the stricter
    resolution base in audit_skill: a link has exactly ONE correct base, the
    containing file's directory, because that is what a reader following it
    actually gets. Backticked paths are prose and stay on the permissive root
    list (they are legitimately repo- or skill-dir-relative).

    A path that appears BOTH backticked and linked on one line (the idiomatic
    ``[`x/Y.md`](x/Y.md)``) is emitted once, as the backtick form, so the pair
    can never be reported twice."""
    out: list[tuple[str, bool]] = []
    seen: set[str] = set()
    cands = [(c.strip(), False) for c in BACKTICK.findall(line) if looks_like_path(c.strip())]
    cands += [(t, True) for raw in MD_LINK.findall(line) if (t := link_target_path(raw))]
    for c, link_only in cands:
        if c not in seen:
            seen.add(c)
            out.append((c, link_only))
    return out


def skill_md_files(skill_dir: Path) -> list[Path]:
    return sorted(p for p in skill_dir.rglob("*.md") if p.is_file())


def collect_cross_skill_refs(skill_dirs: list[Path]) -> set[str]:
    """Module/reference basenames any spine routes into via a cross-skill link
    (a pack -> its consolidation stub's modules, e.g. make-pack ->
    ../make-mcp-tools-expert/modules/NAME.md). Those modules are reachable even
    though the stub's own SKILL.md does not name them. A genuine orphan, which no
    spine references anywhere, is absent from this set and still fires."""
    referenced: set[str] = set()
    for sd in skill_dirs:
        spine = sd / "SKILL.md"
        if spine.is_file():
            referenced.update(CROSS_SKILL_MODULE_REF.findall(spine.read_text(encoding="utf-8")))
    return referenced


def audit_skill(skill_dir: Path, cross_skill_refs: frozenset[str] = frozenset()) -> list[dict]:
    hits: list[dict] = []
    spine = skill_dir / "SKILL.md"
    spine_text = spine.read_text(encoding="utf-8") if spine.is_file() else ""
    if not spine_text:
        return [{"line": 0, "category": "no-spine", "severity": "HIGH",
                 "message": f"{skill_dir.name}: no SKILL.md", "snippet": str(skill_dir)}]

    # 1. forward: named paths resolve. Illustrative examples are skipped (fenced
    # code blocks, `Example:` lines, and the vendored guide docs whose backtick
    # paths are documentation samples) so the gate flags real routing drift only.
    for md in skill_md_files(skill_dir):
        if skill_dir.name == "skil_meta-builder" and md.name in EXAMPLE_PATH_DOCS:
            continue
        text = md.read_text(encoding="utf-8")
        in_fence = False
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or "Example:" in line:
                continue
            for cand, link_only in line_pointers(line):
                if cand in RUNTIME_CREATED:
                    continue
                roots = [md.parent] if link_only else [md.parent, skill_dir, *RESOLUTION_ROOTS]
                if not any((r / cand).exists() for r in roots):
                    what = "link target" if link_only else "pointer"
                    hits.append({
                        "line": i, "category": "dead-pointer", "severity": "HIGH",
                        "message": f"{md.relative_to(skill_dir)}: {what} `{cand}` resolves nowhere",
                        "snippet": line.strip()[:120],
                    })

    # 2. reverse: every module/reference/component reachable from the spine OR
    # from a pack spine that consumes this skill's modules (cross_skill_refs).
    for sub in SKILL_DIRS:
        for f in sorted((skill_dir / sub).glob("*.md")) if (skill_dir / sub).is_dir() else []:
            if f.name not in spine_text and f.name not in cross_skill_refs:
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

    # Cross-skill module references are collected from ALL first-party spines (not
    # just the scanned subset) so a pack spine consuming a stub's modules is seen
    # even when scanning a single skill by path.
    all_first_party = sorted(p for p in SKILLS.iterdir()
                             if p.is_dir() and p.name.startswith(FIRST_PARTY_PREFIX))
    cross_skill_refs = frozenset(collect_cross_skill_refs(all_first_party))

    hits: list[dict] = []
    for sd in skill_dirs:
        hits += audit_skill(sd, cross_skill_refs)

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
