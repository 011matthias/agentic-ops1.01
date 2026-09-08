# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0"]
# ///
"""My side of the business: what I bought, what I listed, and whether it sold.

Two jobs that belong together because they are one flow.

**From a tap to a draft.** Tapping "Gekauft" on the phone writes a row to
alert_feedback, and the database already knows almost everything about that
listing: brand, size, condition, garment class, what I paid, what comparable
items go for, where the seller was, when it was posted. Retyping any of that
into the listing engine by hand is work the machine already did. This assembles
the draft from the row, prices it off the cell's live comps, and asks only for
the three things a photo cannot be parsed for: colour, material, measurements.
Those come out as a short list of open questions rather than hidden inside the
text as "TBD", because a question gets answered and a TBD gets shipped.

**A ledger of my own listings.** Nothing recorded what I actually put up, for
what, with which keywords, or whether it sold. Without that the keyword ranking
is a hypothesis with no feedback path: the corpus can say how other sellers
describe a jacket, but only my own sold listings can say whether the bot's
suggestions worked. `--record` writes the draft into my_listings, `--sold`
closes it out.

Modes:
  --bought                  purchases with no draft yet
  --draft LISTING_ID        the full listing draft for one purchase
  --draft-latest            the same for the most recent purchase
  --record LISTING_ID       file the draft into my own listings
  --mine                    my listings and how they are doing
  --sold MY_ID --price EUR  close one out as sold
"""

import argparse
import importlib.util
import json
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DB_PATH = PROJECT_DIR / "data" / "vinted.db"

# Recovered from 36,229 real price pairs in the corpus, not assumed: the buyer
# protection fee is 0.70 EUR plus 5% of the item price, with a maximum absolute
# error of half a cent across the whole set. It matters because every comp in
# this database is a total_price (what a buyer pays) while the number I type
# into Vinted is the item price, and confusing the two overprices every listing
# by the fee.
FEE_FIXED = 0.70
FEE_RATE = 0.05

