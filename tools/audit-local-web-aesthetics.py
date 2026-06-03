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
  CAN (mechanical):   pure-#fff / pure-#000 base; banned default as the PRIMARY
                      display font; a raw [BITTE PRÜFEN] sentinel in the built
                      HTML; missing "Bilder: Pexels" credit; whether a photo
                      grade rule EXISTS; exclamation marks in visible copy; two
                      sites sharing one hero structure.
  CANNOT (your eye):  is the grade actually warm + consistent; is the type
                      confident-BIG in context; register fit; logo/palette
                      harmony; recognition-before-impression. The messages below
                      report only what was measured and hedge the rest.

Usage:
  uv run tools/audit-local-web-aesthetics.py                  # all sites, advisory
  uv run tools/audit-local-web-aesthetics.py --only praxis-uslu
  uv run tools/audit-local-web-aesthetics.py --strict         # exit 1 on hard fails

Hard fails (only under --strict): raw [BITTE PRÜFEN] in dist, pure-white or
pure-black base colour, a banned default as the primary display font.
"""
from __future__ import annotations

import argparse
import re
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "workspace" / "projects" / "local-web" / "app"
SITES_DIR = APP / "src" / "sites"
PAGES_DIR = APP / "src" / "pages"
DIST = APP / "dist"

BANNED_PRIMARY_FONTS = ["inter", "roboto", "arial", "space grotesk", "system-ui"]
PURE_WHITE = {"#fff", "#ffffff", "white"}
PURE_BLACK = {"#000", "#000000", "black"}
# the raw sentinel, in the forms it could reach the built HTML
SENTINELS = ["BITTE PRÜFEN", "BITTE PR&Uuml;FEN", "BITTE PR&#220;FEN"]
NEAR_CLONE_JACCARD = 0.7

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


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def token_value(css: str, var: str) -> str | None:
    """First value of a CSS custom property, lowercased, comment-stripped."""
    m = re.search(rf"{re.escape(var)}\s*:\s*([^;]+);", css)
    if not m:
        return None
    return strip_comments(m.group(1)).strip().lower()


def luminance(hexv: str | None) -> float | None:
    """WCAG relative luminance of a #rgb / #rrggbb colour, else None."""
    if not hexv:
        return None
    h = hexv.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdef" for c in h):
        return None
    chans = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = chans
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def polarity(L: float | None) -> str:
    if L is None:
        return "?"
    if L < 0.22:
        return "dark"
    if L > 0.6:
        return "light"
    return "mid"


def read_page(slug: str) -> str:
    """A site's page source, covering both flat and folder layouts."""
    return read(PAGES_DIR / f"{slug}.astro") or read(PAGES_DIR / slug / "index.astro")


def hero_fingerprint(astro: str) -> frozenset[str]:
    """Structural classes in the hero region; near-equal sets = cloned hero."""
    flat = " ".join(re.findall(r'class="([^"]+)"', astro))
    toks = set(
        re.findall(
            r"\b(?:hero__[a-z-]+|dh__[a-z-]+|band|bands|discipline-hero|trust__[a-z-]+)\b",
            flat,
        )
    )
    return frozenset(toks)


def hero_type_verdict(page: str) -> tuple[str, str] | None:
    """Max display weight + whether a large scale token appears, across ALL
    hero h1 / wordmark blocks (comment-stripped)."""
    blocks = re.findall(r"\.hero\s+h1\s*\{[^}]*\}|dh__wordmark\s*\{[^}]*\}", page, re.S)
    if not blocks:
        return None
    max_w = 0
    big = False
    for b in blocks:
        b = strip_comments(b)
        for m in re.finditer(r'"wght"\s*(\d+)|font-weight:\s*(\d+)', b):
            max_w = max(max_w, int(next(g for g in m.groups() if g)))
        if re.search(r"--text-(4xl|5xl|6xl|7xl)|clamp\(", b):
            big = True
    if max_w >= 560 and big:
        return ("PASS", f"hero h1 weight ~{max_w} + large scale (confirm BIG-in-context by eye)")
    return ("WARN", f"hero h1 weight {max_w or '?'} / large-scale={big}: may read 'nice' not BIG; push weight>=600 + scale")


