"""Copies the duplicate ladder never saw (front 4, 2026-09-25).

Two shapes counted one purchase twice on the live months:

* one number read two ways. July 2026 held six groups where a slip was read
  once as "169518087198" and once as "Operação #169518087198", or as
  "NFC-e 246836" and "NFC-e no 246836 Serie 406", or with one misread digit
  (271025 / 271825); rung 4 compared the whole strings and called every one
  two purchases. The number is now the long digit run inside the text
  (`reference_digits`), or one misread digit of it on the same day
  (`misread_digit`). Three real OpenAI invoices of one amount on one day stay
  three.
* the rendered mail body. A Stripe-style vendor mails an invoice and the tool
  also saves the mail body; the body prints the vendor its own way, carries
  no invoice number and has its own bytes, so no key ever nominated it
  (September: four, August: one). A body beside the one document it repeats
  is now a copy of it (`body_twin`), and the body is never the kept member.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    BASIS_BODY_TWIN,
    BASIS_MISREAD_DIGIT,
    BASIS_REFERENCE_DIGITS,
    is_rendered_body,
    kept_member,
    vendors_agree,
)
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _x(vendor, day, total, currency, reference, invoice_number=None):
    return ExtractedReceipt(
        date=day, total=total, currency=currency, vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=None, invoice_number=invoice_number,
    )


def _wire(monkeypatch, extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("50.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, files, extractions, label="July 2026"):
    """A month with no statement: the ladder applies as the page is read."""
    _wire(monkeypatch, extractions)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + bytes([i]), "application/octet-stream"))
            for i, name in enumerate(files)
        ],
    ))
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_name(grid, needle):
    return next(e for e in grid["expenses"] if needle in e["document_id"])


# ── one number read two ways ─────────────────────────────────────────────


def test_one_slip_read_with_and_without_its_wrapper_words_counts_once(client, monkeypatch):
    """July's 24 Horas pair: "169518087198" and "Operação #169518087198"."""
    batch_id = _month(client, monkeypatch, ["slip.jpg", "slip-copy.jpg"], [
        _x("24 HORAS BEBIDAS", "2026-07-18", "127.00", "BRL", "169518087198"),
        _x("24 HORAS BEBIDAS", "2026-07-18", "127.00", "BRL", "Operação #169518087198"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"], group["decided_by"]) == (
        BASIS_REFERENCE_DIGITS, "copy", "tool")
    assert _by_name(grid, "slip-copy")["counts_in_total"] is False
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "127.00"}


def test_the_number_the_extractor_put_in_invoice_number_is_read_too(client, monkeypatch):
    """July's Fenix pair: one copy's reference is the authorisation protocol,
    its invoice number the slip number the other copy's reference prints."""
    batch_id = _month(client, monkeypatch, ["fenix.jpg", "fenix-copy.jpg"], [
        _x("SUPERMERCADO FENIX LTDA", "2026-07-13", "50.07", "BRL", "Numero: 310527 Serie: 043"),
        _x("SUPERMERCADO FENIX LTDA", "2026-07-13", "50.07", "BRL", "226260639705984",
           invoice_number="310527"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_REFERENCE_DIGITS, "copy")
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "50.07"}


def test_one_misread_digit_on_the_same_day_counts_once(client, monkeypatch):
    """July's Marinho pair: 271025 and 271825."""
    batch_id = _month(client, monkeypatch, ["marinho.jpg", "marinho-copy.jpg"], [
        _x("MARINHO SUPERMERCADO LTDA", "2026-07-30", "43.12", "BRL", "271025"),
        _x("MARINHO SUPERMERCADO LTDA", "2026-07-30", "43.12", "BRL", "271825"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_MISREAD_DIGIT, "copy")
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "43.12"}


def test_two_numbers_two_digits_apart_stay_two_purchases(client, monkeypatch):
    batch_id = _month(client, monkeypatch, ["a.jpg", "b.jpg"], [
        _x("MARINHO SUPERMERCADO LTDA", "2026-07-30", "43.12", "BRL", "271025"),
        _x("MARINHO SUPERMERCADO LTDA", "2026-07-30", "43.12", "BRL", "271099"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("distinct_reference", "distinct")
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "86.24"}


def test_three_real_openai_invoices_of_one_amount_stay_three(client, monkeypatch):
    """The pinned negative (September 2026): one account prefix, three
    invoice numbers, one day, one amount. No digit run reaches six digits."""
    batch_id = _month(client, monkeypatch, ["o1.jpg", "o2.jpg", "o3.jpg"], [
        _x("OpenAI", "2026-09-16", "80.12", "USD", "58596F4C-0059"),
        _x("OpenAI", "2026-09-16", "80.12", "USD", "58596F4C-0060"),
        _x("OpenAI", "2026-09-16", "80.12", "USD", "58596F4C-0061"),
    ], label="September 2026")
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["verdict"] == "distinct"
    assert grid["summary"]["totals_by_ccy"] == {"USD": "240.36"}


def test_a_shared_number_under_another_merchant_spelling_is_nominated(client, monkeypatch):
    """July's E A Locações pair: '052155' and 'DOC=052155' under
    'E A LOCACOES' and 'B91*E A LOCACOES'. No older key nominated it."""
    batch_id = _month(client, monkeypatch, ["ea.jpg", "ea-copy.jpg"], [
        _x("E A LOCACOES", "2026-07-18", "340.00", "BRL", "052155"),
        _x("B91*E A LOCACOES", "2026-07-18", "340.00", "BRL", "DOC=052155"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_REFERENCE_DIGITS, "copy")
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "340.00"}


# ── the rendered mail body ───────────────────────────────────────────────


def test_the_mail_body_is_a_copy_of_the_invoice_it_repeats(client, monkeypatch):
    """September's Zoho 50.00: the body, uploaded FIRST so it sorts first,
    is still the copy and the invoice the real expense."""
    batch_id = _month(client, monkeypatch, ["rendered-body.jpg", "50102502418.jpg"], [
        _x("ZOHO Corp.", "2026-09-10", "50.00", "USD", "RPCW2002220694639"),
        _x("ZOHO Corporation", "2026-09-10", "50.00", "USD", "50102502418"),
    ], label="September 2026")
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"], group["decided_by"]) == (
        BASIS_BODY_TWIN, "copy", "tool")
    body = _by_name(grid, "rendered-body")
    invoice = _by_name(grid, "50102502418")
    assert body["duplicate"]["is_extra"] is True
    assert body["counts_in_total"] is False
    assert invoice["duplicate"]["is_extra"] is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "50.00"}


def test_a_body_beside_an_invoice_and_its_receipt_leaves_one_counted(client, monkeypatch):
    """September's Lovable 60.00: invoice + receipt (one document by its
    number) + the body a day later. One expense counts."""
    batch_id = _month(client, monkeypatch, [
        "Invoice-H0LHY2WQ-0033.jpg", "Receipt-2177-4265.jpg", "rendered-body.jpg",
    ], [
        _x("Lovable Labs Incorporated", "2026-09-16", "60.00", "USD", "H0LHY2WQ-0033"),
        _x("Lovable Labs Incorporated", "2026-09-16", "60.00", "USD", "H0LHY2WQ-0033"),
        _x("Lovable Labs", "2026-09-17", "60.00", "USD", ""),
    ], label="September 2026")
    grid = _grid(client, batch_id)
    bases = sorted(g["basis"] for g in grid["duplicate_groups"])
    assert bases == [BASIS_BODY_TWIN, "reference"]
    counted = [e["document_id"] for e in grid["expenses"] if e.get("counts_in_total") is not False]
    assert len(counted) == 1 and "rendered-body" not in counted[0]
    assert grid["summary"]["totals_by_ccy"] == {"USD": "60.00"}


def test_a_body_beside_two_real_purchases_is_left_alone(client, monkeypatch):
    """Two invoices of one amount with two numbers: the body could repeat
    either, so no body group is made and nothing moves."""
    batch_id = _month(client, monkeypatch, ["i1.jpg", "i2.jpg", "rendered-body.jpg"], [
        _x("Lovable Labs Incorporated", "2026-09-21", "50.00", "USD", "H0LHY2WQ-0035"),
        _x("Lovable Labs Incorporated", "2026-09-21", "50.00", "USD", "H0LHY2WQ-0036"),
        _x("Lovable Labs", "2026-09-21", "50.00", "USD", ""),
    ], label="September 2026")
    grid = _grid(client, batch_id)
    assert all(g["basis"] != BASIS_BODY_TWIN for g in grid["duplicate_groups"])
    assert grid["summary"]["totals_by_ccy"] == {"USD": "150.00"}


def test_on_a_statement_month_the_body_leaves_the_pool_and_the_invoice_is_matched(
    client, monkeypatch,
):
    """Through the re-match (the pool builder): the body is set aside, the
    charge holds the invoice, and nothing is left unmatched."""
    batch_id = _month(client, monkeypatch, ["rendered-body.jpg", "50102456463.jpg"], [
        _x("Zoho Books", "2026-08-30", "576.00", "USD", "RPS2004132748584"),
        _x("ZOHO Corporation", "2026-08-30", "576.00", "USD", "50102456463"),
    ], label="August 2026")
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    ws.append([datetime(2026, 8, 30), "ZOHO* ZOHO-BOOKS", "Sale", -576.00])
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
    run = client.get(f"/api/runs/{batch_id}").json()
    (row,) = [r for r in run["rows"] if "ZOHO" in r["vendor"]]
    assert "50102456463" in row["chosen_document_id"]
    (aside,) = run["copies_set_aside"]
    assert "rendered-body" in aside["document_id"]
    assert run["unmatched_receipts"] == []


# ── the pieces, directly ─────────────────────────────────────────────────


def _r(doc, vendor="Zoho Books"):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 8, 30),
        detected_total=Decimal("576.00"), detected_currency="USD", detected_vendor=vendor,
    )


def test_merchant_spellings_agree_by_identity_not_by_raw_text():
    assert vendors_agree(_r("a", "Zoho Books"), _r("b", "ZOHO Corporation"))
    assert vendors_agree(_r("a", "E A LOCACOES"), _r("b", "B91*E A LOCACOES"))
    assert vendors_agree(_r("a", "Anthropic"), _r("b", "Anthropic, PBC"))
    assert not vendors_agree(_r("a", "Lovable Labs"), _r("b", "Base44"))
    assert not vendors_agree(_r("a", "MP *PARADA"), _r("b", "MP *POSTO"))


def test_a_body_a_charge_holds_stays_kept():
    """Item 217's rule 1 outranks the body rule: a held copy stays kept."""
    by_id = {d: _r(d) for d in ("0006__rendered-body.pdf", "0007__50102456463.pdf")}
    members = ("0007__50102456463.pdf", "0006__rendered-body.pdf")
    assert kept_member(members, by_id) == "0007__50102456463.pdf"
    assert kept_member(members, by_id, {"0006__rendered-body.pdf"}) == "0006__rendered-body.pdf"
    assert is_rendered_body(_r("0006__rendered-body.pdf"))
    assert not is_rendered_body(_r("0007__50102456463.pdf"))
