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
    """The guard must not suppress real, partial turnover."""
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(10):
        _seed_listing(con, i, f"{vw.BASE}/items/{i}-thing", old)

    def handler(request):
        idx = int(str(request.url).rsplit("/", 1)[1].split("-")[0])
        if idx < 3:
            return httpx.Response(404, text="gone")
        return httpx.Response(200, text="<html>still listed</html>")

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
                        lambda env, title, message, click=None, priority=4: sent.append(title) or True)

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
            "INSERT INTO listings (id, search_tag, brand, cond_tier, garment_class, is_kid,"
            " total_price, last_seen) VALUES (?,'t','Patagonia','very_good','jacket',0,40.0,?)",
            (100 + i, now))
    for i in range(8):                      # kids noise around 10 EUR
        con.execute(
            "INSERT INTO listings (id, search_tag, brand, cond_tier, garment_class, is_kid,"
            " total_price, last_seen) VALUES (?,'t','Patagonia','very_good','jacket',1,10.0,?)",
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
