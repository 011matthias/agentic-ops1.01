#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Client-page structure auditor — enforces rule_client_page_structure.md §2-§6.

Walks platform/public/clients/** and platform/public/docs/** and runs
severity-banded structural probes (the §9.1 enforcement mechanism the rule
mandates). Run before any client-page deploy. Exit 1 if any HIGH finding fires.

WHY THIS EXISTS
---------------
normalize-client-pages.py is the CORRECTOR; it had no AUDITOR to catch its own
bad output, which is exactly how the 2026-06-03 theme-key collision shipped: a
canonical 'theme'-keyed boot script was appended onto pages whose toggle still
wrote a per-site key ('alpha-theme', ...), so the boot read one key while the
toggle wrote another and the user's choice was lost on every reload. The §3
theme probes below are the recurrence-kill: a multi-key page is a HIGH finding
that fails the build. Corrector fixes; auditor catches drift.

PROBES (by rule section)
  §2 chrome   site-nav / sidebar / main-content / footer        (MEDIUM/LOW)
  §3 theme    canonical boot present (HIGH), single boot (MEDIUM),
              theme-key collision = multiple storage keys (HIGH),
              non-canonical single key (MEDIUM), working toggle (LOW)
  §4 dates    Last updated: stamp present                        (MEDIUM)
  §6 print    @media print block present                         (MEDIUM)
  §2.3 anchors  <h2> elements carry an id for deep linking        (LOW)

A page declaring `<!-- chrome-allow: chromeless -->` in its first 2000 chars
(PDF/print/embedded variants) skips the chrome/theme/date/print probes; the
theme-key collision probe still runs (a collision is a bug anywhere).

Usage:
    uv run tools/audit-client-pages.py                 # audit clients + docs
    uv run tools/audit-client-pages.py --dir platform/public/clients
    uv run tools/audit-client-pages.py FILE.html [FILE.html ...]
    uv run tools/audit-client-pages.py --format json
    uv run tools/audit-client-pages.py --severity HIGH  # only show >= HIGH
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOTS = [REPO / "platform" / "public" / "clients", REPO / "platform" / "public" / "docs"]

SEV_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

CHROMELESS = re.compile(r"<!--\s*chrome-allow:\s*chromeless\s*-->")

# §2 chrome
SITE_NAV = re.compile(r"class=[\"'][^\"']*\bsite-nav\b", re.IGNORECASE)
SIDEBAR = re.compile(r"class=[\"'][^\"']*\bsidebar\b", re.IGNORECASE)
MAIN_CONTENT = re.compile(r"class=[\"'][^\"']*\bmain-content\b", re.IGNORECASE)
FOOTER = re.compile(r"<footer\b|class=[\"'][^\"']*\bfooter\b", re.IGNORECASE)

# §3 theme — the recurrence-kill
# 2026-07-22 blind-spot fix: the key regexes matched single-quoted lowercase
# keys only, so a double-quoted "site-theme" or camelCase 'siteTheme' toggle
# was invisible and the collision probe (the 2026-06-03 incident class) never
# fired. Quote class + A-Z in the key class + IGNORECASE on the 'theme'
# literal close all three shapes. Captured keys stay verbatim: localStorage
# keys are case-sensitive, so 'Theme' vs 'theme' IS a collision.
CANONICAL_BOOT = "matchMedia('(prefers-color-scheme:dark)')"
THEME_KEY = re.compile(
    r"localStorage\.(?:get|set)Item\(['\"]([A-Za-z0-9_-]*theme[A-Za-z0-9_-]*)['\"]",
    re.IGNORECASE,
)
THEME_SET = re.compile(
    r"localStorage\.setItem\(['\"]([A-Za-z0-9_-]*theme[A-Za-z0-9_-]*)['\"]",
    re.IGNORECASE,
)
TOGGLE_HINT = re.compile(r"toggleTheme|class=[\"'][^\"']*(?:nav-theme|theme-toggle)\b", re.IGNORECASE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# §4 dates
LAST_UPDATED = re.compile(r"last\s+updated", re.IGNORECASE)
DATA_UPDATED = re.compile(r"data-updated=[\"']\d{4}-\d{2}-\d{2}[\"']")

# §6 print
PRINT_BLOCK = re.compile(r"@media\s+print", re.IGNORECASE)

# §2.3 anchors
H2_OPEN = re.compile(r"<h2\b([^>]*)>", re.IGNORECASE)
HAS_ID = re.compile(r"\bid=[\"'][^\"']+[\"']", re.IGNORECASE)


def find_pages(roots: list[Path]) -> list[Path]:
    pages: list[Path] = []
    for root in roots:
        if root.exists():
            pages.extend(root.rglob("*.html"))
    return sorted(pages)


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def audit_text(text: str) -> list[dict]:
    """Run all probes on one page's HTML. Returns a list of hit dicts."""
    hits: list[dict] = []
    chromeless = bool(CHROMELESS.search(text[:2000]))

    def add(line, category, severity, message):
        hits.append({"line": line, "category": category, "severity": severity, "message": message})

    # --- §3 theme: the collision probe runs ALWAYS (a collision is a bug even
    #     on a chromeless page); the boot/toggle probes are chrome-only. -------
    # Theme probes run on comment-stripped text: a boot script or theme key
    # inside an HTML comment is not live code (2026-07-22 blind-spot fix — a
    # commented-out boot script satisfied boot_count).
    live = HTML_COMMENT.sub("", text)
    theme_keys = {m.group(1) for m in THEME_KEY.finditer(live)}
    boot_count = live.count(CANONICAL_BOOT)
    non_canonical = theme_keys - {"theme"}

    if len(theme_keys) > 1:
        keys = ", ".join(sorted(theme_keys))
        add(1, "theme-key-collision", "HIGH",
            f"page uses multiple theme storage keys ({keys}); the boot script and "
            f"toggle disagree, so the theme choice is lost on reload. "
            f"Run: uv run tools/normalize-client-pages.py --apply")
    elif non_canonical:
        add(1, "theme-key-noncanonical", "MEDIUM",
            f"theme storage key '{next(iter(non_canonical))}' is non-canonical "
            f"(rule mandates 'theme'). Run normalize-client-pages.py --apply")

    if not chromeless:
        if boot_count == 0:
            add(1, "theme-boot-missing", "HIGH",
                "no canonical theme boot script (matchMedia signature) in <head>; "
                "page flashes and cannot restore the saved theme")
        elif boot_count > 1:
            add(1, "theme-boot-duplicate", "MEDIUM",
                f"{boot_count} canonical boot scripts present; expected exactly one")

        has_toggle = bool(THEME_SET.search(live)) or bool(TOGGLE_HINT.search(live))
        if SITE_NAV.search(text) and not has_toggle:
            add(1, "theme-toggle-missing", "LOW",
                "site-nav present but no working theme toggle (button/onclick writing 'theme')")

        # --- §2 chrome ---------------------------------------------------------
        if not SITE_NAV.search(text):
            add(1, "chrome-site-nav", "MEDIUM", "missing top <nav class=\"site-nav\"> (§2.1)")
        if not SIDEBAR.search(text):
            add(1, "chrome-sidebar", "MEDIUM", "missing left <aside class=\"sidebar\"> (§2.2)")
        if not MAIN_CONTENT.search(text):
            add(1, "chrome-main", "LOW", "missing <main class=\"main-content\"> (§2.3)")
        if not FOOTER.search(text):
            add(1, "chrome-footer", "MEDIUM", "missing footer element (§2.4)")

        # --- §4 last-updated ---------------------------------------------------
        if not (LAST_UPDATED.search(text) or DATA_UPDATED.search(text)):
            add(1, "last-updated-missing", "MEDIUM",
                "no 'Last updated: YYYY-MM-DD' stamp or data-updated attr (§4). "
                "Run normalize-client-pages.py --apply --backfill-dates")

        # --- §6 print ----------------------------------------------------------
        if not PRINT_BLOCK.search(text):
            add(1, "print-block-missing", "MEDIUM", "no @media print block (§6); nav/sidebar print visible")

        # --- §2.3 anchor ids ---------------------------------------------------
        h2s = list(H2_OPEN.finditer(text))
        idless = [m for m in h2s if not HAS_ID.search(m.group(1))]
        if h2s and idless:
            add(line_of(text, idless[0].start()), "h2-no-id", "LOW",
                f"{len(idless)} of {len(h2s)} <h2> lack an id for deep linking (§2.3, §7 overseeability)")

    return hits


def audit_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = audit_text(text)
    rel = str(path.relative_to(REPO)) if path.is_absolute() and REPO in path.parents else str(path)
    for h in hits:
        h["file"] = rel
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Client-page structure auditor (rule_client_page_structure.md §2-§6)")
    ap.add_argument("files", nargs="*", help="specific HTML files to audit")
    ap.add_argument("--dir", action="append", help="audit root override (repeatable; default: clients + docs)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--severity", choices=["HIGH", "MEDIUM", "LOW"], default="LOW",
                    help="minimum severity to report (default: LOW = all)")
    args = ap.parse_args()

    if args.files:
        targets = [Path(f) if Path(f).is_absolute() else REPO / f for f in args.files]
    elif args.dir:
        roots = [Path(d) if Path(d).is_absolute() else REPO / d for d in args.dir]
        targets = find_pages(roots)
    else:
        targets = find_pages(ROOTS)

    if not targets:
        print("No client pages found.", file=sys.stderr)
        return 2

    floor = SEV_ORDER[args.severity]
    all_hits: list[dict] = []
    for t in targets:
        if not t.exists():
            print(f"WARN: not found: {t}", file=sys.stderr)
            continue
        all_hits.extend(h for h in audit_file(t) if SEV_ORDER[h["severity"]] >= floor)

    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for h in all_hits:
        by_sev[h["severity"]] = by_sev.get(h["severity"], 0) + 1
        by_cat[h["category"]] = by_cat.get(h["category"], 0) + 1
    highs = sum(1 for h in all_hits if h["severity"] == "HIGH")

    if args.format == "json":
        print(json.dumps({
            "pages_scanned": len(targets),
            "total_hits": len(all_hits),
            "by_severity": by_sev,
            "by_category": by_cat,
            "hits": all_hits,
        }, indent=2))
        return 1 if highs else 0

    # text report — group by file, HIGH first within each
    by_file: dict[str, list[dict]] = {}
    for h in all_hits:
        by_file.setdefault(h["file"], []).append(h)
    for f in sorted(by_file):
        print(f"\n## {f}")
        for h in sorted(by_file[f], key=lambda x: -SEV_ORDER[x["severity"]]):
            print(f"  L{h['line']:4d}  [{h['severity']}] [{h['category']}] {h['message']}")

    print(f"\n---\nScanned {len(targets)} pages. "
          f"{len(all_hits)} findings: "
          f"{by_sev.get('HIGH', 0)} HIGH, {by_sev.get('MEDIUM', 0)} MEDIUM, {by_sev.get('LOW', 0)} LOW.")
    if highs:
        print(f"FAIL: {highs} HIGH finding(s) — do not deploy until resolved (rule_client_page_structure.md §9).")
    else:
        print("PASS: no HIGH findings.")
    return 1 if highs else 0


if __name__ == "__main__":
    sys.exit(main())
