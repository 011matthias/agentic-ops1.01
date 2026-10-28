"""Item 138, the month page's half (owner ruling 2026-09-17: "a tab per card
showing whether its statement is loaded, how many charges matched and what's
still open, plus 'All' and 'No card'").

Both month pages get the tabs from their own GET: `card_sections[]` (one entry
per card in the PDFs' order, No card last) and a `card_section` key on every
row, receipt and expense the page lists. The grouping is the one the PDFs
section on (`_pdf_common.card_sections` over the item 137 card chain), so a
tab and its PDF section can never file a receipt differently.

Route-level throughout: a real month (settings cards, receipt upload,
statement attach, a card pick) read back through `GET /api/runs/{id}`,
`GET /api/expense-batches/{id}` and the reconciliation report, plus a seeded
snapshot for the booked-without-receipt figures.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    JPG,
    _attach,
    _done,
    _expense,
    _extraction,
    _month,
    _pick_card,
    _wire,
)
from tests.test_reconciliation_report_by_card_item_138 import (  # noqa: E402
    _first,
    _month_with_images,
    _pages,
)

LABEL_2838 = "Credit Card Chase Visa - 2838"
LABEL_3645 = "Credit Card Chase Visa - 3645"
EXPENSE_ONLY = ("n_expenses", "totals_by_ccy")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


AUGUST_RECEIPTS = (
    _extraction("Pressmaster", "135.00", "2026-08-23"),
    _extraction("Zoom", "15.00", "2026-08-10", "Visa ending 2838"),
    _extraction("Lovable", "25.00", "2026-08-05"),
    _extraction("Taxi", "30.00", "2026-08-12"),
)
AUGUST_CHARGES = [
    ("2838", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
    ("2838", datetime(2026, 8, 14), "GITHUB", "Sale", -40.00),
    ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
]


def _august(client, batch: str) -> tuple[dict, dict]:
    """Two cards with charges: on 2838 a held receipt, a charge with no
    receipt and a receipt with no charge that PRINTS 2838; on 3645 the live
    LOVABLE case (held there, picked as 2838); and a receipt with no card.
    Returns (run payload, expense payload)."""
    _attach(client, batch, AUGUST_CHARGES)
    lovable = _expense(client, batch, "Lovable")["document_id"]
    resp = _pick_card(client, batch, lovable, "corp-2838")
    assert resp.status_code == 200, resp.text
    run = client.get(f"/api/runs/{batch}")
    grid = client.get(f"/api/expense-batches/{batch}")
    assert run.status_code == 200, run.text
    assert grid.status_code == 200, grid.text
    return run.json(), grid.json()


@pytest.fixture
def august(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, *AUGUST_RECEIPTS)
    return _august(client, _month(client, 4))


def _by_key(sections: list[dict]) -> dict[str, dict]:
    return {s["key"]: s for s in sections}


def test_the_matching_page_has_a_tab_per_card_with_its_statement_figures(august):
    run, _grid = august
    sections = run["card_sections"]
    assert [s["key"] for s in sections] == ["corp-2838", "corp-3645", ""]
    assert [s["label"] for s in sections] == [LABEL_2838, LABEL_3645, "No card"]

    by = _by_key(sections)
    card_2838 = by["corp-2838"]
    assert card_2838["digits"] == ["2838"]
    assert card_2838["statement"] == "loaded"
    assert card_2838["statements"] == ["August2026.xlsx"]
    assert (card_2838["period_start"], card_2838["period_end"]) == (
        "2026-08-14", "2026-08-23"
    )
    assert (card_2838["n_charges"], card_2838["n_matched"]) == (2, 1)
    assert card_2838["unreconciled_by_ccy"] == {"USD": "40.00"}
    # Pressmaster is held here; Zoom prints 2838 and no charge holds it.
    assert (card_2838["n_receipts"], card_2838["n_receipts_without_charge"]) == (2, 1)
    assert card_2838["n_booked_without_receipt"] == 0
    assert card_2838["booked_without_receipt_by_ccy"] == {}

    card_3645 = by["corp-3645"]
    # The Lovable receipt was picked as 2838 but its charge is on 3645: a held
    # receipt follows its charge's card, as in the PDF.
    assert (card_3645["n_charges"], card_3645["n_matched"]) == (1, 1)
    assert card_3645["unreconciled_by_ccy"] == {}
    assert (card_3645["n_receipts"], card_3645["n_receipts_without_charge"]) == (1, 0)

    no_card = by[""]
    assert no_card["statement"] is None and no_card["digits"] == []
    assert (no_card["n_charges"], no_card["n_receipts"]) == (0, 1)
    assert no_card["n_receipts_without_charge"] == 1
    assert all(not set(EXPENSE_ONLY) & set(s) for s in sections)


def test_every_row_and_receipt_on_the_matching_page_names_its_tab(august):
    run, _grid = august
    keys = {s["key"] for s in run["card_sections"]}
    charge_tab = {row["vendor"]: row["card_section"] for row in run["rows"]}
    assert charge_tab == {
        "PRESSMASTER DMCC": "corp-2838", "GITHUB": "corp-2838", "LOVABLE": "corp-3645",
    }
    lovable = next(r for r in run["rows"] if r["vendor"] == "LOVABLE")
    assert lovable["cards_differ"]["receipt_card_key"] == "corp-2838"
    unmatched = {r["vendor"]: r["card_section"] for r in run["unmatched_receipts"]}
    assert unmatched == {"Zoom": "corp-2838", "Taxi": ""}
    for listing in ("unmatched_receipts", "copies_set_aside", "assignable_receipts"):
        for rec in run[listing]:
            assert rec["card_section"] in keys, (listing, rec)
    # The page's "Receipts without a charge" per tab is the section's figure.
    for sec in run["card_sections"]:
        assert sec["n_receipts_without_charge"] == sum(
            1 for r in run["unmatched_receipts"] if r["card_section"] == sec["key"]
        ), sec


def test_the_expenses_page_has_the_same_tabs_and_counts_its_rows_per_tab(august):
    run, grid = august
    sections = grid["card_sections"]
    assert [
        {k: v for k, v in s.items() if k not in EXPENSE_ONLY} for s in sections
    ] == run["card_sections"]

    placed = {e["vendor"]["display"]: e["card_section"] for e in grid["expenses"]}
    assert placed == {
        "Pressmaster": "corp-2838", "Zoom": "corp-2838",
        "Lovable": "corp-3645", "Taxi": "",
    }
    by = _by_key(sections)
    assert (by["corp-2838"]["n_expenses"], by["corp-2838"]["totals_by_ccy"]) == (
        2, {"USD": "150.00"}
    )
    assert (by["corp-3645"]["n_expenses"], by["corp-3645"]["totals_by_ccy"]) == (
        1, {"USD": "25.00"}
    )
    assert (by[""]["n_expenses"], by[""]["totals_by_ccy"]) == (1, {"USD": "30.00"})
    assert sum(s["n_expenses"] for s in sections) == grid["summary"]["n_expenses"]


def test_the_tabs_are_the_reconciliation_reports_sections_in_its_order(
    client, monkeypatch
):
    """The same month with real images, so the PDF renders: its card headings
    run in `card_sections` order and each heading line carries the tab's
    figures."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, *AUGUST_RECEIPTS)
    batch = _month_with_images(client, ["red", "green", "blue", "yellow"])
    run, _grid = _august(client, batch)
    resp = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    pages = _pages(resp.content)

    at = 1
    for sec in run["card_sections"]:
        at = _first(pages, sec["label"], at)
        assert pages[at].startswith(sec["label"]), (sec["label"], pages[at])
        if sec["n_charges"]:
            assert (
                f"{sec['n_charges']} charge{'s' if sec['n_charges'] != 1 else ''}"
                f" · {sec['n_matched']} matched"
            ) in pages[at], (sec, pages[at])
        n = sec["n_receipts"]
        assert f"{n} receipt{'' if n == 1 else 's'}" in pages[at], (sec, pages[at])
        at += 1


