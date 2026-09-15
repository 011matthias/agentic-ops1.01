"""`receipt_image_available` answers the IMAGE ENDPOINT's question, on both
review payloads (item 52).

Criss left "Recibo nao estar abrindo" on the August month. The backlog's
recorded lead was that two flags disagreed on one row and the SPA gated its
viewer on the wrong one. Driving the live app refuted that: the published
bundle references neither flag, and the dead "View receipt" button is the
SPA's own. But the drive found a real one underneath, which is what these
tests pin.

The flag was computed twice. `build_expense_view` resolved it against disk
and was right. `_receipt_view`, which builds the RUN payload, resolved it
from the SHAPE of the document id: a vision-mapped page, or an id starting
`manual:` or `folder:`. Every receipt that arrives by mail or through the
receipts drop is named `NNNN__original-name.pdf` and matches none of those,
so the run payload reported `false` for all 17 unmatched receipts of the
live August month while the endpoint served every one of them 200.

An id-shape test cannot answer this question at all: what the endpoint will
serve depends on what is on disk, and the two drift the moment a new way of
getting a receipt into a month is added. So there is now one resolver,
`receipt_image_file`, and the negative cases below are the contract: the
same row must flip to `false` when its file goes away, or the flag is
decoration rather than an answer.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADER = "Date,Amount,Vendor\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=4):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
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


def _batch(client, name="staples.jpg"):
    """A month whose receipt arrived the way Criss's do: through the drop,
    so its document id is `NNNN__original-name` and not a `manual:` or
    `folder:` key."""
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "April 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, JPG, "application/octet-stream"))],
    ))
    return batch_id


def _attach(client, batch_id, *rows: tuple[str, str, str]):
    body = (HEADER + "".join(f"{d},{a},{v}\n" for d, a, v in rows)).encode()
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("statement.csv", body, "application/octet-stream")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    ))


def _expenses(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"]


def _run(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _image(client, batch_id, document_id):
    return client.get(f"/api/runs/{batch_id}/receipts/{document_id}/image")


def _work_dir(client, batch_id) -> Path:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return Path(store.get_run(batch_id).work_dir)


# ── the flag against the endpoint, on both payloads ──────────────────────


def test_a_dropped_receipt_is_openable_on_the_expense_payload(
    client, monkeypatch
):
    """The screen Criss reviews on. The flag and the endpoint are asserted
    together on purpose: a flag checked only against itself would have
    stayed green through the whole defect."""
    _wire(monkeypatch)
    batch_id = _batch(client)

    (row,) = _expenses(client, batch_id)

    assert row["document_id"] == "0000__staples.jpg"
    assert row["receipt_image_available"] is True
    assert _image(client, batch_id, row["document_id"]).status_code == 200


def test_a_dropped_receipt_is_openable_on_the_run_payload_too(
    client, monkeypatch
):
    """The defect. Once a statement lands the month reconciles, the same
    receipt is rendered by `_receipt_view`, and before item 52 every
    mail-arrived and dropped receipt reported `false` here while the
    endpoint served it."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, ("2026-04-03", "999.00", "SOMETHING ELSE"))

    (rec,) = _run(client, batch_id)["unmatched_receipts"]

    assert rec["document_id"] == "0000__staples.jpg"
    assert rec["receipt_image_available"] is True
    assert _image(client, batch_id, rec["document_id"]).status_code == 200


def test_a_matched_receipt_carries_the_flag_on_its_candidate(
    client, monkeypatch
):
    """The same receipt reached through the other door on the run payload:
    a charge's candidate, which is where a reviewer working the workbench
    actually meets it."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, ("2026-04-15", "42.50", "STAPLES"))

    rows = _run(client, batch_id)["rows"]
    receipts = [
        c["receipt"] for r in rows for c in (r.get("candidates") or [])
        if c.get("receipt")
    ]

    assert receipts, "the charge has no candidate to carry the flag"
    assert all(r["receipt_image_available"] is True for r in receipts)


# ── the negative case: the flag has to be able to say no ─────────────────


def test_a_receipt_whose_file_is_gone_says_so_on_both_payloads(
    client, monkeypatch
):
    """The differential. Same row, same ids, file removed: both payloads
    must flip to `false` and the endpoint must 404. A flag that stays true
    here is not resolving anything, and a reviewer would be offered a View
    button that fails."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, ("2026-04-03", "999.00", "SOMETHING ELSE"))
    doc = "0000__staples.jpg"
    assert _image(client, batch_id, doc).status_code == 200

    (_work_dir(client, batch_id) / "receipts" / doc).unlink()

    assert _image(client, batch_id, doc).status_code == 404
    (expense,) = _expenses(client, batch_id)
    assert expense["receipt_image_available"] is False
    (rec,) = _run(client, batch_id)["unmatched_receipts"]
    assert rec["receipt_image_available"] is False


def test_the_id_shape_alone_never_decides_it(client, monkeypatch):
    """A `folder:`-shaped id with no file behind it was reported openable by
    the old prefix test, which is the mirror image of the live defect and
    the reason the resolver reads disk in both directions."""
    from expense_recon.web.service import receipt_image_file

    _wire(monkeypatch)
    batch_id = _batch(client)
    work_dir = _work_dir(client, batch_id)

    assert receipt_image_file(
        work_dir, "folder:deadbeef", expense_mode=True
    ) is None
    assert receipt_image_file(
        work_dir, "manual:card-1:7", expense_mode=True
    ) is None
    assert receipt_image_file(
        work_dir, "0000__staples.jpg", expense_mode=True
    ) is not None
    # A statement-mode run never serves from the receipts dir, so the
    # resolver must not claim it would.
    assert receipt_image_file(
        work_dir, "0000__staples.jpg", expense_mode=False
    ) is None
