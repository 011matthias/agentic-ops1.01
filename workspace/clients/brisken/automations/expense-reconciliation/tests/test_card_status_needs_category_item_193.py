"""Item 193: the months strip's chip number has one meaning, needs category.

Owner, 2026-09-24, on the /months card strip: "these numbers next to the card
ending numbers have to be consistent in their meaning". The number was
`n_transactions` (statement lines, credits included, no label), so 1176's "3"
was one charge and two credits and read as nothing in particular. The owner's
pick: every expense on the card that needs a category, all months, each card
its own.

The count is the NEEDS CATEGORY box's own set (`"uncategorized"` in
`expenses[].boxes`, which `summary.n_uncategorized` counts), so a month's cards
plus its no-card section add up to the months list's Needs category column.
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


def _receipt(vendor: str, hint: str | None) -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-09-10", total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("OpenAI", "Visa ...9693"),
            _receipt("Perplexity", None),
            _receipt("Staples", "Visa ...2838"),
            _receipt("Zoom", "Visa ...2838"),
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


def _month(client, label: str, n: int) -> str:
    assert client.put("/api/settings", json={"cards": CORP}).status_code == 200
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(n):
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i + 1]) * 64,
                              "application/octet-stream"))],
        ))
    return batch_id


def test_a_months_cards_add_up_to_its_needs_category_column(client):
    """Per card plus no card, the month's figures here equal the month's own
    `summary.n_uncategorized`, the number its NEEDS CATEGORY box and the
    months list's Needs category column show."""
    september = _month(client, "September 2026", 4)

    status = client.get("/api/cards/status").json()
    here = {
        c["key"]: m["n_needs_category"]
        for c in status["cards"] for m in c["receipt_months"]
        if m["run_id"] == september
    }
    here[""] = sum(
        m["n_needs_category"] for m in status["no_card"]["months"]
        if m["run_id"] == september
    )
    view = client.get(f"/api/expense-batches/{september}").json()
    boxes: dict[str, int] = {}
    for expense in view["expenses"]:
        if "uncategorized" in (expense.get("boxes") or []):
            key = expense["card_section"]
            boxes[key] = boxes.get(key, 0) + 1
    assert {k: v for k, v in here.items() if v} == boxes
    assert sum(here.values()) == view["summary"]["n_uncategorized"]
    assert view["summary"]["n_uncategorized"] > 0, (
        "the instrument must see a row in the box, or equality proves nothing"
    )


def test_each_card_and_no_card_carry_the_total(client):
    """The chip reads the card's own total over every month, and No card
    gets one too (it had no number while the number was charges)."""
    _month(client, "September 2026", 4)
    status = client.get("/api/cards/status").json()
    for card in status["cards"]:
        assert card["n_needs_category"] == sum(
            m["n_needs_category"] for m in card["receipt_months"]
        )
    assert status["no_card"]["n_needs_category"] == sum(
        m["n_needs_category"] for m in status["no_card"]["months"]
    )


def test_the_count_is_the_box_not_the_row_count():
    """Differential: only rows in the NEEDS CATEGORY box count, and a
    decided copy (counts_in_total false) counts for nothing."""
    view = {"expenses": [
        {"card_section": "card-2838", "boxes": ["uncategorized"]},
        {"card_section": "card-2838", "boxes": ["categorized", "ready"]},
        {"card_section": "card-2838", "boxes": ["uncategorized"],
         "counts_in_total": False},
        {"card_section": "", "boxes": ["uncategorized"]},
    ]}
    counts = receipt_card_counts(view)
    assert counts["card-2838"]["n_expenses"] == 2
    assert counts["card-2838"]["n_needs_category"] == 1
    assert counts[""]["n_needs_category"] == 1
