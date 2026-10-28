"""The card roll-up is kept while nothing it reads has changed (2026-09-25).

Owner, 2026-09-25, choosing "memo + warm-up" for the months card strip that
lagged the rest of the page: keep the finished `GET /api/cards/status` body
while the data folder is unchanged, and rebuild it in the background once
writes go quiet.

The contract is that a kept body is never an answer a fresh build would not
give. So the key is tested as an instrument first (it moves on a committed
write and on nothing else), then the route (a write is always read fresh,
a write that lands mid-build is never kept), then the warm-up (it builds
only after a quiet spell, and on a thread with no request it builds exactly
what a request builds).
"""
from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from expense_recon.web.card_status_memo import CardStatusMemo, data_version

# ── the key, as an instrument ──────────────────────────────────────────


def _db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x)")
    conn.commit()
    return conn


def test_the_key_moves_on_a_committed_write_and_on_nothing_else(tmp_path):
    conn = _db(tmp_path / "recon-web.sqlite")
    before = data_version(tmp_path)
    assert before is not None
    conn.execute("SELECT * FROM t").fetchall()
    assert data_version(tmp_path) == before
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    after = data_version(tmp_path)
    assert after != before
    assert data_version(tmp_path) == after


def test_a_second_database_is_part_of_the_key(tmp_path):
    _db(tmp_path / "recon-web.sqlite")
    learning = _db(tmp_path / "learning.sqlite")
    before = data_version(tmp_path)
    learning.execute("INSERT INTO t VALUES (1)")
    learning.commit()
    assert data_version(tmp_path) != before


def test_a_wal_database_turns_the_memo_off(tmp_path):
    conn = _db(tmp_path / "recon-web.sqlite")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    assert data_version(tmp_path) is None


def test_a_data_file_is_part_of_the_key_and_a_journal_is_not(tmp_path):
    _db(tmp_path / "recon-web.sqlite")
    chart = tmp_path / "zoho-books-coa.json"
    chart.write_text('{"accounts": []}', encoding="utf-8")
    before = data_version(tmp_path)
    (tmp_path / "recon-web.sqlite-journal").write_bytes(b"x")
    assert data_version(tmp_path) == before
    chart.write_text('{"accounts": [{"code": "E1"}]}', encoding="utf-8")
    assert data_version(tmp_path) != before


def test_a_presets_file_outside_the_folder_is_part_of_the_key(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    presets = tmp_path / "cards.json"
    presets.write_text("[]", encoding="utf-8")
    before = data_version(folder, (presets,))
    presets.write_text('[{"key": "card-2838"}]', encoding="utf-8")
    assert data_version(folder, (presets,)) != before


def test_a_key_that_cannot_be_read_keeps_nothing():
    built = []
    memo = CardStatusMemo(version=lambda: None, build=lambda: built.append(1) or b"{}")
    memo.get()
    memo.get()
    assert len(built) == 2


# ── the route ──────────────────────────────────────────────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

CARDS = {
    "3876": {"label": "Nicolas card", "digits": ["3876"],
             "entity": "Corporate Services", "person": "Nicolas Neumann",
             "zoho_account": "Chase 3876"},
    "card-9693": {"label": "Cloud card", "digits": ["9693"],
                  "entity": "Cloud Services", "person": "Criss",
                  "zoho_account": "Chase 9693"},
}
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-memo"
_SEQ = [0]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARD_STATUS_WARM", raising=False)
    return create_app(tmp_path)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        assert c.put("/api/settings", json={"cards": CARDS}).status_code == 200
        yield c


def _ff(invoice: str, *, hint: str | None = None, day: str = "2026-07-10",
        total: str = "18.00") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor="Fireflies.ai Corp",
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint, invoice_number=invoice,
    )


def _month(client, monkeypatch, label: str, *extractions) -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"memo-{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 3]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _account_months(client, monkeypatch) -> str:
    """July: two purchases of account HQXED19R printing card 3876. May: one
    purchase of the same account printing no card, which reaches 3876 only
    through the billing-account link (item 204 step 4). Returns May."""
    _month(client, monkeypatch, "July 2026",
           _ff("HQXED19R-0007", hint="Visa ...3876", day="2026-07-10"),
           _ff("HQXED19R-0008", hint="Visa ...3876", day="2026-07-24", total="5.00"))
    return _month(client, monkeypatch, "May 2026", _ff("HQXED19R-0004", day="2026-05-12"))


def _on_3876(body: dict) -> set[str]:
    card = next(c for c in body["cards"] if c["key"] == "3876")
    return {m["run_id"] for m in card["receipt_months"]}


