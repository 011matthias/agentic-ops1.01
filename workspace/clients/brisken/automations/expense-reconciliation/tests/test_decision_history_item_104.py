"""Item 104: a decision history, with a name on every line.

Before this, every verdict was an upsert: the previous value was gone the
moment the next one landed. Nobody could answer "who confirmed this, and
when", and a bulk action or a re-match that moved forty rows left nothing
behind saying so. The tool knew "tool" versus "reviewer" but not WHICH
person: Criss logs in with her own code and her feedback notes still read
"operator", because the month's operator column comes from the server's
environment rather than from who signed in.

Route-level through the real app, behind the password gate, with two named
codes so the ledger has two people to tell apart:

* a confirm, a reject, a manual match, a disposition, a charge category, a
  receipt-line category and a duplicate ruling each leave one line carrying
  the row, the old value, the new value, who, when and what triggered it;
* a write that changes nothing leaves no line (a re-match writes every
  charge on the month; recording all of them would bury the four that moved);
* the name is the LOGIN's, not the server's, so criss and matthias are told
  apart on the same machine;
* undo puts the value back, appends its own line and stamps the original;
* undo is REFUSED when the row has moved since, because writing the old
  value back would silently throw the later change away;
* a duplicate ruling is recorded but not undone here: reversing it has to
  re-match the month, which is the resolve route's own job.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import decision_history as dh  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-104"
CRISS_CODE = "criss-code-104"
MATTHIAS_CODE = "matthias-code-104"

HEADERS = ("Date", "Description", "Type", "Amount")
LOVABLE = (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00)
PRESSMASTER = (datetime(2026, 8, 18), "PRESSMASTER FZCO", "Sale", -220.00)
FEE = (datetime(2026, 8, 20), "UBER ONE ANNUAL FEE", "Fee", -95.00)
PAYMENT = (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 111.00)
# The mock categorizer guesses this vendor from its name (source VENDOR),
# so its row reads `vendor_guess` and note #62's Confirm applies to it.
UBER = (datetime(2026, 8, 20), "UBER TRIP", "Sale", -22.30)

ENTITY = "Corporate Services"
PICK = "Professional Services"


@pytest.fixture
def app_root(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    monkeypatch.setenv(
        "EXPENSE_RECON_OPERATOR_CODES",
        f"{CRISS_CODE}:criss,{MATTHIAS_CODE}:matthias",
    )
    monkeypatch.setenv("EXPENSE_RECON_AUTH_SECRET", "item-104-test-secret")
    return tmp_path


def _signed_in(app, code):
    client = TestClient(app)
    client.__enter__()
    login = client.post("/api/login", json={"code": code})
    assert login.status_code == 200, login.text
    client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
    return client


@pytest.fixture
def client(app_root):
    app = create_app(app_root)
    c = _signed_in(app, CRISS_CODE)
    c._app = app
    c._data_root = app_root
    try:
        yield c
    finally:
        c.__exit__(None, None, None)


@pytest.fixture
def matthias(client):
    """A second session on the SAME app, signed in with the other code."""
    c = _signed_in(client._app, MATTHIAS_CODE)
    try:
        yield c
    finally:
        c.__exit__(None, None, None)


def _extraction(vendor, total, date, currency="USD"):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, rows, *extractions, label="August 2026"):
    """A batch with a statement attached and NOTHING decided, so the ledger
    starts empty and every line a test sees is the one it made."""
    _wire(monkeypatch, *extractions)
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": ENTITY, "label": label}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if extractions:
        files = [
            ("files", (f"r-{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
            for i in range(len(extractions))
        ]
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts", files=files
        ))
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch_id


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _tx(client, batch_id, vendor_or_desc):
    for row in _view(client, batch_id)["rows"]:
        if vendor_or_desc in (row.get("vendor") or "", row.get("description") or ""):
            return row["transaction_id"]
    raise AssertionError(f"no row for {vendor_or_desc!r}")


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _doc(client, batch_id):
    # The first receipt in the month, by the id every category route
    # takes. Receipts live on the expense-batch payload, not on the run.
    expenses = _grid(client, batch_id)["expenses"]
    assert expenses, "fixture built no expense to categorize"
    return expenses[0]["document_id"]


def _history(client, batch_id, **params):
    resp = client.get(f"/api/runs/{batch_id}/history", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _entries(client, batch_id, **params):
    return _history(client, batch_id, **params)["entries"]


def _decide(client, batch_id, tx_id, status, chosen=None):
    body = {"transaction_id": tx_id, "status": status}
    if chosen is not None:
        body["chosen_document_id"] = chosen
    return client.post(f"/api/runs/{batch_id}/decisions", json=body)


def _undo(client, batch_id, entry_id):
    return client.post(f"/api/runs/{batch_id}/history/{entry_id}/undo")


# ---------------------------------------------------------------- recording


def test_a_month_that_nobody_touched_has_an_empty_history(client, monkeypatch):
    """The honest answer for every month that existed before this shipped."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    body = _history(client, batch_id)
    assert body["entries"] == []
    assert body["n_entries"] == 0
    assert body["has_more"] is False


