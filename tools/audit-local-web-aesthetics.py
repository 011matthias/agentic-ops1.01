# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
audit-local-web-aesthetics.py - advisory List-B (visual-craft) pre-ship pass.

Prints a per-site checklist of the mechanically-detectable parts of List B
(see .claude/skills/skil_web-build/modules/CONCEIVE.md "The two standards"),
the quantified thresholds in references/design-thresholds.md, the motion
envelope in references/motion-craft.md, and the CONCEIVE.md section 6
saturation bands. Findings cite stable rule IDs (rule:web-*) so they map to
exactly one prose rule. This is ADVISORY by default: the human/visual call
stays the gate. Under --strict (which tools/local-web-deploy.py uses as a
pre-deploy gate) hard-fail classes exit 1.

What it can and cannot judge:
  CAN (mechanical):   pure-#fff / pure-#000 base; banned/saturated display
                      fonts; cream-band base colour (OKLCH); tracking floor;
                      hero clamp ceiling + ratio; line-length band; muted-text
                      contrast; motion-envelope violations; reveal-safety;
                      JSON-LD presence; raw [BITTE PRUEFEN] sentinel; Pexels
                      credit; exclamation marks; cloned hero structures.
  CANNOT (your eye):  is the grade actually warm + consistent; is the type
                      confident-BIG in context; register fit; logo/palette
                      harmony; recognition-before-impression. The messages
                      below report only what was measured and hedge the rest.

Usage:
  uv run tools/audit-local-web-aesthetics.py                  # all sites, advisory
  uv run tools/audit-local-web-aesthetics.py --only praxis-uslu
  uv run tools/audit-local-web-aesthetics.py --strict         # exit 1 on hard fails
  uv run tools/audit-local-web-aesthetics.py --persist        # snapshot scores to .critique/
  uv run tools/audit-local-web-aesthetics.py --trend          # last 5 scores per site

Hard fails (only under --strict): raw [BITTE PRUEFEN] in dist, pure-white or
pure-black base colour, a banned default as the primary display font.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "workspace" / "projects" / "local-web" / "app"
SITES_DIR = APP / "src" / "sites"
PAGES_DIR = APP / "src" / "pages"
GLOBAL_CSS = APP / "src" / "styles" / "global.css"
DIST = APP / "dist"
SNAP_DIR = REPO / "workspace" / "projects" / "local-web" / ".critique"
SNAP_KEEP = 10  # snapshots retained per slug (rule_no_file_bloat supersession)

# Hard bans: exact family match (substring matching false-positived on
# legitimate families containing "inter"/"arial"). rule:web-type-banned-defaults
BANNED_PRIMARY_FONTS = {"inter", "roboto", "arial", "space grotesk", "system-ui"}
# Saturation tier (CONCEIVE.md section 6, rule:web-type-saturation-fonts) - WARN,
# needs the section 3 selection-procedure trace in the BRIEF.
SATURATED_FONTS = {
    "fraunces", "playfair display", "cormorant", "lora", "crimson",
    "crimson text", "crimson pro", "newsreader", "syne", "space mono",
    "dm sans", "dm serif display", "dm serif text", "outfit",
    "plus jakarta sans", "instrument sans", "instrument serif",
}
SATURATED_PREFIXES = ("ibm plex", "cormorant", "crimson", "dm serif")
CREAM_TOKEN_NAMES = re.compile(r"--[\w-]*(cream|sand|bone|linen|parchment)\b", re.I)
PURE_WHITE = {"#fff", "#ffffff", "white"}
PURE_BLACK = {"#000", "#000000", "black"}
# the raw sentinel, in the forms it could reach the built HTML
SENTINELS = ["BITTE PRÜFEN", "BITTE PR&Uuml;FEN", "BITTE PR&#220;FEN"]
NEAR_CLONE_JACCARD = 0.7
# Ambient loops are exempt from the 300ms ceiling
# (design-thresholds.md rule:web-motion-ambient-exemption).
AMBIENT_MS = 5000
AMBIENT_NAMES = re.compile(r"kenburns|ken-burns|marquee|ambient|drift", re.I)
LAYOUT_PROPS = re.compile(r"\b(?:max-|min-)?(?:width|height)\b|\btop\b|\bleft\b|\bright\b|\bbottom\b|\bmargin\b|\bpadding\b")

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


