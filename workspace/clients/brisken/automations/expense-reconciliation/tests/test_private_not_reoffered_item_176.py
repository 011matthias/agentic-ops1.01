"""Backlog item 176 (operator 2026-09-23): the private control is not
offered again on a row that is already private.

Operator: "no need to set this as private again, if user has already set
as private".

`can_mark_private` used to read `private or (...)`, so every confirmed
private row in the estate (2 of 2, September's and July's) told the screen
it could still be marked private. The published SPA reads that field
through one helper::

    Zt(row) = typeof row.can_mark_private === "boolean"
              ? row.can_mark_private : row.card == null

and the control that belongs on a confirmed private row is undo, which the
screen keys on `row.private` itself. So the flag can say what is true.

Pinned here:
* a confirmed private row reads `can_mark_private` false, and clearing the
  confirmation brings it back true;
* the flip does NOT close the private route on an already-private row --
  re-saving who gets reimbursed is one decision being corrected, not a
  second one, and refusing it would have said "paid with a company card"
  about a row no company card paid;
* the company-card refusal the flag backs still bites on a row that is not
  private, which is the half item 41 added it for.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CORP = {"corp-1672": {"digits": ["1672"], "entity": "Corporate Services",
                      "person": "Nicolas"}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, label="August 2026", seed=0):
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    files = [("files", ("r0.jpg", JPG + bytes([0, seed]),
                        "application/octet-stream"))]
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _row(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"][0]


def test_a_confirmed_private_row_is_not_offered_the_private_control(
    client, monkeypatch
):
    """The row the note was left on: September 0046 read `private: true`
    and `can_mark_private: true` together."""
    _patch_ocr(monkeypatch, _extraction(payment_hint="EC-Karte"))
    batch = _create_batch(client)
    row = _row(client, batch)
    # Before the confirmation the option is on offer, which is the point:
    # the flag is not simply always false either.
    assert row["private"] is False
    assert row["suggested_private"] is True
    assert row["can_mark_private"] is True

    doc = row["document_id"]
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True, "reimburse_to": "Dirk Neumann"})
    assert r.status_code == 200, r.text

    row = _row(client, batch)
    assert row["private"] is True
    assert row["reimburse_to"] == "Dirk Neumann"
    assert row["person_source"] == "private"
    assert row["can_mark_private"] is False, (
        "a row that IS private cannot be marked private again"
    )
    # The suggestion is gone too, so neither private control has anything
    # left to render off the payload.
    assert row["suggested_private"] is False


def test_clearing_the_confirmation_offers_the_control_again(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(payment_hint="EC-Karte"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    assert client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                       json={"private": True,
                             "reimburse_to": "Dirk Neumann"}).status_code == 200
    assert _row(client, batch)["can_mark_private"] is False

    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": False})
    assert r.status_code == 200, r.text
    row = _row(client, batch)
    assert row["private"] is False
    assert row["can_mark_private"] is True
    assert row["suggested_private"] is True


def test_who_gets_reimbursed_can_still_be_corrected(client, monkeypatch):
    """The regression the flip would otherwise cause: the private route
    reads the same flag before it writes, so a row that just became
    `can_mark_private: false` by BEING private would have refused its own
    correction -- with the company-card wording, on a row no company card
    paid."""
    _patch_ocr(monkeypatch, _extraction(payment_hint="EC-Karte"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    assert client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                       json={"private": True,
                             "reimburse_to": "Dirk Neumann"}).status_code == 200

    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True, "reimburse_to": "Criss Cavalcanti"})
    assert r.status_code == 200, r.text
    row = _row(client, batch)
    assert row["reimburse_to"] == "Criss Cavalcanti"
    assert row["person"] == "Criss Cavalcanti"
    assert row["can_mark_private"] is False


def test_the_generic_field_put_still_confirms_an_already_private_row(
    client, monkeypatch
):
    """The second caller of the same guard (`PUT .../expenses/{doc}` with
    field `private`), which reaches it once `reimburse_to` is stored."""
    _patch_ocr(monkeypatch, _extraction(payment_hint="EC-Karte"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    assert client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                       json={"private": True,
                             "reimburse_to": "Dirk Neumann"}).status_code == 200

    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "private", "value": "1"})
    assert r.status_code == 200, r.text
    assert _row(client, batch)["private"] is True


def test_a_company_card_row_is_still_refused(client, monkeypatch):
    """The half the guard exists for is untouched: a row a defined company
    card paid still cannot be marked private."""
    client.put("/api/settings", json={"cards": CORP})
    _patch_ocr(monkeypatch, _extraction(payment_hint="VISA ****1672"))
    batch = _create_batch(client)
    row = _row(client, batch)
    assert row["card"]["key"] == "corp-1672"
    assert row["can_mark_private"] is False

    r = client.post(f"/api/runs/{batch}/expenses/{row['document_id']}/private",
                    json={"private": True, "reimburse_to": "Dirk Neumann"})
    assert r.status_code == 400
    assert r.json()["code"] == "company_card"
    assert _row(client, batch)["private"] is False
