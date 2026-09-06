"""Cross-batch settlement: the receipt_claims registry (R4, backlog item 38).

A receipt must never settle two charges across two batches. Within one run
the matcher's per-call assignment already guarantees single consumption
(`assigned_rec` in matching/deterministic.py); across runs the arbiter is
the `receipt_claims` table, written and re-checked by `rematch_month` and
kept current by the reviewer's verdicts.

The protocol under test:

* advisory read at match time — a receipt another run settled is excluded
  from the candidate pool before the matcher sees it;
* commit-time re-check inside the batch writer lock — a pairing whose
  receipt was claimed while the match ran is downgraded to unmatched, never
  committed;
* claims recorded on commit, released on reject, moved on re-pick, refused
  (409) when a pick would steal another run's receipt;
* cascade on batch delete, both directions;
* and the load-bearing pin: with no cross-batch receipts in play, the
  machinery changes NOTHING — a month reconciles identically with the
  claims code active and with it stubbed out.

Today no production path puts one run's receipt in another run's pool, so
the cross-run cases inject foreign claims directly into the store — exactly
the rows the trip-spanning pool (R4b) will write.
"""
from __future__ import annotations

import json
import re
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
OTHER_RUN = "trip-rome-2026"
NOW = "2026-09-06T00:00:00"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor="Staples", total="42.50", date="2026-04-15"):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
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


def _store(client) -> RunStore:
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


def _snapshot(client, batch_id) -> dict:
    with _store(client) as store:
        return store.get_run(batch_id).snapshot or {}


def _matched_pair(client, batch_id) -> tuple[str, str]:
    """(transaction_id, document_id) of the month's one deterministic
    match (STAPLES NYC 42.50 vs the mocked Staples extraction)."""
    matches = (_snapshot(client, batch_id).get("outcome") or {}).get(
        "matches"
    ) or []
    assert matches, "fixture month reconciled nothing; harness broken"
    return matches[0]["transaction_id"], matches[0]["document_id"]


# ── store semantics ──────────────────────────────────────────────────


def test_store_claim_semantics(tmp_path):
    with RunStore(tmp_path / "s.sqlite") as store:
        assert store.upsert_receipt_claim("t1", "doc-a", "m1", "tx-1", NOW)
        # Another run cannot steal a settled receipt.
        assert not store.upsert_receipt_claim("t1", "doc-a", "m2", "tx-9", NOW)
        assert store.get_claims_on_receipts("t1")["doc-a"][
            "claimed_by_run_id"] == "m1"
        # The holder re-picking onto another charge updates in place.
        assert store.upsert_receipt_claim("t1", "doc-a", "m1", "tx-2", NOW)
        assert store.get_claims_on_receipts("t1")["doc-a"][
            "transaction_id"] == "tx-2"
        # replace: exactly the given set, refusing foreign-held receipts.
        store.upsert_receipt_claim("t2", "doc-b", "m2", "tx-b", NOW)
        conflicts = store.replace_claims_by_run(
            "m1", [("t1", "doc-a", "tx-3"), ("t2", "doc-b", "tx-4")], NOW
        )
        assert conflicts == [("t2", "doc-b", "tx-4")]
        assert [c["document_id"] for c in store.get_claims_by_run("m1")] == [
            "doc-a"
        ]
        # release by charge, release by receipt.
        store.delete_claims_for_tx("m1", "tx-3")
        assert store.get_claims_by_run("m1") == []
        store.delete_claims_for_receipt("t2", "doc-b")
        assert store.get_claims_on_receipts("t2") == {}


def test_delete_run_cascades_both_claim_directions(tmp_path):
    with RunStore(tmp_path / "s.sqlite") as store:
        # m1 claims a receipt living in t1; m2 claims a receipt living in m1.
        store.upsert_receipt_claim("t1", "doc-a", "m1", "tx-1", NOW)
        store.upsert_receipt_claim("m1", "doc-b", "m2", "tx-2", NOW)
        store.delete_run("m1")
        assert store.get_claims_on_receipts("t1") == {}, (
            "deleting the claiming run must release the receipts it settled"
        )
        assert store.get_claims_on_receipts("m1") == {}, (
            "claims on a deleted run's receipts point at nothing; drop them"
        )


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "s.sqlite"
    with RunStore(db) as store:
        store.upsert_receipt_claim("t1", "doc-a", "m1", "tx-1", NOW)
    with RunStore(db) as store:  # re-open re-runs _init_schema
        assert store.get_claims_on_receipts("t1")["doc-a"][
            "claimed_by_run_id"] == "m1"


