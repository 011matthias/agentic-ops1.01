# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Vinted listing assistant: title, description and keywords from item facts.

Everything this produces is anchored to a dimension Vinted itself has: the
catalog category, the brand field, size, colour, material, condition, plus a
per-class cut/style vocabulary. That anchoring is the whole design, because of
how Vinted actually ranks (help/409): filters run FIRST and read only the
structured fields, and only what survives the filter gets ordered by relevance.
A keyword that maps to no Vinted dimension cannot be filtered on and cannot be
searched for, so it is noise at best.

It is also why the keywords carry no hash. Vinted does linkify a "#tag" in a
description, but only to an ordinary search for the literal string, so the hash
buys nothing the plain word does not already earn; its real use is letting one
seller's own wardrobe be browsed by a personal tag. Against that small upside
sits an enumerated rule: unrelated or excessive hashtags get a listing hidden,
and a hidden listing does not get its paid push refunded. The observed failure
mode of the tools that do generate them is brand-wide tag blocks reused across
unrelated garments, foreign brands attached for reach, duplicates and typos;
see listing-reference.md for the live evidence.

Modes:
  --suggest    generate a listing from item facts (JSON or flags)
               draws on keyword_research's mined corpus unless --no-corpus
  --validate   check an existing title/description against the catalog rules
  --vocab      print the dimension vocabulary for one garment class
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# --------------------------------------------------------------- dimensions

# Per-class attribute axes. This is where "product-specific keyword dynamics"
# actually lives: a pair of jeans is described along cut / rise / wash / closure,
# a jacket along shape / lining / closure. Filling the axes of the class is what
# separates a listing that reads specific from one that reads generic, and every
# axis here corresponds to something a Vinted buyer can filter or search on.
#
# Values are the vocabulary a listing may draw from, in German first because the
# target market is vinted.de and Vinted ranks by the buyer's language preference.
CLASS_DIMENSIONS: dict[str, dict[str, list[str]]] = {
    "pants": {
        "schnitt": ["Straight Leg", "Bootcut", "Wide Leg", "Mom Fit", "Slim Fit",
                    "Skinny", "Relaxed Fit", "Carpenter", "Cargo", "Chino", "Tapered"],
        "leibhoehe": ["High Waist", "Mid Rise", "Low Rise"],
        "waschung": ["Stonewashed", "Bleached", "Dark Wash", "Light Wash",
                     "Used Look", "Distressed", "Raw Denim"],
        "verschluss": ["Button Fly", "Knopfleiste", "Reissverschluss"],
    },
    "jacket": {
        "bauform": ["Bomberjacke", "Harrington", "Trainingsjacke", "Parka",
                    "Jeansjacke", "Fleecejacke", "Steppjacke", "Windbreaker",
                    "Arbeitsjacke", "Chore Coat", "Softshelljacke", "Daunenjacke"],
        "futter": ["gefuettert", "Teddyfutter", "Fleecefutter", "ungefuettert"],
        "kapuze": ["mit Kapuze", "ohne Kapuze", "abnehmbare Kapuze"],
        "verschluss": ["Reissverschluss", "Druckknoepfe", "Knopfleiste"],
    },
    "sweater": {
        "bindung": ["Zopfmuster", "Kabelstrick", "Feinstrick", "Grobstrick",
                    "Rippstrick", "Sweatstoff"],
        "ausschnitt": ["Rundhals", "V-Ausschnitt", "Halbzip", "Rollkragen",
                       "Troyer", "Kapuze"],
        "passform": ["Oversized", "Regular Fit", "Cropped", "Boxy"],
    },
    "shirt": {
        "schnitt": ["Regular Fit", "Oversized", "Slim Fit", "Boxy", "Cropped"],
        "aermel": ["Kurzarm", "Langarm", "aermellos"],
        "kragen": ["Polokragen", "Rundhals", "V-Ausschnitt", "Hemdkragen",
                   "Buttondown"],
        "print": ["Logo-Print", "Stickerei", "Grafikprint", "Unifarben",
                  "gestreift", "kariert"],
    },
    "shorts": {
        "schnitt": ["Cargo", "Chino", "Jeansshorts", "Sweatshorts", "Bermuda"],
        "laenge": ["knielang", "kurz", "ueber dem Knie"],
    },
    "dress": {
        "laenge": ["Mini", "Midi", "Maxi", "knielang"],
        "schnitt": ["A-Linie", "figurbetont", "Wickelkleid", "Hemdblusenkleid",
                    "Trapezform"],
        "anlass": ["Alltag", "Buero", "Abendkleid", "Sommerkleid"],
    },
}

# Era words only earn their place when the garment genuinely carries them.
ERAS = ["y2k", "90s", "00s", "80s", "70s", "Vintage", "Retro"]

