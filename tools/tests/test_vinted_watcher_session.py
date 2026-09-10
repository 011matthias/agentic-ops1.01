"""Regression suite for the Vinted watcher's session handling.

Pins the 2026-09-07 outage: the anonymous access token is a 24h JWT, and
Vinted reissues nothing when a stale one is presented, so the old
refresh-then-retry path could never recover. Every cycle for 46 hours
retried with the same dead token, backed off, and reported success.

The mock transport below reproduces exactly that server behavior: the
homepage mints a token ONLY when no token cookie is sent. A watcher that
does not clear its jar before refreshing cannot pass these tests.

No network. Run: uv run --with pytest --with httpx --with pyyaml pytest \
    tools/tests/test_vinted_watcher_session.py
"""

import base64
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("yaml")

WATCHER_PATH = (
    Path(__file__).resolve().parents[2]
    / "workspace" / "projects" / "vinted-reselling" / "watcher" / "vinted_watcher.py"
)


@pytest.fixture(scope="module")
def vw():
    spec = importlib.util.spec_from_file_location("vinted_watcher_under_test", WATCHER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_jwt(hours_from_now: float) -> str:
    exp = int((datetime.now(timezone.utc) + timedelta(hours=hours_from_now)).timestamp())
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@pytest.fixture
def paths(vw, tmp_path, monkeypatch):
    """Point the module's on-disk state at a temp dir."""
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


def vinted_server(state=None, api_status_when_valid=200):
    """Mock Vinted: the homepage mints a token only for a cookie-less request.

    This is the real 2026-09-07 behavior, and it is the entire reason the
    original recovery path failed.
    """
    state = state if state is not None else {}
    state.setdefault("minted", 0)
    state.setdefault("api_calls", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        cookie_header = request.headers.get("cookie", "")
        has_token = "access_token_web=" in cookie_header
        if request.url.path == "/":
            if has_token:
                return httpx.Response(200, text="home")          # reissues nothing
            state["minted"] += 1
            return httpx.Response(200, text="home", headers={
                "set-cookie": f"access_token_web={make_jwt(24)}; Domain=.vinted.de; Path=/",
            })
        state["api_calls"] += 1
        if not has_token:
            return httpx.Response(401, json={"error": "unauthorized"})
        token = ""
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("access_token_web="):
                token = part.split("=", 1)[1]
        exp = _exp_of(token)
        if exp is None or exp <= datetime.now(timezone.utc):
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(api_status_when_valid, json={"items": [{"id": 1}]})

    return httpx.MockTransport(handler), state


def _exp_of(token):
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        return datetime.fromtimestamp(json.loads(base64.urlsafe_b64decode(p))["exp"], timezone.utc)
    except Exception:
        return None


def client_with(vw, transport, token=None):
    c = httpx.Client(transport=transport, base_url=vw.BASE, follow_redirects=True)
    if token:
        c.cookies.set(vw.TOKEN_COOKIE, token, domain=".vinted.de")
    return c


# --------------------------------------------------------------- the core fix

def test_api_get_recovers_from_expired_token(vw, con, paths):
    """THE regression: a cycle carrying an expired token must still collect.

    Runs through api_get - the caller the fix changed - not just the helper.
    Without the jar clear in refresh_session, the server (correctly modelled)
    reissues nothing and this returns None.
    """
    transport, state = vinted_server()
    c = client_with(vw, transport, token=make_jwt(-1))       # expired an hour ago

    data = vw.api_get(c, con, vw.BASE + "/api/v2/catalog/items", {"search_text": "x"})

    assert data is not None, "expired session was not healed; the outage would recur"
    assert data["items"] == [{"id": 1}]
    assert state["minted"] == 1, "no fresh token was minted"
    assert vw.meta_get(con, "backoff_until") is None, "should not back off on a healed 401"


def test_refresh_session_clears_jar_before_fetching(vw, paths):
    transport, state = vinted_server()
    c = client_with(vw, transport, token=make_jwt(-1))

    assert vw.refresh_session(c) is True
    assert state["minted"] == 1
    assert vw.token_is_fresh(c, margin_min=60), "jar still holds the stale token"


def test_ensure_session_renews_before_expiry_not_after(vw, paths):
    """Proactive renewal: a token inside the safety margin is replaced early."""
    transport, state = vinted_server()
    c = client_with(vw, transport, token=make_jwt(0.25))     # 15 min left, margin is 45

    assert vw.ensure_session(c) is True
    assert state["minted"] == 1, "token inside the margin was not renewed proactively"

    transport2, state2 = vinted_server()
    c2 = client_with(vw, transport2, token=make_jwt(12))     # plenty of life left
    assert vw.ensure_session(c2) is True
    assert state2["minted"] == 0, "renewed a perfectly good token"


# ------------------------------------------------------------ backoff semantics

def test_403_backs_off_hard_without_burning_a_refresh(vw, con, paths):
    def handler(request):
        if request.url.path == "/":
            pytest.fail("must not try to refresh into a bot wall")
        return httpx.Response(403, text="blocked")

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url=vw.BASE)
    with pytest.raises(vw.SessionWall):
        vw.api_get(c, con, vw.BASE + "/api/v2/catalog/items", {})

    until = vw.parse_ts(vw.meta_get(con, "backoff_until"))
    assert until is not None
    minutes = (until - datetime.now(timezone.utc)).total_seconds() / 60
    assert 50 < minutes <= vw.WALL_BACKOFF_MIN + 1, "403 must back off hard"


def test_persistent_401_backs_off_briefly_not_for_an_hour(vw, con, paths):
    """A 401 that survives a clean refresh is still self-healing; 10 min, not 60."""
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, text="home", headers={
                "set-cookie": f"access_token_web={make_jwt(24)}; Domain=.vinted.de; Path=/"})
        return httpx.Response(401, json={"error": "nope"})

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url=vw.BASE)
    with pytest.raises(vw.SessionWall):
        vw.api_get(c, con, vw.BASE + "/api/v2/catalog/items", {})

    until = vw.parse_ts(vw.meta_get(con, "backoff_until"))
    minutes = (until - datetime.now(timezone.utc)).total_seconds() / 60
    assert 5 < minutes <= vw.AUTH_BACKOFF_MIN + 1, "auth backoff must stay short"


def test_a_wall_stops_the_whole_cycle_instead_of_hammering_it(vw, con, paths, monkeypatch):
    """One 403 must end the cycle, not let eight more searches retry into it."""
    calls = {"api": 0}

    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, text="home", headers={
                "set-cookie": f"access_token_web={make_jwt(24)}; Domain=.vinted.de; Path=/"})
        calls["api"] += 1
        return httpx.Response(403, text="blocked")

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler), base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 8, "comp_window_days": 45, "min_price": 8,
                     "poll_per_page": 48, "seed_pages": 1, "seed_per_page": 96},
        "searches": [{"tag": f"s{i}", "query": "q"} for i in range(9)]})
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "time", type("T", (), {"sleep": staticmethod(lambda *_: None),
                                                   "time": staticmethod(lambda: 0)})())
    for i in range(9):
        vw.meta_set(con, f"seeded:s{i}", vw.now_iso())
    con.commit()
    con.close()

    assert vw.run_cycle() == 1
    assert calls["api"] == 1, f"kept knocking after a 403: {calls['api']} requests"


def test_non_json_body_is_treated_as_a_wall_not_a_crash(vw, con, paths):
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, text="home", headers={
                "set-cookie": f"access_token_web={make_jwt(24)}; Domain=.vinted.de; Path=/"})
        return httpx.Response(200, text="<html>are you a robot</html>",
                              headers={"content-type": "text/html"})

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url=vw.BASE)
    with pytest.raises(vw.SessionWall):
        vw.api_get(c, con, vw.BASE + "/api/v2/catalog/items", {})
    assert vw.meta_get(con, "backoff_until") is not None


def test_repeated_walls_escalate_but_stay_capped(vw, con, paths):
    for _ in range(8):
        vw.set_backoff(con, vw.WALL_BACKOFF_MIN, "wall", escalate=True)
    until = vw.parse_ts(vw.meta_get(con, "backoff_until"))
    minutes = (until - datetime.now(timezone.utc)).total_seconds() / 60
    assert minutes <= vw.MAX_BACKOFF_MIN + 1, "backoff must not escalate without bound"


def test_cookie_read_survives_duplicate_names_across_domains(vw, paths):
    """httpx's Cookies.get() raises CookieConflict here; the watcher must not."""
    c = httpx.Client(base_url=vw.BASE)
    c.cookies.set(vw.TOKEN_COOKIE, make_jwt(24), domain=".vinted.de")
    c.cookies.set(vw.TOKEN_COOKIE, make_jwt(24), domain=".www.vinted.de")
    assert vw.cookie_value(c, vw.TOKEN_COOKIE) is not None
    assert vw.token_is_fresh(c, margin_min=60) is True


def test_malformed_backoff_stamp_cannot_wedge_a_cycle(vw):
    assert vw.parse_ts("not-a-timestamp") is None
    assert vw.parse_ts(None) is None
    assert vw.parse_ts("") is None


# ------------------------------------------------- outcome-data contamination

def _seed_listing(con, item_id, url, last_seen):
    con.execute(
        "INSERT INTO listings (id, search_tag, title, url, first_seen, last_seen) "
        "VALUES (?, 't', 'x', ?, ?, ?)", (item_id, url, last_seen, last_seen))
    con.commit()


def test_login_wall_redirect_is_never_recorded_as_a_sale(vw, con, paths):
    """This is the exact shape that fabricated all 375 outcome rows."""
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(6):
        _seed_listing(con, i, f"{vw.BASE}/items/{i}-thing", old)

    def handler(request):
        return httpx.Response(302, headers={"location": f"{vw.BASE}/member/login"})

    c = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    vw.recheck_gone(c, con, session_proven=True)

    marked = con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL").fetchone()[0]
    assert marked == 0, "a wall-wide redirect was recorded as six sales"


def test_a_mass_gone_batch_is_discarded_even_with_honest_404s(vw, con, paths):
    """Belt to the redirect guard's braces: 25-of-25 404 is still systemic."""
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(10):
        _seed_listing(con, i, f"{vw.BASE}/items/{i}-thing", old)

    c = client_with(vw, httpx.MockTransport(lambda r: httpx.Response(404, text="gone")),
                    token=make_jwt(12))
    vw.recheck_gone(c, con, session_proven=True)

    marked = con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL").fetchone()[0]
    assert marked == 0, "an implausible 100% sweep was written to the outcome data"


def test_a_relisted_row_clears_its_gone_verdict(vw, con, paths):
    """Seeing a listing alive again disproves an earlier gone verdict."""
    now = vw.now_iso()
    con.execute("INSERT INTO listings (id, search_tag, title, gone_at, gone_source, sold_flag,"
                " first_seen, last_seen) VALUES (7,'t','x',?, '404', 1, ?, ?)", (now, now, now))
    con.commit()
    rec = {"id": 7, "search_tag": "t", "title": "x", "brand": "b", "size": "L",
           "condition": "Sehr gut", "cond_tier": "very_good", "garment_class": "jacket",
           "is_kid": 0, "price": 10.0, "total_price": 10.0, "currency": "EUR", "url": "u",
           "photo_url": None, "seller_id": 1, "seller_login": "s", "favourites": 0,
           "views": 0, "promoted": 0, "seed": 0}
    assert vw.upsert(con, rec) is False
    con.commit()
    row = con.execute("SELECT gone_at, sold_flag FROM listings WHERE id=7").fetchone()
    assert row == (None, 0), "outcome data cannot self-correct when a listing returns"


def test_plain_german_page_chrome_is_not_read_as_sold(vw, con, paths):
    """The word 'Verkauft' appears in ordinary page furniture; only a flag counts."""
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_listing(con, 1, f"{vw.BASE}/items/1-thing", old)

    def handler(request):
        return httpx.Response(200, text="<html><a>Verkaufte Artikel ansehen</a></html>")

    c = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    vw.recheck_gone(c, con, session_proven=True)
    assert con.execute("SELECT sold_flag FROM listings WHERE id=1").fetchone()[0] == 0


def test_recheck_records_a_plausible_mixed_batch(vw, con, paths):
    """The guard must not suppress real, partial turnover.

    The live-page body is real bytes from a real Vinted page (2026-09-09). It
    used to be the string "<html>still listed</html>", which stopped being a
    valid stand-in when the recheck learned to read the page's status plugin:
    a 200 carrying no plugin at all is now what a soft wall looks like, so an
    invented body reads as unreadable rather than as alive.
    """
    alive_body = (Path(__file__).resolve().parents[1] / "fixtures" / "vinted-item-page"
                  / "item_alive.snippet.html").read_text(encoding="utf-8")
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(10):
        _seed_listing(con, i, f"{vw.BASE}/items/{i}-thing", old)

    def handler(request):
        idx = int(str(request.url).rsplit("/", 1)[1].split("-")[0])
        if idx < 3:
            return httpx.Response(404, text="gone")
        return httpx.Response(200, text=alive_body)

    c = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    vw.recheck_gone(c, con, session_proven=True)

    marked = con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL").fetchone()[0]
    assert marked == 3, "genuine 30% turnover should be recorded"


@pytest.mark.parametrize("token_hours,proven", [(-1, True), (12, False)])
def test_recheck_refuses_to_judge_without_a_proven_session(vw, con, paths, token_hours, proven):
    """Needs BOTH a live token and a real API success in this same cycle."""
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_listing(con, 1, f"{vw.BASE}/items/1-thing", old)

    def handler(request):
        pytest.fail("must not visit item pages without a proven session")

    c = client_with(vw, httpx.MockTransport(handler), token=make_jwt(token_hours))
    vw.recheck_gone(c, con, session_proven=proven)

    assert con.execute("SELECT gone_at FROM listings WHERE id=1").fetchone()[0] is None


# ------------------------------------------------------------------- liveness

