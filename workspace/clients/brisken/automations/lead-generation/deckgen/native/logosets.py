"""Named customer-logo sets for the deck family's `customers` wall.

Dirk's 2026-07-27 direction (relayed via Matthias): swap the wall's logo set
per prospect, and use TRANSPARENT logos. This module is the single home for
the set membership; grammar renders whichever set a spec's `customers` slide
names, assets verifies every listed logo exists in the curated library.

All names must resolve to a `{name}.png` in the curated transparent library
(`context/decks/customer-logos/normalized/`, built by the tracked
`build-logo-library.py`; overlaid onto the build assets by assets.py). Every
company here is a Brisken customer (owner-confirmed 2026-07-27); the wall
headline is a live-customer claim, so this list is not a wishlist.

Pure data, no imports: both grammar.py and assets.py load it, so it must not
import either (avoids an import cycle).
"""

# canonical logo key -> {name}.png in the curated library. A key may appear in
# more than one set (a customer spans industries).
LOGO_SETS = {
    # The Overview wall — Dirk's approved slide-5 set (transparent, Ford +
    # Siemens Energy added, Angus now transparent, Beautycounter/Global Brands
    # retired). 20 logos, 5x4.
    "master": [
        "google", "accenture", "equinor", "nike", "adm",
        "ab-inbev", "sulzer", "barry-callebaut", "zespri", "angus",
        "medmix", "entegris", "weyerhaeuser", "southwire", "yeti",
        "sothebys", "imax", "ford", "siemens-energy", "asr-group",
    ],
    # Commodities / food / agriculture prospects (MDH Commodities).
    "agri-food": [
        "adm", "barry-callebaut", "zespri", "ab-inbev", "nestle",
        "weyerhaeuser", "angus", "grupo-moura", "southwire", "equinor",
    ],
    # Chemicals + industrials prospects (Digital Co-Worker: chemicals + agri).
    "chemicals-industrials": [
        "angus", "medmix", "entegris", "sulzer", "siemens-energy",
        "southwire", "ford", "grupo-moura", "weyerhaeuser", "adm",
    ],
    # Financial services / tech / consumer prospects (Market Data Hub, Smart
    # Trading).
    "financial-services": [
        "google", "accenture", "sony", "lge", "kaust",
        "sothebys", "imax", "asr-group", "nike", "yeti",
    ],
}

DEFAULT_SET = "master"

# Flat, sorted union — the set of logos the curated library must supply.
ALL_WALL_LOGOS = sorted({name for names in LOGO_SETS.values() for name in names})
