"""FX comparison breakdown on cross-currency candidates (2026-07-25).

A reviewer working an uncertain FX pair should see, side by side, what the
bank statement charged, what the receipt says, and what the receipt is
worth under Zoho's own booked rate. `_fx_breakdown` builds that flat
comparison; these tests pin the math and the graceful-omission rules.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.types import Receipt, Transaction
from expense_recon.web.service import _fx_breakdown


def _tx(amount="77.05", ccy="USD") -> Transaction:
    return Transaction(
        transaction_id="t1",
        legal_entity_id="le1",
        account_id="2838",
        transaction_date=date(2026, 4, 6),
        posting_date=None,
        amount=Decimal(amount) if amount is not None else None,
        transaction_currency=ccy,
        account_card_currency="USD",
        vendor_from_statement="OPENAI *CHATGPT SUBSCR",
    )


def _rec(total="335.31", ccy="BRL", rate="0.196078", base="65.75") -> Receipt:
    return Receipt(
        document_id="ER-00215#004",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 8),
        detected_total=Decimal(total) if total is not None else None,
        detected_currency=ccy,
        detected_vendor="MEGA CENTER COMERCIO",
        exchange_rate=Decimal(rate) if rate is not None else None,
        base_amount=Decimal(base) if base is not None else None,
    )


def test_same_currency_returns_none():
    assert _fx_breakdown(_tx(ccy="USD"), _rec(ccy="USD")) is None


def test_missing_receipt_returns_none():
    assert _fx_breakdown(_tx(), None) is None


def test_missing_amount_returns_none():
    assert _fx_breakdown(_tx(amount=None), _rec()) is None
    assert _fx_breakdown(_tx(), _rec(total=None)) is None


def test_full_breakdown_with_zoho_conversion():
    fx = _fx_breakdown(_tx(), _rec())
    assert fx["charge_amount"] == "77.05"
    assert fx["charge_currency"] == "USD"
    assert fx["receipt_amount"] == "335.31"
    assert fx["receipt_currency"] == "BRL"
    assert fx["rate_label"] == "USD per BRL"
    # Zoho's booked rate is carried through; this pairing implies a higher
    # one (77.05 / 335.31 = 0.229787), which is the FX-coincidence tell.
    assert fx["zoho_rate"] == "0.196078"
    assert fx["implied_rate"] == "0.229787"
    # Zoho values the receipt at 65.75 USD; the charge is 77.05 USD.
    assert fx["zoho_converted"] == "65.75"
    assert fx["converted_gap"] == "11.30"
    assert fx["converted_gap_pct"] == 15  # 11.30 / 77.05


def test_breakdown_without_zoho_conversion():
    """A manual/emailed receipt carries no Zoho rate or base amount: the
    implied rate still renders, the Zoho columns are blank."""
    fx = _fx_breakdown(_tx(), _rec(rate=None, base=None))
    assert fx["implied_rate"] == "0.229787"
    assert fx["zoho_rate"] == ""
    assert fx["zoho_converted"] == ""
    assert fx["converted_gap"] == ""
    assert fx["converted_gap_pct"] is None


# ── item 81: the conversion at the tool's own rate, through the route ────
#
# Note #43 (Matthias, July, on AMAZON 315.56 USD vs the Amazon.de receipt
# 276.08 EUR): "maybe in cross currency cases show the calculation of what the
# receipt's amount is in $ using our FX rate." The block showed only the rate
# the pairing NEEDS (1.143002); the rate the matcher USED (Settings, 1.162275)
# lived in the reason string. These tests drive GET /api/runs/{id}, so what
# they pin is what the SPA receives.

import io  # noqa: E402
from datetime import datetime  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching import deterministic  # noqa: E402
from expense_recon.matching.deterministic import (  # noqa: E402
    MatchingConfig,
    match_month,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REFERENCE_KEYS = {
    "reference_rate", "reference_rate_source", "reference_converted",
    "reference_gap", "reference_gap_pct", "reference_gap_band",
}


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


def _july(client, monkeypatch) -> str:
    """A July month at the live Settings rates, each receipt kept more than
    the FX date window (5 days) away from every other receipt's charge, so no
    pair crosses:

    * AMAZON 315.56 USD vs Amazon.de 276.08 EUR — the note's own pair.
    * SUPERMEC SAO JOSE 8.29 USD vs 41.85 BRL — 2.93%, the edge of the band.
    * FORTNUM AND MASON 50.80 USD vs 40.00 GBP — no GBP:USD rate anywhere.
    * LOJA CENTRO 50.00 USD vs 20.00 EUR — no candidate (implied 2.5 is
      outside the EUR band), so it can only be paired by hand.
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
                date="2026-07-16", total="40.00", currency="GBP",
                vendor="Fortnum & Mason", reference="FM-0716",
                line_items=(), confidence=0.9, notes="",
            ),
            ExtractedReceipt(
                date="2026-07-23", total="20.00", currency="EUR",
                vendor="Loja Centro", reference="LC-0723",
                line_items=(), confidence=0.9, notes="",
            ),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.27, converted_amount=Decimal("50.80"),
                reasoning="Fortnum & Mason, same day, plausible GBP rate",
            )
        ],
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.put("/api/settings", json={
        "entities": {"Corporate Services": {}},
        "cards": {
            "corp-2838": {
                "label": "Corporate card (Chase)", "digits": ["2838"],
                "entity": "Corporate Services", "currency": "USD",
            },
        },
        "fx_reference_rates": {"EUR:USD": "1.162275", "BRL:USD": "0.192448"},
    })
    assert resp.status_code == 200, resp.text
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
            for i, name in enumerate(
                ["Amazon.jpg", "Supermec.jpg", "Fortnum.jpg", "Loja.jpg"]
            )
        ],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("July2026.xlsx", _xlsx_bytes([
            (datetime(2026, 7, 2), "AMAZON* Z11US7DF5", "Sale", -315.56),
            (datetime(2026, 7, 9), "SUPERMEC SAO JOSE", "Sale", -8.29),
            (datetime(2026, 7, 16), "FORTNUM AND MASON", "Sale", -50.80),
            (datetime(2026, 7, 23), "LOJA CENTRO", "Sale", -50.00),
        ]), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch_id


def _row(view: dict, vendor: str) -> dict:
    return next(r for r in view["rows"] if vendor in r["vendor"])


def _chosen(row: dict) -> dict:
    return next(c for c in row["candidates"] if c["is_chosen"])


def test_route_amazon_shows_the_receipt_converted_at_the_settings_rate(
    client, monkeypatch
):
    """The note's pair, with the live numbers: 276.08 EUR x 1.162275 =
    320.88 USD, the charge 315.56 is 5.32 under it, -1.66% of the converted
    amount, inside the 3% match band. The rate the pairing needs and the
    zoho_* keys stay exactly as they were."""
    batch_id = _july(client, monkeypatch)
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "AMAZON"))
    assert chosen["match_type"] == "fx_reference", chosen
    fx = chosen["fx"]
    assert fx["reference_rate"] == "1.162275"
    assert fx["reference_rate_source"] == "settings"
    assert fx["reference_converted"] == "320.88"
    assert fx["reference_gap"] == "-5.32"
    assert fx["reference_gap_pct"] == -1.66
    assert fx["reference_gap_band"] == "match"
    # the arithmetic on screen adds up to the charge, to the cent
    assert Decimal(fx["reference_converted"]) + Decimal(fx["reference_gap"]) == (
        Decimal(fx["charge_amount"])
    )
    # untouched neighbours (item 23 amendment: zoho_* are renamed later, not here)
    assert fx["implied_rate"] == "1.143002"
    assert fx["rate_label"] == "USD per EUR"
    assert (fx["zoho_rate"], fx["zoho_converted"], fx["converted_gap"]) == ("", "", "")
    assert fx["converted_gap_pct"] is None

    # July SUPERMEC SAO JOSE: +2.93% sits just inside the 3% band, decided on
    # the unrounded deviation (2.9309%).
    fx = _chosen(_row(view, "SUPERMEC"))["fx"]
    assert fx["reference_rate"] == "0.192448"
    assert fx["reference_converted"] == "8.05"
    assert fx["reference_gap"] == "+0.24"
    assert fx["reference_gap_pct"] == 2.93
    assert fx["reference_gap_band"] == "match"


