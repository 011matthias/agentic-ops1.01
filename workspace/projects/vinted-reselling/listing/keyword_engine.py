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


def build_title(item: dict) -> str:
    """Brand first, then the one detail that distinguishes this piece."""
    parts = [" ".join(p for p in [item.get("brand"), item.get("model"),
                                  item.get("type")] if p).strip()]
    detail = leading_detail(item)
    if detail:
        parts.append(detail)
    if item.get("color"):
        parts.append(item["color"])
    if item.get("size"):
        parts.append(f"Gr. {item['size']}")
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

    def add(value: str | None) -> None:
        if not value:
            return
        v = str(value).strip()
        if v and v.lower() not in {k.lower() for k in kws}:
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
    hook_bits = [b for b in [era, brand, typ] if b]
    lines.append(f"{' '.join(hook_bits)}." if hook_bits else f"{typ}.")

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
        item = json.loads(Path(raw[1:]).read_text(encoding="utf-8")
                          if raw.startswith("@") else raw)
        out = suggest(item, use_corpus=not args.no_corpus)
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
        print("\nSTRUKTURIERTE FELDER (das harte Filter-Tor)")
        for k, v in out["structured_fields"].items():
            print(f"  {k:<10}{v if v else 'TBD'}")
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