def test_stall_is_reported_once_then_rearms_on_recovery(vw, con, paths, monkeypatch):
    sent = []
    monkeypatch.setattr(vw, "notify",
                        lambda env, title, message, click=None, priority=4, con=None:
                        sent.append(title) or True)

    stale = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vw.meta_set(con, "last_success", stale)
    con.commit()

    vw.check_liveness(con, {})
    vw.check_liveness(con, {})
    assert len(sent) == 1, "a stall must alert once, not every five minutes"

    vw.meta_set(con, "last_success", vw.now_iso())
    con.commit()
    vw.check_liveness(con, {})
    assert vw.meta_get(con, "stale_alerted") in (None, ""), "alert did not re-arm after recovery"

    vw.meta_set(con, "last_success", stale)
    con.commit()
    vw.check_liveness(con, {})
    assert len(sent) == 2, "a second, later outage must alert again"


def test_healthy_watcher_stays_quiet(vw, con, paths, monkeypatch):
    monkeypatch.setattr(vw, "notify",
                        lambda *a, **k: pytest.fail("alerted while collecting normally"))
    vw.meta_set(con, "last_success", vw.now_iso())
    con.commit()
    vw.check_liveness(con, {})


# ------------------------------------------------------ kids-clothing exclusion

# Verbatim size strings from the live database on 2026-09-08. Every one of
# these reached a phone alert because the v1 marker list had year-words but
# no month-words.
LEAKED_KID_SIZES = [
    ("Patagonia Sweatjacke", "24–36 Monate / 92"),
    ("Veste Patagonia excellent etat", "12-18 Monate / 80"),
    ("Pullover mit Kragen Polo Ralph Lauren 2T 86", "18–24 Monate / 86"),
    ("Stone Island / Pantalon de jogging", "24–36 Monate / 92"),
    ("Giacca antivento Patagonia bimbo", "24–36 Monate / 92"),
]

# Adult sizes that a numeric-ladder heuristic would wrongly reject.
ADULT_SIZES = [
    ("Carhartt Skill Pant", "W34 | DE 50"),
    ("Levis 501", "W32 | DE 48"),
    ("The North Face Fleece", "M / 38 / 10"),
    ("Stone Island Polo", "XL"),
    ("Patagonia Jacke", "38"),
]


@pytest.mark.parametrize("title,size", LEAKED_KID_SIZES)
def test_kid_sizes_that_actually_leaked_are_caught(vw, title, size):
    assert vw.is_kid_item(title, size) == 1, f"{size!r} still reads as adult"


@pytest.mark.parametrize("title,size", ADULT_SIZES)
def test_adult_sizes_are_not_mistaken_for_kids(vw, title, size):
    assert vw.is_kid_item(title, size) == 0, f"{size!r} wrongly rejected as kids"


def test_kid_items_are_never_alerted(vw, con, paths, monkeypatch):
    monkeypatch.setattr(vw, "notify", lambda *a, **k: pytest.fail("alerted a kids item"))
    rec = {"id": 99, "search_tag": "t", "title": "Patagonia Jacke", "brand": "Patagonia",
           "size": "18–24 Monate / 86", "condition": "Sehr gut", "cond_tier": "very_good",
           "garment_class": "jacket", "is_kid": 1, "price": 12.0, "total_price": 12.0,
           "currency": "EUR", "url": "u", "photo_url": None, "seller_id": 1,
           "seller_login": "s", "favourites": 0, "views": 0, "promoted": 0, "seed": 0}
    settings = {"deal_ratio": 0.55, "min_comps": 1, "comp_window_days": 45, "min_price": 8}
    assert vw.score_and_alert(con, rec, {"tag": "t"}, settings, {}) is False


def test_kid_items_stay_out_of_comp_pools(vw, con, paths, monkeypatch):
    """A cheap kids fleece must not drag the adult median down."""
    sent = []
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.append(1) or True)
    now = vw.now_iso()
    for i in range(8):                      # adult comps around 40 EUR
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier, garment_class,"
            " is_kid, total_price, last_seen)"
            " VALUES (?,'t','Patagonia','patagonia','very_good','jacket',0,40.0,?)",
            (100 + i, now))
    for i in range(8):                      # kids noise around 10 EUR
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier, garment_class,"
            " is_kid, total_price, last_seen)"
            " VALUES (?,'t','Patagonia','patagonia','very_good','jacket',1,10.0,?)",
            (200 + i, now))
    con.commit()

    rec = {"id": 999, "search_tag": "t", "title": "Patagonia Jacke Herren", "brand": "Patagonia",
           "size": "L", "condition": "Sehr gut", "cond_tier": "very_good",
           "garment_class": "jacket", "is_kid": 0, "price": 20.0, "total_price": 20.0,
           "currency": "EUR", "url": "u", "photo_url": None, "seller_id": 1, "seller_login": "s",
           "favourites": 0, "views": 0, "promoted": 0, "seed": 0}
    settings = {"deal_ratio": 0.55, "min_comps": 6, "comp_window_days": 45, "min_price": 8}

    # Median of adults alone is 40, so 20 EUR is a deal. With kids mixed in the
    # median collapses to 25 and 20 EUR would score as ordinary.
    assert vw.score_and_alert(con, rec, {"tag": "t"}, settings, {}) is True
    assert sent, "a genuine adult deal was missed because kids prices polluted the median"


# ------------------------------------------------------------ schema migration

def test_old_database_gains_new_columns_without_losing_history(vw, paths):
    """A v1 DB must migrate in place; deleting it would destroy market history."""
    import sqlite3
    old = sqlite3.connect(vw.DB_PATH)
    old.execute("CREATE TABLE listings (id INTEGER PRIMARY KEY, search_tag TEXT, title TEXT,"
                " brand TEXT, size TEXT, cond_tier TEXT, total_price REAL,"
                " first_seen TEXT, last_seen TEXT, gone_at TEXT, sold_flag INTEGER DEFAULT 0,"
                " alerted INTEGER DEFAULT 0)")
    old.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    old.execute("INSERT INTO listings (id, search_tag, title, size) VALUES "
                "(1, 't', 'Patagonia Jacke', '18-24 Monate / 86')")
    old.execute("INSERT INTO listings (id, search_tag, title, size) VALUES "
                "(2, 't', 'Carhartt Jacke', 'L')")
    old.commit()
    old.close()

    con = vw.db_connect()
    cols = {row[1] for row in con.execute("PRAGMA table_info(listings)")}
    assert {"garment_class", "is_kid"} <= cols, "migration did not add the new columns"
    assert con.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 2, "history lost"
    assert con.execute("SELECT is_kid FROM listings WHERE id=1").fetchone()[0] == 1
    assert con.execute("SELECT is_kid FROM listings WHERE id=2").fetchone()[0] == 0
    assert con.execute("SELECT garment_class FROM listings WHERE id=2").fetchone()[0] == "jacket"
    con.close()


# ------------------------------------------------------------ cookie persistence

def test_cookie_roundtrip_keeps_domain_and_reads_legacy_files(vw, paths):
    transport, _ = vinted_server()
    c = client_with(vw, transport)
    c.cookies.set("refresh_token_web", "r", domain=".www.vinted.de")
    c.cookies.set("access_token_web", make_jwt(24), domain=".vinted.de")
    vw.save_cookies(c)

    domains = {ck["name"]: ck["domain"] for ck in json.loads(vw.COOKIE_PATH.read_text())}
    assert domains["refresh_token_web"] == ".www.vinted.de"

    reloaded = client_with(vw, transport)
    vw.load_cookies(reloaded)
    assert vw.token_is_fresh(reloaded, margin_min=60)

    vw.COOKIE_PATH.write_text(json.dumps({"access_token_web": make_jwt(24)}))   # v1 format
    legacy = client_with(vw, transport)
    vw.load_cookies(legacy)
    assert vw.token_is_fresh(legacy, margin_min=60), "legacy cookie file must still load"

# ------------------------------------------------ precision upgrade: normalisers

@pytest.mark.parametrize("condition,tier", [
    ("Neu", "new"),                       # the live string the v1 table missed
    ("Neu, mit Etikett", "new_tag"),      # comma spelling, also missed
    ("Neu mit Etikett", "new_tag"),
    ("Neu ohne Etikett", "new"),
    ("Sehr gut", "very_good"),
    ("  sehr   gut ", "very_good"),
    ("Zufriedenstellend", "fair"),
    ("", "unknown"),
    (None, "unknown"),
    ("Nagelneu Deluxe", "unknown"),
])
def test_cond_tier_maps_the_strings_the_api_actually_sends(vw, condition, tier):
    assert vw.cond_tier_of(condition) == tier


def test_cond_tier_backfill_recovers_unknown_rows_exactly_once(vw, paths):
    """The defect excluded every new-condition row from alerts AND comps."""
    import sqlite3
    old = sqlite3.connect(vw.DB_PATH)
    old.execute("CREATE TABLE listings (id INTEGER PRIMARY KEY, search_tag TEXT, title TEXT,"
                " brand TEXT, size TEXT, condition TEXT, cond_tier TEXT, total_price REAL,"
                " first_seen TEXT, last_seen TEXT, gone_at TEXT, sold_flag INTEGER DEFAULT 0,"
                " alerted INTEGER DEFAULT 0)")
    old.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    for i, cond in enumerate(["Neu", "Neu, mit Etikett", "Sehr gut"]):
        old.execute("INSERT INTO listings (id, search_tag, title, condition, cond_tier)"
                    " VALUES (?, 't', 'Carhartt Jacke', ?, 'unknown')", (i + 1, cond))
    old.commit()
    old.close()

    con = vw.db_connect()
    assert con.execute("SELECT cond_tier FROM listings WHERE id=1").fetchone()[0] == "new"
    assert con.execute("SELECT cond_tier FROM listings WHERE id=2").fetchone()[0] == "new_tag"
    assert con.execute("SELECT cond_tier FROM listings WHERE id=3").fetchone()[0] == "very_good"
    flag = con.execute("SELECT v FROM meta WHERE k='datafix:cond_tier_v2'").fetchone()
    assert flag and "rows=3" in flag[0]

    # A row legitimately set to unknown later must not be re-fixed on next connect.
    con.execute("UPDATE listings SET cond_tier='unknown' WHERE id=1")
    con.commit()
    con.close()
    con2 = vw.db_connect()
    assert con2.execute("SELECT cond_tier FROM listings WHERE id=1").fetchone()[0] == "unknown", \
        "data fix re-ran; it must be guarded by its meta flag"
    con2.close()


@pytest.mark.parametrize("size,cls", [
    ("M", "m"),
    ("S / 36 / 8", "s"),                  # combined notation, letter wins
    ("M / 38 / 10", "m"),
    ("W32 | DE 48", "w32"),               # jeans notation, W token beats the DE number
    ("W29", "w29"),
    ("XL / 42 / 14", "xl"),
    ("XXL", "xxl"),
    ("38", "m"),                          # bare women's DE
    ("46", "s"),                          # bare men's DE
    ("52", "xl"),                         # truthful: DE 52 is xl, not l
    ("39", "other"),                      # odd number can only be shoes
    ("12 Jahre / 152", "kids"),
    ("24-36 Monate / 92", "kids"),
    ("Einheitsgröße", "one"),
    ("", "unknown"),
    (None, "unknown"),
])
def test_size_class_normalises_all_three_live_notations(vw, size, cls):
    assert vw.size_class_of(size) == cls


@pytest.mark.parametrize("brand,norm", [
    ("Ralph Lauren", "ralph-lauren"),
    ("Polo Ralph Lauren", "ralph-lauren"),
    ("LAUREN Ralph Lauren", "ralph-lauren"),
    ("Chaps Ralph Lauren", "ralph-lauren"),
    ("adidas", "adidas"),
    ("adidas Originals", "adidas"),
    ("Nike Air", "nike"),
    ("Carhartt WIP", "carhartt"),
    ("Levi Strauss & Co.", "levis"),
    ("The North Face", "the-north-face"),
    ("7 For All Mankind", "7-for-all-mankind"),
    ("Some Unknown Label", "some-unknown-label"),
    ("", ""),
])
def test_brand_norm_folds_families_without_merging_strangers(vw, brand, norm):
    assert vw.brand_norm_of(brand) == norm


# ------------------------------------------------ precision upgrade: alert gates

def _rec(vw, **over):
    """A clean alertable candidate; override what a test is actually about."""
    rec = {"id": 999, "search_tag": "t", "title": "Patagonia Jacke Herren", "brand": "Patagonia",
           "brand_norm": "patagonia", "size": "L", "size_class": "l", "condition": "Sehr gut",
           "cond_tier": "very_good", "garment_class": "jacket", "is_kid": 0, "country": None,
           "price": 20.0, "total_price": 20.0, "currency": "EUR", "url": "u",
           "photo_url": "https://images1.vinted.net/t/x/f800/1.jpeg?s=sig", "seller_id": 1,
           "seller_login": "s", "favourites": 0, "views": 0, "promoted": 0, "seed": 0}
    rec.update(over)
    return rec


def _settings(**over):
    s = {"deal_ratio": 0.55, "min_comps": 6, "comp_window_days": 45, "min_price": 8,
         "size_classes": ["s", "m", "l"], "min_margin": 0, "foreign_advantage_eur": 8,
         "fake_risk_suppress": 0.7, "fake_risk_flag": 0.4,
         "profile_suppress": 0.15, "profile_min_rated": 8}
    s.update(over)
    return s


def _comps(con, vw, n=8, price=40.0, brand_norm="patagonia", size_class="l", base=100):
    now = vw.now_iso()
    for i in range(n):
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier, garment_class,"
            " size_class, is_kid, total_price, last_seen, first_seen)"
            " VALUES (?,'t','Patagonia',?, 'very_good','jacket',?,0,?,?,?)",
            (base + i, brand_norm, size_class, price, now, now))
    con.commit()


