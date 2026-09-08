# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
"""Mine per-product keywords out of the real Vinted corpus, per brand and class.

The static vocabulary in keyword_engine.py is a floor: it knows that jeans have
a cut and a wash, but not that Carhartt's trousers are called Newel, Sid, Landon
and Aviation, or that Patagonia's jackets are Torrentshell and Nano Puff. Those
names are what a buyer actually types, and no hand-written list stays current
with them.

So this reads them off the market instead. The watcher's database holds tens of
thousands of real listing titles tagged by brand family and garment class, which
makes it a corpus of how sellers in exactly this niche describe exactly this
kind of item. Scoring by lift rather than raw frequency is what makes the output
product-specific: "jacke" is common everywhere and says nothing, while
"torrentshell" is sixty times more common in Patagonia jackets than in the
corpus at large and therefore identifies the piece.

This is the half that the tools sold for this job get wrong. Their tag blocks
are brand-wide, so a tank top inherits the tag list of a zip jacket, and foreign
brands ride along for reach. Terms derived from the cell a garment actually
belongs to cannot drift that way, and every term here carries the evidence that
produced it.

Modes:
  --research BRAND/CLASS   ranked keyword candidates for one cell, with evidence
  --cells                  which brand/class cells have enough data to mine
  --fake-vocab             terms that look like counterfeit slang, per brand
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DB_PATH = PROJECT_DIR / "data" / "vinted.db"

# Words that carry no product information: articles, the size and condition
# vocabulary that belongs in structured fields, and marketplace boilerplate.
STOPWORDS = set("""
und oder der die das den dem des ein eine einen einem eines mit fur für von vom
in im am an auf zu zum zur ist sind war wie sehr gut neu neue neuer neues top
gr gre grosse größe size taille tamano talla maat misura eur euro preis price
damen herren mens womens unisex kinder man woman men women homme femme uomo
donna nieuw nieuwe met voor van maat een taglia nuovo nuova neuf neuve pour
avec sans plus tres schon schön super mega best beste hot rare selten
xxs xxl xxxl one onesize einheitsgroesse
""".split())

# Tokens that are sizes, not descriptions. They belong in the size field, where
# Vinted can filter on them; repeating them as keywords buys nothing.
SIZE_TOKEN = re.compile(r"^(x{0,3}[sml]|w\d{2}|l\d{2}|\d{2,3}|\d{2}x\d{2})$")

# Tokens that can ONLY be a size, whatever they sit next to. Kept apart from
# SIZE_TOKEN because a bare 2-3 digit number is ambiguous: 46 is a size and 501
# is the most valuable model name in this corpus, and the same pattern matches
# both. So a bare number is a size only when the whole term is sizes ("w31 46"),
# while an explicit notation makes the phrase around it a size restatement
# ("jeans w31") no matter what else is in it.
SIZE_NOTATION = re.compile(r"^(x{0,3}[sml]|w\d{2}|l\d{2}|\d{2}x\d{2})$")

# Counterfeit slang. Mined terms matching these are never offered as keywords;
# they are reported separately, because a term the forgers use is a signal about
# the market rather than a word to put in a listing.
FAKE_SLANG = re.compile(
    r"^(reps?|replica|replika|replik|fake|aaa|ua|mirror|dhgate|pandabuy|weidian"
    r"|taobao|batch|kopie|copy|inspired|nachbau|clone)$"
)

# Kid vocabulary; those listings are a different market and are excluded.
KID_TOKEN = re.compile(
    r"^(kinder|kids|enfant|jongens|meisjes|baby|bebe|junior|girls|boys|jahre|"
    r"monate|mois|maanden|anni|jaar)$"
)

# The corpus is a German marketplace with a lot of Dutch and French listings.
# Foreign terms are kept but flagged, because writing a German listing in Dutch
# narrows its audience rather than widening it. This hand-written list is only
# the FLOOR, for terms the evidence below is too thin to judge.
FOREIGN_HINT = re.compile(
    r"^(jas|jasje|tussenjas|regenjas|broek|spijkerbroek|trui|vest|jurk|"
    r"veste|blouson|pantalon|chemise|robe|manteau|droit|droite|brut|"
    r"giacca|pantaloni|maglia|camicia|vestito|nuovo)$"
)

# --------------------------------------------------------------- language
#
# The brief proposed weighting terms by seller country. That cannot work here:
# listings.country is filled on 166 of 36,304 rows (0.46%), because the catalog
# response carries no country and the watcher only fetches a seller profile for
# listings that already cleared the deal gate. Joining through the sellers table
# reaches 302 rows. A country weight would be a switch that does nothing.
#
# The language is in the title, where coverage is real: 28.7% of titles carry
# French markers against 15.3% German, which is the leak (the engine offered
# "bleu" for a German listing). The remaining 45% carry no marker at all,
# because "Carhartt Detroit Jacket" is not in any language, and those must count
# for NEITHER side or every brand term would look half-foreign.
LANG_MARKERS = {
    "de": set("""jacke hose pullover pulli hemd kleid rock groesse größe herren damen
        schwarz blau weiss weiß gruen grün rot gelb braun grau kinder neu getragen
        gebraucht mit und sehr gut ohne selten weit eng kurz lang jungen maedchen
        mädchen tasche guter zustand originale echt""".split()),
    "fr": set("""veste blouson pantalon chemise robe manteau pull jean bleu noir blanc
        rouge vert jaune marron gris taille homme femme neuf neuve avec sans pour
        droite droit brut delave délavé enfant porte porté tres très bon etat état
        haute large courte longue poche""".split()),
    "nl": set("""jas jasje broek trui vest jurk spijkerbroek maat heren dames nieuw
        nieuwe zwart blauw wit groen rood geel bruin grijs kinderen met voor van
        gedragen goede staat zonder hoge wijde korte lange zak""".split()),
    "it": set("""giacca pantaloni maglia camicia vestito gonna taglia uomo donna nuovo
        nuova nero blu bianco verde rosso giallo marrone grigio bambino con senza
        usato buono stato alta larga corta lunga tasca""".split()),
}

# A term needs this many language-attributed listings before the evidence is
# allowed to overrule the hand-written floor. Below it the sample is one or two
# sellers, and one French seller does not make a word French.
MIN_LANG_EVIDENCE = 5
# Below this share of German among the attributed listings, a term is a foreign
# word that happens to appear here, not a word this market uses in German.
GERMAN_SHARE_FLOOR = 0.25
# Lift above which a bare number identifies a product line rather than a size.
MODEL_NUMBER_LIFT = 3.0


def title_language(title: str | None) -> str | None:
    """Which language a listing title is written in, or None when it says nothing.

    None is the common and correct answer: a title that is only a brand, a model
    and a size belongs to no language. Returning a guess for those would put
    every brand term into whichever language happened to win a tiebreak.
    """
    words = set(normalise(title))
    hits = {lang: len(words & markers) for lang, markers in LANG_MARKERS.items()}
    best = max(hits, key=lambda k: hits[k])
    if hits[best] == 0:
        return None
    # A tie is genuine ambiguity ("jeans blau" reads German and Dutch), and
    # counting it for one side would bias exactly the shared vocabulary.
    if sum(1 for v in hits.values() if v == hits[best]) > 1:
        return None
    return best


@dataclass
class Term:
    """One mined term plus the evidence that earned it a place."""
    text: str
    n: int                      # listings in this cell containing it
    share: float                # fraction of the cell
    lift: float                 # how much more common here than corpus-wide
    kind: str = "term"          # term | fake-slang | foreign | size | kids | brand
    notes: list[str] = field(default_factory=list)
    ceiling: float = 0.0        # the lift a cell-exclusive term reaches here
    langs: Counter = field(default_factory=Counter)   # language of its listings

    def german_share(self) -> float | None:
        """Share of German among the listings that HAVE an attributable language.

        None when too few are attributable. Language-neutral titles (a brand and
        a model name) are excluded from both numerator and denominator, so a
        model name never looks foreign just because nobody wrote a sentence
        around it.
        """
        attributed = sum(self.langs.values())
        if attributed < MIN_LANG_EVIDENCE:
            return None
        return self.langs.get("de", 0) / attributed

    def score(self) -> float:
        """Rank by how strongly a term identifies this cell, not by raw count.

        Lift alone promotes a term that appears three times and nowhere else;
        share alone promotes the generic word every listing carries. The product
        of the two, with lift damped, puts the identifying-and-common terms on
        top, which is what a buyer types.
        """
        return (self.lift ** 0.5) * self.share

    def is_model_name(self) -> bool:
        """A name only this brand's line uses: absent from the rest of the corpus.

        Torrentshell, Nano Puff, Newel, Sid, Landon. These are the terms a buyer
        types when they know what they want, and they never win on share because
        each names one product out of a catalogue. Judging them by lift alone,
        in their own band, is what keeps them from being buried under "jacke".

        The bar is relative to the ceiling, not a fixed number: a term that
        appears ONLY in this cell reaches lift = corpus size / cell size, so the
        ceiling moves with the data. An absolute threshold silently stops
        recognising model names as soon as a cell grows large relative to the
        corpus, which is exactly when a brand is worth mining.
        """
        if self.kind != "term" or not self.ceiling:
            return False
        return self.lift >= 0.9 * self.ceiling and self.share < 0.6


def language_verdict(term) -> tuple[str, str]:
    """Is this term a foreign WORD, or just a term foreigners happen to use?

    The distinction is the whole difficulty. "Patagonia Nano Puff jas" is a Dutch
    title, but Nano Puff is a product name and belongs in a German listing;
    "jean" is a French word and does not. Judging purely by the language of the
    surrounding titles conflates the two, and it fails on exactly the terms this
    project values most, because a model name inherits whatever language its
    neighbours were written in. Measured on the live corpus, that rule flagged
    Nano Puff (90% Dutch context) and Levi's 501 (85% French context).

    So two tiers, lexical first:

      1. The term's OWN words. A token in a foreign marker set, with none in the
         German set, is a foreign word whatever its context. Precise, and it
         cannot touch a name that is in no dictionary.
      2. Context, but only as a tie-breaker for terms tier 1 says nothing about,
         and only when NOT ONE German-language listing uses the term. That
         catches foreign vocabulary no list happens to name, while a single
         German seller using the word is enough to keep it: a product name in a
         German sentence is a product name.
    """
    parts = term.text.split()
    foreign_hits = {lang: sum(1 for p in parts if p in markers)
                    for lang, markers in LANG_MARKERS.items() if lang != "de"}
    german_hits = sum(1 for p in parts if p in LANG_MARKERS["de"])
    top_lang = max(foreign_hits, key=lambda k: foreign_hits[k]) if foreign_hits else None
    if top_lang and foreign_hits[top_lang] and not german_hits:
        return "foreign", (f"fremdsprachiges Wort ({top_lang}); auf vinted.de "
                           f"schmaelert das die Zielgruppe")
    if german_hits:
        return "german", ""
    if any(FOREIGN_HINT.match(p) for p in parts):
        return "foreign", "fremdsprachig; auf vinted.de schmaelert das die Zielgruppe"

    attributed = sum(term.langs.values())
    if attributed >= MIN_LANG_EVIDENCE and term.langs.get("de", 0) == 0:
        top = term.langs.most_common(1)[0][0]
        return "foreign", (f"alle {attributed} sprachlich zuordenbaren Belege sind "
                           f"{top}, keiner deutsch")
    return "unknown", ""


def normalise(title: str | None) -> list[str]:
    text = re.sub(r"[^0-9a-zA-ZäöüÄÖÜßéèêàçñ]+", " ", (title or "").lower())
    return [w for w in text.split() if len(w) >= 2]


def ngrams(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def size_numbers_of(con: sqlite3.Connection) -> set[str]:
    """Every number the corpus uses as a SIZE, read off the size column itself.

    The size field is the market's own answer to "is this number a size", and it
    needs no threshold: 32 is in there (from W32 and DE 32), 501 is not. Read
    once per run over the distinct values, of which there are a few hundred.
    """
    numbers: set[str] = set()
    # A table shape without the column skips the check rather than crashing the
    # whole research run, the same way the watcher's data fixes do. Losing the
    # size/model split costs precision on one term class; raising costs the run.
    have = {row[1] for row in con.execute("PRAGMA table_info(listings)")}
    if "size" not in have:
        return numbers
    for (size,) in con.execute("SELECT DISTINCT size FROM listings WHERE size IS NOT NULL"):
        for token in re.findall(r"\d{1,3}", str(size)):
            numbers.add(token.lstrip("0") or token)
    return numbers


def classify(term: str, brand_norm: str, lift: float = 0.0,
             size_numbers: set[str] | None = None) -> tuple[str, list[str]]:
    """What kind of thing this term is, which decides whether it may be a keyword."""
    parts = term.split()
    notes: list[str] = []
    if any(KID_TOKEN.match(p) for p in parts):
        return "kids", notes
    if any(FAKE_SLANG.match(p) for p in parts):
        return "fake-slang", notes
    # An explicit size notation poisons the whole phrase: "jeans w31" spends a
    # keyword slot restating the size field, which Vinted filters on anyway.
    if any(SIZE_NOTATION.match(p) for p in parts):
        return "size", ["gehoert ins Groessenfeld, nicht in den Text"]
    if all(SIZE_TOKEN.match(p) for p in parts):
        # A bare number is the genuinely ambiguous case: 46 is a size and 501 is
        # the most valuable model name in this corpus, and one pattern matches
        # both. The size COLUMN settles it, because it is the authority on what
        # counts as a size in this market: 32 appears there (as W32 and DE 32),
        # 501 never does. Lift alone did not work, since a numeric size in a
        # brand that sizes numerically is cell-specific too and scored 7.4x in
        # carhartt/pants, indistinguishable from a model number.
        if size_numbers is not None and all(p in size_numbers for p in parts):
            return "size", ["gehoert ins Groessenfeld, nicht in den Text"]
        if size_numbers is not None and lift >= MODEL_NUMBER_LIFT:
            return "term", notes
        return "size", ["gehoert ins Groessenfeld, nicht in den Text"]
    if any(FOREIGN_HINT.match(p) for p in parts):
        return "foreign", ["fremdsprachig; auf vinted.de schmaelert das die Zielgruppe"]
    brand_words = {w for w in re.split(r"[^a-z0-9]+", brand_norm) if w}
    # Sub-brand spellings the family key does not contain, so that "carhartt wip"
    # is recognised as brand padding rather than as a description.
    brand_words |= {"wip", "originals", "polo", "lauren", "sport", "air", "sb", "acg"}
    # The corpus spells brands as sellers type them, so an apostrophe or a
    # plural drops out: "Levi's" normalises to "levi", which the family key
    # "levis" does not match. Stems close that gap.
    brand_words |= {w[:-1] for w in list(brand_words) if len(w) > 4 and w.endswith("s")}
    brand_words |= {w + "s" for w in list(brand_words) if len(w) > 3}
    if parts and all(p in brand_words for p in parts):
        return "brand", ["steht schon im Markenfeld"]
    # An n-gram whose only content is the brand plus one ordinary word says
    # nothing the brand field and that word do not already say on their own.
    if len(parts) > 1 and any(p in brand_words for p in parts):
        return "brand-padded", ["Marke plus Allerweltswort; beides steht schon einzeln da"]
    return "term", notes


def mine_cell(con: sqlite3.Connection, brand_norm: str, garment_class: str,
              max_n: int = 3, min_count: int = 3) -> tuple[list[Term], int]:
    """Terms that distinguish one brand-and-class cell from the whole corpus."""
    cell_titles = [r[0] for r in con.execute(
        """SELECT title FROM listings
           WHERE brand_norm=? AND garment_class=? AND COALESCE(is_kid,0)=0""",
        (brand_norm, garment_class)).fetchall()]
    n_cell = len(cell_titles)
    if n_cell == 0:
        return [], 0

    cell = Counter()
    # Per term, which languages its listings were written in. This is what
    # replaces the unusable country column: evidence gathered from the same
    # titles the terms come from, so coverage is by construction the same.
    term_langs: dict[str, Counter] = {}
    for title in cell_titles:
        words = [w for w in normalise(title) if w not in STOPWORDS]
        seen = set()
        for n in range(1, max_n + 1):
            seen.update(ngrams(words, n))
        cell.update(seen)
        lang = title_language(title)
        if lang:
            for term in seen:
                term_langs.setdefault(term, Counter())[lang] += 1

    # Background frequency over the whole corpus, so lift measures specificity.
    background = Counter()
    n_all = 0
    for (title,) in con.execute("SELECT title FROM listings"):
        words = [w for w in normalise(title) if w not in STOPWORDS]
        seen = set()
        for n in range(1, max_n + 1):
            seen.update(ngrams(words, n))
        background.update(seen)
        n_all += 1

    size_nums = size_numbers_of(con)
    floor = max(min_count, int(n_cell * 0.005))
    # The lift a term reaches if it appears in this cell and nowhere else.
    ceiling = (n_all / n_cell) if n_cell else 0.0
    terms: list[Term] = []
    for text, k in cell.items():
        if k < floor:
            continue
        share = k / n_cell
        p_all = background[text] / n_all if n_all else 0
        lift = (share / p_all) if p_all else 0.0
        kind, notes = classify(text, brand_norm, lift, size_nums)
        term = Term(text=text, n=k, share=share, lift=lift, kind=kind,
                    notes=notes, ceiling=ceiling,
                    langs=term_langs.get(text, Counter()))
        # The measured language overrules the hand-written list in both
        # directions: a term this market writes in German stays usable even if
        # it looks foreign, and a term the evidence says is French is dropped
        # even though no list named it. That is the whole point of measuring;
        # "bleu" was reaching listings because no list happened to contain it.
        if term.kind in ("term", "foreign"):
            verdict, why = language_verdict(term)
            if verdict == "foreign":
                term.kind, term.notes = "foreign", [why]
            elif verdict == "german" and term.kind == "foreign":
                term.kind, term.notes = "term", []
        terms.append(term)

    # A longer phrase that always appears inside a shorter one adds nothing;
    # prefer the phrase, drop the fragment it subsumes.
    by_text = {t.text: t for t in terms}
    redundant = set()
    for t in terms:
        if " " not in t.text:
            continue
        for part in t.text.split():
            other = by_text.get(part)
            if other and other.n <= t.n * 1.15:
                redundant.add(part)
    terms = [t for t in terms if t.text not in redundant]

    # Cell-exclusive terms all land on the same lift, so score alone leaves them
    # tied and the ordering falls to insertion chance. Preferring the longer
    # phrase among equals puts "newel pant" above "pant relaxed", which is the
    # one that names the product.
    terms.sort(key=lambda t: (round(t.score(), 6), len(t.text.split()), t.n),
               reverse=True)
    return terms, n_cell


def research(con: sqlite3.Connection, brand_norm: str, garment_class: str,
             limit: int = 12) -> dict:
    """The bot's answer for one cell: ranked keywords plus what backs them."""
    terms, n_cell = mine_cell(con, brand_norm, garment_class)
    usable = [t for t in terms if t.kind == "term"]
    models = sorted([t for t in usable if t.is_model_name()],
                    key=lambda t: t.lift, reverse=True)
    rejected = [t for t in terms if t.kind != "term"]

    price_row = con.execute(
        """SELECT COUNT(*), AVG(total_price) FROM listings
           WHERE brand_norm=? AND garment_class=? AND COALESCE(is_kid,0)=0
             AND total_price BETWEEN 3 AND 400""",
        (brand_norm, garment_class)).fetchone()

    return {
        "cell": f"{brand_norm}/{garment_class}",
        "corpus_size": n_cell,
        "priced_listings": price_row[0],
        "mean_price": round(price_row[1], 2) if price_row[1] else None,
        "keywords": [
            {"term": t.text, "n": t.n, "share": round(t.share, 4),
             "lift": round(t.lift, 1), "score": round(t.score(), 4)}
            for t in usable[:limit]
        ],
        "model_names": [
            {"term": t.text, "n": t.n, "share": round(t.share, 4), "lift": round(t.lift, 1)}
            for t in models[:limit]
        ],
        "rejected": [
            {"term": t.text, "kind": t.kind, "n": t.n, "lift": round(t.lift, 1),
             "notes": t.notes}
            for t in rejected[:12]
        ],
        "confidence": ("gut" if n_cell >= 300 else "mittel" if n_cell >= 80 else "duenn"),
    }