# Vinted's own colour filter values. Free-form colour names cannot be filtered
# on, so the engine maps to this list or leaves the field empty.
VINTED_COLOURS = [
    "Schwarz", "Braun", "Grau", "Beige", "Rosa", "Lila", "Rot", "Gelb", "Blau",
    "Grün", "Orange", "Weiß", "Silber", "Gold", "Marineblau", "Khaki",
    "Türkis", "Creme", "Aprikose", "Koralle", "Burgund", "Mehrfarbig",
]

VINTED_CONDITIONS = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut",
                     "Zufriedenstellend"]

# Every brand family the watcher tracks, plus the common sub-brand spellings.
# Used to detect a FOREIGN brand appearing in a listing, which is the single
# most consequential rule violation (catalog-rules: hide or delete).
KNOWN_BRANDS = {
    "carhartt": ["carhartt", "carhartt wip"],
    "stone-island": ["stone island"],
    "ralph-lauren": ["ralph lauren", "polo ralph lauren", "chaps"],
    "the-north-face": ["the north face", "north face", "tnf"],
    "patagonia": ["patagonia"],
    "levis": ["levis", "levi's", "levi strauss"],
    "nike": ["nike"],
    "adidas": ["adidas"],
    "agolde": ["agolde"],
    "citizens-of-humanity": ["citizens of humanity"],
    "mother": ["mother denim"],
    "7-for-all-mankind": ["7 for all mankind", "7fam", "seven for all mankind"],
    "puma": ["puma"], "reebok": ["reebok"], "champion": ["champion"],
    "tommy": ["tommy hilfiger"], "lacoste": ["lacoste"], "gucci": ["gucci"],
    "supreme": ["supreme"], "lonsdale": ["lonsdale"], "sergio": ["sergio tacchini"],
    "columbia": ["columbia"], "arcteryx": ["arc'teryx", "arcteryx"],
    "wrangler": ["wrangler"], "lee": ["lee jeans"], "dickies": ["dickies"],
    "vans": ["vans"], "converse": ["converse"], "new-balance": ["new balance"],
    "zara": ["zara"], "hm": ["h&m"], "diesel": ["diesel"], "napapijri": ["napapijri"],
}

MAX_KEYWORDS = 8
# Vinted names no number; this is the point past which sellers report
# listings being hidden, kept deliberately low because the upside is small.
MAX_HASHTAGS = 3

# The German noun a buyer actually types for each garment class. The watcher's
# classes are internal English labels; a listing titled "pants" would be found
# by nobody on vinted.de.
CLASS_NOUN = {
    "pants": "Hose", "jacket": "Jacke", "sweater": "Pullover", "shirt": "Shirt",
    "shorts": "Shorts", "dress": "Kleid", "skirt": "Rock", "other": None,
}

# The nouns this market actually uses for each class, which is often narrower
# and better than the generic label: a Levi's 501 is a "Jeans", not a "Hose".
# A bounded vocabulary rather than "the most common term in the cell", because
# the most common term in levis/pants is 501 at 87.5%, and picking that as the
# category word put the model in the category field and the word "Jeans" in the
# model field, which is wrong twice over.
CLASS_MARKET_NOUNS = {
    "pants": ["jeans", "hose", "pant", "pants", "chino", "chinos", "cargohose",
              "jogginghose", "cordhose", "trousers"],
    "jacket": ["jacke", "jacket", "parka", "weste", "mantel", "blouson", "coat",
               "windbreaker", "regenjacke", "daunenjacke", "fleecejacke"],
    "sweater": ["pullover", "pulli", "sweater", "hoodie", "sweatshirt", "strickjacke",
                "cardigan", "sweatjacke", "crewneck"],
    "shirt": ["shirt", "tshirt", "hemd", "polo", "poloshirt", "longsleeve", "top"],
    "shorts": ["shorts", "short", "bermuda", "sweatshorts"],
    "dress": ["kleid", "dress", "sommerkleid", "midikleid"],
    "skirt": ["rock", "skirt"],
}

# ---------------------------------------------------------- lenient input
#
# The engine used to take only hand-typed JSON with exact English keys. A
# misspelled or German key was not an error: the value simply vanished, the
# axis came out as TBD, and the output looked finished. Silent degradation is
# the worst failure mode a tool like this has, because it produces a listing
# that reads fine and quietly omits the thing that would have sold it.

FIELD_ALIASES = {
    "brand": "brand", "marke": "brand", "label": "brand",
    "type": "type", "typ": "type", "art": "type", "artikel": "type",
    "kategorie": "garment_class", "klasse": "garment_class",
    "garment_class": "garment_class", "category": "garment_class",
    "model": "model", "modell": "model", "modellname": "model",
    "size": "size", "groesse": "size", "größe": "size", "gr": "size",
    "color": "color", "colour": "color", "farbe": "color",
    "material": "material", "stoff": "material", "fabric": "material",
    "condition": "condition", "zustand": "condition",
    "era": "era", "aera": "era", "ära": "era", "epoche": "era", "jahrzehnt": "era",
    "cut": "cut", "schnitt": "cut", "fit": "cut", "passform": "cut",
    "wash": "wash", "waschung": "wash",
    "rise": "rise", "leibhoehe": "rise", "leibhöhe": "rise", "bund": "rise",
    "closure": "closure", "verschluss": "closure",
    "style": "style", "stil": "style",
    "measurements": "measurements", "masse": "measurements", "maße": "measurements",
}

