"""Feedback note #79 (owner 2026-09-23, anchored on Settings > FX reference
rates): "fx rates should be polled daily via open tickers API".

The app polls OpenTickers for the daily central-bank reference rates (ECB
preferred), stores them as units per EUR by day, refreshes every month's
`matching.fx_daily_rates` from the store on each re-match, and the matcher
reads the rate for the CHARGE's own day one rung above the ECB monthly
average. A rate typed in Settings still wins (owner rulings 2026-09-16 and
09-17). The routes below run against a stubbed provider whose records are
shaped exactly as the live API answered on 2026-09-23.
"""
from __future__ import annotations

import io
import time
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.deterministic import (  # noqa: E402
    MatchingConfig,
    _reference_rate_for,
)
from expense_recon.web import ecb_rates, fx_daily_rates  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The ECB monthly averages the item-82 rung would use, so the routes prove
# the daily rung sits ABOVE it when both are present.
ECB = {
    "2026-06": {"USD": "1.1518", "BRL": "5.898918181818181"},
    "2026-07": {"USD": "1.1417478260869562", "BRL": "5.844895652173915"},
    "2026-08": {"USD": "1.1593095238095241", "BRL": "5.968409523809523"},
}


def _rec(day, ccy, value, source="ECB", **kw):
    """One provider record, the live shape (2026-09-23)."""
    rec = {
        "id": f"EUR_{ccy}_MID", "effectiveDate": day, "sourceCode": source,
        "baseCurrency": "EUR", "quoteCurrency": ccy, "type": "mid",
        "value": value, "scalingFactor": 1, "createdAt": f"{day}T14:00:13.918Z",
        "externalId": f"D.{ccy}.EUR.SP00.A" if source == "ECB" else None,
    }
    rec.update(kw)
    return rec


# Daily ECB fixes around July 2026. No fix on 07-04/05 (weekend) and none on
# 07-09, so the SUPERMEC charge (07-09) reads the nearest day: 07-08 and
# 07-10 tie at one day and the earlier wins. 07-01 has no ECB record, only
# three other sources, so its rate is their median.
HISTORY = {
    "USD": [
        _rec("2026-06-29", "USD", 1.1520), _rec("2026-06-30", "USD", 1.1518),
        _rec("2026-07-01", "USD", 1.1440, "BDI"), _rec("2026-07-01", "USD", 1.1450, "BPT"),
        _rec("2026-07-01", "USD", 1.1420, "BCCR"),
        _rec("2026-07-02", "USD", 1.1430), _rec("2026-07-02", "USD", 1.1428, "BCCR"),
        _rec("2026-07-03", "USD", 1.1435), _rec("2026-07-06", "USD", 1.1410),
        _rec("2026-07-07", "USD", 1.1405), _rec("2026-07-08", "USD", 1.1400),
        _rec("2026-07-10", "USD", 1.1390),
    ],
    "BRL": [
        _rec("2026-06-29", "BRL", 5.9000), _rec("2026-06-30", "BRL", 5.8990),
        _rec("2026-07-01", "BRL", 5.8600, "BDI"),
        _rec("2026-07-02", "BRL", 5.8450), _rec("2026-07-03", "BRL", 5.8400),
        _rec("2026-07-06", "BRL", 5.8350), _rec("2026-07-07", "BRL", 5.8320),
        _rec("2026-07-08", "BRL", 5.8300), _rec("2026-07-10", "BRL", 5.8250),
    ],
}
LATEST = {
    "USD": [
        _rec("2026-09-22", "USD", 1.1458, "BCCR"), _rec("2026-09-22", "USD", 1.1463, "BDI"),
        _rec("2026-09-22", "USD", 1.1463, "BPT"), _rec("2026-09-22", "USD", 1.1463),
    ],
    "BRL": [_rec("2026-09-22", "BRL", 5.8726)],
}


