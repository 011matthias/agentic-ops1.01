"""Backlog item 160 (feedback note #71): a row with a settled category still
says a category is missing.

Owner, 2026-09-20, on July's page: *"this should not be mentioned here i
think..."*. The selector named July's Microsoft Corporation 718.20
(`transaction_id` 49ace8baae6b6723), column 6's first paragraph. Read live
that minute, the row carried BOTH `posting_category` "Software &
Subscriptions" AND `review.reason_code` `partial_uncategorized`, "One or more
receipt lines still need a category before this can post."

Both are true. `posting_category` is the roll-up of the lines that DO carry a
category; the row's second line (25.20, "(illegible)") carries none, and
`books_as[1].unassigned` says so. So the sentence is correct and reads as a
mistake, because it sits beside a filled category field and names nothing.

Pinned here, route-level through the real app:

* the premise, asserted on its own before anything else: the fixture row
  really is partly uncategorized (two lines, exactly one without a category,
  a filled `posting_category`). A field test over a row that is NOT in that
  state would pass while proving nothing, which is how the item-158 gap
  survived;
* `expenses[].uncategorized_lines` names those lines, with the index,
  description and amount the reviewer needs to find them;
* it is the SAME set the verdict is about, so the row cannot name one line
  while the sentence is about another;
* it goes away when a reviewer categorizes the line, through
  `POST /api/runs/{id}/categories` — the override path, which the verdict
  already honours;
* a fully uncategorized row names every line and reads `uncategorized`.
"""
from __future__ import annotations

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

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-160"

# "taxi" is in the line-keyword table, so this line categorizes without an
# LLM key. The other two hit no keyword and no vagueness token, so they land
# REVIEW with no category -- the state the owner's row is in.
CATEGORIZED = "Airport taxi to the venue"
ILLEGIBLE = "Illegible handwriting on the printed copy"
UNREADABLE = "Handwritten note, unreadable"
# The batch carries the entity, as the owner's live row does (from its card),
# so the CATEGORY verdict is the row's headline instead of MISSING ENTITY.
ENTITY = "Corporate Services"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(lines) -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-07-26", total="718.20", currency="USD",
        # A vendor with no registry entry, so nothing stamps a category on
        # the whole receipt before the lines are read (item 149).
        vendor="Trace Item 160 GmbH", reference="G173514057",
        line_items=tuple(
            ExtractedLineItem(description=d, line_total=t) for d, t in lines
        ),
        confidence=0.9, notes="",
    )


def _create_batch(client, label="July 2026"):
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": ENTITY, "label": label})
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


def test_the_fixture_row_is_really_partly_uncategorized(client, monkeypatch):
    """The premise, on its own. Everything below is about a row that shows a
    category AND holds a line without one; if the fixture ever stops being in
    that state, this fails first and says so, instead of the field tests
    passing over a row they were never about."""
    _patch_ocr(monkeypatch, _extraction(
        [(CATEGORIZED, "693.00"), (ILLEGIBLE, "25.20")]
    ))
    row = _row(client, _create_batch(client))

    lines = row["line_items"]
    assert len(lines) == 2, lines
    assert [li["category"] for li in lines] == ["Travel & Transport", None]
    # The row shows a settled category all the same: the roll-up of the line
    # that has one. This is the pair the owner read as a contradiction.
    assert row["posting_category"]["category"] == "Travel & Transport"
    assert row["review"]["reason_code"] == "partial_uncategorized"
    # And the money half already says which part is unassigned.
    assert [b["unassigned"] for b in row["books_as"]] == [False, True]


def test_a_partly_uncategorized_row_names_the_line(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(
        [(CATEGORIZED, "693.00"), (ILLEGIBLE, "25.20")]
    ))
    row = _row(client, _create_batch(client))

    assert row["uncategorized_lines"] == [
        {"index": 1, "description": ILLEGIBLE, "line_total": "25.20"}
    ]
    # The set the sentence is about, not a second opinion on it: every line
    # named here has no category, and every line without one is named.
    named = {e["index"] for e in row["uncategorized_lines"]}
    assert named == {
        li["index"] for li in row["line_items"] if li["category"] is None
    }


def test_a_categorized_row_carries_no_field_at_all(client, monkeypatch):
    """Absent, never null or empty (contract rule 1). A reviewer's own edit
    settles the line, through the route she actually clicks."""
    _patch_ocr(monkeypatch, _extraction(
        [(CATEGORIZED, "693.00"), (ILLEGIBLE, "25.20")]
    ))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]

    resp = client.post(f"/api/runs/{batch}/categories", json={
        "document_id": doc, "line_index": 1,
        "category": "Software & Subscriptions",
    })
    assert resp.status_code == 200, resp.text

    row = _row(client, batch)
    assert "uncategorized_lines" not in row, row.get("uncategorized_lines")
    assert row["review"]["reason_code"] != "partial_uncategorized"


def test_a_fully_uncategorized_row_names_every_line(client, monkeypatch):
    """The other end of the same predicate: nothing categorized at all reads
    `uncategorized`, and every line is named."""
    _patch_ocr(monkeypatch, _extraction(
        [(ILLEGIBLE, "693.00"), (UNREADABLE, "25.20")]
    ))
    row = _row(client, _create_batch(client))

    assert row["review"]["reason_code"] == "uncategorized"
    assert [e["index"] for e in row["uncategorized_lines"]] == [0, 1]
    assert [e["line_total"] for e in row["uncategorized_lines"]] == [
        "693.00", "25.20",
    ]