# What the database cannot know from a catalog row, in the order a listing
# needs them. Material is a Vinted filter field, so its absence costs
# visibility rather than just detail; measurements are the most common buyer
# question on garments.
UNKNOWABLE = {
    "color": "Farbe (Vinted-Filterfeld; ohne sie faellt das Teil aus Farbfiltern)",
    "material": "Material (Filterfeld; steht meist im Innenetikett)",
    "measurements": "Masse flach gemessen (Bund, Schritt, Laenge bzw. Brust, Laenge, Aermel)",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


def load_sibling(name: str):
    """Import a module that sits next to this one, without needing a package."""
    return load_module(name, SCRIPT_DIR / f"{name}.py")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database THROUGH the watcher, so there is one schema owner.

    my_listings is declared in the watcher's DDL and reaches existing databases
    via its reconcile_ddl_columns machinery. Creating the table here as well
    would fork the definition: two places to edit, and the copies drift the
    first time only one of them is updated. So this borrows the watcher's
    db_connect, which also means a database opened by this tool gets exactly
    the same migrations as one opened by the poller.
    """
    vw = load_module("vinted_watcher_for_inventory",
                     PROJECT_DIR / "watcher" / "vinted_watcher.py")
    vw.DATA_DIR = db_path.parent
    vw.DB_PATH = db_path
    con = vw.db_connect()
    con.row_factory = sqlite3.Row
    return con


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def total_to_price(total: float) -> float:
    """The item price whose buyer total is `total`. The inverse of the fee."""
    return round((total - FEE_FIXED) / (1 + FEE_RATE), 2)


def price_to_total(price: float) -> float:
    return round(price + FEE_FIXED + FEE_RATE * price, 2)


# ------------------------------------------------------------------ purchases

def bought(con: sqlite3.Connection) -> list[dict]:
    """Everything tapped as bought, newest first, with what is known about it.

    LEFT JOINs throughout: a rating can outlive both its alert snapshot and the
    listing row (a tap on a listing this database has since lost is still a
    purchase), and dropping those would hide real inventory.
    """
    # Every column is aliased. Without that, l.title and a.title collide in the
    # row mapping and the last one silently wins, which is how a snapshot-only
    # purchase would come out looking like it had no title at all.
    rows = con.execute(
        """SELECT f.listing_id            AS listing_id,
                  f.received_at           AS bought_at,
                  COALESCE(l.title, a.title)             AS title,
                  COALESCE(l.total_price, a.total_at_alert) AS buy_total,
                  a.comp_median           AS comp_median,
                  m.id                    AS my_id,
                  m.status                AS my_status
           FROM alert_feedback f
           LEFT JOIN listings l ON l.id = f.listing_id
           LEFT JOIN alerts   a ON a.id = f.alert_id
           LEFT JOIN my_listings m ON m.source_listing_id = f.listing_id
           WHERE f.verdict = 'bought'
           ORDER BY f.received_at DESC""").fetchall()
    return [dict(r) for r in rows]


def _first(*values):
    for v in values:
        if v not in (None, ""):
            return v
    return None


def purchase(con: sqlite3.Connection, listing_id: int) -> dict | None:
    """One purchase, with the listing row and the alert snapshot merged."""
    listing = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    fb = con.execute(
        "SELECT * FROM alert_feedback WHERE listing_id=? AND verdict='bought'"
        " ORDER BY received_at DESC LIMIT 1", (listing_id,)).fetchone()
    if fb is None:
        return None
    alert = None
    if fb["alert_id"]:
        alert = con.execute("SELECT * FROM alerts WHERE id=?", (fb["alert_id"],)).fetchone()
    if alert is None:
        alert = con.execute(
            "SELECT * FROM alerts WHERE listing_id=? ORDER BY id DESC LIMIT 1",
            (listing_id,)).fetchone()

    def field(name):
        return _first(listing[name] if listing and name in listing.keys() else None,
                      alert[name] if alert and name in alert.keys() else None)

    return {
        "listing_id": listing_id,
        "bought_at": fb["received_at"],
        "title": field("title"),
        "brand": _first(listing["brand"] if listing else None,
                        alert["brand"] if alert else None),
        "brand_norm": field("brand_norm"),
        "size": field("size"),
        "size_class": field("size_class"),
        "condition": field("condition"),
        "cond_tier": field("cond_tier"),
        "garment_class": field("garment_class"),
        "photo_url": listing["photo_url"] if listing else None,
        "url": listing["url"] if listing else None,
        "country": field("country"),
        "posted_at": field("posted_at"),
        "seller_login": listing["seller_login"] if listing else None,
        "buy_total": _first(listing["total_price"] if listing else None,
                            alert["total_at_alert"] if alert else None),
        "comp_median": alert["comp_median"] if alert else None,
        "comp_p25": alert["comp_p25"] if alert else None,
        "comp_p75": alert["comp_p75"] if alert else None,
        "comp_n": alert["comp_n"] if alert else None,
        "discount_pct": alert["discount_pct"] if alert else None,
        "has_listing_row": listing is not None,
    }


# --------------------------------------------------------------------- price

def comps_now(con: sqlite3.Connection, brand_norm: str, garment_class: str,
              cond_tier: str | None, size_class: str | None) -> dict:
    """Live comparable asking prices for the cell, in buyer-paid totals.

    Deliberately widened in steps rather than failing: the exact cell (brand,
    class, condition, size) is the honest comparison, but a thin cell would
    otherwise return nothing at all, and a wider pool clearly labelled is worth
    more than silence. Every result says which pool produced it.
    """
    attempts = [
        ("Marke + Klasse + Zustand + Groesse",
         "brand_norm=? AND garment_class=? AND cond_tier=? AND size_class=?",
         (brand_norm, garment_class, cond_tier, size_class)),
        ("Marke + Klasse + Zustand",
         "brand_norm=? AND garment_class=? AND cond_tier=?",
         (brand_norm, garment_class, cond_tier)),
        ("Marke + Klasse",
         "brand_norm=? AND garment_class=?",
         (brand_norm, garment_class)),
    ]
    for label, where, params in attempts:
        if any(p in (None, "") for p in params):
            continue
        prices = [r[0] for r in con.execute(
            f"SELECT total_price FROM listings WHERE {where}"
            " AND total_price BETWEEN 3 AND 400 AND COALESCE(is_kid,0)=0", params)]
        if len(prices) >= 20:
            prices.sort()
            return {
                "pool": label, "n": len(prices),
                "median": round(statistics.median(prices), 2),
                "p25": round(prices[int(0.25 * (len(prices) - 1))], 2),
                "p75": round(prices[int(0.75 * (len(prices) - 1))], 2),
            }
    return {"pool": None, "n": 0, "median": None, "p25": None, "p75": None}


def price_advice(buy_total: float | None, comps: dict) -> dict:
    """What to ask, why, and what it earns. Framed as asking prices, not sales.

    The corpus is an OFFER corpus: it records what sellers want, not what
    buyers paid. So the median is "what comparable items are listed at", and
    the recommendation says so. Pricing at the median means competing with
    every unsold listing in the cell; the p25-to-median band is where a piece
    that is meant to move actually sits, so the suggestion is the midpoint of
    that band, converted from buyer total to the number Vinted asks me for.
    """
    med, p25 = comps.get("median"), comps.get("p25")
    if med is None:
        return {"ask_price": None, "note": "keine ausreichende Vergleichsbasis"}
    target_total = med if p25 is None else round((med + p25) / 2, 2)
    ask = total_to_price(target_total)
    out = {
        "ask_price": ask,
        "buyer_pays": price_to_total(ask),
        "comp_median_total": med,
        "comp_p25_total": p25,
        "comp_p75_total": comps.get("p75"),
        "pool": comps.get("pool"),
        "comp_n": comps.get("n"),
    }
    if buy_total:
        out["buy_total"] = round(buy_total, 2)
        out["margin_eur"] = round(ask - buy_total, 2)
        out["margin_pct"] = round(100 * (ask - buy_total) / buy_total)
    return out


# --------------------------------------------------------------------- draft

def model_from_title(con: sqlite3.Connection, p: dict) -> tuple[str | None, str | None]:
    """The model name hiding in the seller's own title, per the corpus.

    "Levi's Jeans 501 Herren" carries the single most valuable token there is
    and the structured fields do not: 501 is what a buyer types. Rather than
    keep a hand-written list of model names, this asks the corpus which terms
    identify this cell (keyword_research ranks them by lift precisely because
    model names never win on frequency) and keeps the ones the seller's own
    title actually contains. Returns (model, garment_noun).
    """
    if not (p["brand_norm"] and p["garment_class"] and p["title"]):
        return None, None
    try:
        kr = load_sibling("keyword_research")
        terms, _ = kr.mine_cell(con, p["brand_norm"], p["garment_class"])
    except Exception:
        return None, None                    # research must never break a draft
    words = set(kr.normalise(p["title"]))
    # The noun is resolved FIRST and then excluded from the model, because the
    # corpus ranks the compound "jeans 501" above the bare "501" and taking it
    # as the model produced "Levi's Jeans 501 Jeans". The noun is the common
    # word of the cell that the seller's own title uses: "Jeans" beats the
    # internal label "pants" and beats the generic "Hose".
    nouns = [t.text for t in terms
             if t.kind == "term" and " " not in t.text and t.text in words
             and t.share > 0.15]
    noun = nouns[0] if nouns else None

    def strip_noun(text: str) -> str:
        return " ".join(w for w in text.split() if w != noun)

    models = []
    for t in terms:
        if t.kind != "term" or not t.is_model_name():
            continue
        if not all(part in words for part in t.text.split()):
            continue
        bare = strip_noun(t.text)
        if bare:
            models.append((len(bare.split()), -t.lift, bare))
    # Shortest first: a model name is the token that identifies the line, and
    # every extra word in it is a word the title then says twice.
    models.sort()
    model = models[0][2] if models else None
    return (model.upper() if model and model.isdigit() else
            (model.title() if model else None)), (noun.title() if noun else None)


def draft(con: sqlite3.Connection, listing_id: int, use_corpus: bool = True) -> dict:
    """Assemble the full listing proposal for one purchase."""
    ke = load_sibling("keyword_engine")
    p = purchase(con, listing_id)
    if p is None:
        raise LookupError(f"kein 'Gekauft' fuer Listing {listing_id}")

    model, noun = model_from_title(con, p) if use_corpus else (None, None)
    item = {
        "brand": p["brand"],
        "type": noun or ke.CLASS_NOUN.get(p["garment_class"] or "", p["garment_class"]),
        "garment_class": p["garment_class"],
        "size": p["size"],
        "condition": p["condition"],
    }
    if model:
        item["model"] = model
    comps = comps_now(con, p["brand_norm"], p["garment_class"],
                      p["cond_tier"], p["size_class"])
    # The frozen snapshot is what the buy decision was made against; the live
    # pool is what the sale will be made against. Both are shown because they
    # answer different questions.
    price = price_advice(p["buy_total"], comps)
    if p["comp_median"]:
        price["comp_median_at_purchase"] = p["comp_median"]

    suggestion = ke.suggest(item, use_corpus=use_corpus)
    questions = [text for key, text in UNKNOWABLE.items() if not item.get(key)]
    if not p["has_listing_row"]:
        questions.append("Diese Zeile kennt nur der Alert-Schnappschuss; "
                         "Titel und Groesse vor dem Einstellen pruefen")
    return {"purchase": p, "price": price, "listing": suggestion,
            "open_questions": questions}


# --------------------------------------------------------- my own listings

def record(con: sqlite3.Connection, d: dict, ask_price: float | None = None,
           **over) -> int:
    """File a draft into my_listings. Returns the new row id."""
    p, price, listing = d["purchase"], d["price"], d["listing"]
    ask = ask_price if ask_price is not None else price.get("ask_price")
    ts = now_iso()
    cur = con.execute(
        """INSERT INTO my_listings (vinted_item_id, source_listing_id, title, brand,
               brand_norm, garment_class, size, size_class, condition, cond_tier,
               color, material, keywords, description, buy_price, ask_price,
               comp_median_at_listing, listed_at, status, notes, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (over.get("vinted_item_id"), p["listing_id"], listing["title"], p["brand"],
         p["brand_norm"], p["garment_class"], p["size"], p["size_class"],
         p["condition"], p["cond_tier"], over.get("color"), over.get("material"),
         json.dumps(listing["keywords"], ensure_ascii=False), listing["description"],
         p["buy_total"], ask, price.get("comp_median_total"),
         over.get("listed_at"), over.get("status", "draft"), over.get("notes"), ts, ts))
    con.commit()
    return cur.lastrowid


def mark_sold(con: sqlite3.Connection, my_id: int, sold_price: float,
              sold_at: str | None = None) -> bool:
    cur = con.execute(
        "UPDATE my_listings SET status='sold', sold_at=?, sold_price=?, updated_at=?"
        " WHERE id=?", (sold_at or now_iso(), sold_price, now_iso(), my_id))
    con.commit()
    return cur.rowcount > 0


def mine(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT * FROM my_listings ORDER BY COALESCE(listed_at, created_at) DESC")]


# ------------------------------------------------------------------------ cli

def eur(v) -> str:
    return f"{v:.2f} EUR" if isinstance(v, (int, float)) else "-"


def print_draft(d: dict) -> None:
    p, price, listing = d["purchase"], d["price"], d["listing"]
    print(f"GEKAUFT   {p['title'] or '(kein Titel gespeichert)'}")
    print(f"          Listing {p['listing_id']}, getippt {p['bought_at']}")
    bits = [b for b in (p["brand"], p["size"], p["condition"],
                        p["garment_class"], p["country"]) if b]
    print("          " + " | ".join(bits))
    if p["url"]:
        print(f"          {p['url']}")

    print(f"\nPREIS     Einkauf {eur(p['buy_total'])}")
    if price.get("ask_price") is None:
        print(f"          {price.get('note')}")
    else:
        print(f"          Vorschlag {eur(price['ask_price'])}  "
              f"(Kaeufer zahlt {eur(price['buyer_pays'])} inkl. Gebuehr)")
        print(f"          Marge {eur(price.get('margin_eur'))}"
              f"  ({price.get('margin_pct')}% auf den Einkauf)")
        print(f"          Vergleich: Median {eur(price['comp_median_total'])}, "
              f"p25 {eur(price['comp_p25_total'])}, p75 {eur(price['comp_p75_total'])} "
              f"ueber {price['comp_n']} Anzeigen")
        print(f"          Pool: {price['pool']}")
        print("          Das sind ANGEBOTS-Preise, keine Verkaeufe: was Verkaeufer")
        print("          verlangen, nicht was Kaeufer gezahlt haben.")

    print(f"\nTITEL     ({listing['title_len']} Zeichen)")
    print("          " + listing["title"])
    print("\nBESCHREIBUNG")
    for line in listing["description"].splitlines():
        print("          " + line)
    print(f"\nKEYWORDS  ({len(listing['keywords'])})")
    print("          " + ", ".join(listing["keywords"]))
    print("\nSTRUKTURIERTE FELDER (das harte Filter-Tor)")
    for k, v in listing["structured_fields"].items():
        print(f"          {k:<10}{v if v else 'OFFEN'}")

    if d["open_questions"]:
        print("\nOFFENE FRAGEN (das, was die Datenbank nicht wissen kann)")
        for q in d["open_questions"]:
            print("          - " + q)
    v = listing["validation"]
    print("\nPRUEFUNG: " + ("OK" if v["ok"] else "PROBLEME"))
    for problem in v["problems"]:
        print("          [!] " + problem)
    for warning in v["warnings"]:
        print("          [~] " + warning)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bought", action="store_true", help="purchases and their draft state")
    ap.add_argument("--draft", type=int, metavar="LISTING_ID")
    ap.add_argument("--draft-latest", action="store_true")
    ap.add_argument("--record", type=int, metavar="LISTING_ID",
                    help="file the draft into my_listings")
    ap.add_argument("--mine", action="store_true", help="my own listings")
    ap.add_argument("--sold", type=int, metavar="MY_ID")
    ap.add_argument("--price", type=float, help="with --sold, or override the ask on --record")
    ap.add_argument("--color"), ap.add_argument("--material")
    ap.add_argument("--vinted-id", type=int, help="the item id Vinted gave my listing")
    ap.add_argument("--no-corpus", action="store_true")
    ap.add_argument("--db", help="database path (default: the project's)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db = Path(args.db) if args.db else DB_PATH
    if not db.exists():
        print(f"keine Datenbank unter {db}")
        sys.exit(1)
    con = connect(db)
    try:
        if args.sold is not None:
            if args.price is None:
                print("--sold braucht --price")
                sys.exit(2)
            ok = mark_sold(con, args.sold, args.price)
            print(f"my_listings {args.sold} als verkauft eingetragen" if ok
                  else f"keine eigene Anzeige mit id {args.sold}")
            sys.exit(0 if ok else 1)

        if args.mine:
            rows = mine(con)
            if args.json:
                print(json.dumps(rows, indent=2, ensure_ascii=False))
                return
            if not rows:
                print("noch keine eigenen Anzeigen erfasst "
                      "(--record LISTING_ID nach einem Entwurf)")
                return
            print("%-4s%-34s%9s%9s%9s  %s" % ("id", "Titel", "Einkauf", "Preis", "Verkauft", "Status"))
            for r in rows:
                print("%-4s%-34s%9s%9s%9s  %s" % (
                    r["id"], (r["title"] or "")[:33], eur(r["buy_price"]),
                    eur(r["ask_price"]), eur(r["sold_price"]), r["status"]))
            sold = [r for r in rows if r["status"] == "sold" and r["sold_price"] and r["buy_price"]]
            if sold:
                profit = sum(r["sold_price"] - r["buy_price"] for r in sold)
                print(f"\n{len(sold)} verkauft, Rohertrag {eur(profit)}")
            return

        if args.bought:
            rows = bought(con)
            if args.json:
                print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
                return
            if not rows:
                print("noch nichts als 'Gekauft' getippt")
                return
            print("%-12s%-34s%10s%10s  %s" % ("Listing", "Titel", "Einkauf", "Median", "Entwurf"))
            for r in rows:
                print("%-12s%-34s%10s%10s  %s" % (
                    r["listing_id"], (r["title"] or "(nur Schnappschuss)")[:33],
                    eur(r["buy_total"]), eur(r["comp_median"]),
                    r["my_status"] if r["my_id"] else "offen"))
            return

        target = args.draft or args.record
        if args.draft_latest:
            row = con.execute(
                "SELECT listing_id FROM alert_feedback WHERE verdict='bought'"
                " ORDER BY received_at DESC LIMIT 1").fetchone()
            if row is None:
                print("noch nichts als 'Gekauft' getippt")
                sys.exit(1)
            target = row[0]
        if target is None:
            ap.print_help()
            return

        try:
            d = draft(con, target, use_corpus=not args.no_corpus)
        except LookupError as e:
            print(e)
            sys.exit(1)

        if args.record:
            my_id = record(con, d, ask_price=args.price, color=args.color,
                           material=args.material, vinted_item_id=args.vinted_id,
                           listed_at=now_iso(), status="listed")
            print(f"als eigene Anzeige {my_id} erfasst "
                  f"(Preis {eur(args.price if args.price is not None else d['price'].get('ask_price'))})")
            return

        if args.json:
            print(json.dumps(d, indent=2, ensure_ascii=False, default=str))
            return
        print_draft(d)
    finally:
        con.close()


if __name__ == "__main__":
    main()
