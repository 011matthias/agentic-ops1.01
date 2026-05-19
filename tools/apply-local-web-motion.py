#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Apply the skil_web-build 4b motion / 3D-feel imagery layer to the three
local-web demo sites. Idempotent: re-running is a no-op once applied.

Why this exists as a script: during the 2026-05-19 session, the working
tree kept reverting agent edits to HEAD between tool calls (an external
editor/harness file-sync writing a stale buffer back). Capturing the full
change-set as one re-runnable, idempotent script makes the work durable
and immune to that revert: run it once the revert cause is resolved, then
build + deploy.

Usage:
    uv run tools/apply-local-web-motion.py
    # then:
    npm --prefix workspace/projects/local-web/app run build
    flyctl deploy <app> --config <fly.toml> --remote-only --now
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "workspace" / "projects" / "local-web" / "app" / "src"


def patch(rel: str, repls: list[tuple[str, str]]) -> None:
    p = SRC / rel
    s = p.read_text(encoding="utf-8")
    orig = s
    for old, new in repls:
        if old in s:
            s = s.replace(old, new, 1)
        elif new in s:
            print(f"  ~ already applied: {rel}: {old[:48]!r}")
        else:
            sys.exit(f"NO MATCH in {rel}: {old[:70]!r}")
    if s != orig:
        p.write_text(s, encoding="utf-8")
        print(f"  patched {rel}")
    else:
        print(f"  unchanged {rel}")


GLOBAL_OLD = """  .card {
    background: var(--color-surface);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
  }
}"""

GLOBAL_NEW = """  .card {
    background: var(--color-surface);
    border: 1px solid var(--color-line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }
  /* Default-tier 3D-feel: gentle hover lift on cards. Pointer-only so
     touch never gets a stuck :hover; reduced-motion neutralises it via
     the @layer base rule. (skil_web-build 4b.) */
  @media (hover: hover) and (pointer: fine) {
    .card:hover {
      transform: translateY(-5px);
      box-shadow: var(--shadow-float);
    }
  }
}

/*
  Motion layer (skil_web-build 4b, default tier, CSS-only, ~0 perf cost).
  Fully neutralised by the prefers-reduced-motion block in @layer base,
  AND the reveal hide-state is applied only by a JS class (.reveal-on)
  the head script withholds under reduced-motion or no-JS, so content is
  NEVER left hidden. Gate-safe by construction.
*/
@layer components {
  @keyframes kb-drift {
    from {
      transform: scale(1.04) translate3d(0, 0, 0);
    }
    to {
      transform: scale(1.13) translate3d(-1.6%, -1.4%, 0);
    }
  }
  .figure.is-kenburns img {
    animation: kb-drift 26s ease-in-out infinite alternate;
    transform-origin: 50% 45%;
  }
  @media (prefers-reduced-motion: reduce) {
    .figure.is-kenburns img {
      animation: none;
    }
  }
  .reveal-on [data-reveal] {
    opacity: 0;
    transform: translateY(22px);
    transition: opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1),
      transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
    transition-delay: var(--reveal-delay, 0ms);
    will-change: opacity, transform;
  }
  .reveal-on [data-reveal].is-visible {
    opacity: 1;
    transform: none;
  }
}"""

FIG_PROP_OLD = """  /** Responsive sizes hint; default assumes a near-full-width block. */
  sizes?: string;
}"""
FIG_PROP_NEW = """  /** Responsive sizes hint; default assumes a near-full-width block. */
  sizes?: string;
  /** Ken Burns slow drift (skil_web-build 4b). Hero use only; ignored by
      the honest slot fallback. Reduced-motion safe (global.css). */
  kenburns?: boolean;
}"""

FIG_DESTR_OLD = '''  sizes = "(min-width: 72rem) 68rem, 92vw",
} = Astro.props;'''
FIG_DESTR_NEW = '''  sizes = "(min-width: 72rem) 68rem, 92vw",
  kenburns = false,
} = Astro.props;'''