class _OpenTickers:
    """A stand-in for the provider: answers HISTORY / LATEST per currency,
    records every call, and can be taken down or made to refuse history."""

    def __init__(self) -> None:
        self.latest_calls: list[str] = []
        self.history_calls: list[tuple[str, str, str]] = []
        self.down = False
        self.history_refused = False

    def latest(self, currency: str, **kw) -> list[dict]:
        self.latest_calls.append(currency)
        if self.down:
            raise OSError("OpenTickers unreachable")
        return [dict(r) for r in LATEST.get(currency, [])]

    def historical(self, currency: str, start: str, end: str, **kw) -> list[dict]:
        self.history_calls.append((currency, start, end))
        if self.down:
            raise OSError("OpenTickers unreachable")
        if self.history_refused:
            raise fx_daily_rates.HistoryRefused("plan")
        return [dict(r) for r in HISTORY.get(currency, []) if start <= r["effectiveDate"] <= end]


class _Ecb:
    def __call__(self, start: str, end: str, **kw) -> dict:
        return {m: dict(v) for m, v in ECB.items() if start <= m <= end}


@pytest.fixture
def ot(monkeypatch):
    stub = _OpenTickers()
    monkeypatch.setenv("OPENTICKERS_API_KEY", "test-key")
    monkeypatch.delenv("EXPENSE_RECON_FX_POLL", raising=False)
    monkeypatch.setattr(fx_daily_rates, "fetch_latest", stub.latest)
    monkeypatch.setattr(fx_daily_rates, "fetch_historical", stub.historical)
    monkeypatch.setattr(ecb_rates, "fetch_monthly", _Ecb())
    return stub


@pytest.fixture
def client(tmp_path, monkeypatch, ot):
    """The app with the boot poll thread replaced by a no-op, so every test
    decides for itself when a poll runs (the thread has its own test)."""
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(fx_daily_rates, "start_poll_thread", lambda *a, **k: None)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        c._app = app
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _settings(client, rates: dict | None = None) -> None:
    body = {
        "entities": {"Corporate Services": {}},
        "cards": {
            "corp-2838": {
                "label": "Corporate card (Chase)", "digits": ["2838"],
                "entity": "Corporate Services", "currency": "USD",
            },
        },
    }
    if rates is not None:
        body["fx_reference_rates"] = rates
    resp = client.put("/api/settings", json=body)
    assert resp.status_code == 200, resp.text


def _create_july(client, monkeypatch) -> str:
    """The item-82 July: Amazon.de 276.08 EUR (07-02, charge 315.56 USD),
    Supermercado Sao Jose 41.85 BRL (07-09, charge 8.29), Supermercado
    Fenix 55.74 BRL (06-30, charge 10.82 on the July statement)."""
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-07-02", total="276.08", currency="EUR",
                vendor="Amazon.de", reference="AMZ-302-1",
                line_items=(), confidence=0.9, notes="",
            ),
            ExtractedReceipt(
                date="2026-07-09", total="41.85", currency="BRL",
                vendor="Supermercado Sao Jose", reference="SSJ-0709",
                line_items=(), confidence=0.9, notes="",
            ),
            ExtractedReceipt(
                date="2026-06-30", total="55.74", currency="BRL",
                vendor="Supermercado Fenix", reference="FNX-0630",
                line_items=(), confidence=0.9, notes="",
            ),
        ],
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "July 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + str(i).encode(), "application/octet-stream"))
            for i, name in enumerate(["Amazon.jpg", "Supermec.jpg", "Fenix.jpg"])
        ],
    ))
    return batch_id