def test_a_confirm_leaves_one_line_with_who_what_and_when(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")

    assert _decide(client, batch_id, tx, "confirmed").status_code == 200

    entries = _entries(client, batch_id)
    assert len(entries) == 1
    line = entries[0]
    assert line["row_key"] == tx
    assert line["row_kind"] == "charge"
    assert line["field"] == "decision"
    assert line["new"]["status"] == "confirmed"
    assert line["who"] == "criss"
    assert line["trigger"] == "click"
    assert line["undoable"] is True
    assert line["at"]
    # The reader's one-liner says what moved, in words.
    assert "confirmed" in line["summary"]


def test_the_name_is_the_login_not_the_server(client, matthias, monkeypatch):
    """The confusion item 104 names: the month's operator column came from
    the server's environment, so Criss's work read as the developer's."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")

    assert _decide(client, batch_id, tx, "confirmed").status_code == 200
    assert _decide(matthias, batch_id, tx, "rejected").status_code == 200

    entries = _entries(client, batch_id)
    assert [e["who"] for e in entries] == ["matthias", "criss"]
    assert [e["new"]["status"] for e in entries] == ["rejected", "confirmed"]
    # And the second line's "old" is the first line's "new": the chain holds.
    assert entries[0]["old"]["status"] == "confirmed"


def test_a_write_that_changes_nothing_leaves_no_line(client, monkeypatch):
    """A re-match writes every charge on the month. Recording the ones that
    did not move would bury the ones that did."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")

    _decide(client, batch_id, tx, "confirmed")
    _decide(client, batch_id, tx, "confirmed")
    _decide(client, batch_id, tx, "confirmed")

    assert len(_entries(client, batch_id)) == 1


def test_newest_first_and_one_rows_own_story(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, FEE, PAYMENT])
    one = _tx(client, batch_id, "PRESSMASTER FZCO")
    two = _tx(client, batch_id, "UBER ONE ANNUAL FEE")

    _decide(client, batch_id, one, "confirmed")
    _decide(client, batch_id, two, "confirmed")
    _decide(client, batch_id, one, "rejected")

    entries = _entries(client, batch_id)
    assert len(entries) == 3
    assert [e["id"] for e in entries] == sorted((e["id"] for e in entries), reverse=True)

    mine = _entries(client, batch_id, row_key=one)
    assert len(mine) == 2
    assert {e["row_key"] for e in mine} == {one}


def test_paging_walks_backwards_without_repeating(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, FEE, PAYMENT])
    one = _tx(client, batch_id, "PRESSMASTER FZCO")
    for status in ("confirmed", "rejected", "pending", "confirmed"):
        _decide(client, batch_id, one, status)

    first = _history(client, batch_id, limit=2)
    assert len(first["entries"]) == 2
    assert first["n_entries"] == 4
    assert first["has_more"] is True

    older = _history(client, batch_id, limit=2, before_id=first["entries"][-1]["id"])
    assert [e["id"] for e in older["entries"]] < [e["id"] for e in first["entries"]]
    assert not ({e["id"] for e in older["entries"]} & {e["id"] for e in first["entries"]})


