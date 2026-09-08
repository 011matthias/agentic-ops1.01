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
    """Shipping from abroad is not in the comp median, so the bar moves."""
    monkeypatch.setattr(vw, "notify", lambda *a, **k: True)
    _comps(con, vw, n=8, price=40.0)
    # Bar is 0.55 * 40 = 22. A 21 EUR Italian listing clears the plain gate but
    # not the gate plus 8 EUR of headroom.
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0, country="IT"), {"tag": "t"},
                              _settings(), {}) is False
    assert con.execute("SELECT suppress_reason FROM alerts").fetchone()[0] == "country"
    assert vw.score_and_alert(con, _rec(vw, id=998, total_price=13.0, country="IT"),
                              {"tag": "t"}, _settings(), {}) is True


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
            " margin_eur, quality, sent) VALUES (?,?,'t',?,?,?,1)",
            (7000 + i, now, d, m, vw.alert_quality(d, m, 0.0, 'DE', True, None)))
    con.commit()
    rings = sum(1 for d, m in scores
                if vw.alert_priority(d, 0.0, "DE", True, None, con=con, margin_eur=m) == 5)
    # Out of 400 candidates in one day, only a small head should ring.
    assert rings <= 60, f"{rings} of 400 would ring; the bar is not holding"
    assert rings >= 1, "the bar must not silence everything either"

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
    # 21 EUR clears the plain 0.55 x 40 gate but not the foreign headroom.
    assert vw.score_and_alert(con, _rec(vw, total_price=21.0), {"tag": "t"},
                              _settings(), {}, client=client, seller_budget=[3]) is False
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
    assert vw.is_catch_up(con, 40) is False
    assert vw.is_catch_up(con, 48) is False


def test_a_real_gap_still_suppresses_a_pile(vw, con, paths):
    """After hours offline the listings are stale and racing for them wins nothing."""
    vw.meta_set(con, "last_success",
                (datetime.now(timezone.utc) - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    con.commit()
    assert vw.is_catch_up(con, 40) is True
    # A gap with only a trickle behind it is not a backlog either.
    assert vw.is_catch_up(con, 3) is False


def test_without_a_success_record_a_large_batch_is_treated_as_stale(vw, con, paths):
    """A fresh database has no age information, so it errs toward silence."""
    assert vw.meta_get(con, "last_success") is None
    assert vw.is_catch_up(con, 40) is True
    assert vw.is_catch_up(con, 2) is False


def test_a_corrupt_success_stamp_does_not_wedge_the_gate(vw, con, paths):
    """parse_ts never raises, and the gate must degrade to the old rule."""
    vw.meta_set(con, "last_success", "not-a-timestamp")
    con.commit()
    assert vw.is_catch_up(con, 40) is True
    assert vw.is_catch_up(con, 2) is False

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