def audit_site(slug: str) -> tuple[list[tuple[str, str]], bool, frozenset[str]]:
    rows: list[tuple[str, str]] = []
    hard_fail = False
    theme = read(SITES_DIR / slug / "theme.css")
    page = read_page(slug)
    dist_html = read(DIST / slug / "index.html")

    # B3 - base colours: not pure white/black; report value + polarity --------
    for name, var, pure in (("paper", "--color-paper", PURE_WHITE), ("ink", "--color-ink", PURE_BLACK)):
        v = token_value(theme, var)
        if v in pure:
            rows.append(("FAIL", f"{name} is pure {('white' if pure is PURE_WHITE else 'black')} ({v}); use a warm off-white / near-black"))
            hard_fail = True
        elif v:
            rows.append(("PASS", f"{name} {v} (L={luminance(v):.2f}, {polarity(luminance(v))} base; warmth is the eyeball call)"))

    # B3 - one disciplined accent (advisory list, not a verdict) --------------
    accents = sorted(set(re.findall(r"--color-accent[\w-]*", theme)))
    if accents:
        rows.append(("INFO", f"accent tokens: {', '.join(accents)} (confirm ONE accent reads, not a rainbow)"))

    # B1 - non-default PRIMARY display font -----------------------------------
    disp = token_value(theme, "--font-display") or ""
    primary = disp.split(",")[0].strip().strip('"').strip("'")
    if any(b in primary for b in BANNED_PRIMARY_FONTS):
        rows.append(("FAIL", f"primary display font is a banned default: {primary}"))
        hard_fail = True
    elif primary:
        rows.append(("PASS", f"display font {primary} (non-default)"))

    # B1 - confident-big hero type (heuristic) -------------------------------
    if page:
        v = hero_type_verdict(page)
        if v:
            rows.append(v)

    # B4 - a photo grade rule exists (presence only; warmth is your eye) ------
    if page:
        if re.search(r"filter:\s*[^;]*(?:sepia|saturate)", page):
            rows.append(("PASS", "a sepia/saturate grade filter exists (confirm warm + consistent by eye)"))
        else:
            rows.append(("WARN", "no CSS grade filter found; photos may not share one warm grade"))

    # A5 - no raw [BITTE PRÜFEN] sentinel on the pitchable page ---------------
    if dist_html:
        n = sum(dist_html.count(s) for s in SENTINELS)
        if n:
            rows.append(("FAIL", f"{n} raw [BITTE PRÜFEN] sentinel(s) in built HTML; render quiet 'auf Anfrage' / omit"))
            hard_fail = True
        else:
            rows.append(("PASS", "no raw [BITTE PRÜFEN] sentinel in built HTML"))
        rows.append(("PASS", "Pexels credit present") if "Bilder: Pexels" in dist_html else ("WARN", "no 'Bilder: Pexels' credit found"))
    else:
        rows.append(("INFO", "no dist/ build to scan for sentinels (run npm run build first)"))

    # A8 - German-sober: no exclamation-marketing (heuristic) ----------------
    if page:
        body = re.sub(r"<style\b[^>]*>.*?</style>|<script\b[^>]*>.*?</script>|^---.*?---", "", page, flags=re.S | re.M)
        bangs = len(re.findall(r"!(?!=)", body))  # exclude code operators !=, !==
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
        rows, hard, fp = audit_site(slug)
        fingerprints[slug] = fp
        any_hard = any_hard or hard
        for kind, msg in rows:
            print(f"  {tag(kind)}  {msg}")

    # Per-SET hero diversity (List A1): exact + near-clone via Jaccard --------
    if len(fingerprints) > 1:
        print("\n\033[1mper-SET hero diversity\033[0m")
        flagged = False
        for a, b in combinations(sorted(fingerprints), 2):
            fa, fb = fingerprints[a], fingerprints[b]
            if not fa or not fb:
                continue
            j = len(fa & fb) / len(fa | fb)
            if j == 1.0:
                print(f"  {tag('WARN')}  {a} + {b} share an IDENTICAL hero structure; give one a distinct hero")
                flagged = True
            elif j >= NEAR_CLONE_JACCARD:
                print(f"  {tag('WARN')}  {a} + {b} share most of one hero structure (Jaccard {j:.2f}); diversify")
                flagged = True
        if not flagged:
            print(f"  {tag('PASS')}  each audited site has a distinct hero structure")

    print(f"\n{DIM}advisory only - the human/visual call (grade, register, would-the-owner-pay) stays the gate.{RST}")
    if any_hard and args.strict:
        print(f"{RED}hard fails present (--strict).{RST}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
