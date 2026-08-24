"""`rematch_month` and the judgment cache (PR 2b-1 of the living month).

The living month re-matches whenever a receipt arrives or a statement is
appended. Without a cache each of those re-asks the model about pairs it
has already judged, on Dirk's key, every single time. These tests drive
`rematch_month` itself rather than the cache object, so a cache that is
built but not wired fails them.
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
from expense_recon.web.judgment_cache import JudgmentCache, call_key  # noqa: E402
from expense_recon.web.serialize import snapshot_from_dict  # noqa: E402
from expense_recon.web.service import rematch_month  # noqa: E402
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


def _eur_receipt(total: str = "38.00") -> ExtractedReceipt:
    """A EUR receipt against the fixture's USD 42.50 STAPLES charge: a
    currency mismatch is what routes a pair to FX judgment."""
    return ExtractedReceipt(
        date="2026-04-15", total=total, currency="EUR", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, mock) -> None:
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _mock(extractions, n_fx: int = 8) -> MockLLMClient:
    return MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True,
                same_purchase_confidence=0.91,
                implied_rate=1.118,
                converted_amount=Decimal("42.50"),
                reasoning="same purchase",
            )
        ] * n_fx,
    )


def _create_batch(client) -> str:
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return resp.json()["batch_id"]


def _attach(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={
            "statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(),
                "text/csv",
            ),
        },
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json().get("job_id")
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _fx_calls(mock) -> int:
    return sum(1 for c in mock.calls if c[0] == "judge_fx_match")


def _run_and_txs(client, batch_id):
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        txs, _receipts, _outcome, _errs = snapshot_from_dict(run.snapshot)
        return run, txs


def _rematch(client, batch_id):
    """What the living month's incremental paths will call."""
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        txs, _r, _o, _e = snapshot_from_dict(run.snapshot)
        return rematch_month(
            store, run,
            transactions=txs,
            cfg=run.config or {},
            entity="Corporate Services",
            now_iso="2026-08-25T00:00:00+00:00",
        )


# ── the cache, through its caller ──────────────────────────────────


def test_the_fixture_actually_buys_a_judgment(client, monkeypatch):
    """Guard on the guard: if the fixture stopped producing an FX pair,
    the cache tests below would pass by judging nothing at all."""
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    assert _fx_calls(mock) > 0, "fixture produced no FX judgment to cache"


def test_a_rematch_does_not_re_buy_a_judgment(client, monkeypatch):
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    bought = _fx_calls(mock)
    assert bought > 0

    result = _rematch(client, batch_id)

    assert _fx_calls(mock) == bought, (
        "a re-match re-asked the model about a pair it had already judged"
    )
    assert result["judgments_reused"] > 0
    assert result["judgments_new"] == 0


def test_a_rematch_reaches_the_same_verdict_from_cache(client, monkeypatch):
    """Reuse has to be faithful: the cached verdict must reproduce the
    outcome, not merely skip the call."""
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    attach = _attach(client, batch_id).json()

    again = _rematch(client, batch_id)

    for key in ("n_transactions", "n_matched", "n_review", "n_unmatched_tx"):
        if key in attach:
            assert again[key] == attach[key], key


def test_a_genuinely_new_pair_still_reaches_the_model(client, monkeypatch):
    """The cache must not starve new work. A receipt added after the
    first match is a pair nobody has judged, so it must cost a call."""
    mock = _mock([_eur_receipt(), _eur_receipt("18.50")])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    bought = _fx_calls(mock)

    # A second EUR receipt joins the pool, exactly as a mailed-in
    # receipt will once PR 2b-2 opens the month.
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot)
        receipts = list(snapshot.get("receipts") or [])
        clone = dict(receipts[0])
        clone["document_id"] = clone["document_id"] + "-second"
        clone["detected_total"] = "18.50"
        clone["detected_date"] = "2026-04-03"
        clone["detected_vendor"] = "Delancey Tavern"
        snapshot["receipts"] = receipts + [clone]
        store.update_run_snapshot(batch_id, snapshot)

    result = _rematch(client, batch_id)

    assert _fx_calls(mock) > bought, "a never-judged pair was not sent to the model"
    assert result["judgments_new"] > 0


def test_judgments_survive_the_snapshot(client, monkeypatch):
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    run, _txs = _run_and_txs(client, batch_id)
    stored = (run.snapshot or {}).get("llm_judgments")
    assert isinstance(stored, dict) and stored, "judgments were not persisted"
    assert len(JudgmentCache.from_snapshot(run.snapshot)) == len(stored)


