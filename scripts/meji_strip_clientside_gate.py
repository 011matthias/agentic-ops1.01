# /// script
# requires-python = ">=3.11"
# ///
"""One-off: strip the client-side auth gate (overlay DOM + gate script) from
the Meji Media doc HTML files. Server-side proxy gate replaces it. Theme and
sidebar JS in the same <script> block are preserved.

Idempotent: files without `var MEJI_CODE` are skipped.
"""
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "platform/public/docs/meji-media"


def strip(html: str) -> str:
    if "var MEJI_CODE" not in html:
        return html  # already stripped

    # 1. Remove the overlay DOM: from an optional `<!-- Auth gate -->` comment
    #    / `<div id="auth-gate"` up to (not including) the gate <script>.
    i = html.index('<div id="auth-gate"')
    m = re.search(r"<!--\s*Auth gate\s*-->\s*\Z", html[:i])
    start = m.start() if m else i
    j = html.index("<script>", i)
    html = html[:start] + html[j:]

    # 2. Remove the gate script: `var MEJI_CODE` through the gate IIFE close
    #    (`})();`), plus trailing whitespace. The gate IIFE is the only
    #    `})();` between the var decl and the theme logic that follows.
    k = html.index("var MEJI_CODE")
    e = html.index("})();", k) + len("})();")
    while e < len(html) and html[e] in "\r\n \t":
        e += 1
    html = html[:k] + html[e:]
    return html


def main() -> int:
    files = sorted(DOCS.glob("*.html"))
    changed = 0
    for f in files:
        src = f.read_text(encoding="utf-8")
        out = strip(src)
        if out != src:
            f.write_text(out, encoding="utf-8")
            changed += 1
            print(f"stripped {f.name}")
        else:
            print(f"skip     {f.name} (no client gate)")
    print(f"\n{changed}/{len(files)} files modified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
