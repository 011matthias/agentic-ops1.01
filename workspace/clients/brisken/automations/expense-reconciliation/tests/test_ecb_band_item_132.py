"""Item 90: a tighter clean band for a central-bank rate.

The typed Settings rates this module also covered were RETIRED on
2026-09-23 ("no more typing them in settings you can remove that function
entirely"), so item 132's drift warning -- which existed to say a typed rate
had drifted from the ECB's -- went with them, and its four tests with it.
What is left is the band, plus one test pinning that a typed rate still
sitting in a stored config is ignored rather than obeyed.

Measured before building, Settings rates removed, on a copy of the live July
month: at the old shared 3% band the ECB rate auto-matched two receipts the
labels call "no charge" and demoted one right pair; at 2% it resolves 32
right with one coincidence left (Erste Fracht, +0.2%, out of any band's
reach). A typed Settings rate and the self-derived rates keep 3%, so every
month matched at a Settings rate and the scorer's bundles do not move.

Route-level: every assertion reads `GET /api/runs/{id}` after the real upload
and statement-attach routes, with the ECB's real June-August 2026 averages
behind a stubbed fetch and a mocked model.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web import ecb_rates  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-item-132"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The ECB's monthly averages, units per EUR (same values as item 82's tests).
ECB = {
    "2026-06": {"USD": "1.1518", "BRL": "5.898918181818181"},
    "2026-07": {"USD": "1.1417478260869562", "BRL": "5.844895652173915"},
    "2026-08": {"USD": "1.1593095238095241", "BRL": "5.968409523809523"},
}
JULY_EUR_USD = "1.141748"
# 276.08 EUR x 1.141748 = 315.21 USD; 323.09 is 2.50% over it: inside the old
# 3% band, outside the ECB's 2%.
GAP_2_5_CHARGE = -323.09


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.setattr(
        ecb_rates, "fetch_monthly",
        lambda start, end, **kw: {m: dict(v) for m, v in ECB.items() if start <= m <= end},
    )
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _july(client, monkeypatch, *, rates: dict | None, charge: float, p: float = 0.9) -> dict:
    """A July 2026 month holding one Amazon.de 276.08 EUR receipt (07-02)
    and one AMAZON charge the same day, with the model answering every FX
    question with `p`."""
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-07-02", total="276.08", currency="EUR",
                vendor="Amazon.de", reference="AMZ-302-1",
                line_items=(), confidence=0.9, notes="",
            ),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=p > 0.5, same_purchase_confidence=p,
                implied_rate=None, converted_amount=None,
                reasoning="Judged by the mocked model.",
            )
        ] * 6,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
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
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "July 2026"},
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("Amazon.jpg", JPG, "application/octet-stream"))],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("July2026.xlsx", _xlsx([
            (datetime(2026, 7, 2), "AMAZON* Z11US7DF5", "Sale", charge),
        ]), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return client.get(f"/api/runs/{batch}").json()


def _amazon(view: dict) -> dict:
    rows = [r for r in view["rows"] if "AMAZON" in r["vendor"]]
    assert len(rows) == 1, [r["vendor"] for r in view["rows"]]
    return rows[0]


def _eur_candidate(row: dict) -> dict:
    cands = [c for c in row["candidates"] if (c["fx"] or {}).get("receipt_currency") == "EUR"]
    assert len(cands) == 1, row["candidates"]
    return cands[0]


def _drift(view: dict) -> list[dict]:
    return [
        a for a in view["summary"]["setup_advisories"]
        if a.get("code") == "fx_rate_drift"
    ]


# ── the band ─────────────────────────────────────────────────────────────


def test_route_an_ecb_pair_two_and_a_half_percent_off_is_reviewed_not_reconciled(
    client, monkeypatch
):
    """No rate typed: the pair reads July's ECB average, 2.50% off. Under the
    shared 3% band it reconciled on its own; under the ECB's 2% it goes to
    the model and the reviewer, and the band on screen says why."""
    view = _july(client, monkeypatch, rates=None, charge=GAP_2_5_CHARGE)
    row = _amazon(view)
    assert row["effective_bucket"] == "review", row
    cand = _eur_candidate(row)
    assert cand["match_type"] == "fx_judgment", cand
    assert cand["requires_review"] is True
    fx = cand["fx"]
    assert fx["reference_rate_source"] == "ecb_month"
    assert fx["reference_rate"] == JULY_EUR_USD
    assert fx["reference_gap_pct"] == 2.5
    assert fx["reference_gap_band"] == "review"


def test_the_matchers_reason_names_the_band_the_rate_source_got():
    """The model's answer replaces the matcher's reason on screen, so the
    wording is pinned on the matcher: the ECB pair cites 2%, the same gap on
    a rate the run derived from its own documents reconciles at 3%, and a
    whole percentage prints as it always did."""
    from datetime import date
    from decimal import Decimal

    from expense_recon.matching.deterministic import MatchingConfig, MatchType, match_one
    from expense_recon.matching.types import Receipt, Transaction

    tx = Transaction(
        transaction_id="t1", legal_entity_id="", account_id="2838",
        transaction_date=date(2026, 7, 2), posting_date=None,
        amount=Decimal("323.09"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="", detected_date=date(2026, 7, 2),
        detected_total=Decimal("276.08"), detected_currency="EUR", detected_vendor="Amazon.de",
    )
    ecb = MatchingConfig.from_dict({"fx_ecb_monthly_rates": ECB})
    m = match_one(tx, rec, ecb)
    assert m.match_type == MatchType.FX_JUDGMENT, m
    assert f"ECB monthly average rate {JULY_EUR_USD} (2026-07): deviation 2.5% (above 2%;" in m.reason, m.reason

    derived = {("EUR", "USD"): (Decimal(JULY_EUR_USD), "receipts", 3)}
    assert match_one(
        tx, rec, ecb, derived_rates=derived
    ).match_type == MatchType.FX_REFERENCE

    tx_far = Transaction(**{**tx.__dict__, "amount": Decimal("331.00")})  # 5.0% off
    m = match_one(tx_far, rec, ecb, derived_rates=derived)
    assert m.match_type == MatchType.FX_JUDGMENT
    assert "(above 3%;" in m.reason, m.reason


def test_a_rate_typed_in_settings_is_no_longer_read_from_a_stored_config():
    """The retirement, pinned (owner 2026-09-23: "no more typing them in
    settings you can remove that function entirely").

    July's and August's stored configs still carry the two rates that used
    to outrank everything, and the shipped scorer asset still carries the
    key. Both must keep LOADING -- refusing the key would make an existing
    month unopenable -- and the rate must be IGNORED, so the pair resolves
    on the ECB table sitting in the same config. Regress the drop in
    `_RETIRED_TUNABLES` and this goes red."""
    from datetime import date
    from decimal import Decimal

    from expense_recon.matching.deterministic import MatchingConfig, MatchType, match_one
    from expense_recon.matching.types import Receipt, Transaction

    tx = Transaction(
        transaction_id="t1", legal_entity_id="", account_id="2838",
        transaction_date=date(2026, 7, 2), posting_date=None,
        amount=Decimal("323.09"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="", detected_date=date(2026, 7, 2),
        detected_total=Decimal("276.08"), detected_currency="EUR", detected_vendor="Amazon.de",
    )
    # The live July shape: the retired typed rate beside the ECB table.
    cfg = MatchingConfig.from_dict({
        "fx_ecb_monthly_rates": ECB,
        "fx_reference_rates": {"EUR:USD": "1.162275"},
    })
    assert not hasattr(cfg, "fx_reference_rates")
    m = match_one(tx, rec, cfg)
    # At the typed 1.162275 this pair reconciled; at the ECB rate it is
    # 2.5% off, outside the 2% band, so it defers instead.
    assert m.match_type == MatchType.FX_JUDGMENT, m
    assert f"ECB monthly average rate {JULY_EUR_USD}" in m.reason, m.reason
    assert "1.162275" not in m.reason, m.reason


@pytest.mark.parametrize("source", ["statement", "receipts"])
def test_a_self_derived_rate_keeps_the_three_percent_band(source):
    """The S1 optimize run refuted a tighter band for the self-derived rates
    (a month median sits 1-3% off each receipt's own rate), so only the ECB
    rung tightened: the same 2.50% gap on a derived rate still reconciles,
    with the ECB table present in the same config."""
    from datetime import date
    from decimal import Decimal

    from expense_recon.matching.deterministic import MatchingConfig, MatchType, match_one
    from expense_recon.matching.types import Receipt, Transaction

    tx = Transaction(
        transaction_id="t1", legal_entity_id="", account_id="2838",
        transaction_date=date(2026, 7, 2), posting_date=None,
        amount=Decimal("323.09"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="", detected_date=date(2026, 7, 2),
        detected_total=Decimal("276.08"), detected_currency="EUR", detected_vendor="Amazon.de",
    )
    cfg = MatchingConfig.from_dict({"fx_ecb_monthly_rates": ECB})
    derived = {("EUR", "USD"): (Decimal(JULY_EUR_USD), source, 3)}
    m = match_one(tx, rec, cfg, derived_rates=derived)
    assert m.match_type == MatchType.FX_REFERENCE, m
    assert cfg.reference_match_pct(source) == Decimal("0.03")
    assert cfg.reference_match_pct("ecb_month") == Decimal("0.02")


def test_route_an_ecb_pair_inside_two_percent_still_reconciles(client, monkeypatch):
    """Note #43's own pair (315.56 against 315.21, +0.11%) is untouched."""
    view = _july(client, monkeypatch, rates=None, charge=-315.56)
    row = _amazon(view)
    assert row["effective_bucket"] == "reconciled", row
    cand = _eur_candidate(row)
    assert cand["match_type"] == "fx_reference"
    assert cand["fx"]["reference_gap_band"] == "match"


def test_route_the_judgment_floor_reads_the_ecb_band(client, monkeypatch):
    """Item 131's at-floor exception keeps a model rejection in review only
    when the pair's rate sits in the clean band. At 2.50% on an ECB rate
    that band is 2%, so the rejection at exactly 0.20 is not shown: the
    charge and the receipt go to the unmatched lists."""
    view = _july(client, monkeypatch, rates=None, charge=GAP_2_5_CHARGE, p=0.20)
    row = _amazon(view)
    assert row["effective_bucket"] == "unmatched", row
    assert not [c for c in row["candidates"] if c["match_type"] == "fx_judgment"], row["candidates"]
    assert [r["vendor"] for r in view["unmatched_receipts"]] == ["Amazon.de"]


# ── the drift advisory ───────────────────────────────────────────────────