def test_a_one_card_month_has_no_tabs_and_its_rows_still_name_their_card(
    client, monkeypatch
):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Pressmaster", "135.00", "2026-08-23"),
        _extraction("Taxi", "30.00", "2026-08-12"),
    )
    batch = _month(client, 2)
    _attach(client, batch, AUGUST_CHARGES[:1])
    run = client.get(f"/api/runs/{batch}").json()
    grid = client.get(f"/api/expense-batches/{batch}").json()

    assert run["card_sections"] == [] and grid["card_sections"] == []
    assert [r["card_section"] for r in run["rows"]] == ["corp-2838"]
    assert {e["vendor"]["display"]: e["card_section"] for e in grid["expenses"]} == {
        "Pressmaster": "corp-2838", "Taxi": "",
    }


def test_a_month_without_a_statement_tabs_its_receipts_by_card(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Zoom", "15.00", "2026-09-10", "Visa ending 2838"),
        _extraction("Lovable", "25.00", "2026-09-05", "Visa ending 3645"),
        _extraction("Taxi", "30.00", "2026-09-12"),
    )
    batch = _month(client, 3, label="September 2026")
    grid = client.get(f"/api/expense-batches/{batch}").json()
    sections = grid["card_sections"]
    assert [s["key"] for s in sections] == ["corp-2838", "corp-3645", ""]
    for sec in sections[:2]:
        assert sec["statement"] == "not_loaded", sec
        assert (sec["n_charges"], sec["n_receipts"], sec["n_expenses"]) == (0, 1, 1)
    assert sections[0]["digits"] == ["2838"]  # from the registry: no coverage yet
    # With no statement the Matching address serves the expense payload, tabs
    # included.
    assert client.get(f"/api/runs/{batch}").json()["card_sections"] == sections


