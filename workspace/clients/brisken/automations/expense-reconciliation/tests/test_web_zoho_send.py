"""The in-app "Send to Zoho" (owner decision 2026-09-28), driven through
the routes the button calls.

Every test goes app route -> `web/zoho_send` -> `reconcile_month.run_month`
-> a fake Zoho client, so unwiring any step of that chain (the server
switch, the confirm value, the shared export builder) turns a test red.
The fake is the whole network: it records every call, so a test can prove
what did NOT happen (no read while switched off, no create on a preview).
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import zoho_send  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import reconcile_month as rm  # noqa: E402
from tests.test_zoho_reconcile_month import CARD_NAME, FakeClient, _existing  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
ACCOUNT = "IT: Cloud Subscriptions-Others"  # in the fake chart
_REAL_MAKE_CLIENT = rm._make_client  # before any fixture swaps in the fake


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(rm, "_make_client", lambda org_id: client)
    return client


@pytest.fixture
def client(tmp_path, monkeypatch, fake):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.setenv(rm.POST_ENV, "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _receipt(**over) -> ExtractedReceipt:
    base = dict(
        date="2026-09-03", total="42.50", currency="USD", vendor="Staples",
        reference="INV-1", line_items=(), confidence=0.9, notes="",
    )
    base.update(over)
    return ExtractedReceipt(**base)


def _month(c, monkeypatch, label="September 2026") -> str:
    """A reviewed month: two receipts, a card, a category on each."""
    mock = MockLLMClient(extraction_responses=[
        _receipt(),
        _receipt(vendor="Anthropic", total="100.00", reference="INV-2",
                 date="2026-09-10"),
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    c.put("/api/settings", json={"entities": {
        "Corporate Services": {"default_paid_through": "1010 Chase Corporate"},
    }})
    resp = c.post("/api/expense-batches",
                  data={"legal_entity": "Corporate Services", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    resp = c.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG + b"a", "image/jpeg")),
               ("files", ("b.jpg", JPG + b"b", "image/jpeg"))],
    )
    assert resp.status_code == 200, resp.text
    assert c.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    for doc in _documents(c, batch_id):
        _categorize(c, batch_id, doc, ACCOUNT)
    return batch_id


def _documents(c, batch_id) -> list[str]:
    grid = c.get(f"/api/expense-batches/{batch_id}").json()
    return [e["document_id"] for e in grid["expenses"]]


def _categorize(c, batch_id, document_id, account):
    resp = c.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": document_id,
        "category": "Software & Subscriptions",
        "zoho_account": account,
    })
    assert resp.status_code == 200, resp.text


def _preview(c, batch_id) -> dict:
    resp = c.get(f"/api/runs/{batch_id}/zoho-send")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _send(c, batch_id, confirm) -> dict:
    resp = c.post(f"/api/runs/{batch_id}/zoho-send", json={"confirm": confirm})
    assert resp.status_code == 200, resp.text
    job = c.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["result"]


def _created_refs(fake) -> list[str]:
    return sorted(r["reference_number"] for r in fake.created)


# ── switched off: nothing reads Zoho, nothing sends ─────────────────


def test_switched_off_reads_nothing_and_refuses_the_send(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch)
    monkeypatch.delenv(rm.POST_ENV)

    body = _preview(client, batch_id)
    assert body["enabled"] is False
    assert "switched off" in body["reason"]

    resp = client.post(f"/api/runs/{batch_id}/zoho-send", json={"confirm": "x"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "zoho_send_off"
    assert fake.calls == []


# ── preview ─────────────────────────────────────────────────────────


def test_preview_shows_what_would_be_sent_and_posts_nothing(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch)
    body = _preview(client, batch_id)

    assert body["enabled"] is True
    assert body["status"] == "ready"
    assert body["month"] == "2026-09"
    assert body["company"] == "TEST-BTS" and body["test_company"] is True
    assert body["count"] == 2 and body["total"] == "142.50"
    assert [(e["reference"], e["amount"], e["vendor"]) for e in body["entries"]] == [
        ("INV-1", "42.50", "Staples"), ("INV-2", "100.00", "Anthropic"),
    ]
    assert body["entries"][0]["accounts"] == [ACCOUNT]
    assert body["confirm"]
    assert "create" not in fake.calls


def test_the_preview_is_built_from_the_same_file_as_the_download(client, monkeypatch):
    """The button and the download share one export builder, so what can
    be opened and checked is what gets sent."""
    batch_id = _month(client, monkeypatch)
    rows = list(csv.DictReader(io.StringIO(client.get(f"/runs/{batch_id}/expenses.csv").text)))
    downloaded = sorted((r["Reference#"], r["Expense Amount"]) for r in rows if r["Reference#"])
    previewed = sorted((e["reference"], e["amount"]) for e in _preview(client, batch_id)["entries"])
    assert previewed == downloaded


# ── send ────────────────────────────────────────────────────────────


def test_send_enters_the_previewed_month_and_reads_it_back(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch)
    confirm = _preview(client, batch_id)["confirm"]

    result = _send(client, batch_id, confirm)

    assert result["ok"] is True, result
    assert result["sent"] == 2 and result["checked_ok"] == 2
    assert result["totals_match"] is True
    assert result["total_sent"] == result["total_in_zoho"] == "142.50"
    assert _created_refs(fake) == ["INV-1", "INV-2"]
    assert zoho_send.ledger_path(client._data_root).exists()


def test_sending_the_same_month_again_sends_nothing(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch)
    _send(client, batch_id, _preview(client, batch_id)["confirm"])

    again = _preview(client, batch_id)
    assert again["status"] == "nothing_to_send"
    assert again["already_sent"] == 2
    assert {h["reason"] for h in again["held_back"]} == {"already_in_ledger"}

    result = _send(client, batch_id, again["confirm"])
    assert result["sent"] == 0
    assert _created_refs(fake) == ["INV-1", "INV-2"]


def test_a_month_changed_after_the_preview_is_not_sent(client, fake, monkeypatch):
    """Criss confirms one thing, somebody edits the month, the send must
    not post the edited version she never saw."""
    batch_id = _month(client, monkeypatch)
    confirm = _preview(client, batch_id)["confirm"]
    _categorize(client, batch_id, _documents(client, batch_id)[0], "Office Supplies")

    result = _send(client, batch_id, confirm)

    assert result["ok"] is False
    assert "changed after the preview" in result["reason"]
    assert result["sent"] == 0
    assert "create" not in fake.calls


def test_a_hand_entered_month_is_blocked(client, fake, monkeypatch):
    fake.existing.append(_existing(date="2026-09-05", card=CARD_NAME))
    batch_id = _month(client, monkeypatch)

    body = _preview(client, batch_id)
    assert body["status"] == "blocked"
    assert "typed in by hand" in body["reason"]
    assert body["confirm"] == ""

    result = _send(client, batch_id, "anything")
    assert result["ok"] is False and result["sent"] == 0
    assert "create" not in fake.calls


def test_the_send_needs_the_preview_confirm_value(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch)
    resp = client.post(f"/api/runs/{batch_id}/zoho-send", json={})
    assert resp.status_code == 400
    assert resp.json()["code"] == "zoho_send_confirm_required"
    assert "create" not in fake.calls


def test_a_month_whose_name_names_no_month_cannot_be_sent(client, fake, monkeypatch):
    batch_id = _month(client, monkeypatch, label="misc receipts")
    resp = client.get(f"/api/runs/{batch_id}/zoho-send")
    assert resp.status_code == 409
    assert resp.json()["code"] == "zoho_send_no_month"
    assert fake.calls == []


def test_zoho_failing_the_month_check_blocks_the_send(client, fake, monkeypatch):
    """A month that cannot be checked for hand-entered rows is never sent;
    the runner's occupancy guard reads any failure as UNVERIFIABLE."""
    batch_id = _month(client, monkeypatch)
    fake.occupancy_raises = rm.ZohoAuthError("invalid_code")

    body = _preview(client, batch_id)
    assert body["status"] == "blocked"
    assert "could not be checked" in body["reason"]
    assert "invalid_code" in body["detail"]

    result = _send(client, batch_id, "anything")
    assert result["ok"] is False and result["sent"] == 0
    assert "create" not in fake.calls


def test_a_server_without_a_zoho_login_answers_in_plain_words(client, monkeypatch):
    batch_id = _month(client, monkeypatch)
    monkeypatch.setattr(rm, "_make_client", _REAL_MAKE_CLIENT)
    for var in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET",
                "ZOHO_BOOKS_REFRESH_TOKEN", "ZOHO_REFRESH_TOKEN"):
        monkeypatch.delenv(var, raising=False)

    resp = client.get(f"/api/runs/{batch_id}/zoho-send")
    assert resp.status_code == 409
    assert resp.json()["code"] == "zoho_send_refused"
    assert "no Zoho login" in resp.json()["error"]

    resp = client.post(f"/api/runs/{batch_id}/zoho-send", json={"confirm": "x"})
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "error"
    assert "no Zoho login" in job["error"]