# Per-class axis names are legitimate keys too; they are declared in German in
# CLASS_DIMENSIONS, so they alias to themselves.
for _dims in CLASS_DIMENSIONS.values():
    for _axis in _dims:
        FIELD_ALIASES.setdefault(_axis, _axis)

# Split in two for the same reason keyword_research splits its size patterns: a
# bare number is ambiguous. "w31" can only be a size; "501" next to Levi's is a
# model, and reading it as the size put 501 in the size field and left the model
# empty, which is the wrong answer twice over.
SIZE_NOTATION = re.compile(
    r"^(w\d{2}(?:[/x-]?l\d{2})?|l\d{2}|xxs|xs|s|m|l|xl|xxl|xxxl|3xl)$", re.I)
SIZE_PATTERN = re.compile(
    r"^(w\d{2}(?:[/x-]?l\d{2})?|l\d{2}|xxs|xs|s|m|l|xl|xxl|xxxl|3xl|\d{2,3})$", re.I)


def normalise_keys(raw: dict) -> tuple[dict, list[str]]:
    """Map supplied keys onto the engine's own, reporting the ones it cannot.

    Returns (item, unknown_keys). An unknown key is REPORTED rather than
    dropped: the caller can then ask about it instead of shipping a listing
    that silently lost a field.
    """
    item, unknown = {}, []
    for key, value in raw.items():
        canon = FIELD_ALIASES.get(str(key).strip().lower().replace(" ", "_"))
        if canon is None:
            unknown.append(str(key))
            continue
        if value not in (None, "", []):
            item[canon] = value
    return item, unknown


def parse_free_text(text: str) -> tuple[dict, list[str]]:
    """Read item facts out of a line like "levis 501 w31 blau sehr gut".

    Returns (item, leftovers). Leftovers are the words nothing claimed; they
    are surfaced rather than discarded, because an unclaimed word is usually
    either the model name or a typo, and both are worth a question.
    """
    item: dict = {}
    tokens = [t for t in re.split(r"[\s,;|]+", (text or "").strip()) if t]
    low = " ".join(tokens).lower()
    leftovers: list[str] = []

    # Condition first: it is the only multi-word value, so matching it early
    # stops "sehr gut" being read as two stray words.
    for cond in sorted(VINTED_CONDITIONS, key=len, reverse=True):
        if cond.lower() in low:
            item["condition"] = cond
            low = low.replace(cond.lower(), " ")
            break

    brand = None
    for spellings in KNOWN_BRANDS.values():
        for spelling in sorted(spellings, key=len, reverse=True):
            if re.search(r"(?<![a-z])" + re.escape(spelling) + r"(?![a-z])", low):
                if brand is None or len(spelling) > len(brand):
                    brand = spelling
    if brand:
        item["brand"] = brand.title() if brand.islower() else brand
        low = low.replace(brand, " ")

    remaining = [t for t in re.split(r"[\s,;|]+", low) if t]
    # Unambiguous size notations are claimed first, over the whole line, so that
    # "levis 501 w31" gives size W31 and leaves 501 to become the model. Left to
    # token order, the bare 501 was taken as the size and the model came out
    # empty.
    for token in remaining:
        if SIZE_NOTATION.match(token) and "size" not in item:
            item["size"] = token.upper()
    remaining = [t for t in remaining
                 if not (SIZE_NOTATION.match(t) and item.get("size") == t.upper())]
    for token in remaining:
        if SIZE_PATTERN.match(token) and "size" not in item:
            item["size"] = token.upper()
            continue
        colour = next((c for c in VINTED_COLOURS if c.lower() == token), None)
        if colour and "color" not in item:
            item["color"] = colour
            continue
        era = next((e for e in ERAS if e.lower() == token), None)
        if era and "era" not in item:
            item["era"] = era
            continue
        noun = next((cls for cls, word in CLASS_NOUN.items()
                     if word and word.lower() == token), None)
        if noun and "garment_class" not in item:
            item["garment_class"] = noun
            item.setdefault("type", CLASS_NOUN[noun])
            continue
        axis_hit = False
        for dims in CLASS_DIMENSIONS.values():
            for axis, values in dims.items():
                match = next((v for v in values if v.lower() == token), None)
                if match and axis not in item:
                    item[axis] = match
                    axis_hit = True
                    break
            if axis_hit:
                break
        if axis_hit:
            continue
        leftovers.append(token)

    # A leftover next to a known brand is almost always the model name
    # ("levis 501" -> 501), which is the single most searched-for token there is.
    if leftovers and "model" not in item and item.get("brand"):
        item["model"] = leftovers.pop(0)
    return item, leftovers


