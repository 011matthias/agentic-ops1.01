"""Item 220 step 6 + item 211: what the adjacent-month borrow now reaches.

Three gaps in the neighbour pool (`adjacent_pool_for_month`), each measured
on the 2026-09-25 backup before building:

1. **A receipt whose id the borrowing month already holds was dropped.**
   Months are ingested the same way, so `NNNN__rendered-body.pdf` repeats
   (live: August could not borrow July's Hostinger 172.61, September not
   August's Obsidian 96.00 or Zoho Books 576.00). It now joins under its own
   pool id, `borrowed_pool_id(home run, id)`, and every reader turns that
   back into (home run, id): the claim, the neighbour's `settled_by`, the
   receipt's image. The borrowing month's own receipt of the same id keeps
   its own pairing and its own claim.
2. **Item 211: a receipt printed the day before a calendar-month statement
   opens was outside every window.** Eligibility now starts three days
   before the period (owner yes 2026-09-25), and the arrival trigger that
   owes a neighbour a re-match reads the same window.
3. **The card the home row resolved never reached the borrow.** A pick made
   on July's row now scopes the receipt in August's matcher too.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import borrowed_pool_id  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from tests.test_adjacent_month_pool import (  # noqa: E402
    AUGUST_CSV,
    JPG,
    _attach,
    _august_view,
    _csv,
    _doc_id,
    _google_row,
    _receipt,
    _wire,
)
from tests.test_card_flows_back_c9 import (  # noqa: E402
    CARD_HEADERS,
    _done,
    _xlsx_bytes,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _month(client, label: str, files: list[tuple[str, bytes]]) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if files:
        _add(client, batch_id, files)
    return batch_id


def _add(client, batch_id: str, files: list[tuple[str, bytes]]) -> None:
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (n, b, "application/octet-stream")) for n, b in files],
    ))


def _claims(client, run_id: str) -> dict[tuple[str, str], str]:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return {
            (c["receipt_run_id"], c["document_id"]): c["transaction_id"]
            for c in store.get_claims_by_run(run_id)
        }


# ── 1. the colliding id ──────────────────────────────────────────────


JULY_FILE = JPG + b"-july-google"
AUGUST_FILE = JPG + b"-august-lovable"


def test_a_neighbour_receipt_sharing_an_id_is_borrowed_under_its_own(
    client, monkeypatch
):
    """The live shape: July and August each hold `0000__receipt.jpg`, two
    different receipts. August's 08-01 Google charge settles July's, and
    August's own Lovable receipt keeps its own pairing, claim and file."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", [("receipt.jpg", JULY_FILE)])
    august = _month(client, "August 2026", [("receipt.jpg", AUGUST_FILE)])
    doc = _doc_id(client, july)
    assert doc == _doc_id(client, august), "the fixture must collide"

    _attach(client, august, AUGUST_CSV)

    view = _august_view(client, august)
    row = _google_row(view)
    pool_id = borrowed_pool_id(july, doc)
    assert row["chosen_document_id"] == pool_id, (
        "July's receipt never reached August's matcher"
    )
    assert row["settled_by"] == {
        "run_id": july, "label": "July 2026", "kind": "adjacent",
        "document_id": doc,
    }
    cand = next(c for c in row["candidates"] if c["document_id"] == pool_id)
    assert cand["from_batch"] == row["settled_by"]
    own = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    assert own["chosen_document_id"] == doc
    assert "settled_by" not in own
    assert view["summary"]["n_adjacent_borrowed"] == 1
    assert view["summary"]["n_receipts"] == 1

    # One claim per receipt, each on its HOME month and its id there.
    claims = _claims(client, august)
    assert claims[(july, doc)] == row["transaction_id"]
    assert claims[(august, doc)] == own["transaction_id"]

    # July names the month that took its receipt; August's own row does not.
    jul = next(
        e for e in client.get(f"/api/expense-batches/{july}").json()["expenses"]
        if e["document_id"] == doc
    )
    assert jul["settled_by"]["run_id"] == august
    aug = next(
        e for e in client.get(f"/api/expense-batches/{august}").json()["expenses"]
        if e["document_id"] == doc
    )
    assert "settled_by" not in aug

    # The image under the pool id is July's file; under the plain id,
    # August's own.
    img = client.get(f"/api/runs/{august}/receipts/{pool_id}/image")
    assert img.status_code == 200 and img.content == JULY_FILE
    img = client.get(f"/api/runs/{august}/receipts/{doc}/image")
    assert img.status_code == 200 and img.content == AUGUST_FILE


