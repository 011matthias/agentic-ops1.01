"""Item 190: the card filter leaves the month, so the roll-up must know receipts.

Owner, 2026-09-24: "removing the card filter from inside the months since its
outside now", and "when using this filter, and a month is clicked on by user
he should then only see data from the card that he selected in the filter".

The filter outside the months is `GET /api/cards/status`, and until now it
knew only charges and statements. A month with receipts and no statement yet
(September, while Criss works it) was on no card at all, and receipts on no
card were on nothing, so the strip being removed reached months the filter
replacing it could not. `cards[].receipt_months` and `no_card` close that,
as parallel fields: everything item 185's `/cards` page reads stays as it was.

Everything here runs through the FastAPI app.
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
from expense_recon.web.service import build_card_status  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


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
    # Consumed in upload order, one receipt per upload.
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("OpenAI", "Visa ...9693"),
            _receipt("Perplexity", None),
            _receipt("Staples", "Visa ...2838"),
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
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month_with_receipts(client, label: str, n: int) -> str:
    """A month the way September is today: receipts, no statement."""
    assert client.put("/api/settings", json={"cards": {
        "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                      "entity": "Corporate Services"},
        "card-9693": {"label": "Credit Card Chase Visa - 9693",
                      "digits": ["9693"], "entity": "Cloud Services"},
    }}).status_code == 200
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(n):
        # Distinct bytes: identical files are deduped at upload.
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i]) * 64,
                              "application/octet-stream"))],
        ))
    return batch_id


def _status(client) -> dict:
    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _page_counts(client, batch_id: str) -> dict[str, int]:
    """What the month's own Expenses page counts per card tab."""
    view = client.get(f"/api/expense-batches/{batch_id}").json()
    counts: dict[str, int] = {}
    for expense in view["expenses"]:
        if expense.get("counts_in_total") is False:
            continue
        counts[expense["card_section"]] = counts.get(expense["card_section"], 0) + 1
    return counts


def test_a_month_with_only_receipts_on_a_card_is_named(client):
    """The live shape: 9693 has receipts in August and September and never a
    charge, so the charge-side roll-up listed no month for it. The month is
    named on the receipt side; the charge side still says what it said."""
    september = _month_with_receipts(client, "September 2026", 1)

    payload = _status(client)
    card = {c["key"]: c for c in payload["cards"]}["card-9693"]
    month = next(m for m in payload["months"] if m["run_id"] == september)
    assert card["receipt_months"] == [{
        "run_id": september,
        "label": "September 2026",
        "batch_type": month["batch_type"],
        "n_expenses": 1,
    }]
    assert card["months"] == [], "the charge side is unchanged"
    assert card["never_loaded"] is True, (
        "still no charge and no statement anywhere: /cards reads it as before"
    )


def test_receipts_on_no_card_are_named_by_month(client):
    """The in-month strip had a No card tab; outside the months it needs the
    months that hold such receipts, or they are reachable only unfiltered."""
    september = _month_with_receipts(client, "September 2026", 2)

    no_card = _status(client)["no_card"]
    assert [m["run_id"] for m in no_card["months"]] == [september]
    assert no_card["months"][0]["n_expenses"] == 1
    assert no_card["n_expenses"] == 1


def test_the_counts_are_the_expenses_pages_own(client):
    """Not a second derivation: a month's line here is the count its own
    card tabs show, per card and for no card."""
    september = _month_with_receipts(client, "September 2026", 3)

    payload = _status(client)
    here = {
        c["key"]: m["n_expenses"]
        for c in payload["cards"] for m in c["receipt_months"]
        if m["run_id"] == september
    }
    here[""] = sum(
        m["n_expenses"] for m in payload["no_card"]["months"]
        if m["run_id"] == september
    )
    assert here == _page_counts(client, september) == {
        "card-9693": 1, "": 1, "card-2838": 1,
    }


def test_a_month_the_receipt_count_fails_on_keeps_its_charges(client):
    """One bad month must not blank the page, and it must not take the
    month's charge figures with it either."""
    september = _month_with_receipts(client, "September 2026", 1)

    def broken(run):
        raise RuntimeError("view build failed")

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        payload = build_card_status(store, receipt_cards=broken)
    assert payload["unreadable"] == [september]
    assert [m["run_id"] for m in payload["months"]] == [september]
    assert payload["no_card"] == {"months": [], "n_expenses": 0}
