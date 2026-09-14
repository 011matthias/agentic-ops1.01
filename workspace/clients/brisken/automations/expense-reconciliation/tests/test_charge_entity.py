"""A charge's legal entity comes from its card (backlog item 59, owner
ruling 2026-09-11: blank for a card the registry cannot name).

August 2026 was uploaded as card-2838, so all 111 charges read Corporate
Services while 77 of them sat on cards 3645 and 3876, which the registry
does not know and the coverage panel already listed as "not in your card
list". A charge posted under the wrong company is worse than a charge
with no company: the first is silent, the second is a count on screen and
one card definition away from resolved.

Route-level: a multi-card workbook attached through `POST .../statement`,
the rows read off `GET /api/runs/{id}`, the card defined through
`PUT /api/settings` and folded in through the master-data refresh, the
re-read, and the hand-match guard.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

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

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CARD_HEADERS = ("Card", "Date", "Description", "Type", "Amount")
# Two cards on one Chase workbook: 2838 the registry knows, 3645 it does not.
CARD_ROWS = [
    ("2838", datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    ("3645", datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    ("3645", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
]
PLAIN_HEADERS = ("Date", "Description", "Type", "Amount")
PLAIN_ROWS = [(d, v, t, a) for _c, d, v, t, a in CARD_ROWS]

REGISTRY = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
        "entity": "Corporate Services",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, date, payment_hint=None):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
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


def _put_cards(client, cards):
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


def _create_batch(client, label="August 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": label},
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


def _attach_xlsx(client, batch_id, rows=CARD_ROWS, headers=CARD_HEADERS):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(rows, headers),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _entity_by_vendor(view) -> dict[str, str]:
    return {r["vendor"]: r["legal_entity_id"] for r in view["rows"]}


# ── the ruling ──────────────────────────────────────────────────────────


def test_a_charge_on_an_unknown_card_carries_no_entity(client, monkeypatch):
    """August's shape: filed under card-2838, rows on 2838 and 3645. The
    2838 rows resolve to the registry entity; the 3645 rows are blank, and
    the count on both payloads says how many."""
    _put_cards(client, REGISTRY)
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    view = _view(client, batch_id)
    assert _entity_by_vendor(view) == {
        "LOVABLE": "Corporate Services",
        "OBSIDIAN": "",
        "PRESSMASTER DMCC": "",
    }
    assert view["summary"]["n_charges_no_entity"] == 2
    assert _grid(client, batch_id)["summary"]["n_charges_no_entity"] == 2
    # The coverage panel says the same about the same plastic.
    by_label = {c["label"]: c for c in view["coverage"]}
    assert by_label["3645"]["entity"] == ""
    assert by_label["3645"]["known"] is False
    assert by_label["Corporate card (Chase)"]["entity"] == "Corporate Services"
    # Blank is unscoped: the entity-less receipt still pairs with its charge.
    assert view["summary"]["n_reconciled"] == 1


def test_defining_the_card_fills_the_entity_on_refresh(client, monkeypatch):
    """The fix is one card definition, not 77 row edits: define 3645 in
    Settings, refresh the month's master data, and every charge on it
    carries the card's entity; the snapshot keeps it."""
    _put_cards(client, REGISTRY)
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    assert _view(client, batch_id)["summary"]["n_charges_no_entity"] == 2

    _put_cards(client, {
        **REGISTRY,
        "cloud-3645": {
            "label": "Cloud card", "digits": ["3645"], "entity": "Cloud Services",
        },
    })
    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text

    view = _view(client, batch_id)
    assert _entity_by_vendor(view) == {
        "LOVABLE": "Corporate Services",
        "OBSIDIAN": "Cloud Services",
        "PRESSMASTER DMCC": "Cloud Services",
    }
    assert view["summary"]["n_charges_no_entity"] == 0


def test_a_known_card_without_an_entity_is_still_blank(client, monkeypatch):
    """A card the registry lists but has not assigned to a company gives
    the charge nothing: the gap is the card's entity, and the count keeps
    pointing at it."""
    _put_cards(client, {
        **REGISTRY,
        "cloud-3645": {"label": "Cloud card", "digits": ["3645"], "entity": ""},
    })
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    view = _view(client, batch_id)
    assert _entity_by_vendor(view)["OBSIDIAN"] == ""
    assert view["summary"]["n_charges_no_entity"] == 2


def test_a_workbook_without_a_card_column_keeps_the_upload_entity(client, monkeypatch):
    """No per-row card: the account id IS the card, and the upload's
    entity stands on every row exactly as before."""
    _put_cards(client, REGISTRY)
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id, rows=PLAIN_ROWS, headers=PLAIN_HEADERS)

    view = _view(client, batch_id)
    assert set(_entity_by_vendor(view).values()) == {"Corporate Services"}
    assert view["summary"]["n_charges_no_entity"] == 0


def test_the_reread_keeps_the_per_row_entity(client, monkeypatch):
    _put_cards(client, REGISTRY)
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    _done(client, client.post(f"/api/expense-batches/{batch_id}/statements/reread"))

    view = _view(client, batch_id)
    assert _entity_by_vendor(view)["OBSIDIAN"] == ""
    assert _entity_by_vendor(view)["LOVABLE"] == "Corporate Services"
    assert view["summary"]["n_transactions"] == 3


# ── the hand-match guard follows the matcher's rule ─────────────────────


def test_a_blank_entity_charge_can_be_hand_matched_to_a_named_receipt(client, monkeypatch):
    """A receipt that names Cloud Services against a charge on unknown card
    3645: the matcher treats a blank side as unscoped, and so must the
    manual match. Two NAMED entities that differ still refuse."""
    _put_cards(client, REGISTRY)
    ext = ExtractedReceipt(
        date="2026-08-30", total="96.00", currency="USD", vendor="Obsidian",
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )
    _wire(monkeypatch, ext)
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity",
        json={"legal_entity": "Cloud Services"},
    )
    assert resp.status_code == 200, resp.text
    _attach_xlsx(client, batch_id)

    view = _view(client, batch_id)
    obsidian = next(r for r in view["rows"] if r["vendor"] == "OBSIDIAN")
    assert obsidian["legal_entity_id"] == ""
    lovable = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    assert lovable["legal_entity_id"] == "Corporate Services"

    allowed = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": obsidian["transaction_id"], "document_id": doc},
    )
    assert allowed.status_code == 200, allowed.text

    refused = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": lovable["transaction_id"], "document_id": doc},
    )
    assert refused.status_code == 400
    assert "different legal entities" in refused.json()["error"]