def keywords_for(con: sqlite3.Connection, brand_norm: str, garment_class: str,
                 title_hint: str | None = None, limit: int = 8) -> list[str]:
    """Keywords for one listing, biased toward what its own title already says.

    A cell-level ranking describes the category; this narrows it to the piece in
    hand. A term the seller's own title contains is evidence about THIS garment
    rather than about its neighbours, so it outranks a term that merely leads
    the category.
    """
    terms, _ = mine_cell(con, brand_norm, garment_class)
    hint = set(normalise(title_hint)) if title_hint else set()
    scored = []
    for t in terms:
        if t.kind != "term":
            continue
        in_title = all(p in hint for p in t.text.split()) if hint else False
        # Band 2 is a model name the seller's own title names: the strongest
        # evidence available about THIS garment. Band 1 is any other term the
        # title confirms. Band 0 is the category ranking.
        band = 2 if (in_title and t.is_model_name()) else (1 if in_title else 0)
        scored.append((band, t.score(), t.text))
    scored.sort(reverse=True)
    return [text for _, _, text in scored[:limit]]


def fake_vocab(con: sqlite3.Connection, brand_norm: str | None = None) -> list[dict]:
    """Counterfeit slang the corpus actually contains, per brand.

    Worth surfacing on its own: the forgers' vocabulary is a live signal about
    which brands are being faked here, and it feeds the watcher's title markers
    with evidence rather than guesswork.
    """
    where = "WHERE COALESCE(is_kid,0)=0" + (" AND brand_norm=?" if brand_norm else "")
    params = (brand_norm,) if brand_norm else ()
    hits: dict[str, Counter] = {}
    totals: Counter = Counter()
    for bn, title in con.execute(
            "SELECT brand_norm, title FROM listings " + where, params):
        totals[bn] += 1
        for word in normalise(title):
            if FAKE_SLANG.match(word):
                hits.setdefault(bn, Counter())[word] += 1
    out = []
    for bn, counter in sorted(hits.items(), key=lambda kv: -sum(kv[1].values())):
        out.append({
            "brand": bn,
            "listings": totals[bn],
            "hits": sum(counter.values()),
            "rate": round(sum(counter.values()) / totals[bn], 5) if totals[bn] else 0,
            "terms": counter.most_common(6),
        })
    return out