def test_a_confirmed_pick_of_a_pool_id_claims_the_home_receipt(
    client, monkeypatch
):
    """A reviewer's confirm (`sync_claim_for_decision`) writes the same claim
    the re-match does: on July's receipt under July's id, never on August's
    own receipt of that id."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", [("receipt.jpg", JULY_FILE)])
    august = _month(client, "August 2026", [("receipt.jpg", AUGUST_FILE)])
    doc = _doc_id(client, july)
    _attach(client, august, AUGUST_CSV)
    row = _google_row(_august_view(client, august))
    pool_id = borrowed_pool_id(july, doc)

    resp = client.post(
        f"/api/runs/{august}/decisions",
        json={"transaction_id": row["transaction_id"], "status": "confirmed",
              "chosen_document_id": pool_id},
    )
    assert resp.status_code == 200, resp.text
    claims = _claims(client, august)
    assert claims[(july, doc)] == row["transaction_id"]
    assert (august, pool_id) not in claims and (july, pool_id) not in claims


# ── 2. item 211: the start edge ──────────────────────────────────────


# A calendar-month export: the period opens on the 1st.
AUGUST_CALENDAR_CSV = _csv(
    ("08/01/2026", "71.64", "GOOGLE WORKSPACE"),
    ("08/15/2026", "25.00", "LOVABLE"),
)


@pytest.mark.parametrize(
    "printed, borrowed",
    [("2026-07-31", True), ("2026-07-29", True), ("2026-07-28", False)],
)
def test_a_receipt_printed_before_a_calendar_month_opens_is_borrowed(
    client, monkeypatch, printed, borrowed
):
    """The differential probe for item 211: one date moves, the answer moves.
    Three days before the first charge is in, four is out."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", printed),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", [("jul.jpg", JULY_FILE)])
    august = _month(client, "August 2026", [("aug.jpg", AUGUST_FILE)])
    doc = _doc_id(client, july)

    _attach(client, august, AUGUST_CALENDAR_CSV)

    row = _google_row(_august_view(client, august))
    offered = [c for c in row["candidates"] if c["document_id"] == doc]
    if borrowed:
        assert offered and offered[0]["from_batch"]["run_id"] == july
    else:
        assert not offered and row["effective_bucket"] == "unmatched"
    if printed == "2026-07-31":
        assert row["chosen_document_id"] == doc


def test_a_card_cycle_period_is_not_widened(client, monkeypatch):
    """The narrowing, pinned: August cut the Chase way opens on 07-31, which
    already reaches over the month end, so a receipt printed 07-29 stays
    home. Widened, the live May and June months drew wrong neighbours."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-29"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", [("jul.jpg", JULY_FILE)])
    august = _month(client, "August 2026", [("aug.jpg", AUGUST_FILE)])
    doc = _doc_id(client, july)

    _attach(client, august, AUGUST_CSV)

    view = _august_view(client, august)
    assert all(
        c["document_id"] != doc for r in view["rows"] for c in r["candidates"]
    )
    assert view["summary"]["n_adjacent_borrowed"] == 0


def test_a_receipt_arriving_on_the_31st_owes_the_calendar_month_a_rematch(
    client, monkeypatch
):
    """The arrival trigger reads the same window (`neighbour_months_covering`):
    August's statement opens 08-01 and is already attached when July's 07-31
    receipt arrives, and August settles it without another event."""
    _wire(
        monkeypatch,
        _receipt("Cafe", "12.00", "2026-07-10"),
        _receipt("Lovable", "25.00", "2026-08-15"),
        _receipt("Google", "71.64", "2026-07-31"),
    )
    july = _month(client, "July 2026", [("cafe.jpg", JPG + b"-cafe")])
    august = _month(client, "August 2026", [("aug.jpg", AUGUST_FILE)])
    _attach(client, august, AUGUST_CALENDAR_CSV)
    assert _google_row(_august_view(client, august))["effective_bucket"] == "unmatched"

    _add(client, july, [("google.jpg", JULY_FILE)])

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        google = next(
            r["document_id"] for r in store.get_run(july).snapshot["receipts"]
            if r["document_id"].endswith("google.jpg")
        )
    assert _google_row(_august_view(client, august))["chosen_document_id"] == google


# ── 3. the home row's card rides along ───────────────────────────────


# Two cards of ONE company, so only the card (never the entity) can tell
# the two Google charges apart.
CARDS = {
    "corp-2838": {
        "label": "Corporate card (Chase)", "digits": ["2838"],
        "entity": "Corporate Services", "person": "Dirk",
        "zoho_account": "Chase 2838",
    },
    "corp-3645": {
        "label": "Second corporate card", "digits": ["3645"],
        "entity": "Corporate Services", "person": "Nicolas",
        "zoho_account": "Chase 3645",
    },
}
# The 3645 charge is the closer date, so without the card the receipt would
# lean to it; the pick on July's row says 2838.
AUGUST_TWO_CARDS = [
    ("2838", datetime(2026, 7, 31), "OPENAI", "Sale", -80.28),
    ("3645", datetime(2026, 8, 1), "GOOGLE WORKSPACE", "Sale", -71.64),
    ("2838", datetime(2026, 8, 3), "GOOGLE WORKSPACE", "Sale", -71.64),
    ("2838", datetime(2026, 8, 15), "LOVABLE", "Sale", -25.00),
]


def test_a_card_picked_on_the_home_row_scopes_the_borrowed_receipt(
    client, monkeypatch
):
    assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    july = _month(client, "July 2026", [("google.jpg", JULY_FILE)])
    august = _month(client, "August 2026", [("lovable.jpg", AUGUST_FILE)])
    doc = _doc_id(client, july)
    resp = client.put(
        f"/api/runs/{july}/expenses/{doc}",
        json={"field": "card_key", "value": "corp-2838"},
    )
    assert resp.status_code == 200, resp.text

    _done(client, client.post(
        f"/api/expense-batches/{august}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(AUGUST_TWO_CARDS, CARD_HEADERS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))

    rows = [
        r for r in _august_view(client, august)["rows"]
        if r["vendor"] == "GOOGLE WORKSPACE"
    ]
    holder = [r for r in rows if r.get("chosen_document_id") == doc]
    assert len(holder) == 1, rows
    assert holder[0]["date"] == "2026-08-03", holder[0]
    assert holder[0]["effective_bucket"] == "reconciled", holder[0]
