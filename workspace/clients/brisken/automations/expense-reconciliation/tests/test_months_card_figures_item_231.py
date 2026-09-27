"""Item 231: with a card picked, the months list shows that card's figures.

Owner, 2026-09-27, on the /months list with 2838 picked: the Receipts, Needs
category and Set aside columns "need to adjust automatically to only display"
that card's, per month; 2838 counts only its own, its subcards their own.

Receipts and Needs category already had a per-card, per-month figure on
`GET /api/cards/status` (`receipt_months[].n_expenses` / `.n_needs_category`).
Set aside had none: a file the quarantine holds back is on no charge and was
filed under no card. It now files where an unheld receipt does, under the card
its own reading resolves to, else No card, so per month the cards plus No card
add up to the months list's Set aside column exactly as the other two do.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import receipt_card_counts  # noqa: E402

CORP = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "card-9693": {"label": "Credit Card Chase Visa - 9693",
                  "digits": ["9693"], "entity": "Cloud Services"},
}


def _reading(vendor: str | None, hint: str | None, kind: str = "receipt"):
    return ExtractedReceipt(
        date="2026-09-10", total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint, document_type=kind,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            _reading("OpenAI", "Visa ...9693"),
            _reading("Staples", "Visa ...2838"),
            _reading("Perplexity", None),
            # Two pages the quarantine holds back: one prints 2838, one
            # prints no card at all.
            _reading(None, "Visa ...2838", kind="statement"),
            _reading(None, None, kind="report_summary"),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 8,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _september(client) -> str:
    assert client.put("/api/settings", json={"cards": CORP}).status_code == 200
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "September 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(5):
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i + 1]) * 64,
                              "application/octet-stream"))],
        ))
    return batch_id


def _per_card(status: dict, run_id: str, field: str) -> dict[str, int]:
    """`{card key: figure}` for one month, No card under "", zeros dropped."""
    out = {
        c["key"]: m[field]
        for c in status["cards"] for m in c["receipt_months"]
        if m["run_id"] == run_id
    }
    out[""] = sum(
        m[field] for m in status["no_card"]["months"] if m["run_id"] == run_id
    )
    return {k: v for k, v in out.items() if v}


def test_set_aside_files_under_the_card_its_reading_names(client):
    """The page that prints 2838 counts on 2838, the page that prints no
    card counts on No card, and 9693 has none."""
    september = _september(client)
    status = client.get("/api/cards/status").json()
    assert _per_card(status, september, "n_set_aside") == {"card-2838": 1, "": 1}


def test_each_column_adds_up_to_the_months_list(client):
    """Per month, cards plus No card equal the months list's own figure, for
    all three columns the list shows. The months list row is the instrument:
    it is what the page shows under All."""
    september = _september(client)
    status = client.get("/api/cards/status").json()
    listed = next(
        b for b in client.get("/api/expense-batches").json()["batches"]
        if b["batch_id"] == september
    )["summary"]
    assert listed["n_set_aside"] == 2, (
        "the fixture must set two files aside, or the sums prove nothing"
    )
    for field, column in (
        ("n_expenses", "n_expenses"),
        ("n_needs_category", "n_uncategorized"),
        ("n_set_aside", "n_set_aside"),
    ):
        assert sum(_per_card(status, september, field).values()) == listed[column], field


def test_the_month_page_names_each_set_aside_files_card(client):
    """`set_aside[].card_section` on the month's own payload is where the
    roll-up's count comes from, so the two cannot disagree."""
    september = _september(client)
    view = client.get(f"/api/expense-batches/{september}").json()
    assert sorted(e["card_section"] for e in view["set_aside"]) == ["", "card-2838"]


def test_card_and_no_card_totals(client):
    _september(client)
    status = client.get("/api/cards/status").json()
    for card in status["cards"]:
        assert card["n_set_aside"] == sum(m["n_set_aside"] for m in card["receipt_months"])
    assert status["no_card"]["n_set_aside"] == 1


def test_a_restored_file_no_longer_counts_as_set_aside():
    """Differential on the counter: a restored entry is an expense again, so
    it leaves the figure, the rule `summary.n_set_aside` follows."""
    view = {"expenses": [], "set_aside": [
        {"card_section": "card-2838", "restored": False},
        {"card_section": "card-2838", "restored": True},
        {"card_section": "", "restored": False},
    ]}
    counts = receipt_card_counts(view)
    assert counts["card-2838"]["n_set_aside"] == 1
    assert counts["card-2838"]["n_expenses"] == 0
    assert counts[""]["n_set_aside"] == 1
