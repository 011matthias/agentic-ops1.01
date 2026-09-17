"""One currency for a month's receipts (backlog item 98).

July's expense report closed with three totals (USD, EUR, BRL) and nothing
saying what the month cost in one currency, while the `Exchange Rate` column
the export already carries was empty on all 57 live rows. The accountant
converted by hand, and the deductible figure is the USD one (owner,
2026-09-08).

Pinned through both documents a reviewer actually downloads, because the
figure has to be the same in both:

1. `GET /runs/{id}/expenses.csv` fills `Exchange Rate` and states the
   month's one total under the rows.
2. `GET /runs/{id}/expense-report.pdf` prints each converted row's figure
   and rate under its amount, and the month total on the header line.
3. A receipt a charge settled converts at THAT CHARGE, not at the typed
   rate: the statement is what the card really did. The fixture sets the
   two apart on purpose (a USD 56.00 charge against a EUR 50.00 receipt is
   1.12, where Settings says 1.10), so a test that silently used the wrong
   rung would fail rather than agree by coincidence.
4. A pair the reviewer REJECTED lends nothing, exactly as item 111's card
   inheritance behaves, and the row falls back to the reference rate.
5. A currency no rate can price gets no figure and is NAMED, rather than
   counting as zero and quietly shortening the total (item 65's rule).
6. A receipt that splits across two accounts converts once as one purchase
   and its rows sum to the charge to the cent.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdf")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from types import SimpleNamespace  # noqa: E402

from expense_recon.output.single_currency import (  # noqa: E402
    BASE_CURRENCY,
    RowConversion,
    allocate,
    convert_rows,
    summary_lines,
    total_line,
    unconverted_note,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import usd_reference_rate  # noqa: E402

JPG = b"\xff\xd8\xff\xe0item98-bytes"

CARDS = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838"],
        "entity": "Corporate Services",
        "person": "Dirk",
        "zoho_account": "Chase 2838",
    },
}

# The typed rates. EUR is deliberately NOT the rate the fixture's charge
# implies, so a test that used the wrong rung would fail rather than agree by
# coincidence. Both live months price every row, so the default fixture does
# too; `test_a_currency_with_no_rate_*` drops BRL to prove the other path.
SETTINGS_RATES = {"EUR:USD": "1.10", "BRL:USD": "0.20"}

CARD_HEADERS = ("Card", "Date", "Description", "Type", "Amount")
CARD_ROWS = [
    ("2838", datetime(2026, 9, 5), "KAUFLAND", "Sale", -56.00),
    ("2838", datetime(2026, 9, 6), "ANTHROPIC", "Sale", -30.00),
]

# (file, vendor, total, date, currency)
RECEIPTS = [
    ("kaufland.jpg", "Kaufland", "50.00", "2026-09-05", "EUR"),
    ("anthropic.jpg", "Anthropic", "30.00", "2026-09-06", "USD"),
    ("hotel.jpg", "Hotel Berlin", "20.00", "2026-09-07", "EUR"),
    ("padaria.jpg", "Padaria Sao Paulo", "100.00", "2026-09-08", "BRL"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _wire(monkeypatch):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date=day, total=total, currency=ccy, vendor=vendor,
                reference="", line_items=(), confidence=0.9, notes="",
                payment_hint=None,
            )
            for _n, vendor, total, day, ccy in RECEIPTS
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.12, converted_amount=Decimal("56.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx_bytes(rows, headers) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _month(client, monkeypatch, rates=None) -> str:
    """September with four receipts in three currencies, then a USD Chase
    workbook whose KAUFLAND charge settles the EUR receipt."""
    assert client.put(
        "/api/settings",
        json={
            "cards": CARDS,
            "fx_reference_rates": SETTINGS_RATES if rates is None else rates,
        },
    ).status_code == 200
    _wire(monkeypatch)
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": "September 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + name.encode(), "application/octet-stream"))
            for name, *_rest in RECEIPTS
        ],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "September2026.xlsx", _xlsx_bytes(CARD_ROWS, CARD_HEADERS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch_id


def _csv_rows(client, batch_id):
    """The export CSV as (header, data rows, footer lines)."""
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    parsed = list(csv.reader(io.StringIO(resp.text)))
    header = parsed[0]
    body, footers = [], []
    for row in parsed[1:]:
        if not any(x.strip() for x in row):
            continue
        if len(row) == 1:
            footers.append(row[0])
        else:
            body.append(row)
    return header, body, footers


def _pdf_text(client, batch_id) -> str:
    """The report's text with runs of whitespace flattened to one space.

    The row captions live in a 54-point column and wrap, so the extractor
    returns "= USD 56.00 at\\n1.12, the charge". Matching the raw text would
    report a caption missing that is on the page, which is the shape of
    every false negative this project keeps paying for."""
    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    reader = PdfReader(io.BytesIO(resp.content))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return " ".join(raw.split())


def _charge(client, batch_id, vendor) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json()["rows"] if r["vendor"] == vendor)


def _cell(header, row, name) -> str:
    return row[header.index(name)].strip()


def _by_vendor(header, body) -> dict[str, list[str]]:
    return {_cell(header, r, "Vendor"): r for r in body}


# ── the CSV ─────────────────────────────────────────────────────────


def test_csv_fills_the_exchange_rate_column(client, monkeypatch):
    """The column that has shipped empty on every row since the export
    existed now carries the rate that priced the row."""
    batch_id = _month(client, monkeypatch)
    header, body, _footers = _csv_rows(client, batch_id)
    rows = _by_vendor(header, body)

    # The settled receipt takes the CHARGE's rate (56.00 / 50.00), not the
    # 1.10 typed in Settings. This is the assertion the whole item turns on.
    assert _cell(header, rows["Kaufland"], "Exchange Rate") == "1.120000"
    # No charge settled the hotel or the padaria, so both fall to the typed
    # rate for their own currency.
    assert _cell(header, rows["Hotel Berlin"], "Exchange Rate") == "1.100000"
    assert _cell(header, rows["Padaria Sao Paulo"], "Exchange Rate") == "0.200000"
    # A row already in the filing currency needs no rate: a column of 1.0s
    # is noise in a column a reader scans for what actually converted.
    assert _cell(header, rows["Anthropic"], "Exchange Rate") == ""


def test_csv_states_the_months_one_total(client, monkeypatch):
    """56.00 (the charge) + 30.00 (already USD) + 22.00 (20.00 at 1.10)
    + 20.00 (100.00 at 0.20) = 128.00, in one line under the rows."""
    batch_id = _month(client, monkeypatch)
    _header, _body, footers = _csv_rows(client, batch_id)
    joined = " ".join(footers)

    assert "Total in USD: 128.00" in joined
    # Every row priced, so nothing is missing and nothing says it is.
    assert "Partial" not in joined
    assert "no USD figure" not in joined


def test_a_currency_with_no_rate_is_named_not_counted_as_zero(
    client, monkeypatch
):
    """Item 65's rule on the money side. The figure is NOT called a total
    when it leaves an expense out: a heading a reader carries away cannot be
    undone by a caveat, so the heading itself says partial and says of how
    many."""
    batch_id = _month(client, monkeypatch, rates={"EUR:USD": "1.10"})
    _header, _body, footers = _csv_rows(client, batch_id)
    joined = " ".join(footers)

    assert "Partial total in USD: 108.00 (3 of 4 expenses" in joined
    assert "Total in USD: 108.00" not in joined
    # The CSV prints no row numbers and its order is not the
    # report's, so the note names the row by what is printed on it.
    assert "no USD figure (no rate for its currency)" in joined
    assert "Padaria Sao Paulo 2026-09-08 BRL 100.00" in joined
    assert "expense 4" not in joined


def test_csv_without_the_call_is_unchanged(client, monkeypatch, tmp_path):
    """The writer's own default writes exactly what it wrote before: the
    conversion is a callback, and no callback means no column and no
    footer."""
    from expense_recon.output.zoho_expense_export import (
        write_zoho_expense_export,
    )
    from expense_recon.matching.types import Receipt

    receipt = Receipt(
        document_id="a.jpg", legal_entity_id="Corporate Services",
        detected_date=None, detected_total=Decimal("10.00"),
        detected_currency="EUR", detected_vendor="Cafe",
    )
    out = write_zoho_expense_export([receipt], tmp_path / "plain.csv")
    text = out.read_text(encoding="utf-8")
    assert "Total in USD" not in text
    parsed = list(csv.reader(io.StringIO(text)))
    assert parsed[1][parsed[0].index("Exchange Rate")] == ""


# ── the month report ────────────────────────────────────────────────


def test_report_prints_the_figure_and_the_rate_on_the_row(client, monkeypatch):
    """Under each converted amount, what it is in USD and how that was
    reached; the rate's SOURCE is on the row because a reader who disputes
    the figure needs to know which rate to dispute."""
    batch_id = _month(client, monkeypatch)
    text = _pdf_text(client, batch_id)

    assert "= USD 56.00 at 1.12, the charge" in text, text
    assert "= USD 22.00 at 1.1, your rate" in text
    # A row already in the filing currency is not "converted" at 1.0.
    assert "= USD 30.00" not in text


def test_report_totals_the_month_in_one_currency(client, monkeypatch):
    """The figure rides the header line, beside the per-currency totals that
    raise the question it answers."""
    batch_id = _month(client, monkeypatch)
    text = _pdf_text(client, batch_id)

    assert "BRL 100.00 · EUR 70.00 · USD 30.00 · Total in USD: 128.00" in text
    assert "no USD figure" not in text


def test_report_says_which_rows_it_could_not_price(client, monkeypatch):
    batch_id = _month(client, monkeypatch, rates={"EUR:USD": "1.10"})
    text = _pdf_text(client, batch_id)

    assert "Partial total in USD: 108.00 (3 of 4 expenses" in text
    assert "no USD figure (no rate for its currency)" in text


def test_a_single_currency_month_says_nothing_extra(client, monkeypatch):
    """The gate on the whole feature: a month already in the filing currency
    answers the question on the line above, and repeating the same number
    under a second heading only teaches the reader to skim."""
    assert client.put(
        "/api/settings", json={"cards": CARDS}
    ).status_code == 200
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client",
        lambda cfg: (MockLLMClient(extraction_responses=[
            ExtractedReceipt(
                date="2026-09-06", total="30.00", currency="USD",
                vendor="Anthropic", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ]), None),
    )
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": "September 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("anthropic.jpg", JPG, "application/octet-stream"))],
    ))

    _header, _body, footers = _csv_rows(client, batch_id)
    assert footers == []
    assert "Total in USD" not in _pdf_text(client, batch_id)


# ── the rules the rungs rest on ─────────────────────────────────────


def test_a_rejected_pair_lends_no_rate(client, monkeypatch):
    """Item 111's rule, on the money side: a pair the reviewer threw out is
    not evidence of what the card charged, so the row falls back to the
    typed rate and the month total moves with it."""
    batch_id = _month(client, monkeypatch)
    charge = _charge(client, batch_id, "KAUFLAND")
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={
            "transaction_id": charge["transaction_id"],
            "status": "rejected",
            "chosen_document_id": charge.get("chosen_document_id"),
        },
    )
    assert resp.status_code == 200, resp.text

    header, body, footers = _csv_rows(client, batch_id)
    rows = _by_vendor(header, body)
    assert _cell(header, rows["Kaufland"], "Exchange Rate") == "1.100000"
    # 50.00 at 1.10 = 55.00, so the month reads 1.00 lower than before.
    assert "Total in USD: 127.00" in " ".join(footers)


def test_a_split_receipt_converts_once_and_ties_to_the_charge():
    """Two accounts on one receipt are two listing rows and ONE purchase.
    Rounding each row alone would miss the charge by a cent, which on a
    settled row is the difference between tying out and not."""
    columns = ("Expense Date", "Expense Amount", "Currency Code")
    rows = [
        ["2026-09-05", "16.67", "EUR"],
        ["2026-09-05", "33.33", "EUR"],
    ]
    converted, totals, unconverted, _blank = convert_rows(
        rows, columns,
        numbers_by_doc={"split.jpg": [1, 2]},
        settled_amounts={"split.jpg": (Decimal("56.00"), "USD")},
        reference_rate=lambda ccy, on: None,
    )
    assert unconverted == []
    assert converted[1].amount + converted[2].amount == Decimal("56.00")
    assert totals[BASE_CURRENCY] == Decimal("56.00")


def test_allocation_puts_the_remainder_on_a_row_that_has_an_amount():
    """A zero-amount split never acquires a figure out of nowhere."""
    parts = allocate(
        [Decimal("10.00"), Decimal("0.00"), Decimal("10.00")],
        Decimal("1.115"),
    )
    assert sum(parts) == (Decimal("20.00") * Decimal("1.115")).quantize(
        Decimal("0.01")
    )
    assert parts[1] == Decimal("0.00")


def test_a_charge_in_another_currency_is_not_used_as_a_rate():
    """Converting through two rates would print a figure neither document
    can source, so a non-USD charge lends nothing and the row falls to the
    reference rate."""
    columns = ("Expense Date", "Expense Amount", "Currency Code")
    rows = [["2026-09-05", "50.00", "EUR"]]
    converted, _totals, _unconverted, _blank = convert_rows(
        rows, columns,
        numbers_by_doc={"a.jpg": [1]},
        settled_amounts={"a.jpg": (Decimal("290.00"), "BRL")},
        reference_rate=lambda ccy, on: (Decimal("1.10"), "configured", ""),
    )
    assert converted[1].source == "configured"
    assert converted[1].amount == Decimal("55.00")


def test_an_unreadable_amount_is_skipped_not_counted_as_zero():
    """The rows item 97 captions are already out of every other total on
    the page; a single-currency total that counted them would be the only
    one pretending they were free."""
    columns = ("Expense Date", "Expense Amount", "Currency Code")
    rows = [["2026-09-05", "", "EUR"], ["2026-09-06", "10.00", "EUR"]]
    converted, totals, _unconverted, _blank = convert_rows(
        rows, columns,
        numbers_by_doc={"a.jpg": [1], "b.jpg": [2]},
        reference_rate=lambda ccy, on: (Decimal("1.10"), "configured", ""),
        skip={1},
    )
    assert 1 not in converted
    assert totals[BASE_CURRENCY] == Decimal("11.00")


def test_notes_and_lines_are_silent_when_there_is_nothing_to_say():
    """A clean month says nothing rather than "0 receipts not converted"."""
    assert unconverted_note([]) == ""
    assert total_line({}, []) == ""
    assert RowConversion(None, None, "").caption() == ""

# ── what the adversarial review of this change found ────────────────


def _run_with(config: dict):
    """The two attributes `usd_reference_rate` reads off a run."""
    return SimpleNamespace(config=config, work_dir=".")


def test_the_ecb_rung_actually_fires_on_a_listing_date():
    """The review's first finding, and the one that mattered.

    `ecb_monthly_rate` takes a `date` or a "YYYY-MM" string and rejects
    anything else. The listing cell is a full ISO date, so handing it over
    verbatim failed the month-key match and the ECB rung returned None on
    every row: rung 3 had silently become Settings-typed-rate-only, and a
    hosted month (which carries an ECB table and nothing typed) reported "no
    rate for its currency" for every foreign receipt. The matcher passes a
    `date` object; so must this, or the document and the screen quote
    different rates for the same purchase, which is the thing reusing
    `_reference_rate_for` was for.
    """
    lookup = usd_reference_rate(_run_with({
        "matching": {"fx_ecb_monthly_rates": {
            "2026-09": {"USD": "1.17", "BRL": "6.30"},
        }},
    }))
    assert lookup is not None

    hit = lookup("EUR", "2026-09-05")
    assert hit is not None, "the ECB rung did not fire on a listing date"
    rate, source, month = hit
    assert source == "ecb_month"
    assert month == "2026-09"
    assert rate == Decimal("1.170000")
    # A cross rate through EUR, and a plain month key still works.
    assert lookup("BRL", "2026-09-05")[0] == (
        Decimal("1.17") / Decimal("6.30")
    ).quantize(Decimal("0.000001"))
    assert lookup("EUR", "2026-09")[1] == "ecb_month"
    # Junk in the cell is not a crash and not a guess.
    assert lookup("EUR", "not-a-date") is None
    assert lookup("EUR", "") is None


def test_a_typed_rate_still_outranks_the_ecb_table():
    """Precedence is the matcher's, unchanged: operator intent first."""
    lookup = usd_reference_rate(_run_with({
        "matching": {
            "fx_reference_rates": {"EUR:USD": "1.10"},
            "fx_ecb_monthly_rates": {"2026-09": {"USD": "1.17"}},
        },
    }))
    rate, source, _month = lookup("EUR", "2026-09-05")
    assert (rate, source) == (Decimal("1.10"), "configured")


