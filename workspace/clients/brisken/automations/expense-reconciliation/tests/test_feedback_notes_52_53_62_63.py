"""Four feedback notes from 2026-09-16/17, pinned route-level.

* #62 (Criss, August): "already resolved but it still says needs a look".
  Live, the row was OpenAI 80.04, `review.reason_code: vendor_guess`: the
  CATEGORY was guessed from the vendor name. The only edits that clear that
  verdict change the category, so a right guess could never leave the flag.
  `POST .../expenses/{doc}/confirm-category` keeps it as the reviewer's own,
  and `expenses[].category_confirmable` says when that is on offer.
* #63 (Criss, August): "I can't change the card if I need to." The per-row
  card fix (item 87) already won over a printed card on the grid, but the
  card is also what the matcher scopes a receipt to, and a card edit never
  re-matched. A receipt printing ••3645 that was really paid on 2838 stayed
  scoped to 3645 and could never meet its charge.
* #52 (owner, July): a page set aside as a statement must be viewable before
  it is restored. `set_aside[].receipt_image_available` answers with the
  image endpoint's own rule.
* #53 (owner): do dropped receipts sort themselves into months? Yes; and a
  month that holds a statement re-matches on arrival. The drop ledger now
  says so per month (`has_statement`, `rematch`) instead of dropping it.
"""
from __future__ import annotations

import calendar
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-0917b"
_SEQ = [0]

CARDS = {
    "corp-2838": {
        "label": "Credit Card Chase Visa - 2838",
        "digits": ["2838"],
        "entity": "Corporate Services",
        "person": "Dirk Neumann - Corp Services",
        "zoho_account": "Credit Card - 2838",
    },
    "corp-3645": {
        "label": "Credit Card Chase Visa - 3645",
        "digits": ["3645"],
        "entity": "Corporate Services",
        "person": "Dirk Neumann - Corp Services",
        "zoho_account": "Credit Card - 3645",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, day, payment_hint=None, **kw) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency=kw.pop("currency", "USD"), vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint, **kw,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("1.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    return mock


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, n_files: int, label="August 2026", entity="") -> str:
    resp = client.post("/api/expense-batches", data={"legal_entity": entity, "label": label})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if n_files:
        files = []
        for _ in range(n_files):
            _SEQ[0] += 1
            files.append(("files", (f"r{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 3]),
                                    "application/octet-stream")))
        _done(client, client.post(f"/api/expense-batches/{batch_id}/receipts", files=files))
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _expense(client, batch_id, vendor) -> dict:
    rows = [e for e in _grid(client, batch_id)["expenses"] if e["vendor"]["display"] == vendor]
    assert len(rows) == 1, [e["vendor"] for e in _grid(client, batch_id)["expenses"]]
    return rows[0]


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, rows):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _charge(client, batch_id, vendor) -> dict:
    view = client.get(f"/api/runs/{batch_id}").json()
    return next(r for r in view["rows"] if vendor in r["vendor"])


def _pick_card(client, batch_id, doc, key):
    return client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": "card_key", "value": key}
    )


# ── #62: a right guess can be kept ───────────────────────────────────────


def _confirm(client, batch_id, doc):
    return client.post(f"/api/runs/{batch_id}/expenses/{doc}/confirm-category")


def test_a_vendor_guess_is_kept_and_the_row_leaves_needs_a_look(client, monkeypatch):
    # Live it was OpenAI 80.04; the mock categorizer guesses Uber from its name
    # the same way (`classify_by_vendor`, source VENDOR).
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Uber", "22.30", "2026-08-20", "Visa ...2838"))
    batch = _month(client, 1)

    row = _expense(client, batch, "Uber")
    assert row["posting_category"]["category"] == "Travel & Transport"
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "vendor_guess"
    assert row["category_confirmable"] is True
    # The live shape: editing another field never cleared the flag.
    assert client.put(
        f"/api/runs/{batch}/expenses/{row['document_id']}",
        json={"field": "paid_through", "value": "Credit Card - 2838"},
    ).status_code == 200
    assert _expense(client, batch, "Uber")["review"]["reason_code"] == "vendor_guess"

    resp = _confirm(client, batch, row["document_id"])
    assert resp.status_code == 200, resp.text
    assert "rematch" not in resp.json()

    row = _expense(client, batch, "Uber")
    assert row["posting_category"]["category"] == "Travel & Transport"
    assert row["posting_category"]["source"] == "override"
    assert row["review"]["state"] == "ready", row["review"]
    assert row["category_confirmable"] is False
    assert _grid(client, batch)["summary"]["n_review"] == 0

    # Confirming twice is refused: there is no guess left to keep.
    assert _confirm(client, batch, row["document_id"]).status_code == 400

    # "Undo my category" takes the confirmation back to the tool's guess.
    assert client.put(
        f"/api/runs/{batch}/expenses/{row['document_id']}",
        json={"field": "category", "value": ""},
    ).status_code == 200
    row = _expense(client, batch, "Uber")
    assert row["review"]["reason_code"] == "vendor_guess"
    assert row["category_confirmable"] is True