def cells(con: sqlite3.Connection, min_rows: int = 60) -> list[tuple[str, str, int]]:
    return [(b, g, n) for b, g, n in con.execute(
        """SELECT brand_norm, garment_class, COUNT(*) FROM listings
           WHERE brand_norm IS NOT NULL AND brand_norm!='' AND garment_class!='other'
             AND COALESCE(is_kid,0)=0
           GROUP BY brand_norm, garment_class HAVING COUNT(*) >= ?
           ORDER BY COUNT(*) DESC""", (min_rows,)).fetchall()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research", metavar="BRAND/CLASS",
                    help="ranked keywords for one cell, e.g. patagonia/jacket")
    ap.add_argument("--cells", action="store_true", help="cells with enough data to mine")
    ap.add_argument("--fake-vocab", action="store_true",
                    help="counterfeit slang present in the corpus, per brand")
    ap.add_argument("--brand", help="restrict --fake-vocab to one brand family")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print("no database at " + str(DB_PATH))
        sys.exit(1)
    con = sqlite3.connect("file:" + str(DB_PATH) + "?mode=ro", uri=True)
    try:
        if args.cells:
            rows = cells(con)
            if args.json:
                print(json.dumps([{"brand": b, "class": g, "n": n} for b, g, n in rows], indent=2))
            else:
                print("%-24s%-12s%s" % ("Marke", "Klasse", "Anzeigen"))
                for b, g, n in rows:
                    print("%-24s%-12s%d" % (b, g, n))
            return

        if args.fake_vocab:
            rows = fake_vocab(con, args.brand)
            if args.json:
                print(json.dumps(rows, indent=2, ensure_ascii=False))
                return
            if not rows:
                print("keine Faelscher-Begriffe im Korpus gefunden")
                return
            print("Faelscher-Vokabular im Korpus (Belege, keine Vermutung):\n")
            print("%-24s%10s%8s%9s   %s" % ("Marke", "Anzeigen", "Treffer", "Quote", "Begriffe"))
            for r in rows:
                terms = ", ".join("%s x%d" % (t, k) for t, k in r["terms"])
                print("%-24s%10d%8d%8.3f%%   %s"
                      % (r["brand"], r["listings"], r["hits"], 100 * r["rate"], terms))
            return

        if args.research:
            if "/" not in args.research:
                print("erwarte MARKE/KLASSE, z.B. patagonia/jacket")
                sys.exit(2)
            brand, cls = args.research.split("/", 1)
            out = research(con, brand.strip(), cls.strip())
            if args.json:
                print(json.dumps(out, indent=2, ensure_ascii=False))
                return
            if not out["corpus_size"]:
                print("keine Anzeigen fuer %s" % out["cell"])
                sys.exit(1)
            print("Zelle %s   Korpus %d Anzeigen   Quellenlage %s"
                  % (out["cell"], out["corpus_size"], out["confidence"]))
            if out["mean_price"]:
                print("Durchschnittspreis %.2f EUR ueber %d Anzeigen"
                      % (out["mean_price"], out["priced_listings"]))
            print("\nKeyword-Kandidaten, nach Aussagekraft fuer diese Zelle:")
            print("  %-28s%8s%9s%9s" % ("Begriff", "Anz.", "Anteil", "Lift"))
            for k in out["keywords"]:
                print("  %-28s%8d%8.1f%%%8.1fx" % (k["term"], k["n"], 100 * k["share"], k["lift"]))
            if out["model_names"]:
                print("\nModellnamen dieser Linie (nach Lift, weil sie nie auf Anteil gewinnen):")
                print("  %-28s%8s%9s%9s" % ("Begriff", "Anz.", "Anteil", "Lift"))
                for k in out["model_names"]:
                    print("  %-28s%8d%8.1f%%%8.1fx"
                          % (k["term"], k["n"], 100 * k["share"], k["lift"]))
            if out["rejected"]:
                print("\nAussortiert, mit Grund:")
                for r in out["rejected"]:
                    note = ("; ".join(r["notes"])) or {
                        "size": "Groessenangabe", "kids": "Kinderware",
                        "fake-slang": "Faelscher-Vokabular", "brand": "steht im Markenfeld",
                        "foreign": "fremdsprachig"}.get(r["kind"], r["kind"])
                    print("  %-28s%-14s%s" % (r["term"], r["kind"], note))
            print("\nLift heisst: um diesen Faktor haeufiger in dieser Zelle als im gesamten")
            print("Korpus. Ein hoher Lift identifiziert das Teil, ein hoher Anteil beschreibt")
            print("die Kategorie; die Rangfolge gewichtet beides.")
            return

        ap.print_help()
    finally:
        con.close()


if __name__ == "__main__":
    main()