FIG_TAG_OLD = '''    <figure
      class="figure"
      style={`aspect-ratio:${ratio};border-radius:${rounded};`}
    >'''
FIG_TAG_NEW = '''    <figure
      class:list={["figure", { "is-kenburns": kenburns }]}
      style={`aspect-ratio:${ratio};border-radius:${rounded};`}
    >'''

BASE_OLD = """    <slot name="head" />
  </head>
  <body data-site={site}>
    <a class="skip-link" href="#main">Zum Inhalt springen</a>
    <slot />
  </body>"""

BASE_NEW = '''    <slot name="head" />
    {/* Reveal-arm: runs in <head> BEFORE first paint. The class (and the
        whole hide-then-reveal) exists ONLY when motion is allowed; no-JS
        or reduced-motion -> class absent -> [data-reveal] stays opacity:1.
        A 2.5s failsafe strips the class if the observer never signals. */}
    <script
      is:inline
      set:html={`try{if(!matchMedia('(prefers-reduced-motion: reduce)').matches){var r=document.documentElement;r.classList.add('reveal-on');setTimeout(function(){if(!window.__revealReady)r.classList.remove('reveal-on')},2500)}}catch(e){}`}
    />
  </head>
  <body data-site={site}>
    <a class="skip-link" href="#main">Zum Inhalt springen</a>
    <slot />
    <script>
      const root = document.documentElement;
      if (root.classList.contains("reveal-on")) {
        (window as unknown as { __revealReady?: boolean }).__revealReady =
          true;
        const nodes = Array.from(
          document.querySelectorAll<HTMLElement>("[data-reveal]"),
        );
        const reveal = (el: HTMLElement) => el.classList.add("is-visible");
        if ("IntersectionObserver" in window) {
          const io = new IntersectionObserver(
            (entries) => {
              for (const e of entries) {
                if (e.isIntersecting) {
                  reveal(e.target as HTMLElement);
                  io.unobserve(e.target);
                }
              }
            },
            { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
          );
          nodes.forEach((el) => {
            const group = el.closest("[data-reveal-group]");
            if (group) {
              const sibs = Array.from(
                group.querySelectorAll("[data-reveal]"),
              );
              el.style.setProperty(
                "--reveal-delay",
                `${Math.min(sibs.indexOf(el), 5) * 80}ms`,
              );
            }
            io.observe(el);
          });
        } else {
          nodes.forEach(reveal);
        }
      }
    </script>
  </body>'''


