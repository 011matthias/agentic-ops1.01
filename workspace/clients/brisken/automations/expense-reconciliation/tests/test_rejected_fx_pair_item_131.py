"""Item 131 (2026-09-17 audit): the tool suggested pairs its own model called
"likely NOT the same purchase".

The owner ruled on 2026-07-24 that a foreign-currency pair the model rejects
is not shown. The cut-off was "below 0.20" and the model answers exactly 0.20,
so live July showed two such rows with the model's rejection as their reason:
NOBRE ATACAREJO 65.23 against a Fenix 325.88 BRL receipt (4.01% off the month
rate, a different store) and NATHALIA KEILA FIRMIN 5.61 against a 28.73 BRL
receipt (1.5% off, labelled the right pair). Now:

* a verdict below the floor stays final, exactly as ruled: not shown, the
  charge and the receipt go to the unmatched lists, whatever the rate says;
* a verdict exactly AT the floor is a rejection too, except when the pair's
  own rate arithmetic sits in the clean band (item 81's
  `fx.reference_gap_band` == "match"): then it stays in review, the tool's
  arithmetic first and the model's disagreement after it;
* an at-floor rejection outside the clean band is not shown.

Route-level: every assertion reads `GET /api/runs/{id}` after the real
upload and statement-attach routes, which run `rematch_month` and the judgment
layer with a mocked model.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

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
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-item-131"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MONTH_RATE = "0.192448"  # the live Settings BRL:USD rate


@pytest.fixture(autouse=True)
def _ecb(monkeypatch):
    """MONTH_RATE (BRL:USD 0.192448) as a fetched rate.

    Units per ONE EUR, the ECB's own shape: a pair X:USD is
    units["USD"] / units["X"], and EUR itself is 1. Every month answers the
    same rates, so no test has to know which month its charges fall in.
    Typed Settings rates were retired 2026-09-23; a rate now reaches a
    month only by being fetched."""
    from expense_recon.web import ecb_rates

    def _fetch(start, end, **kw):
        months = ["2026-%02d" % m for m in range(1, 13)]
        return {m: {"USD": "1.162275", "BRL": "6.039423636515"} for m in months if start <= m <= end}

    monkeypatch.setattr(ecb_rates, "fetch_monthly", _fetch)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
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


def _month(client, monkeypatch, receipt: ExtractedReceipt, p: float, charges) -> str:
    """A July month at the live BRL rate: one BRL receipt, the given charges,
    and a model that answers every FX question with `p`, rejecting."""
    mock = MockLLMClient(
        extraction_responses=[receipt],
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=p,
                implied_rate=None, converted_amount=None,
                reasoning="The vendors are different, likely different purchases.",
            )
        ] * 6,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.put("/api/settings", json={
        "entities": {"Corporate Services": {}},
        "cards": {
            "corp-3876": {
                "label": "Corporate card (Chase)", "digits": ["3876"],
                "entity": "Corporate Services", "currency": "USD",
            },
        },
        # MONTH_RATE, reached through the ECB table (typed rates retired
        # 2026-09-23): units per EUR, so BRL:USD = units["USD"]/units["BRL"].
    })
    assert resp.status_code == 200, resp.text
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "July 2026"},
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("receipt.jpg", JPG, "application/octet-stream"))],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("July2026.xlsx", _xlsx(charges), XLSX)},
        data={
            "account_id": "card-3876",
            "account_legal_entities": '{"card-3876": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch


def _row(view: dict, vendor: str) -> dict:
    rows = [r for r in view["rows"] if vendor in r["vendor"]]
    assert len(rows) == 1, [r["vendor"] for r in view["rows"]]
    return rows[0]


def _nathalia(client, monkeypatch, p: float) -> dict:
    """July's NATHALIA pair: 28.73 BRL x 0.192448 = 5.53 USD, the 5.61 charge
    is 1.46% over it, inside the 3% band. A second charge two days later is
    also inside the band (5.47, -1.07%), so the uniqueness gate demotes the
    pair to judgment, which is how the live row reached the model."""
    batch = _month(
        client, monkeypatch,
        ExtractedReceipt(
            date="2026-07-07", total="28.73", currency="BRL",
            vendor="Bezerra Ltda", reference="NFC-0707",
            line_items=(), confidence=0.9, notes="",
        ),
        p,
        [
            (datetime(2026, 7, 7), "NATHALIA KEILA FIRMIN", "Sale", -5.61),
            (datetime(2026, 7, 9), "COL INTERMUNICIPAL", "Sale", -5.47),
        ],
    )
    return client.get(f"/api/runs/{batch}").json()


def test_a_verdict_below_the_floor_stays_final_even_inside_the_clean_band(
    client, monkeypatch
):
    """The owner's 2026-07-24 cut, unchanged: at p=0.10 the clean-band pair
    is not shown (live July: Erste Fracht 21.00 EUR against HOTEL AM
    TIERGARTEN 24.02, -1.59%, another merchant). Both charges fall to
    unmatched and the receipt joins the unmatched list."""
    view = _nathalia(client, monkeypatch, 0.10)
    row = _row(view, "NATHALIA")
    assert row["effective_bucket"] == "unmatched", row
    assert not [c for c in row["candidates"] if c["match_type"] == "fx_judgment"], row["candidates"]
    assert _row(view, "COL INTERMUNICIPAL")["effective_bucket"] == "unmatched"
    assert [r["vendor"] for r in view["unmatched_receipts"]] == ["Bezerra Ltda"]
    assert view["summary"]["n_review"] == 0


def test_a_rejection_at_the_floor_inside_the_clean_band_stays_in_review_with_the_tools_reason_first(
    client, monkeypatch
):
    p = 0.20
    view = _nathalia(client, monkeypatch, p)
    row = _row(view, "NATHALIA")
    assert row["effective_bucket"] == "review", row
    cands = [c for c in row["candidates"] if (c["fx"] or {}).get("receipt_currency") == "BRL"]
    assert len(cands) == 1, row["candidates"]
    cand = cands[0]

    assert cand["match_type"] == "fx_judgment"
    assert cand["confidence"] == pytest.approx(p)
    assert cand["requires_review"] is True
    # The band the reviewer sees is the band that kept the pair.
    assert cand["fx"]["reference_gap_band"] == "match"
    assert cand["fx"]["reference_gap_pct"] == 1.46

    reason = cand["reason"]
    tool = (f"Charge 5.61 USD vs receipt 28.73 BRL at ECB monthly average "
            f"rate {MONTH_RATE} (2026-07): deviation 1.5%.")
    model = f"FX judgment: likely NOT the same purchase (p={p:.2f})."
    assert reason.startswith(tool), reason
    assert "Demoted to judgment" in reason, reason  # the live row's route in
    assert "Kept for review although the model disagrees: " + model in reason, reason
    assert reason.index(tool) < reason.index(model)
    # The receipt is on no unmatched list: it is held by the review row.
    assert all(r["document_id"] != cand["document_id"] for r in view["unmatched_receipts"])


def _nobre(client, monkeypatch, p: float) -> dict:
    """July's NOBRE pair: 325.88 BRL x 0.192448 = 62.71 USD, the 65.23 charge
    is 4.01% over it, the review zone (3-13%), not the clean band."""
    batch = _month(
        client, monkeypatch,
        ExtractedReceipt(
            date="2026-07-11", total="325.88", currency="BRL",
            vendor="Supermercado Fenix Ltda", reference="NFC-0711",
            line_items=(), confidence=0.9, notes="",
        ),
        p,
        [(datetime(2026, 7, 11), "NOBRE ATACAREJO SAO JOS", "Sale", -65.23)],
    )
    return client.get(f"/api/runs/{batch}").json()


def test_a_pair_the_model_rejects_at_the_floor_outside_the_clean_band_is_not_shown(
    client, monkeypatch
):
    view = _nobre(client, monkeypatch, 0.20)
    row = _row(view, "NOBRE")
    assert row["effective_bucket"] == "unmatched", row
    assert not [c for c in row["candidates"] if c["match_type"] == "fx_judgment"], row["candidates"]
    assert [r["vendor"] for r in view["unmatched_receipts"]] == ["Supermercado Fenix Ltda"]
    assert view["summary"]["n_review"] == 0


def test_a_verdict_just_above_the_floor_is_still_shown_with_the_models_reason(
    client, monkeypatch
):
    """The floor moved by one boundary value, not the band: 0.21 is not a
    rejection, and a pair the tool did not stand behind keeps the model's
    reason as before."""
    view = _nobre(client, monkeypatch, 0.21)
    row = _row(view, "NOBRE")
    assert row["effective_bucket"] == "review", row
    cand = next(c for c in row["candidates"] if c["match_type"] == "fx_judgment")
    assert cand["fx"]["reference_gap_band"] == "review"
    assert cand["reason"].startswith("FX judgment: likely NOT the same purchase (p=0.21)."), cand["reason"]
    assert Decimal(cand["fx"]["reference_converted"]) == Decimal("62.71")