def test_confirm_category_refuses_what_is_not_a_guess(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Pressmaster FZCO", "135.00", "2026-08-12", "Visa ...2838"))
    batch = _month(client, 1)
    row = _expense(client, batch, "Pressmaster FZCO")
    assert row["posting_category"] is None
    assert row["category_confirmable"] is False
    assert _confirm(client, batch, row["document_id"]).status_code == 400
    assert _confirm(client, batch, "9999__nope.pdf").status_code == 404


# ── #63: a card picked by hand reaches the matcher ───────────────────────

OBSIDIAN_ROWS = [
    ("2838", datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    ("3645", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
]


def test_a_card_picked_against_the_printed_card_re_matches_the_month(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Obsidian", "96.00", "2026-08-30", "CorpServ & DN ••3645"))
    batch = _month(client, 1)
    _attach(client, batch, OBSIDIAN_ROWS)

    row = _expense(client, batch, "Obsidian")
    assert row["card"]["key"] == "corp-3645" and row["card_source"] == "hint"
    # Scoped to the printed 3645, the receipt cannot meet the 2838 charge.
    assert _charge(client, batch, "OBSIDIAN")["chosen_document_id"] is None

    resp = _pick_card(client, batch, row["document_id"], "corp-2838")
    assert resp.status_code == 200, resp.text
    assert "rematch" in resp.json(), resp.json()
    assert "error" not in (resp.json()["rematch"] or {}), resp.json()["rematch"]

    row = _expense(client, batch, "Obsidian")
    assert row["card"]["key"] == "corp-2838" and row["card_source"] == "override"
    assert _charge(client, batch, "OBSIDIAN")["chosen_document_id"] == row["document_id"]
    # The grid still shows what the receipt printed.
    assert row["payment_hint"] == "CorpServ & DN ••3645"

    # Taking the pick back re-matches too, and the printed card scopes again.
    resp = _pick_card(client, batch, row["document_id"], "")
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text
    assert _charge(client, batch, "OBSIDIAN")["chosen_document_id"] is None


def test_a_pick_on_a_receipt_that_printed_no_card_reaches_the_matcher(client, monkeypatch):
    """Item 137 widened note #63: a pick scopes a receipt that printed no card
    too. The only LOVABLE charge is on 2838, so the pick of 3645 keeps the
    pair but asks for review (tests/test_card_scope_item_137.py)."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "15.00", "2026-08-31"))
    batch = _month(client, 1)
    _attach(client, batch, [("2838", datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
                            ("3645", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00)])
    doc = _expense(client, batch, "Lovable")["document_id"]
    assert _charge(client, batch, "LOVABLE")["chosen_document_id"] == doc
    assert "cards_differ" not in _charge(client, batch, "LOVABLE")

    resp = _pick_card(client, batch, doc, "corp-3645")
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text
    row = _charge(client, batch, "LOVABLE")
    assert row["chosen_document_id"] == doc
    assert row["cards_differ"]["receipt_card"] == "3645"


def test_repicking_the_printed_card_does_not_re_match(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Obsidian", "96.00", "2026-08-30", "CorpServ & DN ••3645"))
    batch = _month(client, 1)
    _attach(client, batch, OBSIDIAN_ROWS)
    doc = _expense(client, batch, "Obsidian")["document_id"]
    assert "rematch" in _pick_card(client, batch, doc, "corp-3645").json()
    # The same value again is not a change.
    assert "rematch" not in _pick_card(client, batch, doc, "corp-3645").json()


# ── #52: a set-aside page can be looked at ───────────────────────────────


def test_a_set_aside_page_says_it_can_be_opened_and_the_viewer_serves_it(client, monkeypatch):
    _wire(
        monkeypatch,
        _extraction("Staples", "42.50", "2026-07-10"),
        _extraction(None, "3352.59", "2026-07-01", document_type="statement"),
    )
    batch = _month(client, 2, label="July 2026", entity="Corporate Services")
    (entry,) = _grid(client, batch)["set_aside"]
    assert entry["reason"] == "statement"
    assert entry["receipt_image_available"] is True
    url = f"/api/runs/{batch}/receipts/{quote(entry['file'])}/image"
    assert client.get(url).status_code == 200

    # The flag follows the file: gone from disk, the flag and the route agree.
    run_dir = next(p for p in (client._data_root / "runs").iterdir() if p.name == batch)
    (run_dir / "receipts" / entry["file"]).unlink()
    (entry,) = _grid(client, batch)["set_aside"]
    assert entry["receipt_image_available"] is False
    assert client.get(url).status_code == 404


# ── #53: the drop page says whether the month re-matched ─────────────────

DAY = date.today().replace(day=1) - timedelta(days=20)   # last month
LABEL = f"{calendar.month_name[DAY.month]} {DAY.year}"


def _drop(client, name: str) -> dict:
    _SEQ[0] += 1
    resp = client.post(
        "/api/receipts",
        files=[("files", (name, JPG + bytes([_SEQ[0] % 256, 9]), "application/octet-stream"))],
    )
    return _done(client, resp)["result"]


def test_a_drop_into_a_month_with_a_statement_reports_the_re_match(client, monkeypatch):
    # routing read + ingest read, per file
    receipt = _extraction("Staples", "42.50", DAY.isoformat(), currency="USD")
    _wire(monkeypatch, receipt, receipt)
    batch = _month(client, 0, label=LABEL, entity="Corporate Services")
    csv = f"Date,Amount,Vendor\n{DAY.isoformat()},42.50,STAPLES\n".encode()
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("statement.csv", csv, "text/csv")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date", "map_amount": "Amount", "map_vendor": "Vendor",
        },
    ))

    result = _drop(client, "staples.jpg")
    (entry,) = result["months"]
    assert entry["batch_id"] == batch and entry["created_batch"] is False
    assert entry["has_statement"] is True
    assert entry["rematch"]["ok"] is True, entry
    assert entry["rematch"]["n_transactions"] == 1
    assert entry["rematch"]["n_matched"] == 1


def test_a_drop_that_creates_its_month_reports_no_statement(client, monkeypatch):
    receipt = _extraction("Staples", "42.50", DAY.isoformat(), currency="USD")
    _wire(monkeypatch, receipt, receipt)
    (entry,) = _drop(client, "staples.jpg")["months"]
    assert entry["created_batch"] is True
    assert entry["has_statement"] is False
    assert "rematch" not in entry