def hex_to_rgb(hexv: str | None) -> tuple[float, float, float] | None:
    if not hexv:
        return None
    h = hexv.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdef" for c in h):
        return None
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(hexv: str | None) -> float | None:
    """WCAG relative luminance of a #rgb / #rrggbb colour, else None."""
    rgb = hex_to_rgb(hexv)
    if rgb is None:
        return None
    chans = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    r, g, b = chans
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str | None, hex_b: str | None) -> float | None:
    la, lb = luminance(hex_a), luminance(hex_b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def oklch(hexv: str | None) -> tuple[float, float, float] | None:
    """sRGB hex -> OKLCH (L, C, hue degrees). Ottosson's OKLab transform."""
    rgb = hex_to_rgb(hexv)
    if rgb is None:
        return None
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    r, g, b = lin
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    h = math.degrees(math.atan2(bb, a)) % 360
    return (L, C, h)


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


def style_blocks(astro: str) -> str:
    """The CSS inside an .astro page's <style> blocks, comment-stripped."""
    return strip_comments("\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", astro, re.S)))


def declarations(css: str):
    """Yield individual CSS declarations (property: value) for context checks."""
    for decl in re.split(r"[;{}]", css):
        decl = decl.strip()
        if ":" in decl:
            yield decl


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


def font_checks(theme: str) -> tuple[list[tuple[str, str]], bool]:
    rows: list[tuple[str, str]] = []
    hard = False
    disp = token_value(theme, "--font-display") or ""
    primary = re.sub(r"\s+", " ", disp.split(",")[0].strip().strip('"').strip("'")).lower()
    # fontsource variable faces register as "<family> variable" — match the family
    primary = re.sub(r"\s+variable$", "", primary)
    if not primary:
        return rows, hard
    if primary in BANNED_PRIMARY_FONTS:
        rows.append(("FAIL", f"primary display font is a banned default: {primary} [web-type-banned-defaults]"))
        hard = True
    elif primary in SATURATED_FONTS or primary.startswith(SATURATED_PREFIXES):
        rows.append(("WARN", f"display font {primary} is on the saturation tier; BRIEF needs the 4-step selection trace [web-type-saturation-fonts]"))
    else:
        rows.append(("PASS", f"display font {primary} (non-default, off the saturation tier)"))
    return rows, hard


