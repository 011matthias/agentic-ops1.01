# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# direction: minimize
"""Scorer: total local page weight in bytes for one or more HTML files.

Counts the HTML file itself plus every LOCAL asset it references (img/script/
source/video/audio/embed/iframe `src`, video `poster`, and `<link href>` for
stylesheet/icon/preload rels). External http(s):// and data: refs are skipped;
so are url(...) refs inside CSS (documented limitation - inline the check in a
dedicated scorer if a target leans on CSS backgrounds). Referenced files are
deduped by resolved path, and a reference that does not exist on disk counts
as 0 bytes but is reported, so a broken ref cannot masquerade as a win.

Deterministic: pure local file sizes, no network, no timing.

Contract (tools/scorers/README.md): last stdout line is `SCORE: <int bytes>`,
exit 0 only on successful measurement.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

SRC_TAGS = {"img", "script", "source", "video", "audio", "embed", "iframe"}
LINK_RELS = {"stylesheet", "icon", "preload", "apple-touch-icon", "manifest"}


class _RefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag in SRC_TAGS and a.get("src"):
            self.refs.append(a["src"])
        if tag == "video" and a.get("poster"):
            self.refs.append(a["poster"])
        if tag == "link" and a.get("href"):
            rels = set((a.get("rel") or "").lower().split())
            if rels & LINK_RELS:
                self.refs.append(a["href"])


def _is_local(ref: str) -> bool:
    r = ref.strip().lower()
    return bool(r) and not r.startswith(
        ("http://", "https://", "//", "data:", "mailto:", "tel:", "#")
    )


def measure(html_path: Path) -> tuple[int, list[str]]:
    """Return (total_bytes, notes) for one HTML file + its local assets."""
    parser = _RefCollector()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    total = html_path.stat().st_size
    notes = [f"  {html_path.name}: {html_path.stat().st_size} B (html)"]
    seen: set[Path] = set()
    for ref in parser.refs:
        if not _is_local(ref):
            continue
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        target = (html_path.parent / clean).resolve()
        if target in seen:
            continue
        seen.add(target)
        if target.is_file():
            size = target.stat().st_size
            total += size
            notes.append(f"  {clean}: {size} B")
        else:
            notes.append(f"  {clean}: MISSING (0 B counted, fix the ref)")
    return total, notes


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: page-weight.py FILE.html [...]", file=sys.stderr)
        return 2
    paths = [Path(a) for a in argv]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        print(f"input file(s) not found: {missing}", file=sys.stderr)
        return 2
    grand_total = 0
    for p in paths:
        subtotal, notes = measure(p)
        grand_total += subtotal
        print(f"{p}:")
        print("\n".join(notes))
        print(f"  subtotal: {subtotal} B")
    print(f"SCORE: {grand_total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