def test_a_repeat_read_is_served_without_a_rebuild(app, client, monkeypatch):
    _account_months(client, monkeypatch)
    memo = app.state.card_status_memo
    first = client.get("/api/cards/status")
    builds = memo.builds
    second = client.get("/api/cards/status")
    assert first.status_code == second.status_code == 200
    assert second.content == first.content
    assert second.headers["content-type"] == "application/json"
    assert memo.builds == builds


def test_a_kept_body_is_what_a_fresh_build_answers(app, client, monkeypatch):
    _account_months(client, monkeypatch)
    client.get("/api/cards/status")
    kept = client.get("/api/cards/status").content
    assert kept == app.state.card_status_memo._build()


def test_a_settings_change_is_read_fresh(app, client, monkeypatch):
    """A settings write is a new key, so the next open rebuilds. (Retiring a
    card leaves this body unchanged: a month keeps the registry it was
    created with. The test asserts the rebuild, not a difference.)"""
    may = _account_months(client, monkeypatch)
    before = client.get("/api/cards/status")
    assert may in _on_3876(before.json())
    memo = app.state.card_status_memo
    builds = memo.builds
    retired = {**CARDS, "3876": {**CARDS["3876"], "active": False}}
    assert client.put("/api/settings", json={"cards": retired}).status_code == 200
    after = client.get("/api/cards/status")
    assert memo.builds == builds + 1
    assert after.content == memo._build()


def test_an_edit_inside_a_month_is_read_fresh(app, client, monkeypatch):
    may = _account_months(client, monkeypatch)
    assert may in _on_3876(client.get("/api/cards/status").json())
    doc = client.get(f"/api/expense-batches/{may}").json()["expenses"][0]["document_id"]
    resp = client.put(f"/api/runs/{may}/expenses/{doc}",
                      json={"field": "card_key", "value": "card-9693"})
    assert resp.status_code == 200, resp.text
    assert may not in _on_3876(client.get("/api/cards/status").json())


def test_a_write_during_the_build_is_not_kept(app, client, monkeypatch):
    _account_months(client, monkeypatch)
    memo = app.state.card_status_memo
    real = memo._build
    db = app.state.db_path

    def build_then_write():
        body = real()
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE IF NOT EXISTS memo_probe (x)")
        conn.execute("INSERT INTO memo_probe VALUES (1)")
        conn.commit()
        conn.close()
        return body

    monkeypatch.setattr(memo, "_build", build_then_write)
    client.get("/api/cards/status")
    monkeypatch.setattr(memo, "_build", real)
    builds = memo.builds
    client.get("/api/cards/status")
    assert memo.builds == builds + 1


# ── the warm-up ────────────────────────────────────────────────────────


def test_the_warm_up_builds_once_the_folder_is_quiet(app, client, monkeypatch):
    _account_months(client, monkeypatch)
    memo, warmer = app.state.card_status_memo, app.state.card_status_warmer
    builds = memo.builds
    assert warmer.step(100.0) is False          # key seen, quiet clock starts
    assert warmer.step(110.0) is False          # not quiet long enough
    assert warmer.step(121.0) is True           # 21 s quiet: built
    assert memo.builds == builds + 1
    assert warmer.step(130.0) is False          # already holds this key
    client.get("/api/cards/status")
    assert memo.builds == builds + 1            # the open is a hit


def test_a_write_restarts_the_quiet_clock(app, client, monkeypatch):
    _account_months(client, monkeypatch)
    warmer = app.state.card_status_warmer
    warmer.step(0.0)
    assert warmer.step(21.0) is True
    retired = {**CARDS, "3876": {**CARDS["3876"], "active": False}}
    assert client.put("/api/settings", json={"cards": retired}).status_code == 200
    assert warmer.step(30.0) is False           # new key: clock restarts here
    assert warmer.step(45.0) is False
    assert warmer.step(51.0) is True


def test_the_warm_up_stays_off_while_receipt_first_is_off(app, client, monkeypatch):
    warmer = app.state.card_status_warmer
    monkeypatch.delenv("EXPENSE_RECON_RECEIPT_FIRST")
    warmer.step(0.0)
    assert warmer.step(100.0) is False
    assert app.state.card_status_memo.builds == 0


def test_a_warm_build_off_any_request_equals_the_request_build(app, client, monkeypatch):
    """The warm-up runs on its own thread, where no request middleware has
    opened the billing-account scope. May's receipt reaches card 3876 only
    through that scope, so a build without it would file May under no card."""
    may = _account_months(client, monkeypatch)
    requested = client.get("/api/cards/status").content
    out: dict[str, bytes] = {}
    worker = threading.Thread(
        target=lambda: out.setdefault("body", app.state.card_status_memo._build())
    )
    worker.start()
    worker.join()
    assert out["body"] == requested
    assert may in _on_3876(json.loads(out["body"]))