def base_colour_checks(theme: str) -> tuple[list[tuple[str, str]], bool]:
    rows: list[tuple[str, str]] = []
    hard = False
    paper = token_value(theme, "--color-paper")
    ink = token_value(theme, "--color-ink")
    for name, v, pure in (("paper", paper, PURE_WHITE), ("ink", ink, PURE_BLACK)):
        if v in pure:
            rows.append(("FAIL", f"{name} is pure {('white' if pure is PURE_WHITE else 'black')} ({v}); use an off-white / near-black [web-color-one-accent]"))
            hard = True
        elif v:
            L = luminance(v)
            rows.append(("PASS", f"{name} {v} (L={L:.2f}, {polarity(L)} base; the base CHOICE is a BRIEF call)" if L is not None else f"{name} {v} (non-hex; polarity unmeasured)"))
    # Cream-band detector (CONCEIVE.md section 6, rule:web-color-cream-band)
    ok = oklch(paper)
    if ok:
        L, C, h = ok
        if 0.84 <= L <= 0.97 and C >= 0.02 and 40 <= h <= 100:
            rows.append(("WARN", f"paper sits in the 2026 cream/sand saturation band (OKLCH L={L:.2f} C={C:.3f} h={h:.0f}); confirm the BRIEF justifies a warm base [web-color-cream-band]"))
        elif 0.005 <= C <= 0.015:
            rows.append(("PASS", f"paper tint C={C:.3f} sits in the legitimate tinted-neutral range [web-color-cream-band]"))
    if CREAM_TOKEN_NAMES.search(theme):
        rows.append(("WARN", "theme has a cream/sand/bone/linen/parchment token NAME (a tell by itself) [web-color-cream-band]"))
    # Muted-text contrast (design-thresholds.md rule:web-color-muted-contrast)
    muted = token_value(theme, "--color-muted")
    cr = contrast_ratio(muted, paper)
    if cr is not None:
        if cr < 4.5:
            rows.append(("WARN", f"muted text on paper is {cr:.2f}:1 (<4.5:1) - the most common shipped a11y bug [web-color-muted-contrast]"))
        else:
            rows.append(("PASS", f"muted text on paper {cr:.2f}:1 (>=4.5:1) [web-color-muted-contrast]"))
    accents = sorted(set(re.findall(r"--color-accent[\w-]*", theme)))
    if accents:
        rows.append(("INFO", f"accent tokens: {', '.join(accents)} (confirm ONE accent reads, not a rainbow)"))
    return rows, hard


def threshold_checks(css: str) -> list[tuple[str, str]]:
    """design-thresholds.md scans over a site's CSS (theme + page styles)."""
    rows: list[tuple[str, str]] = []
    # tracking floor
    floors = [v for v in re.findall(r"letter-spacing\s*:\s*(-\d*\.?\d+)em", css) if float(v) < -0.04]
    if floors:
        rows.append(("WARN", f"letter-spacing tighter than -0.04em ({', '.join(sorted(set(floors)))}em); -0.02 to -0.03 is plenty [web-type-tracking-floor]"))
    # hero clamp ceiling + ratio (font-size clamps only)
    for m in re.finditer(r"font-size\s*:\s*clamp\(\s*([\d.]+)rem[^,]*,[^,]+,\s*([\d.]+)rem\s*\)", css):
        lo, hi = float(m.group(1)), float(m.group(2))
        if hi > 6.0:
            rows.append(("WARN", f"font-size clamp() max {hi}rem exceeds the 6rem ceiling - shouting, not confident [web-type-hero-clamp-ceiling]"))
        if lo > 0 and hi / lo > 2.5:
            rows.append(("WARN", f"font-size clamp() max/min ratio {hi / lo:.1f}x exceeds 2.5x; browser zoom/reflow breaks [web-type-clamp-ratio]"))
    # line length ceiling. Only the too-long side: a SHORT ch max-width on a
    # headline/sub is deliberate shaping, not a readability bug.
    for v in re.findall(r"max-width\s*:\s*(\d+(?:\.\d+)?)ch", css):
        ch = float(v)
        if ch > 78:
            rows.append(("WARN", f"max-width {ch:g}ch exceeds the 78ch readability ceiling (target 65-75) [web-type-line-length]"))
    return rows


