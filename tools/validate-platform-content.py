#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Platform (unpauseai.com) content standards validator.

Walks the public-facing surfaces of `platform/` and reports drift from
rule_platform_standards.md. Designed to be runnable both manually and
as a deploy gate.

Usage:
    uv run tools/validate-platform-content.py            # full repo scan
    uv run tools/validate-platform-content.py PATH ...   # scan specific files
    uv run tools/validate-platform-content.py --format json
    uv run tools/validate-platform-content.py --severity HIGH   # filter

Exit codes:
    0 = no HIGH findings (warnings may still be reported)
    1 = at least one HIGH finding
    2 = usage error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent.parent
PLATFORM = REPO / "platform" / "src"

PUBLIC_APP = PLATFORM / "app" / "(public)"
PROPOSALS = PLATFORM / "content" / "proposals"
# Blog markdown renders public at /blog/[slug]; before 2026-07-22 it was the
# one public content surface the validator never scanned (the corpus build
# would have shipped un-gated against the house voice standard).
BLOG = PLATFORM / "content" / "blog"
COMPONENTS = PLATFORM / "components"
EMAIL_LIB = PLATFORM / "lib" / "email.ts"
LAYOUT = PLATFORM / "app" / "layout.tsx"

# ---- Banned vocabulary ----

CORPORATE_THESAURUS = [
    "robust", "leverage", "ensure", "facilitate", "comprehensive",
    "streamline", "optimize", "holistic", "unlock",
]
# Phrases require word-boundary handling on the full pattern.
META_PHRASES = [
    r"it's important to note",
    r"keep in mind",
    r"worth mentioning",
    r"in summary",
    r"in conclusion",
    r"to summarize",
    r"not just [\w ]+ but",
]
DRIVE_PATTERN = re.compile(r"\bdrive (results|value|growth)\b", re.IGNORECASE)

# Brand typos. Order matters: more specific first.
BRAND_TYPOS = [
    (re.compile(r"\bUnpausAI\b"), "UnpauseAI (e-dropped typo)"),
    (re.compile(r"\bUnpauseai\b"), "UnpauseAI (lowercase a)"),
    (re.compile(r"\bUnPauseAI\b"), "UnpauseAI (extra cap)"),
    (re.compile(r"\bUnpause AI\b"), "UnpauseAI (space)"),
]

# Heading drift in proposal markdowns.
HEADING_FIXES = {
    "## Timeline": "## Timeline & Milestones",
    "## Timeline and Milestones": "## Timeline & Milestones",
    "## Proposed Solution": "## Our Proposed Solution",
    "## What We're Proposing": "## Our Proposed Solution",
    "## About UnpausAI": "## About UnpauseAI",
}
# These section titles are valid for the Track 1/2 proposal family.
TRACK_FAMILY_HEADINGS = {
    "## Centerpiece", "## Track", "## Compensation", "## Pages",
    "## Downloadable artifact", "## Next steps",
}

EM_DASH = "—"
EM_DASH_ENT = "&mdash;"
DD_SUBSTITUTE = re.compile(r" -- ")  # space, two hyphens, space

# A leading `*` is a block-comment continuation (` * foo`) only in JS/TS source.
# In markdown it opens a bullet (`* item`) or a bold run (`**Lead** ...`), both
# of which render, so the comment skip must not apply there.
JS_FAMILY_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

# Permitted em-dash patterns (placeholders in tables; metadata titles for admin).
EM_DASH_PLACEHOLDER = re.compile(r'\?\?\s*"' + EM_DASH + r'"|<span[^>]*>' + EM_DASH + r"</span>")


@dataclass
class Finding:
    file: str
    line: int
    severity: str  # HIGH | MEDIUM | LOW
    rule: str
    text: str  # short context excerpt

    def render(self) -> str:
        return f"  {self.severity:<6} {self.file}:{self.line}  [{self.rule}] {self.text}"


# ---- scope detection ----

def is_in_scope(path: Path) -> bool:
    """Return True if the file is on a public-facing surface."""
    try:
        rel = path.resolve().relative_to(PLATFORM)
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    # app/(public)/**
    if parts[0] == "app" and len(parts) > 1 and parts[1] == "(public)":
        return True
    # content/proposals/** and content/blog/**
    if parts[0] == "content" and len(parts) > 1 and parts[1] in {"proposals", "blog"}:
        return True
    # components/Header.tsx, Footer.tsx, proposal/**
    if parts[0] == "components":
        if len(parts) >= 2 and parts[1] in {"Header.tsx", "Footer.tsx", "Logo.tsx"}:
            return True
        if len(parts) >= 2 and parts[1] == "proposal":
            return True
    # public-rendered email surfaces
    if rel == Path("lib/email.ts"):
        return True
    if rel == Path("app/layout.tsx"):
        return True
    return False