def read_item(raw) -> tuple[dict, list[str]]:
    """Accept a dict, a JSON string, or a free-text line. Returns (item, notes)."""
    notes: list[str] = []
    if isinstance(raw, dict):
        item, unknown = normalise_keys(raw)
    else:
        text = str(raw).strip()
        parsed = None
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                notes.append(f"sieht aus wie JSON, ist aber keins ({e.msg}); "
                             "als Freitext gelesen")
        if isinstance(parsed, dict):
            item, unknown = normalise_keys(parsed)
        else:
            item, leftovers = parse_free_text(text)
            unknown = []
            if leftovers:
                notes.append("nicht zugeordnet: " + ", ".join(leftovers)
                             + " (Modellname? Tippfehler?)")
    if unknown:
        notes.append("unbekannte Felder, deshalb ignoriert: " + ", ".join(unknown)
                     + "; bekannt sind: " + ", ".join(sorted(set(FIELD_ALIASES.values()))))
    # The class is what selects the axis vocabulary, so deriving it from the
    # noun is worth doing rather than leaving the whole per-class layer unused.
    if "garment_class" not in item and item.get("type"):
        typ = str(item["type"]).lower()
        for cls, word in CLASS_NOUN.items():
            if word and word.lower() in typ:
                item["garment_class"] = cls
                break
    if "type" not in item and item.get("garment_class"):
        noun = CLASS_NOUN.get(item["garment_class"])
        if noun:
            item["type"] = noun
    return item, notes


def open_questions(item: dict) -> list[str]:
    """What is still missing, as questions to answer rather than TBD to ship.

    Ordered by what it costs to leave out. Colour and material are Vinted
    FILTER fields: a listing without them is excluded from those filters
    outright, which is a visibility loss, not a cosmetic one. Everything after
    is detail a buyer would otherwise have to ask for.
    """
    questions = []
    if not item.get("brand"):
        questions.append("Marke? (Pflicht-Filterfeld; ohne sie ist die Anzeige praktisch unsichtbar)")
    if not item.get("garment_class") and not item.get("type"):
        questions.append("Was ist es? (Hose, Jacke, Pullover, Shirt, Shorts, Kleid)")
    if not item.get("size"):
        questions.append("Groesse? (Filterfeld)")
    if not item.get("condition"):
        questions.append("Zustand? (" + " / ".join(VINTED_CONDITIONS) + ")")
    if not item.get("color"):
        questions.append("Farbe? (Filterfeld; Vinted kennt: "
                         + ", ".join(VINTED_COLOURS[:8]) + ", ...)")
    if not item.get("material"):
        questions.append("Material? (Filterfeld; steht im Innenetikett)")
    if not item.get("measurements"):
        questions.append("Masse flach gemessen? (haeufigste Rueckfrage)")
    axes = CLASS_DIMENSIONS.get(item.get("garment_class") or "", {})
    missing = [a for a in axes if not item.get(a)]
    if missing:
        questions.append("Optional, macht den Titel spezifisch: "
                         + ", ".join(f"{a} ({'/'.join(axes[a][:3])} ...)" for a in missing))
    return questions


def brand_key(name: str) -> str | None:
    """Which known brand family a string names, if any."""
    low = (name or "").lower()
    best, best_len = None, 0
    for key, spellings in KNOWN_BRANDS.items():
        for spelling in spellings:
            if spelling in low and len(spelling) > best_len:
                best, best_len = key, len(spelling)
    return best


def foreign_brands(text: str, own_brand: str) -> list[str]:
    """Brand names in the text that are not the listing's own brand.

    This is the rule with teeth. Vinted's catalog rules forbid irrelevant brand
    names "in the brand field, the title, the item description and/or the
    hashtags", and a listing hidden for it does not get its paid push refunded.
    """
    own = brand_key(own_brand)
    low = (text or "").lower()
    # Tag-style compounds are how a foreign brand usually sneaks in: the live
    # example that prompted this carried "#niketrack" and "#adidastrack" on a
    # Lonsdale garment. Word boundaries alone would wave those through, so
    # compound tokens are also matched on a prefix.
    compounds = [t.lstrip("#").lower() for t in re.findall(r"#\w+|\b\w{8,}\b", low)]
    found = []
    for key, spellings in KNOWN_BRANDS.items():
        if key == own:
            continue
        for spelling in spellings:
            if re.search(r"(?<![a-z])" + re.escape(spelling) + r"(?![a-z])", low):
                found.append(spelling)
                break
            if len(spelling) >= 4 and any(c.startswith(spelling) or spelling in c
                                          for c in compounds):
                found.append(spelling)
                break
    return found


# ------------------------------------------------------------------ suggest

