"""'Confirm all matched' follows the owner's pairing rule (item 101).

The button (`POST /api/runs/{id}/decisions/confirm-matched`) confirmed every
pending row in the matcher's raw matched list. Measured live on 2026-09-17,
read-only: July would have confirmed 27 rows that are all workbook-yellow
(`turn: posted`, which never offers Confirm); August all 7 open pairs,
among them BASE44 50.00 at vendor 40 (the Base44/Lovable wrong-pair shape),
two `fx_reference` pairs and one `probable` pair.

It now confirms only the pairs the owner's rule lets through without a closer
look (item 76, `service.confirmable_pair`), whatever the category says, and
`summary.n_confirm_matched` on the run payload is that number. A booked row
is never confirmed by the bulk confirm either.

Route-level: every test drives the real routes through the app's TestClient.
Fixtures are copied from `tests/test_self_confirm.py`, not imported.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
RUN = "month"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


# ── a seeded month: every pair shaped exactly as the case needs ─────


def _tx(tx_id, day, vendor, entry_status=None):
    return Transaction(
        transaction_id=tx_id, legal_entity_id="le1", account_id="card-2838",
        transaction_date=date(2026, 8, day), posting_date=None,
        amount=Decimal("50.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
        entry_status=entry_status,
    )


def _rec(doc_id, day, vendor, source=ClassificationSource.LINE):
    """`LINE` is a trusted tier (category `ready`); `VENDOR` reads `check`."""
    return Receipt(
        document_id=doc_id, legal_entity_id="le1",
        detected_date=date(2026, 8, day), detected_total=Decimal("50.00"),
        detected_currency="USD", detected_vendor=vendor,
        detected_reference="R" + doc_id,
        line_items=(LineItem(
            description="item", line_total=Decimal("50.00"),
            categorization=Categorization(
                category="Software", zoho_account="6100 Software",
                confidence=1.0, source=source,
            ),
        ),),
    )


def _pair(tx_id, doc_id, match_type=MatchType.EXACT, vendor=1.0, review=False):
    return Match(
        transaction_id=tx_id, document_id=doc_id, match_type=match_type,
        confidence=0.6 if review else 0.99, reason="seeded",
        requires_review=review, score=60 if review else 95,
        amount_score=1.0, date_score=1.0, vendor_score=vendor,
    )


def _seed(client, cases):
    """`cases`: (tx_id, day, vendor, entry_status, category source, match
    type, vendor score). Each charge gets one receipt and one matched pair.
    Seeded straight into the store, so no re-match (and no self-confirm)
    has run: every row starts pending."""
    txs, recs, matches = [], [], []
    for tx_id, day, vendor, entry, source, match_type, vendor_score in cases:
        doc = "r-" + tx_id
        txs.append(_tx(tx_id, day, vendor, entry))
        recs.append(_rec(doc, day, vendor.title(), source))
        matches.append(_pair(tx_id, doc, match_type, vendor_score))
    outcome = MatchOutcome(
        matches=matches, unmatched_transactions=[], unmatched_receipts=[],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        store.create_run(
            run_id=RUN, created_at="2026-09-01T00:00:00+00:00",
            label="August 2026", operator=None, summary={},
            snapshot=snapshot_to_dict(txs, recs, outcome, []), config={},
            work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
        )
    finally:
        store.close()


CLEAN = ("t-clean", 3, "GOOGLE", None, ClassificationSource.LINE, MatchType.EXACT, 1.0)
BOOKED = ("t-booked", 4, "ADOBE", "posted", ClassificationSource.LINE, MatchType.EXACT, 1.0)
VENDOR_40 = ("t-base44", 5, "BASE44", None, ClassificationSource.LINE, MatchType.EXACT, 0.40)
FX = ("t-fx", 6, "ANTHROPIC", None, ClassificationSource.LINE, MatchType.FX_REFERENCE, 1.0)
PROBABLE = ("t-probable", 7, "AMAZON", None, ClassificationSource.LINE, MatchType.PROBABLE, 1.0)
CHECK = ("t-check", 8, "OPENAI", None, ClassificationSource.VENDOR, MatchType.EXACT, 0.75)


def _view(client, run_id=RUN):
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, run_id=RUN):
    return {r["transaction_id"]: r for r in _view(client, run_id)["rows"]}


def _confirm_matched(client, run_id=RUN):
    resp = client.post(f"/api/runs/{run_id}/decisions/confirm-matched")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _decide(client, tx_id, status, doc=None, run_id=RUN):
    resp = client.post(f"/api/runs/{run_id}/decisions", json={
        "transaction_id": tx_id, "status": status, "chosen_document_id": doc,
    })
    assert resp.status_code == 200, resp.text


# ── the rule, through the button ────────────────────────────────────


def test_a_booked_row_is_not_confirmed(client):
    """July's shape: a yellow row is booked, its turn is `posted`, and the
    button leaves it alone even though the pair itself is clean."""
    _seed(client, [BOOKED, CLEAN])
    assert _rows(client)["t-booked"]["turn"] == "posted"

    body = _confirm_matched(client)
    assert body["confirmed"] == 1
    rows = _rows(client)
    assert (rows["t-booked"]["status"], rows["t-booked"]["turn"]) == ("pending", "posted")
    assert rows["t-clean"]["status"] == "confirmed"


def test_a_vendor_40_exact_pair_is_not_confirmed(client):
    """August's BASE44 50.00: same amount, same day, the vendor agrees at 40.
    Stays the reviewer's call, and counts as left by the rule."""
    _seed(client, [VENDOR_40])
    (cand,) = _rows(client)["t-base44"]["candidates"]
    assert (cand["match_type"], cand["vendor_pct"]) == ("exact", 40)

    body = _confirm_matched(client)
    assert (body["confirmed"], body["skipped_rule"]) == (0, 1)
    row = _rows(client)["t-base44"]
    assert (row["status"], row["turn"]) == ("pending", "decide")