def test_size_gate_blocks_the_phone_but_never_the_comp_pool(vw, con, paths, monkeypatch):
    """Alerting narrows to resale-friendly sizes; the price database keeps everything."""
    sent = []
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.append(1) or True)
    # The comp pool is built entirely from XL rows: if comps were size-filtered
    # too, an M candidate would find nothing and could never alert.
    _comps(con, vw, n=8, price=40.0, size_class="xl")

    assert vw.score_and_alert(con, _rec(vw, size="XL", size_class="xl"), {"tag": "t"},
                              _settings(), {}) is False, "XL must not reach the phone"
    assert not sent
    assert vw.score_and_alert(con, _rec(vw, size="M", size_class="m"), {"tag": "t"},
                              _settings(), {}) is True, "comps must not be size-filtered"
    assert sent


def test_per_search_size_classes_override_the_global_set(vw, con, paths, monkeypatch):
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0, size_class="w27")
    jeans = {"tag": "t", "size_classes": ["w26", "w27", "w28"]}
    assert vw.score_and_alert(con, _rec(vw, size="W27", size_class="w27"), jeans,
                              _settings(), {}) is True
    assert vw.score_and_alert(con, _rec(vw, id=998, size="M", size_class="m"), jeans,
                              _settings(), {}) is False


def test_comp_pool_reunites_split_brand_families(vw, con, paths, monkeypatch):
    """Polo Ralph Lauren and Ralph Lauren are one market, so one comp pool."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    now = vw.now_iso()
    for i, raw in enumerate(["Ralph Lauren", "Polo Ralph Lauren", "LAUREN Ralph Lauren"] * 3):
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier, garment_class,"
            " size_class, is_kid, total_price, last_seen, first_seen)"
            " VALUES (?,'t',?,?, 'very_good','sweater','m',0,40.0,?,?)",
            (300 + i, raw, vw.brand_norm_of(raw), now, now))
    con.commit()
    rec = _rec(vw, brand="Polo Ralph Lauren", brand_norm="ralph-lauren",
               garment_class="sweater", size="M", size_class="m", title="Ralph Lauren Pullover")
    assert vw.score_and_alert(con, rec, {"tag": "t"}, _settings(), {}) is True


def test_price_gates_read_total_price_and_a_zero_cap_blocks(vw, con, paths, monkeypatch):
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    # 7.50 ex-fee, 8.90 total: the floor is about what the buyer pays, so this passes.
    assert vw.score_and_alert(con, _rec(vw, price=7.5, total_price=8.9), {"tag": "t"},
                              _settings(), {}) is True
    # price_max: 0 is an explicit "never alert", not a falsy no-op.
    assert vw.score_and_alert(con, _rec(vw, id=998), {"tag": "t", "price_max": 0},
                              _settings(), {}) is False


def test_alert_writes_a_full_decision_snapshot(vw, con, paths, monkeypatch):
    """The listings row is overwritten on re-sight; the snapshot is the record."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t"}, _settings(), {}) is True
    row = con.execute(
        "SELECT listing_id, comp_n, comp_median, discount_pct, margin_eur, deal_ratio_used,"
        " size_class, brand_norm, sent, suppress_reason FROM alerts").fetchone()
    assert row[0] == 999
    assert row[1] == 8
    assert row[2] == 40.0
    assert row[3] == 50            # 20 EUR against a 40 EUR median
    assert row[4] == 20.0
    assert row[5] == 0.55
    assert (row[6], row[7]) == ("l", "patagonia")
    assert row[8] == 1 and row[9] is None


def test_suppressed_candidates_are_recorded_not_forgotten(vw, con, paths, monkeypatch):
    """The backtest scorer needs the rejects to judge the policy that rejected them."""
    monkeypatch.setattr(vw, "notify",
                        lambda *a, **k: pytest.fail("a suppressed candidate was pushed"))
    _comps(con, vw, n=8, price=40.0, brand_norm="stone-island")
    # Suppression needs TWO independent signals. Price alone tops out at 0.6,
    # below the 0.7 bar, deliberately: silencing every deep discount would throw
    # away exactly the steals this watcher exists to find. Here an absurd price
    # meets a title the seller wrote themselves.
    rec = _rec(vw, price=3.0, total_price=3.5, brand="Stone Island",
               brand_norm="stone-island",
               title="Stone Island Jacke 1:1 Qualitaet")
    assert vw.score_and_alert(con, rec, {"tag": "t"}, _settings(min_price=3), {}) is False
    row = con.execute("SELECT sent, suppress_reason, fake_risk FROM alerts").fetchone()
    assert row[0] == 0
    assert row[1] == "fake_risk"
    assert row[2] >= 0.7


def test_a_deep_discount_alone_still_reaches_the_phone(vw, con, paths, monkeypatch):
    """The counterweight to suppression: a steal is not a fake just for being cheap."""
    sent = {}
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.update(k) or True)
    _comps(con, vw, n=8, price=40.0)
    rec = _rec(vw, price=3.0, total_price=3.5)     # 8.75% of median, no other signal
    assert vw.score_and_alert(con, rec, {"tag": "t"}, _settings(min_price=3), {}) is True
    assert "FAKE-RISIKO" in sent["message"], "it must arrive warned, not silently"


# ------------------------------------------------ precision upgrade: fake risk

def test_fake_risk_price_tiers_do_not_stack(vw, con, paths):
    """One price, one verdict, and never two terms for the same fact."""
    absurd, why = vw.fake_risk_score(con, _rec(vw, total_price=4.0), med=40.0)
    assert len([w for w in why if w.startswith("preis")]) == 1
    assert absurd == 0.6
    good, why2 = vw.fake_risk_score(con, _rec(vw, total_price=9.0), med=40.0)
    assert len([w for w in why2 if w.startswith("preis")]) == 1
    assert absurd > good


def test_a_hype_brand_sharpens_the_price_test_rather_than_adding_to_it(vw, con, paths):
    """The two used to be separate terms and both fired for the same fact.

    Anything below 0.15 of the median is also below 0.30, so a hype-brand item
    at 9% of market scored 0.6 plus 0.2 and was suppressed on price alone. That
    is exactly the steal this watcher exists to find.
    """
    plain = _rec(vw, total_price=11.0, brand="Some Label", brand_norm="some-label")
    hype = _rec(vw, total_price=11.0, brand="Stone Island", brand_norm="stone-island")
    # 27.5% of the median: below the hype threshold, above the ordinary one.
    assert vw.fake_risk_score(con, plain, med=40.0)[0] == 0.0
    assert vw.fake_risk_score(con, hype, med=40.0)[0] == 0.4
    # And at any price, the price test alone can never reach the suppress bar.
    for price in (1.0, 3.0, 5.0, 9.0):
        score, _ = vw.fake_risk_score(con, _rec(vw, total_price=price,
                                                brand="Stone Island",
                                                brand_norm="stone-island"), med=40.0)
        assert score < 0.7, f"{price} EUR was silenced on price alone"


def test_fake_risk_title_markers_flag_without_suppressing(vw, con, paths, monkeypatch):
    sent = {}
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.update(k) or True)
    _comps(con, vw, n=8, price=40.0)
    rec = _rec(vw, title="Patagonia Jacke 1:1 Qualitaet")
    assert vw.score_and_alert(con, rec, {"tag": "t"}, _settings(), {}) is True
    assert "FAKE-RISIKO" in sent["message"], "a flagged listing must say so on the phone"


def test_identical_title_across_sellers_raises_risk(vw, con, paths):
    now = vw.now_iso()
    for i in range(3):
        con.execute(
            "INSERT INTO listings (id, search_tag, title, seller_id, last_seen)"
            " VALUES (?,'t','Patagonia Jacke Herren',?,?)", (400 + i, 500 + i, now))
    con.commit()
    score, why = vw.fake_risk_score(con, _rec(vw), med=40.0)
    assert any(w.startswith("titel_bei_") for w in why)
    assert score >= 0.3


def test_a_clean_listing_scores_no_risk(vw, con, paths):
    score, why = vw.fake_risk_score(con, _rec(vw, total_price=22.0), med=40.0)
    assert score == 0.0 and why == []


# ------------------------------------------------ precision upgrade: country

def test_foreign_listings_need_price_headroom(vw, con, paths, monkeypatch):
    """Shipping from abroad is not in the comp median, so the bar moves.

    The default reading is the owner's own wording of criterion 5: at least the
    headroom below the comparable price. Comps sit at 40, so 31 clears and 33
    does not. Both still had to pass the ordinary deal gate first.
    """
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="IT"), {"tag": "t"},
                              _settings(), {}) is True
    assert vw.score_and_alert(con, _rec(vw, id=997, total_price=13.0, country="IT"),
                              {"tag": "t"}, _settings(), {}) is True


def test_the_foreign_headroom_basis_is_the_owners_switch(vw, con, paths, monkeypatch):
    """Which number the 8 EUR comes off is config, and it is worth ~83% of the stream.

    Under "deal_gate" the headroom is subtracted from 0.55 x median rather than
    from the median: measured over 622 real foreign candidates that killed
    83.1% of them, while 99.5% satisfied the criterion as it was written. The
    default is the literal reading; the strict one stays reachable in one word.
    """
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    strict = _settings(foreign_advantage_basis="deal_gate")
    # 21 EUR clears 0.55 x 40 = 22 but not 22 minus 8 EUR of headroom.
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="IT"), {"tag": "t"},
                              strict, {}) is False
    assert con.execute("SELECT suppress_reason FROM alerts").fetchone()[0] == "country"
    assert vw.score_and_alert(con, _rec(vw, id=998, total_price=13.0, country="IT"),
                              {"tag": "t"}, strict, {}) is True


def test_an_unset_basis_falls_back_to_the_literal_reading(vw, con, paths, monkeypatch):
    """The code default, not the yaml value: an old config must not resurrect the
    strict gate silently. The yaml is the owner's to flip; this is the floor
    under it."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    silent = _settings()
    silent.pop("foreign_advantage_basis", None)
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="IT"), {"tag": "t"},
                              silent, {}) is True


def test_the_resolved_country_reaches_the_alert_row_and_the_listing(vw, con, paths, monkeypatch):
    """Two columns, and the obvious one-line fix fills one by emptying the other.

    score_and_alert resolves the country into a local, and record_alert used to
    read rec, so 1194 of 1226 alert rows carried NULL while the gate above them
    had used a real country. Writing it back onto rec would satisfy the
    `not rec.get("country")` guard and skip the UPDATE that fills
    listings.country, which is the only column carrying correct location data
    today; both assertions below have to hold at once.
    """
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    con.execute("INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier,"
                " garment_class, size_class, total_price, first_seen, last_seen)"
                " VALUES (999,'t','Patagonia','patagonia','very_good','jacket','l',21.0,?,?)",
                (vw.now_iso(), vw.now_iso()))
    con.commit()
    calls = []
    payload = {"login": "x", "country_iso_code": "IT", "feedback_count": 60,
               "feedback_reputation": 0.9}
    client = httpx.Client(transport=_seller_server(vw, payload, calls), base_url=vw.BASE)
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0), {"tag": "t"},
                              _settings(), {}, client=client, seller_budget=[3]) is True
    assert con.execute("SELECT country FROM alerts").fetchone()[0] == "IT"
    assert con.execute("SELECT country FROM listings WHERE id=999").fetchone()[0] == "IT"


def test_a_suppressed_candidate_also_records_its_country(vw, con, paths, monkeypatch):
    """The backtest needs the country of what was DROPPED most of all."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="IT"), {"tag": "t"},
                              _settings(foreign_advantage_basis="deal_gate"), {}) is False
    row = con.execute("SELECT suppress_reason, country FROM alerts").fetchone()
    assert row == ("country", "IT")


def test_domestic_and_unknown_country_use_the_plain_gate(vw, con, paths, monkeypatch):
    """country is forward-only, so unknown must not be punished as foreign."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="DE"), {"tag": "t"},
                              _settings(), {}) is True
    assert vw.score_and_alert(con, _rec(vw, id=998, total_price=21.0, country=None),
                              {"tag": "t"}, _settings(), {}) is True


def test_item_country_reads_the_field_without_inventing_one(vw):
    assert vw.item_country({"user": {"country_iso_code": "de"}}) == "DE"
    assert vw.item_country({"user": {"id": 1, "login": "x"}}) is None
    assert vw.item_country({}) is None


# ------------------------------------------------ precision upgrade: feedback

def test_alert_carries_three_rating_buttons(vw, monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured.update(json)
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr(vw.httpx, "post", fake_post)
    env = {"NTFY_TOPIC": "alerts", "NTFY_FEEDBACK_TOPIC": "fb"}
    assert vw.notify(env, "t", "m", click="u", actions=vw.feedback_actions(env, 12345)) is True
    actions = captured["actions"]
    assert len(actions) == 3
    assert [a["body"] for a in actions] == ["good 12345", "bad 12345", "bought 12345"]
    assert all(a["url"] == "https://ntfy.sh/fb" and a["method"] == "POST" for a in actions)
    assert actions[0]["label"] == "\U0001F44D" and actions[1]["label"] == "\U0001F44E"


def test_no_feedback_topic_means_no_buttons(vw):
    assert vw.feedback_actions({"NTFY_TOPIC": "alerts"}, 1) is None


def test_ingest_feedback_stores_taps_and_dedupes_replays(vw, con, paths, monkeypatch):
    con.execute("INSERT INTO alerts (listing_id, alerted_at, search_tag, sent)"
                " VALUES (999, ?, 't', 1)", (vw.now_iso(),))
    con.commit()
    messages = [
        {"id": "m1", "event": "message", "message": "good 999"},
        {"id": "m2", "event": "message", "message": "bought 999"},
    ]
    monkeypatch.setattr(vw, "_ntfy_poll", lambda topic, since: messages)
    env = {"NTFY_FEEDBACK_TOPIC": "fb"}
    assert vw.ingest_feedback(con, env) == 2
    assert vw.ingest_feedback(con, env) == 0, "a replayed poll must not double-count"
    assert con.execute("SELECT COUNT(*) FROM alert_feedback").fetchone()[0] == 2
    assert vw.meta_get(con, "feedback_since") == "m2"


def test_ingest_feedback_ignores_noise_on_a_public_topic(vw, con, paths, monkeypatch):
    con.execute("INSERT INTO alerts (listing_id, alerted_at, search_tag, sent)"
                " VALUES (999, ?, 't', 1)", (vw.now_iso(),))
    con.commit()
    monkeypatch.setattr(vw, "_ntfy_poll", lambda topic, since: [
        {"id": "n1", "event": "message", "message": "hello there"},
        {"id": "n2", "event": "message", "message": "good notanumber"},
        {"id": "n3", "event": "message", "message": "maybe 999"},
        {"id": "n4", "event": "message", "message": "good 123456"},   # no such alert
        {"id": "n5", "event": "open", "message": "good 999"},         # not a message event
    ])
    assert vw.ingest_feedback(con, {"NTFY_FEEDBACK_TOPIC": "fb"}) == 0
    assert con.execute("SELECT COUNT(*) FROM alert_feedback").fetchone()[0] == 0


def test_learned_taste_ranks_but_never_overrides_an_explicit_gate(vw, con, paths, monkeypatch):
    """A good feedback track must not smuggle a suppressed candidate through."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: pytest.fail("gate was overridden"))
    _comps(con, vw, n=8, price=40.0)
    for i in range(10):                      # a strongly liked cell
        con.execute("INSERT INTO alerts (id, listing_id, alerted_at, search_tag, brand_norm,"
                    " garment_class, size_class, sent) VALUES (?,?,?,'t','patagonia','jacket','xl',1)",
                    (i + 1, 700 + i, vw.now_iso()))
        con.execute("INSERT INTO alert_feedback (listing_id, alert_id, verdict, received_at, source)"
                    " VALUES (?,?, 'good', ?, 'cli')", (700 + i, i + 1, vw.now_iso()))
    con.commit()
    # XL is outside the configured classes; the liked track must not rescue it.
    assert vw.score_and_alert(con, _rec(vw, size="XL", size_class="xl"), {"tag": "t"},
                              _settings(), {}) is False


