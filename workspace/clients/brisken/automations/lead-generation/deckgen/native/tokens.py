# /// script
# requires-python = ">=3.10"
# dependencies = ["python-pptx"]
# ///
"""Design tokens for the NEW-generation (native) Brisken deck family.

One family: the base tokens below are shared by every deck; each deck's
identity is exactly one Palette (accent + bright + layout signature). The
values were lifted verbatim from the Dirk-approved
`NEW - Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx`
build source. Changing a base token changes the whole family; do that only
with a DESIGN.md update in the same commit.
"""
from dataclasses import dataclass

from pptx.dml.color import RGBColor

# ---------------------------------------------------------------- base tokens
INK = RGBColor(0x0F, 0x14, 0x17)        # near-black text / dark slides
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
NEUTRAL = RGBColor(0xF4, 0xF6, 0xF7)    # cards / panels
MUTED = RGBColor(0x5B, 0x66, 0x6B)      # secondary text
FAINT = RGBColor(0x8A, 0x95, 0x99)      # tertiary text
LINE = RGBColor(0xE2, 0xE7, 0xE9)       # hairline on paper
ONINK = RGBColor(0xEC, 0xEF, 0xF0)      # primary text on ink
ONINK_SUB = RGBColor(0x9A, 0xA6, 0xAB)  # subordinate text on ink
NEUTRAL_DK = RGBColor(0x1B, 0x23, 0x27)  # panel on ink

DISPLAY = "Century Gothic"
BODY = "Segoe UI"
SEMI = "Segoe UI Semibold"
ALLOWED_FONTS = {DISPLAY, BODY, SEMI}

EMU = 914400
SW, SH = 13.333, 7.5
MARGIN = 0.62
CW = SW - 2 * MARGIN            # content width 12.093
RIGHT = SW - MARGIN


# ---------------------------------------------------------------- palettes
@dataclass(frozen=True)
class Palette:
    name: str
    accent: RGBColor      # the deck's identity color (was TEAL on the Overview)
    bright: RGBColor      # focal accent, ONE element per slide (was BRIGHT)
    signature: str        # per-deck layout signature: none|rail-left|bar-right|baseline|corner-dots


PALETTES = {
    # The approved Overview: teal, no extra signature (parity with the shipped deck).
    "overview": Palette("overview", RGBColor(0x0E, 0x7C, 0x86), RGBColor(0x17, 0xB0, 0xBE), "none"),
    # Product decks: same system, one accent + one signature each.
    "market-data-hub": Palette("market-data-hub", RGBColor(0x1B, 0x7A, 0x3D), RGBColor(0x27, 0xAE, 0x60), "rail-left"),
    "mdh-commodities": Palette("mdh-commodities", RGBColor(0x9C, 0x4A, 0x1E), RGBColor(0xC2, 0x66, 0x1B), "baseline"),
    "smart-trading": Palette("smart-trading", RGBColor(0x3A, 0x4A, 0x9F), RGBColor(0x54, 0x68, 0xD4), "bar-right"),
    "digital-co-worker": Palette("digital-co-worker", RGBColor(0x6D, 0x40, 0x98), RGBColor(0x94, 0x63, 0xD6), "corner-dots"),
}


def hexstr(c: RGBColor) -> str:
    return str(c)
