"""Item 257: one card's interim workbook inside its closing statement is ONE
charge, not two (owner 2026-10-29: "merge the doubles").

Live September 2026 lists 15 charges of card 9693 twice because the interim
xlsx and the PDF print the same purchase with different merchant text
("OPENAI" against "OPENAI OPENAI.COM CA"), and vendor is part of the content
id. The fold is by card + day + amount + currency ACROSS two files of the
card, multiset-wise (n lines and m lines leave max(n, m)), keeps the side a
person or the tool already decided, and never folds two lines of one file.

The unit half pins `merge_transactions`; the route half drives the attach and
the re-read through the FastAPI app, so a fold that is not wired into either
caller turns a test red.
"""
from __future__ import annotations

import io
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.ingest._common import assign_content_ids, merge_transactions
from expense_recon.matching.types import Transaction

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# -- unit: the fold ---------------------------------------------------------


def _tx(vendor, amount="182.82", day=14, account="card-9693", **kw):
    return Transaction(
        transaction_id="",
        legal_entity_id="Cloud Services",
        account_id=account,
        transaction_date=date(2026, 9, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        **kw,
    )


def _parse(*txs):
    return assign_content_ids(list(txs))


def _fold(held, incoming, *, held_file="interim.xlsx", decided=(), files=None):
    files = files if files is not None else {t.transaction_id: held_file for t in held}
    return merge_transactions(
        held, incoming, files=files, incoming_file="closing.pdf",
        decided=frozenset(decided),
    )


def test_the_same_charge_with_other_merchant_text_is_one_charge():
    interim = _parse(_tx("ANTHROPIC"))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA"))
    assert interim[0].transaction_id != closing[0].transaction_id

    merged = _fold(interim, closing)

    assert [t.vendor_from_statement for t in merged.transactions] == ["ANTHROPIC"]
    assert merged.folded == [closing[0].transaction_id]
    assert merged.added == []


def test_a_pdf_card_number_and_a_workbook_account_name_are_one_card():
    """The PDF parser files a charge under the bare cycle-marker card, the
    workbook under whatever the operator typed: '9693' against 'card-9693'."""
    interim = _parse(_tx("OPENAI", account="card-9693"))
    closing = _parse(_tx("OPENAI OPENAI.COM CA", account="9693"))

    assert len(_fold(interim, closing).transactions) == 1


@pytest.mark.parametrize(
    "other",
    [
        dict(account="card-1176"),
        dict(day=15),
        dict(amount="182.83"),
    ],
)
def test_another_card_day_or_amount_is_another_charge(other):
    interim = _parse(_tx("ANTHROPIC"))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA", **other))

    merged = _fold(interim, closing)

    assert len(merged.transactions) == 2
    assert merged.folded == []


def test_a_line_naming_no_card_is_never_folded():
    interim = _parse(_tx("ANTHROPIC", account=""))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA", account=""))

    assert len(_fold(interim, closing).transactions) == 2


def test_two_lines_of_one_file_are_never_folded_into_each_other():
    """Two identical coffees are two charges. The closing file holds two,
    the interim holds none of them: both land."""
    closing = _parse(_tx("COFFEE", "4.00"), _tx("COFFEE SHOP NYC", "4.00"))

    merged = _fold([], closing)

    assert len(merged.transactions) == 2


def test_n_lines_in_one_file_and_m_in_the_other_leave_the_larger():
    interim = _parse(_tx("COFFEE", "4.00"), _tx("COFFEE", "4.00"))
    closing = _parse(_tx("COFFEE SHOP NYC", "4.00"))
    assert len(_fold(interim, closing).transactions) == 2  # max(2, 1)

    interim = _parse(_tx("COFFEE", "4.00"))
    closing = _parse(
        _tx("COFFEE SHOP NYC", "4.00"), _tx("COFFEE SHOP NYC", "4.00")
    )
    merged = _fold(interim, closing)
    assert len(merged.transactions) == 2  # max(1, 2)
    assert len(merged.folded) == 1 and len(merged.added) == 1


def test_a_held_line_of_unknown_file_is_never_folded_against():
    interim = _parse(_tx("ANTHROPIC"))

    merged = _fold(interim, _parse(_tx("ANTHROPIC ANTHROPIC.COM CA")), files={})

    assert len(merged.transactions) == 2


def test_the_held_line_wins_when_neither_side_is_decided():
    interim = _parse(_tx("ANTHROPIC", source_row=7))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA"))

    merged = _fold(interim, closing)

    assert merged.transactions == interim
    assert merged.transactions[0].source_row == 7


def test_the_incoming_line_replaces_the_held_one_only_it_is_decided_on():
    interim = _parse(_tx("ANTHROPIC"), _tx("AWS", "10.00"))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA"))
    new_id = closing[0].transaction_id

    merged = _fold(interim, closing, decided={new_id})

    assert [t.vendor_from_statement for t in merged.transactions] == [
        "ANTHROPIC ANTHROPIC.COM CA", "AWS",
    ]
    assert merged.swapped == [(interim[0].transaction_id, new_id)]
    assert merged.files[new_id] == "closing.pdf"
    assert interim[0].transaction_id not in merged.files


def test_two_decided_sides_both_stay():
    interim = _parse(_tx("ANTHROPIC"))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA"))

    merged = _fold(
        interim, closing,
        decided={interim[0].transaction_id, closing[0].transaction_id},
    )

    assert len(merged.transactions) == 2
    assert merged.held == [closing[0].transaction_id]


def test_without_files_it_is_the_id_only_fold_it_was():
    interim = _parse(_tx("ANTHROPIC"))
    closing = _parse(_tx("ANTHROPIC ANTHROPIC.COM CA"))

    assert len(merge_transactions(interim, closing).transactions) == 2


# -- route: attach and re-read ---------------------------------------------

HEADERS = ("Date", "Description", "Type", "Amount")
FORM = {
    "account_id": "card-9693",
    "account_legal_entities": '{"card-9693": "Cloud Services"}',
    "account_card_currency": "USD",
}
INTERIM = [
    (datetime(2026, 9, 14), "ANTHROPIC", "Sale", -182.82),
    (datetime(2026, 9, 14), "SAP SE", "Sale", -481.07),
    (datetime(2026, 9, 9), "COFFEE", "Sale", -4.00),
    (datetime(2026, 9, 9), "COFFEE", "Sale", -4.00),
]
CLOSING = [
    (datetime(2026, 9, 14), "ANTHROPIC ANTHROPIC.COM CA", "Sale", -182.82),
    (datetime(2026, 9, 14), "SAP SE WALLDORF", "Sale", -481.07),
    (datetime(2026, 9, 9), "COFFEE SHOP NYC", "Sale", -4.00),
    (datetime(2026, 9, 30), "HETZNER", "Sale", -50.00),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-09-14", total="182.82", currency="USD",
            vendor="Anthropic", reference="", line_items=(), confidence=0.9,
            notes="", payment_hint=None,
        ),
    ])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client) -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "September"}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("anthropic.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, name, rows):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, _xlsx(rows), XLSX)},
        data=dict(FORM),
    ))