def test_learned_suppression_needs_real_evidence(vw, con, paths, monkeypatch):
    """One bad rating is an opinion; a rated-out cell is a pattern."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    con.execute("INSERT INTO alerts (id, listing_id, alerted_at, search_tag, brand_norm,"
                " garment_class, size_class, sent) VALUES (1, 800, ?, 't','patagonia','jacket','l',1)",
                (vw.now_iso(),))
    con.execute("INSERT INTO alert_feedback (listing_id, alert_id, verdict, received_at, source)"
                " VALUES (800, 1, 'bad', ?, 'cli')", (vw.now_iso(),))
    con.commit()
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t"}, _settings(), {}) is True, \
        "a single bad rating must not silence a whole cell"

    for i in range(50, 60):
        con.execute("INSERT INTO alerts (id, listing_id, alerted_at, search_tag, brand_norm,"
                    " garment_class, size_class, sent)"
                    " VALUES (?,?,?, 't','patagonia','jacket','l',1)", (i, 800 + i, vw.now_iso()))
        con.execute("INSERT INTO alert_feedback (listing_id, alert_id, verdict, received_at, source)"
                    " VALUES (?,?, 'bad', ?, 'cli')", (800 + i, i, vw.now_iso()))
    con.commit()
    assert vw.score_and_alert(con, _rec(vw, id=997), {"tag": "t"}, _settings(), {}) is False
    assert con.execute(
        "SELECT suppress_reason FROM alerts WHERE listing_id=997").fetchone()[0] == "learned"


def test_cli_feedback_records_a_rating_by_hand(vw, con, paths, capsys):
    con.execute("INSERT INTO alerts (listing_id, alerted_at, search_tag, sent)"
                " VALUES (999, ?, 't', 1)", (vw.now_iso(),))
    con.commit()
    con.close()
    assert vw.cli_feedback(999, "bad") == 0
    assert vw.cli_feedback(999, "nonsense") == 2
    con2 = vw.db_connect()
    assert con2.execute("SELECT verdict, source FROM alert_feedback").fetchone() == ("bad", "cli")
    con2.close()


def test_alerts_disabled_collects_data_without_alerting(vw, con, paths, monkeypatch):
    """Probe and dropped brands keep feeding the price database; that is the asset."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: pytest.fail("alerts_disabled was ignored"))
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t", "alerts_disabled": True},
                              _settings(), {}) is False


# ------------------------------------------------ precision upgrade: image links

def test_reverse_image_links_encode_the_signed_photo_url(vw):
    links = vw.reverse_image_links("https://images1.vinted.net/t/x/f800/1.jpeg?s=a&b=c")
    assert set(links) == {"lens", "bing", "yandex"}
    assert "%3Fs%3Da%26b%3Dc" in links["lens"], "query string must survive as one parameter"
    assert links["lens"].startswith("https://lens.google.com/uploadbyurl?url=")
    assert vw.reverse_image_links(None) is None


def test_alert_message_carries_an_image_check_link(vw, con, paths, monkeypatch):
    sent = {}
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.update(k) or True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t"}, _settings(), {}) is True
    assert "lens.google.com" in sent["message"]


def test_quality_weighs_absolute_margin_not_just_discount_depth(vw):
    """60% off a 12 EUR item deserves less attention than 45% off a 90 EUR one."""
    cheap = vw.alert_quality(60, 7.0, 0.0, "DE", True, None)
    dear = vw.alert_quality(45, 50.0, 0.0, "DE", True, None)
    assert dear > cheap
    # Fake risk, foreign shipping and a disliked cell all cost quality.
    clean = vw.alert_quality(50, 30.0, 0.0, "DE", True, None)
    assert vw.alert_quality(50, 30.0, 0.5, "DE", True, None) < clean
    assert vw.alert_quality(50, 30.0, 0.0, "IT", True, None) < clean
    assert vw.alert_quality(50, 30.0, 0.0, "DE", False, None) < clean
    assert vw.alert_quality(50, 30.0, 0.0, "DE", True, 0.1) < clean
    assert vw.alert_quality(50, 30.0, 0.0, "DE", True, 0.9) > clean


def test_a_flagged_listing_never_interrupts(vw, con, paths):
    """Whatever it scores, a fake-risk flag means it arrives quietly."""
    assert vw.alert_priority(80, 0.5, "DE", True, None, con=con, margin_eur=90) == 2


def test_without_history_the_ladder_falls_back_to_absolute_cuts(vw, con, paths):
    """A cold start should ring for the obvious ones rather than stay silent."""
    loud = vw.alert_priority(60, 0.0, "DE", True, None, con=con, margin_eur=45)
    assert loud == 5
    quiet = vw.alert_priority(15, 0.0, "DE", False, None, con=con, margin_eur=5)
    assert quiet == 2


def test_the_loud_tier_is_relative_to_the_days_own_stream(vw, con, paths):
    """An absolute bar cannot hold: measured on real rows it put 46% of
    candidates in the ringing tier once country data existed, and 0% before it.
    The bar is the day's own competition instead, so the loud tier stays near
    RING_BUDGET_PER_DAY however busy the market gets.
    """
    now = vw.now_iso()
    # A day of strong alerts: every one better than the candidate below.
    for i in range(40):
        con.execute(
            "INSERT INTO alerts (listing_id, alerted_at, search_tag, discount_pct,"
            " margin_eur, quality, sent) VALUES (?,?,'t',?,?,?,1)",
            (6000 + i, now, 60, 60, vw.alert_quality(60, 60, 0.0, 'DE', True, None)))
    con.commit()
    # Same candidate that rings on a cold start must now be merely normal or
    # quiet, because forty better ones already came through today.
    assert vw.alert_priority(45, 0.0, "DE", True, None, con=con, margin_eur=20) < 5
    # Something that beats the whole field still rings.
    assert vw.alert_priority(70, 0.0, "DE", True, None, con=con, margin_eur=80) == 5


def test_a_busy_day_does_not_multiply_the_ringing(vw, con, paths):
    """The point of the relative bar: volume can triple without the phone doing so."""
    now = vw.now_iso()
    import random
    rng = random.Random(7)
    scores = []
    for i in range(400):
        d, m = rng.uniform(45, 80), rng.uniform(5, 70)
        scores.append((d, m))
        con.execute(
            "INSERT INTO alerts (listing_id, alerted_at, search_tag, discount_pct,"
            " margin_eur, quality, sent) VALUES (?,?,'t',?,?,?,?)",
            (7000 + i, now, d, m, vw.alert_quality(d, m, 0.0, 'DE', True, None),
             1 if i < 150 else 0))
    con.commit()
    rings = sum(1 for d, m in scores
                if vw.alert_priority(d, 0.0, "DE", True, None, con=con, margin_eur=m) == 5)
    # Out of 400 candidates in one day, only a small head should ring.
    assert rings <= 60, f"{rings} of 400 would ring; the bar is not holding"
    assert rings >= 1, "the bar must not silence everything either"


def _fill_day(vw, con, n, when=None, quality=200.0, sent=0, suppress=None, first_id=20000):
    """n recorded candidates at one moment, all better than any test candidate."""
    when = when or vw.now_iso()
    for i in range(n):
        con.execute(
            "INSERT INTO alerts (listing_id, alerted_at, search_tag, quality, sent,"
            " suppress_reason) VALUES (?,?,'t',?,?,?)",
            (first_id + i, when, quality, sent, suppress))
    con.commit()


def test_yesterdays_field_does_not_set_todays_bar(vw, con, paths):
    """The whole 2026-09-10 failure in one assertion.

    The pool was a rolling 24 hours, so a morning was ranked against the
    previous day's finished field: 470 of the 528 rows in the 08:20Z pool were
    from the day before and the bar stood at the 88.6th percentile of a day
    that was over. Nine pushes arrived, none of them loud.
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _fill_day(vw, con, 200, when=yesterday, quality=500.0)
    # A good candidate, hopeless against yesterday's field, alone in today's.
    # Both bars read the same pool, so both are asserted: against a rolling
    # window this is priority 0, silently withheld.
    assert vw.alert_priority(60, 0.0, "DE", True, None, con=con, margin_eur=40) == 5
    assert vw.ranking_pool(con) == [], "yesterday's rows are in today's pool"


def test_messages_ntfy_refused_never_enter_the_pool(vw, con, paths):
    """147 of the 528 pool rows (27.8%) were pushes that never arrived.

    A notify_failed row is a refusal by the notification service, not a find.
    Letting them compete raised the bar on the strength of alerts nobody saw.
    """
    _fill_day(vw, con, 200, quality=500.0, suppress="notify_failed")
    assert vw.ranking_pool(con) == []
    assert vw.alert_priority(50, 0.0, "DE", True, None, con=con, margin_eur=25) > 0
    _fill_day(vw, con, 200, quality=500.0, suppress="send_budget", first_id=30000)
    assert len(vw.ranking_pool(con)) == 200, "a withheld candidate is still a candidate"


def test_the_hard_ceiling_stops_a_second_flood(vw, con, paths):
    """The cutout behind the budgets: it counts pushes that actually left."""
    _fill_day(vw, con, vw.HARD_SEND_CEILING - 1, sent=1, quality=1.0)
    assert vw.alert_priority(70, 0.0, "DE", True, None, con=con, margin_eur=80) > 0
    _fill_day(vw, con, 1, sent=1, quality=1.0, first_id=40000)
    assert vw.pushes_today(con) == vw.HARD_SEND_CEILING
    assert vw.alert_priority(70, 0.0, "DE", True, None, con=con, margin_eur=80) == 0


def test_a_flagged_listing_cannot_be_promoted_past_the_fake_check(vw, con, paths):
    """The regression the 2026-09-10 rework had to not introduce.

    alert_priority returns 2 for fake risk before it ever considers the ring
    bar, so no "it has been quiet, ring the best one" clause can be slipped in
    above it. The live case: the Stone Island piece at 09:20:47Z, quality
    136.344 and the day's second best, correctly silent at fake_risk 0.40.
    """
    _fill_day(vw, con, 50, quality=1.0)
    top = vw.alert_priority(80, 0.0, "DE", True, None, con=con, margin_eur=90)
    flagged = vw.alert_priority(80, 0.4, "DE", True, None, con=con, margin_eur=90)
    assert top == 5, "the unflagged twin must be the loudest thing in the day"
    assert flagged == 2, "a fake-risk flag must survive being the best of the day"

# ------------------------------------------- precision upgrade: seller profile

def _seller_server(vw, payload, calls):
    """A transport that answers the user endpoint once and counts the calls."""
    def handler(request):
        calls.append(str(request.url))
        if "/api/v2/users/" in str(request.url):
            return httpx.Response(200, json={"user": payload})
        return httpx.Response(200, json={"items": []})
    return httpx.MockTransport(handler)


def test_seller_profile_is_fetched_once_and_then_cached(vw, con, paths):
    """Sellers repeat across listings, so the cost is per seller, not per item."""
    calls = []
    payload = {"login": "meike", "country_iso_code": "nl", "city": "Amsterdam",
               "feedback_count": 121, "positive_feedback_count": 89,
               "feedback_reputation": 0.78, "item_count": 173, "business": False}
    client = httpx.Client(transport=_seller_server(vw, payload, calls), base_url=vw.BASE)
    budget = [6]
    first = vw.seller_profile(client=client, con=con, seller_id=42, budget=budget)
    assert first["country"] == "NL"
    assert first["feedback_count"] == 121
    second = vw.seller_profile(client=client, con=con, seller_id=42, budget=budget)
    assert second["country"] == "NL"
    assert len(calls) == 1, "a cached seller must not be fetched twice"
    assert budget == [5], "only the uncached lookup may spend budget"


def test_seller_lookups_are_capped_per_cycle(vw, con, paths):
    """An unbounded lookup would multiply the request budget on a busy cycle."""
    calls = []
    payload = {"login": "x", "country_iso_code": "de", "feedback_count": 5}
    client = httpx.Client(transport=_seller_server(vw, payload, calls), base_url=vw.BASE)
    budget = [2]
    for seller_id in (1, 2, 3, 4):
        vw.seller_profile(client=client, con=con, seller_id=seller_id, budget=budget)
    assert len(calls) == 2, "the cap must hold"
    assert budget == [0]


def test_a_failed_lookup_costs_no_accusation(vw, con, paths):
    """No profile means no seller-based risk, never a guessed one."""
    def handler(request):
        return httpx.Response(500)
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=vw.BASE)
    prof = vw.seller_profile(client=client, con=con, seller_id=99, budget=[3])
    assert prof is None
    assert vw.seller_risk(None, "stone-island", 10.0, 100.0) == (0.0, [])


def test_new_account_selling_a_hype_brand_cheap_raises_risk(vw):
    """The classic counterfeit shape, now measurable via the profile endpoint."""
    fresh = {"feedback_count": 0, "feedback_reputation": None}
    score, why = vw.seller_risk(fresh, "stone-island", 20.0, 100.0)
    assert score >= 0.3 and "neuer_verkaeufer_hype_billig" in why
    # The same empty account selling an ordinary brand at an ordinary price is
    # just a beginner, and must not be treated as a forger.
    mild, why2 = vw.seller_risk(fresh, "patagonia", 80.0, 100.0)
    assert mild < score and "keine_bewertungen" in why2


def test_an_established_seller_with_good_feedback_adds_no_risk(vw):
    solid = {"feedback_count": 121, "feedback_reputation": 0.95}
    assert vw.seller_risk(solid, "stone-island", 20.0, 100.0) == (0.0, [])


def test_bad_reputation_with_enough_ratings_raises_risk(vw):
    poor = {"feedback_count": 40, "feedback_reputation": 0.42}
    score, why = vw.seller_risk(poor, "patagonia", 50.0, 100.0)
    assert score >= 0.2 and any("schlechte_reputation" in w for w in why)


def test_country_comes_from_the_seller_and_is_written_back(vw, con, paths, monkeypatch):
    """The catalog response carries no country; the seller profile does."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    calls = []
    payload = {"login": "x", "country_iso_code": "IT", "feedback_count": 60,
               "feedback_reputation": 0.9}
    client = httpx.Client(transport=_seller_server(vw, payload, calls), base_url=vw.BASE)
    con.execute("INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier,"
                " garment_class, size_class, total_price, first_seen, last_seen)"
                " VALUES (999,'t','Patagonia','patagonia','very_good','jacket','l',21.0,?,?)",
                (vw.now_iso(), vw.now_iso()))
    con.commit()
    # 21 EUR clears the plain 0.55 x 40 gate but not that gate minus 8 EUR.
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0), {"tag": "t"},
                              _settings(foreign_advantage_basis="deal_gate"), {},
                              client=client, seller_budget=[3]) is False
    assert con.execute("SELECT country FROM listings WHERE id=999").fetchone()[0] == "IT"
    assert con.execute("SELECT suppress_reason FROM alerts").fetchone()[0] == "country"


