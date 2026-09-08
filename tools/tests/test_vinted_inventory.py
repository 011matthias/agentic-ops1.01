"""Regression suite for the listing drafts, lenient input, language, trend and demand.

Covers points 2 to 7b of the 2026-09-09 listing-bot brief:

  2  a "Gekauft" tap becomes a priced listing draft with no retyping
  3  input is read leniently (German keys, free text) and gaps become QUESTIONS
  4  foreign-language terms stop leaking into German listings
  5  trend is computed on observed windows, or refuses with the shortfall
  6  my own listings are recorded so suggestions can ever be evaluated
  7b terms are weighted by real sales once there are enough of them

The refusal paths matter as much as the success paths here. A tool that
fabricates a trend from two days of data, or demand from an offer corpus, is
worse than one that says it cannot yet: the brief asks for honest
"still-offer-corpus" over pretended demand, so both directions are pinned.

No network. Run: uv run --with pytest --with httpx --with pyyaml pytest \
    tools/tests/test_vinted_inventory.py
"""

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
LISTING_DIR = ROOT / "workspace" / "projects" / "vinted-reselling" / "listing"
WATCHER_PATH = ROOT / "workspace" / "projects" / "vinted-reselling" / "watcher" / "vinted_watcher.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ke():
    return _load("keyword_engine", LISTING_DIR / "keyword_engine.py")


@pytest.fixture(scope="module")
def kr():
    return _load("keyword_research", LISTING_DIR / "keyword_research.py")


@pytest.fixture(scope="module")
def inv():
    return _load("inventory", LISTING_DIR / "inventory.py")


@pytest.fixture
def db(inv, tmp_path):
    """A real database, migrated by the watcher, so the schema is the live one."""
    con = inv.connect(tmp_path / "test.db")
    yield con
    con.close()