def test_a_row_with_no_readable_amount_gets_no_rate_and_its_own_reason():
    """The review's third finding. A blank amount cell parsed as zero, so
    the row joined the total contributing nothing AND got an exchange rate
    stamped on it: a rate is a claim about a number, and there was no
    number. It is also not a currency problem, so it must not be reported as
    one."""
    columns = ("Expense Date", "Expense Amount", "Currency Code", "Vendor")
    rows = [
        ["2026-09-05", "", "EUR", "Mystery Cafe"],
        ["2026-09-06", "10.00", "EUR", "Hotel"],
    ]
    converted, totals, unconverted, no_amount = convert_rows(
        rows, columns,
        numbers_by_doc={"a.jpg": [1], "b.jpg": [2]},
        reference_rate=lambda ccy, on: (Decimal("1.10"), "configured", ""),
    )
    assert 1 not in converted, "a blank amount must not be priced"
    assert unconverted == [] and no_amount == [1]
    assert totals[BASE_CURRENCY] == Decimal("11.00")

    lines = summary_lines(totals, unconverted, converted, no_amount=no_amount)
    assert any("amount could not be read" in line for line in lines)
    assert not any("no rate for" in line for line in lines)


def test_a_charge_that_implies_no_usable_rate_falls_back(client, monkeypatch):
    """The review's fifth finding. Rung 2 used to be an `elif`, so a charge
    that was present but could not yield a positive rate blocked rung 3 and
    the row reported "no rate" for a currency the month has a rate for."""
    columns = ("Expense Date", "Expense Amount", "Currency Code")
    rows = [["2026-09-05", "50.00", "EUR"]]
    for charge in ((Decimal("-56.00"), "USD"), (Decimal("0.00"), "USD")):
        converted, _totals, unconverted, _blank = convert_rows(
            rows, columns,
            numbers_by_doc={"a.jpg": [1]},
            settled_amounts={"a.jpg": charge},
            reference_rate=lambda ccy, on: (Decimal("1.10"), "configured", ""),
        )
        assert unconverted == [], charge
        assert converted[1].source == "configured", charge
        assert converted[1].amount == Decimal("55.00"), charge


def test_a_rate_the_receipt_printed_is_not_overwritten(tmp_path):
    """The review's sixth finding. A rate read off the document is what that
    purchase was actually converted at; ours is a reconstruction, and the
    document outranks it."""
    from expense_recon.matching.types import Receipt
    from expense_recon.output.zoho_expense_export import (
        EXPENSE_COLUMNS as COLS,
        write_zoho_expense_export,
    )

    receipt = Receipt(
        document_id="a.jpg", legal_entity_id="Corporate Services",
        detected_date=None, detected_total=Decimal("10.00"),
        detected_currency="EUR", detected_vendor="Cafe",
        exchange_rate=Decimal("1.08"),
    )
    out = write_zoho_expense_export(
        [receipt], tmp_path / "priced.csv",
        single_currency=lambda groups: ({1: "1.100000"}, []),
    )
    parsed = list(csv.reader(io.StringIO(out.read_text(encoding="utf-8"))))
    assert parsed[1][COLS.index("Exchange Rate")] == "1.08"