def test_scoring_without_a_client_still_works(vw, con, paths, monkeypatch):
    """Every existing call site passes no client; none of them may break."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t"}, _settings(), {}) is True

def test_a_server_error_backs_off_instead_of_holding_the_cadence(vw, con, paths):
    """A 5xx wave is the far end struggling; keep polling and you make it worse.

    Live shape on 2026-09-08: a burst of one-off probe requests alongside the
    normal 5-minute cycle turned every catalog call into a 500, including
    searches that had answered minutes earlier. Without this the watcher would
    have kept its cadence pointed at a struggling endpoint indefinitely.
    """
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        return httpx.Response(500, text="oops")

    client = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    with pytest.raises(vw.SessionWall):
        vw.api_get(client, con, f"{vw.BASE}/api/v2/catalog/items", {"search_text": "x"})
    until = vw.parse_ts(vw.meta_get(con, "backoff_until"))
    assert until is not None, "a 5xx must set a backoff"
    minutes = (until - datetime.now(timezone.utc)).total_seconds() / 60
    assert 5 < minutes <= vw.SERVER_BACKOFF_MIN + 1
    assert len([c for c in calls if "catalog" in c]) == 1, "no retry into a 5xx"


def test_a_server_error_is_not_mistaken_for_a_bot_wall(vw, con, paths):
    """They call for different waits, so they must not share a code path."""
    assert vw.SERVER_BACKOFF_MIN < vw.WALL_BACKOFF_MIN

# ------------------------------------ politeness: a refusal must survive the cycle

def test_a_wall_on_the_seller_endpoint_is_not_erased_by_a_good_catalog_poll(vw, paths, monkeypatch):
    """Vinted rate-limits the client, not one endpoint.

    Found by adversarial review and reproduced: the catalog answered 200 while
    /api/v2/users/{id} answered 429. api_get set the backoff and raised,
    seller_profile swallowed it, and then run_cycle's success branch deleted
    backoff_until AND backoff_level, because a poll had got through. The
    refusal and its escalation level both vanished, and five minutes later the
    watcher polled at full rate again, forever.
    """
    calls = {"catalog": 0, "user": 0}

    def handler(request):
        path = request.url.path
        if path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        if "/api/v2/users/" in path:
            calls["user"] += 1
            return httpx.Response(429, text="slow down")
        calls["catalog"] += 1
        return httpx.Response(200, json={"items": [{
            "id": 5000 + calls["catalog"], "title": "Patagonia Regenjacke Herren",
            "brand_title": "Patagonia", "size_title": "M", "status": "Sehr gut",
            "price": {"amount": "20.0", "currency_code": "EUR"},
            "total_item_price": {"amount": "20.0"},
            "user": {"id": 77, "login": "s"}, "url": "u",
            "photo": {"url": "p"}, "favourite_count": 0, "view_count": 0}]})

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler),
                                             base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 1, "comp_window_days": 45,
                     "min_price": 5, "poll_per_page": 48, "seed_pages": 1,
                     "seed_per_page": 10, "size_classes": ["m"], "min_margin": 0,
                     "foreign_advantage_eur": 8, "fake_risk_suppress": 0.7,
                     "fake_risk_flag": 0.4, "profile_suppress": 0.15,
                     "profile_min_rated": 8},
        "searches": [{"tag": "t", "query": "q", "price_max": 100}]})
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)

    con = vw.db_connect()
    now = vw.now_iso()
    vw.meta_set(con, "seeded:t", now)           # steady-state path, so scoring runs
    vw.meta_set(con, "last_success", now)       # ...and no gap, so no freshness screen
    for i in range(4):                          # comps so a candidate can score
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, brand_norm, cond_tier,"
            " garment_class, size_class, is_kid, total_price, last_seen, first_seen)"
            " VALUES (?,'t','Patagonia','patagonia','very_good','jacket','m',0,60.0,?,?)",
            (900 + i, now, now))
    con.commit()
    con.close()
    vw.acquire_lock()
    vw.LOCK_PATH.unlink(missing_ok=True)

    vw.run_cycle()

    con = vw.db_connect()
    until = vw.meta_get(con, "backoff_until")
    level = vw.meta_get(con, "backoff_level")
    con.close()
    assert calls["user"] >= 1, "the seller endpoint must actually have been tried"
    assert until is not None, "the 429 was erased by the successful catalog poll"
    assert level is not None, "the escalation level was erased too"


def test_a_clean_cycle_still_clears_an_old_backoff(vw, paths, monkeypatch):
    """The counterweight: without a wall, a good poll must free the watcher."""
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        return httpx.Response(200, json={"items": []})

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler),
                                             base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 8, "comp_window_days": 45,
                     "min_price": 5, "poll_per_page": 48, "seed_pages": 1,
                     "seed_per_page": 10},
        "searches": [{"tag": "t", "query": "q"}]})
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)

    con = vw.db_connect()
    vw.meta_set(con, "seeded:t", vw.now_iso())
    # An EXPIRED backoff: an active one would correctly skip the cycle, which
    # would prove nothing about the clearing branch.
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vw.meta_set(con, "backoff_until", past)
    vw.meta_set(con, "backoff_level", "2")
    con.commit()
    con.close()

    vw.run_cycle()

    con = vw.db_connect()
    assert vw.meta_get(con, "backoff_until") is None, "a clean cycle must free the watcher"
    con.close()


def test_the_recheck_loop_backs_off_instead_of_walking_into_a_wall(vw, con, paths, monkeypatch):
    """The recheck is the biggest request block and had no wall handling at all.

    It fetches item pages rather than the JSON API, so it cannot go through
    api_get. Without its own status check a 429 matched no branch: not 404/410,
    not a redirect, not 200. The loop simply went round again, twenty-five
    times, and repeated an hour later.
    """
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(429, text="slow down")

    client = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(40):
        con.execute("INSERT INTO listings (id, search_tag, url, first_seen, last_seen)"
                    " VALUES (?,'t',?,?,?)",
                    (700 + i, f"{vw.BASE}/items/{700+i}", old, old))
    con.commit()
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)

    vw.recheck_gone(client, con, session_proven=True)

    assert len(calls) == 1, f"walked into the wall {len(calls)} times instead of stopping"
    assert vw.meta_get(con, "backoff_until") is not None, "a 429 in recheck set no backoff"
    assert con.execute("SELECT COUNT(*) FROM listings WHERE gone_at IS NOT NULL"
                       ).fetchone()[0] == 0, "a refusal must never be recorded as an outcome"


def test_recheck_still_records_real_outcomes(vw, con, paths, monkeypatch):
    """The counterweight: the new guard must not swallow honest 404s."""
    def handler(request):
        return httpx.Response(404)

    client = client_with(vw, httpx.MockTransport(handler), token=make_jwt(12))
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(10):
        con.execute("INSERT INTO listings (id, search_tag, url, first_seen, last_seen)"
                    " VALUES (?,'t',?,?,?)",
                    (750 + i, f"{vw.BASE}/items/{750+i}", old, old))
    con.commit()
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)
    vw.recheck_gone(client, con, session_proven=True)
    # All ten 404 at once, so the batch ceiling discards them as systemic; what
    # matters here is that the pass ran rather than being cut short by the guard.
    assert vw.meta_get(con, "last_recheck") is not None
    assert vw.meta_get(con, "backoff_until") is None, "an honest 404 is not a wall"

# --------------------------------- backlog: a gap makes a backlog, not a count

def test_a_busy_search_is_not_mistaken_for_a_backlog(vw, con, paths):
    """Measured cost of the old rule: 67% of listings were never scored.

    A search returning 40 new listings five minutes after the last successful
    poll is watching a busy market, not working through a pile. The old
    count-only rule suppressed nike-vintage on 77% of its cycles and
    adidas-vintage on 75%, which is precisely where the turnover is.
    """
    vw.meta_set(con, "last_success",
                (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    assert vw.is_catch_up(con) is False


def test_only_the_clock_decides_that_a_cycle_is_a_catch_up(vw, con, paths):
    """Batch size says nothing, and reading it as a signal cost a whole morning.

    On 2026-09-10 the count condition discarded 449 of 456 freshly collected
    listings without scoring one, 76.3% of them under 45 minutes old. Raising
    the threshold was not the fix either: the comparison is a strict
    greater-than against a page size of 48, and the largest batch in 1887 log
    lines was exactly 48, so at 48 the gate would never fire again and the
    freshness check behind it would be dead code. The gap decides that a batch
    needs screening; CATCH_UP_FRESH_MIN decides, per listing, what survives it.
    """
    vw.meta_set(con, "last_success",
                (datetime.now(timezone.utc) - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    assert vw.is_catch_up(con) is True
    vw.meta_set(con, "last_success",
                (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    assert vw.is_catch_up(con) is False


def test_an_unknown_gap_is_treated_as_one(vw, con, paths):
    """A fresh database or a corrupt stamp has no age information to trust."""
    assert vw.meta_get(con, "last_success") is None
    assert vw.is_catch_up(con) is True
    vw.meta_set(con, "last_success", "not-a-timestamp")
    con.commit()
    assert vw.is_catch_up(con) is True

# ------------------- a public topic must not be able to break the feedback poll

def test_an_oversized_id_from_a_stranger_cannot_kill_the_poll(vw, con, paths, monkeypatch):
    """The feedback topic is public by obscurity, so anyone can post to it.

    An unbounded digit run reached sqlite as an integer too large to bind and
    raised OverflowError inside the poll, on every cycle, until someone noticed.
    A single message from a stranger was enough to end the rating channel.
    """
    con.execute("INSERT INTO alerts (listing_id, alerted_at, search_tag, sent)"
                " VALUES (4242, ?, 't', 1)", (vw.now_iso(),))
    con.commit()
    monkeypatch.setattr(vw, "_ntfy_poll", lambda topic, since: [
        {"id": "a", "event": "message", "message": "good " + "9" * 400},
        {"id": "b", "event": "message", "message": "good 4242"},   # a real one behind it
    ])
    got = vw.ingest_feedback(con, {"NTFY_FEEDBACK_TOPIC": "t"})
    assert got == 1, "the genuine rating behind the junk must still land"
    assert con.execute("SELECT listing_id FROM alert_feedback").fetchone()[0] == 4242


@pytest.mark.parametrize("junk", [
    "good " + "9" * 400,
    "bad " + "1" * 25,
    "bought 99999999999999999999999999",
])
def test_absurd_ids_are_rejected_by_shape(vw, junk):
    assert vw.FEEDBACK_RE.match(junk) is None


def test_a_real_ten_digit_listing_id_still_parses(vw):
    """The bound must not exclude the ids Vinted actually issues."""
    m = vw.FEEDBACK_RE.match("good 9932723613")
    assert m and m.group(2) == "9932723613"


# --------------------------- a backfill that died must be redone, not assumed

def test_a_column_added_without_its_backfill_is_filled_on_the_next_start(vw, paths):
    """ALTER TABLE commits on the spot, so a crash mid-backfill leaves a hole.

    Keying completion on the column existing meant the fill was never retried
    and those rows stayed blank for good. On a database that cannot be rebuilt
    that is silent and permanent.
    """
    import sqlite3
    old = sqlite3.connect(vw.DB_PATH)
    old.execute("CREATE TABLE listings (id INTEGER PRIMARY KEY, search_tag TEXT,"
                " title TEXT, brand TEXT,"
                " size TEXT, condition TEXT, cond_tier TEXT, total_price REAL,"
                " first_seen TEXT, last_seen TEXT, gone_at TEXT,"
                " sold_flag INTEGER DEFAULT 0, alerted INTEGER DEFAULT 0)")
    old.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    for i in range(5):
        old.execute("INSERT INTO listings (id, search_tag, title, brand, size, condition,"
                    " cond_tier) VALUES (?, 't', 'Carhartt Jacke', 'Carhartt WIP', 'M',"
                    " 'Sehr gut', 'very_good')", (i,))
    # The crash: the column exists, nothing filled it, no flag was written.
    old.execute("ALTER TABLE listings ADD COLUMN brand_norm TEXT")
    old.commit()
    old.close()

    con = vw.db_connect()
    filled = con.execute(
        "SELECT COUNT(*) FROM listings WHERE brand_norm='carhartt'").fetchone()[0]
    assert filled == 5, "the interrupted backfill was never redone"
    assert vw.meta_get(con, "backfill:brand_norm") is not None
    con.close()


def test_a_completed_backfill_is_not_repeated(vw, paths):
    """The flag is what stops it, so a hand-edited value must survive a restart."""
    con = vw.db_connect()
    con.execute("INSERT INTO listings (id, search_tag, brand, brand_norm)"
                " VALUES (1, 't', 'Carhartt', 'deliberately-different')")
    con.commit()
    con.close()
    con = vw.db_connect()
    assert con.execute("SELECT brand_norm FROM listings WHERE id=1").fetchone()[0] \
        == "deliberately-different", "a finished backfill must not run again"
    con.close()


# --------------------------------- 2026-09-08: the alerts table stopped recording
#
# alerts.quality was added to the DDL. CREATE TABLE IF NOT EXISTS does nothing
# to a table that already exists, and the migration loop only ever walked
# listings, so the production alerts table never got the column. Every INSERT
# raised OperationalError from that moment. The insert sits behind the ntfy
# call, so alerts kept arriving on the phone; the per-search handler caught the
# error as if it were a flaky poll and logged a warning into a stdout that
# run-hidden.vbs discards. 21 alerts and the owner's first two real rating taps
# were lost in two hours, and nothing anywhere reported a failure.

def _old_shape_alerts_db(vw):
    """A database whose alerts table predates the quality column."""
    import sqlite3 as s3
    c = s3.connect(vw.DB_PATH)
    c.executescript("""
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            alerted_at TEXT NOT NULL,
            search_tag TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    c.commit()
    c.close()


