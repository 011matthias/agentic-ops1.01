# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx", "pillow"]
# ///
"""Slide grammar for the native deck family. Every builder is content-
parameterized and palette-aware; no deck copy lives in this file (specs own
the copy, DESIGN.md owns the content contracts). Geometry is ported verbatim
from the approved Overview's build source; the `overview` palette must
regenerate that deck visually unchanged.

Builders that are new relative to the approved Overview:
- problem(): the product-deck BEFORE-world slide (three stacked bands).
- hierarchy(focal_app=...): highlights one app card for product decks.
- success(stories=[...]): generalized to 2 or 3 story cards.
"""
import importlib.util
import pathlib

from PIL import Image
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

_here = pathlib.Path(__file__).parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _here / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load("tokens")
D = _load("draw")

INK, PAPER, NEUTRAL, MUTED, FAINT, LINE = T.INK, T.PAPER, T.NEUTRAL, T.MUTED, T.FAINT, T.LINE
ONINK, ONINK_SUB, NEUTRAL_DK = T.ONINK, T.ONINK_SUB, T.NEUTRAL_DK
DISPLAY, BODY, SEMI = T.DISPLAY, T.BODY, T.SEMI
SW, SH, MARGIN, CW, RIGHT = T.SW, T.SH, T.MARGIN, T.CW, T.RIGHT

# The platform truth for the where-it-sits slide (one place, not per spec).
PLATFORM_APPS = [
    ("mdh", "Market Data Hub", "market truth"),
    ("bst", "Brisken Smart Trading", "autonomous trading"),
    ("dcw", "Digital Co-Worker", "the manual middle"),
    ("open", "+ your own apps", "an open platform"),
]

CUSTOMER_LOGOS = [
    "google", "accenture", "equinor", "nike", "adm",
    "ab-inbev", "sulzer", "barry-callebaut", "zespri", "angus-chemical",
    "medmix", "entegris", "weyerhaeuser", "southwire", "yeti",
    "sothebys", "imax", "beautycounter", "global-brands", "asr-group",
]