def test_has_more_is_false_when_the_page_exactly_fills(client, monkeypatch):
    """A full page is not evidence of a next one. Comparing the page size
    to the limit says "maybe" and reads as "yes", which hands the reader a
    next page that is empty."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, FEE, PAYMENT])
    one = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, one, "confirmed")
    _decide(client, batch_id, one, "rejected")

    exact = _history(client, batch_id, limit=2)
    assert len(exact["entries"]) == 2
    assert exact["n_entries"] == 2
    assert exact["has_more"] is False

    short = _history(client, batch_id, limit=1)
    assert short["has_more"] is True


def test_a_bulk_confirm_records_one_line_per_row_it_moved(client, monkeypatch):
    """Through `decisions/bulk`, the caller the SPA's Reject-all uses."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, FEE, LOVABLE, PAYMENT])
    ids = [
        r["transaction_id"] for r in _view(client, batch_id)["rows"]
        if r.get("description") != "Payment Thank You-Mobile"
    ]
    resp = client.post(
        f"/api/runs/{batch_id}/decisions/bulk",
        json={"transaction_ids": ids, "status": "rejected"},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["updated"]
    assert updated >= 1

    entries = _entries(client, batch_id)
    # Exactly the rows the route says it wrote, and every line says `bulk`.
    assert len(entries) == updated
    assert {e["trigger"] for e in entries} == {"bulk"}
    assert {e["who"] for e in entries} == {"criss"}
    assert {e["new"]["status"] for e in entries} == {"rejected"}


def test_confirm_ready_records_through_its_own_route(client, monkeypatch):
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    resp = client.post(f"/api/runs/{batch_id}/decisions/confirm-ready")
    assert resp.status_code == 200, resp.text
    confirmed = resp.json()["confirmed"]

    entries = _entries(client, batch_id)
    assert len(entries) == confirmed
    if confirmed:
        assert {e["trigger"] for e in entries} == {"bulk"}
        assert {e["who"] for e in entries} == {"criss"}


def test_confirm_matched_records_through_its_own_route(client, monkeypatch):
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    resp = client.post(f"/api/runs/{batch_id}/decisions/confirm-matched")
    assert resp.status_code == 200, resp.text
    confirmed = resp.json()["confirmed"]

    entries = _entries(client, batch_id)
    assert len(entries) == confirmed
    if confirmed:
        assert {e["trigger"] for e in entries} == {"bulk"}


def test_a_manual_match_records_the_receipt_it_chose(client, monkeypatch):
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    tx = _tx(client, batch_id, "LOVABLE")
    doc = _doc(client, batch_id)
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": tx, "document_id": doc},
    )
    assert resp.status_code == 200, resp.text

    line = _entries(client, batch_id, row_key=tx)[0]
    assert line["field"] == "decision"
    assert line["new"]["chosen_document_id"] == doc
    assert line["trigger"] == "click"
    assert line["who"] == "criss"


