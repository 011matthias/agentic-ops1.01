"""Item 143: every table in both PDFs fits the A4 page.

Found 2026-09-17 while building item 138 and confirmed on a raster of the
August pages: the month report's listing was 732 pt wide and the
reconciliation report's charge table 672 pt (its coverage table 572 pt),
against 503.9 pt of frame. reportlab centers a table that is too wide, so
the two widest ran off both sides of the paper: the listing's `#` and Date
cut on the left, Ccy and Receipt on the right, on every month report since
item 24. The text layer still
holds the clipped cells, so every text-extraction test stayed green.

These tests measure the layout instead. `drawn` records each Table the
document template actually places, with the width of the frame it was
placed in, while the real builder runs. For every table: its width is
within the frame, no cell's text is wider than its column, and a column
holding a number, a date or a currency never breaks a word to get there
(a date split over two lines reads as two values). The fixtures carry the
lengths of the live months: "Lovable Labs Incorporated (@lovable)",
"Software & Subscriptions", "CHASE VISA - 2838 - TRAVEL",
"WEB*NETWORKSOLUTIONS", three-digit row numbers, six-figure amounts.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import Paragraph, Table  # noqa: E402
from reportlab.platypus.frames import Frame  # noqa: E402

from expense_recon.output._pdf_common import TABLE_WIDTH_MAX  # noqa: E402
from expense_recon.output.month_report_pdf import (  # noqa: E402
    build_expense_report_pdf,
)
from expense_recon.output.reconciliation_report_pdf import (  # noqa: E402
    build_reconciliation_report_pdf,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _done,
    _expense,
    _extraction,
    _pick_card,
    _wire,
)

# Columns whose values are one token each: they must fit on one line.
ONE_TOKEN_COLUMNS = {"#", "Date", "Amount", "Ccy", "Charges", "Matched", "No receipt",
                     "Copies"}

LISTING = ["#", "Date", "Vendor", "Account", "Entity", "Paid through", "Amount",
           "Ccy", "Receipt"]
REIMBURSEMENTS = ["#", "Date", "Vendor", "Amount", "Ccy"]
COVERAGE = ["Card", "Statements", "Period", "Charges", "Matched", "No receipt",
            "Unreconciled"]
CHARGES = ["#", "Date", "Charge", "Amount", "Ccy", "Status", "Receipt", "Account"]
NO_RECEIPT = ["Date", "Charge", "Amount", "Ccy"]
NO_CHARGE = ["Date", "Vendor", "Amount", "Ccy", "Why"]
DUPLICATES = ["What", "Date", "Amount", "Ccy", "Copies"]
COPIES_SET_ASIDE = ["What", "Date", "Amount", "Ccy", "Copies", "Why"]


@pytest.fixture
def drawn(monkeypatch):
    """Every Table the document template places, with its frame's width."""
    tables: list[tuple[Table, float]] = []
    original = Frame.add

    def add(self, flowable, canv, trySplit=0):
        placed = original(self, flowable, canv, trySplit=trySplit)
        if placed and isinstance(flowable, Table):
            tables.append((flowable, self._getAvailableWidth()))
        return placed

    monkeypatch.setattr(Frame, "add", add)
    return tables


def _flowables(value) -> list:
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _plain(value) -> str:
    return " ".join(
        f.getPlainText() if isinstance(f, Paragraph) else str(f)
        for f in _flowables(value)
    )


def _headers(drawn) -> set[tuple[str, ...]]:
    return {tuple(_plain(c) for c in table._cellvalues[0]) for table, _w in drawn}