def leading_detail(item: dict) -> str | None:
    """The one attribute that most distinguishes this piece from its neighbours.

    Drawn from the class's own axes, in the order those axes are declared: for
    jeans the cut says more than the closure, for a jacket the shape says more
    than the lining. This is the per-class dynamic doing its job in the title,
    where a buyer scanning a grid actually reads it.
    """
    if item.get("cut") or item.get("style"):
        return item.get("cut") or item.get("style")
    for axis in CLASS_DIMENSIONS.get(item.get("garment_class") or "", {}):
        if item.get(axis):
            return item[axis]
    return None


def dedupe_words(text: str) -> str:
    """Drop a word the phrase already used. Case-insensitive, order-preserving.

    Brand, model and type are supplied independently and routinely overlap:
    brand "Levi's", model "501", type "Jeans" is fine, but a model mined as
    "Jeans 501" next to type "Jeans" reads "Levi's Jeans 501 Jeans". The title
    is the scarcest space in a listing and a repeated word buys nothing twice.
    """
    seen, out = set(), []
    for word in text.split():
        key = word.lower().strip(".,|")
        if key and key in seen:
            continue
        seen.add(key)
        out.append(word)
    return " ".join(out)


def build_title(item: dict) -> str:
    """Brand first, then the one detail that distinguishes this piece."""
    parts = [dedupe_words(" ".join(p for p in [item.get("brand"), item.get("model"),
                                               item.get("type")] if p).strip())]
    detail = leading_detail(item)
    if detail:
        parts.append(detail)
    if item.get("color"):
        parts.append(item["color"])
    if item.get("size"):
        # Vinted stores denim sizes in a dual notation, "W31 | DE 46". Both
        # belong in the size FIELD, which is what buyers filter on, but a title
        # spends scarce characters saying one thing twice. The first notation
        # is the one the garment is searched by.
        parts.append(f"Gr. {str(item['size']).split('|')[0].strip()}")
    title = " | ".join(p for p in parts if p)
    return title


