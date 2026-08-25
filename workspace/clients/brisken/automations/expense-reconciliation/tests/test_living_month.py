"""The month stays open once its statement is loaded (2b-2).

Attaching a statement used to CLOSE the month: nine routes through
`_mutable_expense_run_or_error`, plus five refusals in the service functions
beneath them, all answered "a statement is already attached". That made
reconciliation a final exam, which is exactly what the owner directive
reshaped -- the statement is an input stream and the month is a workspace
the accountant works across.

Four of those operations open here: receipts arriving, a set-aside page
restored, a card assigned, master data refreshed. Each is followed by
`rematch_after_change`, because an operation that is allowed but does not
re-reconcile is worse than one that is refused: the receipt would sit in the
pool while the match outcome still described the month as it was before.

Two things deliberately stay closed, each for its own reason and each pinned
below: a second statement upload (append is its own round) and the four
expense-edit overlay routes (PR #628's note -- an edit surface is worth
reopening only once its edits are reversible and honestly attributed).
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

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor="Staples", total="42.50", date="2026-04-15",
                payment_hint=None):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
    )


def _wire(monkeypatch, *extractions, n_fx=12):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("42.50"),
                reasoning="same purchase",
            )
        ] * n_fx,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_batch(client, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _attach(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    job_id = resp.json().get("job_id") if resp.status_code == 200 else None
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _add_receipt(client, batch_id, name="late.jpg", body=b"9"):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, JPG + body, "application/octet-stream"))],
    )
    if resp.status_code == 200:
        job_id = resp.json().get("job_id")
        if job_id:
            assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _grid(client, batch_id):
    return client.get(f"/api/expense-batches/{batch_id}").json()


def _transactions(client, batch_id):
    """The month's stored charges. Read from the STORE, not the grid: the
    grid's summary is receipt-centric and never carried a charge count."""
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {}).get("transactions") or []


def test_a_receipt_that_arrives_after_the_statement_joins_the_month(
    client, monkeypatch
):
    """The core of the living month. The statement is loaded, then a receipt
    arrives -- as Dirk's do, all month -- and the month takes it."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    before = len(_grid(client, batch_id)["expenses"])

    resp = _add_receipt(client, batch_id)

    assert resp.status_code == 200, resp.text
    after = _grid(client, batch_id)["expenses"]
    assert len(after) == before + 1
    assert any(
        (r.get("vendor") or {}).get("display") == "Late Vendor" for r in after
    ), "the receipt was accepted but never reached the month's pool"


def test_the_arrival_re_reconciles_rather_than_just_landing(
    client, monkeypatch
):
    """Allowed but inert would be worse than refused: the reviewer would see
    a receipt in the pool and a match outcome that predates it.

    Asserted against the STORED run summary, not the expense grid's: the
    grid's summary is receipt-centric and carries no match counts, so it
    would move on the add alone and prove nothing. `n_receipts_matched` and
    `n_unmatched_rec` are written by `rematch_month` and by nothing else on
    this path, so their sum moving is the re-match having run.
    """
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    def _accounted() -> int:
        with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
            s = store.get_run(batch_id).summary or {}
        return s["n_receipts_matched"] + s["n_unmatched_rec"]

    before = _accounted()

    _add_receipt(client, batch_id)

    assert _accounted() == before + 1, (
        "the pool grew but the match outcome did not: the re-match never ran"
    )


def test_an_all_duplicate_add_does_not_pay_for_a_re_match(client, monkeypatch):
    """Re-matching costs model calls. An upload whose every file is already
    in the pool changed nothing, so it must not trigger one."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    _add_receipt(client, batch_id)
    summary_after_first = _grid(client, batch_id)["summary"]

    # Byte-identical to the one just added: the pool dedupes it away.
    again = _add_receipt(client, batch_id)
    assert again.status_code == 200, again.text

    assert _grid(client, batch_id)["summary"]["n_receipts"] == (
        summary_after_first["n_receipts"]
    )