def _problems(drawn) -> list[str]:
    """What does not fit: a table wider than its frame, a cell wider than
    its column, a one-token column that had to break a word."""
    out: list[str] = []
    for table, frame_width in drawn:
        head = [_plain(c) for c in table._cellvalues[0]]
        width = sum(table._colWidths)
        if width > frame_width + 0.01:
            out.append(f"{head}: table {width:.1f} pt, frame {frame_width:.1f} pt")
        for r, row in enumerate(table._cellvalues):
            for c, value in enumerate(row):
                style = table._cellStyles[r][c]
                inner = table._colWidths[c] - style.leftPadding - style.rightPadding
                for flowable in _flowables(value):
                    if isinstance(flowable, Paragraph):
                        flowable.wrap(inner, 100_000)
                        widest = max(flowable.getActualLineWidths0() or [0.0])
                        split = flowable._splitLongWordCount
                    else:
                        widest = stringWidth(str(flowable), style.fontname, style.fontsize)
                        split = 0
                    where = f"{head[c]!r} row {r} ({_plain(value)!r})"
                    if widest > inner + 0.01:
                        out.append(f"{where}: {widest:.1f} pt in a {inner:.1f} pt cell")
                    if split and head[c] in ONE_TOKEN_COLUMNS:
                        out.append(f"{where}: a word broken to fit {inner:.1f} pt")
    return out


def test_the_budget_is_the_frame_the_template_lays_out(drawn):
    """`TABLE_WIDTH_MAX`, which the column comments cite, is the width the
    real template gives a table, not a number that drifted from it."""
    build_expense_report_pdf(_rows(1), EXPENSE_COLUMNS, title="August 2026")
    assert {round(w, 3) for _t, w in drawn} == {round(TABLE_WIDTH_MAX, 3)}


# ── month report ────────────────────────────────────────────────────


def _row(n: int, **kw) -> list[str]:
    values = {
        "Expense Date": f"2026-08-{n % 28 + 1:02d}",
        "Vendor": VENDORS[n % len(VENDORS)],
        "Expense Account": ACCOUNTS[n % len(ACCOUNTS)],
        "Legal Entity": ("Corporate Services", "Brisken Treasury Consulting GmbH")[n % 2],
        "Paid Through": PAID_THROUGH[n % len(PAID_THROUGH)],
        "Expense Amount": ("50.00", "1,234.56", "123,456.78", "7.12")[n % 4],
        "Currency Code": ("USD", "EUR")[n % 2],
        **kw,
    }
    row = [""] * len(EXPENSE_COLUMNS)
    for key, value in values.items():
        row[EXPENSE_COLUMNS.index(key)] = value
    return row


VENDORS = ("Lovable Labs Incorporated (@lovable)", "Anthropic, PBC (@anthropic)",
           "Obsidian", "EasyPark Italia S.r.l", "WEB*NETWORKSOLUTIONS",
           "Deutsche Bahn Fernverkehr AG")
ACCOUNTS = ("Software & Subscriptions", "(uncategorized - assign)",
            "Travel Expense: Public Transport", "Meals & Entertainment")
PAID_THROUGH = ("Credit Card - 2838", "CHASE VISA - 2838 - TRAVEL",
                "(paid-through - assign)", "Credit Card - 3645")


def _rows(count: int) -> list[list[str]]:
    return [_row(n) for n in range(count)]


def _png(color: str) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (300, 400), color).save(buf, format="PNG")
    return buf.getvalue()


def test_a_long_flat_listing_fits_the_page(drawn):
    """Three-digit expense numbers, an unreadable amount and the longest
    live values, in the one flat table a month without sections prints."""
    rows = _rows(104) + [_row(104, **{"Expense Amount": ""})]
    build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Expense report - July 2026",
        amounts_unreadable=[105],
        evidence=[{"rows": [1], "label": "Lovable", "name": "r1.png",
                   "data": _png("red")}],
    )
    assert _headers(drawn) == {tuple(LISTING)}
    assert _problems(drawn) == []