# ── rematch protocol ─────────────────────────────────────────────────


def test_commit_records_the_months_own_settlements(client, monkeypatch):
    """The registry half: a reconciled month's deterministic matches are on
    file as claims, keyed on the receipt's home run."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    tx_id, doc_id = _matched_pair(client, batch_id)
    with _store(client) as store:
        claims = store.get_claims_by_run(batch_id)
    assert [(c["receipt_run_id"], c["document_id"], c["transaction_id"])
            for c in claims] == [(batch_id, doc_id, tx_id)]


def test_a_foreign_settled_receipt_cannot_settle_a_second_charge(
    client, monkeypatch
):
    """THE cross-run guard, trip-shaped: another run has already settled
    this receipt (the claim row R4b's spanning pool will write), so this
    month's matcher must not consume it -- one receipt, one charge,
    globally. Disable the advisory read in `rematch_month` and the Staples
    receipt settles both that foreign charge and ours."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc_id = _snapshot(client, batch_id)["receipts"][0]["document_id"]
    with _store(client) as store:
        assert store.upsert_receipt_claim(
            batch_id, doc_id, OTHER_RUN, "tx-elsewhere", NOW
        )

    _attach(client, batch_id)

    outcome = _snapshot(client, batch_id).get("outcome") or {}
    assert not any(
        m["document_id"] == doc_id for m in outcome.get("matches") or []
    ), "a receipt settled by another run settled a second charge here"
    assert doc_id in (outcome.get("unmatched_receipts") or []), (
        "the excluded receipt must stay visible in this month's pool"
    )
    with _store(client) as store:
        assert store.get_claims_by_run(batch_id) == []
        assert store.get_claims_on_receipts(batch_id)[doc_id][
            "claimed_by_run_id"] == OTHER_RUN
    # The view names who settled it -- parallel field, absent elsewhere.
    view = client.get(f"/api/runs/{batch_id}").json()
    settled = [
        r for r in view["unmatched_receipts"]
        if r.get("document_id") == doc_id
    ]
    assert settled and settled[0]["settled_by"]["run_id"] == OTHER_RUN
    assert settled[0]["settled_by"]["transaction_id"] == "tx-elsewhere"
    assert all(
        "settled_by" not in r
        for r in view["unmatched_receipts"]
        if r.get("document_id") != doc_id
    ), "settled_by must be ABSENT on unsettled receipts, not null"


def test_commit_recheck_downgrades_a_claim_raced_in_mid_match(
    client, monkeypatch
):
    """The authoritative half: the advisory read passed (no claim yet), the
    claim lands WHILE the matcher runs, and the commit inside the writer
    lock re-reads and downgrades rather than committing a double
    settlement."""
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc_id = _snapshot(client, batch_id)["receipts"][0]["document_id"]
    db_path = Path(client._data_root) / "recon-web.sqlite"

    from expense_recon.matching import deterministic as det

    real_match_month = det.match_month

    def race(transactions, receipts, cfg=None):
        outcome = real_match_month(transactions, receipts, cfg)
        with RunStore(db_path) as s:
            s.upsert_receipt_claim(
                batch_id, doc_id, OTHER_RUN, "tx-elsewhere", NOW
            )
        return outcome

    monkeypatch.setattr(det, "match_month", race)
    _attach(client, batch_id)

    outcome = _snapshot(client, batch_id).get("outcome") or {}
    assert not any(
        m["document_id"] == doc_id for m in outcome.get("matches") or []
    ), "a claim raced in mid-match was committed anyway"
    assert doc_id in (outcome.get("unmatched_receipts") or [])
    # The charge the pairing would have settled is unmatched, not dropped.
    staples_tx = [
        t["transaction_id"]
        for t in _snapshot(client, batch_id).get("transactions") or []
        if "STAPLES" in (t.get("vendor_from_statement") or "")
    ]
    assert staples_tx, "fixture statement lost its Staples row"
    assert staples_tx[0] in (outcome.get("unmatched_transactions") or [])
    with _store(client) as store:
        assert store.get_claims_by_run(batch_id) == []


# ── reviewer verdicts ────────────────────────────────────────────────


def test_reject_releases_and_repick_moves_the_claim(client, monkeypatch):
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    tx_id, doc_id = _matched_pair(client, batch_id)

    r = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": "rejected"},
    )
    assert r.status_code == 200, r.text
    with _store(client) as store:
        assert store.get_claims_by_run(batch_id) == [], (
            "a rejected match must release its receipt"
        )

    r = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={
            "transaction_id": tx_id,
            "status": "confirmed",
            "chosen_document_id": doc_id,
        },
    )
    assert r.status_code == 200, r.text
    with _store(client) as store:
        claims = store.get_claims_by_run(batch_id)
    assert [(c["document_id"], c["transaction_id"]) for c in claims] == [
        (doc_id, tx_id)
    ]


