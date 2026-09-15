"""Report totals: formed in Decimal, and never short in silence (item 65).

Section 12 row 13 of `docs/electronic-storage-system-description.md` discloses
two defects in one line. Amounts are carried as strings so no precision is
lost, and the report then re-summed them in binary floating point; and a row
whose amount would not parse was skipped with `continue`, so a month could
print a total quietly short by one receipt with nothing on the page saying so.

The live months say what that is worth today: on 2026-09-15 both August
(`074a7b8905d7`) and July (`50622baec444`) printed totals equal to a Decimal
sum over the same amounts to the cent, with zero unparseable rows. Through the
app the Amount cell is always a finite two-decimal string -- `_amount` formats
a Decimal, and `validate_expense_field` refuses a non-finite total at the edge
-- so the drop path is unreachable from the route and the float error stays
below the printed digit (August USD accumulated 2663.9500000000007 against an
exact 2663.95). The arithmetic is still the wrong arithmetic, and the builder
is a public function whose row contract does not promise two decimals, so the
fixtures below are constructed: that is the protocol's answer when the live
case does not reproduce, not a reason to skip the fix.

Route-level, through `GET /runs/{id}/expense-report.pdf`, because the caller
the fix changed is the report route, not the summing helper it added.
"""
from __future__ import annotations

import io
import re
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output._pdf_common import (  # noqa: E402
    UNREADABLE_CAPTION,
    excluded_note,
    parse_amount,
    sum_amounts,
)
from expense_recon.output.month_report_pdf import (  # noqa: E402
    build_expense_report_pdf,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

COL_AMOUNT = EXPENSE_COLUMNS.index("Expense Amount")


def _jpg(tag: str) -> bytes:
    """Distinct bytes per file. Byte-identical uploads collapse as
    duplicates (item 56), which would quietly leave a two-receipt fixture
    holding one expense."""
    return b"\xff\xd8\xff\xe0fake-jpeg-bytes-" + tag.encode()


def _norm(text: str) -> str:
    """PDF text extraction breaks a cell's caption across lines and keeps
    the layout's double spaces, so assertions compare normalized text."""
    return re.sub(r"\s+", " ", text)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(Path(tmp_path))
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-07-01", total="42.50", currency="EUR", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _batch(client, files):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "Corporate Services"}
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    add = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (n, d, "application/octet-stream")) for n, d in files],
    )
    assert add.status_code == 200, add.text
    assert client.get(f"/jobs/{add.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _report_text(client, batch_id) -> str:
    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    reader = PdfReader(io.BytesIO(resp.content))
    return _norm("\n".join(p.extract_text() or "" for p in reader.pages))


def _row(**kw) -> list[str]:
    row = [""] * len(EXPENSE_COLUMNS)
    for key, value in kw.items():
        row[EXPENSE_COLUMNS.index(key)] = value
    return row


def _listing(pdf: bytes) -> str:
    return _norm(PdfReader(io.BytesIO(pdf)).pages[0].extract_text() or "")


# ── the silent drop, through the route ──────────────────────────────


def test_an_unreadable_amount_is_captioned_and_counted_not_dropped(
    client, monkeypatch
):
    """The regress target. A row the total cannot read says so on its own
    row AND in a footer that counts it, instead of leaving a total quietly
    short by one receipt.

    The bad cell is injected at the seam the route uses, because no input
    the app accepts can produce one: this is defence in depth on a public
    builder, and the constructed fixture is how the protocol says to build
    when the live case does not reproduce.
    """
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Trenitalia", total="42.50"),
        _extraction(vendor="Cafe Lisboa", total="18.00"),
    )
    batch_id = _batch(client, [("tren.jpg", _jpg("tren")), ("cafe.jpg", _jpg("cafe"))])

    from expense_recon.web import service as svc

    real = svc.build_expense_rows

    def corrupt(*args, **kwargs):
        rows = [list(r) for r in real(*args, **kwargs)]
        rows[1][COL_AMOUNT] = "eighteen euro"
        return rows

    monkeypatch.setattr(svc, "build_expense_rows", corrupt)

    text = _report_text(client, batch_id)

    # The caption sits on the row itself.
    assert UNREADABLE_CAPTION in text
    # The footer counts it and names which expense to go look at.
    assert "1 receipt excluded from the total: expense 2." in text
    # And the total is the ONE amount that could be read -- not 60.50, and
    # not a total that silently pretends 42.50 is the whole month.
    assert "EUR 42.50" in text
    assert "60.50" not in text


