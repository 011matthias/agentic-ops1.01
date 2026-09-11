"""Month health (backlog item 57, 2026-09-11): readiness refuses a month
the matcher could not see.

August 2026 was uploaded on 2026-09-10 with every purchase printed
negative. The matcher saw 111 credits, proposed nothing, and the month
reported ``ready_to_post: true`` with 0 of 111 matched and 31 receipts in
the pool, four of them the same amount on the same day as a charge.
Nothing was undecided because nothing had been proposed.

Every test here goes through the routes: a workbook attached through
`POST .../statement`, the verdict read off `GET /api/runs/{id}` (the
workbench) and `GET /api/expense-batches/{id}` (the grid). The rule must
refuse readiness on the broken month, name the broken input, and get out
of the way once the month is repaired.
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

CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
CHASE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    (datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
NO_TYPE_HEADERS = ("Date", "Description", "Amount")
NO_TYPE_ROWS = [(d, v, a) for d, v, _t, a in CHASE_ROWS]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, date, currency="USD", payment_hint=None):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
    )


def _wire(monkeypatch, *extractions, fx_match=False):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=fx_match, same_purchase_confidence=0.9 if fx_match else 0.1,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="mock",
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


def _create_batch(client, n_receipts=1, label="August 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
        for i in range(n_receipts)
    ]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts", files=files,
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


def _attach_xlsx(
    client, batch_id, rows=CHASE_ROWS, headers=CHASE_HEADERS,
    entity="Corporate Services",
):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(rows, headers),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "%s"}' % entity,
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _attach_with_the_old_parser(client, batch_id):
    """The pre-2026-09-11 state through the REAL attach path: no Type
    column and the majority inference off, so every purchase arrives as a
    credit. This is August 2026 as it sat on the volume."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "expense_recon.ingest.statement_xlsx.infer_sign_flip",
            lambda amounts: False,
        )
        _attach_xlsx(client, batch_id, rows=NO_TYPE_ROWS, headers=NO_TYPE_HEADERS)


def _workbench(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── the defect as August showed it ──────────────────────────────────────


def test_a_zero_match_month_with_exact_pairs_is_not_ready(client, monkeypatch):
    """Three receipts, three charges, same amounts, same days, every charge
    a credit because the sign was never canonicalized. Before item 57 this
    month read ready_to_post: true with nothing undecided."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
        _extraction("Pressmaster FZCO", "135.00", "2026-08-23"),
    )
    batch_id = _create_batch(client, n_receipts=3)
    _attach_with_the_old_parser(client, batch_id)

    summary = _workbench(client, batch_id)["summary"]
    assert summary["n_reconciled"] == 0
    assert summary["n_undecided"] == 0, "the trap: nothing to decide"
    assert summary["ready_to_post"] is False
    health = summary["month_health"]
    assert health["checked"] is True
    assert health["state"] == "broken"
    assert health["reason"] == "zero_match_with_exact_pairs"
    assert health["n_exact_pairs"] == 3
    assert health["suspects"] == ["sign"]
    assert "sign" in health["detail"]


def test_the_grid_carries_the_same_verdict(client, monkeypatch):
    """Both review payloads say the month is broken; the SPA renders
    whichever one it is on."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)

    grid = _grid(client, batch_id)["summary"]["month_health"]
    bench = _workbench(client, batch_id)["summary"]["month_health"]
    assert grid == bench
    assert grid["state"] == "broken"


def test_the_reread_repair_clears_the_verdict(client, monkeypatch):
    """The fix path the operator has: re-read the stored workbook through
    the repaired parser. The month reconciles and readiness is the
    reviewer's decisions again."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)
    assert _workbench(client, batch_id)["summary"]["month_health"]["state"] == "broken"

    _done(client, client.post(f"/api/expense-batches/{batch_id}/statements/reread"))

    summary = _workbench(client, batch_id)["summary"]
    assert summary["n_reconciled"] == 1
    assert summary["month_health"]["state"] == "ok"
    assert summary["month_health"]["n_exact_pairs"] == 1
    assert summary["month_health"]["suspects"] == []
    # One matched row, not yet confirmed: the ordinary post gate.
    assert summary["n_undecided"] == 1
    assert summary["ready_to_post"] is False
    resp = client.post(f"/api/runs/{batch_id}/decisions/confirm-matched")
    assert resp.status_code == 200, resp.text
    assert resp.json()["summary"]["ready_to_post"] is True


# ── the other three inputs the rule can name ────────────────────────────


def test_a_named_other_entity_is_the_suspect(client, monkeypatch):
    """The receipt names Cloud Services, the card resolves to Corporate
    Services: the matcher never pairs across entities, so the month
    reconciles 0 and the verdict names the entity."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity",
        json={"legal_entity": "Cloud Services"},
    )
    assert resp.status_code == 200, resp.text
    _attach_xlsx(client, batch_id, entity="Corporate Services")

    health = _workbench(client, batch_id)["summary"]["month_health"]
    assert health["state"] == "broken"
    assert health["suspects"] == ["entity"]


def test_a_different_currency_is_the_suspect(client, monkeypatch):
    """Same number, different money: a EUR 15.00 receipt against a USD 15.00
    charge is not an exact match and the FX judgment says no."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31", currency="EUR"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    health = _workbench(client, batch_id)["summary"]["month_health"]
    assert health["state"] == "broken"
    assert health["suspects"] == ["currency"]


def test_a_receipt_naming_another_present_card_is_the_suspect(client, monkeypatch):
    """Card scoping: the receipt's payment mode names 3645, which is on the
    statement, while the charge is on 2838. The matcher drops the pair."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31", payment_hint="Visa ...3645"),
    )
    batch_id = _create_batch(client)
    rows = [
        ("2838", datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
        ("3645", datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    ]
    _attach_xlsx(client, batch_id, rows=rows, headers=("Card", "Date", "Description", "Type", "Amount"))

    health = _workbench(client, batch_id)["summary"]["month_health"]
    assert health["state"] == "broken", health
    assert health["suspects"] == ["card"]


# ── silence where it has nothing to say ─────────────────────────────────


def test_a_healthy_month_is_judged_by_decisions_alone(client, monkeypatch):
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    summary = _workbench(client, batch_id)["summary"]
    assert summary["n_reconciled"] == 1
    assert summary["month_health"] == {
        "checked": True, "state": "ok", "reason": None,
        "n_exact_pairs": 1, "suspects": [], "detail": None,
    }


def test_no_exact_pair_means_nothing_to_say(client, monkeypatch):
    """A month whose receipts simply do not match anything is not broken;
    the rule stays out of the reviewer's way."""
    _wire(monkeypatch, _extraction("Somewhere Else", "1.23", "2026-08-02"))
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)

    summary = _workbench(client, batch_id)["summary"]
    assert summary["n_reconciled"] == 0
    assert summary["month_health"]["state"] == "ok"
    assert summary["month_health"]["n_exact_pairs"] == 0
    assert summary["ready_to_post"] is True


def test_unchecked_before_a_statement(client, monkeypatch):
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    health = _grid(client, batch_id)["summary"]["month_health"]
    assert health["checked"] is False
    assert health["state"] == "ok"