def test_a_month_listed_by_card_fits_the_page(drawn):
    """Item 138's shape: a section per card with its statement line and
    notes, its receipts behind it, then reimbursements and copies."""
    rows = _rows(9)
    build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Expense report - August 2026",
        sections_heading="Listing by card",
        sections=[
            {"caption": "Credit Card Chase Visa - 3645", "label": "Card 3645",
             "detail": "Statement: August2026.xlsx · 2026-07-31 to 2026-08-31",
             "notes": ["Expense 2 is held on a charge on this card, but its own "
                       "card is Credit Card - 2838."],
             "start": 1, "count": 4},
            {"caption": "Credit Card Chase Visa - 2838", "label": "Card 2838",
             "start": 5, "count": 3},
            {"caption": "No card", "label": "No card", "start": 8, "count": 2},
        ],
        receipts_by_section=True,
        evidence=[
            {"rows": [1], "label": "Lovable", "name": "r1.png", "data": _png("red")},
            {"rows": [5, 6], "label": "Anthropic", "name": "r5.png",
             "data": _png("blue")},
        ],
        reimbursements=[{
            "person": "Dirk Neumann - Corp Services",
            "rows": [{"n": 10, "date": "2026-08-02",
                      "vendor": "Taxi Lisboa Aeroporto Unipessoal Lda",
                      "amount": "18.00", "currency": "EUR"}],
            "totals": {"EUR": "18.00"},
        }],
        copies_set_aside=[{"vendor": "Obsidian", "date": "2026-08-30",
                           "amount": "96.00", "currency": "USD", "rows": [3]}],
        copies_set_aside_totals={"USD": "96.00"},
    )
    assert _headers(drawn) == {tuple(LISTING), tuple(REIMBURSEMENTS)}
    assert _problems(drawn) == []


def test_a_cost_center_month_with_cards_inside_fits_the_page(drawn):
    """The owner's cards-inside-cost-centers shape: a sub-table per card."""
    build_expense_report_pdf(
        _rows(7), EXPENSE_COLUMNS, title="Expense report - August 2026",
        sections_heading="Listing by cost center",
        sections_note="Card and receipt spend only, not the total project cost.",
        sections=[
            {"caption": "Lidar (project)", "label": "Lidar", "start": 1, "count": 4,
             "subsections": [
                 {"caption": "Credit Card Chase Visa - 2838", "label": "Card 2838",
                  "start": 1, "count": 2},
                 {"caption": "No card", "label": "No card", "start": 3, "count": 2},
             ]},
            {"caption": "Unassigned", "label": "Unassigned", "start": 5, "count": 3},
        ],
    )
    assert _headers(drawn) == {tuple(LISTING)}
    assert len(drawn) >= 3
    assert _problems(drawn) == []


def test_a_trip_report_fits_the_page(drawn):
    build_expense_report_pdf(
        _rows(5), EXPENSE_COLUMNS, title="Trip report - Rome, Sibos 2026",
        sections=[
            {"person": "Dirk Neumann - Corp Services", "on_roster": True,
             "start": 1, "count": 3},
            {"person": "Matthias Silva", "on_roster": False, "start": 4, "count": 2},
        ],
    )
    assert _headers(drawn) == {tuple(LISTING)}
    assert _problems(drawn) == []


# ── reconciliation report ───────────────────────────────────────────


def _charge(n: int, card: str, **kw) -> dict:
    row = {
        "transaction_id": f"t{n}", "date": f"2026-08-{n % 28 + 1:02d}",
        "vendor": ("WEB*NETWORKSOLUTIONS", "MICROSOFT#G177387448",
                   "PROTON AG* PROTON AG", "EasyPark Italia S.r.l")[n % 4],
        "amount": ("2.76", "1,234.56", "123,456.78")[n % 3], "currency": "USD",
        "coverage_key": card, "effective_bucket": "unmatched", "status": "",
        "posting_category": {"zoho_account": ACCOUNTS[n % len(ACCOUNTS)]},
    }
    row.update(kw)
    return row