def test_a_disposition_records_its_own_field(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    resp = client.post(
        f"/api/runs/{batch_id}/disposition",
        json={"transaction_id": tx, "disposition": "reimbursable_personal"},
    )
    assert resp.status_code == 200, resp.text

    line = _entries(client, batch_id)[0]
    assert line["field"] == "disposition"
    assert line["new"] == "reimbursable_personal"
    assert line["who"] == "criss"
    assert "disposition" in line["summary"]


def test_a_charge_category_records_the_pick(client, monkeypatch):
    """Item 109's edit: a category on a charge that has no receipt."""
    batch_id = _month(client, monkeypatch, [FEE, PAYMENT])
    tx = _tx(client, batch_id, "UBER ONE ANNUAL FEE")
    resp = client.put(
        f"/api/runs/{batch_id}/charges/{tx}/category", json={"category": PICK}
    )
    assert resp.status_code == 200, resp.text

    line = _entries(client, batch_id, row_key=tx)[0]
    assert line["field"] == "charge_category"
    assert line["new"]["category"] == PICK
    assert line["old"] is None
    assert line["detail"]["line_index"] is not None


def test_a_receipt_line_category_records_one_line_per_line_changed(
    client, monkeypatch
):
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    doc = _doc(client, batch_id)

    resp = client.post(
        f"/api/runs/{batch_id}/categories",
        json={"document_id": doc, "line_index": 0, "category": PICK},
    )
    assert resp.status_code == 200, resp.text

    lines = [e for e in _entries(client, batch_id) if e["field"] == "receipt_category"]
    assert len(lines) == 1
    assert lines[0]["row_kind"] == "receipt"
    assert lines[0]["new"]["category"] == PICK
    assert lines[0]["trigger"] == "click"

    # The same category again moves nothing, so it records nothing.
    client.post(
        f"/api/runs/{batch_id}/categories",
        json={"document_id": doc, "line_index": 0, "category": PICK},
    )
    again = [e for e in _entries(client, batch_id) if e["field"] == "receipt_category"]
    assert len(again) == 1


# -------------------------------------------------------------------- undo


def test_undo_puts_the_value_back_and_appends_its_own_line(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, tx, "confirmed")
    _decide(client, batch_id, tx, "rejected")

    reject_line = _entries(client, batch_id)[0]
    assert reject_line["new"]["status"] == "rejected"

    resp = _undo(client, batch_id, reject_line["id"])
    assert resp.status_code == 200, resp.text

    row = next(
        r for r in _view(client, batch_id)["rows"] if r["transaction_id"] == tx
    )
    assert row["status"] == "confirmed"

    entries = _entries(client, batch_id)
    # The undo is its own line, and the original still says what it did.
    assert entries[0]["trigger"] == "undo"
    assert entries[0]["new"]["status"] == "confirmed"
    assert entries[0]["old"]["status"] == "rejected"
    original = next(e for e in entries if e["id"] == reject_line["id"])
    assert original["new"]["status"] == "rejected"
    assert original["undone_at"]
    assert original["undone_by"] == "criss"
    assert original["undoable"] is False


def test_undo_of_a_first_verdict_returns_the_row_to_pending(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, tx, "confirmed")

    line = _entries(client, batch_id)[0]
    assert _undo(client, batch_id, line["id"]).status_code == 200

    row = next(
        r for r in _view(client, batch_id)["rows"] if r["transaction_id"] == tx
    )
    assert row["status"] == "pending"
    # The undo line says `pending`, which is what it actually restored --
    # not the `null` the original line recorded as "there was no row".
    assert _entries(client, batch_id)[0]["new"]["status"] == "pending"


def test_undo_is_refused_when_the_row_moved_since(client, monkeypatch):
    """The guard that matters: undoing Tuesday's line must not silently
    throw Thursday's work away."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, tx, "confirmed")
    stale = _entries(client, batch_id)[0]
    _decide(client, batch_id, tx, "rejected")

    resp = _undo(client, batch_id, stale["id"])
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "history_superseded"

    row = next(
        r for r in _view(client, batch_id)["rows"] if r["transaction_id"] == tx
    )
    assert row["status"] == "rejected"  # untouched


def test_undo_twice_is_refused(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, tx, "confirmed")
    line = _entries(client, batch_id)[0]

    assert _undo(client, batch_id, line["id"]).status_code == 200
    second = _undo(client, batch_id, line["id"])
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "history_already_undone"


def test_undo_of_a_category_restores_the_previous_pick(client, monkeypatch):
    batch_id = _month(client, monkeypatch, [FEE, PAYMENT])
    tx = _tx(client, batch_id, "UBER ONE ANNUAL FEE")
    client.put(f"/api/runs/{batch_id}/charges/{tx}/category", json={"category": PICK})
    client.put(
        f"/api/runs/{batch_id}/charges/{tx}/category",
        json={"category": "Software & Subscriptions"},
    )
    latest = _entries(client, batch_id, row_key=tx)[0]
    assert latest["new"]["category"] == "Software & Subscriptions"

    assert _undo(client, batch_id, latest["id"]).status_code == 200
    restored = _entries(client, batch_id, row_key=tx)[0]
    assert restored["trigger"] == "undo"
    assert restored["new"]["category"] == PICK


def test_a_duplicate_ruling_is_recorded_but_not_undone_here(client, monkeypatch):
    """Reversing a duplicate ruling has to re-match the month (item 56), so
    the one-click undo is withheld rather than leaving the month saying one
    thing and matching another. The CHANGE is still on the record."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": "group-104", "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text

    line = _entries(client, batch_id)[0]
    assert line["field"] == "duplicate"
    assert line["row_kind"] == "group"
    assert line["old"] is None  # nothing had been ruled on this group
    assert line["new"] == "ignore"
    assert line["who"] == "criss"
    assert line["undoable"] is False

    # A SECOND ruling has to carry the first as its old value, or the
    # ledger cannot show that a ruling was changed rather than made.
    second = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": "group-104", "resolution": "confirmed"},
    )
    assert second.status_code == 200, second.text
    latest = _entries(client, batch_id)[0]
    assert latest["old"] == "ignore"
    assert latest["new"] == "confirmed"

    refused = _undo(client, batch_id, line["id"])
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "history_not_undoable"