def _reread(client, batch_id):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statements/reread"
    ))


def _run(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _vendors(client, batch_id) -> list[str]:
    return sorted(r["vendor"] for r in _run(client, batch_id)["rows"])


def _decide(client, batch_id, vendor):
    run = _run(client, batch_id)
    (row,) = [r for r in run["rows"] if r["vendor"] == vendor]
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": row["transaction_id"], "status": "rejected"},
    )
    assert resp.status_code == 200, resp.text
    return row["transaction_id"]


def test_attaching_the_closing_file_folds_its_doubles(client):
    batch_id = _batch(client)
    _attach(client, batch_id, "interim.xlsx", INTERIM)
    _attach(client, batch_id, "closing.xlsx", CLOSING)

    # 4 interim lines + (ANTHROPIC, SAP SE, one COFFEE folded) + HETZNER new.
    assert _vendors(client, batch_id) == [
        "ANTHROPIC", "COFFEE", "COFFEE", "HETZNER", "SAP SE",
    ]


def test_the_closing_file_attached_first_keeps_its_own_text(client):
    batch_id = _batch(client)
    _attach(client, batch_id, "closing.xlsx", CLOSING)
    _attach(client, batch_id, "interim.xlsx", INTERIM)

    assert _vendors(client, batch_id) == [
        "ANTHROPIC ANTHROPIC.COM CA", "COFFEE", "COFFEE SHOP NYC",
        "HETZNER", "SAP SE WALLDORF",
    ]


def _attach_without_the_fold(client, batch_id, monkeypatch):
    """The month as it stands live today: both sides present."""
    real = service.merge_transactions
    monkeypatch.setattr(
        service, "merge_transactions", lambda e, i, **kw: real(e, i)
    )
    _attach(client, batch_id, "interim.xlsx", INTERIM)
    _attach(client, batch_id, "closing.xlsx", CLOSING)
    monkeypatch.setattr(service, "merge_transactions", real)


def test_a_re_read_folds_a_month_that_holds_both_sides(client, monkeypatch):
    batch_id = _batch(client)
    _attach_without_the_fold(client, batch_id, monkeypatch)
    assert len(_run(client, batch_id)["rows"]) == 8

    _reread(client, batch_id)

    assert len(_run(client, batch_id)["rows"]) == 5
    assert _vendors(client, batch_id) == [
        "ANTHROPIC", "COFFEE", "COFFEE", "HETZNER", "SAP SE",
    ]


def test_a_re_read_keeps_the_decided_side_and_its_verdict(client, monkeypatch):
    batch_id = _batch(client)
    _attach_without_the_fold(client, batch_id, monkeypatch)
    kept = _decide(client, batch_id, "SAP SE WALLDORF")

    _reread(client, batch_id)

    rows = {r["transaction_id"]: r for r in _run(client, batch_id)["rows"]}
    assert kept in rows and rows[kept]["vendor"] == "SAP SE WALLDORF"
    assert "SAP SE" not in [r["vendor"] for r in rows.values()]
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert kept in store.get_decisions(batch_id)


def test_a_re_read_with_both_sides_decided_keeps_both(client, monkeypatch):
    batch_id = _batch(client)
    _attach_without_the_fold(client, batch_id, monkeypatch)
    a = _decide(client, batch_id, "SAP SE")
    b = _decide(client, batch_id, "SAP SE WALLDORF")

    _reread(client, batch_id)

    ids = {r["transaction_id"] for r in _run(client, batch_id)["rows"]}
    assert {a, b} <= ids