def motion_checks(css: str) -> list[tuple[str, str]]:
    """references/motion-craft.md envelope scan over a site's CSS."""
    rows: list[tuple[str, str]] = []
    slow: set[str] = set()
    for decl in declarations(css):
        prop = decl.split(":", 1)[0].strip().lower()
        if not prop.startswith(("transition", "animation")):
            continue
        if AMBIENT_NAMES.search(decl):
            continue  # ambient exemption [web-motion-ambient-exemption]
        for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(ms|s)\b", decl):
            ms = float(num) * (1000 if unit == "s" else 1)
            if 300 < ms < AMBIENT_MS:
                slow.add(f"{num}{unit}")
        if prop.startswith("transition"):
            if re.search(r"\bease-out\b", decl) and "cubic-bezier" not in decl:
                rows.append(("WARN", f"built-in ease-out in '{decl[:60]}'; use a custom cubic-bezier [web-motion-easing-custom]"))
            if prop in ("transition", "transition-property") and LAYOUT_PROPS.search(decl.split(":", 1)[1]):
                rows.append(("WARN", f"transition animates a layout property in '{decl[:60]}'; transform/opacity only [web-motion-composite-only]"))
    if slow:
        rows.append(("WARN", f"interaction duration(s) over 300ms: {', '.join(sorted(slow))} [web-motion-duration-ceiling]"))
    if re.search(r"scale\(\s*0(?:\.0+)?\s*\)", css):
        rows.append(("WARN", "scale(0) start; begin from 0.95+ [web-motion-no-scale-zero]"))
    return rows


def reveal_safety_check(page_css: str, global_css: str) -> tuple[str, str] | None:
    """rule:web-motion-reveal-safety - content hidden for a reveal transition
    must have a no-JS / prefers-reduced-motion exposure path."""
    combined = page_css + "\n" + global_css
    hides = re.search(r"\[data-reveal\][^{]*\{[^}]*opacity\s*:\s*0", combined)
    if not hides:
        return None
    exposed = re.search(r"\.no-js\b[^{]*\[data-reveal\]|prefers-reduced-motion[^{]*\{[^@]*\[data-reveal\]", combined, re.S)
    if exposed:
        return ("PASS", "reveal-hidden content has a no-JS / reduced-motion exposure path [web-motion-reveal-safety]")
    return ("WARN", "content is hidden for scroll-reveal with no no-JS / reduced-motion exposure path - it ships blank in headless/hidden tabs [web-motion-reveal-safety]")


def audit_site(slug: str, global_css: str) -> tuple[list[tuple[str, str]], bool, frozenset[str]]:
    rows: list[tuple[str, str]] = []
    hard_fail = False
    theme = strip_comments(read(SITES_DIR / slug / "theme.css"))
    page = read_page(slug)
    page_css = style_blocks(page)
    site_css = theme + "\n" + page_css
    dist_html = read(DIST / slug / "index.html")

    r, h = base_colour_checks(theme)
    rows += r
    hard_fail |= h

    r, h = font_checks(theme)
    rows += r
    hard_fail |= h

    # B1 - confident-big hero type (heuristic) -------------------------------
    if page:
        v = hero_type_verdict(page)
        if v:
            rows.append(v)

    # design-thresholds + motion envelope over this site's CSS ----------------
    rows += threshold_checks(site_css)
    rows += motion_checks(site_css)
    if page:
        v = reveal_safety_check(page_css, global_css)
        if v:
            rows.append(v)
        if "prefers-reduced-motion" not in site_css and "prefers-reduced-motion" not in global_css and re.search(r"animation|transition", site_css):
            rows.append(("WARN", "site animates but no prefers-reduced-motion block found in its CSS or global.css [web-motion-reduced-motion]"))

    # B4 - a photo grade rule exists (presence only; warmth is your eye) ------
    if page:
        if re.search(r"filter:\s*[^;]*(?:sepia|saturate)", page):
            rows.append(("PASS", "a sepia/saturate grade filter exists (confirm warm + consistent by eye)"))
        else:
            rows.append(("WARN", "no CSS grade filter found; photos may not share one warm grade"))

    # A5 - no raw [BITTE PRUEFEN] sentinel on the pitchable page --------------
    if dist_html:
        n = sum(dist_html.count(s) for s in SENTINELS)
        if n:
            rows.append(("FAIL", f"{n} raw [BITTE PRÜFEN] sentinel(s) in built HTML; render quiet 'auf Anfrage' / omit"))
            hard_fail = True
        else:
            rows.append(("PASS", "no raw [BITTE PRÜFEN] sentinel in built HTML"))
        rows.append(("PASS", "Pexels credit present") if "Bilder: Pexels" in dist_html else ("WARN", "no 'Bilder: Pexels' credit found"))
        # BUILD section 1 - LocalBusiness-family JSON-LD ----------------------
        rows.append(("PASS", "JSON-LD block present in built HTML") if "application/ld+json" in dist_html
                    else ("WARN", "no application/ld+json in built HTML; BUILD section 1 mandates LocalBusiness-family structured data"))
    else:
        rows.append(("INFO", "no dist/ build to scan for sentinels (run npm run build first)"))

    # A8 - German-sober: no exclamation-marketing (heuristic) ----------------
    if page:
        body = re.sub(r"<style\b[^>]*>.*?</style>|<script\b[^>]*>.*?</script>|^---.*?---", "", page, flags=re.S | re.M)
        bangs = len(re.findall(r"!(?!=)", body))  # exclude code operators !=, !==
        if bangs:
            rows.append(("WARN", f"{bangs} exclamation mark(s) in copy (German-sober tone: prefer none)"))

    return rows, hard_fail, hero_fingerprint(page)


