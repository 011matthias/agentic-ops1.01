"""Backlog items 36 + 37 (2026-08-29 round).

Item 36: the expense-batch view exposes `period_suggestion` — the
dates-plurality month the receipts collectively read as — so the SPA can
OFFER a rename instead of the operator having to notice a mismatch. The
label stays the only authority; the field is null whenever
`month_from_dates` finds no consensus (fewer than 4 dated expenses, or no
clear winner).

Item 37: the statement-attach route accepts the column-mapping keys the
DEPLOYED SPA actually sends on its retry (`map_date`, `map_description`,
`map_currency`); those were silently dropped by FastAPI, so the
operator's column picks never reached the parser. Canonical names win on
conflict.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(date, vendor="Staples", total="42.50"):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_batch(client, label, n_files):
    # Distinct bytes per file: the intake dedupes on content digest.
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
        for i in range(n_files)
    ]
    resp = client.post(
        "/api/expense-batches",
        files=files,
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── item 36: period_suggestion ──────────────────────────────────────


def test_period_suggestion_consensus_and_label_month(client, monkeypatch):
    """Five April receipts under a month-less label suggest 2026-04 with
    label_month null; renaming the batch to name the month fills it."""
    _wire(monkeypatch, *[
        _extraction(f"2026-04-{d:02d}") for d in (3, 7, 11, 19, 25)
    ])
    batch_id = _create_batch(client, "TEST pipeline batch", 5)

    sugg = _grid(client, batch_id)["period_suggestion"]
    assert sugg == {
        "month": "2026-04",
        "label_month": None,
        "n_dates": 5,
        "n_in_month": 5,
    }

    resp = client.post(
        f"/api/runs/{batch_id}/rename", json={"label": "April 2026"}
    )
    assert resp.status_code == 200, resp.text
    sugg = _grid(client, batch_id)["period_suggestion"]
    assert sugg["month"] == "2026-04"
    assert sugg["label_month"] == "2026-04"


def test_period_suggestion_null_below_consensus_floor(client, monkeypatch):
    """Three dated receipts are below the 4-date floor: null, never a
    guess (a guessed month would put good rows under suspicion)."""
    _wire(monkeypatch, *[
        _extraction(f"2026-04-{d:02d}") for d in (3, 7, 11)
    ])
    batch_id = _create_batch(client, "TEST tiny batch", 3)
    assert _grid(client, batch_id)["period_suggestion"] is None


def test_period_suggestion_plurality_over_mixed_months(client, monkeypatch):
    """Five April + two August receipts: April wins the plurality and the
    counts say how contested it was."""
    dates = [f"2026-04-{d:02d}" for d in (3, 7, 11, 19, 25)]
    dates += ["2026-08-02", "2026-08-14"]
    _wire(monkeypatch, *[_extraction(d) for d in dates])
    batch_id = _create_batch(client, "TEST mixed batch", 7)

    sugg = _grid(client, batch_id)["period_suggestion"]
    assert sugg == {
        "month": "2026-04",
        "label_month": None,
        "n_dates": 7,
        "n_in_month": 5,
    }


# ── item 37: the SPA's alias map keys ───────────────────────────────

CSV_ODD_HEADERS = (
    "When,Who,How Much,Ccy\n"
    "2026-04-07,ACME STORE,12.34,USD\n"
    "2026-04-09,BETA MART,56.78,USD\n"
)


def _attach_with(client, batch_id, data):
    return client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("odd.csv", CSV_ODD_HEADERS.encode(), "text/csv")},
        data={
            "account_id": "amex-9001",
            "account_card_currency": "USD",
            **data,
        },
    )


def _snapshot_transactions(client, batch_id):
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {}).get("transactions") or []


def test_attach_accepts_the_spa_alias_map_keys(client, monkeypatch):
    """The deployed SPA retry sends map_date / map_description /
    map_currency. Pre-fix those were silently dropped and this POST
    came back 400 with the file's headers."""
    _wire(monkeypatch, _extraction("2026-04-07", vendor="ACME STORE",
                                   total="12.34"))
    batch_id = _create_batch(client, "April 2026", 1)

    resp = _attach_with(client, batch_id, {
        "map_date": "When",
        "map_description": "Who",
        "map_amount": "How Much",
        "map_currency": "Ccy",
    })
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    txs = _snapshot_transactions(client, batch_id)
    assert len(txs) == 2
    dump = json.dumps(txs)
    assert "ACME STORE" in dump and "BETA MART" in dump
    assert "2026-04-09" in dump


def test_canonical_map_names_win_over_aliases(client, monkeypatch):
    """Both spellings sent: the canonical name decides. 'Wrong' as the
    alias value must not shadow the real date column."""
    _wire(monkeypatch, _extraction("2026-04-07", vendor="ACME STORE",
                                   total="12.34"))
    batch_id = _create_batch(client, "April 2026", 1)

    resp = _attach_with(client, batch_id, {
        "map_transaction_date": "When",
        "map_date": "Ccy",
        "map_description": "Who",
        "map_amount": "How Much",
    })
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    dump = json.dumps(_snapshot_transactions(client, batch_id))
    assert "2026-04-07" in dump and "2026-04-09" in dump
