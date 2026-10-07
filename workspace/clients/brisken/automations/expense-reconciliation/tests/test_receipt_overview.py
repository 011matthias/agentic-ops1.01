"""The Receipt overview (Dirk, 2026-10-07): every receipt in the tool, one row
each, for the page that replaces Email intake.

Two halves. The builder (`receipt_overview.build_receipt_overview`) is pure
and pinned on hand-made payloads: one status per row read off the month's own
verdicts, the mail join three ways, and the mail that never became (or is no
longer) an expense. The route is pinned THROUGH the app: receipts dropped on
the Receipts page appear with what the receipt reads, and a later drop or a
held mail reaches the memoized body on the next read."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from expense_recon.web.receipt_overview import (
    BODY_FILE,
    BatchPage,
    build_receipt_overview,
    file_name_of,
    file_type_of,
)


def _expense(doc: str, **kw) -> dict:
    row = {
        "document_id": doc,
        "receipt_name": "",
        "vendor": {"display": "Acme", "raw": "ACME"},
        "date": "2026-09-03",
        "total": "1,087.06",
        "currency": "USD",
        "without_charge": False,
        "review": {"state": "ready", "reason_code": None},
        "receipt_image_available": True,
        "card": {"label": "Visa 9693"},
        "person": "Brisken Cloud Services",
        "books_as": [{"account": "IT Subscriptions", "unassigned": False}],
    }
    row.update(kw)
    return row


def _page(*expenses, set_aside=(), has_statement=True, batch_id="b1", label="September 2026"):
    return BatchPage(
        batch_id=batch_id, label=label, batch_type="company-month",
        view={"expenses": list(expenses), "set_aside": list(set_aside),
              "has_statement": has_statement},
    )


def _by_id(payload: dict) -> dict[str, dict]:
    return {r["id"]: r for r in payload["receipts"]}


# --- the builder ------------------------------------------------------------

def test_file_name_and_type():
    assert file_name_of("0003__0021__receipt_22_p28.png") == "receipt_22_p28.png"
    assert file_type_of("0001__Scan.JPEG") == "jpg"
    assert file_type_of("0007__rendered-body.pdf") == "email_body"
    assert file_type_of("README") == "other"


def test_status_is_the_months_own_verdict_in_order():
    page = _page(
        _expense("0000__dup.pdf", counts_in_total=False, private=True),
        _expense("0001__priv.pdf", private=True, without_charge=True),
        _expense("0002__bill.pdf", payment_path="bill", without_charge=True),
        _expense("0003__out.pdf", settled_outside={"at": "x"}, without_charge=True),
        _expense("0004__held.pdf"),
        _expense("0005__waits.pdf", without_charge=True, waits_for_statements=["9693"]),
        _expense("0006__none.pdf", without_charge=True),
    )
    rows = _by_id(build_receipt_overview([page], []))
    assert rows["b1/0000__dup.pdf"]["status"] == "duplicate"
    assert rows["b1/0001__priv.pdf"]["status"] == "private"
    assert rows["b1/0002__bill.pdf"]["status"] == "bill"
    assert rows["b1/0003__out.pdf"]["status"] == "settled_outside"
    assert rows["b1/0004__held.pdf"]["status"] == "matched"
    assert rows["b1/0005__waits.pdf"]["status"] == "waiting_for_statement"
    assert rows["b1/0006__none.pdf"]["status"] == "no_charge"
    # A month with no statement yet: nothing can hold the receipt.
    bare = _page(_expense("0000__x.pdf", without_charge=True), has_statement=False)
    assert build_receipt_overview([bare], [])["receipts"][0]["status"] == "waiting_for_statement"


def test_receipt_fields_read_what_the_receipt_says():
    row = build_receipt_overview([_page(_expense("0000__inv.pdf"))], [])["receipts"][0]
    assert row["vendor"] == "Acme"
    assert row["receipt_date"] == "2026-09-03"
    assert row["total"] == "1,087.06" and row["amount"] == 1087.06
    assert row["currency"] == "USD"
    assert row["file_name"] == "inv.pdf" and row["file_type"] == "pdf"
    assert row["card"] == "Visa 9693" and row["category"] == "IT Subscriptions"
    assert row["source"] == "upload" and row["review"] == "ready"
    assert row["can_view"] is True and row["document_id"] == "0000__inv.pdf"


def test_upload_arrival_is_the_stored_files_time():
    page = _page(_expense("0000__inv.pdf"))
    row = build_receipt_overview(
        [page], [], stored_at=lambda b, d: "2026-09-18T11:23:24+00:00"
    )["receipts"][0]
    assert row["received_at"] == "2026-09-18T11:23:24+00:00"
    assert row["received_from"] == "stored_file"


def test_mail_joins_three_ways():
    mail = [
        {"archive": "A1", "at": "2026-10-01T00:40:31+00:00", "subject": "Fw: Afi",
         "from": "dirk@brisken.com", "status": "ingested", "batch_id": "b1",
         "documents": ["0000__by_archive.pdf"]},
        {"archive": "A2", "at": "2026-09-07T06:47:17+00:00", "subject": "Fw: GitHub",
         "status": "ingested", "batch_id": "b1", "documents": ["0001__by_doc.pdf"]},
        {"archive": "A3", "at": "2026-09-09T14:09:00+00:00", "subject": "Fw: moved",
         "status": "ingested", "batch_id": "b0", "documents": ["0009__moved.pdf"]},
    ]
    page = _page(
        _expense("0000__by_archive.pdf", submitted_by={
            "person": "Dirk Neumann", "archive": "A1",
            "received_at": "2026-10-01T00:40:31+00:00"}),
        _expense("0001__by_doc.pdf"),
        # Moved here from another month: only the arrival second links it.
        _expense("0002__moved.pdf", submitted_by={
            "person": "Criss", "received_at": "2026-09-09T14:09:00+00:00"}),
    )
    rows = _by_id(build_receipt_overview([page], mail))
    assert rows["b1/0000__by_archive.pdf"]["subject"] == "Fw: Afi"
    assert rows["b1/0000__by_archive.pdf"]["submitted_by"] == "Dirk Neumann"
    assert rows["b1/0001__by_doc.pdf"]["subject"] == "Fw: GitHub"
    assert rows["b1/0001__by_doc.pdf"]["source"] == "email"
    assert rows["b1/0002__moved.pdf"]["subject"] == "Fw: moved"
    # The moved receipt is accounted for, so its mail shows no "removed" row.
    assert not [r for r in rows.values() if r["status"] == "removed"]


def test_mail_that_is_not_an_expense_still_has_a_row():
    mail = [
        {"archive": "P", "at": "2026-10-03T08:00:00+00:00", "subject": "Taxi",
         "status": "pooled", "files": ["a.pdf", "b.jpg"], "pool_month": "2026-11"},
        {"archive": "H", "at": "2026-09-28T00:31:40+00:00", "subject": "Body only",
         "status": "held_body_only", "files": []},
        {"archive": "D", "at": "2026-10-02T15:44:32+00:00", "subject": "DB ticket",
         "status": "duplicate", "files": ["ticket.pdf"], "duplicate_of_subject": "DB ticket (1st)"},
        {"archive": "X", "at": "2026-08-24T22:51:15+00:00", "subject": "Dismissed",
         "status": "dismissed", "files": ["x.pdf"]},
    ]
    payload = build_receipt_overview([], mail)
    by_status = {}
    for r in payload["receipts"]:
        by_status.setdefault(r["status"], []).append(r)
    assert [r["file_name"] for r in by_status["waiting_for_month"]] == ["a.pdf", "b.jpg"]
    assert by_status["waiting_for_month"][0]["pool_month"] == "2026-11"
    assert by_status["held"][0]["file_type"] == "email_body"
    assert by_status["held"][0]["file_name"] == BODY_FILE
    assert by_status["duplicate"][0]["duplicate_of"] == "DB ticket (1st)"
    assert by_status["dismissed"][0]["subject"] == "Dismissed"
    assert all(r["source"] == "email" for r in payload["receipts"])
    # Newest arrival first.
    assert [r["received_at"] for r in payload["receipts"]] == sorted(
        (r["received_at"] for r in payload["receipts"]), reverse=True)


def test_removed_documents_and_deleted_months():
    mail = [
        {"archive": "R", "at": "2026-09-09T14:03:09+00:00", "subject": "Lovable",
         "status": "ingested", "batch_id": "b1",
         "documents": ["0000__kept.pdf", "0001__deleted.pdf"]},
        {"archive": "G", "at": "2026-08-21T09:19:05+00:00", "subject": "Gone month",
         "status": "ingested", "batch_id": "gone", "documents": ["0000__x.pdf"]},
    ]
    page = _page(_expense("0000__kept.pdf"))
    rows = [r for r in build_receipt_overview([page], mail)["receipts"]
            if r["status"] == "removed"]
    by_doc = {r["file_name"]: r for r in rows}
    assert set(by_doc) == {"deleted.pdf", "x.pdf"}
    assert by_doc["deleted.pdf"]["can_view"] is True
    assert by_doc["deleted.pdf"]["batch_label"] == "September 2026"
    assert by_doc["x.pdf"]["can_view"] is False and by_doc["x.pdf"]["batch_id"] is None


def test_set_aside_files_are_listed_restored_ones_are_not():
    page = _page(set_aside=[
        {"document_id": "0010__statement.pdf", "display": "statement.pdf",
         "reason": "statement", "restored": False, "at": "2026-10-05T10:57:52+00:00"},
        {"document_id": "0011__back.pdf", "display": "back.pdf", "reason": "other",
         "restored": True, "at": "2026-10-05T10:57:52+00:00"},
    ])
    rows = build_receipt_overview([page], [])["receipts"]
    assert [(r["file_name"], r["status"], r["set_aside_reason"]) for r in rows] == [
        ("statement.pdf", "set_aside", "statement")]


def test_every_row_carries_every_key():
    mail = [{"archive": "P", "at": "2026-10-03T08:00:00+00:00", "status": "pooled",
             "files": ["a.pdf"]}]
    page = _page(_expense("0000__a.pdf"), set_aside=[
        {"document_id": "0001__s.pdf", "restored": False, "at": "2026-10-01T00:00:00+00:00"}])
    payload = build_receipt_overview([page], mail)
    assert len({tuple(sorted(r)) for r in payload["receipts"]}) == 1
    assert payload["by_source"] == {"upload": 2, "email": 1}


# --- the route, through the app --------------------------------------------

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000
DAY = date.today().replace(day=1) - timedelta(days=20)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _ocr(monkeypatch, mapping: dict) -> None:
    class _ByName(MockLLMClient):
        def extract_receipt(self, *, file_name, images=None, text=None):
            for name, (vendor, total) in mapping.items():
                if str(file_name).endswith(name):
                    return ExtractedReceipt(
                        date=DAY.isoformat(), total=total, currency="EUR",
                        vendor=vendor, reference="", line_items=(),
                        confidence=0.9, notes="",
                    )
            raise AssertionError(f"unbudgeted read of {file_name!r}")

    mock = _ByName()
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _drop(client, files):
    resp = client.post(
        "/api/receipts",
        files=[("files", (n, b, "application/octet-stream")) for n, b in files],
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _overview(client) -> dict:
    resp = client.get("/api/receipts/overview")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_route_lists_dropped_receipts_with_what_they_read(client, monkeypatch):
    _ocr(monkeypatch, {"staples.jpg": ("Staples", "42.50"), "uber.jpg": ("Uber", "18.00")})
    _drop(client, [("staples.jpg", JPG), ("uber.jpg", JPG + b"2")])
    payload = _overview(client)
    rows = {r["file_name"]: r for r in payload["receipts"]}
    assert set(rows) == {"staples.jpg", "uber.jpg"}
    staples = rows["staples.jpg"]
    assert staples["vendor"] == "Staples"
    assert staples["amount"] == 42.5 and staples["currency"] == "EUR"
    assert staples["receipt_date"] == DAY.isoformat()
    assert staples["source"] == "upload" and staples["file_type"] == "jpg"
    # No statement yet: nothing can hold it.
    assert staples["status"] == "waiting_for_statement"
    # The stored file's write time stands in for an upload's arrival.
    assert staples["received_from"] == "stored_file" and staples["received_at"]
    assert staples["can_view"] is True and staples["batch_label"]


def test_route_memo_sees_a_new_drop_and_a_held_mail(client, monkeypatch):
    _ocr(monkeypatch, {"a.jpg": ("A", "1.00"), "b.jpg": ("B", "2.00")})
    _drop(client, [("a.jpg", JPG)])
    first = _overview(client)
    assert first == _overview(client)  # a read in between changes nothing
    _drop(client, [("b.jpg", JPG + b"b")])
    assert {r["file_name"] for r in _overview(client)["receipts"]} == {"a.jpg", "b.jpg"}

    # A held mail writes only under inbound/: the key has to see it.
    inbound = client._data_root / "inbound"
    archive = inbound / "20261007T080000-abcdef12"
    archive.mkdir(parents=True)
    (archive / "meta.json").write_text(json.dumps({"status": "held_body_only"}))
    with (inbound / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "at": "2026-10-07T08:00:00+00:00", "from": "dirk@brisken.com",
            "subject": "Fw: taxi", "status": "held_body_only",
            "archive": archive.name, "files": [],
        }) + "\n")
    held = [r for r in _overview(client)["receipts"] if r["status"] == "held"]
    assert [(r["subject"], r["file_type"]) for r in held] == [("Fw: taxi", "email_body")]

    # Dismissing rewrites only that archive's meta.json.
    (archive / "meta.json").write_text(json.dumps({"status": "dismissed"}))
    statuses = {r["status"] for r in _overview(client)["receipts"]}
    assert "held" not in statuses and "dismissed" in statuses