def test_a_column_added_to_the_ddl_reaches_an_existing_table(vw, paths):
    _old_shape_alerts_db(vw)
    con = vw.db_connect()
    live = {r[1] for r in con.execute("PRAGMA table_info(alerts)")}
    declared = {name for name, _ in vw.ddl_columns()["alerts"]}
    assert declared <= live, f"still missing after migrate: {sorted(declared - live)}"
    con.close()


def test_record_alert_survives_a_database_that_predates_the_column(vw, paths):
    """The bite: this is the exact call that failed silently in production."""
    _old_shape_alerts_db(vw)
    con = vw.db_connect()
    rec = {"id": 42, "search_tag": "t", "title": "x", "brand": "Levi\'s",
           "size": "W31 | DE 46", "price": 8.0, "total_price": 9.1}
    rowid = vw.record_alert(con, rec, {"quality": 88.0, "priority": 5, "sent": 1})
    assert rowid > 0
    assert con.execute("SELECT quality FROM alerts WHERE id=?", (rowid,)).fetchone()[0] == 88.0
    con.close()


def test_ddl_columns_reads_columns_and_not_constraints(vw):
    tables = vw.ddl_columns()
    assert {"listings", "alerts", "sellers", "alert_feedback", "meta"} <= set(tables)
    alerts = dict(tables["alerts"])
    assert "quality" in alerts and "comp_median" in alerts
    assert not any(name.lower() in {"primary", "unique", "foreign", "check"}
                   for name in alerts), "a table constraint was read as a column"
    # A multi-column declaration on one line must still yield every column.
    assert {"title", "brand", "brand_norm"} <= set(alerts)


def test_a_column_sqlite_cannot_add_in_place_is_reported_not_crashed(vw, paths, capsys):
    assert vw.alterable("REAL") is True
    assert vw.alterable("INTEGER NOT NULL DEFAULT 0") is True
    assert vw.alterable("INTEGER PRIMARY KEY AUTOINCREMENT") is False
    assert vw.alterable("TEXT NOT NULL") is False, "SQLite refuses this on a filled table"
    assert vw.alterable("TEXT UNIQUE") is False, "alert_feedback.ntfy_msg_id is exactly this"
    assert vw.alterable("TEXT DEFAULT CURRENT_TIMESTAMP") is False
    import sqlite3 as s3
    c = s3.connect(vw.DB_PATH)
    # verdict is TEXT NOT NULL with no default, which SQLite will not add to an
    # existing table. The connect must report it and carry on: bricking every
    # mode of the watcher over one column is worse than running without it.
    c.executescript(
        "CREATE TABLE alert_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " listing_id INTEGER NOT NULL, received_at TEXT NOT NULL, source TEXT NOT NULL);"
        "CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);")
    c.commit()
    c.close()
    con = vw.db_connect()                       # must not raise
    out = capsys.readouterr().out
    assert "alert_feedback.verdict is missing and cannot be added in place" in out
    assert con.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0, \
        "the connect has to stay usable"
    con.close()


def test_an_index_that_cannot_be_built_does_not_brick_the_connect(vw, paths, capsys):
    import sqlite3 as s3
    c = s3.connect(vw.DB_PATH)
    c.executescript("CREATE TABLE alerts (listing_id INTEGER);"      # no alerted_at
                    "CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);")
    c.commit()
    c.close()
    con = vw.db_connect()                       # used to raise: no such column
    assert "index not created" in capsys.readouterr().out
    con.close()


def test_a_rating_outlives_a_missing_alert_snapshot(vw, con, paths, monkeypatch):
    """The tap is the scarce thing; a bookkeeping gap must not discard it."""
    con.execute("INSERT INTO listings (id, search_tag, title) VALUES (9934904203, 't', 'x')")
    con.commit()
    monkeypatch.setattr(vw, "_ntfy_poll", lambda topic, since: [
        {"id": "m1", "event": "message", "message": "bought 9934904203"},
    ])
    assert vw.ingest_feedback(con, {"NTFY_FEEDBACK_TOPIC": "fb"}) == 1
    row = con.execute("SELECT verdict, alert_id FROM alert_feedback").fetchone()
    assert row == ("bought", None), "stored, and honestly unlinked"


def test_a_rating_for_a_listing_we_never_saw_is_still_refused(
        vw, con, paths, monkeypatch, capsys):
    monkeypatch.setattr(vw, "_ntfy_poll", lambda topic, since: [
        {"id": "m1", "event": "message", "message": "good 5555555555"},
    ])
    assert vw.ingest_feedback(con, {"NTFY_FEEDBACK_TOPIC": "fb"}) == 0
    assert con.execute("SELECT COUNT(*) FROM alert_feedback").fetchone()[0] == 0
    assert "stranger noise" in capsys.readouterr().out, "silence is what hid the last one"


def test_log_lines_land_in_a_file_the_hidden_task_cannot_swallow(vw, paths):
    vw.log("hello from a headless cycle")
    text = (paths / vw.LOG_NAME).read_text(encoding="utf-8")
    assert "hello from a headless cycle" in text


def test_the_log_file_rotates_instead_of_growing_without_end(vw, paths, monkeypatch):
    monkeypatch.setattr(vw, "LOG_MAX_BYTES", 200)
    for i in range(40):
        vw.log(f"line {i} padded out to move past the cap quickly")
    assert (paths / (vw.LOG_NAME + ".1")).exists(), "nothing was rotated"
    assert (paths / vw.LOG_NAME).stat().st_size < 4000


def test_a_schema_error_is_told_apart_from_a_transient_one(vw):
    import sqlite3 as s3
    assert vw.is_schema_error(s3.OperationalError("table alerts has no column named quality"))
    assert vw.is_schema_error(s3.OperationalError("no such table: alerts"))
    assert not vw.is_schema_error(s3.OperationalError("database is locked"))
    assert not vw.is_schema_error(ValueError("no such column"))


def test_a_schema_mismatch_ends_the_cycle_instead_of_reading_as_a_flaky_poll(
        vw, paths, monkeypatch):
    """Non-zero exit is the only signal a hidden scheduled task can carry."""
    import sqlite3 as s3

    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        return httpx.Response(200, json={"items": []})

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler),
                                             base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 8, "comp_window_days": 45,
                     "min_price": 5, "poll_per_page": 48, "seed_pages": 1,
                     "seed_per_page": 10},
        "searches": [{"tag": "t", "query": "q"}, {"tag": "t2", "query": "q2"}]})
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)

    def boom(*a, **k):
        raise s3.OperationalError("table alerts has no column named quality")

    monkeypatch.setattr(vw, "poll_search", boom)
    with pytest.raises(s3.OperationalError):
        vw.run_cycle()


def test_a_flaky_search_still_costs_only_itself(vw, paths, monkeypatch):
    """The counterweight: the narrow escalation must not swallow the old rule."""
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        return httpx.Response(200, json={"items": []})

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler),
                                             base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 8, "comp_window_days": 45,
                     "min_price": 5, "poll_per_page": 48, "seed_pages": 1,
                     "seed_per_page": 10},
        "searches": [{"tag": "bad", "query": "q"}, {"tag": "good", "query": "q2"}]})
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)
    seen = []

    def one_sided(client, con, search, *a, **k):
        seen.append(search["tag"])
        if search["tag"] == "bad":
            raise ValueError("malformed page")
        return True

    monkeypatch.setattr(vw, "poll_search", one_sided)
    assert vw.run_cycle() == 0
    assert seen == ["bad", "good"], "the second search was never reached"


# ------------------------- 2026-09-08: the real posting time, and young + liked
#
# The owner asked whether likes-per-time-since-posted would help as a criterion.
# It does not as a ratio: the bot polls newest_first every five minutes, so the
# denominator is a draw from the poll interval (median 3.18 min over 33,231 live
# rows), not a market fact, and 64% of alert candidates carry zero hearts anyway.
# What the question uncovered is that the bot had no idea how old a listing
# really was: listing_age_min measures time since WE saw it and was 0.0 on every
# single alert, while 7 of 107 alerts were on listings 3.8 hours to 5.05 days
# old, four of them ringing. The photo URL carries the upload epoch, already
# stored on every row. The owner's rule: young AND already liked should ring.

def test_the_posting_time_is_read_off_the_photo_url(vw):
    now = datetime.now(timezone.utc)
    epoch = int((now - timedelta(minutes=7)).timestamp())
    url = f"https://images1.vinted.net/t/02_00a50_Bx/f800/{epoch}.jpeg?s=abc"
    posted = vw.posted_at_of(url)
    assert posted is not None
    assert 6.0 <= vw.post_age_min(posted) <= 8.0


def test_the_revision_segment_some_urls_carry_is_not_a_parse_failure(vw):
    """171 of 35,393 production rows have /r1/ or /r3/ before the epoch."""
    now = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
    assert vw.posted_at_of(f"https://images1.vinted.net/t/06_00/f800/r3/{now}.jpeg") is not None
    assert vw.posted_at_of(f"https://images1.vinted.net/t/06_00/f200/{now}.jpg") is not None


def test_an_implausible_epoch_is_refused_rather_than_believed(vw):
    assert vw.posted_at_of(None) is None
    assert vw.posted_at_of("https://images1.vinted.net/t/06_00/f800/nope.jpeg") is None
    future = int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())
    assert vw.posted_at_of(f"https://images1.vinted.net/t/06_00/f800/{future}.jpeg") is None
    assert vw.posted_at_of("https://images1.vinted.net/t/06_00/f800/0000000001.jpeg") is None
    assert vw.post_age_min(None) is None


def test_the_posting_time_is_backfilled_over_the_whole_history(vw, paths):
    """It is retroactive: the photo URL was stored from the very first row."""
    con = vw.db_connect()
    con.execute("ALTER TABLE listings DROP COLUMN posted_at")
    epoch = int((datetime.now(timezone.utc) - timedelta(hours=5)).timestamp())
    con.execute("INSERT INTO listings (id, search_tag, photo_url) VALUES (1, 't', ?)",
                (f"https://images1.vinted.net/t/02_00/f800/{epoch}.jpeg",))
    con.execute("DELETE FROM meta WHERE k='backfill:posted_at'")
    con.commit()
    con.close()
    con = vw.db_connect()
    filled = con.execute("SELECT posted_at FROM listings WHERE id=1").fetchone()[0]
    assert filled is not None, "the backfill did not run"
    assert 290 < vw.post_age_min(filled) < 310
    con.close()


def test_hearts_on_a_young_listing_lift_the_score(vw):
    base = dict(discount_pct=60.0, margin_eur=20.0, fake=0.0, country="DE",
                size_ok_core=True, prof=None)
    cold = vw.alert_quality(**base, fresh_likes=0)
    one = vw.alert_quality(**base, fresh_likes=1)
    many = vw.alert_quality(**base, fresh_likes=5)
    assert cold < one < many, "more hearts on a young post must score higher"
    assert many == pytest.approx(cold * (1 + vw.FRESH_LIKE_WEIGHT))


def test_the_heart_boost_is_capped_so_one_viral_listing_cannot_own_the_channel(vw):
    base = dict(discount_pct=60.0, margin_eur=20.0, fake=0.0, country="DE",
                size_ok_core=True, prof=None)
    assert vw.alert_quality(**base, fresh_likes=5) == vw.alert_quality(**base, fresh_likes=247)