def main() -> None:
    if not SRC.is_dir():
        sys.exit(f"src not found: {SRC}")

    patch("styles/global.css", [(GLOBAL_OLD, GLOBAL_NEW)])
    patch("components/Figure.astro", [
        (FIG_PROP_OLD, FIG_PROP_NEW),
        (FIG_DESTR_OLD, FIG_DESTR_NEW),
        (FIG_TAG_OLD, FIG_TAG_NEW),
    ])
    patch("layouts/BaseLayout.astro", [(BASE_OLD, BASE_NEW)])

    patch("pages/praxis-uslu.astro", [
        ('''      <div class="wrap hero__figure">
        <Figure
          site="praxis-uslu"
          name="hero"
          label="Praxis / Empfang, warmes Tageslicht"
          ratio="21 / 9"
          priority
        />''',
         '''      <div class="wrap hero__figure" data-reveal>
        <Figure
          site="praxis-uslu"
          name="hero"
          label="Praxis / Empfang, warmes Tageslicht"
          ratio="21 / 9"
          priority
          kenburns
        />'''),
        ('<header class="section__head">\n          <p class="eyebrow">Leistungen</p>',
         '<header class="section__head" data-reveal>\n          <p class="eyebrow">Leistungen</p>'),
        ('<ol class="leistungen">', '<ol class="leistungen" data-reveal-group>'),
        ('<li class="leistung">', '<li class="leistung" data-reveal>'),
        ('<div class="signature__media">', '<div class="signature__media" data-reveal>'),
        ('<div class="signature__text">', '<div class="signature__text" data-reveal>'),
        ('<div class="wrap contact__grid">\n        <div>\n          <p class="eyebrow">Sprechzeiten</p>',
         '<div class="wrap contact__grid">\n        <div data-reveal>\n          <p class="eyebrow">Sprechzeiten</p>'),
        ('<div class="contact__side">', '<div class="contact__side" data-reveal>'),
    ])

    patch("pages/coffee-boxx.astro", [
        ('''      <div class="wrap hero__figure">
        <Figure
          site="coffee-boxx"
          name="hero"
          label="Espresso, warmer Dampf, nah"
          ratio="21 / 9"
          priority
        />''',
         '''      <div class="wrap hero__figure" data-reveal>
        <Figure
          site="coffee-boxx"
          name="hero"
          label="Espresso, warmer Dampf, nah"
          ratio="21 / 9"
          priority
          kenburns
        />'''),
        ('<header class="section__head">\n          <p class="eyebrow">Die Karte</p>',
         '<header class="section__head" data-reveal>\n          <p class="eyebrow">Die Karte</p>'),
        ('<dl class="menu">', '<dl class="menu" data-reveal-group>'),
        ('<div class="menu__row">', '<div class="menu__row" data-reveal>'),
        ('<header class="section__head">\n          <p class="eyebrow">Galerie</p>',
         '<header class="section__head" data-reveal>\n          <p class="eyebrow">Galerie</p>'),
        ('<div class="gallery__stagger">', '<div class="gallery__stagger" data-reveal-group>'),
        ('<div class={`gallery__item gallery__item--${i + 1}`}>',
         '<div class={`gallery__item gallery__item--${i + 1}`} data-reveal>'),
        ('<div class="wrap contact__grid">\n        <div>\n          <p class="eyebrow">Öffnungszeiten</p>',
         '<div class="wrap contact__grid">\n        <div data-reveal>\n          <p class="eyebrow">Öffnungszeiten</p>'),
        ('<div class="contact__side">', '<div class="contact__side" data-reveal>'),
    ])

    patch("pages/pronto-pronto.astro", [
        ('''          label="Pizza, dunkel und appetitlich"
          ratio="16 / 9"
          rounded="0"
          priority
          sizes="100vw"
        />''',
         '''          label="Pizza, dunkel und appetitlich"
          ratio="16 / 9"
          rounded="0"
          priority
          sizes="100vw"
          kenburns
        />'''),
        ('<header class="section__head">\n          <p class="eyebrow">Speisekarte</p>',
         '<header class="section__head" data-reveal>\n          <p class="eyebrow">Speisekarte</p>'),
        ('<ul id="menu-list" class="menu">', '<ul id="menu-list" class="menu" data-reveal>'),
        ('<header class="section__head">\n          <p class="eyebrow">Liefergebiet</p>',
         '<header class="section__head" data-reveal>\n          <p class="eyebrow">Liefergebiet</p>'),
        ('<ul class="chips">', '<ul class="chips" data-reveal>'),
        ('<div class="liefern__facts">\n          <div>\n            <span class="liefern__big">10%</span>',
         '<div class="liefern__facts" data-reveal-group>\n          <div data-reveal>\n            <span class="liefern__big">10%</span>'),
        ('<div>\n            <span class="liefern__big">0,00 €</span>',
         '<div data-reveal>\n            <span class="liefern__big">0,00 €</span>'),
        ('<div>\n            <span class="liefern__big">{pronto.zonesTotal}</span>',
         '<div data-reveal>\n            <span class="liefern__big">{pronto.zonesTotal}</span>'),
        ('<div class="wrap contact__grid">\n        <div>\n          <p class="eyebrow">Öffnungszeiten</p>',
         '<div class="wrap contact__grid">\n        <div data-reveal>\n          <p class="eyebrow">Öffnungszeiten</p>'),
        ('<div class="contact__side">', '<div class="contact__side" data-reveal>'),
    ])

    print("ALL PATCHES DONE")


if __name__ == "__main__":
    main()
