#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Client-page structure corrector — implements rule_client_page_structure.md.

Walks `platform/public/clients/**` and `platform/public/docs/**` and
idempotently injects:

  1. Theme boot script in <head> (prevents flash, applies stored theme)
  2. nav-theme toggle button onclick handler (was CSS-only, dead)
  3. @media print stylesheet (where missing)
  4. Optional last-updated stamp in footer (--backfill-dates)

Skip a file with the marker `<!-- chrome-allow: chromeless -->` in the
first 20 lines.

Usage:
    uv run tools/normalize-client-pages.py                # report only (dry-run default)
    uv run tools/normalize-client-pages.py --apply        # write changes
    uv run tools/normalize-client-pages.py --apply --backfill-dates
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOTS = [REPO / "platform" / "public" / "clients", REPO / "platform" / "public" / "docs"]

CHROMELESS = re.compile(r"<!--\s*chrome-allow:\s*chromeless\s*-->")

BOOT_SCRIPT = """<script>(function(){var t=localStorage.getItem('theme');var d=document.documentElement;d.setAttribute('data-theme',t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light');})();</script>
"""
BOOT_MARKER = "data-theme', t === 'dark'"  # fragment unique to OUR boot script (not used for matching; placeholder)
BOOT_SIGNATURE = "localStorage.getItem('theme')"

TOGGLE_ONCLICK = "(function(){var d=document.documentElement;var c=d.getAttribute('data-theme')==='dark'?'light':'dark';d.setAttribute('data-theme',c);localStorage.setItem('theme',c);})()"

PRINT_BLOCK = """@media print {
    .site-nav, .sidebar, .mobile-nav-toggle, .cta-section { display: none !important; }
    .main-content { margin-left: 0 !important; }
    body { padding-top: 0 !important; }
    h2 { page-break-before: always; }
    h2:first-of-type { page-break-before: avoid; }
}
"""

HEAD_RE = re.compile(r"</head>", re.IGNORECASE)
STYLE_OPEN_RE = re.compile(r"<style[^>]*>", re.IGNORECASE)
NAV_THEME_BTN_RE = re.compile(r"<button[^>]*class=[\"'][^\"']*nav-theme[^\"']*[\"'][^>]*>([\s\S]*?)</button>", re.IGNORECASE)
NAV_THEME_BTN_HAS_ONCLICK_RE = re.compile(r"<button[^>]*class=[\"'][^\"']*nav-theme[^\"']*[\"'][^>]*onclick=", re.IGNORECASE)
SITE_NAV_OPEN_RE = re.compile(r"<nav[^>]*class=[\"'][^\"']*site-nav[^\"']*[\"'][^>]*>", re.IGNORECASE)
NAV_RIGHT_CLOSE_RE = re.compile(r"(<div[^>]*class=[\"'][^\"']*nav-right[^\"']*[\"'][^>]*>)([\s\S]*?)(</div>)", re.IGNORECASE)
PRINT_PRESENT_RE = re.compile(r"@media\s+print", re.IGNORECASE)
FOOTER_RE = re.compile(r"(<(?:footer|div)[^>]*class=[\"'][^\"']*footer[^\"']*[\"'][^>]*>)([\s\S]*?)(</(?:footer|div)>)", re.IGNORECASE)
LAST_UPDATED_RE = re.compile(r"(?i)last\s+updated")
DATA_UPDATED_RE = re.compile(r"data-updated=[\"'](\d{4}-\d{2}-\d{2})[\"']")