def test_hearts_never_rescue_a_candidate_a_named_gate_refused(vw):
    """The owner's frame: his criteria are the backbone, signals rank within it."""
    hot = dict(discount_pct=60.0, margin_eur=20.0, country="DE",
               size_ok_core=True, prof=None)
    assert vw.alert_priority(fake=0.5, **{k: v for k, v in hot.items()
                                          if k != "margin_eur"},
                             margin_eur=20.0, fresh_likes=5) == 2, \
        "a fake-flagged listing must stay quiet however many hearts it has"


def _deal_settings():
    return {"deal_ratio": 0.55, "min_comps": 5, "comp_window_days": 45,
            "min_price": 5, "size_classes": ["m"], "min_margin": 0,
            "foreign_advantage_eur": 8, "fake_risk_suppress": 0.7,
            "fake_risk_flag": 0.4, "profile_suppress": 0.15, "profile_min_rated": 8}


def test_a_young_liked_listing_outranks_an_identical_cold_one(vw, con, paths, monkeypatch):
    """End to end through score_and_alert: same deal, hearts decide the priority."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    sent = []
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.append(k) or True)
    settings = _deal_settings()
    fresh = int(datetime.now(timezone.utc).timestamp()) - 120
    photo = f"https://images1.vinted.net/t/02_00/f800/{fresh}.jpeg"

    def candidate(listing_id, favourites):
        return {"id": listing_id, "search_tag": "t", "title": "Carhartt Jacke",
                "brand": "Carhartt", "brand_norm": "carhartt", "size": "M",
                "size_class": "m", "condition": "Sehr gut", "cond_tier": "very_good",
                "garment_class": "jacket", "is_kid": 0, "country": "DE",
                "price": 18.0, "total_price": 20.0, "currency": "EUR",
                "url": "u", "photo_url": photo, "posted_at": vw.posted_at_of(photo),
                "seller_id": 1, "seller_login": "s", "favourites": favourites,
                "views": 0, "promoted": 0, "seed": 0}

    for lid, favs in ((5001, 0), (5002, 4)):
        rec = candidate(lid, favs)
        vw.upsert(con, rec)
        assert vw.score_and_alert(con, rec, {"tag": "t", "query": "q"}, settings, {})
    cold, liked = con.execute(
        "SELECT quality FROM alerts WHERE listing_id IN (5001,5002) ORDER BY listing_id"
    ).fetchall()
    assert liked[0] > cold[0], "hearts on a fresh listing did not lift the score"
    assert "4 Herzen" in sent[1]["message"] and "frisch und schon gefragt" in sent[1]["message"]
    assert "Herzen" not in sent[0]["message"]


def test_hearts_on_a_stale_listing_do_not_count_as_demand(vw, con, paths, monkeypatch):
    """The counterweight: the same hearts, five days later, mean the opposite."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    sent = []
    monkeypatch.setattr(vw, "notify", lambda *a, **k: sent.append(k) or True)
    old = int((datetime.now(timezone.utc) - timedelta(days=5)).timestamp())
    photo = f"https://images1.vinted.net/t/02_00/f800/{old}.jpeg"
    rec = {"id": 5003, "search_tag": "t", "title": "Carhartt Jacke",
           "brand": "Carhartt", "brand_norm": "carhartt", "size": "M",
           "size_class": "m", "condition": "Sehr gut", "cond_tier": "very_good",
           "garment_class": "jacket", "is_kid": 0, "country": "DE",
           "price": 18.0, "total_price": 20.0, "currency": "EUR", "url": "u",
           "photo_url": photo, "posted_at": vw.posted_at_of(photo),
           "seller_id": 1, "seller_login": "s", "favourites": 4, "views": 0,
           "promoted": 0, "seed": 0}
    vw.upsert(con, rec)
    assert vw.score_and_alert(con, rec, {"tag": "t", "query": "q"}, _deal_settings(), {})
    assert "frisch und schon gefragt" not in sent[0]["message"]
    assert "seit 5.0 Tagen online" in sent[0]["message"], sent[0]["message"]
    q = con.execute("SELECT quality FROM alerts WHERE listing_id=5003").fetchone()[0]
    cold = vw.alert_quality(50.0, 20.0, 0.0, "DE", True, None, fresh_likes=0)
    assert q == pytest.approx(cold), "a stale listing was boosted by its hearts"


def test_the_first_favourite_reading_is_frozen_against_later_overwrites(vw, con, paths):
    """Without a frozen first point there is no second point to measure against."""
    rec = {"id": 6001, "search_tag": "t", "title": "x", "brand": "Carhartt",
           "brand_norm": "carhartt", "size": "M", "size_class": "m",
           "condition": "Sehr gut", "cond_tier": "very_good", "garment_class": "jacket",
           "is_kid": 0, "country": "DE", "price": 10.0, "total_price": 11.0,
           "currency": "EUR", "url": "u", "photo_url": None, "posted_at": None,
           "seller_id": 1, "seller_login": "s", "favourites": 2, "views": 0,
           "promoted": 0, "seed": 0}
    assert vw.upsert(con, rec) is True
    rec["favourites"] = 19
    assert vw.upsert(con, rec) is False
    row = con.execute("SELECT favourites, fav_first FROM listings WHERE id=6001").fetchone()
    assert row == (19, 2), "the first reading must survive every re-sight"


def test_the_alert_snapshot_keeps_the_posting_time(vw, paths):
    con = vw.db_connect()
    rowid = vw.record_alert(con, {"id": 7, "search_tag": "t"},
                            {"posted_at": "2026-09-08T10:00:00Z", "sent": 1})
    assert con.execute("SELECT posted_at FROM alerts WHERE id=?",
                       (rowid,)).fetchone()[0] == "2026-09-08T10:00:00Z"
    con.close()


# ------------------------------ 2026-09-09: the phone went quiet at the quota
#
# The relative bar capped how many alerts could make a SOUND and let everything
# below it through silently, on the reasoning that volume should stay where the
# owner set it. It did not: he asked for roughly 50 a day and got 319, which
# only became visible once the alerts table started recording the evening
# before. ntfy counts every message against a daily quota whatever its
# priority, so at 16:40Z the free tier answered 429 and the phone stayed silent
# for the rest of the day, dropping the good alerts along with the filler. And
# notify() returned False on a non-200 without logging, so 24 refusals left no
# trace anywhere.

def _seed_candidates(con, vw, qualities, sent=1):
    now = vw.now_iso()
    for i, q in enumerate(qualities):
        con.execute(
            "INSERT INTO alerts (listing_id, alerted_at, search_tag, quality, sent)"
            " VALUES (?,?,'t',?,?)", (800000 + i, now, q, sent))
    con.commit()


def test_a_candidate_outside_the_days_send_budget_is_not_pushed(vw, con, paths):
    _seed_candidates(con, vw, [200.0] * (vw.SEND_BUDGET_PER_DAY + 5))
    assert vw.alert_priority(40.0, 0.0, "DE", True, None, con=con, margin_eur=5.0) == 0


def test_the_best_of_the_day_still_rings(vw, con, paths):
    _seed_candidates(con, vw, [10.0] * (vw.SEND_BUDGET_PER_DAY + 5))
    assert vw.alert_priority(70.0, 0.0, "DE", True, None, con=con, margin_eur=60.0) == 5


def test_the_middle_of_the_day_arrives_without_ringing(vw, con, paths):
    """15 loud, 60 sent: a candidate between the two bars must still arrive."""
    qs = [500.0] * vw.RING_BUDGET_PER_DAY + [1.0] * (vw.SEND_BUDGET_PER_DAY + 5)
    _seed_candidates(con, vw, qs)
    assert vw.alert_priority(40.0, 0.0, "DE", True, None, con=con, margin_eur=5.0) == 3


def test_the_baseline_counts_every_scored_candidate_not_only_the_sent_ones(vw, con, paths):
    """Ranking against sent-only would ratchet the cap open again.

    Once the tail stops being sent, the worst SENT alert becomes the bar to
    beat. The bar collapses toward the best of a shrinking set and the cap
    stops capping, which is the failure this whole change exists to prevent.
    """
    _seed_candidates(con, vw, [200.0] * (vw.SEND_BUDGET_PER_DAY + 5), sent=0)
    assert vw.alert_priority(40.0, 0.0, "DE", True, None, con=con, margin_eur=5.0) == 0, \
        "unsent candidates were ignored, so the budget did not bind"


def test_a_cold_start_is_generous_rather_than_silent(vw, con, paths):
    _seed_candidates(con, vw, [500.0] * 3)
    assert vw.alert_priority(70.0, 0.0, "DE", True, None, con=con, margin_eur=60.0) > 0
    assert vw.alert_priority(10.0, 0.0, "DE", True, None, con=None, margin_eur=1.0) > 0


def test_a_flagged_listing_still_never_interrupts(vw, con, paths):
    qs = [1.0] * (vw.SEND_BUDGET_PER_DAY + 5)
    _seed_candidates(con, vw, qs)
    assert vw.alert_priority(70.0, 0.5, "DE", True, None, con=con, margin_eur=60.0) == 2