def test_a_pick_that_would_steal_another_runs_receipt_is_refused(
    client, monkeypatch
):
    """409 on the single-decision route and on manual-match; the decision
    is NOT written, so the row does not claim what it cannot hold."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    _add_receipt(client, batch_id)
    snap = _snapshot(client, batch_id)
    free_doc = next(
        r["document_id"] for r in snap["receipts"]
        if r.get("detected_vendor") == "Late Vendor"
    )
    coffee_tx = next(
        t["transaction_id"] for t in snap["transactions"]
        if "COFFEE" in (t.get("vendor_from_statement") or "")
    )
    with _store(client) as store:
        assert store.upsert_receipt_claim(
            batch_id, free_doc, OTHER_RUN, "tx-elsewhere", NOW
        )

    r = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={
            "transaction_id": coffee_tx,
            "status": "confirmed",
            "chosen_document_id": free_doc,
        },
    )
    assert r.status_code == 409, r.text
    r = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": coffee_tx, "document_id": free_doc},
    )
    assert r.status_code == 409, r.text
    with _store(client) as store:
        assert coffee_tx not in store.get_decisions(batch_id), (
            "the refused verdict must not be written"
        )


# ── lifecycle ────────────────────────────────────────────────────────


def test_deleting_the_month_releases_its_claims(client, monkeypatch):
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    assert _matched_pair(client, batch_id)
    r = client.post(
        f"/api/runs/{batch_id}/delete", json={"confirm": batch_id}
    )
    assert r.status_code == 200, r.text
    with _store(client) as store:
        assert store.get_claims_by_run(batch_id) == []
        assert store.get_claims_on_receipts(batch_id) == {}


def test_deleting_an_expense_releases_its_claim(client, monkeypatch):
    _wire(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    doc_id = _snapshot(client, batch_id)["receipts"][0]["document_id"]
    with _store(client) as store:
        store.upsert_receipt_claim(
            batch_id, doc_id, OTHER_RUN, "tx-elsewhere", NOW
        )
    r = client.delete(f"/api/runs/{batch_id}/expenses/{doc_id}")
    assert r.status_code == 200, r.text
    with _store(client) as store:
        assert store.get_claims_on_receipts(batch_id) == {}


# ── the load-bearing pin ─────────────────────────────────────────────


_TS = re.compile(r"\d{4}-\d{2}-\d{2}T[0-9:.+\-]*")


def _normalized(payload, batch_id: str) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return _TS.sub("TS", text.replace(batch_id, "RUN"))


def test_with_zero_cross_batch_receipts_the_machinery_changes_nothing(
    monkeypatch, tmp_path
):
    """The pin the whole round hangs on: for a month with no cross-batch
    receipts (every month until trips exist), the claims machinery is
    inert -- the same inputs reconcile to the same outcome, summary, and
    view payload with the claims code active and with it stubbed out.
    Ids and timestamps are the only difference, normalized away."""
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def build(root: Path, neutered: bool):
        _wire(monkeypatch, _extraction())
        app = create_app(root)
        with TestClient(app) as c:
            c._data_root = root
            if neutered:
                monkeypatch.setattr(
                    RunStore, "get_claims_on_receipts",
                    lambda self, run_id: {},
                )
                monkeypatch.setattr(
                    RunStore, "replace_claims_by_run",
                    lambda self, run_id, claims, at: [],
                )
                monkeypatch.setattr(
                    RunStore, "upsert_receipt_claim",
                    lambda self, *a, **k: True,
                )
            batch_id = _create_batch(c)
            _attach(c, batch_id)
            view = c.get(f"/api/runs/{batch_id}").json()
            with RunStore(root / "recon-web.sqlite") as store:
                run = store.get_run(batch_id)
            snap = {
                k: (run.snapshot or {}).get(k)
                for k in ("transactions", "receipts", "outcome")
            }
            return (
                _normalized(view, batch_id),
                _normalized(snap, batch_id),
                _normalized(run.summary, batch_id),
            )

    live = build(tmp_path / "live", neutered=False)
    inert = build(tmp_path / "inert", neutered=True)
    assert live[1] == inert[1], "snapshot diverged with zero claims in play"
    assert live[2] == inert[2], "summary diverged with zero claims in play"
    assert live[0] == inert[0], "view payload diverged with zero claims"
