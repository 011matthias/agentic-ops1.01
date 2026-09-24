"""Item 195: a statement re-read must not re-stamp a PDF's charges with the
entity "card".

A Chase statement PDF takes its charges' legal entity from the caller, one
company per file, and its rows print no `card_last4`, so the match-time
stamp (`stamp_charge_entities`, item 59) never repairs them. The attach
resolves that entity from the account id the SPA sends (the chosen card's
key), but the PDF's config block has no `account_id` key, so the upload's
`statements[]` entry recorded `""`. A re-read then resolved the entity from
nothing, and `RunForm.resolve_legal_entity` turned nothing into the raw
fallback `"card"`: a named entity no receipt carries. Worse, a PDF entry
with no recorded account borrowed `config.statement`'s, which describes
whatever file arrived LAST, so a PDF sitting under a later workbook re-read
under the workbook's company.

Live shape (2026-09-25, August `074a7b8905d7`): two PDF entries,
`20260804-statements-1176-.pdf` (3 charges, Consulting) and
`20260804-statements-9693--2.pdf` (21 charges, Cloud Services), both
recorded with `account_id: ""`, beside `August2026.xlsx` on `card-2838`.
The same empty account made the second PDF's advisory claim both files were
"on the same account".

Everything here runs through the FastAPI app except the advisory check,
which is the pure function the commit calls.
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import statement_advisory  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

REGISTRY = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838"],
        "entity": "Corporate Services",
    },
    "consulting-1176": {
        "label": "Consulting card (Chase)",
        "digits": ["1176"],
        "entity": "Consulting",
    },
    "cloud-9693": {
        "label": "Cloud card (Chase)",
        "digits": ["9693"],
        "entity": "Cloud Services",
    },
}

# One cycle on card 1176, the live 1176 file's shape.
PDF_1176 = """\
Opening/Closing Date 07/06/26 - 08/04/26
ACCOUNT ACTIVITY
07/10 AWS CLOUD SERVICES 100.00
07/12 GITHUB INC 21.00
TRANSACTIONS THIS CYCLE (CARD 1176) $121.00
"""

# Two cycles in one file, on cards the registry files under two companies.
PDF_TWO_COMPANIES = """\
Opening/Closing Date 07/06/26 - 08/04/26
ACCOUNT ACTIVITY
07/10 AWS CLOUD SERVICES 100.00
TRANSACTIONS THIS CYCLE (CARD 1176) $100.00
07/14 OPENAI CHATGPT 20.00
TRANSACTIONS THIS CYCLE (CARD 9693) $20.00
"""

# The other card over an overlapping cycle, the live 9693 file's shape.
PDF_9693 = """\
Opening/Closing Date 07/03/26 - 08/04/26
ACCOUNT ACTIVITY
07/11 OPENAI CHATGPT 20.00
07/14 ANTHROPIC CLAUDE 18.00
TRANSACTIONS THIS CYCLE (CARD 9693) $38.00
"""

XLSX_HEADERS = ("Date", "Description", "Type", "Amount")
XLSX_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-08-30", total="96.00", currency="USD", vendor="Obsidian",
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


def _put_cards(client, cards):
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


def _create_batch(client, label="August 2026") -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("obsidian.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _pdf_text(monkeypatch, text: str) -> None:
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [text],
    )


def _attach_pdf(client, batch_id, *, account_id: str, name="chase.pdf"):
    # What the SPA sends: the chosen card's key as `account_id`, and no
    # `account_legal_entities` at all (AttachStatementDialog.tsx).
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, b"%PDF-1.4 synthetic " + name.encode(),
                             "application/pdf")},
        data={"account_id": account_id, "account_card_currency": "USD"},
    ))


def _attach_xlsx(client, batch_id):
    wb = Workbook()
    ws = wb.active
    ws.append(list(XLSX_HEADERS))
    for row in XLSX_ROWS:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={"account_id": "card-2838", "account_card_currency": "USD"},
    ))


def _reread(client, batch_id):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statements/reread"
    ))


def _run(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _entities(view: dict, account_id: str) -> set[str]:
    return {
        r.get("legal_entity_id") or ""
        for r in view["rows"] if r["account_id"] == account_id
    }


def _age_entry(client, batch_id, file_name: str) -> None:
    """Rewrite one `statements[]` entry the way the live PDF entries were
    written: account recorded as empty."""
    path = Path(client._data_root) / "recon-web.sqlite"
    with RunStore(path) as store:
        run = store.get_run(batch_id)
        snap = dict(run.snapshot)
        snap["statements"] = [
            {**e, "account_id": ""} if e["file"] == file_name else e
            for e in snap["statements"]
        ]
        store.update_run_snapshot(batch_id, snap)


# ── the re-read keeps the company the upload was filed under ─────────────


def test_a_reread_keeps_the_entity_a_pdf_was_attached_under(client, monkeypatch):
    _put_cards(client, REGISTRY)
    _pdf_text(monkeypatch, PDF_1176)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="consulting-1176")
    assert _entities(_run(client, batch_id), "1176") == {"Consulting"}

    _reread(client, batch_id)

    assert _entities(_run(client, batch_id), "1176") == {"Consulting"}


def test_a_pdf_entry_records_the_account_it_was_filed_under(client, monkeypatch):
    """The account the SPA sent is what the entity was resolved from, so it
    is what a re-read needs, and what tells two card PDFs apart."""
    _put_cards(client, REGISTRY)
    _pdf_text(monkeypatch, PDF_1176)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="consulting-1176")

    (entry,) = _run(client, batch_id)["statements"]
    assert entry["account_id"] == "consulting-1176"

    _reread(client, batch_id)
    (entry,) = _run(client, batch_id)["statements"]
    assert entry["account_id"] == "consulting-1176"


def test_a_pdf_recorded_without_its_account_rereads_under_its_printed_card(
    client, monkeypatch
):
    """August's shape: the PDF entry says nothing about its account and a
    workbook on another company's card arrived after it, so
    `config.statement` describes the workbook. The PDF must not borrow that
    account; its own cycle marker names its card."""
    _put_cards(client, REGISTRY)
    _pdf_text(monkeypatch, PDF_1176)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="consulting-1176")
    _attach_xlsx(client, batch_id)
    _age_entry(client, batch_id, "chase.pdf")

    _reread(client, batch_id)

    view = _run(client, batch_id)
    assert _entities(view, "1176") == {"Consulting"}
    assert _entities(view, "card-2838") == {"Corporate Services"}


def test_a_pdf_filed_with_no_account_takes_the_company_its_card_prints(
    client, monkeypatch
):
    """An attach with the account field left empty (the SPA's typed-id path
    allows it). "card" is not a company; the cycle marker names one."""
    _put_cards(client, REGISTRY)
    _pdf_text(monkeypatch, PDF_1176)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="")

    assert _entities(_run(client, batch_id), "1176") == {"Consulting"}
    _reread(client, batch_id)
    assert _entities(_run(client, batch_id), "1176") == {"Consulting"}


def test_a_pdf_whose_card_the_registry_cannot_name_carries_no_entity(
    client, monkeypatch
):
    """Item 59's rule on the PDF side: a visible gap beats a made-up
    company. Blank is counted as a charge without a company."""
    _pdf_text(monkeypatch, PDF_1176)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="")

    view = _run(client, batch_id)
    assert _entities(view, "1176") == {""}
    assert view["summary"]["n_charges_no_entity"] == 2


def test_a_pdf_printing_two_companies_cards_carries_no_entity(
    client, monkeypatch
):
    """One company per statement is the parser's contract. When the cards a
    file prints belong to two companies and nobody said which one the file
    is for, neither is picked."""
    _put_cards(client, REGISTRY)
    _pdf_text(monkeypatch, PDF_TWO_COMPANIES)
    batch_id = _create_batch(client)
    _attach_pdf(client, batch_id, account_id="")

    view = _run(client, batch_id)
    assert _entities(view, "1176") == {""}
    assert _entities(view, "9693") == {""}


# ── the advisory ────────────────────────────────────────────────────────


def _entry(file_name: str, account_id: str) -> dict:
    return {
        "file": file_name, "card_key": "", "account_id": account_id,
        "period_start": "2026-07-06", "period_end": "2026-08-04",
        "n_rows": 21, "n_new": 21,
    }


def test_two_uploads_with_no_recorded_account_are_not_the_same_account():
    """The live 9693 advisory said the 1176 file covered its period "on the
    same account". Nothing recorded on either side is an unknown, not a
    match."""
    prior = [_entry("20260804-statements-1176-.pdf", "")]
    assert statement_advisory(
        prior, _entry("20260804-statements-9693--2.pdf", "")
    ) is None


def test_the_same_recorded_account_over_one_period_still_advises():
    prior = [_entry("partial.pdf", "cloud-9693")]
    advisory = statement_advisory(prior, _entry("full.pdf", "cloud-9693"))
    assert advisory is not None
    assert advisory.code == "statement_period_overlap"


def test_two_card_pdfs_attached_through_the_spa_do_not_advise(
    client, monkeypatch
):
    _put_cards(client, REGISTRY)
    batch_id = _create_batch(client)
    _pdf_text(monkeypatch, PDF_1176)
    _attach_pdf(client, batch_id, account_id="consulting-1176",
                name="20260804-statements-1176-.pdf")
    _pdf_text(monkeypatch, PDF_9693)
    _attach_pdf(client, batch_id, account_id="cloud-9693",
                name="20260804-statements-9693-.pdf")

    entries = _run(client, batch_id)["statements"]
    # The two cycles overlap (07-10..07-12 inside 07-11..07-14), so only the
    # accounts tell the files apart.
    assert entries[1]["period_start"] <= entries[0]["period_end"]
    assert [e["advisory"] for e in entries] == [None, None]
