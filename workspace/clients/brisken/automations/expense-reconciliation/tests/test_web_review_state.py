"""Review-by-exception classification (2026-07-27).

Every workbench row carries a server-computed review = {state, reason} so the
SPA can group the exceptions and bulk-confirm the rest with no logic of its
own: ready / check / pick / none. The matrix below is the contract; the
adversarial-verify findings that shaped it are called out where they bite
(partial-uncategorization must be caught structurally; a confirmed MATCH is
not a confirmed CATEGORY; Confirm-all touches only true ready rows).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.serialize import categorization_to_dict, snapshot_to_dict
from expense_recon.web.service import (
    _matched_category_review,
    ready_confirm_pairs,
    resolve_review,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


# ── builders ────────────────────────────────────────────────────────


def _cat(category="Software", account="Cloud Payable",
         source=ClassificationSource.LINE, decision=None):
    return Categorization(
        category=category, zoho_account=account, confidence=1.0,
        source=source, decision=decision,
    )


def _rec(*cats, doc="r1"):
    """One receipt, one line per arg (a Categorization or None)."""
    return Receipt(
        document_id=doc, legal_entity_id="le",
        detected_date=date(2026, 4, 7), detected_total=Decimal("10.00"),
        detected_currency="USD", detected_vendor="V",
        line_items=tuple(
            LineItem(description=f"item{i}", line_total=Decimal("10.00"),
                     categorization=c)
            for i, c in enumerate(cats)
        ),
    )


def _rv(matched_rec=None, *, is_posted=False, effective_bucket="reconciled",
        status="pending", overrides=None, charge_category=None):
    return resolve_review(
        is_posted=is_posted, effective_bucket=effective_bucket, status=status,
        matched_rec=matched_rec, overrides=overrides or {},
        charge_category=charge_category,
    )


# ── terminal / non-target rows -> none ──────────────────────────────


def test_posted_is_none():
    assert _rv(_rec(_cat()), is_posted=True)["state"] == "none"


def test_refund_is_none():
    assert _rv(effective_bucket="refund")["state"] == "none"


def test_rejected_is_none():
    assert _rv(_rec(_cat()), status="rejected")["state"] == "none"


# ── stable reason_code for the SPA to localize (EN + PT) ────────────


def test_reason_codes():
    assert _rv(effective_bucket="review")["reason_code"] == "uncertain_match"
    assert _rv(_rec(None))["reason_code"] == "uncategorized"
    assert _rv(_rec(_cat(source=ClassificationSource.LINE), None))["reason_code"] == "partial_uncategorized"
    assert _rv(_rec(_cat(decision="ai_override_heavy")))["reason_code"] == "category_account_mismatch"
    assert _rv(_rec(_cat(source=ClassificationSource.VENDOR)))["reason_code"] == "vendor_guess"
    assert _rv(_rec(_cat(source=None)))["reason_code"] == "unknown_provenance"
    assert _rv(_rec(_cat()))["reason_code"] is None  # ready
    cc = {"category": "M", "zoho_account": "M", "source": "LEARNED"}
    assert _rv(effective_bucket="unmatched", charge_category=cc)["reason_code"] == "receiptless_suggested"
    assert _rv(effective_bucket="refund")["reason_code"] is None


# ── uncertain match -> check ────────────────────────────────────────


def test_review_bucket_is_check():
    r = _rv(effective_bucket="review")
    assert r["state"] == "check" and r["reason"]


# ── matched category quality (the pick > check > ready ladder) ───────


def test_matched_all_trusted_is_ready():
    assert _rv(_rec(_cat(source=ClassificationSource.LINE)))["state"] == "ready"


def test_matched_learned_is_ready():
    assert _rv(_rec(_cat(source=ClassificationSource.LEARNED)))["state"] == "ready"


def test_matched_fully_uncategorized_is_pick():
    # posting_category would be None (every line skipped).
    assert _rv(_rec(None))["state"] == "pick"


def test_matched_partial_skipped_line_is_pick():
    # HIGH finding: line0=LINE, line1=no categorization object. The joined
    # source reads "LINE" (all-trusted) because the skipped line contributes
    # nothing; only a structural line scan catches the gap. Must be pick, or
    # Confirm-all would ratify a row that exports "(uncategorized - assign)".
    assert _rv(_rec(_cat(source=ClassificationSource.LINE), None))["state"] == "pick"


def test_matched_partial_review_line_is_pick():
    review_line = _cat(category=None, account=None, source=ClassificationSource.REVIEW)
    assert _rv(_rec(_cat(source=ClassificationSource.LINE), review_line))["state"] == "pick"


def test_matched_ai_override_heavy_is_check():
    r = _rv(_rec(_cat(source=ClassificationSource.LINE, decision="ai_override_heavy")))
    assert r["state"] == "check" and "account" in r["reason"].lower()


def test_matched_review_unresolved_is_check():
    r = _rv(_rec(_cat(source=ClassificationSource.LINE, decision="review_unresolved")))
    assert r["state"] == "check"


def test_matched_vendor_guess_is_check():
    r = _rv(_rec(_cat(source=ClassificationSource.VENDOR)))
    assert r["state"] == "check" and "guessed" in r["reason"].lower()


def test_matched_unknown_provenance_is_check():
    # categorized but no source tier -> not trusted -> check (not vacuous ready).
    assert _rv(_rec(_cat(source=None)))["state"] == "check"


def test_kept_er_decision_stays_ready():
    # kept_er is agreement, not a disagreement -> does not force check.
    assert _rv(_rec(_cat(source=ClassificationSource.LINE, decision="kept_er")))["state"] == "ready"


# ── confirmed MATCH is not a confirmed CATEGORY (HIGH finding) ───────


def test_confirmed_but_uncategorized_is_pick_not_ready():
    assert _rv(_rec(None), status="confirmed")["state"] == "pick"


def test_confirmed_and_trusted_is_ready():
    assert _rv(_rec(_cat()), status="confirmed")["state"] == "ready"


def test_confirmed_vendor_guess_stays_check():
    assert _rv(_rec(_cat(source=ClassificationSource.VENDOR)), status="confirmed")["state"] == "check"


# ── reviewer override wins (EDITED is trusted) ──────────────────────


def test_override_is_ready():
    rec = _rec(_cat(source=ClassificationSource.VENDOR))  # would be check...
    ov = {("r1", 0): {"category": "Travel", "zoho_account": "T"}}  # ...but edited
    assert _matched_category_review(rec, ov)["state"] == "ready"


# ── receiptless ─────────────────────────────────────────────────────


def test_receiptless_with_category_is_check():
    cc = {"category": "Meals", "zoho_account": "M", "source": "LEARNED"}
    r = _rv(effective_bucket="unmatched", charge_category=cc)
    assert r["state"] == "check" and r["reason"]


def test_receiptless_no_category_is_none():
    assert _rv(effective_bucket="unmatched", charge_category=None)["state"] == "none"


# ── Confirm-all touches ONLY ready rows (safety) ────────────────────


def _tx(tid):
    return Transaction(
        transaction_id=tid, legal_entity_id="le", account_id="a",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("10.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=tid,
    )


def _run_row(snapshot):
    from expense_recon.web.store import RunRow
    return RunRow(
        run_id="run1", created_at="2026-07-20T00:00:00", label="t",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir="", llm_enabled=False, has_coa=False,
    )


def test_ready_confirm_pairs_excludes_check_and_pick():
    txs = [_tx("A"), _tx("B"), _tx("C")]
    recs = [
        _rec(_cat(source=ClassificationSource.LINE), doc="rA"),           # ready
        _rec(_cat(source=ClassificationSource.VENDOR), doc="rB"),         # check
        _rec(None, doc="rC"),                                             # pick
    ]
    outcome = MatchOutcome(matches=[
        Match(transaction_id="A", document_id="rA", match_type=MatchType.EXACT, confidence=1.0, reason="x"),
        Match(transaction_id="B", document_id="rB", match_type=MatchType.EXACT, confidence=1.0, reason="x"),
        Match(transaction_id="C", document_id="rC", match_type=MatchType.EXACT, confidence=1.0, reason="x"),
    ])
    snap = snapshot_to_dict(txs, recs, outcome, [])
    pairs = ready_confirm_pairs(_run_row(snap), {}, {})
    assert pairs == [("A", "rA")]  # ONLY the ready row, never B (check) / C (pick)


# ── wiring: build_view row carries review + the run adjudication flag ─


def test_build_view_row_carries_review_and_adjudication_flag():
    from expense_recon.web.service import build_view
    tx = _tx("A")
    rec = _rec(_cat(source=ClassificationSource.LINE, decision="ai_override_heavy"), doc="rA")
    outcome = MatchOutcome(matches=[
        Match(transaction_id="A", document_id="rA", match_type=MatchType.EXACT, confidence=1.0, reason="x"),
    ])
    view = build_view(_run_row(snapshot_to_dict([tx], [rec], outcome, [])), {}, {})
    row = next(r for r in view["rows"] if r["transaction_id"] == "A")
    assert row["review"]["state"] == "check"          # ai_override_heavy mismatch
    assert view["adjudication_available"] is True     # a .decision was present


def test_adjudication_flag_false_without_decision():
    from expense_recon.web.service import build_view
    tx = _tx("A")
    rec = _rec(_cat(source=ClassificationSource.LINE), doc="rA")  # decision=None
    outcome = MatchOutcome(matches=[
        Match(transaction_id="A", document_id="rA", match_type=MatchType.EXACT, confidence=1.0, reason="x"),
    ])
    view = build_view(_run_row(snapshot_to_dict([tx], [rec], outcome, [])), {}, {})
    assert view["adjudication_available"] is False


# ── endpoint smoke: confirm-ready is 200 and never posts non-ready ──


def test_confirm_ready_endpoint_shape_and_safety(tmp_path):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from expense_recon.web.app import create_app

    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/api/runs",
            files={
                "statement": ("s.csv", (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv"),
                "receipts": ("r.csv", (EXAMPLES / "receipts.example.csv").read_bytes(), "text/csv"),
            },
            data={"account_id": "amex-9001", "account_card_currency": "USD"},
        )
        run_id = c.get(f"/jobs/{resp.json()['job_id']}").json()["run_id"]
        pre = c.get(f"/api/runs/{run_id}").json()["rows"]
        ready_pending = [
            row for row in pre
            if row["review"]["state"] == "ready" and row["status"] == "pending"
        ]
        r = c.post(f"/api/runs/{run_id}/decisions/confirm-ready")
        assert r.status_code == 200
        body = r.json()
        assert {"ok", "confirmed", "remaining", "summary"} <= set(body)
        # It confirmed exactly the ready+pending rows, no more.
        assert body["confirmed"] == len(ready_pending)
        # Safety: the bulk action never confirmed a check / pick row.
        post = c.get(f"/api/runs/{run_id}").json()["rows"]
        assert all(
            row["status"] != "confirmed" or row["review"]["state"] == "ready"
            for row in post
        )
        assert c.post("/api/runs/nope0000/decisions/confirm-ready").status_code == 404