def score(rows: list[tuple[str, str]]) -> int:
    fails = sum(1 for k, _ in rows if k == "FAIL")
    warns = sum(1 for k, _ in rows if k == "WARN")
    return max(0, 100 - 15 * fails - 5 * warns)


def persist_snapshot(slug: str, rows: list[tuple[str, str]]) -> None:
    """Fire-and-forget per-slug snapshot; prune beyond SNAP_KEEP (supersession)."""
    try:
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "slug": slug, "ts": ts, "score": score(rows),
            "fail": sum(1 for k, _ in rows if k == "FAIL"),
            "warn": sum(1 for k, _ in rows if k == "WARN"),
            "rows": rows,
        }
        (SNAP_DIR / f"{ts}__{slug}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        old = sorted(SNAP_DIR.glob(f"*__{slug}.json"))
        for p in old[:-SNAP_KEEP]:
            p.unlink(missing_ok=True)
    except OSError as e:
        print(f"  {tag('INFO')}  snapshot persist failed (non-blocking): {e}")


def print_trend() -> int:
    if not SNAP_DIR.exists():
        print("no snapshots yet - run with --persist first")
        return 0
    by_slug: dict[str, list[tuple[str, int]]] = {}
    for p in sorted(SNAP_DIR.glob("*__*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            by_slug.setdefault(d["slug"], []).append((d["ts"], d["score"]))
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    for slug in sorted(by_slug):
        last = by_slug[slug][-5:]
        line = " -> ".join(str(s) for _, s in last)
        print(f"  {slug}: {line}   (latest {last[-1][0]})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="audit a single slug")
    ap.add_argument("--strict", action="store_true", help="exit 1 on hard fails")
    ap.add_argument("--persist", action="store_true", help="snapshot per-site scores to .critique/")
    ap.add_argument("--trend", action="store_true", help="print last 5 scores per site and exit")
    args = ap.parse_args()

    if args.trend:
        return print_trend()

    if not SITES_DIR.exists():
        print(f"no sites dir at {SITES_DIR}", file=sys.stderr)
        return 2

    global_css = strip_comments(read(GLOBAL_CSS))
    slugs = [args.only] if args.only else sorted(p.name for p in SITES_DIR.iterdir() if p.is_dir())

    any_hard = False
    fingerprints: dict[str, frozenset[str]] = {}
    for slug in slugs:
        print(f"\n\033[1m{slug}\033[0m")
        rows, hard, fp = audit_site(slug, global_css)
        fingerprints[slug] = fp
        any_hard = any_hard or hard
        for kind, msg in rows:
            print(f"  {tag(kind)}  {msg}")
        print(f"  {DIM}score {score(rows)}/100 (100 - 15*FAIL - 5*WARN){RST}")
        if args.persist:
            persist_snapshot(slug, rows)

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
