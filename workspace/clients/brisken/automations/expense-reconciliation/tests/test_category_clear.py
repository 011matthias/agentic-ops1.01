"""Item 78: a category picked by mistake can be taken back.

The Review expenses dropdown offers the eight categories and no blank, so a
mis-click on an uncategorized row was permanent from the screen. The route
already took `""` as "clear my edit"; nothing pinned what the row then
shows. Pinned here, route-level: clearing drops the reviewer's pick and the
row returns to what the tool had, which for an uncategorized row is no
category at all.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-78"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _batch_with_one_receipt(client, monkeypatch) -> tuple[str, dict]:
    extraction = ExtractedReceipt(
        date="2026-08-12", total="135.00", currency="USD", vendor="Pressmaster FZCO",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    mock = MockLLMClient(extraction_responses=[extraction])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "August 2026"})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    resp = client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("r.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch, _row(client, batch)


def _row(client, batch) -> dict:
    (row,) = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return row


def _category(row) -> "str | None":
    # an uncategorized row carries no posting category at all
    return (row.get("posting_category") or {}).get("category")


def _set_category(client, batch, doc, value):
    return client.put(
        f"/api/runs/{batch}/expenses/{doc}", json={"field": "category", "value": value}
    )


def test_a_mistaken_category_on_an_uncategorized_row_can_be_cleared(client, monkeypatch):
    batch, row = _batch_with_one_receipt(client, monkeypatch)
    doc = row["document_id"]
    assert _category(row) is None, row["posting_category"]

    resp = _set_category(client, batch, doc, "Meals & Entertainment")
    assert resp.status_code == 200, resp.text
    assert _category(_row(client, batch)) == "Meals & Entertainment"

    resp = _set_category(client, batch, doc, "")
    assert resp.status_code == 200, resp.text
    after = _row(client, batch)
    assert _category(after) is None
    assert (after.get("posting_category") or {}).get("source") != "override"


def test_null_clears_like_an_empty_string(client, monkeypatch):
    batch, row = _batch_with_one_receipt(client, monkeypatch)
    doc = row["document_id"]
    assert _set_category(client, batch, doc, "Travel & Transport").status_code == 200
    assert _set_category(client, batch, doc, None).status_code == 200
    assert _category(_row(client, batch)) is None


def test_a_category_outside_the_eight_is_still_refused(client, monkeypatch):
    batch, row = _batch_with_one_receipt(client, monkeypatch)
    resp = _set_category(client, batch, row["document_id"], "Groceries")
    assert resp.status_code == 400
