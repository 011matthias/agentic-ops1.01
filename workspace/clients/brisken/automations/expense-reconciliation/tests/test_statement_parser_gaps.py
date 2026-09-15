"""The two parser gaps of backlog item 64, exercised through the routes.

**(a) An unrecognised Type label used to flip the row's sign.** Both parsers
canonicalized on the export's debit/credit column: a label `is_credit_type`
claimed became a credit, and ANYTHING ELSE was read as a purchase and abs'd.
"Anything else" includes every label the vocabulary does not carry, so a
German export's "Lastschrift" (direct debit) and "Gutschrift" (credit note)
both came out positive purchases and the month's credits vanished into the
charges. An unknown label is not evidence of direction; the printed sign now
stands, and each distinct unknown label is reported once with its row count.

**(b) `statements[]` did not record HOW an upload was read.** The re-read
rebuilds a month from the files it holds, and recovered each file's column
map from `config.statement`, which only ever describes the LATEST upload. So
on a month holding two statements the earlier one was re-guessed (losing the
operator's manual column picks, or failing outright on headers the guess
cannot name), and every file was re-read at the last upload's card currency.
Each entry now carries the map and the currency it was read with.

Live evidence, 2026-09-15: both live months (August `074a7b8905d7`, July
`50622baec444`) hold exactly ONE statement each, whose `file` still matches
`config.statement.path`, and their workbooks carry only `Sale`, `Payment`
and one `Fee`. Neither gap bites either month today. Both fixtures are
therefore constructed, per the parallel-round protocol §3.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.ingest.statement_csv import (  # noqa: E402
    parse_statement_csv_tolerant,
)
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# A German card export: purchases printed negative under "Lastschrift", the
# refund positive under "Gutschrift", neither label in the vocabulary.
DE_HEADERS = ("Date", "Description", "Type", "Amount")
DE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Lastschrift", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Lastschrift", -96.00),
    (datetime(2026, 8, 23), "PRESSMASTER DMCC", "Lastschrift", -135.00),
    (datetime(2026, 8, 4), "AMAZON RETURN", "Gutschrift", 40.00),
]

# Headers no auto-detect can name, so the map can only come from the
# operator's picks at attach time or from what the entry recorded.
OPAQUE_HEADERS = ("F1", "F2", "F3")
OPAQUE_ROWS = [
    (datetime(2026, 7, 14), "HETZNER", 61.00),
    (datetime(2026, 7, 21), "FIGMA", 45.00),
]
OPAQUE_MAP = {
    "map_transaction_date": "F1",
    "map_vendor": "F2",
    "map_amount": "F3",
}

PLAIN_HEADERS = ("Date", "Description", "Amount")
PLAIN_ROWS = [(datetime(2026, 7, 9), "SUPABASE", 92.70)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, date, currency="USD"):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create_batch(client, label="August 2026"):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _xlsx_bytes(rows, headers) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(
    client, batch_id, rows, headers, name="August2026.xlsx",
    currency="USD", extra=None,
):
    data = {
        "account_id": "card-2838",
        "account_legal_entities": '{"card-2838": "Corporate Services"}',
        "account_card_currency": currency,
    }
    data.update(extra or {})
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            name, _xlsx_bytes(rows, headers),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data=data,
    )
    return _done(client, resp)


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _reread(client, batch_id):
    resp = client.post(f"/api/expense-batches/{batch_id}/statements/reread")
    assert resp.status_code == 200, resp.text
    return client.get(f"/jobs/{resp.json()['job_id']}").json()


def _stored_transactions(client, batch_id) -> list[dict]:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        return list((run.snapshot or {}).get("transactions") or [])


def _amount(row: dict) -> Decimal:
    return Decimal(str(row["amount"]).replace(",", ""))


# ── (a) an unrecognised Type label keeps the printed sign ────────────────


def test_german_labels_keep_their_printed_signs_through_the_attach(
    client, monkeypatch
):
    """The defect as a German export would have hit it: three negative
    "Lastschrift" purchases and one positive "Gutschrift" refund. Pre-fix
    every row was abs'd to a purchase, so the refund joined the charges and
    the month's one credit disappeared. Post-fix the printed signs stand:
    the refund is the credit, the purchases are purchases."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach(client, batch_id, DE_ROWS, DE_HEADERS)

    view = _view(client, batch_id)
    # A negative amount is this parser's canonical credit. The Gutschrift
    # printed positive, so keeping its sign makes it a purchase, and the
    # three Lastschrift rows printed negative, so they stay credits. The
    # point is not which bucket each lands in: it is that the parser no
    # longer overrides a sign on the strength of a label it cannot read.
    by_vendor = {r["vendor"]: r for r in view["rows"]}
    by_vendor.update({
        t["vendor_from_statement"]: t for t in _stored_transactions(client, batch_id)
    })
    assert _amount(by_vendor["LOVABLE"]) == Decimal("-15.00")
    assert _amount(by_vendor["OBSIDIAN"]) == Decimal("-96.00")
    assert _amount(by_vendor["AMAZON RETURN"]) == Decimal("40.00")

    notes = [
        i for i in view["parse_issues"]
        if isinstance(i, dict) and i.get("severity") == "info"
    ]
    messages = " ".join(n["message"] for n in notes)
    assert len(notes) == 2, notes
    assert "'Lastschrift'" in messages and "3 rows" in messages
    assert "'Gutschrift'" in messages and "1 row" in messages
    assert all(n["line"] == 0 for n in notes), notes


