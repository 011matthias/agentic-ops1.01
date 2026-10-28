"""Item 88: a month's corrections are saved to memory at sign-off.

Owner ruling 2026-09-16: save a month's corrections to memory automatically
at month sign-off, with the Memory page as the undo. The app's sign-off is
Publish. Route-level through the FastAPI app:

* publishing saves the month's corrections, and the next month auto-fills
  from them (the caller the fix changed, end to end);
* publishing again with nothing new saves nothing, so the Memory page's
  counts are not inflated by unpublish / publish;
* a correction made after the last save is saved at the next publish;
* a save through the button counts as saved for the next publish;
* a failed save never fails the publish, and the reply names it.
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction() -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _patch_ocr(monkeypatch) -> None:
    mock = MockLLMClient(extraction_responses=[_extraction()])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _create_batch(client, monkeypatch, name="a.jpg", data=JPG) -> str:
    _patch_ocr(monkeypatch)
    resp = client.post("/api/expense-batches", data={"legal_entity": "Corporate Services"})
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
    return client.get(f"/api/expense-batches/{batch_id}").json()["expenses"][0]["document_id"]


def _edit(client, batch_id, doc, field, value) -> None:
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": field, "value": value}
    )
    assert resp.status_code == 200, resp.text


def _publish(client, batch_id) -> dict:
    # These months have receipts and no statement, so since item 100 they
    # publish only on an explicit override; the memory save is the same.
    resp = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["published"] is True
    return body["memory"]


def _field_counts(client) -> dict[str, int]:
    memory = client.get("/api/memory").json()
    return {c["field"]: c["count"] for c in memory["field_corrections"]}


def test_publishing_saves_the_month_and_the_next_month_autofills(client, monkeypatch):
    batch1 = _create_batch(client, monkeypatch)
    doc = _doc(client, batch1)
    _edit(client, batch1, doc, "vendor", "Staples Inc")
    _edit(client, batch1, doc, "paid_through", "1010 Chase")
    assert _field_counts(client) == {}, "nothing is learned before sign-off"

    memory = _publish(client, batch1)
    assert memory["saved"] is True
    assert memory["learned"]["field_corrections"] == 2
    assert set(_field_counts(client)) == {"vendor", "paid_through"}

    batch2 = _create_batch(client, monkeypatch, name="again.jpg", data=JPG + b"x")
    row = client.get(f"/api/expense-batches/{batch2}").json()["expenses"][0]
    assert row["paid_through"] == "1010 Chase"
    assert "Auto-filled from a prior correction" in row["data_quality_note"]


def test_publishing_again_with_nothing_new_saves_nothing(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    assert _publish(client, batch)["saved"] is True
    before = _field_counts(client)

    assert client.post(f"/api/runs/{batch}/unpublish").status_code == 200
    memory = _publish(client, batch)
    assert memory == {"saved": False, "reason": "unchanged"}
    assert _field_counts(client) == before, "the same correction was counted twice"


def test_a_correction_after_the_last_save_is_saved_at_the_next_publish(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    assert _publish(client, batch)["saved"] is True

    _edit(client, batch, doc, "vendor", "Staples Inc")
    memory = _publish(client, batch)
    assert memory["saved"] is True
    assert "vendor" in _field_counts(client)


def test_a_save_by_the_button_counts_for_the_next_publish(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)
    doc = _doc(client, batch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert resp.json()["learned"]["field_corrections"] == 1

    assert _publish(client, batch) == {"saved": False, "reason": "unchanged"}
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert store.get_memory_commit(batch)["trigger"] == "button"


def test_a_failed_save_never_fails_the_publish(client, monkeypatch):
    batch = _create_batch(client, monkeypatch)

    def boom(*args, **kwargs):
        raise RuntimeError("learning store unavailable")

    monkeypatch.setattr("expense_recon.web.service.commit_to_memory", boom)
    memory = _publish(client, batch)
    assert memory["saved"] is False
    assert "learning store unavailable" in memory["error"]
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert store.get_run(batch).published is True
        assert store.get_memory_commit(batch) is None, "a failed save is not recorded as saved"


def test_deleting_a_month_drops_the_record_of_its_save(tmp_path):
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        store.create_run(
            run_id="r1", created_at="2026-07-31T00:00:00", label="July 2026",
            operator=None, summary={}, snapshot={}, config={},
            work_dir=str(tmp_path), llm_enabled=False, has_coa=False,
        )
        store.set_memory_commit("r1", "abc", "2026-07-31T00:00:00", "publish")
        assert store.delete_run("r1") is True
        assert store.get_memory_commit("r1") is None
