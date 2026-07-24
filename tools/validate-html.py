#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Structural validation for self-contained HTML deliverables.

Catches structural failures that don't show up in a browser quick-check
but break in production:

  * Unclosed tags (basic balance check)
  * Duplicate IDs (breaks anchor links and JS lookups)
  * Missing <title>, charset, viewport
  * External resources without integrity (security risk for client deliverables)
  * Artefact weight vs origin/main (WARNING when a file grew >20% AND >10 KB
    vs its committed version; catches silently duplicated embedded assets,
    e.g. the 2026-07-22 PDF regen that doubled a 92KB logo blob per page)
  * Cross-page consistency (in --dir mode, recursive over the tree):
      - All pages reference the same set of sibling pages
      - All pages share the same theme-toggle and search wiring
      - Inter-page links all use absolute paths (Vercel cleanUrls fix)

Per rule_behaviors.md "HTML structural validation": "Before deploying any
self-contained HTML, run uv run tools/validate-html.py {files}. Fix all
failures before deploy. For multi-page sets, run in directory mode to
check cross-page consistency. This is a B2 gate extension."

Usage:
    uv run tools/validate-html.py FILE.html
    uv run tools/validate-html.py --dir path/to/pages/
    uv run tools/validate-html.py FILE.html --format json

Exit 0 = pass. Exit 1 = structural failure. Exit 2 = usage error.
WARNING-severity findings (artefact-weight) are reported but never fail.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# [artefact-weight] growth thresholds vs the committed origin/main version.
# Both must trip: relative growth >20% AND absolute growth >10 KB (the
# absolute floor keeps tiny files from warning on trivial edits).
WEIGHT_RATIO = 1.20
WEIGHT_ABS_FLOOR = 10 * 1024

# Any RFC-3986 scheme prefix (http:, https:, mailto:, tel:, data:, ...).
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

# Cross-page wiring probes (--dir mode). Mirror validate-deliverable.py's
# per-page QoL patterns: a page "has" a feature when ALL patterns in the
# tuple match somewhere in the file.
THEME_WIRING = (re.compile(r"data-theme", re.IGNORECASE),
                re.compile(r"localStorage", re.IGNORECASE))
SEARCH_WIRING = (re.compile(r"metaKey|ctrlKey", re.IGNORECASE),
                 re.compile(r"['\"]k['\"]|KeyK", re.IGNORECASE))


class StructuralChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, int]] = []
        self.unclosed: list[tuple[str, int]] = []
        self.unexpected_close: list[tuple[str, int]] = []
        self.ids: dict[str, list[int]] = {}
        self.has_title = False
        self.has_charset = False
        self.has_viewport = False
        self.in_title = False
        self.title_text = ""
        self.external_scripts: list[tuple[str, int]] = []
        self.external_links: list[tuple[str, int]] = []
        self.relative_links: list[tuple[str, int]] = []
        self.script_no_integrity: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs):
        line = self.getpos()[0]
        attr_dict = dict(attrs)

        if tag == "title":
            self.has_title = True
            self.in_title = True
        if tag == "meta":
            charset = attr_dict.get("charset")
            name = (attr_dict.get("name") or "").lower()
            if charset:
                self.has_charset = True
            if name == "viewport":
                self.has_viewport = True
        if tag == "script":
            src = attr_dict.get("src", "")
            if src and (src.startswith("http://") or src.startswith("https://") or src.startswith("//")):
                self.external_scripts.append((src, line))
                if not attr_dict.get("integrity"):
                    self.script_no_integrity.append((src, line))
        if tag == "link" and (attr_dict.get("rel") or "").lower() == "stylesheet":
            href = attr_dict.get("href", "")
            if href and (href.startswith("http://") or href.startswith("https://") or href.startswith("//")):
                self.external_links.append((href, line))
        if tag == "a":
            href = (attr_dict.get("href") or "").strip()
            # Flag ANY relative href: not absolute (/...), not a scheme URL
            # (http:, https:, mailto:, tel:, data:, javascript:, ...), not a
            # pure #anchor. The old suffix test only caught .html/.htm or
            # slash-bearing hrefs, so the extensionless form the Vercel
            # cleanUrls breakage actually produces (href="solution") passed.
            if href and not href.startswith(("#", "/")) and not SCHEME_RE.match(href):
                self.relative_links.append((href, line))

        elem_id = attr_dict.get("id")
        if elem_id:
            self.ids.setdefault(elem_id, []).append(line)

        if tag in VOID_TAGS:
            return
        self.stack.append((tag, line))

    def handle_endtag(self, tag: str):
        if tag == "title":
            self.in_title = False
        if tag in VOID_TAGS:
            return
        line = self.getpos()[0]
        if not self.stack:
            self.unexpected_close.append((tag, line))
            return
        last_tag, _open_line = self.stack[-1]
        if last_tag == tag:
            self.stack.pop()
        else:
            # Try to recover: pop until match found or empty
            for j in range(len(self.stack) - 1, -1, -1):
                if self.stack[j][0] == tag:
                    # Everything above j is unclosed
                    for k in range(len(self.stack) - 1, j - 1, -1):
                        unclosed_tag, unclosed_line = self.stack.pop()
                        if unclosed_tag != tag:
                            self.unclosed.append((unclosed_tag, unclosed_line))
                    return
            self.unexpected_close.append((tag, line))

    def handle_data(self, data: str):
        if self.in_title:
            self.title_text += data

    def finalize(self) -> list[tuple[str, int]]:
        return list(self.stack)  # leftover unclosed


