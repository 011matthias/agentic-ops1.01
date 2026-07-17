#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "cryptography"]
# ///
"""Banned-content scan for client-facing demo material.

The existing validators enforce banned LANGUAGE (em-dashes, AI-tells,
corporate thesaurus). Nothing enforced banned CONTENT that originates in a
client directive, because those directives live in Planner, not in a rule
file. Twice on 2026-07-09 a Brisken artifact reached the client naming SAP
BTP, against Dirk's standing "Exclude BTP from all demos" directive: first
the two TreasuryCentral decks linked to him on SharePoint, then a video end
card. Both were caught after delivery, by hand.

This reads what actually ships, not the source that produced it:

  * .pdf   -> extracted page text (the deck the client opens)
  * .pptx  -> ppt/slides/slideN.xml (catches hidden slides and speaker-visible
              text that never reaches the PDF)
  * .html / .md / .txt / .srt / .vtt -> raw text

Source files (.js, .py) are scanned too when passed explicitly, so a
generator can be checked before it is ever run.

Terms and per-path exemptions live in `tools/fixtures/demo-banned-terms.json`
so a new client directive is a data change, not a code change.

Exit 1 on any unexempted hit. Wire into the deploy/send path as a B2 gate.

Usage:
    uv run tools/validate-demo-material.py FILE [FILE ...]
    uv run tools/validate-demo-material.py --dir path/to/decks
    uv run tools/validate-demo-material.py --client brisken --dir .
    uv run tools/validate-demo-material.py --list-terms
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "tools" / "fixtures" / "demo-banned-terms.json"

TEXT_SUFFIXES = {".html", ".htm", ".md", ".txt", ".srt", ".vtt", ".js", ".py", ".json"}
SLIDE_XML = re.compile(r"ppt/slides/slide\d+\.xml$")
SCAN_SUFFIXES = TEXT_SUFFIXES | {".pdf", ".pptx"}


@dataclass
class Hit:
    path: Path
    where: str
    term: str
    context: str
    line: int = 0  # 1-based for text files; 0 when only page/slide is known


def load_config() -> dict:
    if not CONFIG.exists():
        sys.exit(f"missing config: {CONFIG}")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def rules_for(cfg: dict, client: str | None) -> tuple[list[dict], list[dict]]:
    """Return (terms, exemptions), merging the shared set with a client's."""
    terms = list(cfg.get("shared", {}).get("terms", []))
    exempt = list(cfg.get("shared", {}).get("exempt", []))
    if client:
        block = cfg.get("clients", {}).get(client)
        if block is None:
            sys.exit(f"unknown client '{client}'. known: {sorted(cfg.get('clients', {}))}")
        terms += block.get("terms", [])
        exempt += block.get("exempt", [])
    else:
        for block in cfg.get("clients", {}).values():
            terms += block.get("terms", [])
            exempt += block.get("exempt", [])
    return terms, exempt


def pdf_segments(path: Path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages, 1):
        yield f"page {i}", page.extract_text() or ""


def pptx_segments(path: Path):
    with zipfile.ZipFile(path) as z:
        names = sorted(
            (n for n in z.namelist() if SLIDE_XML.match(n)),
            key=lambda n: int(re.search(r"slide(\d+)\.xml$", n).group(1)),
        )
        for n in names:
            xml = z.read(n).decode("utf8", "ignore")
            # join <a:t> runs so a term split across runs is still found
            text = " ".join(re.findall(r"<a:t>(.*?)</a:t>", xml, re.S))
            num = re.search(r"slide(\d+)\.xml$", n).group(1)
            yield f"slide {num}", text


def text_segments(path: Path):
    yield "text", path.read_text(encoding="utf-8", errors="ignore")