def test_a_trip_has_no_card_tabs(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    trip = client.post("/api/trips", json={
        "name": "Rome", "start": "2026-09-01", "end": "2026-09-10",
        "travelers": ["Dirk Neumann"],
    })
    assert trip.status_code == 200, trip.text
    _wire(
        monkeypatch,
        _extraction("Hotel", "300.00", "2026-09-02", "Visa ending 2838"),
        _extraction("Dinner", "80.00", "2026-09-03", "Visa ending 3645"),
    )
    resp = client.post("/api/expense-batches", files=[
        ("files", ("h.jpg", JPG + b"h", "application/octet-stream")),
        ("files", ("d.jpg", JPG + b"d", "application/octet-stream")),
    ], data={"batch_type": "trip", "trip_id": trip.json()["trip_id"]})
    _done(client, resp)
    grid = client.get(f"/api/expense-batches/{resp.json()['batch_id']}").json()
    assert grid["card_sections"] == []
    assert {e["card_section"] for e in grid["expenses"]} == {"corp-2838", "corp-3645"}


def _tx(tid, day, vendor, amount, last4, currency="USD", **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=date(2026, 4, day), posting_date=None,
        amount=Decimal(amount), transaction_currency=currency,
        account_card_currency=currency, vendor_from_statement=vendor,
        card_last4=last4, **kw,
    )


def _rc(doc, vendor, total, day) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=date(2026, 4, day),
        detected_total=Decimal(total), detected_currency="USD", detected_vendor=vendor,
    )


def test_booked_charges_without_a_receipt_are_counted_on_their_own_card(client):
    """Item 102's figure, per tab: a yellow row no receipt holds counts on its
    card, in its currency; a yellow row a receipt holds does not."""
    charges = [
        _tx("t_open", 1, "AMAZON", "180.00", "2838"),
        _tx("t_booked", 10, "YELLOW ROW", "50.00", "2838", entry_status="posted"),
        _tx("t_booked_eur", 11, "YELLOW EUR", "12.30", "3645", currency="EUR",
            entry_status="posted"),
        _tx("t_booked_ok", 15, "CAFE", "20.00", "3645", entry_status="posted"),
    ]
    receipts = [_rc("m1", "Cafe", "20.00", 15), _rc("m2", "Kiosk", "7.00", 16)]
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_booked_ok", document_id="m1", match_type=MatchType.EXACT,
            confidence=0.99, reason="exact", score=95,
            amount_score=1.0, date_score=1.0, vendor_score=1.0,
        )],
        unmatched_transactions=["t_open", "t_booked", "t_booked_eur"],
        unmatched_receipts=["m2"],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    store.create_run(
        run_id="booked", created_at="2026-05-02T00:00:00", label="April 2026",
        operator=None, summary={}, snapshot=snapshot_to_dict(charges, receipts, outcome, []),
        config={}, work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    store.close()
    run = client.get("/api/runs/booked").json()

    sections = run["card_sections"]
    assert [s["digits"] for s in sections] == [["2838"], ["3645"], []]
    card_2838, card_3645, no_card = sections
    assert card_2838["statement"] == "not_recorded"  # charges, no recorded upload
    assert card_2838["unreconciled_by_ccy"] == {"USD": "180.00"}
    assert (card_2838["n_booked_without_receipt"], card_2838["booked_without_receipt_by_ccy"]) == (
        1, {"USD": "50.00"}
    )
    assert (card_3645["n_booked_without_receipt"], card_3645["booked_without_receipt_by_ccy"]) == (
        1, {"EUR": "12.30"}
    )
    assert (card_3645["n_receipts"], card_3645["n_receipts_without_charge"]) == (1, 0)
    assert (no_card["n_receipts"], no_card["n_receipts_without_charge"]) == (1, 1)
    assert sum(s["n_booked_without_receipt"] for s in sections) == (
        run["summary"]["n_booked_no_receipt"]
    )
