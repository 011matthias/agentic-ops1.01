# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
audit-local-web-aesthetics.py - advisory List-B (visual-craft) pre-ship pass.

Prints a per-site checklist of the mechanically-detectable parts of List B
(see .claude/skills/skil_web-build/modules/CONCEIVE.md "The two standards").
This is ADVISORY: the human/visual call stays the gate. It catches the cheap
tells a static read CAN see, so the eyeball pass can focus on the rest
(grade quality, register fit, "would the owner pay").

What it can and cannot judge:
  CAN (mechanical):   pure-#fff paper / pure-#000 ink; banned default as the
                      PRIMARY display font; a raw [BITTE PRUEFEN] sentinel in
                      the built HTML; missing "Bilder: Pexels" credit; whether
                      a consistent photo grade rule exists; exclamation marks
                      in visible copy; two sites sharing one hero structure.
  CANNOT (your eye):  is the grade actually warm + consistent; is the type
                      confident-BIG in context; register fit; logo/palette
                      harmony; recognition-before-impression.

Usage:
  uv run tools/audit-local-web-aesthetics.py                  # all sites, advisory
  uv run tools/audit-local-web-aesthetics.py --only praxis-uslu
  uv run tools/audit-local-web-aesthetics.py --strict         # exit 1 on hard fails

Hard fails (only under --strict): raw [BITTE PRUEFEN] in dist, pure-white paper
or pure-black ink, a banned default as the primary display font.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "workspace" / "projects" / "local-web" / "app"
SITES_DIR = APP / "src" / "sites"
PAGES_DIR = APP / "src" / "pages"
DIST = APP / "dist"

BANNED_PRIMARY_FONTS = ["inter", "roboto", "arial", "space grotesk", "system-ui"]
PURE_WHITE = {"#fff", "#ffffff", "white"}
PURE_BLACK = {"#000", "#000000", "black"}
SENTINEL = "BITTE PRÜFEN"  # the raw [BITTE PRÜFEN] string

GREEN, YELLOW, RED, DIM, RST = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"


def tag(kind: str) -> str:
    return {
        "PASS": f"{GREEN}PASS{RST}",
        "WARN": f"{YELLOW}WARN{RST}",
        "FAIL": f"{RED}FAIL{RST}",
        "INFO": f"{DIM}INFO{RST}",
    }[kind]


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def token_value(css: str, var: str) -> str | None:
    """First value of a CSS custom property, lowercased, comment-stripped."""
    m = re.search(rf"{re.escape(var)}\s*:\s*([^;]+);", css)
    if not m:
        return None
    val = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).strip().lower()
    return val


def hero_fingerprint(astro: str) -> frozenset[str]:
    """Structural classes in the hero region; two sites sharing it = cloned."""
    classes = set(re.findall(r'class="([^"]+)"', astro))
    flat = " ".join(classes)
    toks = set(re.findall(r"\b(?:hero__[a-z-]+|dh__[a-z-]+|band|bands|discipline-hero|trust__[a-z-]+)\b", flat))
    return frozenset(toks)