def test_operator_decisions_survive_a_rematch(client, monkeypatch):
    """The reason PR 2a shipped first: a re-match must not move a
    decision onto a different charge, or lose it."""
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    view = client.get(f"/api/runs/{batch_id}").json()
    tx_id = view["rows"][0]["transaction_id"]
    assert client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": "rejected"},
    ).status_code == 200

    _rematch(client, batch_id)

    after = client.get(f"/api/runs/{batch_id}").json()
    row = next(r for r in after["rows"] if r["transaction_id"] == tx_id)
    assert row["status"] == "rejected"


# ── the key ────────────────────────────────────────────────────────


def test_a_corrected_receipt_amount_misses_the_cache():
    """Why the key is content and not `(transaction_id, document_id)`:
    a reviewer can correct an amount after the pair was judged, and the
    verdict the model gave for the OLD numbers must not be handed back."""
    base = dict(
        tx_amount=Decimal("42.50"), tx_currency="USD", tx_date="2026-04-15",
        tx_vendor="STAPLES NYC", receipt_currency="EUR",
        receipt_date="2026-04-15", receipt_vendor="Staples",
        receipt_reference=None,
    )
    before = call_key("judge_fx_match", {**base, "receipt_amount": Decimal("38.00")})
    after = call_key("judge_fx_match", {**base, "receipt_amount": Decimal("39.00")})
    assert before != after


def test_the_same_call_keys_the_same_across_processes():
    """Keys are persisted, so they must not depend on anything
    process-local (a dict's insertion order, an object's id)."""
    a = call_key("judge_fx_match", {"tx_vendor": "X", "tx_amount": Decimal("1.00")})
    b = call_key("judge_fx_match", {"tx_amount": Decimal("1.00"), "tx_vendor": "X"})
    assert a == b


def test_no_client_stays_no_client():
    """The judgment layer reads `client is None` as "leave it for a
    human". A wrapper around None would silently defeat that."""
    assert JudgmentCache().wrap(None) is None


def test_the_wrapper_is_invisible_to_non_judgment_calls():
    """Extraction and categorization must pass straight through, or the
    proxy would quietly disable OCR."""
    mock = MockLLMClient(extraction_responses=[_eur_receipt()])
    wrapped = JudgmentCache().wrap(mock)
    assert wrapped.extract_receipt(file_name="a.pdf", text="x").total == "38.00"


def test_a_model_change_re_buys_the_judgment():
    """A verdict is only as good as the model that gave it. When the
    deployment moves to a stronger model (as the vision path did on
    2026-08-24) the old model's answers must not be served forever."""
    kwargs = {"tx_vendor": "STAPLES NYC", "tx_amount": Decimal("42.50")}
    assert (
        call_key("judge_fx_match", kwargs, "gpt-4o-mini")
        != call_key("judge_fx_match", kwargs, "gpt-5-mini")
    )


def test_the_wrapper_adopts_the_clients_model():
    """The model reaches the key by being read off the live client, so
    nothing has to remember to pass it in."""

    class _Client:
        model = "gpt-5-mini"

    cache = JudgmentCache()
    cache.wrap(_Client())
    assert cache._model == "gpt-5-mini"


def test_a_rematch_does_not_discard_another_writers_judgments(
    client, monkeypatch
):
    """The match runs for minutes on a row read before it started. A
    re-match that commits MEANWHILE paid for entries of its own, and
    overwriting the key wholesale would throw them away and re-buy them
    later.

    The other writer has to land mid-flight to be a real test: injected
    before our read it would simply be part of our own cache, which is
    why this patches `match_month` to commit it while we match.
    """
    mock = _mock([_eur_receipt()])
    _wire(monkeypatch, mock)
    batch_id = _create_batch(client)
    _attach(client, batch_id)

    from expense_recon.matching import deterministic as det

    real_match = det.match_month
    fired = []

    def _match_then_another_writer_commits(*args, **kwargs):
        outcome = real_match(*args, **kwargs)
        if not fired:
            fired.append(True)
            with RunStore(client._data_root / "recon-web.sqlite") as store:
                run = store.get_run(batch_id)
                snapshot = dict(run.snapshot)
                judgments = dict(snapshot.get("llm_judgments") or {})
                judgments["from-another-writer"] = {
                    "is_match": False,
                    "same_purchase_confidence": 0.1,
                    "implied_rate": None,
                    "converted_amount": None,
                    "reasoning": "someone else paid for this",
                }
                snapshot["llm_judgments"] = judgments
                store.update_run_snapshot(batch_id, snapshot)
        return outcome

    monkeypatch.setattr(det, "match_month", _match_then_another_writer_commits)

    _rematch(client, batch_id)

    assert fired, "the mid-flight writer never ran; the test proves nothing"
    run, _txs = _run_and_txs(client, batch_id)
    stored = (run.snapshot or {}).get("llm_judgments") or {}
    assert "from-another-writer" in stored, (
        "a concurrent writer's judgments were discarded at commit"
    )
    assert len(stored) > 1, "our own judgments were lost instead"
