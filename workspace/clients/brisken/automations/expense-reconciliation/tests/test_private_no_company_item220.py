"""Item 220 step 7: a confirmed private row with no company.

A private expense needs no company: the boxes and the entity ask exempt it
(`expense_boxes`, `_expense_review`). The GL engine reads only the stored
company, so it refused such a row's lines `entity_missing`, and the row said
"Set the company, then pick the account" beside a private badge. Live
2026-09-27: July 0028 Brauhaus Kühler Krug (private on the row) and September
0024 DB Fernverkehr AG (private through the private card list).

The verdict is restated at read time as `private_no_company`, in the same
`pick` state with the same `category_refused` code, so no box and no count
moves. Every assertion reads the grid route (`build_expense_view`, the caller
the fix changed); nothing here writes a category.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from expense_recon.categorize import ENTITY_MISSING  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    PRIVATE_NO_COMPANY,
    PRIVATE_NO_COMPANY_TEXT,
)
from expense_recon.web.store import RunStore  # noqa: E402
from tests.test_card_company_recategorizes_item_206 import (  # noqa: E402
    CARDS,
    CORP,
    _app,
    _month,
    _row,
    _stored,
)

DB_3281 = "DEBIT-MASTERCARD ***** ***** ***** 3281"
OLD_SENTENCE = "Set the company, then pick the account."
# A non-private row with no company asks for it; with no statement loaded for
# the fixture's cards the ask is phrased as waiting for one (item 204).
COMPANY_ASKS = {"needs_entity", "waits_for_statement"}


@pytest.fixture
def web(tmp_path, monkeypatch):
    """Item 206's GL month fixture: two company cards, curated charts."""
    with _app(tmp_path, monkeypatch, gl=True) as c:
        assert c.put("/api/settings", json={"cards": CARDS}).status_code == 200
        yield c


def _summary(web, batch_id) -> dict:
    return web.get(f"/api/expense-batches/{batch_id}").json()["summary"]


def _mark_private(web, batch_id, doc, on: bool = True) -> None:
    body = {"private": True, "reimburse_to": "Dirk Neumann"} if on else {"private": False}
    r = web.post(f"/api/runs/{batch_id}/expenses/{doc}/private", json=body)
    assert r.status_code == 200, r.text


def _reads_private_no_company(row: dict) -> None:
    review = row["review"]
    assert row["private"] is True and not row["legal_entity_id"]
    assert review["state"] == "pick"
    assert review["reason_code"] == "category_refused"
    assert review["refusal"] == PRIVATE_NO_COMPANY
    assert review["reason"] == PRIVATE_NO_COMPANY_TEXT
    assert OLD_SENTENCE not in review["reason"]
    # The to-do boxes already treated the row as private; they stay.
    assert row["boxes"] == ["uncategorized", "private"]


def test_a_row_marked_private_with_no_company_is_not_told_to_set_one(web, monkeypatch):
    batch_id, doc, _client = _month(web, monkeypatch)
    # Before the private mark the row asks for its company, which is right.
    assert _row(web, batch_id)["review"]["reason_code"] in COMPANY_ASKS
    assert _stored(web, batch_id)["refusal"] == ENTITY_MISSING, "precondition"

    _mark_private(web, batch_id, doc)

    _reads_private_no_company(_row(web, batch_id))
    summary = _summary(web, batch_id)
    # Same `pick` state: the row still counts as open and uncategorized.
    assert summary["n_review"] == 1
    assert summary["n_uncategorized"] == 1
    assert summary["n_private"] == 1
    # Read time only: the stored answer is the engine's, untouched.
    assert _stored(web, batch_id)["refusal"] == ENTITY_MISSING


def test_a_row_the_private_card_list_makes_private_reads_the_same(web, monkeypatch):
    """September's DB Fernverkehr path: the private card list, not a row flag."""
    r = web.put("/api/settings", json={"private_cards": {
        "3281": {"person": "Dirk Neumann", "note": "personal DKB card"}}})
    assert r.status_code == 200, r.text
    batch_id, _doc, _client = _month(web, monkeypatch, DB_3281)

    row = _row(web, batch_id)
    assert row["private_source"] == "private_card_list"
    _reads_private_no_company(row)


def test_undoing_private_brings_the_company_ask_back(web, monkeypatch):
    batch_id, doc, _client = _month(web, monkeypatch)
    _mark_private(web, batch_id, doc)
    assert _row(web, batch_id)["review"]["refusal"] == PRIVATE_NO_COMPANY

    _mark_private(web, batch_id, doc, on=False)

    row = _row(web, batch_id)
    assert row["private"] is False
    assert row["review"]["reason_code"] in COMPANY_ASKS
    assert "refusal" not in row["review"]
    assert "needs_entity" in row["boxes"]


def test_a_private_row_that_shows_a_company_keeps_the_engine_verdict(web, monkeypatch):
    """The engine answers for the company a row shows, so the restatement
    never touches such a row; the company sweep re-runs it at its next edit
    (item 206)."""
    batch_id, doc, _client = _month(web, monkeypatch)
    _mark_private(web, batch_id, doc)
    with RunStore(Path(web._data_root) / "recon-web.sqlite") as store:
        store.set_expense_field_override(
            batch_id, doc, "legal_entity", CORP, "2026-09-27T00:00:00")

    row = _row(web, batch_id)
    assert row["legal_entity_id"] == CORP and row["private"] is True
    assert row["review"]["refusal"] == ENTITY_MISSING
