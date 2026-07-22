#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""HTML deliverable QoL features validator.

Per rule_deliverables.md, self-contained HTML deliverables MUST include:
  1. Dark/light mode toggle (pill button, [data-theme] CSS, localStorage)
  2. Copy-to-clipboard on code/command blocks (hover-reveal)
  3. Keyboard search (Ctrl/Cmd+K, visible hint)
  4. Filter/search state persistence (localStorage)

Static HTML on Vercel: must use absolute paths between pages
(rule_deliverables.md "Static HTML paths"). Relative paths break with
cleanUrls + trailingSlash:false on nested routes.

Friction context: 2026-03-15 delivery-gap entry — agent shipped HTML
infographic without baseline QoL features and the user had to identify
the gap. This validator closes that loop.

Usage:
    uv run tools/validate-deliverable.py FILE.html
    uv run tools/validate-deliverable.py FILE.html --format json

Suppression: a file can declare exemptions via a sibling
`.deliverable-config.yaml` with keys like `skip: [dark-mode, copy-clipboard]`
and a `reason:` field. Without yaml available we accept a comment marker
in the HTML head: `<!-- deliverable-allow: dark-mode, copy-clipboard -->`.

Exit 0 = pass. Exit 1 = required feature missing. Exit 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Each check: (id, severity, description, regex, also_check)
# also_check is an optional second pattern that must ALSO appear (AND).
# Severity HIGH = ship-blocker per rule_deliverables.md, MEDIUM = strong warning.

CHECKS: list[dict] = [
    {
        "id": "dark-mode-toggle",
        "severity": "HIGH",
        "description": "Dark/light mode toggle (data-theme + localStorage)",
        "patterns": [
            r"data-theme",
            r"localStorage",
        ],
        "message": "Missing dark/light mode toggle. Required: [data-theme] CSS attribute selector AND localStorage persistence.",
    },
    {
        "id": "copy-clipboard",
        "severity": "HIGH",
        "description": "Copy-to-clipboard on code blocks",
        "patterns": [
            r"navigator\.clipboard|clipboard\.writeText",
        ],
        "message": "Missing copy-to-clipboard. Required: navigator.clipboard.writeText on code/command blocks.",
    },
    {
        "id": "keyboard-search",
        "severity": "HIGH",
        "description": "Keyboard search shortcut (Ctrl/Cmd+K)",
        "patterns": [
            r"(metaKey|ctrlKey)",
            r"(['\"]k['\"]|KeyK)",
        ],
        "message": "Missing keyboard shortcut (Ctrl/Cmd+K). Required: keydown handler checking metaKey||ctrlKey + K.",
    },
    {
        "id": "state-persistence",
        "severity": "MEDIUM",
        "description": "Filter/search state persistence",
        "patterns": [
            r"localStorage\.(setItem|getItem)",
        ],
        "message": "Missing localStorage persistence (filter/search state should survive reloads).",
    },
]


SUPPRESS_RE = re.compile(r"<!--\s*deliverable-allow:\s*([\w,\s-]+?)\s*(?:\|\s*reason:\s*(.*?))?\s*-->")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
RELATIVE_LINK_RE = re.compile(r'<a\s+[^>]*href=["\'](?!https?://|mailto:|#|/|tel:|javascript:)([^"\']+)["\']', re.IGNORECASE)
SCRIPT_SRC_RE = re.compile(r'<script\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)
LINK_HREF_RE = re.compile(r'<link\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)


def parse_suppressions(text: str) -> set[str]:
    suppressed: set[str] = set()
    for m in SUPPRESS_RE.finditer(text):
        cats = m.group(1)
        for c in cats.split(","):
            c = c.strip()
            if c:
                suppressed.add(c)
    return suppressed


def find_line(text: str, pattern: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(pattern, line):
            return i
    return 0


def check_relative_paths(text: str) -> list[dict]:
    """Vercel cleanUrls breaks relative paths between static pages.

    Flag <a href="..."> that uses a path relative to the current page.
    Skip mailto/tel/javascript/anchor/absolute-https/absolute-root.
    """
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in RELATIVE_LINK_RE.finditer(line):
            href = m.group(1)
            # Skip same-page anchors
            if href.startswith("#"):
                continue
            # We've already excluded http(s)://, mailto:, tel:, javascript:, /
            # in the regex; everything left is a relative path.
            if href.startswith("./") or href.startswith("../") or "/" in href or href.endswith(".html") or href.endswith(".htm"):
                hits.append({
                    "line": i,
                    "category": "relative-path",
                    "severity": "HIGH",
                    "message": f"Relative path '{href}' breaks on Vercel cleanUrls. Use absolute path starting with /.",
                    "snippet": line.strip()[:160],
                })
    return hits


def check_qol_features(text: str, suppressed: set[str]) -> list[dict]:
    # Strip HTML comments first: a feature string inside a comment is not a
    # working feature (2026-07-22 blind-spot fix — commented-out boilerplate
    # satisfied all three HIGH ship-blocker checks). Suppression markers are
    # parsed from the raw text by the caller before this runs.
    live = HTML_COMMENT_RE.sub("", text)
    hits = []
    for check in CHECKS:
        if check["id"] in suppressed:
            continue
        all_present = all(re.search(p, live, re.IGNORECASE) for p in check["patterns"])
        if not all_present:
            hits.append({
                "line": 1,
                "category": check["id"],
                "severity": check["severity"],
                "message": check["message"],
                "snippet": check["description"],
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


def emit_text(path: Path, payload: dict) -> None:
    if payload["total"] == 0:
        return
    print(f"\n## {path}")
    for h in payload["hits"]:
        print(f"  L{h['line']:4d}  [{h['severity']}] [{h['category']}] {h['message']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="HTML files to check")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    targets = [Path(f) for f in args.files if Path(f).is_file()]
    if not targets:
        if args.format == "json":
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        print("ERROR: no files.", file=sys.stderr)
        return 2

    # Filter to HTML only
    html_targets = [p for p in targets if p.suffix.lower() in (".html", ".htm")]
    if not html_targets:
        if args.format == "json":
            print(json.dumps({"total": 0, "hits": [], "by_category": {}, "by_severity": {}}))
            return 0
        print("(no HTML files to check)", file=sys.stderr)
        return 0

    if args.format == "json" and len(html_targets) == 1:
        text = html_targets[0].read_text(encoding="utf-8", errors="replace")
        suppressed = parse_suppressions(text)
        hits = check_qol_features(text, suppressed)
        if "relative-path" not in suppressed:
            hits.extend(check_relative_paths(text))
        print(json.dumps(aggregate(hits)))
        return 0

    grand_total = 0
    grand_cat: dict[str, int] = {}
    grand_sev: dict[str, int] = {}
    for path in html_targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        suppressed = parse_suppressions(text)
        hits = check_qol_features(text, suppressed)
        if "relative-path" not in suppressed:
            hits.extend(check_relative_paths(text))
        payload = aggregate(hits)
        emit_text(path, payload)
        grand_total += payload["total"]
        for k, v in payload["by_category"].items():
            grand_cat[k] = grand_cat.get(k, 0) + v
        for k, v in payload["by_severity"].items():
            grand_sev[k] = grand_sev.get(k, 0) + v

    if args.format == "json":
        print(json.dumps({
            "total": grand_total,
            "hits": [],
            "by_category": grand_cat,
            "by_severity": grand_sev,
        }))
        return 0

    print(f"\n---\nGrand total: {grand_total} hits across {len(html_targets)} HTML files.")
    return 1 if grand_total else 0


if __name__ == "__main__":
    sys.exit(main())