def test_fx_and_probable_pairs_are_not_confirmed(client):
    """Exact pairs only (owner ruling 2026-09-16): a pair matched through a
    reference rate or inside the tip band stays for a person."""
    _seed(client, [FX, PROBABLE])
    body = _confirm_matched(client)
    assert (body["confirmed"], body["skipped_rule"]) == (0, 2)
    rows = _rows(client)
    for tx in ("t-fx", "t-probable"):
        assert (rows[tx]["status"], rows[tx]["turn"]) == ("pending", "decide")


def test_a_clean_exact_pair_is_confirmed_even_when_its_category_is_check(client):
    """Confirming a pairing is not a category verdict: vendor 75 exact pair,
    category guessed from the vendor (`check`). Confirmed, as a person's
    confirm (they pressed the button), and the category keeps asking."""
    _seed(client, [CHECK])
    row = _rows(client)["t-check"]
    assert row["review"]["state"] == "check"
    assert row["candidates"][0]["vendor_pct"] == 75

    body = _confirm_matched(client)
    assert (body["confirmed"], body["skipped_rule"], body["remaining"]) == (1, 0, 0)
    row = _rows(client)["t-check"]
    assert (row["status"], row["decided_by"]) == ("confirmed", "reviewer")
    assert "decided_rule" not in row
    assert row["review"]["state"] == "check"


def test_a_reviewers_earlier_reject_is_never_stomped(client):
    """A clean pair a person turned down stays turned down, and it is not
    counted as left by the rule: it is not anyone's turn any more."""
    _seed(client, [CLEAN])
    _decide(client, "t-clean", "rejected")
    assert _view(client)["summary"]["n_confirm_matched"] == 0

    body = _confirm_matched(client)
    assert (body["confirmed"], body["skipped_rule"]) == (0, 0)
    row = _rows(client)["t-clean"]
    assert (row["status"], row["decided_by"]) == ("rejected", "reviewer")


def test_n_confirm_matched_is_what_the_route_then_confirms(client):
    """The number the button shows is the number it confirms, and after the
    click it reads 0; every other open pairing is reported as left."""
    _seed(client, [CLEAN, BOOKED, VENDOR_40, FX, PROBABLE, CHECK])
    before = _view(client)["summary"]
    assert before["n_confirm_matched"] == 2
    assert before["n_undecided"] == 5

    body = _confirm_matched(client)
    assert body["confirmed"] == before["n_confirm_matched"]
    assert body["skipped_rule"] == before["n_undecided"] - body["confirmed"]
    assert body["remaining"] == 0
    assert body["summary"]["n_confirm_matched"] == 0
    assert _view(client)["summary"]["n_confirm_matched"] == 0
    confirmed = {tx for tx, r in _rows(client).items() if r["status"] == "confirmed"}
    assert confirmed == {"t-clean", "t-check"}


