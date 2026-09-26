"""Backlog item 224 step 6: a receipt whose lines do not add up to its total.

The extractor reads a total and a list of lines and nothing compared them.
`_posting_amounts` pro-rates the charged amount across the lines, so the
TOTAL posts either way and a one-account receipt books right whatever its
lines say. A receipt split across accounts does not: each account takes the
share its misread lines give it (live: Lovable 200.00 read as lines of 600.00,
LIDL 140.96 as 116.35 over 33 lines, Brave 3.73 as 8.73).

Pinned here, route-level through the real app (upload, grid, CSV):

* the premise on its own: the split fixture really books to two accounts;
* a split receipt whose lines disagree carries `line_sum_gap`, a
  `line_sum_split` review, and every one of its CSV rows says
  `(lines do not add up)`;
* a one-account receipt carries the field and the note but no review and no
  marker, because the total is what posts;
* lines priced net (lines = total less the printed tax) and lines that agree
  within 0.05 carry nothing, which is most live rows;
* a missing category still outranks the check.
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-224"
ENTITY = "Corporate Services"
MARK = "(lines do not add up)"
# Two line keywords that categorize without an LLM key, into different
# categories, so the receipt splits; and one that hits nothing.
TAXI = "Airport taxi to the venue"
COFFEE = "Coffee for the team"
ILLEGIBLE = "Illegible handwriting on the printed copy"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _patch_ocr(monkeypatch, extraction):
    mock = MockLLMClient(extraction_responses=[extraction])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(total, lines, *, tax=None) -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-07-26", total=total, currency="USD",
        vendor="Trace Item 224 GmbH", reference="LS-224",
        line_items=tuple(
            ExtractedLineItem(description=d, line_total=t) for d, t in lines
        ),
        confidence=0.9, notes="", tax=tax,
    )


def _upload(client, monkeypatch, extraction) -> str:
    _patch_ocr(monkeypatch, extraction)
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": ENTITY, "label": "July 2026"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("r0.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _row(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    expenses = resp.json()["expenses"]
    assert len(expenses) == 1, expenses
    return expenses[0]


def _pick_accounts(client, batch_id, picks) -> None:
    """A reviewer's per-line picks, through the route the grid calls: each
    `(line_index, category, account)`. Two lines on two accounts is how a
    receipt comes to split; with no chart the keyword categories alone all
    book to the one unmapped placeholder."""
    doc = _row(client, batch_id)["document_id"]
    for index, category, account in picks:
        resp = client.post(f"/api/runs/{batch_id}/categories", json={
            "document_id": doc, "line_index": index,
            "category": category, "zoho_account": account,
        })
        assert resp.status_code == 200, resp.text
        assert "ignored" not in resp.json(), resp.json()


SPLIT = [
    (0, "Travel & Transport", "6100 Travel"),
    (1, "Meals & Entertainment", "6002 Meals"),
]


def _csv_descriptions(client, batch_id) -> list[str]:
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert rows, resp.text
    return [r["Expense Description"] for r in rows]


def test_the_split_fixture_really_books_to_two_accounts(client, monkeypatch):
    """The premise. Lines that agree with the total, split across two
    categories: two `books_as` parts, no gap field, no marker. If the fixture
    ever stops splitting, this fails first instead of the split tests passing
    over a one-account row."""
    batch_id = _upload(client, monkeypatch, _extraction(
        "600.00", [(TAXI, "400.00"), (COFFEE, "200.00")]
    ))
    _pick_accounts(client, batch_id, SPLIT)
    row = _row(client, batch_id)
    assert row["is_split"] is True, row["books_as"]
    assert [b["account"] for b in row["books_as"]] == ["6100 Travel", "6002 Meals"]
    assert not any(MARK in d for d in _csv_descriptions(client, batch_id))
    assert "line_sum_gap" not in row and "line_sum_note" not in row
    assert row["review"]["reason_code"] != "line_sum_split"


def test_a_split_receipt_whose_lines_disagree_asks_for_a_check(client, monkeypatch):
    batch_id = _upload(client, monkeypatch, _extraction(
        "200.00", [(TAXI, "400.00"), (COFFEE, "200.00")]
    ))
    _pick_accounts(client, batch_id, SPLIT)
    row = _row(client, batch_id)
    assert row["is_split"] is True, row["books_as"]
    # Signed lines minus total; the total still posts, pro-rated 2:1.
    assert row["line_sum_gap"] == "400.00"
    assert [b["amount"] for b in row["books_as"]] == ["133.33", "66.67"]
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "line_sum_split"
    assert row["review"]["line_sum_gap"] == "400.00"
    assert "600.00 USD, not the total 200.00 USD" in row["review"]["reason"]
    assert "split across accounts" in row["line_sum_note"]
    descriptions = _csv_descriptions(client, batch_id)
    assert len(descriptions) == 2, descriptions
    assert all(d.endswith(MARK) for d in descriptions), descriptions


def test_a_one_account_receipt_reports_the_gap_and_posts_its_total(
    client, monkeypatch,
):
    batch_id = _upload(client, monkeypatch, _extraction(
        "200.00", [(TAXI, "450.00"), ("Taxi back to the airport", "150.00")]
    ))
    row = _row(client, batch_id)
    assert row["is_split"] is False, row["books_as"]
    assert row["line_sum_gap"] == "400.00"
    assert row["line_sum_note"] == (
        "The lines add up to 600.00 USD, not the total 200.00 USD. "
        "The total is what posts."
    )
    assert row["review"]["reason_code"] != "line_sum_split"
    assert [b["amount"] for b in row["books_as"]] == ["200.00"]
    assert not any(MARK in d for d in _csv_descriptions(client, batch_id))


def test_lines_short_of_the_total_read_as_a_negative_gap(client, monkeypatch):
    row = _row(client, _upload(client, monkeypatch, _extraction(
        "140.96", [(TAXI, "116.35")]
    )))
    assert row["line_sum_gap"] == "-24.61"
    assert "116.35 USD, not the total 140.96 USD" in row["line_sum_note"]


@pytest.mark.parametrize(
    ("total", "lines", "tax"),
    [
        # priced net: 180.00 of lines, 34.20 VAT, 214.20 total (Anthropic)
        ("214.20", [(TAXI, "180.00")], "34.20"),
        # within the tolerance
        ("600.04", [(TAXI, "400.00"), (COFFEE, "200.00")], None),
        # agree exactly
        ("600.00", [(TAXI, "400.00"), (COFFEE, "200.00")], None),
    ],
)
def test_lines_that_add_up_carry_nothing(client, monkeypatch, total, lines, tax):
    batch_id = _upload(client, monkeypatch, _extraction(total, lines, tax=tax))
    if len(lines) > 1:
        _pick_accounts(client, batch_id, SPLIT)
    row = _row(client, batch_id)
    assert "line_sum_gap" not in row and "line_sum_note" not in row, row
    assert row["review"]["reason_code"] != "line_sum_split"
    assert not any(MARK in d for d in _csv_descriptions(client, batch_id))


def test_a_missing_category_outranks_the_check(client, monkeypatch):
    """A split row with an uncategorized line is asked for the category
    first; the gap still rides on the row and the CSV still says it."""
    batch_id = _upload(client, monkeypatch, _extraction(
        "5.00", [(TAXI, "3.00"), (ILLEGIBLE, "2.76")]
    ))
    _pick_accounts(client, batch_id, SPLIT[:1])
    row = _row(client, batch_id)
    assert row["is_split"] is True, row["books_as"]
    assert row["review"]["state"] == "pick", row["review"]
    assert row["review"]["reason_code"] == "partial_uncategorized"
    assert row["line_sum_gap"] == "0.76"
    assert all(d.endswith(MARK) for d in _csv_descriptions(client, batch_id))