def audit_site(slug: str, strict: bool) -> tuple[list[tuple[str, str]], bool, frozenset[str]]:
    rows: list[tuple[str, str]] = []
    hard_fail = False
    theme = read(SITES_DIR / slug / "theme.css")
    page = read(PAGES_DIR / slug / ".astro") or read(PAGES_DIR / f"{slug}.astro")
    dist_html = read(DIST / slug / "index.html")

    # B3 - warm neutrals, not pure black/white -------------------------------
    paper = token_value(theme, "--color-paper")
    ink = token_value(theme, "--color-ink")
    if paper in PURE_WHITE:
        rows.append(("FAIL", f"paper is pure white ({paper}); use a warm off-white"))
        hard_fail = True
    elif paper:
        rows.append(("PASS", f"warm paper {paper}"))
    if ink in PURE_BLACK:
        rows.append(("FAIL", f"ink is pure black ({ink}); use a warm near-black"))
        hard_fail = True
    elif ink:
        rows.append(("PASS", f"near-black ink {ink}"))

    # B3 - one disciplined accent (advisory count) ---------------------------
    accents = sorted(set(re.findall(r"--color-accent[\w-]*", theme)))
    extra = [a for a in accents if a not in ("--color-accent", "--color-accent-ink", "--color-accent-soft", "--color-accent-display", "--color-accent-text")]
    if extra:
        rows.append(("INFO", f"accent tokens: {', '.join(accents)} (confirm ONE accent reads, not a rainbow)"))

    # B1 - non-default PRIMARY display font ----------------------------------
    disp = token_value(theme, "--font-display") or ""
    primary = disp.split(",")[0].strip().strip('"').strip("'")
    if any(b in primary for b in BANNED_PRIMARY_FONTS):
        rows.append(("FAIL", f"primary display font is a banned default: {primary}"))
        hard_fail = True
    elif primary:
        rows.append(("PASS", f"display font {primary}"))

    # B1 - confident-big hero type (heuristic) -------------------------------
    if page:
        hero_h1 = re.search(r"\.hero\s*h1\s*\{[^}]*\}|dh__wordmark\s*\{[^}]*\}", page, re.S)
        blob = hero_h1.group(0) if hero_h1 else ""
        wght = re.search(r'"wght"\s*(\d+)|font-weight:\s*(\d+)', blob)
        wnum = int(next(g for g in wght.groups() if g)) if wght else 0
        big = bool(re.search(r"--text-(4xl|5xl|6xl)|clamp\(", blob))
        if blob and wnum >= 560 and big:
            rows.append(("PASS", f"hero h1 confident (weight ~{wnum}, large scale)"))
        elif blob:
            rows.append(("WARN", f"hero h1 may read 'nice' not BIG (weight {wnum or '?'}); push weight>=600 + scale"))

    # B4 - one consistent grade rule present (advisory) ----------------------
    if page:
        if re.search(r"filter:\s*[^;]*(?:sepia|saturate)", page):
            rows.append(("PASS", "a photo grade rule is present (verify it is warm + consistent by eye)"))
        else:
            rows.append(("WARN", "no CSS grade filter found; photos may not share one warm grade"))

    # A5 - no raw [BITTE PRUEFEN] sentinel on the pitchable page -------------
    if dist_html:
        n = dist_html.count(SENTINEL)
        if n:
            rows.append(("FAIL", f"{n} raw [BITTE PRÜFEN] sentinel(s) in built HTML; render quiet 'auf Anfrage' / omit"))
            hard_fail = True
        else:
            rows.append(("PASS", "no raw [BITTE PRÜFEN] sentinel in built HTML"))
        if "Bilder: Pexels" in dist_html:
            rows.append(("PASS", "Pexels credit present"))
        else:
            rows.append(("WARN", "no 'Bilder: Pexels' credit found"))
    else:
        rows.append(("INFO", "no dist/ build to scan for sentinels (run npm run build first)"))

    # A8 - German-sober: no exclamation-marketing (heuristic) ----------------
    if page:
        body = re.sub(r"<style>.*?</style>|<script>.*?</script>|---.*?---", "", page, flags=re.S)
        # Count true exclamation marks only: exclude code operators (!=, !==).
        bangs = len(re.findall(r"!(?!=)", body))
        if bangs:
            rows.append(("WARN", f"{bangs} exclamation mark(s) in copy (German-sober tone: prefer none)"))

    return rows, hard_fail, hero_fingerprint(page)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="audit a single slug")
    ap.add_argument("--strict", action="store_true", help="exit 1 on hard fails")
    args = ap.parse_args()

    if not SITES_DIR.exists():
        print(f"no sites dir at {SITES_DIR}", file=sys.stderr)
        return 2

    slugs = [args.only] if args.only else sorted(p.name for p in SITES_DIR.iterdir() if p.is_dir())

    any_hard = False
    fingerprints: dict[str, frozenset[str]] = {}
    for slug in slugs:
        print(f"\n\033[1m{slug}\033[0m")
        rows, hard, fp = audit_site(slug, args.strict)
        fingerprints[slug] = fp
        any_hard = any_hard or hard
        for kind, msg in rows:
            print(f"  {tag(kind)}  {msg}")

    # Per-SET hero diversity (List A1) --------------------------------------
    if len(fingerprints) > 1:
        print("\n\033[1mper-SET hero diversity\033[0m")
        seen: dict[frozenset[str], list[str]] = {}
        for slug, fp in fingerprints.items():
            if fp:
                seen.setdefault(fp, []).append(slug)
        clones = [g for g in seen.values() if len(g) > 1]
        if clones:
            for g in clones:
                print(f"  {tag('WARN')}  {' + '.join(g)} share one hero structure; diversify so the SET is not one template")
        else:
            print(f"  {tag('PASS')}  each audited site has a distinct hero structure")

    print(f"\n{DIM}advisory only - the human/visual call (grade, register, would-the-owner-pay) stays the gate.{RST}")
    if any_hard and args.strict:
        print(f"{RED}hard fails present (--strict).{RST}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