def test_two_unreadable_amounts_are_both_named(client, monkeypatch):
    """Plural, and the numbers are listed so the reader can find them."""
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="A", total="10.00"),
        _extraction(vendor="B", total="20.00"),
        _extraction(vendor="C", total="30.00"),
    )
    batch_id = _batch(
        client,
        [("a.jpg", _jpg("a")), ("b.jpg", _jpg("b")), ("c.jpg", _jpg("c"))],
    )

    from expense_recon.web import service as svc

    real = svc.build_expense_rows

    def corrupt(*args, **kwargs):
        rows = [list(r) for r in real(*args, **kwargs)]
        rows[0][COL_AMOUNT] = "n/a"
        rows[2][COL_AMOUNT] = "see attached"
        return rows

    monkeypatch.setattr(svc, "build_expense_rows", corrupt)

    text = _report_text(client, batch_id)
    assert "2 receipts excluded from the total: expenses 1, 3." in text
    assert "EUR 20.00" in text


def test_a_clean_month_says_nothing_about_exclusions(client, monkeypatch):
    """Neutral at zero: a report where every amount read does not carry a
    "0 receipts excluded" line. Both live months are this case."""
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Trenitalia", total="42.50"),
        _extraction(vendor="Cafe Lisboa", total="18.00"),
    )
    batch_id = _batch(client, [("tren.jpg", _jpg("tren")), ("cafe.jpg", _jpg("cafe"))])

    text = _report_text(client, batch_id)
    assert "excluded from the total" not in text
    assert UNREADABLE_CAPTION not in text
    assert "EUR 60.50" in text


# ── the arithmetic, through the route and at the builder ────────────


def test_the_route_prints_the_decimal_sum_for_a_float_hostile_month(
    client, monkeypatch
):
    """The 0.1 + 0.2 shape end to end. In binary float these three amounts
    accumulate to 0.6000000000000001; the printed month total is the exact
    decimal sum."""
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="A", total="0.10"),
        _extraction(vendor="B", total="0.20"),
        _extraction(vendor="C", total="0.30"),
    )
    batch_id = _batch(
        client,
        [("a.jpg", _jpg("a")), ("b.jpg", _jpg("b")), ("c.jpg", _jpg("c"))],
    )

    assert 0.10 + 0.20 + 0.30 != 0.60  # the arithmetic being replaced
    text = _report_text(client, batch_id)
    assert "EUR 0.60" in text
    assert "0.6000000000000001" not in text


def test_the_printed_total_changes_when_the_sum_is_decimal():
    """The float sum and the Decimal sum print DIFFERENT cents here, which
    is what makes this the observable half of row 13.

    `2.675` is not representable in binary: the nearest double is just below
    it, so float rounds the total down to 2.67 while the exact decimal value
    rounds half-to-even up to 2.68. The builder's row contract is "export
    rows"; it does not promise two decimals, and rounding a reader's money
    the wrong way because of the storage format is the defect.
    """
    rows = [_row(**{"Expense Amount": "2.675", "Currency Code": "EUR",
                    "Vendor": "Half a cent"})]
    listing = _listing(build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Rounding",
    ))
    assert "EUR 2.68" in listing
    assert "EUR 2.67" not in listing
    assert f"{float('2.675'):,.2f}" == "2.67"  # what it printed before


