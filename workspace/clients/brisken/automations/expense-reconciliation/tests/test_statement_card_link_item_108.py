"""Item 108 (the 1176 half): a statement upload names the card it covers.

Live August 2026 is the case. `20260804-statements-1176-.pdf` is attached,
the month holds the three charges it printed on card 1176, and the coverage
panel still reads `statements: []` for `card-1176` while the row labelled
"No card on the charge" holds the file. Read off the screen that says "we
have no statement for this card", which is how the item came to propose
asking Dirk for a file the month already had.

Both joins that could have answered were blind, each for its own reason:

* the operator typed no card (the plain attach form names none), so the
  `card_key` voice was silent;
* the charge voice read `statement_anchors`, the WRITEBACK's map, which is
  empty by construction for a PDF. `statement_origins` (note item T3) is
  the record that does hold a PDF's charges, and it existed already; the
  coverage join simply never read it.

That is the first half here. The second is the month the live August one
actually is: recorded BEFORE the origins existed, so nothing at all names
its PDF's charges. For that shape the file's own name is the last thing
left, and it is read the narrow way: a digit run counts only where it
resolves to a card the registry DEFINES, so 1176 lands and the cycle date
20260804 does not become a card.

Everything here runs through the FastAPI app.
"""
from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.statement_origin import (  # noqa: E402
    STATEMENT_ORIGINS_KEY,
)
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
PDF_BYTES = b"%PDF-1.4 synthetic"

# A Chase cycle whose card is printed where a real one prints it, at the
# foot of the activity. Two charges, both on 1176.
PDF_PAGE_1 = """\
Opening/Closing Date 07/04/26 - 08/03/26
ACCOUNT ACTIVITY
07/05 COFFEE SHOP NYC 5.75
"""
PDF_PAGE_2 = """\
Page 2 of 2
07/10 AWS CLOUD SERVICES 100.00
TRANSACTIONS THIS CYCLE (CARD 1176) $105.75
"""

# The live attach form names no card and no account: this is what the plain
# dialog sends, and it is why both last resorts matter.
BARE_FORM = {"account_id": "", "account_card_currency": "USD"}

XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-07-10", total="100.00", currency="USD", vendor="AWS",
            reference="", line_items=(), confidence=0.9, notes="",
            payment_hint=None,
        ),
    ])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _cards(client, **cards) -> None:
    """Seed the registry BEFORE the batch: a batch snapshots the composed
    registry into its own config, and coverage reads that snapshot."""
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


def _batch(client, label="August 2026") -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("aws.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _attach_pdf(client, batch_id, filename="20260804-statements-1176-.pdf"):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (filename, PDF_BYTES, "application/pdf")},
        data=dict(BARE_FORM),
    ))


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount", "Card"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _forget_the_origins(client, batch_id) -> None:
    """Make the month the one Criss actually has: recorded before
    `statement_origins` existed, so no record names which upload printed
    which charge. The anchors are left exactly as they are, which for a PDF
    upload means empty."""
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot or {})
        assert snapshot.pop(STATEMENT_ORIGINS_KEY, None) is not None, (
            "the origins were never recorded, so this fixture proves nothing"
        )
        assert store.update_run_snapshot(batch_id, snapshot)


def _coverage(client, batch_id) -> dict[str, dict]:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return {c["key"]: c for c in resp.json()["coverage"]}


ONE_ELEVEN_SEVENTY_SIX = {"card-1176": {
    "label": "Credit Card Chase Visa - 1176",
    "digits": ["1176"],
    "entity": "Consulting",
}}


# ── 1. the origins join, which is what a PDF has ────────────────────────


def test_a_pdf_statement_lands_on_the_card_its_charges_name(
    client, monkeypatch
):
    """The join the anchors could not make, isolated: the file is called
    `chase.pdf`, so nothing about the upload says "1176" except the charges
    it printed. Those are exactly what the origins record holds and the
    anchors, being the writeback's row map, do not."""
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [PDF_PAGE_1, PDF_PAGE_2],
    )
    _cards(client, **ONE_ELEVEN_SEVENTY_SIX)
    batch_id = _batch(client)
    _attach_pdf(client, batch_id, filename="chase.pdf")

    rows = _coverage(client, batch_id)
    assert rows["card-1176"]["statements"] == ["chase.pdf"]
    assert rows["card-1176"]["n_transactions"] == 2
    assert rows.get("", {}).get("statements", []) == [], (
        "the no-card row must not also hold it"
    )


