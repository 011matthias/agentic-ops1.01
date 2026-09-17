"""The two PDFs say what the screen says (backlog items 96 + 97, 2026-09-17).

Item 96, the reconciliation report. July 2026 printed "72 charges with no
receipt" under "What needs attention" while 48 of them were yellow rows in
Criss's workbook, which the month page folds away as already booked; every
receipt no charge held was captioned "Unmatched receipt", a copy set aside and
a receipt waiting on a review row included; and the receipts-with-no-charge
table gave no reason. The document now reads the screen's own payload for all
three: the booked rows leave the to-do table for one line and read "already
posted" in the listing, each caption says where the screen puts the receipt,
and the table carries the screen's short reason.

Item 97, the month report. Captions were numbered from a second fan-out that
ran without the chart and the COA gate; whenever it counted differently from
the rows written, the captions fell back to 1..N and named other purchases.
And a receipt whose total was never read wrote no listing row while its page
was still appended. The captions now come from the pass that writes the rows,
and an unreadable total writes one row with a blank amount.

Route-level throughout, and parity-driven where it can be: the expected words
are read off `GET /api/runs/{id}`, the payload the month page renders, then
looked for in `GET /runs/{id}/reconciliation-report.pdf`.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from PIL import Image  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.output._pdf_common import UNREADABLE_CAPTION  # noqa: E402
from expense_recon.unmatched_reasons import (  # noqa: E402
    RECEIPT_REASON_SHORT,
    RECEIPT_REASON_TEXT,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _norm(text: str) -> str:
    return " ".join(text.split())


def _pdf_text(client, path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    return _norm(" ".join(
        p.extract_text() or "" for p in PdfReader(io.BytesIO(resp.content)).pages
    ))


# ── item 96: a month holding every place a receipt can sit ──────────────


def _png(color: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 60), color).save(buf, format="PNG")
    return buf.getvalue()


def _tx(tid, day, vendor, amount, card, **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=date(2026, 4, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
        card_last4=card, **kw,
    )


def _rc(doc, vendor, total, day, mode=None) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=date(2026, 4, day),
        detected_total=Decimal(total), detected_currency="USD",
        detected_vendor=vendor, payment_mode=mode,
    )


ORIGINAL = "0001__pressmaster.png"
COPY = "0002__pressmaster-again.png"
REVIEW = "0003__github.png"
CARD_NOT_LOADED = "0004__zoom.png"
EDGE = "0005__uber.png"
CASH = "0006__cafe.png"
NO_CHARGE = "0007__staples.png"
BANK = "0008__konsult.png"


def _seed_month(client, *, two_cards: bool) -> str:
    """April 2026, statement April 1 to 20. AMAZON and AWS are open; YELLOW
    ROW is booked in the workbook with no receipt; PRESSMASTER holds its
    receipt, whose byte-identical second copy is set aside; GITHUB is a
    review row still waiting on its candidate. Of the receipts nobody holds,
    one each: a card whose statement is not loaded, the statement's edge, a
    cash tender, nothing found, and one settled by bank transfer."""
    other = "3645" if two_cards else "2838"
    charges = [
        _tx("t_open", 1, "AMAZON", "180.00", "2838"),
        _tx("t_booked", 5, "YELLOW ROW", "50.00", "2838", entry_status="posted"),
        _tx("t_press", 10, "PRESSMASTER DMCC", "135.00", other),
        _tx("t_github", 12, "GITHUB", "40.00", other),
        _tx("t_last", 20, "AWS", "12.00", "2838"),
    ]
    receipts = [
        _rc(ORIGINAL, "Pressmaster", "135.00", 10),
        _rc(COPY, "Pressmaster", "135.00", 10),
        _rc(REVIEW, "GitHub", "40.00", 12),
        _rc(CARD_NOT_LOADED, "Zoom", "15.00", 11, mode="Visa ending 9999"),
        _rc(EDGE, "Uber", "31.10", 20),
        _rc(CASH, "Cafe", "9.00", 8, mode="Cash"),
        _rc(NO_CHARGE, "Staples", "42.50", 9),
        _rc(BANK, "Konsult", "500.00", 7),
    ]
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_press", document_id=ORIGINAL,
            match_type=MatchType.EXACT, confidence=0.99, reason="exact",
            score=95, amount_score=1.0, date_score=1.0, vendor_score=1.0,
        )],
        judgment_required=[Match(
            transaction_id="t_github", document_id=REVIEW,
            match_type=MatchType.POSSIBLE, confidence=0.6, reason="possible",
            requires_review=True, score=60, amount_score=1.0, date_score=1.0,
            vendor_score=0.4,
        )],
        unmatched_transactions=["t_open", "t_booked", "t_last"],
        unmatched_receipts=[COPY, CARD_NOT_LOADED, EDGE, CASH, NO_CHARGE, BANK],
    )
    snapshot = snapshot_to_dict(charges, receipts, outcome, [])
    snapshot["receipt_digests"] = {ORIGINAL: "a" * 16, COPY: "a" * 16}
    snapshot["settled_outside"] = {
        BANK: {"how": "bank_transfer", "note": "", "at": "2026-05-02T00:00:00"},
    }
    root = client._data_root
    work = root / "run96"
    (work / "receipts").mkdir(parents=True)
    colors = ["red", "red", "green", "blue", "yellow", "purple", "orange", "gray"]
    for rec, color in zip(receipts, colors):
        (work / "receipts" / rec.document_id).write_bytes(_png(color))
    db = RunStore(root / "recon-web.sqlite")
    db.create_run(
        run_id="run96", created_at="2026-05-02T00:00:00", label="April 2026",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir=str(work), llm_enabled=False, has_coa=False,
    )
    db.close()
    return "run96"


@pytest.mark.parametrize("two_cards", [False, True], ids=["flat", "per-card"])
def test_the_reconciliation_report_uses_the_screens_status_and_caption_words(
    client, two_cards
):
    run_id = _seed_month(client, two_cards=two_cards)
    view = client.get(f"/api/runs/{run_id}").json()
    text = _pdf_text(client, f"/runs/{run_id}/reconciliation-report.pdf")

    # The fixture is what it claims to be, read off the screen's payload.
    rows = {r["transaction_id"]: r for r in view["rows"]}
    booked = [
        t for t in view["unmatched_transactions"]
        if rows[t["transaction_id"]]["section"] == "posted"
    ]
    still_open = [t for t in view["unmatched_transactions"] if t not in booked]
    assert [t["vendor"] for t in booked] == ["YELLOW ROW"]
    assert booked[0]["reason_code"] == "already_booked"
    assert sorted(t["vendor"] for t in still_open) == ["AMAZON", "AWS"]
    assert view["summary"]["n_booked_no_receipt"] == len(booked)
    assert {r["document_id"]: r["reason_code"] for r in view["unmatched_receipts"]} == {
        CARD_NOT_LOADED: "card_statement_not_loaded",
        EDGE: "charge_in_neighbouring_period",
        CASH: "not_a_card_charge",
        NO_CHARGE: "no_charge_on_any_loaded_statement",
    }
    assert [r["document_id"] for r in view["copies_set_aside"]] == [COPY]
    assert view["summary"]["n_settled_outside"] == 1
    assert rows["t_github"]["effective_bucket"] == "review"
    assert rows["t_github"]["chosen_document_id"] is None

    # (a) Booked is not a to-do: out of the table, one line, "already posted".
    n_open = sum(int(n) for n in re.findall(
        r"(?<!workbook: )\b(\d+) charges? with no receipt", text
    ))
    assert n_open == len(still_open)
    assert (
        f"Already booked in your workbook: {len(booked)} charge with no receipt, "
        "marked already posted in the listing below."
    ) in text
    assert "YELLOW ROW 50.00 USD already posted" in text
    for t in still_open:
        assert f"{t['vendor']} {t['amount']} USD no receipt" in text

    # (c) The receipts table gives the screen's short reason on each row.
    assert sum(
        int(n) for n in re.findall(r"(\d+) receipts with no charge", text)
    ) == len(view["unmatched_receipts"])
    for rec in view["unmatched_receipts"]:
        assert (
            f"{rec['vendor']} {rec['total']} {rec['currency']} "
            f"{RECEIPT_REASON_SHORT[rec['reason_code']]}"
        ) in text

    # (b) Each caption says where the screen puts the receipt.
    assert "Unmatched receipt" not in text
    for rec in view["unmatched_receipts"]:
        assert f"Receipt with no charge · {rec['vendor']}" in text
        assert RECEIPT_REASON_TEXT[rec["reason_code"]] in text
    for rec in view["copies_set_aside"]:
        assert f"Copy set aside · {rec['vendor']}" in text
        assert "copy of Pressmaster (pressmaster.png), set aside" in text
    assert "Paid by bank transfer · Konsult" in text
    assert (
        "Waiting for review · GitHub 2026-04-12 · 40.00 USD · proposed for the "
        "charge GITHUB 40.00 USD of 2026-04-12, not confirmed yet"
    ) in text
    assert "Charge 2026-04-10 · PRESSMASTER DMCC" in text
    assert "—" not in text.split("April 2026", 1)[1]


def test_a_month_with_only_booked_charges_left_says_nothing_is_open(client):
    """The "Nothing" line must not claim every charge has a receipt when the
    booked ones have none."""
    charges = [
        _tx("t_booked", 5, "YELLOW ROW", "50.00", "2838", entry_status="posted"),
        _tx("t_press", 10, "PRESSMASTER DMCC", "135.00", "2838"),
    ]
    receipts = [_rc(ORIGINAL, "Pressmaster", "135.00", 10)]
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_press", document_id=ORIGINAL,
            match_type=MatchType.EXACT, confidence=0.99, reason="exact", score=95,
        )],
        unmatched_transactions=["t_booked"],
    )
    db = RunStore(client._data_root / "recon-web.sqlite")
    db.create_run(
        run_id="booked", created_at="2026-05-02T00:00:00", label="April 2026",
        operator=None, summary={}, snapshot=snapshot_to_dict(charges, receipts, outcome, []),
        config={}, work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    db.close()
    text = _pdf_text(client, "/runs/booked/reconciliation-report.pdf")
    assert (
        "Nothing. Every charge has a receipt or is already booked, every "
        "receipt has a charge, and no duplicate is left undecided."
    ) in text
    assert "Already booked in your workbook: 1 charge with no receipt" in text
    assert "charges with no receipt" not in text


# ── item 97: the month report's captions and its unreadable totals ──────


def _jpg(tag: str) -> bytes:
    return b"\xff\xd8\xff\xe0fake-jpeg-bytes-" + tag.encode()


def _extraction(vendor, total, day, **kw) -> ExtractedReceipt:
    base = dict(
        date=f"2026-07-{day:02d}", total=total, currency="EUR", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(kw)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp) -> None:
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _batch(client, tags, label="July 2026") -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (f"{t.lower()}.jpg", _jpg(t), "application/octet-stream"))
            for t in tags
        ],
    ))
    return batch_id


def _doc(client, batch_id, vendor) -> str:
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    (row,) = [e for e in grid["expenses"] if e["vendor"]["display"] == vendor]
    return row["document_id"]


def _assert_captions_name_their_rows(text: str, expected: dict[str, str]) -> None:
    """Every caption's expense numbers are listing rows of that caption's
    vendor, and each vendor is captioned with exactly the numbers expected."""
    captions = re.findall(r"Expenses? (\d+(?:, \d+)*) · ([A-Z][a-z]+)", text)
    assert {vendor: nums for nums, vendor in captions} == expected, captions
    for nums, vendor in captions:
        for n in nums.split(", "):
            assert re.search(
                rf"(?<!\d){n} 2026-07-\d\d {vendor}\b", text
            ), (n, vendor, text[:600])


def test_an_unreadable_total_writes_a_row_and_every_caption_names_its_own(
    client, monkeypatch
):
    """The real case, through the route: OCR read no total on Bravo. It used
    to write no row, so the month read three expenses, the footer never
    fired, and the captions fell back to 1..4 over a three-row listing:
    "Expense 3 · Charlie" named Delta's row and "Expense 4 · Delta" named
    nothing."""
    _patch_ocr(
        monkeypatch,
        _extraction("Alpha", "10.00", 1),
        _extraction("Bravo", None, 2),
        _extraction("Charlie", "30.00", 3),
        _extraction("Delta", "40.00", 4),
    )
    batch_id = _batch(client, ["alpha", "bravo", "charlie", "delta"])
    summary = client.get(f"/api/expense-batches/{batch_id}").json()["summary"]
    assert summary["n_amounts_unreadable"] == 1

    text = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")
    assert "4 expenses · EUR 80.00" in text
    assert re.search(
        rf"2 2026-07-02 Bravo .*?{re.escape(UNREADABLE_CAPTION)}", text
    ), text[:800]
    assert "1 receipt excluded from the total: expense 2." in text
    _assert_captions_name_their_rows(
        text, {"Alpha": "1", "Bravo": "2", "Charlie": "3", "Delta": "4"}
    )

    csv_rows = client.get(f"/runs/{batch_id}/expenses.csv").text.splitlines()
    assert any(",Bravo," in line for line in csv_rows), csv_rows


def test_a_split_receipt_is_captioned_with_both_rows_and_the_next_with_its_own(
    client, monkeypatch
):
    """A receipt booking to two accounts writes two rows; the receipts after
    it keep the numbers of the rows actually written for them."""
    _patch_ocr(
        monkeypatch,
        _extraction(
            "Alpha", "30.00", 1,
            line_items=(
                ExtractedLineItem(description="train ticket", line_total="20.00"),
                ExtractedLineItem(description="lunch", line_total="10.00"),
            ),
        ),
        _extraction("Bravo", "5.00", 2),
        _extraction("Charlie", "7.00", 3),
    )
    batch_id = _batch(client, ["alpha", "bravo", "charlie"])
    alpha = _doc(client, batch_id, "Alpha")
    for index, category in ((0, "Travel & Transport"), (1, "Meals & Entertainment")):
        resp = client.post(f"/api/runs/{batch_id}/categories", json={
            "document_id": alpha, "line_index": index, "category": category,
            "zoho_account": category,
        })
        assert resp.status_code == 200, resp.text

    text = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")
    assert "4 expenses · EUR 42.00" in text
    _assert_captions_name_their_rows(
        text, {"Alpha": "1, 2", "Bravo": "3", "Charlie": "4"}
    )


CARDS = {
    "corp-2838": {
        "label": "Credit Card Chase Visa - 2838", "digits": ["2838"],
        "entity": "Corporate Services", "person": "Dirk Neumann - Corp Services",
        "zoho_account": "Credit Card - 2838",
    },
    "corp-3645": {
        "label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
        "entity": "Corporate Services", "person": "Dirk Neumann - Corp Services",
        "zoho_account": "Credit Card - 3645",
    },
}


def test_inside_per_card_sections_the_unreadable_row_and_the_captions_hold(
    client, monkeypatch
):
    """Item 138's per-card listing: Charlie's total was not read and it
    prints 3645, so its row, its caption and its footer line sit in the
    3645 section, and every caption still names its own row."""
    client.put("/api/settings", json={"cards": CARDS})
    _patch_ocr(
        monkeypatch,
        _extraction("Alpha", "96.00", 30, currency="USD", payment_hint="Visa ...2838"),
        _extraction("Bravo", "25.00", 5, currency="USD", payment_hint="Visa ...3645"),
        _extraction("Charlie", None, 10, currency="USD", payment_hint="Visa ...3645"),
    )
    batch_id = _batch(client, ["alpha", "bravo", "charlie"])
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Description", "Type", "Amount"])
    for row in (
        ("2838", datetime(2026, 7, 30), "ALPHA", "Sale", -96.00),
        ("3645", datetime(2026, 7, 5), "BRAVO", "Sale", -25.00),
    ):
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "July2026.xlsx", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))

    text = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")
    assert "Listing by card" in text
    sec_3645 = text.index("Credit Card Chase Visa - 3645: 2 expenses")
    assert text.index("Credit Card Chase Visa - 2838: 1 expense") < sec_3645
    assert re.search(
        rf"3 2026-07-10 Charlie .*?{re.escape(UNREADABLE_CAPTION)}", text
    ), text[:1200]
    assert "1 receipt excluded from the total: expense 3." in text
    _assert_captions_name_their_rows(
        text, {"Alpha": "1", "Bravo": "2", "Charlie": "3"}
    )
