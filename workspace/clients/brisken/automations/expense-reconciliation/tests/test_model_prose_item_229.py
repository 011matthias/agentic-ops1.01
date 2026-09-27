"""Item 229 (note #95, owner 2026-09-26: "ai slop remove or improve").

The FX judge's reason ended in the model's own sentence, and the review
cause served it again as `cause_detail.model_reasoning`, so April's Matching
page printed "The converted amount of 104.00 USD is close to the transaction
amount, but the vendors are different and the card numbers match only
partially" under a charge whose tool-rate gap was -2.48%. What is served and
printed now stops at the verdict, p and the tool's own conversion; the stored
reason keeps the model's text.
"""
from __future__ import annotations

import io
from decimal import Decimal

import pytest

from expense_recon.llm.client import FxJudgmentResult, MockLLMClient
from expense_recon.matching.judgment import without_model_prose

MODEL_TEXT = "The vendors are different and the card numbers match only partially."


def _verdict(p: float) -> FxJudgmentResult:
    return FxJudgmentResult(
        is_match=p >= 0.5,
        same_purchase_confidence=p,
        implied_rate=0.018,
        converted_amount=Decimal("1.00"),
        reasoning=MODEL_TEXT,
    )


@pytest.fixture
def hosted(tmp_path, monkeypatch):
    """The rematch fixture (a EUR receipt against USD STAPLES 42.50) judged
    "likely NOT" by a model that explains itself; yields (client, batch_id)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import tests.test_rematch_judgment_cache as rj
    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[rj._eur_receipt()], fx_responses=[_verdict(0.4)] * 8
    )
    rj._wire(monkeypatch, mock)
    with TestClient(create_app(tmp_path)) as client:
        client._data_root = tmp_path
        batch_id = rj._create_batch(client)
        rj._attach(client, batch_id)
        yield client, batch_id


def _staples(view):
    return next(r for r in view["rows"] if "STAPLES" in r["vendor"])


def test_the_matching_row_serves_no_model_sentence(hosted):
    client, batch_id = hosted
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    row = _staples(resp.json())
    reason = row["candidates"][0]["reason"]
    assert reason == "FX judgment: likely NOT the same purchase (p=0.40)."
    review = row["review"]
    assert review["cause"] == "model_doubts"
    assert review["cause_detail"]["model_p"] == 0.4
    assert "model_reasoning" not in review["cause_detail"]


def test_the_reconciled_csv_prints_no_model_sentence(hosted):
    client, batch_id = hosted
    resp = client.get(f"/runs/{batch_id}/reconciled.csv")
    assert resp.status_code == 200, resp.text
    assert "FX judgment: likely NOT the same purchase (p=0.40)." in resp.text
    assert MODEL_TEXT not in resp.text
    assert "approx rate" not in resp.text


def test_the_excel_report_prints_no_model_sentence(hosted):
    openpyxl = pytest.importorskip("openpyxl")
    client, batch_id = hosted
    resp = client.get(f"/runs/{batch_id}/report.xlsx")
    assert resp.status_code == 200, resp.text
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    cells = [
        str(c.value) for ws in wb.worksheets for r in ws.iter_rows() for c in r
        if c.value is not None
    ]
    text = "\n".join(cells)
    assert "FX judgment: likely NOT the same purchase (p=0.40)." in text
    assert MODEL_TEXT not in text
    assert "approx rate" not in text


def test_the_tools_conversion_stays_and_other_reasons_pass_through():
    judged = (
        "FX judgment: likely same purchase (p=0.82). 50.00 EUR = 58.11 USD at "
        "the tool's rate 1.162275, +1.2% from the charge. The vendors match."
    )
    assert without_model_prose(judged) == (
        "FX judgment: likely same purchase (p=0.82). 50.00 EUR = 58.11 USD at "
        "the tool's rate 1.162275, +1.2% from the charge."
    )
    assert without_model_prose(
        "FX judgment: likely NOT the same purchase (p=0.30). ~104.0 USD from "
        "551.96 BRL at ~0.19 (approx rate, review). The converted amount of "
        "104.00 USD is close to the transaction amount."
    ) == "FX judgment: likely NOT the same purchase (p=0.30)."
    assert without_model_prose("Ambiguous pick (p=0.70): the date is closer.") == (
        "Ambiguous pick (p=0.70)."
    )
    assert without_model_prose("Ambiguous pick (p=0.70).") == "Ambiguous pick (p=0.70)."
    for other in ("EXACT amount + vendor", "", "FX reference: 1.0% off"):
        assert without_model_prose(other) == other