# ── 2. the file name, for a month recorded before the origins ───────────


def test_a_month_older_than_the_origins_reads_the_file_name(
    client, monkeypatch
):
    """Live August. No origins, no anchors (a PDF has none), no typed card
    and no account id: the name is the only thing left that names 1176, and
    without it the file sits in the no-card row while the card it covers
    reads "no statement loaded"."""
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [PDF_PAGE_1, PDF_PAGE_2],
    )
    _cards(client, **ONE_ELEVEN_SEVENTY_SIX)
    batch_id = _batch(client)
    _attach_pdf(client, batch_id)
    _forget_the_origins(client, batch_id)

    rows = _coverage(client, batch_id)
    assert rows["card-1176"]["statements"] == [
        "20260804-statements-1176-.pdf"
    ]
    assert rows.get("", {}).get("statements", []) == []


def test_a_cycle_date_in_the_name_never_becomes_a_card(client, monkeypatch):
    """`20260804` is a digit run in the same name and is no card at all.
    The narrow rule is what keeps it out: only a run the registry resolves
    counts, so an unknown one leaves the file where it was rather than
    minting a `digits:` row out of a date."""
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [PDF_PAGE_1, PDF_PAGE_2],
    )
    _cards(client, **ONE_ELEVEN_SEVENTY_SIX)
    batch_id = _batch(client)
    _attach_pdf(client, batch_id, filename="20260804-statements-.pdf")
    _forget_the_origins(client, batch_id)

    rows = _coverage(client, batch_id)
    assert rows["card-1176"]["statements"] == []
    assert rows[""]["statements"] == ["20260804-statements-.pdf"]
    assert not [k for k in rows if k.startswith("digits:")], sorted(rows)


def test_two_cards_in_one_name_stay_silent(client, monkeypatch):
    """Ambiguity surfaces instead of guessing, the same ruling
    `resolve_card` follows. A file naming two defined cards picks
    neither."""
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [PDF_PAGE_1, PDF_PAGE_2],
    )
    _cards(client, **{
        **ONE_ELEVEN_SEVENTY_SIX,
        "card-3876": {"label": "Credit Card Chase Visa - 3876",
                      "digits": ["3876"], "entity": "Corporate Services"},
    })
    batch_id = _batch(client)
    _attach_pdf(client, batch_id, filename="statements-1176-and-3876.pdf")
    _forget_the_origins(client, batch_id)

    rows = _coverage(client, batch_id)
    assert rows["card-1176"]["statements"] == []
    assert rows["card-3876"]["statements"] == []
    assert rows[""]["statements"] == ["statements-1176-and-3876.pdf"]


# ── 3. the blast radius: the name is the LAST resort, never an override ──


def test_the_name_never_overrides_the_charges_a_file_printed(
    client, monkeypatch
):
    """A workbook prints its charges and they say 3876. The name says 1176,
    because Criss reused a filename. The charges win and the name is never
    consulted: the last resort only runs when both joins are silent, which
    is what keeps this change from moving any file that already lands."""
    _cards(client, **{
        **ONE_ELEVEN_SEVENTY_SIX,
        "card-3876": {"label": "Credit Card Chase Visa - 3876",
                      "digits": ["3876"], "entity": "Corporate Services"},
    })
    batch_id = _batch(client)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statements-1176-.xlsx",
            _xlsx([("2026-08-04", "AWS CLOUD", "Sale", -100.00, "3876")]),
            XLSX_MIME,
        )},
        data={**BARE_FORM, "map_transaction_date": "Date",
              "map_amount": "Amount", "map_vendor": "Description",
              "map_card": "Card"},
    ))

    rows = _coverage(client, batch_id)
    assert rows["card-3876"]["statements"] == ["statements-1176-.xlsx"]
    assert rows["card-1176"]["statements"] == []