def test_a_card_assignment_is_not_gated_by_the_statement(client, monkeypatch):
    """Matching is entity-scoped, so a card with no legal entity is what
    leaves a month matching nothing (Cards R3 F1). Fixing that mid-month is
    the reason this route opens at all.

    Stated as an equivalence rather than a 200, so the test says exactly
    what changed and nothing more: the SAME request gets the SAME answer
    whether or not a statement is loaded. Asserting a 200 would drag a whole
    card registry into a test about the guard, and asserting "not 400" would
    pass for the wrong reason the day the payload shape changes.
    """
    _wire(monkeypatch, _extraction(payment_hint="Visa"),
          _extraction(payment_hint="Visa"))
    payload = {"assignments": [{"hint": "Visa", "card": "corp-2838"}],
               "learn": False}

    open_batch = _create_batch(client)
    open_resp = client.post(
        f"/api/expense-batches/{open_batch}/cards", json=payload
    )

    reconciling = _create_batch(client, label="May 2026")
    _attach(client, reconciling)
    recon_resp = client.post(
        f"/api/expense-batches/{reconciling}/cards", json=payload
    )

    assert recon_resp.status_code == open_resp.status_code
    assert recon_resp.json() == open_resp.json()
    assert "statement is already attached" not in recon_resp.text


def test_refresh_master_data_is_allowed_on_a_reconciling_month(
    client, monkeypatch
):
    """The bulk form of the same operation, open for the same reason."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text


def test_a_second_statement_is_taken_not_refused(client, monkeypatch):
    """The refusal this file used to pin, lifted deliberately in PR 2b-2b-2.

    Both layers had to go: the route gate (`_mutable_expense_run_or_error`)
    and `prepare_statement_attach`'s own check beneath it. A test on the
    route alone would have passed against a service that still refused, which
    is the shape 2b-2a already found once.

    What replaces the refusal is the fold, not a free-for-all: the same file
    twice adds nothing. `tests/test_statement_append.py` owns the append
    behavior; this pins that the door is open at all, where the closed door
    used to be pinned."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    before = len(_transactions(client, batch_id))

    assert _attach(client, batch_id).status_code == 200
    assert len(_transactions(client, batch_id)) == before


def test_the_expense_edit_overlay_stays_closed(client, monkeypatch):
    """Not because re-applying an edit is dangerous -- it is idempotent by
    construction -- but because a re-match bakes the overlay into the pool,
    so the edit surface reopens only with the re-match an edit must trigger.
    Pinned so the guard lift above cannot quietly take these with it."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc_id = _grid(client, batch_id)["expenses"][0]["document_id"]
    _attach(client, batch_id)

    edit = client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}",
        json={"field": "vendor", "value": "X"},
    )
    assert edit.status_code == 400
    assert "workbench" in edit.json()["error"]
    assert client.post(
        f"/api/runs/{batch_id}/expenses", json={"vendor": "Y", "total": "1"}
    ).status_code == 400
    assert client.request(
        "DELETE", f"/api/runs/{batch_id}/expenses/{doc_id}"
    ).status_code == 400
    assert client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}/entity",
        json={"legal_entity": "Corporate Services"},
    ).status_code == 400


def test_a_failed_re_match_does_not_lose_the_receipt(client, monkeypatch):
    """The add commits inside the lock; the re-match runs after it. So a
    re-match that throws -- an OpenAI outage, a corrupt row -- must not
    report the add as failed, or a receipt that safely landed would be
    marked failed and replayed. It is reported, not raised."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    import expense_recon.web.service as service

    def _boom(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(service, "rematch_month", _boom)

    resp = _add_receipt(client, batch_id)
    assert resp.status_code == 200, resp.text

    rows = _grid(client, batch_id)["expenses"]
    assert any(
        (r.get("vendor") or {}).get("display") == "Late Vendor" for r in rows
    ), "the receipt was lost when the re-match failed"


def test_baseline_grows_with_receipts_that_arrive_after_the_bake(
    client, monkeypatch
):
    """Deferred from PR #628, which could not reach this state: no caller
    could add a receipt to a statement-bearing month. Now one can, so the
    extraction baseline's per-document growth is drivable end to end. Each
    arrival is pristine when it lands and must get its own audit baseline."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    _add_receipt(client, batch_id)

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        snapshot = store.get_run(batch_id).snapshot or {}
        baseline = {
            r["document_id"]: r.get("detected_vendor")
            for r in snapshot.get("extracted_receipts") or []
        }
    late = [d for d in baseline if "late" in d.lower()]
    assert late, f"the late receipt never entered the baseline: {list(baseline)}"
    assert baseline[late[0]] == "Late Vendor"