def test_a_withheld_candidate_is_still_recorded_with_its_score(vw, con, paths, monkeypatch):
    """The backtest needs the whole candidate stream, not just what was pushed."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    _seed_candidates(con, vw, [9999.0] * (vw.SEND_BUDGET_PER_DAY + 5))
    monkeypatch.setattr(vw, "notify", lambda *a, **k: pytest.fail("must not push"))
    rec = {"id": 7101, "search_tag": "t", "title": "Carhartt Jacke", "brand": "Carhartt",
           "brand_norm": "carhartt", "size": "M", "size_class": "m",
           "condition": "Sehr gut", "cond_tier": "very_good", "garment_class": "jacket",
           "is_kid": 0, "country": "DE", "price": 18.0, "total_price": 20.0,
           "currency": "EUR", "url": "u", "photo_url": None, "posted_at": None,
           "seller_id": 1, "seller_login": "s", "favourites": 0, "views": 0,
           "promoted": 0, "seed": 0}
    vw.upsert(con, rec)
    settings = {"deal_ratio": 0.55, "min_comps": 5, "comp_window_days": 45,
                "min_price": 5, "size_classes": ["m"], "min_margin": 0,
                "foreign_advantage_eur": 8, "fake_risk_suppress": 0.7,
                "fake_risk_flag": 0.4, "profile_suppress": 0.15, "profile_min_rated": 8}
    assert vw.score_and_alert(con, rec, {"tag": "t", "query": "q"}, settings, {}) is False
    row = con.execute("SELECT sent, suppress_reason, quality FROM alerts"
                      " WHERE listing_id=7101").fetchone()
    assert row[0] == 0 and row[1] == "send_budget"
    assert row[2] is not None, "a withheld candidate must keep its score"


class _Refusal:
    """An ntfy error response, body and all."""

    def __init__(self, status=429, code=None, error="limit reached: daily message quota reached"):
        self.status_code = status
        self._payload = {"code": code, "error": error} if code else {"error": error}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


def test_ntfy_refusing_the_push_is_logged_with_status_and_body(vw, monkeypatch, capsys, paths):
    """Neither half is optional.

    The status alone left "daily quota" a plausible guess rather than a fact
    for two days, because a short-window rate limit and an exhausted day share
    HTTP 429 and only the body tells them apart.
    """
    monkeypatch.setattr(vw.httpx, "post",
                        lambda *a, **k: _Refusal(code=vw.NTFY_DAILY_LIMIT_CODE))
    assert vw.notify({"NTFY_TOPIC": "t"}, "title", "msg") is False
    out = capsys.readouterr().out
    assert "429" in out
    assert str(vw.NTFY_DAILY_LIMIT_CODE) in out, "the ntfy error code must be logged"
    assert "daily message quota reached" in out, "the body must be logged verbatim"


def test_the_daily_quota_code_stops_further_sends_until_the_rollover(vw, con, paths, monkeypatch):
    """147 messages were thrown at a closed door over four hours on 2026-09-09.

    Nothing remembered the first refusal, so every cycle re-learned it. Code
    42908 means the day is over at ntfy's end; the latch runs to the UTC
    rollover, because ntfy's day is UTC rather than the operator's.
    """
    posts = []
    monkeypatch.setattr(vw.httpx, "post",
                        lambda *a, **k: posts.append(1) or _Refusal(code=vw.NTFY_DAILY_LIMIT_CODE))
    assert vw.notify({"NTFY_TOPIC": "t"}, "title", "msg", con=con) is False
    assert len(posts) == 1
    assert vw.ntfy_quota_blocked(con) is True
    assert vw.notify({"NTFY_TOPIC": "t"}, "title", "msg", con=con) is False
    assert len(posts) == 1, "a second send was attempted against a known-closed quota"
    until = vw.parse_ts(vw.meta_get(con, vw.NTFY_QUOTA_KEY))
    assert until.hour == 0 and until.minute == 0
    assert until > datetime.now(timezone.utc)


def test_a_momentary_rate_limit_does_not_latch_the_day(vw, con, paths, monkeypatch):
    """429 is also the short-window limit, which clears in seconds. Latching on
    it would silence a whole day for a hiccup."""
    monkeypatch.setattr(vw.httpx, "post", lambda *a, **k: _Refusal(code=42901,
                                                                   error="limit reached: 60 per hour"))
    assert vw.notify({"NTFY_TOPIC": "t"}, "title", "msg", con=con) is False
    assert vw.ntfy_quota_blocked(con) is False
    # And a refusal with no readable code must not latch either.
    monkeypatch.setattr(vw.httpx, "post", lambda *a, **k: _Refusal(status=503, error="oops"))
    assert vw.notify({"NTFY_TOPIC": "t"}, "title", "msg", con=con) is False
    assert vw.ntfy_quota_blocked(con) is False


def test_a_held_candidate_is_recorded_as_held_not_as_a_failed_push(vw, con, paths, monkeypatch):
    """A refusal by ntfy and a hold by us are different facts about a candidate,
    and the backtest reads both out of this one column."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: pytest.fail("sent into a closed quota"))
    _comps(con, vw, n=8, price=40.0)
    vw.meta_set(con, vw.NTFY_QUOTA_KEY,
                (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    assert vw.score_and_alert(con, _rec(vw), {"tag": "t"}, _settings(), {}) is False
    row = con.execute("SELECT suppress_reason, quality FROM alerts").fetchone()
    assert row[0] == "ntfy_quota"
    assert row[1] is not None, "a held candidate keeps its score for the backtest"


# ------------------- 2026-09-10: the catch-up threw away the freshest listings
#
# The machine slept 669 minutes. On waking, every search logged "backlog
# catch-up, alerts suppressed" and scored nothing, on the assumption that a
# pile arriving after a gap is stale. Measured against that exact batch, the
# assumption is backwards: of 456 listings collected, 48.9% were under 15
# minutes old and 76.3% under 45, because page 1 of a catalogue search holds
# the NEWEST 48 items and the real overnight backlog had already scrolled off
# it. The branch was discarding the morning's freshest listings, 223 of them
# under a quarter of an hour old.
#
# The gate needs BOTH a time gap AND more than BACKLOG_SUPPRESS new listings,
# so every case here supplies a full batch; a handful after a gap is steady
# state by design and must stay that way.

def _rec_aged(vw, listing_id, minutes, **over):
    epoch = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
    photo = f"https://images1.vinted.net/t/02_00/f800/{epoch}.jpeg"
    rec = {"id": listing_id, "search_tag": "t", "title": "Carhartt Jacke",
           "brand": "Carhartt", "brand_norm": "carhartt", "size": "M",
           "size_class": "m", "condition": "Sehr gut", "cond_tier": "very_good",
           "garment_class": "jacket", "is_kid": 0, "country": "DE",
           "price": 18.0, "total_price": 20.0, "currency": "EUR", "url": "u",
           "photo_url": photo, "posted_at": vw.posted_at_of(photo),
           "seller_id": 1, "seller_login": "s", "favourites": 0, "views": 0,
           "promoted": 0, "seed": 0}
    rec.update(over)
    return rec


def _batch(vw, start_id, minutes, n=20, **over):
    return [_rec_aged(vw, start_id + i, minutes, **over) for i in range(n)]


def _drive(vw, con, monkeypatch, recs, gap_hours):
    """Run one poll_search over recs, with last_success gap_hours in the past."""
    when = (datetime.now(timezone.utc) - timedelta(hours=gap_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    vw.meta_set(con, "last_success", when)
    vw.meta_set(con, "seeded:t", when)
    con.commit()
    by_id = {r["id"]: r for r in recs}
    monkeypatch.setattr(vw, "api_get", lambda *a, **k: {"items": [{"id": r["id"]} for r in recs]})
    monkeypatch.setattr(vw, "parse_item", lambda item, tag, seed: by_id[item["id"]])
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)
    # notify returns False so MAX_ALERTS_PER_SEARCH never truncates the loop;
    # what is under test is which candidates got SCORED.
    monkeypatch.setattr(vw, "notify", lambda *a, **k: False)
    scored = []
    real = vw.score_and_alert
    monkeypatch.setattr(vw, "score_and_alert",
                        lambda c, r, *a, **k: (scored.append(r["id"]),
                                               real(c, r, *a, **k))[1])
    settings = {"deal_ratio": 0.55, "min_comps": 5, "comp_window_days": 45,
                "min_price": 5, "poll_per_page": 48, "size_classes": ["m"],
                "min_margin": 0, "foreign_advantage_eur": 8,
                "fake_risk_suppress": 0.7, "fake_risk_flag": 0.4,
                "profile_suppress": 0.15, "profile_min_rated": 8}
    vw.poll_search(None, con, {"tag": "t", "query": "q"}, settings, {})
    return scored


def test_a_fresh_listing_survives_the_catch_up(vw, con, paths, monkeypatch):
    """223 of the 456 real ones were under 15 minutes old and were discarded."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    scored = _drive(vw, con, monkeypatch, _batch(vw, 8100, 3), gap_hours=11)
    assert len(scored) == 20, f"fresh listings were dropped after a gap: {len(scored)}"


def test_a_genuinely_old_listing_is_still_dropped_in_a_catch_up(vw, con, paths, monkeypatch):
    """The counterweight: the branch still exists to drop what really is stale."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    scored = _drive(vw, con, monkeypatch, _batch(vw, 8200, 60 * 9), gap_hours=11)
    assert scored == [], f"a stale batch was scored: {len(scored)}"


def test_the_freshness_line_is_drawn_where_it_was_measured(vw, con, paths, monkeypatch):
    """Either side of CATCH_UP_FRESH_MIN, so the constant is the contract."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    just_inside = vw.CATCH_UP_FRESH_MIN - 5
    just_outside = vw.CATCH_UP_FRESH_MIN + 15
    recs = _batch(vw, 8300, just_inside, n=10) + _batch(vw, 8400, just_outside, n=10)
    scored = _drive(vw, con, monkeypatch, recs, gap_hours=11)
    assert all(i < 8400 for i in scored), f"a listing past the line was scored: {scored}"
    assert len(scored) == 10, f"the fresh half was not fully scored: {len(scored)}"


def test_an_unreadable_age_stays_suppressed_during_a_catch_up(vw, con, paths, monkeypatch):
    """Unknown age is not evidence of freshness; be conservative after a gap."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    recs = _batch(vw, 8500, 3, posted_at=None, photo_url=None)
    assert _drive(vw, con, monkeypatch, recs, gap_hours=11) == []


def test_steady_state_still_scores_everything(vw, con, paths, monkeypatch):
    """No gap means no age filter: the test belongs to the catch-up branch only."""
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    recs = _batch(vw, 8600, 3, n=10) + _batch(vw, 8700, 60 * 9, n=10)
    scored = _drive(vw, con, monkeypatch, recs, gap_hours=0)
    assert len(scored) == 20, f"steady state filtered by age: {len(scored)}"


def test_batch_size_no_longer_decides_anything_after_a_gap(vw, con, paths, monkeypatch):
    """Age decides, at every batch size, in both directions.

    The old rule let a small batch skip the freshness screen entirely, so three
    nine-hour-old listings were scored while forty-nine fresh ones were thrown
    away. Both halves were wrong and both came from counting.
    """
    _comps(con, vw, n=10, price=40.0, brand_norm="carhartt", size_class="m")
    assert _drive(vw, con, monkeypatch, _batch(vw, 8800, 60 * 9, n=3), gap_hours=11) == [], \
        "a small batch of genuinely old listings must still be screened out"
    assert len(_drive(vw, con, monkeypatch, _batch(vw, 8900, 3, n=3), gap_hours=11)) == 3, \
        "a small batch of fresh listings must be scored"
    assert len(_drive(vw, con, monkeypatch, _batch(vw, 9000, 3, n=48), gap_hours=11)) == 48, \
        "a full page of fresh listings must be scored; 48 is the page size"


# ------------------------------- 2026-09-10: optional residential egress proxy
#
# Vinted refuses datacenter IPs at the door: probed from a Fly machine in
# Frankfurt, GET https://www.vinted.de/ answered 403 on the first request,
# before a session could be minted. A cloud move is therefore impossible as-is
# and a residential egress is the only route to a 24/7 host. The switch is
# off by default and its consequences are documented at the config, because it
# converts a polite reader on a home line into evasion of a control Vinted set.
#
# What these tests protect is narrow and mechanical: the default stays absent,
# a configured proxy actually reaches the HTTP client, and credentials in the
# URL never reach the log file.

def test_no_proxy_is_configured_by_default(vw, paths, monkeypatch):
    monkeypatch.setattr(vw, "load_env", lambda: {})
    assert vw.egress_proxy() is None
    monkeypatch.setattr(vw, "load_env", lambda: {"EGRESS_PROXY_URL": ""})
    assert vw.egress_proxy() is None, "an empty value must read as unset"


def test_a_configured_proxy_reaches_the_client(vw, paths, monkeypatch):
    monkeypatch.setattr(vw, "load_env", lambda: {"EGRESS_PROXY_URL": "http://p.example:8080"})
    seen = {}

    class FakeClient:
        def __init__(self, **kw):
            seen.update(kw)

    monkeypatch.setattr(vw.httpx, "Client", FakeClient)
    vw.new_client()
    assert seen.get("proxy") == "http://p.example:8080"


def test_the_client_is_built_without_a_proxy_when_unset(vw, paths, monkeypatch):
    monkeypatch.setattr(vw, "load_env", lambda: {})
    seen = {}

    class FakeClient:
        def __init__(self, **kw):
            seen.update(kw)

    monkeypatch.setattr(vw.httpx, "Client", FakeClient)
    vw.new_client()
    assert seen.get("proxy") is None


def test_proxy_credentials_never_reach_the_log(vw, paths, monkeypatch, capsys):
    """The URL carries a username and password; the log file is on disk."""
    url = "http://sekretuser:sekretpass@resi.example:9000"
    monkeypatch.setattr(vw, "load_env", lambda: {"EGRESS_PROXY_URL": url})
    monkeypatch.setattr(vw.httpx, "Client", lambda **kw: object())
    vw.new_client()
    out = capsys.readouterr().out
    assert "resi.example" in out and "9000" in out, "the host should be visible"
    assert "sekretuser" not in out and "sekretpass" not in out
    on_disk = (paths / vw.LOG_NAME).read_text(encoding="utf-8")
    assert "sekretpass" not in on_disk, "the secret was written to the log file"


def test_redaction_survives_odd_urls(vw):
    assert vw.redact_proxy("http://h.example:1080") == "http://h.example:1080"
    assert vw.redact_proxy("socks5://u:p@h.example") == "socks5://<user:pass@>h.example"
    assert "?" in vw.redact_proxy("not a url at all")


# --------------------------------------- 2026-09-10: volume had no instrument
#
# The collapse from ~180 pushes a day to 9 ran two days before anyone saw it.
# The alerts table held the whole story and nothing read it out, so the first
# signal was the owner noticing that his phone had gone quiet. These are the
# instruments that make the next one visible within one cycle.

def test_the_cycle_logs_what_the_send_path_is_doing(vw, con, paths):
    """Four numbers, and the pool size is the one that cannot be recovered later.

    The alerts table records what each decision WAS; only this line records
    what it was measured against, which is the half that broke.
    """
    _fill_day(vw, con, 30, quality=100.0, sent=1)
    line = vw.log_volume(con)
    assert "pool_n=30" in line
    assert "send_bar=" in line and "ring_bar=" in line
    assert "pushes_today=30" in line
    on_disk = (paths / vw.LOG_NAME).read_text(encoding="utf-8")
    assert "pool_n=30" in on_disk, "the headless run writes to the file, not stdout"


def test_the_cycle_line_says_so_when_the_day_is_still_cold(vw, con, paths):
    """An empty morning has no bars, and printing 0.0 would read as a bar of zero."""
    line = vw.log_volume(con)
    assert "pool_n=0" in line and "cold start" in line


def test_a_real_cycle_emits_the_volume_line(vw, paths, monkeypatch, capsys):
    """The instrument has to be WIRED, not merely present.

    A helper the cycle never calls is exactly the shape of the failure this
    whole change is about: the alerts table could always have answered "how
    many pushes today" and nothing ever asked it.
    """
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200, headers={
                "set-cookie": f"access_token_web={make_jwt(12)}; Path=/"})
        return httpx.Response(200, json={"items": []})

    monkeypatch.setattr(vw, "new_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(handler),
                                             base_url=vw.BASE))
    monkeypatch.setattr(vw, "load_env", lambda: {})
    monkeypatch.setattr(vw, "load_config", lambda: {
        "settings": {"deal_ratio": 0.55, "min_comps": 1, "comp_window_days": 45,
                     "min_price": 5, "poll_per_page": 48, "seed_pages": 1,
                     "seed_per_page": 10, "size_classes": ["m"], "min_margin": 0,
                     "foreign_advantage_eur": 8, "fake_risk_suppress": 0.7,
                     "fake_risk_flag": 0.4, "profile_suppress": 0.15,
                     "profile_min_rated": 8},
        "searches": [{"tag": "t", "query": "q", "price_max": 100}]})
    monkeypatch.setattr(vw.time, "sleep", lambda *_: None)
    con = vw.db_connect()
    vw.meta_set(con, "seeded:t", vw.now_iso())
    con.commit()
    con.close()
    vw.LOCK_PATH.unlink(missing_ok=True)

    vw.run_cycle()
    assert "volume: pool_n=" in capsys.readouterr().out, \
        "a cycle ran without reporting its volume"


def test_status_reports_yesterday_and_the_weekly_mean(vw, con, paths, capsys):
    """The number the owner would have looked at, had it existed."""
    today = datetime.now(timezone.utc).astimezone()
    for back, n, loud in ((0, 3, 1), (1, 12, 4), (2, 9, 2)):
        when = (today - timedelta(days=back)).replace(hour=12, minute=0, second=0, microsecond=0)
        stamp = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(n):
            con.execute(
                "INSERT INTO alerts (listing_id, alerted_at, search_tag, sent, priority)"
                " VALUES (?,?,'t',1,?)", (50000 + back * 100 + i, stamp, 5 if i < loud else 3))
    con.commit()
    counts = vw.daily_push_counts(con, days=8)
    assert counts[0] == (today.strftime("%Y-%m-%d"), 3, 1)
    assert counts[1][1:] == (12, 4)
    assert counts[2][1:] == (9, 2)
    assert sum(c[1] for c in counts[3:]) == 0, "days with no alerts read zero, not vanish"
    vw.print_status()
    out = capsys.readouterr().out
    assert "pushes: heute 3 (1 laut)" in out
    assert "gestern 12 (4 laut)" in out
    assert "Schnitt 7 Tage 3.0" in out


def test_status_names_an_active_ntfy_send_hold(vw, con, paths, capsys):
    """A silent phone with a healthy watcher has exactly one other explanation."""
    vw.meta_set(con, vw.NTFY_QUOTA_KEY,
                (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    vw.print_status()
    assert "Sendesperre" in capsys.readouterr().out
