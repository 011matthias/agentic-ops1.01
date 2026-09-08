"""Regression suite for listing time-series capture and the sold/withdrawn split.

Two failures this pins, both of which were silently destroying the only data
this project cannot rebuild:

1. upsert() overwrote price, favourites and views on every re-sight. A seller
   who cut the price three times looked identical to one who never moved it.
   Nothing anywhere kept the difference, and it cannot be backfilled.

2. The sold marker was `is_sold":true`, which appears on NO Vinted item page.
   The sold branch was unreachable, so every sale the recheck visited was
   recorded as "alive" with its last_seen pushed forward. Probed 2026-09-09
   against the owner's own bought item: a sold listing answers 200 and carries
   a `buyer_item_status` plugin with theme SUCCESS, while a live one carries
   `item_status` with is_closed false. 404 is deletion, which is not a sale.

The fixtures under tools/fixtures/vinted-item-page/ are real bytes cut out of
real pages. A test over hand-written HTML would only pin my idea of the page.

No network. Run: uv run --with pytest --with httpx --with pyyaml pytest \
    tools/tests/test_vinted_outcomes.py
"""

import importlib.util
import sys
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
WATCHER_PATH = ROOT / "workspace" / "projects" / "vinted-reselling" / "watcher" / "vinted_watcher.py"
FIXTURES = ROOT / "tools" / "fixtures" / "vinted-item-page"