def stamp(**kw):
    return (datetime.now(timezone.utc) - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_listing(con, item_id, title, *, brand="Levi's", brand_norm="levis",
                garment_class="pants", size="W31 | DE 46", size_class="w31",
                cond="Sehr gut", cond_tier="very_good", price=20.0, total=21.7,
                posted=None, first_seen=None, sold=None, gone=None):
    con.execute(
        """INSERT INTO listings (id, search_tag, title, brand, brand_norm, size,
               size_class, condition, cond_tier, garment_class, is_kid, price,
               total_price, currency, url, posted_at, first_seen, last_seen,
               sold_flag, gone_at)
           VALUES (?,'t',?,?,?,?,?,?,?,?,0,?,?,'EUR',?,?,?,?,?,?)""",
        (item_id, title, brand, brand_norm, size, size_class, cond, cond_tier,
         garment_class, price, total, f"https://www.vinted.de/items/{item_id}-x",
         posted, first_seen or posted, first_seen or posted, 1 if sold else 0, gone))


def mark_bought(con, item_id, alert_id=None):
    con.execute(
        "INSERT INTO alert_feedback (listing_id, alert_id, verdict, received_at, source)"
        " VALUES (?, ?, 'bought', ?, 'cli')", (item_id, alert_id, stamp(hours=1)))


# ------------------------------------------- 2. a tap becomes a priced draft

def test_a_bought_tap_becomes_a_complete_draft_without_retyping(inv, db):
    """The whole point: everything the database already knows must not be
    retyped. Brand, size, condition, class and buy price come from the row."""
    for i in range(30):
        add_listing(db, 1000 + i, f"Levi's 501 Jeans {i}", price=24.0, total=25.9)
    add_listing(db, 9999, "Levi's Jeans 501 Herren", price=8.0, total=9.1)
    mark_bought(db, 9999)
    db.commit()

    d = inv.draft(db, 9999)
    assert d["purchase"]["brand"] == "Levi's"
    assert d["purchase"]["size"] == "W31 | DE 46"
    assert d["purchase"]["buy_total"] == 9.1
    assert d["listing"]["title"], "a draft with no title is not a draft"
    assert d["price"]["ask_price"] is not None


def test_the_model_name_is_lifted_out_of_the_sellers_own_title(inv, db):
    """501 is the most valuable token on the listing and lives only in the free
    text. The structured fields never carry it.

    The corpus needs OTHER cells in it, because a model name is identified by
    lift: a term in every row of a single-cell corpus distinguishes nothing.
    """
    for i in range(60):
        add_listing(db, 2000 + i, f"Levi's 501 Jeans straight {i}")
    for i in range(40):
        add_listing(db, 2500 + i, f"Levi's Jeans bootcut {i}")     # same cell, no 501
    for i in range(200):                                            # background
        add_listing(db, 2900 + i, f"Carhartt Jacke Detroit {i}",
                    brand="Carhartt", brand_norm="carhartt", garment_class="jacket")
    add_listing(db, 8888, "Levi’s Jeans 501 Herren", price=8.0, total=9.1)
    mark_bought(db, 8888)
    db.commit()
    d = inv.draft(db, 8888)
    assert "501" in d["listing"]["title"], d["listing"]["title"]


def test_the_price_is_the_item_price_not_the_buyer_total(inv, db):
    """Every comp in the database is a buyer-paid total, but Vinted asks for the
    item price. Confusing them overprices every listing by the fee."""
    for i in range(30):
        add_listing(db, 3000 + i, f"Levi's 501 {i}", price=25.0, total=26.95)
    add_listing(db, 7777, "Levi's 501", price=8.0, total=9.1)
    mark_bought(db, 7777)
    db.commit()
    d = inv.draft(db, 7777)
    ask = d["price"]["ask_price"]
    assert ask < d["price"]["comp_median_total"], "the ask must be net of the fee"
    assert d["price"]["buyer_pays"] == pytest.approx(round(ask * 1.05 + 0.7, 2), abs=0.02)


def test_the_fee_inversion_round_trips(inv):
    """Recovered from 36,229 real pairs: fee = 0.70 + 5%."""
    assert inv.total_to_price(26.95) == 25.0
    assert inv.price_to_total(25.0) == 26.95
    assert inv.price_to_total(inv.total_to_price(45.0)) == pytest.approx(45.0, abs=0.01)


def test_what_the_database_cannot_know_is_asked_not_filled_in(inv, db):
    """Colour, material and measurements cannot come off a catalog row. A TBD in
    the body gets published; a question gets answered."""
    for i in range(30):
        add_listing(db, 4000 + i, f"Levi's 501 {i}")
    add_listing(db, 6666, "Levi's 501", price=8.0, total=9.1)
    mark_bought(db, 6666)
    db.commit()
    questions = " ".join(inv.draft(db, 6666)["open_questions"]).lower()
    for missing in ("farbe", "material", "masse"):
        assert missing in questions


def test_a_purchase_whose_listing_row_is_gone_still_drafts(inv, db):
    """A tap can outlive its listing row; the live database has exactly such a
    row. Dropping it would hide real inventory."""
    db.execute("INSERT INTO alerts (id, listing_id, alerted_at, search_tag, brand,"
               " brand_norm, garment_class, cond_tier, size_class, comp_median,"
               " total_at_alert) VALUES (5, 5555, ?, 't', 'Patagonia', 'patagonia',"
               " 'jacket', 'very_good', 'm', 68.95, 31.03)", (stamp(hours=2),))
    mark_bought(db, 5555, alert_id=5)
    db.commit()
    d = inv.draft(db, 5555)
    assert d["purchase"]["brand"] == "Patagonia", "the snapshot must fill in"
    assert any("Schnappschuss" in q for q in d["open_questions"])


# --------------------------------------------------- 3. lenient input

def test_german_field_names_are_understood(ke):
    item, notes = ke.read_item({"marke": "Levi's", "groesse": "W31",
                                "farbe": "Blau", "zustand": "Sehr gut"})
    assert item["brand"] == "Levi's" and item["size"] == "W31"
    assert item["color"] == "Blau" and item["condition"] == "Sehr gut"


def test_free_text_is_parsed(ke):
    """The brief's own example line."""
    item, _ = ke.read_item("levis 501 w31 blau sehr gut")
    assert item["brand"].lower() == "levis"
    assert item["size"] == "W31"
    assert item["color"] == "Blau"
    assert item["condition"] == "Sehr gut"
    assert item["model"] == "501"


def test_an_unknown_key_is_reported_and_not_silently_dropped(ke):
    """The shipped failure: a wrong key vanished, the axis came out TBD, and the
    output looked finished."""
    item, notes = ke.read_item({"brnad": "Levi's", "size": "M"})
    assert "brand" not in item
    assert any("brnad" in n for n in notes), notes


def test_broken_json_is_reported_rather_than_crashing(ke):
    item, notes = ke.read_item('{"brand": "Levi\'s", ')
    assert any("JSON" in n for n in notes)


def test_missing_axes_come_back_as_questions_not_tbd(ke):
    out = ke.suggest({"brand": "Levi's", "garment_class": "pants"}, use_corpus=False)
    assert out["open_questions"]
    assert any("Farbe" in q for q in out["open_questions"])


def test_the_class_is_derived_from_the_noun_so_the_axes_are_used(ke):
    item, _ = ke.read_item({"marke": "Carhartt", "typ": "Jacke"})
    assert item["garment_class"] == "jacket"


def test_a_repeated_word_is_dropped_from_the_title(ke):
    """A model mined as "Jeans 501" beside type "Jeans" produced
    "Levi's Jeans 501 Jeans"."""
    assert ke.build_title({"brand": "Levi's", "model": "Jeans 501",
                           "type": "Jeans"}).startswith("Levi's Jeans 501")
    assert ke.build_title({"brand": "Levi's", "model": "Jeans 501",
                           "type": "Jeans"}).count("Jeans") == 1


def test_the_dual_size_notation_is_not_repeated_in_the_title(ke):
    title = ke.build_title({"brand": "Levi's", "size": "W31 | DE 46"})
    assert "Gr. W31" in title and "DE 46" not in title


def test_a_keyword_and_its_own_permutation_are_one_keyword(ke):
    kws, _ = ke.build_keywords({"brand": "Levi's", "type": "Jeans",
                                "garment_class": "pants"},
                               mined=["501 jeans", "jeans 501", "straight"])
    assert not ({"501 jeans", "jeans 501"} <= set(kws)), kws


# ------------------------------------------------------ 4. language leak

def test_a_french_word_is_kept_out_of_a_german_listing(kr):
    """The live leak: the engine offered "bleu" for a German listing."""
    term = kr.Term(text="bleu", n=10, share=0.1, lift=3.0)
    assert kr.language_verdict(term)[0] == "foreign"
    assert kr.language_verdict(kr.Term(text="jean", n=10, share=0.1, lift=3.0))[0] == "foreign"


def test_a_model_name_is_not_foreign_just_because_its_neighbours_are(kr):
    """Nano Puff sits in 90% Dutch titles and 501 in 85% French ones, purely
    because those sellers write more prose. Judging by context alone killed both."""
    from collections import Counter
    for text in ("nano puff", "torrentshell", "501"):
        # ceiling is the lift a cell-exclusive term reaches, so lift at the
        # ceiling is what marks a product name. That is the exemption.
        term = kr.Term(text=text, n=10, share=0.05, lift=70.0, ceiling=72.0,
                       langs=Counter({"nl": 9, "fr": 4}))
        assert kr.language_verdict(term)[0] != "foreign", text


def test_a_german_word_survives_a_foreign_context(kr):
    from collections import Counter
    term = kr.Term(text="jacke", n=50, share=0.2, lift=3.0,
                   langs=Counter({"fr": 40, "de": 10}))
    assert kr.language_verdict(term)[0] == "german"


def test_an_unlisted_foreign_word_is_caught_by_its_evidence(kr):
    """Tier 2: no list names it, but not one German seller uses it."""
    from collections import Counter
    term = kr.Term(text="doudoune", n=8, share=0.03, lift=9.0,
                   langs=Counter({"fr": 8}))
    assert kr.language_verdict(term)[0] == "foreign"


def test_one_german_seller_is_enough_to_keep_a_word(kr):
    from collections import Counter
    term = kr.Term(text="softshell", n=9, share=0.03, lift=9.0,
                   langs=Counter({"fr": 8, "de": 1}))
    assert kr.language_verdict(term)[0] != "foreign"


def test_the_language_of_a_brand_only_title_is_nobodys(kr):
    """45% of titles are a brand and a model. Guessing a language for those puts
    every brand term into whichever language won a tiebreak."""
    assert kr.title_language("Carhartt Detroit Jacket") is None
    assert kr.title_language("Levi's 501 W31") is None
    assert kr.title_language("Veste Carhartt bleu homme") == "fr"
    assert kr.title_language("Carhartt Jacke schwarz Herren") == "de"


def test_a_french_term_does_not_reach_the_keywords_of_a_real_cell(kr, db):
    """Runs THROUGH mine_cell, not through the helper. The engine offering "bleu"
    was the shipped defect, and a test that only calls language_verdict cannot
    tell a wired filter from an unwired one."""
    # "bleu" has to stand on its own, not always beside the same neighbour, or
    # the existing subsumption rule folds it into "jean bleu" and the language
    # filter is never the thing that removed it.
    for i in range(120):
        tail = ("jean homme", "pantalon droit", "taille haute", "delave")[i % 4]
        add_listing(db, 80_000 + i, f"Levi's 501 bleu {tail} {i}")
    for i in range(120):
        tail = ("Jeans Herren", "Hose gerade", "hoher Bund", "gewaschen")[i % 4]
        add_listing(db, 81_000 + i, f"Levi's 501 blau {tail} {i}")
    for i in range(200):
        add_listing(db, 82_000 + i, f"Carhartt Jacke {i}", brand="Carhartt",
                    brand_norm="carhartt", garment_class="jacket")
    db.commit()
    usable = {t.text for t in kr.mine_cell(db, "levis", "pants")[0] if t.kind == "term"}
    # Substring, not equality: the mined terms are phrases ("501 bleu",
    # "bleu jean"), and the bare token is folded into them by the existing
    # subsumption rule. An equality check passes whether or not the filter runs,
    # which is precisely the kind of assertion that cannot tell a wired fix from
    # an unwired one.
    for french in ("bleu", "jean", "pantalon", "delave"):
        assert not any(french in t.split() for t in usable), (french, sorted(usable))
    assert any("501" in t for t in usable), sorted(usable)
    assert any("blau" in t.split() for t in usable), "German colour must survive"

    terms = kr.keywords_for(db, "levis", "pants", title_hint="Levi's 501 bleu jean")
    assert not any("bleu" in t.split() or "jean" in t.split() for t in terms), terms


def test_a_size_notation_never_becomes_a_keyword(kr):
    assert kr.classify("jeans w31", "levis")[0] == "size"


def test_a_model_number_is_not_mistaken_for_a_size(kr):
    """501 and 46 match the same pattern. The size column is the authority."""
    sizes = {"31", "46", "32", "34"}
    assert kr.classify("501", "levis", 7.6, sizes)[0] == "term"
    assert kr.classify("32", "carhartt", 7.4, sizes)[0] == "size"


# ------------------------------------------------------------- 5. trend

def test_a_trend_is_refused_while_the_window_is_too_short(kr, db):
    """Two days of data cannot carry a week-over-week ratio, and saying so is the
    deliverable. The corpus today has 3 observation days."""
    for i in range(80):
        add_listing(db, 100 + i, f"Levi's 501 jeans {i}",
                    posted=stamp(days=1), first_seen=stamp(days=1))
    db.commit()
    out = kr.trend(db, "levis", "pants")
    assert out["verdict"] == "insufficient"
    assert "Sammeltagen" in out["why"]


def test_a_trend_is_computed_once_the_windows_are_real(kr, db):
    """The success path: "carpenter" triples between the windows."""
    for day in range(1, 15):
        base = 10_000 + day * 100
        # Above the 50-row floor that separates an observation day from an
        # outage; the 2026-09-07 token expiry is what that floor exists for.
        for i in range(60):
            # carpenter is in a thirteenth of the older window, a quarter of the newer
            share = 13 if day > 7 else 4
            word = "carpenter" if i % share == 0 else "straight"
            add_listing(db, base + i, f"Levi's 501 jeans {word} {i}",
                        posted=stamp(days=day), first_seen=stamp(days=day))
    db.commit()
    out = kr.trend(db, "levis", "pants")
    assert out["verdict"] == "ok", out.get("why")
    rising = {r["term"] for r in out["rising"]}
    assert "carpenter" in rising, out["rising"]


def test_a_backlog_dumped_into_today_is_not_counted_as_new(kr, db):
    """The seed crawl put 19,948 rows under one date that were not posted then.
    Counting those would read as a supply explosion."""
    for i in range(80):
        add_listing(db, 200 + i, f"Levi's 501 backlog {i}",
                    posted=stamp(days=60), first_seen=stamp(days=1))
    db.commit()
    assert kr.observed_new(db, "levis", "pants", stamp(days=7), stamp(days=0)) == []


# ------------------------------------------- 6. my own listings ledger

def test_a_draft_can_be_recorded_and_closed_out_as_sold(inv, db):
    for i in range(30):
        add_listing(db, 400 + i, f"Levi's 501 {i}", price=25.0, total=26.95)
    add_listing(db, 4444, "Levi's 501", price=8.0, total=9.1)
    mark_bought(db, 4444)
    db.commit()

    d = inv.draft(db, 4444)
    my_id = inv.record(db, d, ask_price=22.0, color="Blau", listed_at=stamp(days=2),
                       status="listed")
    rows = inv.mine(db)
    assert len(rows) == 1
    assert rows[0]["ask_price"] == 22.0 and rows[0]["buy_price"] == 9.1
    assert json.loads(rows[0]["keywords"]), "the keywords used must be recorded"

    assert inv.mark_sold(db, my_id, 22.0) is True
    row = inv.mine(db)[0]
    assert row["status"] == "sold" and row["sold_price"] == 22.0


def test_a_recorded_listing_shows_up_against_its_purchase(inv, db):
    """--bought must stop offering a draft for something already listed."""
    for i in range(30):
        add_listing(db, 500 + i, f"Levi's 501 {i}")
    add_listing(db, 3333, "Levi's 501", price=8.0, total=9.1)
    mark_bought(db, 3333)
    db.commit()
    assert inv.bought(db)[0]["my_id"] is None
    inv.record(db, inv.draft(db, 3333), status="listed")
    assert inv.bought(db)[0]["my_status"] == "listed"


def test_marking_a_listing_that_does_not_exist_reports_failure(inv, db):
    assert inv.mark_sold(db, 999, 10.0) is False


# --------------------------------------------- 7b. demand from real sales

def test_demand_refuses_to_invent_a_signal_from_too_few_sales(kr, db):
    """The brief's explicit requirement: say "still offer corpus" rather than
    pretend demand. Below 30 sales a doubling is 1.4 sigma, which is noise."""
    for i in range(200):
        add_listing(db, 600 + i, f"Levi's 501 jeans {i}")
    for i in range(5):
        add_listing(db, 900 + i, f"Levi's 501 jeans carpenter {i}",
                    posted=stamp(days=3), sold=True, gone=stamp(days=1))
    db.commit()
    out = kr.demand(db, "levis", "pants")
    assert out["basis"] == "angebots-korpus"
    assert out["sold_n"] == 5 and out["needed_for_provisional"] == 25
    assert out["terms"] == []


def test_demand_ranks_by_real_sales_once_there_are_enough(kr, db):
    """Success path: 'carpenter' is rare in the corpus and common among sales."""
    for i in range(400):
        add_listing(db, 20_000 + i, f"Levi's 501 jeans straight {i}")
    for i in range(60):
        add_listing(db, 30_000 + i, f"Levi's 501 jeans carpenter {i}",
                    posted=stamp(days=4), sold=True, gone=stamp(days=1))
    db.commit()
    out = kr.demand(db, "levis", "pants")
    assert out["basis"] == "vorlaeufig"
    assert out["sold_n"] == 60
    top = [t["term"] for t in out["terms"][:3]]
    assert "carpenter" in top, out["terms"][:5]


def test_a_deleted_listing_is_never_counted_as_a_sale(kr, db):
    """404 is deletion. Counting it as demand is the 2026-09-07 fabrication."""
    for i in range(200):
        add_listing(db, 40_000 + i, f"Levi's 501 jeans {i}")
    for i in range(50):
        add_listing(db, 50_000 + i, f"Levi's 501 jeans deleted {i}",
                    posted=stamp(days=4), sold=False, gone=stamp(days=1))
    db.commit()
    assert kr.demand(db, "levis", "pants")["sold_n"] == 0


def test_the_speed_split_waits_for_enough_timed_sales(kr, db):
    """It halves an already small set, so it needs the full reliable bar."""
    for i in range(300):
        add_listing(db, 60_000 + i, f"Levi's 501 jeans {i}")
    for i in range(40):
        add_listing(db, 70_000 + i, f"Levi's 501 jeans fast {i}",
                    posted=stamp(days=4), sold=True, gone=stamp(days=1))
    db.commit()
    out = kr.demand(db, "levis", "pants")
    assert out["fast_terms"] == []
    assert "Tempo" in out["speed_note"]