def test_route_a_pair_with_no_reference_rate_carries_no_reference_keys(
    client, monkeypatch
):
    """GBP has no rate in Settings and nothing derives one, so the FORTNUM
    candidate keeps its FX block (the implied rate still renders) with none
    of the six keys: absent, not empty, not null. The EUR and BRL rates in the
    same Settings prove the absence is per pair."""
    batch_id = _july(client, monkeypatch)
    view = client.get(f"/api/runs/{batch_id}").json()

    cands = _row(view, "FORTNUM")["candidates"]
    assert cands, _row(view, "FORTNUM")
    for c in cands:
        fx = c["fx"]
        assert fx["receipt_currency"] == "GBP"
        assert fx["implied_rate"] == "1.27"
        assert not REFERENCE_KEYS & set(fx), fx


def test_route_a_hand_match_shows_the_conversion_too(client, monkeypatch):
    """The second call site: a receipt paired by hand renders through the
    synthesized `manual` candidate, and its block reads the same rate. 20.00
    EUR x 1.162275 = 23.25 USD against a 50.00 charge is far outside the 13%
    review band, which is exactly what a reviewer pairing by hand should see."""
    batch_id = _july(client, monkeypatch)
    view = client.get(f"/api/runs/{batch_id}").json()
    loja = _row(view, "LOJA")
    assert loja["candidates"] == [], loja
    doc = next(
        r["document_id"] for r in view["unmatched_receipts"]
        if r["vendor"] == "Loja Centro"
    )

    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": loja["transaction_id"], "document_id": doc},
    )
    assert resp.status_code == 200, resp.text
    view = client.get(f"/api/runs/{batch_id}").json()

    chosen = _chosen(_row(view, "LOJA"))
    assert chosen["match_type"] == "manual", chosen
    fx = chosen["fx"]
    assert fx["reference_rate"] == "1.162275"
    assert fx["reference_rate_source"] == "settings"
    assert fx["reference_converted"] == "23.25"
    assert fx["reference_gap"] == "+26.75"
    assert fx["reference_gap_pct"] == 115.10
    assert fx["reference_gap_band"] == "outside"