@pytest.fixture(scope="module")
def vw():
    spec = importlib.util.spec_from_file_location("vinted_watcher_outcomes", WATCHER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def paths(vw, tmp_path, monkeypatch):
    monkeypatch.setattr(vw, "DATA_DIR", tmp_path)
    monkeypatch.setattr(vw, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(vw, "COOKIE_PATH", tmp_path / "cookies.json")
    monkeypatch.setattr(vw, "LOCK_PATH", tmp_path / "cycle.lock")
    return tmp_path


@pytest.fixture
def con(vw, paths):
    c = vw.db_connect()
    yield c
    c.close()


def listing(**over):
    rec = {"id": 1, "search_tag": "t", "title": "Levi's 501", "brand": "Levi's",
           "brand_norm": "levis", "size": "W31", "size_class": "w31",
           "condition": "Sehr gut", "cond_tier": "very_good", "garment_class": "pants",
           "is_kid": 0, "country": "DE", "price": 20.0, "total_price": 22.0,
           "currency": "EUR", "url": "https://www.vinted.de/items/1-x",
           "photo_url": None, "posted_at": None, "seller_id": 9, "seller_login": "s",
           "favourites": 3, "views": 0, "promoted": 0, "seed": 0}
    rec.update(over)
    return rec


def events(con, listing_id=1):
    return con.execute(
        "SELECT field, old_value, new_value FROM listing_events"
        " WHERE listing_id=? ORDER BY id", (listing_id,)).fetchall()


# ------------------------------------------------- 1. the time series survives

def test_a_price_cut_is_recorded_instead_of_overwritten(vw, con):
    """The whole point: three cuts must be three rows, not one final number."""
    vw.upsert(con, listing())
    for price, total in ((18.0, 20.0), (15.0, 17.0), (12.0, 14.0)):
        vw.upsert(con, listing(price=price, total_price=total))
    cuts = [e for e in events(con) if e[0] == "price"]
    assert [(e[1], e[2]) for e in cuts] == [(20.0, 18.0), (18.0, 15.0), (15.0, 12.0)]
    assert con.execute("SELECT price FROM listings WHERE id=1").fetchone()[0] == 12.0


def test_favourite_growth_is_recorded(vw, con):
    vw.upsert(con, listing(favourites=3))
    vw.upsert(con, listing(favourites=7))
    assert ("favourites", 3.0, 7.0) in events(con)


def test_a_resight_that_changed_nothing_writes_nothing(vw, con):
    """~13.8k re-sights a day. A row per sighting would grow the table by that
    much daily while carrying no information."""
    vw.upsert(con, listing())
    for _ in range(5):
        vw.upsert(con, listing())
    assert events(con) == []


def test_float_noise_is_not_mistaken_for_a_price_change(vw, con):
    vw.upsert(con, listing(price=26.95))
    vw.upsert(con, listing(price=26.950000000000003))
    assert events(con) == []


def test_the_very_first_sighting_records_no_change(vw, con):
    """An insert has nothing to compare against; 'unknown became 3' teaches nothing."""
    vw.upsert(con, listing())
    assert events(con) == []


def test_the_change_is_captured_before_the_overwrite(vw, con):
    """Ordering is the bug: read the old value after the UPDATE and it is gone."""
    vw.upsert(con, listing(price=20.0))
    vw.upsert(con, listing(price=9.0))
    assert events(con)[0] == ("price", 20.0, 9.0)


# ------------------------------------- 7a. sold is told apart from withdrawn

def snippet(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_a_real_sold_page_reads_as_sold(vw):
    verdict, evidence = vw.item_page_verdict(200, snippet("item_sold.snippet.html"))
    assert verdict == "sold"
    assert "SUCCESS" in evidence


def test_a_real_live_page_reads_as_alive(vw):
    verdict, evidence = vw.item_page_verdict(200, snippet("item_alive.snippet.html"))
    assert verdict == "alive"
    assert evidence == "item_status:open"


def test_the_word_verkauft_on_a_live_page_does_not_mark_it_sold(vw):
    """The i18n bundle ships 'Dieser Artikel wurde schon verkauft' to EVERY page.
    A text search for the word marks 100% of live listings sold."""
    body = snippet("i18n_verkauft_on_a_live_page.snippet.html")
    assert "verkauft" in body.lower(), "fixture no longer carries the trap"
    assert vw.item_page_verdict(200, body)[0] != "sold"


def test_a_404_is_deletion_and_never_a_sale(vw):
    """404 is what the old code read as the only kind of gone. It is not a sale,
    and recording it as one would be the 2026-09-07 fabrication again."""
    assert vw.item_page_verdict(404, "") == ("gone", "404")
    assert vw.item_page_verdict(410, "")[0] == "gone"


def test_an_unreadable_page_is_unknown_rather_than_guessed(vw):
    assert vw.item_page_verdict(200, "<html>wall</html>")[0] == "unknown"
    assert vw.item_page_verdict(403, "")[0] == "unknown"
    assert vw.item_page_verdict(500, "")[0] == "unknown"


def test_a_closed_listing_that_did_not_sell_is_not_counted_as_demand(vw):
    body = (r'\"name\":\"item_status\",\"section\":\"sidebar\",\"data\":'
            r'{\"item_id\":1,\"is_closed\":true,\"item_closing_action\":\"not_sold\"}')
    assert vw.item_page_verdict(200, body)[0] == "closed"


def test_a_closed_listing_whose_action_says_sold_counts_as_sold(vw):
    body = (r'\"name\":\"item_status\",\"section\":\"sidebar\",\"data\":'
            r'{\"item_id\":1,\"is_closed\":true,\"item_closing_action\":\"sold\"}')
    assert vw.item_page_verdict(200, body)[0] == "sold"


def test_an_unknown_buyer_status_theme_is_closed_not_sold(vw):
    """Only the SUCCESS theme is the sold panel. A theme we have never seen is a
    closure we do not understand, and guessing it into the sales data is exactly
    the failure this whole module exists to prevent."""
    body = (r'\"name\":\"buyer_item_status\",\"data\":{\"item_id\":1,'
            r'\"title\":\"Nicht mehr verf\",\"theme\":\"EXPIRED\"}')
    assert vw.item_page_verdict(200, body)[0] == "closed"


# ------------------------------------------- 7a. the verdict reaches the database

def _recheck(vw, con, monkeypatch, pages):
    """Drive the real recheck_gone against a mock transport. `pages` maps url -> (code, body)."""
    def handler(request):
        code, body = pages[str(request.url)]
        return httpx.Response(code, text=body, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    monkeypatch.setattr(vw, "token_is_fresh", lambda *a, **k: True)
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)
    vw.recheck_gone(client, con, session_proven=True)
    client.close()


def test_a_sale_is_written_to_the_database_not_read_as_still_alive(vw, con, monkeypatch):
    """The live bug: a sold page answers 200, so the old code bumped last_seen
    and the sale was erased. This is the assertion that runs THROUGH recheck_gone."""
    vw.upsert(con, listing(id=1, url="https://x/items/1",
                           posted_at="2026-01-01T00:00:00Z"))
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z' WHERE id=1")
    con.commit()
    _recheck(vw, con, monkeypatch,
             {"https://x/items/1": (200, snippet("item_sold.snippet.html"))})
    row = con.execute("SELECT gone_at, sold_flag, gone_source FROM listings WHERE id=1").fetchone()
    assert row[0] is not None, "a sold listing must be closed out, not bumped"
    assert row[1] == 1, "the sale must be flagged as a sale"
    assert "SUCCESS" in row[2]


def test_a_deleted_listing_is_closed_out_but_not_flagged_sold(vw, con, monkeypatch):
    """A realistic batch: one deletion among live listings. A batch that is ALL
    404 trips the systemic-sweep ceiling instead, which is the next test."""
    pages = {}
    for i in range(2, 7):
        vw.upsert(con, listing(id=i, url=f"https://x/items/{i}"))
        pages[f"https://x/items/{i}"] = (200, snippet("item_alive.snippet.html"))
    pages["https://x/items/2"] = (404, "")
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z'")
    con.commit()
    _recheck(vw, con, monkeypatch, pages)
    row = con.execute("SELECT gone_at, sold_flag, gone_source FROM listings WHERE id=2").fetchone()
    assert row[0] is not None and row[1] == 0 and row[2] == "404"


def test_a_whole_batch_reading_404_is_still_discarded_as_systemic(vw, con,
                                                                  monkeypatch, capsys):
    """The 2026-09-07 guard, kept: 375 fabricated 'sales' arrived as 15 batches of
    25 that were all gone. A market does not delete a whole sample at once."""
    pages = {}
    for i in range(40, 50):
        vw.upsert(con, listing(id=i, url=f"https://x/items/{i}"))
        pages[f"https://x/items/{i}"] = (404, "")
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z'")
    con.commit()
    _recheck(vw, con, monkeypatch, pages)
    assert con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL").fetchone()[0] == 0
    assert "systemic" in capsys.readouterr().out


def test_a_live_listing_is_left_open(vw, con, monkeypatch):
    vw.upsert(con, listing(id=3, url="https://x/items/3"))
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z' WHERE id=3")
    con.commit()
    _recheck(vw, con, monkeypatch,
             {"https://x/items/3": (200, snippet("item_alive.snippet.html"))})
    row = con.execute("SELECT gone_at, last_seen FROM listings WHERE id=3").fetchone()
    assert row[0] is None
    assert row[1] > "2026-01-01T00:00:00Z", "a live listing gets its clock bumped"


def test_a_batch_of_unreadable_pages_is_discarded_rather_than_recorded(vw, con,
                                                                       monkeypatch, capsys):
    """A 200 carrying no status plugin is not an item page; it is what a soft wall
    looks like now that hard redirects are caught. Recording it would repeat the
    2026-09-07 fabrication in a new costume."""
    pages = {}
    for i in range(10, 20):
        vw.upsert(con, listing(id=i, url=f"https://x/items/{i}"))
        pages[f"https://x/items/{i}"] = (200, "<html>nothing here</html>")
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z'")
    con.commit()
    _recheck(vw, con, monkeypatch, pages)
    assert con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL").fetchone()[0] == 0
    assert "no status plugin" in capsys.readouterr().out


def test_the_alerted_cohort_is_bought_first_with_the_fixed_budget(vw, con):
    """25 pages an hour against ~13.8k new listings a day is a 4% sample whatever
    the policy. The alerted listings are the only cohort that can tell us whether
    the deal gate is right, and there are ~50 a day, so they always fit."""
    for i in range(1, 40):
        vw.upsert(con, listing(id=i, url=f"https://x/items/{i}"))
    con.execute("UPDATE listings SET first_seen='2026-01-01T00:00:00Z',"
                " last_seen='2026-01-01T00:00:00Z'")
    # the newest rows are the alerted ones, so oldest-first would never reach them
    for i in (37, 38, 39):
        con.execute("INSERT INTO alerts (listing_id, alerted_at, search_tag)"
                    " VALUES (?, '2026-01-01T00:00:00Z', 't')", (i,))
    con.commit()
    picked = [i for i, _ in vw.recheck_queue(con, 25)]
    assert {37, 38, 39} <= set(picked), "alerted listings must not wait behind the backlog"
    assert len(picked) == 25, "the budget is spent, not exceeded"