def is_admin_or_portal(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(PLATFORM)
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 2 and parts[0] == "app" and parts[1] in {"admin", "portal"}


# ---- collectors ----

def iter_target_files(explicit: list[Path] | None) -> Iterable[Path]:
    if explicit:
        for p in explicit:
            if p.is_file():
                yield p
        return
    # Default scan: all in-scope files.
    for sub in (PUBLIC_APP, PROPOSALS, BLOG):
        if sub.exists():
            for ext in ("*.tsx", "*.ts", "*.md", "*.mdx", "*.txt"):
                for p in sub.rglob(ext):
                    yield p
    if COMPONENTS.exists():
        for name in ("Header.tsx", "Footer.tsx", "Logo.tsx"):
            p = COMPONENTS / name
            if p.is_file():
                yield p
        prop_dir = COMPONENTS / "proposal"
        if prop_dir.exists():
            for p in prop_dir.rglob("*.tsx"):
                yield p
    if EMAIL_LIB.is_file():
        yield EMAIL_LIB
    if LAYOUT.is_file():
        yield LAYOUT


# ---- checks ----

def check_em_dashes(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    admin_or_portal = is_admin_or_portal(path)
    js_family = path.suffix.lower() in JS_FAMILY_SUFFIXES
    for i, line in enumerate(lines, 1):
        # Skip JS/TS comments and JSX comments; they don't render.
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        # Block-comment continuation lines, JS/TS source only. Applying this
        # to markdown silently exempted every bullet and every bold-lead line.
        if js_family and stripped.startswith("*"):
            continue
        # Markdown YAML frontmatter does render (slugs, project_title used in metadata).
        # Check raw line for em-dash variants.
        excerpt = line.rstrip("\n")[:200]
        if EM_DASH in line:
            if admin_or_portal and EM_DASH_PLACEHOLDER.search(line):
                continue
            findings.append(Finding(
                file=str(path), line=i, severity="HIGH",
                rule="em-dash:unicode", text=excerpt,
            ))
        if EM_DASH_ENT in line:
            findings.append(Finding(
                file=str(path), line=i, severity="HIGH",
                rule="em-dash:entity", text=excerpt,
            ))
        if DD_SUBSTITUTE.search(line):
            findings.append(Finding(
                file=str(path), line=i, severity="HIGH",
                rule="em-dash:dd-substitute", text=excerpt,
            ))
    return findings


def check_brand_spelling(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(lines, 1):
        for pat, label in BRAND_TYPOS:
            if pat.search(line):
                findings.append(Finding(
                    file=str(path), line=i, severity="HIGH",
                    rule=f"brand:{label}", text=line.rstrip("\n")[:200],
                ))
    return findings


def check_banned_vocab(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(lines, 1):
        # Skip code-fence-like lines (rough heuristic for .md).
        if line.lstrip().startswith("```"):
            continue
        low = line.lower()
        for word in CORPORATE_THESAURUS:
            # Word boundary search.
            if re.search(rf"\b{word}\b", low):
                # Allow inside a markdown blockquote (lifted from source posting).
                if line.lstrip().startswith(">"):
                    continue
                # Allow inside a quoted string within a "research:" block
                # (frontmatter quotes from job postings).
                if re.search(rf'"[^"]*\b{word}\b[^"]*"', line):
                    # likely a citation of the posting in research notes
                    findings.append(Finding(
                        file=str(path), line=i, severity="LOW",
                        rule=f"banned-word:{word}", text=line.rstrip("\n")[:200] + "  (quoted — review)",
                    ))
                    continue
                findings.append(Finding(
                    file=str(path), line=i, severity="MEDIUM",
                    rule=f"banned-word:{word}", text=line.rstrip("\n")[:200],
                ))
        for phrase_re in META_PHRASES:
            if re.search(phrase_re, low):
                findings.append(Finding(
                    file=str(path), line=i, severity="MEDIUM",
                    rule="banned-phrase", text=line.rstrip("\n")[:200],
                ))
        if DRIVE_PATTERN.search(line):
            findings.append(Finding(
                file=str(path), line=i, severity="MEDIUM",
                rule="banned-phrase:drive", text=line.rstrip("\n")[:200],
            ))
    return findings


def check_proposal_headings(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    if path.suffix.lower() not in {".md", ".mdx"}:
        return findings
    # The canonical-heading contract is proposal-specific (rule_platform_standards
    # §3). A blog post may legitimately carry "## Timeline"; only proposals drift.
    try:
        path.resolve().relative_to(PROPOSALS)
    except ValueError:
        return findings
    # Skip Track-family proposals (heading vocabulary differs).
    text = "".join(lines)
    is_track_family = any(h in text for h in TRACK_FAMILY_HEADINGS)
    if is_track_family:
        return findings
    for i, line in enumerate(lines, 1):
        for bad, good in HEADING_FIXES.items():
            if line.strip() == bad:
                findings.append(Finding(
                    file=str(path), line=i, severity="MEDIUM",
                    rule="heading-drift", text=f"{bad}  ->  {good}",
                ))
    return findings


def check_email_consistency(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    # Flag any unpauseai.com address that isn't one of the sanctioned trio:
    #   nicolas.neumann@unpauseai.com (public contact)
    #   no-reply@unpauseai.com (transactional from)
    #   onboarding@resend.dev (resend technical fallback)
    SANCTIONED = {
        "admin@unpauseai.com",
        "no-reply@unpauseai.com",
        "onboarding@resend.dev",
    }
    addr_re = re.compile(r"([\w.+-]+@unpauseai\.com)", re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        for m in addr_re.finditer(line):
            addr = m.group(1).lower()
            if addr in SANCTIONED:
                continue
            findings.append(Finding(
                file=str(path), line=i, severity="HIGH",
                rule="email:unsanctioned", text=line.rstrip("\n")[:200],
            ))
    return findings


def check_dead_links(public_jsx_files: list[Path]) -> list[Finding]:
    """Find <Link href="/foo"> targets that don't exist in app/(public)."""
    findings: list[Finding] = []
    if not PUBLIC_APP.exists():
        return findings
    # Enumerate available routes.
    available: set[str] = set()
    available.add("/")
    for p in PUBLIC_APP.rglob("page.tsx"):
        rel = p.parent.relative_to(PUBLIC_APP)
        if str(rel) == ".":
            continue
        # Strip dynamic segments like [slug] for the existence check; we just
        # want to know that the route family exists.
        parts = []
        for part in rel.parts:
            if part.startswith("[") and part.endswith("]"):
                parts.append("*")
            else:
                parts.append(part)
        available.add("/" + "/".join(parts))
    # Also assume top-level admin/portal/login/assessment routes are valid.
    available.update({"/admin", "/portal", "/login", "/auth"})

    link_re = re.compile(r'href=["\'](/[^"\'#?]+)["\']')
    for p in public_jsx_files:
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in link_re.finditer(line):
                target = m.group(1).rstrip("/")
                if not target:
                    target = "/"
                # Normalize: collapse dynamic-segment placeholders.
                norm = target
                # Quick lookup: exact match or prefix in available routes.
                if norm in available or norm + "/" in available:
                    continue
                # Try walking up: a target like /proposals/foo should match /proposals/*.
                hit = False
                head = norm
                while "/" in head:
                    head = head.rsplit("/", 1)[0] or "/"
                    if head + "/*" in available or head in available:
                        hit = True
                        break
                if hit:
                    continue
                findings.append(Finding(
                    file=str(p), line=i, severity="HIGH",
                    rule="dead-link", text=f'href="{target}"  (no matching app/(public) route)',
                ))
    return findings


# ---- runner ----

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="Specific files to check (default: full repo scan)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--severity", choices=("HIGH", "MEDIUM", "LOW"), default=None,
                    help="Only report at this severity or higher")
    args = ap.parse_args()

    explicit = [Path(p) for p in args.paths] if args.paths else None
    files: list[Path] = []
    public_jsx_files: list[Path] = []
    for p in iter_target_files(explicit):
        if not is_in_scope(p):
            continue
        files.append(p)
        if p.suffix in {".tsx", ".ts"} and "(public)" in str(p):
            public_jsx_files.append(p)
        if p.name in {"Header.tsx", "Footer.tsx"}:
            public_jsx_files.append(p)

    all_findings: list[Finding] = []
    for p in files:
        try:
            lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
        all_findings.extend(check_em_dashes(p, lines))
        all_findings.extend(check_brand_spelling(p, lines))
        all_findings.extend(check_banned_vocab(p, lines))
        all_findings.extend(check_proposal_headings(p, lines))
        all_findings.extend(check_email_consistency(p, lines))
    all_findings.extend(check_dead_links(public_jsx_files))

    severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    threshold = severity_rank.get(args.severity or "LOW", 1)
    filtered = [f for f in all_findings if severity_rank[f.severity] >= threshold]

    if args.format == "json":
        print(json.dumps({
            "scanned": len(files),
            "total_findings": len(all_findings),
            "filtered_findings": len(filtered),
            "findings": [asdict(f) for f in filtered],
        }, indent=2))
    else:
        # Group by file for readability.
        by_file: dict[str, list[Finding]] = {}
        for f in filtered:
            by_file.setdefault(f.file, []).append(f)
        if not by_file:
            print(f"OK: {len(files)} files scanned, 0 findings at or above"
                  f" {args.severity or 'LOW'}.")
        else:
            print(f"validate-platform-content.py: {len(files)} files scanned,"
                  f" {len(filtered)} findings.\n")
            for fname, items in sorted(by_file.items()):
                print(f"{fname}")
                for it in items:
                    print(f"  {it.severity:<6} L{it.line:<5} [{it.rule}]")
                    print(f"           {it.text}")
                print()
            highs = sum(1 for f in filtered if f.severity == "HIGH")
            meds = sum(1 for f in filtered if f.severity == "MEDIUM")
            lows = sum(1 for f in filtered if f.severity == "LOW")
            print(f"Summary: {highs} HIGH, {meds} MEDIUM, {lows} LOW")

    high_count = sum(1 for f in all_findings if f.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