def test_the_view_asks_the_matchers_own_lookup_for_the_rate(
    client, monkeypatch
):
    """No second derivation: the block's rate comes from
    `matching.deterministic._reference_rate_for`, so replacing that one
    function moves the screen. A source the view has never heard of (item 82
    adds `ecb_month`) passes through as the matcher named it."""
    batch_id = _july(client, monkeypatch)

    def _stub(cfg, from_ccy, to_ccy, derived, on=None):
        return Decimal("1.2"), "ecb_month", 0

    monkeypatch.setattr(deterministic, "_reference_rate_for", _stub)
    fx = _chosen(_row(client.get(f"/api/runs/{batch_id}").json(), "AMAZON"))["fx"]
    assert fx["reference_rate"] == "1.2"
    assert fx["reference_rate_source"] == "ecb_month"
    assert fx["reference_converted"] == "331.30"  # 276.08 x 1.2 = 331.296
    assert fx["reference_gap"] == "-15.74"
    assert fx["reference_gap_pct"] == -4.75
    assert fx["reference_gap_band"] == "review"


def _seeded_month(client, run_id: str, transactions, receipts) -> dict:
    """A month whose outcome the MATCHER produced (so every reason string is
    its own), seeded as a run and read back through the route. Used for the
    two derived sources, which a Chase workbook upload cannot produce."""
    outcome = match_month(transactions, receipts, MatchingConfig())
    store = RunStore(client._data_root / "recon-web.sqlite")
    store.create_run(
        run_id=run_id, created_at="2026-09-16T00:00:00", label=run_id,
        operator=None, summary={},
        snapshot=snapshot_to_dict(transactions, receipts, outcome, []),
        config={}, work_dir=str(client._data_root), llm_enabled=False,
        has_coa=False,
    )
    store.close()
    return client.get(f"/api/runs/{run_id}").json()


def _usd_charge(tx_id, day, amount, vendor="MERCHANT", **kw) -> Transaction:
    return Transaction(
        transaction_id=tx_id, legal_entity_id="", account_id="card-2838",
        transaction_date=date(2026, 7, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor, **kw,
    )


def _foreign_receipt(doc, day, total, ccy, vendor="Merchant", **kw) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 7, day),
        detected_total=Decimal(total), detected_currency=ccy,
        detected_vendor=vendor, **kw,
    )


def test_every_fx_reference_reason_carries_the_rate_the_block_shows(
    client, monkeypatch
):
    """The screen and the decision cannot drift. For every candidate the
    matcher resolved on a reference rate, the rate the block prints appears
    verbatim in the reason the matcher wrote, across all three sources:
    Settings (the uploaded July month), the statement's own FX lines, and the
    receipts' own booked rates (both seeded from a real `match_month`)."""
    views = [client.get(f"/api/runs/{_july(client, monkeypatch)}").json()]

    # statement: charge s1 printed its GBP original at 1.27; charge s2 carries
    # no FX detail and meets a GBP receipt at that derived rate.
    views.append(_seeded_month(
        client, "fx-derived-statement",
        [
            _usd_charge("s1", 3, "63.50", "HARRODS", original_amount=Decimal("50.00"),
                        original_currency="GBP", fx_rate=Decimal("1.27")),
            _usd_charge("s2", 20, "25.40", "PRET A MANGER"),
        ],
        [_foreign_receipt("gbp-1", 20, "20.00", "GBP", "Pret")],
    ))
    # receipts: three expense-report lines booked EUR at 1.10 (no base
    # amount, so the base-amount rung stays out of the way).
    views.append(_seeded_month(
        client, "fx-derived-receipts",
        [
            _usd_charge("e1", 4, "11.00", "CAFE ONE"),
            _usd_charge("e2", 12, "22.00", "CAFE TWO"),
            _usd_charge("e3", 20, "33.00", "CAFE THREE"),
        ],
        [
            _foreign_receipt("eur-1", 4, "10.00", "EUR", exchange_rate=Decimal("1.10")),
            _foreign_receipt("eur-2", 12, "20.00", "EUR", exchange_rate=Decimal("1.10")),
            _foreign_receipt("eur-3", 20, "30.00", "EUR", exchange_rate=Decimal("1.10")),
        ],
    ))

    seen_sources = set()
    for view in views:
        n = 0
        for row in view["rows"]:
            for c in row["candidates"]:
                if c["match_type"] != "fx_reference":
                    continue
                n += 1
                fx = c["fx"]
                assert fx["reference_rate"] in c["reason"], (fx, c["reason"])
                seen_sources.add(fx["reference_rate_source"])
        assert n, [r["candidates"] for r in view["rows"]]
    assert seen_sources == {"settings", "statement", "receipts"}, seen_sources