class Deck:
    """One deck build: presentation + palette + assets dir."""

    def __init__(self, prs, palette, assets_dir):
        self.prs = prs
        self.pal = palette
        self.A = pathlib.Path(assets_dir)

    # ------------------------------------------------------------ shared bits
    def blank(self, bg=PAPER):
        return D.blank(self.prs, bg)

    def kicker(self, slide, x, y, txt, color=None, w=None):
        return D.text(slide, x, y, w or CW, 0.3,
                      [{"text": txt.upper(), "font": SEMI, "size": 12.5,
                        "color": color or self.pal.accent, "bold": True, "spc": 2.6}])

    def headline(self, slide, x, y, txt, size=40, w=None, color=INK):
        return D.text(slide, x, y, w or (CW - 0.4), 1.4,
                      [{"text": txt, "font": DISPLAY, "size": size, "color": color,
                        "line_spacing": 1.02}])

    def footer(self, slide, page):
        D.rect(slide, MARGIN, 6.92, CW, 0.014, fill=LINE)
        D.text(slide, MARGIN, 7.0, 8.0, 0.3,
               [{"text": "TreasuryCentral, powered by OnePilot", "font": BODY,
                 "size": 9, "color": FAINT, "spc": 0.4}])
        D.text(slide, RIGHT - 2.0, 7.0, 2.0, 0.3,
               [{"text": f"{page:02d}", "font": BODY, "size": 9, "color": FAINT,
                 "align": PP_ALIGN.RIGHT}])

    def brand_mark(self, slide, dark=False, x=None, y=6.86, h=0.30):
        logo = self.A / ("brisken_reversed.png" if dark else "brisken_dark.png")
        iw, ih = Image.open(logo).size
        w = h * (iw / ih)
        xx = (RIGHT - w) if x is None else x
        slide.shapes.add_picture(str(logo), D.IN(xx), D.IN(y), D.IN(w), D.IN(h))

    def card(self, slide, x, y, w, h, label, body, focal=False, on_ink=False, open_slot=False):
        pal = self.pal
        if open_slot:
            c = D.rect(slide, x, y, w, h, fill=None, line=pal.accent, line_w=1.25,
                       rounded=True, radius=0.07, dash="dash")
            body_c = (ONINK_SUB if on_ink else MUTED)
        elif on_ink:
            c = D.rect(slide, x, y, w, h, fill=NEUTRAL_DK, rounded=True, radius=0.07)
            body_c = ONINK_SUB
        else:
            c = D.rect(slide, x, y, w, h, fill=NEUTRAL, rounded=True, radius=0.07)
            body_c = MUTED
        D.rect(slide, x + 0.24, y + 0.26, 0.34, 0.05, fill=(pal.bright if focal else pal.accent))
        paras = [{"text": label, "font": SEMI, "size": 15.5,
                  "color": (INK if not on_ink else ONINK) if not open_slot else pal.accent,
                  "bold": True, "space_after": 6}]
        if body:
            paras.append({"text": body, "font": BODY, "size": 13.5, "color": body_c,
                          "line_spacing": 1.14})
        D.text(slide, x + 0.24, y + 0.44, w - 0.48, h - 0.6, paras)
        return c

    def chip(self, slide, x, y, w, h, label, fill=NEUTRAL, txt=INK, line=None):
        D.rect(slide, x, y, w, h, fill=fill, line=line, line_w=1.0, rounded=True, radius=0.14)
        D.text(slide, x + 0.12, y, w - 0.24, h,
               [{"text": label, "font": SEMI, "size": 12, "color": txt,
                 "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)

    def signature(self, slide):
        """Per-deck layout signature on light slides. The Overview carries none
        (parity with the approved deck)."""
        sig = self.pal.signature
        if sig == "rail-left":
            D.rect(slide, 0, 0, 0.07, SH, fill=self.pal.accent)
        elif sig == "bar-right":
            D.rect(slide, SW - 0.07, 0, 0.07, SH, fill=self.pal.accent)
        elif sig == "baseline":
            D.rect(slide, 0, SH - 0.07, SW, 0.07, fill=self.pal.accent)
        elif sig == "corner-dots":
            for i, c in enumerate([self.pal.accent, self.pal.accent, self.pal.bright]):
                D.rect(slide, SW - 0.72 + i * 0.18, 0.26, 0.09, 0.09,
                       fill=c, rounded=True, radius=0.5)

    # ------------------------------------------------------------ slides
    def cover(self, eyebrow, title, sub, tagline, title_size=72):
        s = self.blank(PAPER)
        D.text(s, MARGIN, 2.28, 8, 0.4,
               [{"text": eyebrow.upper(), "font": SEMI, "size": 13, "color": self.pal.accent,
                 "bold": True, "spc": 3.2}])
        D.text(s, MARGIN - 0.02, 2.74, 11.5, 2.2,
               [{"text": title, "font": DISPLAY, "size": title_size, "color": INK,
                 "line_spacing": 0.98}])
        D.text(s, MARGIN, 4.34, 11, 0.9,
               [{"text": sub, "font": DISPLAY, "size": 30, "color": MUTED}])
        D.rect(s, MARGIN + 0.02, 4.28, 2.2, 0.045, fill=self.pal.bright)
        if tagline:
            D.text(s, MARGIN, 5.28, 10, 0.5,
                   [{"text": tagline, "font": BODY, "size": 16, "color": FAINT}])
        self.brand_mark(s, dark=False, y=6.74, h=0.34)
        return s

    def divider(self, num, title, sub=None):
        s = self.blank(INK)
        D.rect(s, 0, 0, SW, 0.09, fill=self.pal.accent)
        D.text(s, MARGIN, 2.7, 3, 0.7,
               [{"text": num, "font": DISPLAY, "size": 26, "color": self.pal.bright, "spc": 1}])
        D.text(s, MARGIN - 0.02, 3.2, 11.5, 1.4,
               [{"text": title, "font": DISPLAY, "size": 46, "color": ONINK,
                 "line_spacing": 1.0}])
        if sub:
            D.text(s, MARGIN, 4.34, 9.5, 0.8,
                   [{"text": sub, "font": BODY, "size": 16, "color": ONINK_SUB,
                     "line_spacing": 1.2}])
        self.brand_mark(s, dark=True, y=6.82, h=0.28)
        return s

    def short_version(self, page, head, cards, note=None, focal=2):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, "The short version")
        self.headline(s, MARGIN, 1.02, head, size=38)
        gap = 0.34
        n = len(cards)
        cwd = (CW - gap * (n - 1)) / n
        y, h = 2.55, 3.05
        for i, c in enumerate(cards):
            self.card(s, MARGIN + i * (cwd + gap), y, cwd, h, c["label"], c["body"],
                      focal=(i == focal))
        if note:
            D.text(s, MARGIN, 6.05, CW, 0.4, [{"text": note, "font": BODY, "size": 14,
                                               "color": FAINT, "italic": True}])
        self.footer(s, page)
        return s

    def about(self, page, kick, head, intro, cards, footnote=None, focal=1):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=34)
        D.text(s, MARGIN, 1.95, 11.0, 0.6, [{"text": intro, "font": BODY, "size": 16,
                                             "color": MUTED, "line_spacing": 1.25}])
        gap = 0.36
        n = len(cards)
        cwd = (CW - gap * (n - 1)) / n
        y, h = 3.0, 2.7
        for i, c in enumerate(cards):
            self.card(s, MARGIN + i * (cwd + gap), y, cwd, h, c["label"], c["body"],
                      focal=(i == focal))
        if footnote:
            D.text(s, MARGIN, 5.95, CW, 0.4, [{"text": footnote, "font": BODY,
                                               "size": 12.5, "color": FAINT}])
        self.footer(s, page)
        return s

    def hub(self, page, kick, head, intro, cards, focal=2):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=36)
        D.text(s, MARGIN, 2.28, 11.3, 0.8, [{"text": intro, "font": BODY, "size": 16.5,
                                             "color": MUTED, "line_spacing": 1.3}])
        gap = 0.36
        n = len(cards)
        cwd = (CW - gap * (n - 1)) / n
        y, h = 3.7, 2.5
        for i, c in enumerate(cards):
            self.card(s, MARGIN + i * (cwd + gap), y, cwd, h, c["label"], c["body"],
                      focal=(i == focal))
        self.footer(s, page)
        return s

    def customers(self, page, head, caption):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, "Customers")
        self.headline(s, MARGIN, 1.02, head, size=38)
        cols = 5
        gx, gy = 0.28, 0.22
        cellw = (CW - gx * (cols - 1)) / cols
        top, cellh = 2.2, 0.82
        for i, name in enumerate(CUSTOMER_LOGOS):
            r, c = divmod(i, cols)
            x = MARGIN + c * (cellw + gx)
            y = top + r * (cellh + gy)
            D.rect(s, x, y, cellw, cellh, fill=NEUTRAL, rounded=True, radius=0.12)
            D.place_image(s, self.A / "logos" / f"{name}.png", x + 0.2, y + 0.13,
                          cellw - 0.4, cellh - 0.26, max_h=cellh - 0.32)
        D.text(s, MARGIN, 6.36, CW, 0.4,
               [{"text": caption, "font": BODY, "size": 12.5, "color": FAINT}])
        self.footer(s, page)
        return s

    def governance(self, page, kick, head, intro, cards, footline=None, focal=1):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=38)
        D.text(s, MARGIN, 1.95, 11.2, 0.7, [{"text": intro, "font": BODY, "size": 15,
                                             "color": MUTED, "line_spacing": 1.2}])
        gap = 0.32
        n = len(cards)
        cwd = (CW - gap * (n - 1)) / n
        y, h = 2.9, 2.85
        for i, c in enumerate(cards):
            self.card(s, MARGIN + i * (cwd + gap), y, cwd, h, c["label"], c["body"],
                      focal=(i == focal))
        if footline:
            D.text(s, MARGIN, 6.0, CW, 0.4, [{"text": footline, "font": SEMI, "size": 13,
                                              "color": self.pal.accent}])
        self.footer(s, page)
        return s

    def hierarchy(self, page, head="One platform. Every application. Grounded in SAP.",
                  caption="OnePilot connects your SAP and non-SAP systems alike.",
                  footnote="In production across financial services, chemicals, food & drink, "
                           "oil & gas, commodity and agricultural treasuries.",
                  focal_app=None):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, "Where it sits")
        self.headline(s, MARGIN, 1.02, head, size=32)
        cx = 1.7
        cw = SW - 2 * cx
        D.rect(s, cx + 1.5, 2.12, cw - 3.0, 0.78, fill=self.pal.bright, rounded=True, radius=0.12)
        D.text(s, cx + 1.5, 2.16, cw - 3.0, 0.42, [{"text": "TreasuryCentral", "font": DISPLAY,
               "size": 20, "color": PAPER, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
        D.text(s, cx + 1.5, 2.53, cw - 3.0, 0.3, [{"text": "one workspace on OnePilot",
               "font": BODY, "size": 12, "color": RGBColor(0xEA, 0xFB, 0xFC),
               "align": PP_ALIGN.CENTER}])
        pb_y, pb_h = 3.16, 2.18
        D.rect(s, cx, pb_y, cw, pb_h, fill=NEUTRAL, line=self.pal.accent, line_w=1.5,
               rounded=True, radius=0.045)
        D.text(s, cx + 0.3, pb_y + 0.16, cw - 0.6, 0.34,
               [{"text": "OnePilot", "font": DISPLAY, "size": 15, "color": self.pal.accent}])
        D.text(s, cx + 0.3, pb_y + 0.16, cw - 0.6, 0.34,
               [{"text": "the platform underneath", "font": BODY, "size": 12, "color": MUTED,
                 "align": PP_ALIGN.RIGHT}])
        n = len(PLATFORM_APPS)
        agap = 0.28
        inner_x = cx + 0.36
        inner_w = cw - 0.72
        aw = (inner_w - agap * (n - 1)) / n
        ay, ah = pb_y + 0.66, 1.4
        for i, (key, nm, dsc) in enumerate(PLATFORM_APPS):
            ax = inner_x + i * (aw + agap)
            openslot = (key == "open")
            focal = (key == focal_app)
            if openslot:
                D.rect(s, ax, ay, aw, ah, fill=None, line=self.pal.accent, line_w=1.25,
                       rounded=True, radius=0.09, dash="dash")
            elif focal:
                D.rect(s, ax, ay, aw, ah, fill=PAPER, line=self.pal.bright, line_w=2.0,
                       rounded=True, radius=0.09)
            else:
                D.rect(s, ax, ay, aw, ah, fill=PAPER, line=LINE, line_w=1.0,
                       rounded=True, radius=0.09)
            D.rect(s, ax + 0.22, ay + 0.24, 0.32, 0.05,
                   fill=(self.pal.bright if focal else self.pal.accent))
            D.text(s, ax + 0.22, ay + 0.42, aw - 0.44, 0.7,
                   [{"text": nm, "font": SEMI, "size": 13.5,
                     "color": (self.pal.accent if openslot else INK), "bold": True}])
            D.text(s, ax + 0.22, ay + ah - 0.42, aw - 0.44, 0.3,
                   [{"text": dsc, "font": BODY, "size": 11.5, "color": FAINT}])
        D.text(s, cx, 5.40, cw, 0.24, [{"text": caption, "font": BODY, "size": 11.5,
               "color": FAINT, "italic": True, "align": PP_ALIGN.CENTER}])
        D.rect(s, cx + 1.5, 5.68, cw - 3.0, 0.72, fill=INK, rounded=True, radius=0.12)
        D.text(s, cx + 1.5, 5.68, cw - 3.0, 0.72,
               [{"text": "SAP   ·   your book of records, grounded", "font": SEMI, "size": 14,
                 "color": ONINK, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
        if footnote:
            D.text(s, MARGIN, 6.5, CW, 0.3,
                   [{"text": footnote, "font": BODY, "size": 12, "color": FAINT,
                     "align": PP_ALIGN.CENTER}])
        self.footer(s, page)
        return s

    def functional(self, page, kick, head, product, sources, dests, note=None, badge=False):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=34)
        col_y, col_h = 2.55, 3.1
        src_x, src_w = MARGIN, 3.0
        ctr_x, ctr_w = 4.35, 4.65
        dst_x, dst_w = 10.05, RIGHT - 10.05
        for lx, lw, lab in [(src_x, src_w, "SOURCES"), (dst_x, dst_w, "DESTINATIONS")]:
            D.text(s, lx, col_y - 0.34, lw, 0.3, [{"text": lab, "font": SEMI, "size": 10.5,
                   "color": FAINT, "spc": 2, "align": PP_ALIGN.CENTER}])

        def chips(zx, zw, items):
            ch = 0.62
            g = (col_h - ch * len(items)) / (len(items) - 1) if len(items) > 1 else 0
            for i, it in enumerate(items):
                self.chip(s, zx, col_y + i * (ch + g), zw, ch, it, fill=NEUTRAL, txt=INK)

        chips(src_x, src_w, sources)
        chips(dst_x, dst_w, dests)
        D.rect(s, ctr_x, col_y + 0.15, ctr_w, col_h - 0.3, fill=PAPER, line=self.pal.bright,
               line_w=2.0, rounded=True, radius=0.05)
        D.text(s, ctr_x + 0.3, col_y + 0.5, ctr_w - 0.6, 0.5,
               [{"text": "BRISKEN", "font": SEMI, "size": 11, "color": self.pal.accent,
                 "spc": 2, "align": PP_ALIGN.CENTER}])
        D.text(s, ctr_x + 0.3, col_y + 0.86, ctr_w - 0.6, 0.7,
               [{"text": product, "font": DISPLAY, "size": 21, "color": INK,
                 "align": PP_ALIGN.CENTER, "line_spacing": 1.0}])
        D.text(s, ctr_x + 0.3, col_y + 1.62, ctr_w - 0.6, 0.34,
               [{"text": "on SAP's own cloud  ·  governed end to end", "font": BODY,
                 "size": 12.5, "color": MUTED, "align": PP_ALIGN.CENTER}])
        D.rect(s, ctr_x + 0.4, col_y + 2.06, ctr_w - 0.8, 0.66, fill=NEUTRAL, rounded=True,
               radius=0.12)
        D.text(s, ctr_x + 0.5, col_y + 2.06, ctr_w - 1.0, 0.66,
               [{"text": "Audit trail · segregation of duty · anomaly alerts · person-in-the-loop",
                 "font": BODY, "size": 10.5, "color": MUTED, "align": PP_ALIGN.CENTER,
                 "line_spacing": 1.1}], anchor=MSO_ANCHOR.MIDDLE)
        D.arrow(s, src_x + src_w + 0.14, col_y + col_h / 2 - 0.16,
                ctr_x - (src_x + src_w) - 0.28, 0.32, self.pal.bright)
        D.arrow(s, ctr_x + ctr_w + 0.14, col_y + col_h / 2 - 0.16,
                dst_x - (ctr_x + ctr_w) - 0.28, 0.32, self.pal.bright)
        D.text(s, MARGIN, col_y + col_h + 0.28, CW, 0.3,
               [{"text": "CONNECTS VIA   RFC / OData  ·  AMQP  ·  SFTP  ·  REST  ·  HTTP  ·  Email  ·  Excel add-in",
                 "font": SEMI, "size": 11, "color": self.pal.accent, "spc": 0.6,
                 "align": PP_ALIGN.CENTER}])
        if note:
            D.text(s, MARGIN, col_y + col_h + 0.62, CW, 0.3,
                   [{"text": note, "font": BODY, "size": 12, "color": FAINT,
                     "align": PP_ALIGN.CENTER}])
        if badge:
            D.place_image(s, self.A / "sap_certified.png", RIGHT - 1.9, 0.5, 1.9, 0.5,
                          halign="right", valign="top")
        self.footer(s, page)
        return s

    def app(self, page, kick, head, gloss, problem, steps, freed, connects):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=34)
        D.text(s, MARGIN, 1.92, 11.4, 0.5, [{"text": gloss, "font": BODY, "size": 14.5,
               "color": MUTED, "italic": True, "line_spacing": 1.18}])
        cols = [("THE PROBLEM IT REMOVES", problem, False),
                ("WHAT IT DOES, STEP BY STEP", steps, True),
                ("WHAT YOU NO LONGER DO BY HAND", freed, False)]
        gap = 0.34
        n = 3
        cwd = (CW - gap * (n - 1)) / n
        y, h = 2.5, 3.28
        for i, (label, items, numbered) in enumerate(cols):
            x = MARGIN + i * (cwd + gap)
            D.rect(s, x, y, cwd, h, fill=NEUTRAL, rounded=True, radius=0.05)
            D.rect(s, x + 0.26, y + 0.28, 0.36, 0.05,
                   fill=(self.pal.bright if i == 1 else self.pal.accent))
            D.text(s, x + 0.26, y + 0.46, cwd - 0.52, 0.5, [{"text": label, "font": SEMI,
                   "size": 11.5, "color": INK, "bold": True, "spc": 0.5, "line_spacing": 1.05}])
            paras = []
            for j, it in enumerate(items):
                if numbered:
                    paras.append({"text": f"{j+1}   {it}", "font": BODY, "size": 12.5,
                                  "color": MUTED, "line_spacing": 1.12, "space_after": 6})
                else:
                    paras.append({"text": it, "font": BODY, "size": 13, "color": MUTED,
                                  "line_spacing": 1.18, "space_after": 8})
            D.text(s, x + 0.26, y + 1.12, cwd - 0.52, h - 1.3, paras)
        D.rect(s, MARGIN, 5.98, CW, 0.6, fill=INK, rounded=True, radius=0.08)
        D.text(s, MARGIN + 0.3, 5.98, CW - 0.6, 0.6, [{"text": connects, "font": BODY,
               "size": 11.5, "color": ONINK, "line_spacing": 1.05}], anchor=MSO_ANCHOR.MIDDLE)
        self.footer(s, page)
        return s

    def usecase(self, page, kick, title, gloss, before, steps, checkpoint,
                actor="THE DIGITAL CO-WORKER"):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, title, size=32)
        if gloss:
            D.text(s, MARGIN, 1.86, 11.5, 0.4, [{"text": gloss, "font": BODY, "size": 13.5,
                   "color": FAINT, "italic": True, "line_spacing": 1.15}])
        top = 2.5
        lx, lw = MARGIN, 4.35
        D.text(s, lx, top, lw, 0.3, [{"text": "BEFORE  ·  TODAY, BY HAND", "font": SEMI,
               "size": 11, "color": FAINT, "spc": 1.6}])
        D.rect(s, lx, top + 0.42, 0.05, 3.35, fill=MUTED)
        D.text(s, lx + 0.3, top + 0.4, lw - 0.3, 3.4, [{"text": before, "font": BODY,
               "size": 15, "color": INK, "line_spacing": 1.32}])
        rx = lx + lw + 0.5
        rw = RIGHT - rx
        D.text(s, rx, top, rw, 0.3, [{"text": f"AFTER  ·  {actor}, IN ORDER", "font": SEMI,
               "size": 11, "color": self.pal.accent, "spc": 1.4}])
        sy = top + 0.44
        n = len(steps)
        rowh = 0.5
        for j, st in enumerate(steps):
            yy = sy + j * rowh
            D.rect(s, rx, yy + 0.02, 0.30, 0.30, fill=self.pal.accent, rounded=True, radius=0.25)
            D.text(s, rx, yy + 0.02, 0.30, 0.30, [{"text": str(j + 1), "font": SEMI, "size": 12,
                   "color": PAPER, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
            D.text(s, rx + 0.44, yy, rw - 0.44, rowh, [{"text": st, "font": BODY, "size": 13.5,
                   "color": INK, "line_spacing": 1.05}], anchor=MSO_ANCHOR.MIDDLE)
        cy = sy + n * rowh + 0.12
        D.rect(s, rx, cy, rw, 0.62, fill=NEUTRAL, rounded=True, radius=0.1)
        D.rect(s, rx, cy, 0.08, 0.62, fill=self.pal.bright)
        D.text(s, rx + 0.28, cy, rw - 0.5, 0.62, [{"text": checkpoint, "font": SEMI, "size": 13,
               "color": INK}], anchor=MSO_ANCHOR.MIDDLE)
        self.footer(s, page)
        return s

    def problem(self, page, kick, head, bands, stat=None):
        """Product-deck BEFORE-world slide: three stacked bands (sources /
        the manual middle / your systems). Never names the product."""
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=34)
        y0, bh, gap = 2.42, 1.18, 0.24
        for i, band in enumerate(bands):
            y = y0 + i * (bh + gap)
            villain = band.get("villain", i == 1)
            if villain:
                D.rect(s, MARGIN, y, CW, bh, fill=INK, rounded=True, radius=0.05)
                D.rect(s, MARGIN, y, 0.08, bh, fill=self.pal.bright)
                lab_c, body_c = self.pal.bright, ONINK
            else:
                D.rect(s, MARGIN, y, CW, bh, fill=NEUTRAL, rounded=True, radius=0.05)
                lab_c, body_c = self.pal.accent, INK
            D.text(s, MARGIN + 0.32, y + 0.18, CW - 0.64, 0.3,
                   [{"text": band["label"].upper(), "font": SEMI, "size": 11, "color": lab_c,
                     "spc": 1.6}])
            D.text(s, MARGIN + 0.32, y + 0.52, CW - 0.64, bh - 0.6,
                   [{"text": band["body"], "font": BODY, "size": 14, "color": body_c,
                     "line_spacing": 1.18}])
        if stat:
            D.text(s, MARGIN, y0 + 3 * bh + 2 * gap + 0.12, CW, 0.4,
                   [{"text": stat, "font": BODY, "size": 12.5, "color": FAINT}])
        self.footer(s, page)
        return s

    def success(self, page, head, intro, stories):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, "Success stories")
        self.headline(s, MARGIN, 1.02, head, size=36)
        D.text(s, MARGIN, 1.98, 11.4, 0.5, [{"text": intro, "font": BODY, "size": 15,
               "color": MUTED, "line_spacing": 1.2}])
        gap = 0.36
        n = len(stories)
        # Cap card width so 1-2 stories center at sane width; for n=3 the cap
        # is inert and the geometry equals the approved Overview exactly.
        cwd = min((CW - gap * (n - 1)) / n, 4.5)
        x0 = MARGIN + (CW - (n * cwd + (n - 1) * gap)) / 2
        y, h = 2.66, 3.82
        for i, st in enumerate(stories):
            x = x0 + i * (cwd + gap)
            D.rect(s, x, y, cwd, h, fill=NEUTRAL, rounded=True, radius=0.05)
            D.rect(s, x + 0.28, y + 0.3, 0.4, 0.055,
                   fill=(self.pal.bright if i == 0 else self.pal.accent))
            D.text(s, x + 0.28, y + 0.48, cwd - 0.56, 0.4, [{"text": st["industry"].upper(),
                   "font": SEMI, "size": 12, "color": self.pal.accent, "spc": 1.2}])
            D.text(s, x + 0.28, y + 0.88, cwd - 0.56, 0.32, [{"text": st["deployment"],
                   "font": BODY, "size": 11.5, "color": FAINT}])
            D.text(s, x + 0.28, y + 1.26, cwd - 0.56, 1.0, [{"text": st["what"],
                   "font": DISPLAY, "size": 14, "color": INK, "line_spacing": 1.1}])
            D.text(s, x + 0.28, y + 2.42, cwd - 0.56, 0.66, [{"text": st["highlight"],
                   "font": BODY, "size": 11.5, "color": MUTED, "line_spacing": 1.16}])
            by = y + h - 0.66
            D.rect(s, x + 0.28, by, cwd - 0.56, 0.56, fill=PAPER, line=LINE, line_w=1.0,
                   rounded=True, radius=0.1)
            D.rect(s, x + 0.28, by, 0.06, 0.56, fill=self.pal.accent)
            D.text(s, x + 0.46, by + 0.07, cwd - 0.74, 0.2, [{"text": "REPLACED",
                   "font": SEMI, "size": 8.5, "color": self.pal.accent, "spc": 1.4}])
            D.text(s, x + 0.46, by + 0.24, cwd - 0.74, 0.32, [{"text": st["replaced"],
                   "font": BODY, "size": 11, "color": INK, "line_spacing": 1.04}])
        self.footer(s, page)
        return s

    def compare(self, page, kick, head, left_label, left_items, right_label, right_items):
        s = self.blank(PAPER)
        self.kicker(s, MARGIN, 0.62, kick)
        self.headline(s, MARGIN, 1.02, head, size=32)
        colw = (CW - 0.5) / 2
        y, h = 2.35, 3.75
        D.rect(s, MARGIN, y, colw, h, fill=NEUTRAL, rounded=True, radius=0.05)
        D.text(s, MARGIN + 0.34, y + 0.32, colw - 0.68, 0.4, [{"text": left_label,
               "font": SEMI, "size": 12, "color": MUTED, "spc": 1.0}])
        for i, t in enumerate(left_items):
            yy = y + 0.94 + i * 0.66
            D.text(s, MARGIN + 0.34, yy, 0.3, 0.4, [{"text": "·", "font": BODY, "size": 16,
                   "color": FAINT}])
            D.text(s, MARGIN + 0.66, yy, colw - 1.0, 0.62, [{"text": t, "font": BODY,
                   "size": 13.5, "color": INK, "line_spacing": 1.14}])
        rx = MARGIN + colw + 0.5
        D.rect(s, rx, y, colw, h, fill=INK, rounded=True, radius=0.05)
        D.rect(s, rx, y, 0.09, h, fill=self.pal.bright)
        D.text(s, rx + 0.34, y + 0.32, colw - 0.68, 0.4, [{"text": right_label, "font": SEMI,
               "size": 12, "color": self.pal.bright, "spc": 1.0}])
        for i, t in enumerate(right_items):
            yy = y + 0.94 + i * 0.66
            D.text(s, rx + 0.34, yy, 0.3, 0.4, [{"text": "→", "font": BODY, "size": 14,
                   "color": self.pal.bright}])
            D.text(s, rx + 0.72, yy, colw - 1.06, 0.62, [{"text": t, "font": BODY,
                   "size": 13.5, "color": ONINK, "line_spacing": 1.14}])
        self.footer(s, page)
        return s

    def contact(self, head="Let's map your first use case.",
                sub="We build the autonomous treasury one use case at a time, on "
                    "the platform you already run."):
        s = self.blank(INK)
        D.rect(s, 0, 0, SW, 0.09, fill=self.pal.accent)
        D.text(s, MARGIN, 2.4, 3, 0.4, [{"text": "CONTACT", "font": SEMI, "size": 12.5,
               "color": self.pal.bright, "bold": True, "spc": 3}])
        D.text(s, MARGIN - 0.02, 2.88, 11.5, 1.3, [{"text": head, "font": DISPLAY,
               "size": 42, "color": ONINK}])
        D.text(s, MARGIN, 4.1, 10, 0.6, [{"text": sub, "font": BODY, "size": 16,
               "color": ONINK_SUB, "line_spacing": 1.3}])
        D.rect(s, MARGIN + 0.02, 4.98, 2.0, 0.045, fill=self.pal.bright)
        D.text(s, MARGIN, 5.2, 11, 0.4, [{"text": "Dirk Neumann", "font": SEMI, "size": 16,
               "color": ONINK}])
        D.text(s, MARGIN, 5.56, 11, 0.4, [{"text": "dirk.neumann@brisken.com    ·    +1 936-777-4451",
               "font": BODY, "size": 14, "color": ONINK_SUB}])
        D.text(s, MARGIN, 5.94, 11, 0.4, [{"text": "Brisken HQ, Houston, TX    ·    resources.brisken.com",
               "font": BODY, "size": 14, "color": ONINK_SUB}])
        self.brand_mark(s, dark=True, y=6.78, h=0.32)
        return s