def test_the_per_call_cap_reports_the_remainder(client, monkeypatch):
    """Like confirm-ready: past the cap, confirm the cap and say how many
    are left rather than truncating in silence."""
    monkeypatch.setattr("expense_recon.web.app._BULK_DECISION_LIMIT", 1)
    _seed(client, [CLEAN, CHECK])
    body = _confirm_matched(client)
    assert (body["confirmed"], body["remaining"]) == (1, 1)
    assert body["summary"]["n_confirm_matched"] == 1


# ── the other two bulk confirms and a booked row ────────────────────


def test_confirm_n_shown_skips_a_booked_row_and_reject_is_unchanged(client):
    """`POST .../decisions/bulk` confirming explicit ids never confirms a
    booked row; rejecting the same ids works as before."""
    _seed(client, [BOOKED, CLEAN])
    resp = client.post(f"/api/runs/{RUN}/decisions/bulk", json={
        "transaction_ids": ["t-booked", "t-clean"], "status": "confirmed",
    })
    assert resp.status_code == 200, resp.text
    assert (resp.json()["updated"], resp.json()["skipped"]) == (1, 1)
    rows = _rows(client)
    assert (rows["t-booked"]["status"], rows["t-booked"]["turn"]) == ("pending", "posted")
    assert rows["t-clean"]["status"] == "confirmed"

    resp = client.post(f"/api/runs/{RUN}/decisions/bulk", json={
        "transaction_ids": ["t-booked"], "status": "rejected",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated"] == 1
    assert _rows(client)["t-booked"]["status"] == "rejected"


def test_confirm_ready_never_confirms_a_booked_row(client):
    """A booked row's review state is `none` however clean its category,
    so 'Confirm all Ready' already leaves it; pinned here."""
    _seed(client, [BOOKED, CLEAN])
    rows = _rows(client)
    assert rows["t-booked"]["review"]["state"] == "none"
    assert rows["t-clean"]["review"]["state"] == "ready"

    resp = client.post(f"/api/runs/{RUN}/decisions/confirm-ready")
    assert resp.status_code == 200, resp.text
    assert resp.json()["confirmed"] == 1
    rows = _rows(client)
    assert rows["t-booked"]["status"] == "pending"
    assert rows["t-clean"]["status"] == "confirmed"


# ── through a real re-match: the tool left it, the person confirms it ─


def _job_done(client, resp):
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _statement_month(client, monkeypatch):
    """One receipt (42.50, 04-15) pairing exactly with the example
    statement's STAPLES NYC 42.50 charge, no merchant registry, so the
    category is `pick` and the tool does not confirm it itself."""
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-04-15", total="42.50", currency="USD", vendor="STAPLES NYC",
        reference="", line_items=(), confidence=0.9, notes="",
    )])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "April 2026"},
    )
    _job_done(client, resp)
    batch_id = resp.json()["batch_id"]
    _job_done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG + b"a.jpg", "application/octet-stream"))],
    ))
    _job_done(client, client.post(
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
    ))
    return batch_id


def test_a_pair_the_tool_left_for_its_category_is_confirmed_by_the_button(
    client, monkeypatch
):
    batch_id = _statement_month(client, monkeypatch)
    view = _view(client, batch_id)
    row = next(r for r in view["rows"] if "STAPLES" in r["vendor"])
    assert (row["status"], row["turn"], row["review"]["state"]) == (
        "pending", "decide", "pick",
    )
    assert view["summary"]["n_confirm_matched"] == 1

    body = _confirm_matched(client, batch_id)
    assert body["confirmed"] == 1
    row = next(r for r in _view(client, batch_id)["rows"] if "STAPLES" in r["vendor"])
    assert (row["status"], row["decided_by"]) == ("confirmed", "reviewer")