def test_history_refuses_an_unknown_run_and_a_foreign_entry(client, monkeypatch):
    one = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    two = _month(client, monkeypatch, [FEE, PAYMENT], label="July 2026")
    tx = _tx(client, one, "PRESSMASTER FZCO")
    _decide(client, one, tx, "confirmed")
    line = _entries(client, one)[0]

    assert client.get("/api/runs/no-such-run/history").status_code == 404
    # An entry id that belongs to another month is not reachable through it.
    foreign = _undo(client, two, line["id"])
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["code"] == "history_entry_not_found"


def test_the_gate_covers_both_routes(app_root):
    """Neither route is in the open set; a session is required."""
    app = create_app(app_root)
    with TestClient(app) as anon:
        assert anon.get("/api/runs/whatever/history").status_code == 401
        assert anon.post("/api/runs/whatever/history/1/undo").status_code == 401


# ------------------------------------- the sites the item's text undercounted
#
# The item named "the four write points". Enumerating every set_decision /
# set_category_override call in src/ found nine, and then three more that are
# reviewer-driven and were still silent. A ledger with invisible holes is
# worse than no ledger, because it gets trusted.


def test_confirming_the_tools_guess_is_itself_a_line(client, monkeypatch):
    """Note #62's Confirm writes an override where there was none. That is a
    reviewer verdict and it left no trace."""
    batch_id = _month(
        client, monkeypatch, [UBER, PAYMENT],
        _extraction("Uber", 22.30, "2026-08-20"),
    )
    doc = _doc(client, batch_id)
    grid = _grid(client, batch_id)["expenses"][0]
    assert grid["category_confirmable"] is True, grid["review"]
    resp = client.post(f"/api/runs/{batch_id}/expenses/{doc}/confirm-category")
    assert resp.status_code == 200, resp.text

    lines = [e for e in _entries(client, batch_id) if e["field"] == "receipt_category"]
    assert lines, "confirming the guess recorded nothing"
    assert lines[0]["row_key"] == doc
    assert lines[0]["who"] == "criss"
    assert lines[0]["new"] is not None
    # `click`, not the `bulk` the whole-expense PUT writes: keeping a
    # guess is one decision about one receipt.
    assert {line["trigger"] for line in lines} == {"click"}


def test_an_expense_field_edit_of_the_category_is_a_line(client, monkeypatch):
    """`PUT /expenses/{doc}` folds category edits into the same override
    table the category route writes; it recorded nothing."""
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    doc = _doc(client, batch_id)
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "category", "value": PICK},
    )
    assert resp.status_code == 200, resp.text

    lines = [e for e in _entries(client, batch_id) if e["field"] == "receipt_category"]
    assert lines, "the expense field edit recorded nothing"
    assert {line["new"]["category"] for line in lines} == {PICK}
    assert {line["trigger"] for line in lines} == {"bulk"}
    assert {line["who"] for line in lines} == {"criss"}

    # And the same value again moves nothing, so it records nothing more.
    n = len(lines)
    client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "category", "value": PICK},
    )
    again = [e for e in _entries(client, batch_id) if e["field"] == "receipt_category"]
    assert len(again) == n