def _attach_statement(client, batch_id: str) -> None:
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("July2026.xlsx", _xlsx_bytes([
            (datetime(2026, 6, 30), "SUPERMERCADO FENIX", "Sale", -10.82),
            (datetime(2026, 7, 2), "AMAZON* Z11US7DF5", "Sale", -315.56),
            (datetime(2026, 7, 9), "SUPERMEC SAO JOSE", "Sale", -8.29),
        ]), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _config(client, batch_id: str) -> dict:
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        return store.get_run(batch_id).config or {}
    finally:
        store.close()


def _row(view: dict, vendor: str) -> dict:
    return next(r for r in view["rows"] if vendor in r["vendor"])


def _chosen(row: dict) -> dict:
    return next(c for c in row["candidates"] if c["is_chosen"])


def _poll(client) -> dict:
    resp = client.post("/api/fx/poll")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── routes ────────────────────────────────────────────────────────────────


def test_route_a_month_with_no_typed_rate_matches_on_the_polled_daily_rate(
    client, monkeypatch, ot
):
    """No rate in Settings, the ECB monthly table present, the daily table
    polled: every pair reads the daily rate for the CHARGE's day, names its
    source and day, and the ECB average is never reached. Note #43's pair
    reads 276.08 EUR x 1.143 = 315.56 USD, 0.00, where July's ECB average
    printed +0.35 and the old Settings rate -5.32."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    _poll(client)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "AMAZON"))
    assert chosen["match_type"] == "fx_reference", chosen
    fx = chosen["fx"]
    assert Decimal(fx["reference_rate"]) == Decimal("1.143")
    assert fx["reference_rate_source"] == "opentickers_day"
    assert fx["reference_rate_period"] == "2026-07-02"
    assert fx["reference_converted"] == "315.56"
    assert fx["reference_gap"] == "0.00"
    assert fx["reference_gap_band"] == "match"
    assert "OpenTickers daily reference rate" in chosen["reason"], chosen["reason"]
    assert "2026-07-02" in chosen["reason"]

    # 06-30 Fenix: the June day, not the month's label
    fx = _chosen(_row(view, "FENIX"))["fx"]
    assert fx["reference_rate_source"] == "opentickers_day"
    assert fx["reference_rate_period"] == "2026-06-30"
    assert fx["reference_rate"] == "0.195253"  # 1.1518 / 5.8990
    assert fx["reference_converted"] == "10.88"

    matching = _config(client, batch_id)["matching"]
    assert "2026-07-02" in matching["fx_daily_rates"]
    assert matching["fx_daily_rates"]["2026-07-02"] == {"USD": "1.143", "BRL": "5.845"}
    assert set(matching["fx_ecb_monthly_rates"]) == {"2026-06", "2026-07", "2026-08"}


def test_route_a_charge_on_a_day_with_no_fix_reads_the_nearest_day_earlier_on_a_tie(
    client, monkeypatch, ot
):
    """SUPERMEC is charged 07-09, a day the provider has no fix for; 07-08
    and 07-10 both sit one day away and the earlier wins: 41.85 BRL x
    (1.1400 / 5.8300) = 8.18 against 8.29, +1.30%, inside the 2% band the
    daily source shares with the ECB average (`fx_ecb_match_pct`)."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    _poll(client)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "SUPERMEC"))
    fx = chosen["fx"]
    assert fx["reference_rate_source"] == "opentickers_day"
    assert fx["reference_rate_period"] == "2026-07-08"
    assert Decimal(fx["reference_rate"]) == Decimal("0.19554")  # 1.1400 / 5.8300
    assert fx["reference_converted"] == "8.18"
    assert fx["reference_gap_pct"] == 1.3
    assert fx["reference_gap_band"] == "match"
    assert chosen["match_type"] == "fx_reference"


def test_route_a_rate_typed_in_settings_is_ignored_and_the_daily_rate_answers(
    client, monkeypatch, ot
):
    """Owner directive 2026-09-23 retired the typed rates outright, so the
    ruling they used to win under no longer applies: a PUT still carrying
    the key is accepted and ignored, and every pair reads the polled daily
    rate."""
    _settings(client, {"EUR:USD": "1.162275"})
    batch_id = _create_july(client, monkeypatch)
    _poll(client)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    assert "fx_reference_rates" not in client.get("/api/settings").json()
    fx = _chosen(_row(view, "AMAZON"))["fx"]
    assert Decimal(fx["reference_rate"]) == Decimal("1.143")
    assert fx["reference_rate_source"] == "opentickers_day"
    assert fx["reference_rate_period"] == "2026-07-02"
    assert fx["reference_gap"] == "0.00"

    fx = _chosen(_row(view, "SUPERMEC"))["fx"]
    assert fx["reference_rate_source"] == "opentickers_day"


def test_route_a_month_matched_before_any_poll_picks_the_rates_up_on_its_next_rematch(
    client, monkeypatch, ot
):
    """The table is read from the store on every re-match, so a month that
    matched on the ECB average before the first poll reads the daily rates
    the next time anything re-matches it (here: a settings refresh through a
    second statement upload of the same file is not needed; a poll then a
    re-read does it)."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    _attach_statement(client, batch_id)
    before = _chosen(_row(client.get(f"/api/runs/{batch_id}").json(), "AMAZON"))["fx"]
    assert before["reference_rate_source"] == "ecb_month"
    assert "fx_daily_rates" not in _config(client, batch_id)["matching"]

    _poll(client)
    _done(client, client.post(f"/api/expense-batches/{batch_id}/statements/reread"))
    after = _chosen(_row(client.get(f"/api/runs/{batch_id}").json(), "AMAZON"))["fx"]
    assert after["reference_rate_source"] == "opentickers_day"
    assert after["reference_rate_period"] == "2026-07-02"


def test_route_the_poll_backfills_once_then_polls_latest_and_settings_shows_it(
    client, monkeypatch, ot
):
    """The first round asks `/historical` from the month before the earliest
    month (July -> 2026-06-01) to today, then `/latest`, for USD and BRL
    (the defaults; the card is USD). The second round asks `/latest` only.
    `GET /api/settings` carries the derived `fx_daily_rates` block with the
    newest day's rates as units per EUR and as every pair; a PUT that
    carries the key is accepted and ignored, like every derived key."""
    _settings(client)
    _create_july(client, monkeypatch)

    first = _poll(client)
    assert first["ok"] is True, first
    assert first["backfilled_from"] == "2026-06-01"
    assert first["errors"] == []
    today = date.today().isoformat()
    assert sorted(ot.history_calls) == [("BRL", "2026-06-01", today), ("USD", "2026-06-01", today)]
    assert sorted(ot.latest_calls) == ["BRL", "USD"]
    assert first["first_day"] == "2026-06-29"
    assert first["last_day"] == "2026-09-22"
    assert first["currencies"] == ["BRL", "USD"]

    second = _poll(client)
    assert second["backfilled_from"] is None
    assert len(ot.history_calls) == 2
    assert sorted(ot.latest_calls) == ["BRL", "BRL", "USD", "USD"]
    assert second["n_days"] == first["n_days"]

    block = client.get("/api/settings").json()["fx_daily_rates"]
    assert block["provider"] == "opentickers"
    assert block["enabled"] is True
    assert block["poll_interval_hours"] == 24
    assert block["backfilled_from"] == "2026-06-01"
    assert block["history_refused"] is False
    assert block["last_error"] == ""
    assert block["last_fetched_at"]
    assert block["latest"]["day"] == "2026-09-22"
    assert block["latest"]["per_eur"] == {"BRL": "5.8726", "USD": "1.1463"}
    assert block["latest"]["pairs"]["EUR:USD"] == "1.146300"
    assert block["latest"]["pairs"]["BRL:USD"] == "0.195195"  # 1.1463 / 5.8726
    assert block["latest"]["pairs"]["USD:EUR"] == "0.872372"
    assert set(block["latest"]["pairs"]) == {
        "BRL:EUR", "BRL:USD", "EUR:BRL", "EUR:USD", "USD:BRL", "USD:EUR",
    }

    resp = client.put("/api/settings", json={"fx_daily_rates": {"latest": {}}})
    assert resp.status_code == 200, resp.text
    assert "fx_daily_rates" in resp.json().get("ignored", []), resp.json()


def test_route_the_ecb_record_wins_and_a_day_without_one_takes_the_median(
    client, monkeypatch, ot
):
    _settings(client)
    _create_july(client, monkeypatch)
    _poll(client)
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        rows = {
            (r["day"], r["ccy"]): (r["per_eur"], r["source"])
            for r in store.conn.execute(
                "SELECT day, ccy, per_eur, source FROM fx_daily_rates"
            ).fetchall()
        }
    finally:
        store.close()
    assert rows[("2026-07-02", "USD")] == ("1.143", "ECB")
    assert rows[("2026-07-01", "USD")] == ("1.144", "median:BCCR,BDI,BPT")
    assert rows[("2026-09-22", "USD")] == ("1.1463", "ECB")


def test_route_a_provider_outage_never_blocks_a_month(client, monkeypatch, ot):
    """The provider is down: the poll answers 200 with `ok: false` and the
    errors, stores nothing, and the month still attaches and matches on the
    ECB average as before this item."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    ot.down = True
    result = _poll(client)
    assert result["ok"] is False
    assert result["n_stored"] == 0
    assert len(result["errors"]) == 3, result  # history (one try), latest x2
    assert result["n_days"] == 0

    _attach_statement(client, batch_id)
    fx = _chosen(_row(client.get(f"/api/runs/{batch_id}").json(), "AMAZON"))["fx"]
    assert fx["reference_rate_source"] == "ecb_month"
    assert "fx_daily_rates" not in _config(client, batch_id)["matching"]

    block = client.get("/api/settings").json()["fx_daily_rates"]
    assert block["n_days"] == 0
    assert "unreachable" in block["last_error"]
    assert block["latest"] == {}


def test_route_a_plan_that_refuses_history_still_stores_the_latest_day(
    client, monkeypatch, ot
):
    _settings(client)
    _create_july(client, monkeypatch)
    ot.history_refused = True
    result = _poll(client)
    assert result["ok"] is True, result
    assert result["backfilled_from"] is None
    assert result["errors"] and result["errors"][0].startswith("history:")
    assert result["first_day"] == result["last_day"] == "2026-09-22"

    _poll(client)
    assert len(ot.history_calls) == 1  # not asked again once refused
    block = client.get("/api/settings").json()["fx_daily_rates"]
    assert block["history_refused"] is True


def test_route_no_provider_key_means_no_thread_and_a_409(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENTICKERS_API_KEY", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    assert app.state.fx_poll is None
    with TestClient(app) as client:
        resp = client.post("/api/fx/poll")
        assert resp.status_code == 409, resp.text
        assert resp.json()["code"] == "fx_poll_disabled"
        block = client.get("/api/settings").json()["fx_daily_rates"]
        assert block["enabled"] is False
        assert block["n_days"] == 0


def test_the_boot_thread_polls_once_at_start(tmp_path, ot):
    """`start_poll_thread` runs a round at boot: within a few seconds the
    stub has answered latest for both currencies and the store holds them."""
    store = RunStore(tmp_path / "recon-web.sqlite")
    store.close()
    thread = fx_daily_rates.start_poll_thread(
        tmp_path / "recon-web.sqlite", interval_s=3600,
    )
    assert thread is not None and thread.daemon
    deadline = time.time() + 10
    while time.time() < deadline and len(ot.latest_calls) < 2:
        time.sleep(0.05)
    assert sorted(ot.latest_calls) == ["BRL", "USD"]
    deadline = time.time() + 5
    while time.time() < deadline:
        store = RunStore(tmp_path / "recon-web.sqlite")
        try:
            status = store.fx_daily_rates_status()
        finally:
            store.close()
        if status["last_day"] == "2026-09-22":
            break
        time.sleep(0.05)
    assert status["last_day"] == "2026-09-22", status


def test_the_thread_is_off_without_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENTICKERS_API_KEY", raising=False)
    assert fx_daily_rates.start_poll_thread(tmp_path / "x.sqlite") is None
    monkeypatch.setenv("OPENTICKERS_API_KEY", "k")
    monkeypatch.setenv("EXPENSE_RECON_FX_POLL", "0")
    assert fx_daily_rates.start_poll_thread(tmp_path / "x.sqlite") is None


# ── the matcher ───────────────────────────────────────────────────────────


def _cfg(**kw) -> MatchingConfig:
    return MatchingConfig.from_dict({
        "fx_daily_rates": {
            "2026-07-03": {"USD": "1.1435", "BRL": "5.8400"},
            "2026-07-07": {"USD": "1.1405", "BRL": "5.8320"},
        },
        **kw,
    })


def test_the_daily_rate_is_the_cross_through_eur_on_the_charge_day():
    assert _cfg().daily_rate("BRL", "USD", date(2026, 7, 3)) == (Decimal("0.195805"), "2026-07-03")
    assert _cfg().daily_rate("EUR", "USD", "2026-07-07") == (Decimal("1.140500"), "2026-07-07")
    assert _cfg().daily_rate("USD", "EUR", "2026-07-07") == (Decimal("0.876808"), "2026-07-07")


def test_a_day_with_no_fix_reads_the_nearest_inside_the_window_earlier_on_a_tie():
    cfg = _cfg()
    assert cfg.daily_rate("EUR", "USD", date(2026, 7, 4))[1] == "2026-07-03"  # 1 vs 3 days
    assert cfg.daily_rate("EUR", "USD", date(2026, 7, 5))[1] == "2026-07-03"  # 2 vs 2: earlier
    assert cfg.daily_rate("EUR", "USD", date(2026, 7, 6))[1] == "2026-07-07"  # 3 vs 1
    assert cfg.daily_rate("EUR", "USD", date(2026, 7, 11))[1] == "2026-07-07"  # 4: the edge
    assert cfg.daily_rate("EUR", "USD", date(2026, 7, 12)) is None  # 5: outside
    assert cfg.daily_rate("EUR", "USD", "2026-07") is None  # a month is not a day
    assert cfg.daily_rate("EUR", "USD", None) is None
    assert cfg.daily_rate("GBP", "USD", date(2026, 7, 3)) is None  # pair absent
    assert _cfg(fx_daily_rate_max_gap_days=1).daily_rate("EUR", "USD", date(2026, 7, 5)) is None


def test_the_rung_order_is_derived_then_daily_then_ecb():
    cfg = MatchingConfig.from_dict({
        "fx_reference_rates": {"EUR:USD": "1.162275"},
        "fx_daily_rates": {"2026-07-02": {"USD": "1.1430", "BRL": "5.8450"}},
        "fx_ecb_monthly_rates": {"2026-07": {"USD": "1.1417478", "BRL": "5.8448957"}},
    })
    on = date(2026, 7, 2)
    # The typed rate is in the config and is ignored: the daily rate answers.
    assert _reference_rate_for(cfg, "EUR", "USD", None, on=on) == (Decimal("1.143"), "opentickers_day", 0)
    derived = {("BRL", "USD"): (Decimal("0.19"), "statement", 3)}
    assert _reference_rate_for(cfg, "BRL", "USD", derived, on=on) == (Decimal("0.19"), "statement", 3)
    assert _reference_rate_for(cfg, "BRL", "USD", None, on=on) == (Decimal("0.195552"), "opentickers_day", 0)
    # outside the daily window the month average answers
    assert _reference_rate_for(cfg, "BRL", "USD", None, on=date(2026, 7, 20)) == (
        Decimal("0.195341"), "ecb_month", 0,
    )
    # a charge with no date reaches neither
    assert _reference_rate_for(cfg, "BRL", "USD", None, on=None) is None


def test_the_band_for_the_daily_source_is_the_ecb_band():
    cfg = MatchingConfig()
    assert cfg.reference_match_pct("opentickers_day") == cfg.fx_ecb_match_pct
    assert cfg.reference_match_pct("ecb_month") == cfg.fx_ecb_match_pct
    assert cfg.reference_match_pct("configured") == cfg.fx_reference_match_pct


def test_a_malformed_day_key_is_refused():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        MatchingConfig.from_dict({"fx_daily_rates": {"2026-07": {"USD": "1.1"}}})
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        MatchingConfig.from_dict({"fx_daily_rates": {"2026-07-32": {"USD": "1.1"}}})


# ── the table ─────────────────────────────────────────────────────────────


def test_pick_prefers_the_ecb_record_then_the_median_and_skips_what_it_cannot_trust():
    rows = fx_daily_rates.pick(HISTORY["USD"] + [
        _rec("2026-07-02", "USD", 0.87, baseCurrency="USD", quoteCurrency="EUR"),  # other base
        _rec("2026-07-03", "USD", 114.35, scalingFactor=100),  # scaled
        _rec("2026-07-03", "USD", -1.0, "BDI"),  # non-positive
        _rec("2026-07-03", "USD", "n/a", "BPT"),  # not a number
        _rec("2026-7-3", "USD", 1.14),  # malformed day
        _rec("2026-07-03", "usd", 1.14, "XX", type="close"),  # non-mid, non-ECB
        "garbage",
    ])
    table = {(d, c): (v, s) for d, c, v, s in rows}
    assert table[("2026-07-02", "USD")] == ("1.143", "ECB")
    assert table[("2026-07-01", "USD")] == ("1.144", "median:BCCR,BDI,BPT")
    assert table[("2026-07-03", "USD")] == ("1.1435", "ECB")
    assert ("2026-7-3", "USD") not in table
    assert fx_daily_rates.as_table(rows)["2026-07-01"] == {"USD": "1.144"}
    assert fx_daily_rates.pick([]) == []


def test_needed_currencies_grows_with_settings_and_the_months():
    class _Run:
        def __init__(self, cfg):
            self.config = cfg
            self.label = "July 2026"

    assert fx_daily_rates.needed_currencies({}, []) == ["BRL", "USD"]
    assert fx_daily_rates.needed_currencies(
        {"cards": {"c1": {"currency": "jpy"}, "c2": "not a dict"}},
        [_Run({"statement": {"account_card_currency": "cad"}}), _Run({})],
    ) == ["BRL", "CAD", "JPY", "USD"]
    # A retired typed pair names no currency any more (item 168): GBP and
    # CHF used to widen the poll from here and no longer do.
    assert fx_daily_rates.needed_currencies(
        {"fx_reference_rates": {"GBP:USD": "1.3", "eur:chf": "0.9"}}, [],
    ) == ["BRL", "USD"]


def test_backfill_start_is_the_month_before_the_earliest_month():
    class _Run:
        def __init__(self, label):
            self.label = label

    today = date(2026, 9, 23)
    assert fx_daily_rates.backfill_start([_Run("July 2026"), _Run("January 2026")], today) == "2025-12-01"
    assert fx_daily_rates.backfill_start([_Run("a trip")], today) == "2026-06-25"
    assert fx_daily_rates.backfill_start([], today) == "2026-06-25"


def test_the_store_keeps_the_digits_and_replaces_a_day_on_conflict(tmp_path):
    store = RunStore(tmp_path / "recon-web.sqlite")
    try:
        assert store.fx_daily_rates_status() == {
            "n_days": 0, "first_day": None, "last_day": None, "currencies": [],
        }
        store.upsert_fx_daily_rates(
            [("2026-07-02", "usd", "1.1430", "ECB"), ("2026-07-02", "BRL", "5.8450", "ECB")],
            "2026-09-23T10:00:00+00:00",
        )
        store.upsert_fx_daily_rates([("2026-07-02", "USD", "1.1431", "ECB")], "2026-09-24T10:00:00+00:00")
        assert store.fx_daily_rates() == {"2026-07-02": {"BRL": "5.8450", "USD": "1.1431"}}
        assert store.fx_daily_rates("2026-07-03") == {}
        assert store.fx_daily_rates(end="2026-07-01") == {}
        assert store.fx_daily_rates_status() == {
            "n_days": 1, "first_day": "2026-07-02", "last_day": "2026-07-02",
            "currencies": ["BRL", "USD"],
        }
        assert store.get_fx_meta("x") is None
        store.set_fx_meta("x", "1")
        store.set_fx_meta("x", "2")
        assert store.get_fx_meta("x") == "2"
    finally:
        store.close()
