# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
validate-dist.py — deliverable-rule gate for framework-built sites.

Closes the 2026-05-08 regression: validate-html.py / the post-write hook
make rule_deliverables enforcement structural for hand-written HTML, but
they do NOT scan framework build output (Astro `dist/`). A banned em-dash
reached a built deliverable and was caught only by a manual B2 grep. This
script makes the dist/ scan structural and is wired as an npm `postbuild`
step so a failing build never deploys.

Rules enforced (rule_deliverables.md "HTML deliverables MUST NOT include"):
  - em-dash U+2014  (—)
  - &mdash; / &#8212; / &#x2014; entities
  - `--` used as a typographic em-dash substitute in *visible* HTML text
    (CSS custom properties `--name`, HTML comments, and JS operators are
    legitimate and intentionally NOT flagged — only reader-facing prose)

Usage:
  uv run python tools/validate-dist.py <dist-dir> [more-dirs...]
Exit: 0 = clean, 1 = violations (prints file:line offenders).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EM_DASH = "—"
ENTITY_RE = re.compile(r"&mdash;|&#8212;|&#x2014;", re.IGNORECASE)
# `--` flanked by word/space on visible text. Not anchored to CSS/JS because
# we strip those first.
TYPO_DASH_RE = re.compile(r"(?<![\-!<>])--(?![\->])")

TAG_RE = re.compile(r"<[^>]+>")
STYLE_SCRIPT_RE = re.compile(
    r"<(style|script)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def visible_text(html: str) -> str:
    """Reader-facing text only: drop <style>/<script>, comments, tags."""
    html = STYLE_SCRIPT_RE.sub(" ", html)
    html = HTML_COMMENT_RE.sub(" ", html)
    html = TAG_RE.sub(" ", html)
    return html


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def scan_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []

    # em-dash + entities: banned everywhere in the shipped artifact
    # (including CSS/JS comments — that was the exact 2026-05-08 miss).
    for m in re.finditer(re.escape(EM_DASH), raw):
        problems.append(f"{path}:{line_of(raw, m.start())}: em-dash U+2014")
    for m in ENTITY_RE.finditer(raw):
        problems.append(
            f"{path}:{line_of(raw, m.start())}: mdash entity '{m.group(0)}'"
        )

    # typographic `--`: only in visible HTML prose.
    if path.suffix.lower() in {".html", ".htm"}:
        vis = visible_text(raw)
        for m in TYPO_DASH_RE.finditer(vis):
            snippet = vis[max(0, m.start() - 30) : m.start() + 30]
            snippet = " ".join(snippet.split())
            problems.append(
                f"{path}: typographic '--' in visible text: …{snippet}…"
            )
    return problems


def main(argv: list[str]) -> int:
    targets = argv[1:] or ["dist"]
    files: list[Path] = []
    for t in targets:
        root = Path(t)
        if not root.exists():
            print(f"validate-dist: path not found: {root}", file=sys.stderr)
            return 1
        for ext in ("*.html", "*.htm", "*.css", "*.js"):
            files.extend(root.rglob(ext))

    if not files:
        print("validate-dist: no html/css/js files found to scan")
        return 0

    all_problems: list[str] = []
    for f in sorted(files):
        all_problems.extend(scan_file(f))

    if all_problems:
        print(
            f"validate-dist: FAIL. {len(all_problems)} deliverable-rule "
            f"violation(s) across {len(files)} file(s):\n"
        )
        for p in all_problems:
            print("  " + p)
        print(
            "\nFix at SOURCE (not via minifier). See rule_deliverables.md."
        )
        return 1

    print(
        f"validate-dist: OK. {len(files)} file(s) scanned, "
        f"zero em-dash / &mdash; / typographic dash."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
