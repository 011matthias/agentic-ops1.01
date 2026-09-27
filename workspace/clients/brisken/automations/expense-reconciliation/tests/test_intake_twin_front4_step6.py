"""The intake decides once (item 223 step 6, front 4, 2026-09-27).

A Stripe-style vendor mails one purchase as two attachments of one mail, the
INVOICE and its RECEIPT. Since step 4 the receipt reads the invoice's number
too and each reading says which of the two it is, so the pair is known at
arrival. The intake records it on both parts' provenance
(``intake_provenance[doc].twin_of``) and the duplicate ladder starts from it
(rung 0, basis ``intake_twin``). Before this, a pair whose vendor spelling,
references and text layer all differed reached no key and counted twice.

July to September hold ten such mails; every pair already sits in a single
copy group, and no stored row carries the record, so nothing on a live month
moves.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    BASIS_INTAKE_TWIN,
    TWIN_OF_KEY,
    decide_receipt_groups,
    intake_twins,
    stamp_intake_twins,
    twin_links,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import STATUS_INGESTED, process_message  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

DOMAIN = "expenses.brisken.com"
DAY = "2026-08-15"
# Over the intake's 4096-byte skip for images (a smaller one is a logo).
JPG = b"\xff\xd8\xff\xe0" + b"0" * 5000
INVOICE = "Invoice-HMVWDWIL-0034.jpg"
RECEIPT = "Receipt-2810-5339-6113.jpg"


# ── the rule, on readings ────────────────────────────────────────────────


def _r(doc, *, total="100.00", ccy="USD", kind=None, inv=None, rec=None,
       vendor="Anthropic, PBC", ref=None, mode=None):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 8, 15),
        detected_total=Decimal(total), detected_currency=ccy,
        detected_vendor=vendor, detected_reference=ref, payment_mode=mode,
        invoice_number=inv, receipt_number=rec, document_kind=kind,
    )


def _prov(*docs, archive="20260815T101500-aaaaaa"):
    return {d: {"person": "Dirk", "address": "dirk@brisken.com",
                "received_at": "2026-08-15T10:15:00Z", "archive": archive}
            for d in docs}


def _pair(**kw):
    return [
        _r("0000__Invoice.pdf", kind="invoice", inv="HMVWDWIL-0034", **kw),
        _r("0001__Receipt.pdf", kind="receipt", inv="HMVWDWIL0034",
           rec="2810-5339-6113", vendor="Anthropic, PBC (@anthropic)"),
    ]


def test_an_invoice_and_its_receipt_in_one_mail_are_twins_both_ways():
    pair = _pair()
    assert intake_twins(pair, _prov("0000__Invoice.pdf", "0001__Receipt.pdf")) == {
        "0000__Invoice.pdf": "0001__Receipt.pdf",
        "0001__Receipt.pdf": "0000__Invoice.pdf",
    }


@pytest.mark.parametrize("case", [
    "two_mails", "web_upload", "amounts_differ", "two_cards", "third_document",
    "two_invoices", "short_number",
])
def test_anything_less_than_one_whole_pair_is_left_to_the_ladder(case):
    docs = _pair()
    prov = _prov("0000__Invoice.pdf", "0001__Receipt.pdf")
    if case == "two_mails":
        prov["0001__Receipt.pdf"] = {**prov["0001__Receipt.pdf"], "archive": "other"}
    elif case == "web_upload":
        prov = {}
    elif case == "amounts_differ":  # a part payment
        docs[1] = _r("0001__Receipt.pdf", total="40.00", kind="receipt", inv="HMVWDWIL-0034")
    elif case == "two_cards":
        docs = [_r("0000__Invoice.pdf", kind="invoice", inv="HMVWDWIL-0034", mode="Visa - 9693"),
                _r("0001__Receipt.pdf", kind="receipt", inv="HMVWDWIL-0034", mode="Visa - 1176")]
    elif case == "third_document":
        docs.append(_r("0002__Reminder.pdf", kind="reminder", inv="HMVWDWIL-0034"))
        prov.update(_prov("0002__Reminder.pdf"))
    elif case == "two_invoices":
        docs[1] = _r("0001__Receipt.pdf", kind="invoice", inv="HMVWDWIL-0034")
    elif case == "short_number":
        docs = [_r("0000__Invoice.pdf", kind="invoice", inv="0034"),
                _r("0001__Receipt.pdf", kind="receipt", inv="0034")]
    assert intake_twins(docs, prov) == {}


def test_a_mail_recorded_before_the_archive_key_is_known_by_its_arrival_stamp():
    prov = _prov("0000__Invoice.pdf", "0001__Receipt.pdf")
    for e in prov.values():
        e.pop("archive")
    assert len(intake_twins(_pair(), prov)) == 2


def test_the_record_is_stamped_on_copies_and_read_back_only_when_mutual():
    prov = _prov("0000__Invoice.pdf", "0001__Receipt.pdf", "0002__Other.pdf")
    stamped = stamp_intake_twins(prov, _pair())
    assert TWIN_OF_KEY not in prov["0000__Invoice.pdf"]  # the input is untouched
    assert stamped["0000__Invoice.pdf"][TWIN_OF_KEY] == "0001__Receipt.pdf"
    assert TWIN_OF_KEY not in stamped["0002__Other.pdf"]  # absent, never null
    assert twin_links(stamped) == {"0000__Invoice.pdf": "0001__Receipt.pdf",
                                   "0001__Receipt.pdf": "0000__Invoice.pdf"}
    half = {**stamped, "0001__Receipt.pdf": prov["0001__Receipt.pdf"]}
    assert twin_links(half) == {}


def test_the_ladder_starts_from_the_record_and_a_reviewer_still_outranks_it():
    pair = _pair()
    twins = twin_links(stamp_intake_twins(_prov("0000__Invoice.pdf", "0001__Receipt.pdf"), pair))
    assert decide_receipt_groups(pair) == []  # no older key sees this pair
    (d,) = decide_receipt_groups(pair, twins=twins)
    assert (d.basis, d.verdict, d.decided_by) == (BASIS_INTAKE_TWIN, "copy", "tool")
    (ruled,) = decide_receipt_groups(pair, twins=twins, resolutions={d.group_id: "ignore"})
    assert (ruled.basis, ruled.verdict, ruled.decided_by) == (
        BASIS_INTAKE_TWIN, "distinct", "reviewer")


def test_a_pair_an_older_key_already_holds_keeps_its_group_and_its_count():
    """Every live September pair: one group already, the receipt counted. The
    record changes the reason, not the membership, so no saved ruling's group
    id moves."""
    pair = [
        _r("0000__Invoice.pdf", kind="invoice", inv="H0LHY2WQ-0033", ref="H0LHY2WQ-0033"),
        _r("0001__Receipt.pdf", kind="receipt", inv="H0LHY2WQ-0033", ref="H0LHY2WQ-0033"),
    ]
    (before,) = decide_receipt_groups(pair)
    twins = intake_twins(pair, _prov("0000__Invoice.pdf", "0001__Receipt.pdf"))
    (after,) = decide_receipt_groups(pair, twins=twins)
    assert before.basis == "reference" and after.basis == BASIS_INTAKE_TWIN
    assert (after.group_id, after.members, after.verdict) == (
        before.group_id, before.members, before.verdict)


# ── through the app: the mail intake records it, the grid reads it ───────


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _x(vendor, reference, kind, invoice_number, receipt_number=None, total="100.00"):
    return ExtractedReceipt(
        date=DAY, total=total, currency="USD", vendor=vendor, reference=reference,
        line_items=(), confidence=0.9, notes="", invoice_number=invoice_number,
        receipt_number=receipt_number, document_kind=kind,
    )


# Nothing older joins these two: the vendor is spelled two ways, the
# references differ, and a JPEG has no text layer for rung 3 to read.
INV_X = _x("Anthropic, PBC", "HMVWDWIL-0034", "invoice", "HMVWDWIL-0034")
REC_X = _x("Anthropic, PBC (@anthropic)", "2810-5339-6113", "receipt",
           "HMVWDWIL0034", "2810-5339-6113")


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _create_batch(client, monkeypatch) -> str:
    _patch_ocr(monkeypatch)
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "Corporate Services", "label": "August 2026"})
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _deliver(client, monkeypatch, attachments, *extractions):
    msg = EmailMessage()
    msg["From"] = "Dirk Neumann <dirk.neumann@brisken.com>"
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = "Your receipt from Anthropic, PBC #2810-5339-6113"
    msg["Message-ID"] = f"<{abs(hash(tuple(n for n, _ in attachments)))}@brisken.com>"
    msg.set_content("Receipt from Anthropic, PBC\n$100.00\n")
    for name, data in attachments:
        msg.add_attachment(data, maintype="image", subtype="jpeg", filename=name)
    _patch_ocr(monkeypatch, *extractions)
    state = client.app.state
    return process_message(state.db_path, state.learning_db_path, state.data_root,
                           msg.as_bytes(), synchronous=True)


def _provenance(client, batch_id) -> dict:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {}).get("intake_provenance") or {}


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(grid, needle):
    return next(e for e in grid["expenses"] if needle in e["document_id"])


def test_the_mail_records_the_pair_and_the_month_counts_it_once(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch)
    result = _deliver(client, monkeypatch,
                      [(INVOICE, JPG + b"i"), (RECEIPT, JPG + b"r")],
                      INV_X, REC_X, INV_X, REC_X)
    assert result["status"] == STATUS_INGESTED, result

    prov = _provenance(client, batch_id)
    inv_doc, rec_doc = f"0000__{INVOICE}", f"0001__{RECEIPT}"
    assert prov[inv_doc][TWIN_OF_KEY] == rec_doc
    assert prov[rec_doc][TWIN_OF_KEY] == inv_doc

    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"], group["decided_by"]) == (
        BASIS_INTAKE_TWIN, "copy", "tool")
    # Item 217 unchanged: the payment receipt is the real expense.
    assert "counts_in_total" not in _row(grid, "Receipt-")  # absent = counts
    assert _row(grid, "Invoice-")["counts_in_total"] is False
    assert _row(grid, "Invoice-")["submitted_by"][TWIN_OF_KEY] == rec_doc
    assert grid["summary"]["totals_by_ccy"] == {"USD": "100.00"}
    assert grid["summary"]["n_copies_set_aside"] == 1


def test_the_same_two_files_uploaded_by_hand_record_nothing(client, monkeypatch):
    """The differential: identical readings, no mail. Nothing is recorded and
    nothing older joins them, so both count, as before this step."""
    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, INV_X, REC_X)
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (INVOICE, JPG + b"i", "application/octet-stream")),
               ("files", (RECEIPT, JPG + b"r", "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    assert all(TWIN_OF_KEY not in e for e in _provenance(client, batch_id).values())
    grid = _grid(client, batch_id)
    assert grid["duplicate_groups"] == []
    assert grid["summary"]["totals_by_ccy"] == {"USD": "200.00"}


def test_a_reviewer_who_splits_the_amounts_takes_the_pair_back(client, monkeypatch):
    """The record holds only while the two still read as one purchase."""
    batch_id = _create_batch(client, monkeypatch)
    _deliver(client, monkeypatch, [(INVOICE, JPG + b"i"), (RECEIPT, JPG + b"r")],
             INV_X, REC_X, INV_X, REC_X)
    doc = _row(_grid(client, batch_id), "Invoice-")["document_id"]
    resp = client.put(f"/api/runs/{batch_id}/expenses/{doc}",
                      json={"field": "total", "value": "60.00"})
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    assert grid["duplicate_groups"] == []
    assert grid["summary"]["totals_by_ccy"] == {"USD": "160.00"}


def test_not_a_copy_on_the_recorded_pair_counts_both(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch)
    _deliver(client, monkeypatch, [(INVOICE, JPG + b"i"), (RECEIPT, JPG + b"r")],
             INV_X, REC_X, INV_X, REC_X)
    (group,) = _grid(client, batch_id)["duplicate_groups"]
    resp = client.post(f"/api/runs/{batch_id}/duplicates/resolve",
                       json={"group_id": group["group_id"], "resolution": "ignore"})
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    (ruled,) = grid["duplicate_groups"]
    assert (ruled["basis"], ruled["verdict"], ruled["decided_by"]) == (
        BASIS_INTAKE_TWIN, "distinct", "reviewer")
    assert grid["summary"]["totals_by_ccy"] == {"USD": "200.00"}