def git_mtime(path: Path) -> str | None:
    """Return YYYY-MM-DD of the last git commit touching this file, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=REPO, capture_output=True, text=True, timeout=10,
        )
        s = out.stdout.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
    except Exception:
        pass
    return None


def fs_mtime(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def find_pages() -> list[Path]:
    pages: list[Path] = []
    for root in ROOTS:
        if root.exists():
            pages.extend(root.rglob("*.html"))
    return sorted(pages)


def needs_boot_script(text: str) -> bool:
    return BOOT_SIGNATURE not in text


def inject_boot_script(text: str) -> str:
    return HEAD_RE.sub(BOOT_SCRIPT + "</head>", text, count=1)


def needs_toggle_onclick(text: str) -> bool:
    if not NAV_THEME_BTN_RE.search(text):
        return False  # no button exists; we don't add one if site-nav layout missing
    return not NAV_THEME_BTN_HAS_ONCLICK_RE.search(text)


def inject_toggle_onclick(text: str) -> str:
    def repl(m):
        whole = m.group(0)
        if "onclick=" in whole.lower():
            return whole
        # Insert onclick + aria-label before the closing >
        # Match the opening tag only.
        opening_end = whole.find(">")
        if opening_end == -1:
            return whole
        opening = whole[:opening_end]
        rest = whole[opening_end:]
        if "aria-label" not in opening.lower():
            opening = opening + f' onclick="{TOGGLE_ONCLICK}" aria-label="Toggle theme"'
        else:
            opening = opening + f' onclick="{TOGGLE_ONCLICK}"'
        return opening + rest
    return NAV_THEME_BTN_RE.sub(repl, text, count=1)


def needs_print_block(text: str) -> bool:
    return not PRINT_PRESENT_RE.search(text)


def inject_print_block(text: str) -> str:
    """Inject the print block at the start of the first <style> block."""
    m = STYLE_OPEN_RE.search(text)
    if not m:
        return text
    insert_at = m.end()
    return text[:insert_at] + "\n" + PRINT_BLOCK + text[insert_at:]


def needs_last_updated(text: str) -> bool:
    if DATA_UPDATED_RE.search(text):
        return False
    return not LAST_UPDATED_RE.search(text)


def inject_last_updated(text: str, date_str: str) -> str:
    stamp = f'<p class="footer-updated" style="font-size:11px;color:var(--text2);margin-top:6px;">Last updated: {date_str}</p>'
    def repl(m):
        open_, body, close = m.group(1), m.group(2), m.group(3)
        if "Last updated" in body or "footer-updated" in body:
            return m.group(0)
        return f"{open_}{body}\n  {stamp}\n{close}"
    new = FOOTER_RE.sub(repl, text, count=1)
    return new


def process_file(path: Path, *, apply: bool, backfill_dates: bool) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    head_window = text[:2000]
    if CHROMELESS.search(head_window):
        return {"path": str(path), "skipped": "chromeless"}

    changes = []
    new_text = text

    if needs_boot_script(new_text) and HEAD_RE.search(new_text):
        new_text = inject_boot_script(new_text)
        changes.append("boot-script")

    if needs_toggle_onclick(new_text):
        new_text = inject_toggle_onclick(new_text)
        changes.append("toggle-onclick")

    if needs_print_block(new_text) and STYLE_OPEN_RE.search(new_text):
        new_text = inject_print_block(new_text)
        changes.append("print-block")

    if backfill_dates and needs_last_updated(new_text) and FOOTER_RE.search(new_text):
        d = git_mtime(path) or fs_mtime(path)
        new_text = inject_last_updated(new_text, d)
        changes.append(f"last-updated:{d}")

    if not changes:
        return {"path": str(path), "changes": []}
    if apply and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return {"path": str(path), "changes": changes, "wrote": apply}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--backfill-dates", action="store_true",
                    help="inject Last updated: stamp from git mtime where absent")
    ap.add_argument("--root", action="append",
                    help="override scan root (repeatable; default: clients + docs)")
    args = ap.parse_args()

    global ROOTS
    if args.root:
        ROOTS = [REPO / r if not Path(r).is_absolute() else Path(r) for r in args.root]

    pages = find_pages()
    print(f"Scanning {len(pages)} client pages...")
    counts = {"boot-script": 0, "toggle-onclick": 0, "print-block": 0,
              "last-updated": 0, "chromeless": 0, "unchanged": 0}
    touched: list[str] = []
    for p in pages:
        res = process_file(p, apply=args.apply, backfill_dates=args.backfill_dates)
        if res.get("skipped") == "chromeless":
            counts["chromeless"] += 1
            continue
        ch = res.get("changes", [])
        if not ch:
            counts["unchanged"] += 1
            continue
        touched.append(str(p.relative_to(REPO)))
        for c in ch:
            key = c.split(":", 1)[0]
            counts[key] = counts.get(key, 0) + 1

    print()
    print("Per-fix counts:")
    for k in ("boot-script", "toggle-onclick", "print-block", "last-updated"):
        print(f"  {k:<16} {counts.get(k, 0):>4}")
    print(f"  unchanged       {counts['unchanged']:>4}")
    print(f"  chromeless      {counts['chromeless']:>4}")
    print(f"  files touched   {len(touched):>4}")
    if args.apply:
        print()
        print(f"Mode: APPLIED ({sum(counts.get(k,0) for k in ('boot-script','toggle-onclick','print-block','last-updated'))} edits)")
    else:
        print()
        print("Mode: DRY-RUN (re-run with --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