def test_attaching_a_mailed_receipt_by_hand_is_a_line(client, monkeypatch):
    """The attach records a confirmed decision against the new document, so
    the charge changed verdict with nothing on the record."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _wire(monkeypatch, _extraction("PRESSMASTER FZCO", 220.00, "2026-08-18"))

    resp = client.post(
        f"/api/runs/{batch_id}/transactions/{tx}/receipt",
        files={"file": ("mailed.jpg", JPG + b"-attach", "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text

    lines = _entries(client, batch_id, row_key=tx)
    assert lines, "the manual attach recorded nothing"
    assert lines[0]["field"] == "decision"
    assert lines[0]["new"]["status"] == "confirmed"
    assert lines[0]["new"]["chosen_document_id"]
    assert lines[0]["who"] == "criss"


# ------------------------------------------ what the adversarial review found
#
# Every test below reproduces a defect an adversarial reviewer found in the
# first cut. They were written before the fixes and watched go from red to
# green, which is the only evidence that a fix is wired.


def test_an_account_only_pick_is_recorded_and_survives_an_undo(client, monkeypatch):
    """The review's one data-loss defect.

    `_category_value` collapsed "no override at all" and "an override with an
    account but no category" to the same `None`. Two consequences: setting
    only the account recorded NO line, and an undo of an older line compared
    equal to the row's present value, so it was allowed and overwrote the
    account pick with nothing to show for it.
    """
    batch_id = _month(client, monkeypatch, [FEE, PAYMENT])
    tx = _tx(client, batch_id, "UBER ONE ANNUAL FEE")
    url = f"/api/runs/{batch_id}/charges/{tx}/category"

    assert client.put(url, json={"category": PICK}).status_code == 200
    assert client.put(url, json={"category": ""}).status_code == 200
    stale = _entries(client, batch_id, row_key=tx)[0]
    assert stale["new"] is None  # the clear

    # An account with no category is a reviewer decision and is stored.
    before = len(_entries(client, batch_id, row_key=tx))
    assert client.put(url, json={"zoho_account": "6100 Consulting"}).status_code == 200
    after = _entries(client, batch_id, row_key=tx)
    assert len(after) == before + 1, "an account-only pick recorded nothing"
    assert after[0]["new"]["zoho_account"] == "6100 Consulting"

    # And the stale line can no longer be put back over it.
    resp = _undo(client, batch_id, stale["id"])
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "history_superseded"


def test_a_first_disposition_is_not_offered_an_undo_it_cannot_honour(
    client, monkeypatch
):
    """There is no "no disposition" value to write back, so the button would
    always have failed, and with the wrong code."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    assert client.post(
        f"/api/runs/{batch_id}/disposition",
        json={"transaction_id": tx, "disposition": "reimbursable_personal"},
    ).status_code == 200

    first = _entries(client, batch_id)[0]
    assert first["old"] is None
    assert first["undoable"] is False, "offered an undo that cannot be honoured"

    refused = _undo(client, batch_id, first["id"])
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "history_not_undoable"

    # A SECOND disposition has a previous value, so that one IS undoable.
    assert client.post(
        f"/api/runs/{batch_id}/disposition",
        json={"transaction_id": tx, "disposition": "do_not_export"},
    ).status_code == 200
    second = _entries(client, batch_id)[0]
    assert second["undoable"] is True
    assert _undo(client, batch_id, second["id"]).status_code == 200


def test_confirm_ready_actually_confirms_something(client, monkeypatch):
    """The review caught the old version asserting `0 == 0`: its fixture
    confirmed nothing, so it passed with the wiring deleted."""
    batch_id = _month(
        client, monkeypatch, [LOVABLE, PAYMENT],
        _extraction("LOVABLE", 15.00, "2026-08-31"),
    )
    doc = _doc(client, batch_id)
    # Give the line a category of the reviewer's own, which is what moves the
    # row into `ready` for the bulk confirm.
    assert client.post(
        f"/api/runs/{batch_id}/categories",
        json={"document_id": doc, "line_index": 0, "category": PICK},
    ).status_code == 200

    resp = client.post(f"/api/runs/{batch_id}/decisions/confirm-ready")
    assert resp.status_code == 200, resp.text
    confirmed = resp.json()["confirmed"]
    assert confirmed >= 1, "fixture confirmed nothing, so this proves nothing"

    lines = [e for e in _entries(client, batch_id) if e["field"] == "decision"]
    assert len(lines) == confirmed
    assert {line["trigger"] for line in lines} == {"bulk"}
    assert {line["who"] for line in lines} == {"criss"}


