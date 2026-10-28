"""Item 163: a memory save says what it will do, where it went, and undoes.

Feedback note #81 (owner, 2026-09-23) on the "Save corrections to memory"
button: "based on what? this should be reversible for now, and state
explicitly where these are saved so user can manage this". Route-level
through the FastAPI app, so every test runs through the caller the fix
changed rather than through the helpers it added:

* the plan lists the writes a save would make, and writes nothing;
* the plan and the save agree, key for key (the preview cannot lie);
* the save is recorded with which month taught it and what it learned;
* the undo puts a changed row back to its previous value;
* the undo deletes a row the save created;
* the undo restores the merchant registry the save grew;
* after an undo the next publish teaches the corrections again;
* an undone save cannot be undone twice, and an older save cannot jump
  the queue.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor: str = "Staples") -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-07-01", total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _patch_ocr(monkeypatch, vendor: str = "Staples") -> None:
    mock = MockLLMClient(extraction_responses=[_extraction(vendor)])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _create_batch(client, monkeypatch, name="a.jpg", data=JPG, vendor="Staples") -> str:
    _patch_ocr(monkeypatch, vendor)
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "Corporate Services"}
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _doc(client, batch_id) -> str:
    return client.get(
        f"/api/expense-batches/{batch_id}"
    ).json()["expenses"][0]["document_id"]


def _edit(client, batch_id, doc, field, value) -> None:
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": field, "value": value}
    )
    assert resp.status_code == 200, resp.text


def _save(client, batch_id) -> dict:
    resp = client.post(f"/api/runs/{batch_id}/commit-memory")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _plan(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}/memory-plan")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _corrections(client) -> dict[str, str]:
    memory = client.get("/api/memory").json()
    return {c["field"]: (c["value"] if "value" in c else c["field"])
            for c in memory["field_corrections"]}


def _correction_rows(client) -> list[dict]:
    return client.get("/api/memory").json()["field_corrections"]


def _commits(client) -> list[dict]:
    resp = client.get("/api/memory/commits")
    assert resp.status_code == 200, resp.text
    return resp.json()["commits"]


def _undo(client, journal_id: int):
    return client.post(f"/api/memory/commits/{journal_id}/undo")


def test_the_plan_lists_the_writes_and_writes_nothing(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    # The vendor edit is what makes the registry half of the plan non-empty,
    # so "writes nothing" is asserted over a plan that HAS something to write
    # on both sides. Without it the registry assertion below passes vacuously.
    _edit(client, batch, doc, "vendor", "Staples Incorporated")
    merchants_before = client.get("/api/settings").json()["merchants"]

    plan = _plan(client, batch)
    assert plan["registry"], "the plan found nothing to change in the registry"
    assert client.get("/api/settings").json()["merchants"] == merchants_before, \
        "the preview changed the merchant registry"
    tables = {w["table"] for w in plan["writes"]}
    assert "field_correction" in tables
    paid = [w for w in plan["writes"] if w["key"].get("field") == "paid_through"]
    assert paid, plan["writes"]
    assert paid[0]["value"] == "1010 Chase"
    assert paid[0]["surface"] == "memory"
    assert paid[0]["key"]["vendor_norm"]

    assert _correction_rows(client) == [], "the preview wrote to the store"
    assert _commits(client) == [], "the preview recorded a save"


def test_the_plan_and_the_save_agree_key_for_key(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    _edit(client, batch, doc, "legal_entity", "Cloud Services")

    planned = {
        (w["table"], tuple(sorted(w["key"].items()))) for w in _plan(client, batch)["writes"]
    }
    _save(client, batch)
    written = {
        (r["table"], tuple(sorted(r["key"].items()))) for r in _commits(client)[0]["rows"]
    }
    assert planned == written


def test_a_save_is_recorded_with_its_month_and_what_it_taught(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")

    body = _save(client, batch)
    assert isinstance(body["journal_id"], int)

    entry = _commits(client)[0]
    assert entry["id"] == body["journal_id"]
    assert entry["run_id"] == batch
    assert entry["trigger"] == "button"
    assert entry["reverted_at"] == ""
    assert entry["learned"]["field_corrections"] >= 1
    assert all(r["surface"] == "memory" for r in entry["rows"])


def test_the_undo_puts_a_changed_row_back(client, monkeypatch):
    batch1 = _create_batch(client, monkeypatch)
    _edit(client, batch1, _doc(client, batch1), "paid_through", "1010 Chase")
    _save(client, batch1)
    assert [r["value"] for r in _correction_rows(client)
            if r["field"] == "paid_through"] == ["1010 Chase"]

    batch2 = _create_batch(client, monkeypatch, name="b.jpg", data=JPG + b"x")
    _edit(client, batch2, _doc(client, batch2), "paid_through", "2020 Amex")
    second = _save(client, batch2)["journal_id"]
    assert [r["value"] for r in _correction_rows(client)
            if r["field"] == "paid_through"] == ["2020 Amex"]

    resp = _undo(client, second)
    assert resp.status_code == 200, resp.text
    assert resp.json()["undone"] is True
    assert [r["value"] for r in _correction_rows(client)
            if r["field"] == "paid_through"] == ["1010 Chase"], \
        "the undo did not restore the value the earlier save had taught"


def test_the_undo_deletes_a_row_the_save_created(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    _edit(client, batch, _doc(client, batch), "paid_through", "1010 Chase")
    journal_id = _save(client, batch)["journal_id"]
    assert _correction_rows(client), "nothing was learned to undo"

    resp = _undo(client, journal_id)
    assert resp.status_code == 200, resp.text
    assert _correction_rows(client) == [], "a row the save created survived the undo"
    assert _commits(client)[0]["reverted_at"]


def test_the_undo_restores_the_merchant_registry(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "vendor", "Staples Incorporated")

    before = client.get("/api/settings").json()["merchants"]
    plan = _plan(client, batch)
    assert plan["registry"], "a vendor edit teaches the registry, so the plan says so"

    journal_id = _save(client, batch)["journal_id"]
    after = client.get("/api/settings").json()["merchants"]
    assert after != before, "the save did not change the registry"

    assert _undo(client, journal_id).status_code == 200
    assert client.get("/api/settings").json()["merchants"] == before


def test_after_an_undo_the_next_publish_teaches_again(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    _edit(client, batch, _doc(client, batch), "paid_through", "1010 Chase")
    journal_id = _save(client, batch)["journal_id"]
    assert _undo(client, journal_id).status_code == 200
    assert _correction_rows(client) == []

    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    assert resp.json()["memory"]["saved"] is True, \
        "publish reported 'unchanged' over a memory the undo had emptied"
    assert [r["value"] for r in _correction_rows(client)
            if r["field"] == "paid_through"] == ["1010 Chase"]


def test_an_undone_save_cannot_be_undone_twice(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    _edit(client, batch, _doc(client, batch), "paid_through", "1010 Chase")
    journal_id = _save(client, batch)["journal_id"]
    assert _undo(client, journal_id).status_code == 200

    resp = _undo(client, journal_id)
    assert resp.status_code == 409
    assert resp.json()["code"] == "memory_journal_already_reverted"


def test_an_older_save_cannot_jump_the_queue(client, monkeypatch):
    batch1 = _create_batch(client, monkeypatch)
    _edit(client, batch1, _doc(client, batch1), "paid_through", "1010 Chase")
    first = _save(client, batch1)["journal_id"]

    batch2 = _create_batch(client, monkeypatch, name="b.jpg", data=JPG + b"x")
    _edit(client, batch2, _doc(client, batch2), "paid_through", "2020 Amex")
    second = _save(client, batch2)["journal_id"]

    resp = _undo(client, first)
    assert resp.status_code == 409
    assert resp.json()["code"] == "memory_journal_not_latest"
    assert resp.json()["latest_id"] == second
    assert [r["value"] for r in _correction_rows(client)
            if r["field"] == "paid_through"] == ["2020 Amex"], \
        "the refused undo changed the store anyway"


def test_an_unknown_save_is_a_404(client):
    resp = _undo(client, 4242)
    assert resp.status_code == 404
    assert resp.json()["code"] == "memory_journal_not_found"