def _view(cards: list[str]) -> dict:
    rows = []
    for i, card in enumerate(cards):
        doc = f"d{i}"
        rows += [
            _charge(10 * i + 1, card, status="confirmed", chosen_document_id=doc,
                    effective_bucket="matched",
                    candidates=[{"document_id": doc, "receipt": {
                        "vendor": "Lovable Labs Incorporated (@lovable)"}}],
                    cards_differ={"document_id": doc,
                                  "receipt_card_label": "Credit Card Chase Visa - 2838"}),
            _charge(10 * i + 2, card),
            _charge(10 * i + 3, card, section="posted", entry_status="posted"),
            _charge(10 * i + 4, card, effective_bucket="refund", row_type="payment"),
        ]
    unmatched = [r for r in rows if r["effective_bucket"] == "unmatched"]
    coverage = [{
        "key": card, "label": f"Credit Card Chase Visa - {card}", "digits": [card],
        "statements": ["August2026.xlsx", "20260804-statements-1176-.pdf"],
        "period_start": "2026-07-31", "period_end": "2026-08-31",
        "n_transactions": 4, "n_reconciled": 1, "n_unmatched_tx": 2,
        "unreconciled_by_ccy": {"USD": "124,691.34", "EUR": "7.12"},
    } for card in dict.fromkeys(cards)]
    return {
        "summary": {"n_transactions": len(rows), "n_reconciled": len(cards),
                    "match_rate": 25.0, "unreconciled_by_ccy": {"USD": "124,691.34"},
                    "booked_no_receipt_by_ccy": {"USD": "1,234.56"}},
        "coverage": coverage,
        "rows": rows,
        "unmatched_transactions": unmatched,
        "unmatched_receipts": [{
            "document_id": "u1", "date": "2026-08-12",
            "vendor": "Taxi Lisboa Aeroporto Unipessoal Lda", "total": "1,234.56",
            "currency": "EUR", "reason_code": "charge_in_neighbouring_period",
        }],
        "duplicate_groups": [
            {"kind": "receipt", "members": ["u1", "u2"], "state": "open"},
            {"kind": "receipt", "members": ["d0", "c1"], "state": "decided",
             "verdict": "copy", "basis": "printed_reference"},
        ],
        "duplicate_receipts": [[
            {"document_id": "u1", "vendor": "Taxi Lisboa Aeroporto Unipessoal Lda",
             "date": "2026-08-12", "total": "1,234.56", "currency": "EUR"},
        ], [
            {"document_id": "d0", "vendor": "Lovable Labs Incorporated (@lovable)",
             "date": "2026-08-02", "total": "123,456.78", "currency": "USD"},
        ]],
    }


def _recon_evidence(cards: list[str]) -> tuple[list[dict], dict]:
    evidence = [
        {"document_id": f"d{i}", "label": "Charge · WEB*NETWORKSOLUTIONS",
         "name": f"d{i}.png", "data": _png("red")}
        for i in range(len(cards))
    ] + [{"document_id": "u1", "label": "Receipt with no charge · Taxi"}]
    return evidence, {"u1": ("", "")}


@pytest.mark.parametrize("cards", [
    ["2838", "3645", "1176"],  # one section per card, the coverage table
    ["2838"],                  # the flat document
])
def test_the_reconciliation_report_fits_the_page(drawn, cards):
    evidence, receipt_cards = _recon_evidence(cards)
    build_reconciliation_report_pdf(
        _view(cards), title="Reconciliation - August 2026",
        evidence=evidence, receipt_cards=receipt_cards,
    )
    expected = {tuple(CHARGES), tuple(NO_RECEIPT), tuple(DUPLICATES),
                tuple(COPIES_SET_ASIDE), tuple(NO_CHARGE)}
    if len(cards) > 1:
        expected.add(tuple(COVERAGE))
    assert _headers(drawn) == expected
    assert _problems(drawn) == []


# ── through the routes ──────────────────────────────────────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def test_both_downloads_of_a_two_card_month_fit_the_page(client, monkeypatch, drawn):
    """The documents a reviewer downloads: a real month with two cards, a
    statement, receipts held on either card and one on no card."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated (@lovable)", "25.00", "2026-08-05"),
        _extraction("Pressmaster", "135.00", "2026-08-23"),
        _extraction("Zoom", "15.00", "2026-08-10", "Visa ending 2838"),
        _extraction("Taxi", "30.00", "2026-08-12"),
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    files = [("files", (f"receipt-{c}.png", _png(c), "image/png"))
             for c in ("red", "green", "blue", "yellow")]
    _done(client, client.post(f"/api/expense-batches/{batch}/receipts", files=files))
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
        ("2838", datetime(2026, 8, 14), "WEB*NETWORKSOLUTIONS", "Sale", -40.00),
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    ])
    lovable = _expense(client, batch, "Lovable Labs Incorporated (@lovable)")
    assert _pick_card(client, batch, lovable["document_id"], "corp-2838").status_code == 200

    resp = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    assert {tuple(COVERAGE), tuple(CHARGES)} <= _headers(drawn)
    assert _problems(drawn) == []

    drawn.clear()
    resp = client.get(f"/runs/{batch}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    assert tuple(LISTING) in _headers(drawn)
    assert _problems(drawn) == []