def test_a_known_label_is_still_canonicalized(client, monkeypatch):
    """The guard on the fix: `Sale` and `Payment` are recognised, so their
    signs are still overwritten. Both live months are 109-111 negative
    `Sale` rows; reading those as credits would break every month in the
    system, which is why "unrecognised" had to mean "in neither vocabulary"
    rather than "not a credit"."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach(client, batch_id, [
        (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
        (datetime(2026, 8, 4), "Payment Thank You", "Payment", 7823.16),
        (datetime(2026, 8, 6), "ANNUAL MEMBERSHIP FEE", "Fee", -95.00),
    ], DE_HEADERS)

    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 1
    lovable = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    assert _amount(lovable) == Decimal("15.00")
    fee = next(r for r in view["rows"] if r["vendor"] == "ANNUAL MEMBERSHIP FEE")
    assert _amount(fee) == Decimal("95.00")
    assert not [
        i for i in view["parse_issues"]
        if isinstance(i, dict) and i.get("severity") == "info"
    ]


def test_one_note_per_distinct_label_not_per_row(tmp_path):
    """At the parser, where the row counts are cheap to state: forty rows
    of one unknown label are one note that says forty, and a Type column
    mapped onto a description column reports as a capped summary rather
    than five hundred notes."""
    rows = "\n".join(
        f"08/{i % 28 + 1:02d}/2026,VENDOR {i},-{i}.00,Lastschrift"
        for i in range(1, 41)
    )
    src = tmp_path / "de.csv"
    src.write_text(
        f"Date,Description,Amount,Type\n{rows}\n", encoding="utf-8"
    )
    _, issues = parse_statement_csv_tolerant(
        src,
        column_map={
            "transaction_date": "Date", "vendor": "Description",
            "amount": "Amount", "type": "Type",
        },
        account_id="x", legal_entity_id="x", account_card_currency="EUR",
    )
    notes = [i for i in issues if i.severity == "info"]
    assert len(notes) == 1
    assert "'Lastschrift'" in notes[0].message and "40 rows" in notes[0].message

    mismapped = "\n".join(
        f"08/{i % 28 + 1:02d}/2026,VENDOR {i},-{i}.00,DESCRIPTION {i}"
        for i in range(1, 41)
    )
    src2 = tmp_path / "mismapped.csv"
    src2.write_text(
        f"Date,Description,Amount,Type\n{mismapped}\n", encoding="utf-8"
    )
    _, issues2 = parse_statement_csv_tolerant(
        src2,
        column_map={
            "transaction_date": "Date", "vendor": "Description",
            "amount": "Amount", "type": "Type",
        },
        account_id="x", legal_entity_id="x", account_card_currency="EUR",
    )
    notes2 = [i for i in issues2 if i.severity == "info"]
    assert len(notes2) == 11, [n.message for n in notes2]
    assert "30 further Type labels" in notes2[-1].message


# ── (b) the entry records the map and the currency it was read with ──────


def test_statements_entry_records_its_map_and_currency(client, monkeypatch):
    """Through the attach route and GET /api/runs/{id}: the entry carries
    the map the parser was handed, including the operator's manual picks,
    and the card currency the upload declared."""
    _wire(monkeypatch, _extraction("Hetzner", "61.00", "2026-07-14"))
    batch_id = _create_batch(client, label="July 2026")
    _attach(
        client, batch_id, OPAQUE_ROWS, OPAQUE_HEADERS,
        name="July2026.xlsx", currency="eur", extra=OPAQUE_MAP,
    )

    entry = _view(client, batch_id)["statements"][0]
    assert entry["column_map"] == {
        "transaction_date": "F1", "vendor": "F2", "amount": "F3",
    }
    assert entry["card_currency"] == "EUR"


def test_reread_reuses_the_recorded_map_of_an_earlier_upload(
    client, monkeypatch
):
    """The gap, at the caller that had it. A month takes two statements;
    the first has headers no auto-detect can name and was attached with the
    operator's picks. `config.statement` now describes the SECOND upload, so
    the re-read used to re-guess the first and refuse the whole month with
    "Could not auto-detect these required statement columns". With the map
    recorded on the entry the re-read succeeds and both files' charges come
    back."""
    _wire(
        monkeypatch,
        _extraction("Hetzner", "61.00", "2026-07-14"),
        _extraction("Supabase", "92.70", "2026-07-09"),
    )
    batch_id = _create_batch(client, label="July 2026")
    _attach(
        client, batch_id, OPAQUE_ROWS, OPAQUE_HEADERS,
        name="July2026.xlsx", extra=OPAQUE_MAP,
    )
    _attach(
        client, batch_id, PLAIN_ROWS, PLAIN_HEADERS, name="July2026-b.xlsx",
    )
    before = {t["vendor_from_statement"] for t in _stored_transactions(client, batch_id)}
    assert before == {"HETZNER", "FIGMA", "SUPABASE"}

    job = _reread(client, batch_id)
    assert job["status"] == "done", job

    after = {t["vendor_from_statement"] for t in _stored_transactions(client, batch_id)}
    assert after == before
    entries = _view(client, batch_id)["statements"]
    assert len(entries) == 2
    assert entries[0]["column_map"]["transaction_date"] == "F1"


def test_reread_keeps_each_uploads_own_card_currency(client, monkeypatch):
    """The other half, and the one that fails silently rather than loudly.
    A month holding a EUR card statement and a USD one re-read every file at
    whichever currency arrived last, because that is what
    `config.statement` holds. A charge whose currency moved stops matching
    its receipt, and nothing reports it."""
    _wire(
        monkeypatch,
        _extraction("Hetzner", "61.00", "2026-07-14", currency="EUR"),
        _extraction("Supabase", "92.70", "2026-07-09"),
    )
    batch_id = _create_batch(client, label="July 2026")
    _attach(
        client, batch_id, OPAQUE_ROWS, OPAQUE_HEADERS, name="July2026.xlsx",
        currency="EUR", extra=OPAQUE_MAP,
    )
    _attach(
        client, batch_id, PLAIN_ROWS, PLAIN_HEADERS, name="July2026-b.xlsx",
        currency="USD",
    )

    def currencies():
        return {
            t["vendor_from_statement"]: t["transaction_currency"]
            for t in _stored_transactions(client, batch_id)
        }

    assert currencies() == {
        "HETZNER": "EUR", "FIGMA": "EUR", "SUPABASE": "USD",
    }

    job = _reread(client, batch_id)
    assert job["status"] == "done", job
    assert currencies() == {
        "HETZNER": "EUR", "FIGMA": "EUR", "SUPABASE": "USD",
    }


def test_an_entry_recorded_before_item_64_still_rereads(client, monkeypatch):
    """Backward compatibility, stated as a test rather than as a comment: a
    single-statement month whose entry predates both fields (the shape both
    live months are in right now) still re-reads, through the
    `config.statement` fallback."""
    _wire(monkeypatch, _extraction("Supabase", "92.70", "2026-07-09"))
    batch_id = _create_batch(client, label="July 2026")
    _attach(
        client, batch_id, PLAIN_ROWS, PLAIN_HEADERS, name="July2026.xlsx",
    )

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot or {})
        entries = [dict(e) for e in snapshot.get("statements") or []]
        for entry in entries:
            entry.pop("column_map", None)
            entry.pop("card_currency", None)
        snapshot["statements"] = entries
        store.update_run_snapshot(batch_id, snapshot)

    view = _view(client, batch_id)
    assert "column_map" not in view["statements"][0]
    assert "card_currency" not in view["statements"][0]

    job = _reread(client, batch_id)
    assert job["status"] == "done", job
    entry = _view(client, batch_id)["statements"][0]
    assert entry["column_map"]["vendor"] == "Description"
    assert entry["card_currency"] == "USD"