def test_a_trip_sections_per_person_sum_in_decimal_too():
    """The second total site: a sectioned listing sums each slice with the
    same helper, so a per-person line and the month's line cannot disagree
    about the arithmetic they used."""
    rows = [
        _row(**{"Expense Amount": "2.675", "Currency Code": "EUR",
                "Vendor": "Dirk one"}),
        _row(**{"Expense Amount": "1.00", "Currency Code": "EUR",
                "Vendor": "Criss one"}),
    ]
    pdf = build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Trip",
        sections=[
            {"person": "Dirk", "on_roster": True, "start": 1, "count": 1},
            {"person": "Criss", "on_roster": True, "start": 2, "count": 1},
        ],
    )
    listing = _listing(pdf)
    assert "Dirk: 1 expense" in listing
    assert "EUR 2.68" in listing


def test_an_unreadable_row_inside_a_section_still_reaches_the_footer():
    """A sectioned report keeps the same guarantee: the per-person sum drops
    the row it cannot read, and the footer still names it."""
    rows = [
        _row(**{"Expense Amount": "10.00", "Currency Code": "EUR",
                "Vendor": "Readable"}),
        _row(**{"Expense Amount": "later", "Currency Code": "EUR",
                "Vendor": "Not readable"}),
    ]
    pdf = build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Trip",
        sections=[
            {"person": "Dirk", "on_roster": True, "start": 1, "count": 2},
        ],
    )
    listing = _listing(pdf)
    assert UNREADABLE_CAPTION in listing
    assert "1 receipt excluded from the total: expense 2." in listing
    assert "Dirk: 2 expenses · EUR 10.00" in listing


# ── the helper's own edges ──────────────────────────────────────────


def test_a_blank_amount_is_zero_and_a_nonfinite_one_is_unreadable():
    """Blank has always counted as nothing and still does; that is not the
    same event as a cell nobody can parse. NaN is the trap: it PARSES, and
    a float sum would carry it into every other row's total."""
    assert parse_amount("") == Decimal("0")
    assert parse_amount(None) == Decimal("0")
    assert parse_amount("1,234.56") == Decimal("1234.56")
    assert parse_amount("NaN") is None
    assert parse_amount("Infinity") is None
    assert parse_amount("eighteen euro") is None

    totals, unreadable = sum_amounts([
        (1, "EUR", "10.00"), (2, "EUR", "NaN"), (3, "EUR", "5.00"),
    ])
    assert totals == {"EUR": Decimal("15.00")}
    assert unreadable == [2]


def test_an_empty_currency_buckets_rather_than_vanishing():
    totals, unreadable = sum_amounts([(1, "", "7.00"), (2, None, "3.00")])
    assert totals == {"?": Decimal("10.00")}
    assert unreadable == []


def test_the_footer_is_silent_at_zero_and_singular_at_one():
    assert excluded_note([]) == ""
    assert excluded_note([4]) == "1 receipt excluded from the total: expense 4."
    assert excluded_note([7, 4]) == (
        "2 receipts excluded from the total: expenses 4, 7."
    )


# ── the payload half ────────────────────────────────────────────────


def test_the_batch_payload_counts_expenses_with_no_readable_amount(
    client, monkeypatch
):
    """`summary.n_amounts_unreadable`: the count a reviewer can act on. A
    receipt whose amount was never read is in no total -- `totals_by_ccy`
    skips it and the listing cannot print it -- so the month says how many
    there are instead of leaving the gap to arithmetic."""
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Readable", total="42.50"),
        _extraction(vendor="Unreadable", total=None),
    )
    batch_id = _batch(
        client, [("a.jpg", _jpg("a")), ("b.jpg", _jpg("b"))]
    )

    summary = client.get(f"/api/expense-batches/{batch_id}").json()["summary"]
    assert summary["n_amounts_unreadable"] == 1
    # The field answers its own question and moves nothing else: the total
    # still carries only the amount that was readable.
    assert summary["totals_by_ccy"] == {"EUR": "42.50"}


def test_the_count_is_zero_on_a_month_where_every_amount_read(
    client, monkeypatch
):
    """Both live months on 2026-09-15 are this case."""
    _patch_ocr(monkeypatch, _extraction(vendor="Readable", total="42.50"))
    batch_id = _batch(client, [("a.jpg", _jpg("a"))])

    summary = client.get(f"/api/expense-batches/{batch_id}").json()["summary"]
    assert summary["n_amounts_unreadable"] == 0