def build_keywords(item: dict, mined: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Keywords drawn only from dimensions Vinted can filter or search on.

    Returns (keywords, notes). Each keyword traces to a field the seller
    actually supplied, so a listing never claims an attribute nobody verified.

    `mined` carries terms researched from the real corpus by keyword_research,
    which is where the model names live: this module knows jeans have a cut,
    but only the market knows that Carhartt calls its trousers Newel and Sid.
    Supplied facts still rank first, because they describe the garment in hand
    rather than its neighbours.
    """
    kws: list[str] = []
    notes: list[str] = []

    # A phrase and its own permutation are one keyword, not two. The corpus
    # legitimately ranks "501 jeans" and "jeans 501" separately, because
    # sellers type both, but a listing that carries both has spent two of its
    # eight slots saying one thing: Vinted matches on the words, not the order.
    seen_wordsets: set[frozenset] = set()

    def add(value: str | None) -> None:
        if not value:
            return
        v = str(value).strip()
        if not v or v.lower() in {k.lower() for k in kws}:
            return
        words = frozenset(v.lower().split())
        if words in seen_wordsets:
            return
        seen_wordsets.add(words)
        kws.append(v)

    # Dimension 1+2: the category word and the brand-plus-type compound. These
    # are what a buyer actually types.
    add(item.get("type"))
    if item.get("brand") and item.get("type"):
        add(f"{item['brand']} {item['type']}")
    add(item.get("model"))

    # Dimension 3: the class-specific axes, which is what makes the set
    # product-specific rather than brand-wide.
    cls = item.get("garment_class")
    dims = CLASS_DIMENSIONS.get(cls, {})
    for axis in dims:
        if item.get(axis):
            add(item[axis])
    for axis, value in (("cut", None), ("wash", None), ("rise", None)):
        if item.get(axis):
            add(item[axis])

    # Dimension 4: material and era, both only when supplied.
    if item.get("material"):
        add(item["material"].split("(")[0].strip())
    if item.get("era"):
        add(item["era"])

    if not dims and cls:
        notes.append(f"keine Dimensions-Achsen fuer Klasse {cls!r} hinterlegt")
    missing = [a for a in dims if not item.get(a)]
    if missing:
        notes.append("nicht befuellte Achsen dieser Klasse: " + ", ".join(missing))

    # Corpus terms fill the remaining slots. They are appended rather than
    # merged so a researched term can never displace a stated fact.
    if mined:
        before = len(kws)
        for term in mined:
            if len(kws) >= MAX_KEYWORDS:
                break
            add(term)
        if len(kws) > before:
            notes.append("aus dem Korpus ergaenzt: "
                         + ", ".join(kws[before:]))

    if len(kws) > MAX_KEYWORDS:
        notes.append(f"auf {MAX_KEYWORDS} gekuerzt (Vinted wertet Tag-Masse als "
                     f"Ausblendungsgrund); weggefallen: {', '.join(kws[MAX_KEYWORDS:])}")
        kws = kws[:MAX_KEYWORDS]
    return kws, notes


def build_description(item: dict, keywords: list[str]) -> str:
    """Hook, style prose, detail block, measurements.

    Keywords land inside the prose rather than in a block at the end: the same
    words carry the same search weight either way, and a wall of tags is a
    documented reason for Vinted to hide the listing.
    """
    brand = item.get("brand") or ""
    typ = item.get("type") or "Artikel"
    lines = []

    era = item.get("era")
    # The model belongs in the first line: on a Levi's it is the whole point of
    # the garment, and a hook reading "Levi's Jeans" describes a category while
    # "Levi's 501 Jeans" describes the item.
    hook_bits = [b for b in [era, brand, item.get("model"), typ] if b]
    lines.append(f"{dedupe_words(' '.join(hook_bits))}." if hook_bits else f"{typ}.")

    style_bits = []
    for axis in ("cut", "rise", "wash", "closure", "fit"):
        if item.get(axis):
            style_bits.append(item[axis])
    cls_dims = CLASS_DIMENSIONS.get(item.get("garment_class") or "", {})
    for axis in cls_dims:
        if item.get(axis):
            style_bits.append(item[axis])
    if style_bits:
        lines.append("")
        lines.append(", ".join(dict.fromkeys(style_bits)) + ".")

    lines.append("")
    lines.append("Details:")
    for label, key in (("Marke", "brand"), ("Modell", "model"), ("Groesse", "size"),
                       ("Material", "material"), ("Farbe", "color"),
                       ("Zustand", "condition")):
        value = item.get(key)
        lines.append(f"- {label}: {value}" if value else f"- {label}: TBD")

    measures = item.get("measurements") or {}
    lines.append("")
    if measures:
        lines.append("Masse flach gemessen:")
        for k, v in measures.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("Masse flach gemessen: TBD")

    extra = [k for k in keywords if k.lower() not in " ".join(lines).lower()]
    if extra:
        lines.append("")
        lines.append("Wird auch gesucht als: " + ", ".join(extra) + ".")
    return "\n".join(lines)


def mined_terms(item: dict) -> tuple[list[str], list[str]]:
    """Corpus terms for this item, or nothing when the database is not there.

    Kept optional on purpose: the engine stays a pure function that runs
    anywhere, and the research layer is an enrichment rather than a dependency.
    """
    brand = brand_key(item.get("brand") or "")
    cls = item.get("garment_class")
    if not brand or not cls:
        return [], []
    try:
        import importlib.util
        import sqlite3
        research_path = SCRIPT_DIR / "keyword_research.py"
        if not research_path.exists():
            return [], []
        spec = importlib.util.spec_from_file_location("keyword_research", research_path)
        kr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kr)
        if not kr.DB_PATH.exists():
            return [], ["keine Korpus-Datenbank; nur die statischen Achsen genutzt"]
        con = sqlite3.connect("file:" + str(kr.DB_PATH) + "?mode=ro", uri=True)
        try:
            hint = " ".join(str(item.get(k) or "") for k in
                            ("brand", "model", "type", "cut", "style", "era"))
            hint += " " + " ".join(str(v) for v in item.values() if isinstance(v, str))
            terms = kr.keywords_for(con, brand, cls, title_hint=hint, limit=MAX_KEYWORDS)
            return terms, []
        finally:
            con.close()
    except Exception as e:                       # research must never break a listing
        return [], [f"Korpus-Recherche uebersprungen: {type(e).__name__}"]


def slug_tag(text: str) -> str | None:
    """A term as a Vinted-linkifiable tag, or None if nothing usable is left.

    Vinted linkifies `#\\w+`, so the tag has to survive as one word. Umlauts
    are folded rather than kept: the linkified target is a search_text query,
    and the corpus spells the same garment both ways.
    """
    folded = (text or "").lower()
    for src, dst in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        folded = folded.replace(src, dst)
    tag = re.sub(r"[^a-z0-9]", "", folded)
    return tag if len(tag) >= 3 else None


def build_hashtags(item: dict, keywords: list[str],
                   mined: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Returns (tags, candidates_to_confirm).

    Deliberately few and deliberately conservative. A tag on Vinted buys no
    reach (there are no tag pages; `/hashtag/*` is a 404), only self-sorting
    within a wardrobe, while "besonders viele oder nicht zugehoerige Hashtags"
    is an enumerated reason for Vinted to hide the listing outright, with no
    refund on a paid push.

    Which is why the chosen tags come ONLY from fields the seller supplied. A
    mined corpus term describes the CELL, not this garment, and as a hashtag it
    stops being a search word and becomes a claim: the first draft of this
    function offered "#cargo #knee #chino" for one pair of trousers, which
    cannot all be true, and "#nuptse" for a North Face jacket whose model
    nobody had entered. Both are the hide trigger, not a keyword strategy.

    The corpus still earns its place, one step back: its high-lift terms come
    back as CANDIDATES for the seller to confirm. That is the honest version of
    per-product research. It says "this cell's buyers search for `single knee`;
    take it if your trousers actually are one", instead of asserting it.

    Order of preference among the supplied fields: the model, because it is the
    one term a buyer searches that no other listing carries by accident; then
    the cut or defining style; then the era.
    """
    brand = item.get("brand") or ""
    tags: list[str] = []
    used: set[str] = set()

    def words(text: str | None) -> set[str]:
        # Stemmed to a trailing-s, so "pant" and "pants" are one word rather
        # than two of three slots.
        out = set()
        for w in re.split(r"[^a-z0-9]+", (text or "").lower()):
            if w:
                out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
        return out

    # Words with no sorting power of their own, because Vinted already filters
    # on them: the category (in either language), the size, the colour.
    inert = (words(item.get("type")) | words(item.get("garment_class"))
             | words(item.get("size")) | words(item.get("color")))

    def add(*parts: str | None) -> None:
        if len(tags) >= MAX_HASHTAGS:
            return
        joined = " ".join(p for p in parts if p)
        tag = slug_tag(joined.replace(" ", ""))
        if tag and tag not in tags:
            tags.append(tag)
            used.update(words(joined))

    if item.get("model"):
        add(brand, item.get("model"))
    add(item.get("cut") or item.get("style"))
    if item.get("era"):
        add(item.get("era"))
    if not tags and brand and item.get("type"):
        add(brand, item.get("type"))

    # Candidates: what this cell's listings actually say, minus anything the
    # chosen tags or Vinted's own filters already cover. Never auto-adopted.
    candidates = []
    for term in (mined or []):
        if len(candidates) >= MAX_HASHTAGS:
            break
        if words(term) - used - inert:
            tag = slug_tag(term.replace(" ", ""))
            if tag and tag not in tags and tag not in candidates:
                candidates.append(tag)
    return tags[:MAX_HASHTAGS], candidates


def suggest(item: dict, use_corpus: bool = True) -> dict:
    """Full listing proposal plus the validation of what it produced."""
    mined, mine_notes = mined_terms(item) if use_corpus else ([], [])
    keywords, notes = build_keywords(item, mined=mined)
    notes = mine_notes + notes
    tags, tag_candidates = build_hashtags(item, keywords, mined=mined)
    title = build_title(item)
    description = build_description(item, keywords)
    result = {
        "title": title,
        "title_len": len(title),
        "description": description,
        "keywords": keywords,
        "hashtags": tags,
        "hashtag_candidates": tag_candidates,
        "structured_fields": {
            "brand": item.get("brand"), "category": item.get("type"),
            "size": item.get("size"), "color": item.get("color"),
            "material": item.get("material"), "condition": item.get("condition"),
        },
        "notes": notes,
        # What is missing, phrased as questions. A TBD inside the description
        # gets published; a question gets answered.
        "open_questions": open_questions(item),
    }
    result["validation"] = validate(title, description, item.get("brand") or "",
                                   keywords)
    return result


# ----------------------------------------------------------------- validate

def validate(title: str, description: str, own_brand: str,
             keywords: list[str] | None = None) -> dict:
    """Check a listing against the catalog rules that get listings hidden."""
    problems, warnings = [], []
    blob = f"{title}\n{description}"

    strangers = foreign_brands(blob, own_brand)
    if strangers:
        problems.append("fremde Marke(n) genannt: " + ", ".join(strangers)
                        + " (catalog-rules: Artikel wird versteckt oder geloescht)")

    tags = re.findall(r"#\w+", blob)
    # Vinted does linkify tags, so a couple of accurate ones are survivable and
    # a large wardrobe can genuinely use them to self-sort. The rule bites on
    # volume: "besonders viele oder nicht zugehoerige Hashtags" is an
    # enumerated reason to hide the listing, and a hidden listing loses its
    # paid push with no refund.
    if len(tags) > MAX_HASHTAGS:
        problems.append(f"{len(tags)} Hashtags; ab etwa {MAX_HASHTAGS} wertet Vinted "
                        "das als 'besonders viele' und blendet den Artikel aus")
    elif tags:
        warnings.append(f"{len(tags)} Hashtag(s); die Raute bringt gegenueber dem "
                        "blossen Wort nichts, ausser du sortierst damit dein "
                        "eigenes Sortiment")

    if keywords is not None and len(keywords) > MAX_KEYWORDS:
        problems.append(f"{len(keywords)} Keywords, erlaubt sind {MAX_KEYWORDS}")

    if keywords:
        seen, dupes = set(), []
        for k in keywords:
            if k.lower() in seen:
                dupes.append(k)
            seen.add(k.lower())
        if dupes:
            problems.append("doppelte Keywords: " + ", ".join(dupes))

    if re.search(r"(neu|gut|sehr gut|good|new)\s*/\s*10", blob, re.I):
        problems.append("Zahlen-Slot mit einem Wort gefuellt (z.B. 'Neu/10')")

    if len(title) > 80:
        warnings.append(f"Titel {len(title)} Zeichen; kuerzer als 80 liest sich besser")
    if "TBD" in description:
        missing = re.findall(r"- ([A-Za-zäöüÄÖÜ ]+): TBD", description)
        missing += ["Masse"] if "Masse flach gemessen: TBD" in description else []
        warnings.append("noch offen: " + ", ".join(missing)
                        + " (Material und Masse sind die haeufigsten Rueckfragen, "
                          "Material ist ausserdem ein Filterfeld)")

    colour_named = [c for c in VINTED_COLOURS if c.lower() in blob.lower()]
    if not colour_named:
        warnings.append("keine Vinted-Farbe erkannt; Farbe ist ein Filterfeld")

    return {"ok": not problems, "problems": problems, "warnings": warnings}


# --------------------------------------------------------------------- cli

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suggest", metavar="JSON",
                    help='item facts as JSON, or @path to a JSON file')
    ap.add_argument("--validate", nargs=2, metavar=("BRAND", "FILE"),
                    help="check an existing listing text file against the rules")
    ap.add_argument("--vocab", metavar="CLASS",
                    help="print the dimension vocabulary for a garment class")
    ap.add_argument("--no-corpus", action="store_true",
                    help="skip the mined corpus terms; static axes only")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.vocab:
        dims = CLASS_DIMENSIONS.get(args.vocab)
        if not dims:
            print(f"keine Achsen fuer {args.vocab!r}; bekannt: "
                  + ", ".join(sorted(CLASS_DIMENSIONS)))
            sys.exit(1)
        print(json.dumps(dims, indent=2, ensure_ascii=False) if args.json else
              "\n".join(f"{axis}: {', '.join(vals)}" for axis, vals in dims.items()))
        return

    if args.validate:
        brand, path = args.validate
        text = Path(path).read_text(encoding="utf-8")
        head, _, body = text.partition("\n")
        report = validate(head, body, brand)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("OK" if report["ok"] else "PROBLEME:")
            for p in report["problems"]:
                print(f"  [!] {p}")
            for w in report["warnings"]:
                print(f"  [~] {w}")
        sys.exit(0 if report["ok"] else 1)

    if args.suggest:
        raw = args.suggest
        if raw.startswith("@"):
            raw = Path(raw[1:]).read_text(encoding="utf-8")
        # Accepts JSON with English OR German keys, and plain free text like
        # "levis 501 w31 blau sehr gut". A key it cannot place is reported, not
        # silently dropped.
        item, read_notes = read_item(raw)
        out = suggest(item, use_corpus=not args.no_corpus)
        out["notes"] = read_notes + out["notes"]
        out["parsed_as"] = item
        if args.json:
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        print("TITEL (" + str(out["title_len"]) + " Zeichen)")
        print("  " + out["title"])
        print("\nBESCHREIBUNG")
        for line in out["description"].splitlines():
            print("  " + line)
        print("\nKEYWORDS (" + str(len(out["keywords"])) + ")")
        print("  " + ", ".join(out["keywords"]))
        if out["hashtags"] or out["hashtag_candidates"]:
            print("\nHASHTAGS (max " + str(MAX_HASHTAGS) + " insgesamt)")
            if out["hashtags"]:
                print("  belegt: " + " ".join("#" + t for t in out["hashtags"]))
            if out["hashtag_candidates"]:
                print("  Kandidaten aus dem Korpus, nur nehmen wenn zutreffend:")
                print("    " + " ".join("#" + t for t in out["hashtag_candidates"]))
            print("  Die Raute bringt keine Reichweite (Vinted hat keine Tag-Seiten),")
            print("  nur Selbstsortierung. Zu viele oder unpassende sind ein")
            print("  Ausblendungsgrund, deshalb wird nichts geraten.")
        print("\nGELESEN ALS")
        for k, v in sorted(out.get("parsed_as", item).items()):
            print(f"  {k:<16}{v}")
        print("\nSTRUKTURIERTE FELDER (das harte Filter-Tor)")
        for k, v in out["structured_fields"].items():
            print(f"  {k:<10}{v if v else 'OFFEN'}")
        if out["open_questions"]:
            print("\nOFFENE FRAGEN")
            for q in out["open_questions"]:
                print("  - " + q)
        if out["notes"]:
            print("\nHINWEISE")
            for n in out["notes"]:
                print("  " + n)
        v = out["validation"]
        print("\nPRUEFUNG: " + ("OK" if v["ok"] else "PROBLEME"))
        for p in v["problems"]:
            print("  [!] " + p)
        for w in v["warnings"]:
            print("  [~] " + w)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