def check_one(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parser = StructuralChecker()
    try:
        parser.feed(text)
    except Exception as e:
        return [{
            "line": 0, "category": "parse-error", "severity": "HIGH",
            "message": f"HTML parser error: {e}", "snippet": "",
        }]

    hits: list[dict] = []

    if not parser.has_title:
        hits.append({"line": 1, "category": "missing-head", "severity": "MEDIUM",
                     "message": "Missing <title>.", "snippet": ""})
    elif not parser.title_text.strip():
        hits.append({"line": 1, "category": "missing-head", "severity": "MEDIUM",
                     "message": "<title> is empty.", "snippet": ""})
    if not parser.has_charset:
        hits.append({"line": 1, "category": "missing-head", "severity": "MEDIUM",
                     "message": "Missing <meta charset='utf-8'>.", "snippet": ""})
    if not parser.has_viewport:
        hits.append({"line": 1, "category": "missing-head", "severity": "LOW",
                     "message": "Missing viewport meta tag.", "snippet": ""})

    for tag, line in parser.unclosed:
        hits.append({"line": line, "category": "unclosed-tag", "severity": "HIGH",
                     "message": f"<{tag}> opened but never closed.", "snippet": ""})
    for tag, line in parser.finalize():
        hits.append({"line": line, "category": "unclosed-tag", "severity": "HIGH",
                     "message": f"<{tag}> opened but never closed (EOF).", "snippet": ""})
    for tag, line in parser.unexpected_close:
        hits.append({"line": line, "category": "unexpected-close", "severity": "HIGH",
                     "message": f"</{tag}> with no matching open tag.", "snippet": ""})

    for elem_id, lines in parser.ids.items():
        if len(lines) > 1:
            hits.append({"line": lines[0], "category": "duplicate-id", "severity": "HIGH",
                         "message": f"id='{elem_id}' appears {len(lines)}x (lines: {lines}). Breaks anchors and JS lookups.",
                         "snippet": ""})

    for script_url, line in parser.script_no_integrity:
        hits.append({"line": line, "category": "script-no-integrity", "severity": "LOW",
                     "message": f"External script '{script_url}' without integrity attribute. Consider adding SRI hash.",
                     "snippet": ""})

    for href, line in parser.relative_links:
        hits.append({"line": line, "category": "relative-link", "severity": "HIGH",
                     "message": f"Relative path '{href}' breaks on Vercel cleanUrls. Use absolute path starting with /.",
                     "snippet": ""})

    return hits


def _git_baseline_size(path: Path) -> int | None:
    """Byte size of this file's committed origin/main version, or None.

    None means "no baseline": git unavailable, file outside any repo, no
    origin/main ref, or the path does not exist on origin/main (new file).
    Callers skip silently on None.
    """
    try:
        resolved = path.resolve()
        top = subprocess.run(
            ["git", "-C", str(resolved.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=15,
        )
        if top.returncode != 0 or not top.stdout.strip():
            return None
        root = Path(top.stdout.strip()).resolve()
        rel = resolved.relative_to(root).as_posix()
        size = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-s", f"origin/main:{rel}"],
            capture_output=True, text=True, timeout=15,
        )
        if size.returncode != 0:
            return None
        return int(size.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def check_weight(path: Path) -> list[dict]:
    """Warn when the file grew sharply vs its committed origin/main version.

    Catches silently duplicated embedded assets (friction register
    2026-07-22: a PDF regeneration doubled a 92KB logo blob into every
    page). WARNING severity only: reported in text and JSON output but
    never a failure, never changes the exit code.
    """
    baseline = _git_baseline_size(path)
    if baseline is None or baseline <= 0:
        return []
    try:
        current = path.stat().st_size
    except OSError:
        return []
    growth = current - baseline
    if current > baseline * WEIGHT_RATIO and growth > WEIGHT_ABS_FLOOR:
        pct = round(growth / baseline * 100)
        return [{
            "line": 0, "category": "artefact-weight", "severity": "WARNING",
            "message": (f"grew {pct}% vs origin/main ({baseline} -> {current} bytes) "
                        "— check for duplicated embedded assets"),
            "snippet": "",
        }]
    return []


def check_directory(d: Path) -> list[dict]:
    """Cross-page consistency for a directory of HTML files (recursive)."""
    files = sorted(d.rglob("*.html")) + sorted(d.rglob("*.htm"))
    if len(files) < 2:
        return []

    hits: list[dict] = []
    # All page filenames as expected absolute references
    page_names = {f.name for f in files}

    # Collect inter-page links + feature wiring per file
    link_map: dict[Path, set[str]] = {}
    wiring: dict[str, dict[Path, bool]] = {"theme-toggle": {}, "keyboard-search": {}}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if "chrome-allow: chromeless" in text[:2000]:
            continue  # PDF/print/redirect-stub pages carry no nav by design (rule §2)
        wiring["theme-toggle"][f] = all(p.search(text) for p in THEME_WIRING)
        wiring["keyboard-search"][f] = all(p.search(text) for p in SEARCH_WIRING)
        refs = set()
        for m in re.finditer(r'href=["\']([^"\']+)["\']', text):
            href = m.group(1)
            if href.startswith("/"):
                tail = href.rstrip("/").rsplit("/", 1)[-1]
                if tail in page_names or f"{tail}.html" in page_names:
                    refs.add(tail.replace(".html", ""))
            elif href.endswith(".html") and not href.startswith("http"):
                # Relative — already flagged by check_one, just ignore for consistency
                pass
        link_map[f] = refs

    # Inconsistency: page A links to B/C/D but page B doesn't. Even ONE
    # missing link is a hole in the set's navigation (was >= 2, which let
    # a single dropped sibling ship silently).
    if len(link_map) >= 3:
        all_refs = set().union(*link_map.values()) if link_map.values() else set()
        for f, refs in link_map.items():
            missing = all_refs - refs - {f.stem}
            if missing:
                hits.append({
                    "line": 0, "category": "nav-inconsistency", "severity": "MEDIUM",
                    "message": f"{f.name} is missing nav links to: {', '.join(sorted(missing))}. Multi-page sets should have consistent navigation.",
                    "snippet": "",
                })

    # Wiring consistency (the docstring's promised check): if SOME pages
    # carry theme-toggle / Ctrl-Cmd+K search wiring and others don't, the
    # set is inconsistent. All-present and all-absent are both uniform
    # (per-page requirements are validate-deliverable.py's job).
    for feature, presence in wiring.items():
        if len(presence) < 2:
            continue
        have = sorted(f.name for f, ok in presence.items() if ok)
        lack = sorted(f.name for f, ok in presence.items() if not ok)
        if have and lack:
            hits.append({
                "line": 0, "category": f"{feature}-inconsistency", "severity": "MEDIUM",
                "message": (f"{len(have)}/{len(presence)} pages carry {feature} wiring "
                            f"but these do not: {', '.join(lack)}. "
                            "Multi-page sets should share the same wiring."),
                "snippet": "",
            })

    return hits


def aggregate(hits: list[dict]) -> dict:
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for h in hits:
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
        by_sev[h["severity"]] = by_sev.get(h["severity"], 0) + 1
    return {
        "total": len(hits),
        "hits": hits,
        "by_category": by_cat,
        "by_severity": by_sev,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="HTML files to check")
    ap.add_argument("--dir", help="Directory mode (cross-page consistency check)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    targets: list[Path] = []
    for f in args.files:
        p = Path(f)
        if p.is_file() and p.suffix.lower() in (".html", ".htm"):
            targets.append(p)
        elif not p.is_file():
            print(f"WARNING: skipping '{f}' — not a file.", file=sys.stderr)
        else:
            print(f"WARNING: skipping '{f}' — not an .html/.htm file "
                  "(this tool validates HTML only).", file=sys.stderr)

    extra_hits: list[dict] = []
    if args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            print(f"ERROR: not a directory: {d}", file=sys.stderr)
            return 2
        targets.extend(d.rglob("*.html"))
        targets.extend(d.rglob("*.htm"))
        extra_hits.extend(check_directory(d))

    if not targets and not extra_hits:
        if args.format == "json":
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        print("ERROR: no HTML files.", file=sys.stderr)
        return 2

    if args.format == "json" and len(targets) == 1 and not extra_hits:
        hits = check_one(targets[0]) + check_weight(targets[0])
        print(json.dumps(aggregate(hits)))
        return 0

    grand_hits: list[dict] = list(extra_hits)
    for path in sorted(set(targets)):
        per_file = check_one(path) + check_weight(path)
        if per_file:
            print(f"\n## {path}")
            for h in per_file:
                print(f"  L{h['line']:4d}  [{h['severity']}] [{h['category']}] {h['message']}")
        grand_hits.extend(per_file)

    payload = aggregate(grand_hits)

    if args.format == "json":
        print(json.dumps(payload))
        return 0

    if extra_hits:
        print("\n## Cross-page consistency")
        for h in extra_hits:
            print(f"  [{h['severity']}] [{h['category']}] {h['message']}")

    print(f"\n---\nGrand total: {payload['total']} hits across {len(targets)} files.")
    # WARNING-severity findings (artefact-weight) report but never fail.
    failures = sum(1 for h in grand_hits if h["severity"] != "WARNING")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