def test_the_per_row_count_counts_that_row(client, monkeypatch):
    """`n_entries` was the month's total even when the list was filtered to
    one row, and the SPA's per-row fold reads exactly that filter."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, FEE, PAYMENT])
    one = _tx(client, batch_id, "PRESSMASTER FZCO")
    two = _tx(client, batch_id, "UBER ONE ANNUAL FEE")
    _decide(client, batch_id, one, "confirmed")
    _decide(client, batch_id, one, "rejected")
    _decide(client, batch_id, two, "confirmed")

    whole = _history(client, batch_id)
    assert whole["n_entries"] == 3

    row = _history(client, batch_id, row_key=one)
    assert len(row["entries"]) == 2
    assert row["n_entries"] == 2, "the per-row fold showed the month's count"


def test_the_summary_does_not_say_category_twice(client, monkeypatch):
    """`describe` is the reader-facing line; it read
    "category category Professional Services to none"."""
    batch_id = _month(client, monkeypatch, [FEE, PAYMENT])
    tx = _tx(client, batch_id, "UBER ONE ANNUAL FEE")
    url = f"/api/runs/{batch_id}/charges/{tx}/category"
    assert client.put(url, json={"category": PICK}).status_code == 200
    # The doubling only shows once there is an OLD dict to render as well,
    # so a single edit would not have reproduced it.
    assert client.put(url, json={"category": "Software & Subscriptions"}).status_code == 200

    summary = _entries(client, batch_id, row_key=tx)[0]["summary"]
    assert "category category" not in summary, summary
    assert summary == f"category {PICK} to Software & Subscriptions", summary


def test_deleting_a_month_takes_its_history_with_it(client, monkeypatch):
    """`delete_run` clears every other per-run table; the ledger was left
    behind, unreachable through the API."""
    batch_id = _month(client, monkeypatch, [PRESSMASTER, PAYMENT])
    tx = _tx(client, batch_id, "PRESSMASTER FZCO")
    _decide(client, batch_id, tx, "confirmed")
    assert _history(client, batch_id)["n_entries"] == 1

    # The delete route wants the label typed back, which is its own guard.
    resp = client.post(
        f"/api/runs/{batch_id}/delete", json={"confirm": batch_id}
    )
    assert resp.status_code == 200, resp.text

    from expense_recon.web.store import RunStore
    db = RunStore(client._data_root / "recon-web.sqlite")
    try:
        left = db.list_history(batch_id, limit=50)
    finally:
        db.conn.close()
    assert left == [], f"{len(left)} orphaned history rows survived the delete"


def test_the_gate_lets_a_session_through(app_root):
    """The 401 half passed with both routes deleted (the middleware answers
    before routing), so it proved nothing on its own."""
    app = create_app(app_root)
    with TestClient(app) as anon:
        assert anon.get("/api/runs/whatever/history").status_code == 401
    signed = _signed_in(app, CRISS_CODE)
    try:
        # 404 for an unknown run, not 401 and not 405: the route exists and
        # the session reached it.
        resp = signed.get("/api/runs/no-such-run/history")
        assert resp.status_code == 404, resp.text
        assert resp.json()["code"] == "run_not_found"
    finally:
        signed.__exit__(None, None, None)


# ------------------------------------------------------------- pure module


def test_no_verdict_and_a_verdict_of_nothing_compare_the_same():
    """Otherwise the first write on every charge would record a line from
    nothing to pending."""
    assert dh.decision_value(None, None) is None
    assert dh.decision_value(None, "doc") is None
    assert dh.decision_value("pending", None) == {
        "status": "pending", "chosen_document_id": None
    }


def test_a_reordered_value_is_not_a_change():
    entry = dh.make_entry(
        run_id="r", row_key="t", row_kind=dh.ROW_CHARGE, field=dh.FIELD_DECISION,
        old={"status": "confirmed", "chosen_document_id": "d"},
        new={"chosen_document_id": "d", "status": "confirmed"},
        who="criss", at="2026-09-18T00:00:00+00:00", trigger=dh.TRIGGER_CLICK,
    )
    assert entry is None


def test_a_corrupt_stored_value_reads_as_absent_not_as_a_crash():
    assert dh.decode("{not json") is None
    assert dh.decode(None) is None
    assert dh.decode("") is None


def test_an_unknown_field_or_trigger_is_a_programming_error():
    for kwargs in (
        {"field": "nonsense", "trigger": dh.TRIGGER_CLICK, "row_kind": dh.ROW_CHARGE},
        {"field": dh.FIELD_DECISION, "trigger": "nonsense", "row_kind": dh.ROW_CHARGE},
        {"field": dh.FIELD_DECISION, "trigger": dh.TRIGGER_CLICK, "row_kind": "nope"},
    ):
        with pytest.raises(ValueError):
            dh.make_entry(
                run_id="r", row_key="t", old=None, new="x",
                who="criss", at="2026-09-18T00:00:00+00:00", **kwargs,
            )
