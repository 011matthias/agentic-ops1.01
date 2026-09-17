"""Item 82: a reference rate per month, from the ECB (owner ruling 2026-09-16).

The hosted months matched every foreign receipt against ONE rate per pair
from Settings (EUR:USD 1.162275, BRL:USD 0.192448), copied into each month at
creation: July and August both cited a rate that was nobody's month. The
ruling: per month, from the ECB (`EXR/M.USD.EUR.SP00.A`,
`EXR/M.BRL.EUR.SP00.A`, BRL:USD as the cross), and a rate the operator types
still wins.

The routes below run with the real ECB monthly averages for June, July and
August 2026 (fetched 2026-09-17) behind a stubbed fetch, so what they pin is
what the SPA receives when the ECB answers.
"""
from __future__ import annotations

import io
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
from expense_recon.web import ecb_rates  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import _setup_advisories  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The ECB's own monthly averages, units per EUR, as the API returned them.
ECB = {
    "2026-06": {"USD": "1.1518", "BRL": "5.898918181818181"},
    "2026-07": {"USD": "1.1417478260869562", "BRL": "5.844895652173915"},
    "2026-08": {"USD": "1.1593095238095241", "BRL": "5.968409523809523"},
}


class _Ecb:
    """A stand-in for the ECB Data API: answers from ECB for the span asked,
    records every span, and can be taken down."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.down = False

    def __call__(self, start: str, end: str, **kw) -> dict:
        self.calls.append((start, end))
        if self.down:
            raise OSError("ECB unreachable")
        return {m: dict(v) for m, v in ECB.items() if start <= m <= end}


@pytest.fixture
def ecb(monkeypatch):
    stub = _Ecb()
    monkeypatch.setattr(ecb_rates, "fetch_monthly", stub)
    return stub


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
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
    """An empty July 2026 company month with three receipts, spaced so no
    receipt reaches another's charge inside the 5-day FX window:

    * Amazon.de 276.08 EUR, 07-02 (note #43's pair; charge 315.56 USD)
    * Supermercado Sao Jose 41.85 BRL, 07-09 (charge 8.29 USD)
    * Supermercado Fenix 55.74 BRL, 06-30 (charge 10.82 USD dated 06-30,
      on the July statement: the June charge July really holds)
    """
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


# ── routes ────────────────────────────────────────────────────────────────


def test_route_a_month_with_no_typed_rate_matches_on_the_ecb_monthly_average(
    client, monkeypatch, ecb
):
    """No rate in Settings: the July month matches on July's ECB average and
    says so. Note #43's pair reads 276.08 EUR x 1.141748 = 315.21 USD, +0.35
    (+0.11%), where the old Settings rate printed -5.32 (-1.66%). The rate
    the block prints appears verbatim in the reason the matcher wrote."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "AMAZON"))
    assert chosen["match_type"] == "fx_reference", chosen
    fx = chosen["fx"]
    assert fx["reference_rate"] == "1.141748"
    assert fx["reference_rate_source"] == "ecb_month"
    assert fx["reference_rate_period"] == "2026-07"
    assert fx["reference_converted"] == "315.21"
    assert fx["reference_gap"] == "+0.35"
    assert fx["reference_gap_pct"] == 0.11
    assert fx["reference_gap_band"] == "match"
    assert "1.141748" in chosen["reason"], chosen["reason"]
    assert "ECB" in chosen["reason"]

    fx = _chosen(_row(view, "SUPERMEC"))["fx"]
    assert fx["reference_rate"] == "0.195341"  # 1.1417478 / 5.8448957
    assert fx["reference_rate_source"] == "ecb_month"
    assert fx["reference_converted"] == "8.18"
    assert fx["reference_gap_pct"] == 1.41


def test_route_a_june_charge_on_the_july_statement_reads_junes_average(
    client, monkeypatch, ecb
):
    """The rate is keyed by the CHARGE's month, not the month's label: card
    networks lock the rate at authorization. The 06-30 Fenix charge reads
    June's BRL:USD 0.195256 (10.88, -0.58%), not July's 0.195341."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "FENIX"))
    fx = chosen["fx"]
    assert fx["reference_rate"] == "0.195256"
    assert fx["reference_rate_period"] == "2026-06"
    assert fx["reference_converted"] == "10.88"
    assert fx["reference_gap_pct"] == -0.58
    assert "0.195256" in chosen["reason"]


def test_route_a_rate_typed_in_settings_still_wins(client, monkeypatch, ecb):
    """Owner ruling: a rate the operator types wins. With EUR:USD typed, the
    Amazon pair stays on 1.162275 and carries no period; BRL, not typed,
    still reads the ECB. The ECB table is stored either way."""
    _settings(client, {"EUR:USD": "1.162275"})
    batch_id = _create_july(client, monkeypatch)
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()

    fx = _chosen(_row(view, "AMAZON"))["fx"]
    assert fx["reference_rate"] == "1.162275"
    assert fx["reference_rate_source"] == "settings"
    assert "reference_rate_period" not in fx
    assert fx["reference_gap"] == "-5.32"

    fx = _chosen(_row(view, "SUPERMEC"))["fx"]
    assert fx["reference_rate_source"] == "ecb_month"

    matching = _config(client, batch_id)["matching"]
    assert matching["fx_reference_rates"] == {"EUR:USD": "1.162275"}
    assert set(matching["fx_ecb_monthly_rates"]) == {"2026-06", "2026-07", "2026-08"}


def test_route_the_rates_are_fetched_when_the_month_is_created(
    client, monkeypatch, ecb
):
    """Creating "July 2026" asks the ECB once for June..August and stores
    the averages as the ECB published them, before any statement exists."""
    _settings(client)
    batch_id = _create_july(client, monkeypatch)

    assert ("2026-06", "2026-08") in ecb.calls
    table = _config(client, batch_id)["matching"]["fx_ecb_monthly_rates"]
    assert table["2026-07"] == ECB["2026-07"]
    assert list(table) == ["2026-06", "2026-07", "2026-08"]


def test_route_an_ecb_outage_never_blocks_and_the_statement_attach_fetches_again(
    client, monkeypatch, ecb
):
    """Fail-open at creation: the ECB is down, the month is created with no
    rates at all (the config key is absent, not empty). The statement attach
    asks again, finds the ECB up, and the month matches on it."""
    _settings(client)
    ecb.down = True
    batch_id = _create_july(client, monkeypatch)
    assert "fx_ecb_monthly_rates" not in (_config(client, batch_id).get("matching") or {})

    ecb.down = False
    _attach_statement(client, batch_id)
    view = client.get(f"/api/runs/{batch_id}").json()
    fx = _chosen(_row(view, "AMAZON"))["fx"]
    assert fx["reference_rate_source"] == "ecb_month"
    assert fx["reference_rate"] == "1.141748"


def test_route_a_trip_fetches_nothing(client, monkeypatch, ecb):
    """A trip is matched inside the company months that borrow it, against
    their rates. Labelled like a month on purpose: the label alone would
    otherwise ask the ECB for June..August."""
    _settings(client)
    trip = client.post("/api/trips", json={
        "name": "Rome", "start": "2026-07-01", "end": "2026-07-05",
        "travelers": ["Nicolas"],
    })
    assert trip.status_code == 200, trip.text
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-07-02", total="20.00", currency="EUR", vendor="Bar Roma",
        reference="", line_items=(), confidence=0.9, notes="",
    )])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("r.jpg", JPG, "application/octet-stream"))],
        data={
            "legal_entity": "", "label": "July 2026",
            "batch_type": "trip", "trip_id": trip.json()["trip_id"],
        },
    )
    _done(client, resp)
    assert ecb.calls == []
    assert "fx_ecb_monthly_rates" not in (
        _config(client, resp.json()["batch_id"]).get("matching") or {}
    )


# ── the matcher's lookup ─────────────────────────────────────────────────


def _cfg(**kw) -> MatchingConfig:
    return MatchingConfig.from_dict({"fx_ecb_monthly_rates": ECB, **kw})


def test_ecb_rate_is_the_cross_through_eur_for_the_month_asked():
    cfg = _cfg()
    assert cfg.ecb_monthly_rate("EUR", "USD", date(2026, 7, 14)) == (Decimal("1.141748"), "2026-07")
    assert cfg.ecb_monthly_rate("BRL", "USD", "2026-08") == (Decimal("0.194241"), "2026-08")
    assert cfg.ecb_monthly_rate("USD", "BRL", "2026-06") == (Decimal("5.121478"), "2026-06")
    assert cfg.ecb_monthly_rate("USD", "USD", "2026-07") is None
    assert cfg.ecb_monthly_rate("GBP", "USD", "2026-07") is None
    assert cfg.ecb_monthly_rate("EUR", "USD", None) is None


def test_a_month_not_yet_published_reads_its_nearest_neighbour_and_names_it():
    """September's average does not exist until October: a September charge
    reads August and the month says so. A tie goes to the earlier month."""
    cfg = _cfg()
    assert cfg.ecb_monthly_rate("EUR", "USD", date(2026, 9, 2)) == (Decimal("1.159310"), "2026-08")
    gap = MatchingConfig.from_dict({"fx_ecb_monthly_rates": {
        "2026-06": ECB["2026-06"], "2026-08": ECB["2026-08"],
    }})
    assert gap.ecb_monthly_rate("EUR", "USD", "2026-07")[1] == "2026-06"


def test_the_rung_order_is_typed_then_derived_then_ecb():
    """A typed rate wins; a rate the month derives from its own statement
    FX lines or booked receipt rates comes next; the ECB average is the
    fallback. Without a date the ECB rung cannot answer."""
    derived = {("EUR", "USD"): (Decimal("1.15"), "statement", 3)}
    typed = _cfg(fx_reference_rates={"EUR:USD": "1.2"})
    on = date(2026, 7, 14)
    assert _reference_rate_for(typed, "EUR", "USD", derived, on=on) == (Decimal("1.2"), "configured", 0)
    assert _reference_rate_for(_cfg(), "EUR", "USD", derived, on=on) == (Decimal("1.15"), "statement", 3)
    assert _reference_rate_for(_cfg(), "EUR", "USD", {}, on=on) == (Decimal("1.141748"), "ecb_month", 0)
    assert _reference_rate_for(_cfg(), "EUR", "USD", {}) is None
    assert _reference_rate_for(MatchingConfig(), "EUR", "USD", {}, on=on) is None


def test_a_malformed_month_key_is_refused():
    with pytest.raises(ValueError, match="YYYY-MM"):
        MatchingConfig.from_dict({"fx_ecb_monthly_rates": {"July": {"USD": "1.1"}}})


# ── the fetch ────────────────────────────────────────────────────────────


CSV = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
    "EXR.M.BRL.EUR.SP00.A,M,BRL,EUR,SP00,A,2026-07,5.844895652173915\n"
    "EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2026-07,1.1417478260869562\n"
    "EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2026-08,1.1593095238095241\n"
    "EXR.M.XXX.EUR.SP00.A,M,XX,EUR,SP00,A,2026-08,1.0\n"
    "EXR.M.JPY.EUR.SP00.A,M,JPY,EUR,SP00,A,2026-08,\n"
)


def test_the_ecb_csv_parses_to_units_per_eur_by_month():
    assert ecb_rates.parse_csv(CSV) == {
        "2026-07": {"BRL": "5.844895652173915", "USD": "1.1417478260869562"},
        "2026-08": {"USD": "1.1593095238095241"},
    }


def test_months_after_the_current_one_are_never_asked_for(monkeypatch):
    calls = []
    monkeypatch.setattr(ecb_rates, "fetch_monthly", lambda s, e, **kw: calls.append((s, e)) or {})
    ecb_rates.rates_for_months(["2026-08", "2026-09", "2026-10"], today=date(2026, 9, 17))
    assert calls == [("2026-08", "2026-09")]
    calls.clear()
    ecb_rates.rates_for_months(["2026-10"], today=date(2026, 9, 17))
    assert calls == []


def test_the_fetch_can_be_switched_off(monkeypatch, ecb):
    monkeypatch.setenv("EXPENSE_RECON_ECB_RATES", "0")
    assert ecb_rates.rates_for_months(["2026-07"]) == {}
    assert ecb.calls == []


# ── the setup advisory ───────────────────────────────────────────────────


def test_the_advisory_is_quiet_for_a_currency_the_ecb_covers():
    """The old advisory told the operator to add this month's rate in
    Settings. With the ECB table in the config it speaks only for a currency
    neither source can convert."""
    from expense_recon.matching.types import Receipt, Transaction

    tx = Transaction(
        transaction_id="t1", legal_entity_id="", account_id="2838",
        transaction_date=date(2026, 7, 2), posting_date=None,
        amount=Decimal("10"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="X",
    )

    def rec(doc, ccy):
        return Receipt(
            document_id=doc, legal_entity_id="", detected_date=date(2026, 7, 2),
            detected_total=Decimal("10"), detected_currency=ccy, detected_vendor="X",
        )

    cfg = {"matching": {"fx_ecb_monthly_rates": ECB}}
    notes = _setup_advisories(cfg, [tx], [rec("a", "BRL"), rec("b", "GBP")], has_coa=True)
    fx = [n for n in notes if n["setting"] == "fx_reference_rates"]
    assert len(fx) == 1 and "GBP" in fx[0]["message"], fx
    assert "Add this month's rate" not in fx[0]["message"]
