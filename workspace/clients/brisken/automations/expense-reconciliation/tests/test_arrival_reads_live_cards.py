"""Note #54 (owner, 2026-09-16) / audit item 108: a receipt arriving into a
month that already exists reads the card list as it is today.

"make sure if a month already exists, but a receipt is inserted through the
Receipts tab or through email, that the receipt goes through the entire
process all the other receipts inside the month have gone through."

Categorization, memory and the re-match against a loaded statement already
ran on arrivals. The card chain did not: each month kept the copy of the
card registry it was created with, so September (opened by mail on 7 Sept,
before the cards had people and companies) resolved every later arrival
against that copy and showed 40 rows with no person.

Route-level (B2, through the caller): the add route, then the grid.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
_SEQ = [0]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-09-03", total="42.50", currency="USD",
                vendor="Regus", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint="Visa ...3645")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _mock(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _add(client, batch, monkeypatch, *extractions):
    _mock(monkeypatch, *extractions)
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"r{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 3]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _month(client, monkeypatch) -> str:
    _mock(monkeypatch)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "September 2026"})
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _rows(client, batch) -> list[dict]:
    resp = client.get(f"/api/expense-batches/{batch}")
    assert resp.status_code == 200, resp.text
    return sorted(resp.json()["expenses"], key=lambda e: e["vendor"]["raw"])


def _cards(person: str = "", entity: str = "") -> dict:
    entry = {"label": "Corp 3645", "digits": ["3645"]}
    if person:
        entry["person"] = person
    if entity:
        entry["entity"] = entity
    return {"cards": {"corp-3645": entry}}


def test_an_arrival_reads_the_card_list_as_it_is_today(client, monkeypatch):
    # The month is created while the card has no person and no company.
    client.put("/api/settings", json=_cards())
    september = _month(client, monkeypatch)
    _add(client, september, monkeypatch, _extraction(vendor="Regus"))
    [first] = _rows(client, september)
    assert first["card"]["key"] == "corp-3645"
    assert first["person"] == "" and first["legal_entity_id"] == ""

    # Settings learns who the card belongs to; nobody presses refresh.
    client.put("/api/settings", json=_cards("Dirk Neumann", "Corporate Services"))

    # The next receipt arrives. It, and the row already there, read today's list.
    _add(client, september, monkeypatch, _extraction(vendor="Uber", total="30.00"))
    rows = _rows(client, september)
    assert [r["vendor"]["raw"] for r in rows] == ["Regus", "Uber"]
    for row in rows:
        assert row["person"] == "Dirk Neumann", row["vendor"]
        assert row["legal_entity_id"] == "Corporate Services", row["vendor"]


def test_the_refresh_is_on_the_months_audit_trail(client, monkeypatch):
    client.put("/api/settings", json=_cards())
    september = _month(client, monkeypatch)
    _add(client, september, monkeypatch, _extraction(vendor="Regus"))
    client.put("/api/settings", json=_cards("Dirk Neumann"))
    _add(client, september, monkeypatch, _extraction(vendor="Uber", total="30.00"))

    with RunStore(client._data_root / "recon-web.sqlite") as db:
        audit = db.get_run(september).snapshot["master_data_refreshes"]
    (entry,) = [a for a in audit if a["operator"] == "auto: receipt arrival"]
    fields = {c["field"] for c in entry["changes"]}
    assert "cards" in fields
    assert {"field": "row_persons", "n_rows_changed": 1} in entry["changes"]


def test_an_arrival_with_nothing_new_in_settings_writes_no_audit_row(client, monkeypatch):
    client.put("/api/settings", json=_cards("Dirk Neumann", "Corporate Services"))
    september = _month(client, monkeypatch)
    _add(client, september, monkeypatch, _extraction(vendor="Regus"))
    _add(client, september, monkeypatch, _extraction(vendor="Uber", total="30.00"))
    assert all(r["person"] == "Dirk Neumann" for r in _rows(client, september))
    with RunStore(client._data_root / "recon-web.sqlite") as db:
        audit = db.get_run(september).snapshot.get("master_data_refreshes") or []
    assert audit == []