def segments(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_segments(path)
    if suffix == ".pptx":
        return pptx_segments(path)
    return text_segments(path)


def is_exempt(path: Path, term: str, exemptions: list[dict]) -> str | None:
    """An exemption matches on path glob plus term. term "*" exempts every term."""
    rel = path.as_posix()
    for ex in exemptions:
        want = ex["term"]
        if want != "*" and want.lower() != term.lower():
            continue
        if fnmatch.fnmatch(rel, ex["path"]) or fnmatch.fnmatch(path.name, ex["path"]):
            return ex.get("reason", "exempt")
    return None


def scan(path: Path, terms: list[dict], exemptions: list[dict]) -> tuple[list[Hit], list[str]]:
    hits: list[Hit] = []
    skipped: list[str] = []
    try:
        for where, text in segments(path):
            if not text:
                continue
            for entry in terms:
                term = entry["term"]
                pattern = entry.get("pattern") or rf"\b{re.escape(term)}\b"
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    reason = is_exempt(path, term, exemptions)
                    if reason:
                        skipped.append(f"{path.name} [{where}] '{term}' exempt: {reason}")
                        continue
                    lo, hi = max(0, m.start() - 45), min(len(text), m.end() + 45)
                    ctx = " ".join(text[lo:hi].split())
                    line = text.count("\n", 0, m.start()) + 1 if where == "text" else 0
                    hits.append(Hit(path, where, term, ctx, line))
    except Exception as exc:  # unreadable/corrupt file is a finding, not a crash
        # A file exempted for every term ("*") is out of scope entirely, so an
        # unreadable one is noise, not a finding. Term-specific exemptions still fail.
        reason = is_exempt(path, "*", exemptions)
        if reason:
            skipped.append(f"{path.name} [read] unreadable, exempt: {reason}")
        else:
            hits.append(Hit(path, "read", "<unreadable>", f"{type(exc).__name__}: {exc}"))
    return hits, skipped


def collect(paths: list[str], as_dir: bool) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if as_dir or p.is_dir():
            out += [f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in SCAN_SUFFIXES]
        elif p.is_file():
            out.append(p)
        else:
            sys.exit(f"not found: {p}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files or directories to scan")
    ap.add_argument("--dir", action="store_true", help="treat every path as a directory to walk")
    ap.add_argument("--client", help="restrict to one client's directives (default: all)")
    ap.add_argument("--list-terms", action="store_true", help="print the active banned terms and exit")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    ap.add_argument("--format", choices=("text", "json"), default="text",
                    help="json emits the post-write-gate dispatcher contract (see tools/INDEX.md)")
    args = ap.parse_args()

    cfg = load_config()
    terms, exemptions = rules_for(cfg, args.client)

    if args.list_terms:
        for entry in terms:
            print(f"{entry['term']:<38} {entry.get('source', '')}")
        return 0

    if not args.paths:
        ap.error("no paths given")

    files = collect(args.paths, args.dir)
    if not files:
        print("no scannable files found")
        return 0

    all_hits: list[Hit] = []
    all_skipped: list[str] = []
    for f in files:
        hits, skipped = scan(f, terms, exemptions)
        all_hits += hits
        all_skipped += skipped

    if args.format == "json":
        payload = {
            "total": len(all_hits),
            "hits": [
                {
                    "line": h.line,
                    "category": "banned-content",
                    "severity": "HIGH",
                    "message": f"banned term '{h.term}' ({h.where}); client directive, "
                               "see tools/fixtures/demo-banned-terms.json",
                    "snippet": h.context,
                }
                for h in all_hits
            ],
            "by_category": {"banned-content": len(all_hits)} if all_hits else {},
            "by_severity": {"HIGH": len(all_hits)} if all_hits else {},
        }
        print(json.dumps(payload))
        return 1 if all_hits else 0

    if not args.quiet:
        print(f"scanned {len(files)} file(s) against {len(terms)} banned term(s)")
        for line in all_skipped:
            print(f"  exempt  {line}")

    if all_hits:
        print(f"\nFAIL: {len(all_hits)} banned-content hit(s)\n")
        for h in all_hits:
            try:
                shown = h.path.relative_to(REPO)
            except ValueError:
                shown = h.path
            print(f"  {shown}")
            print(f"    {h.where}: '{h.term}'")
            print(f"    ...{h.context}...")
        print("\nThese ship to the client. Fix the artifact, or add a justified")
        print(f"exemption to {CONFIG.relative_to(REPO)}.")
        return 1

    if not args.quiet:
        print("PASS: no banned content")
    return 0


if __name__ == "__main__":
    sys.exit(main())
