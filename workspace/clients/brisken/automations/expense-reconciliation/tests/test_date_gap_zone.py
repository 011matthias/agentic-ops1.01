"""Item 80 (note #44): a one-day gap is not a date mismatch.

The SPA printed "date mismatch" whenever the chosen candidate's `date_pct`
was below 99, which is any gap of one day or more. On July 2026 that put the
chip, and a place in the Warnings filter, on six reconciled rows that the
labels call right: every one sat one day from its receipt, the ordinary
midnight / time-zone / charged-at-shipment case.

Owner ruling 2026-09-16: gap = the charge's transaction date minus the
receipt's date, in calendar days. -1..+1 is no signal (`none`), +2..+7 and
-3..-2 are a neutral note (`lag`), anything else is `mismatch`. The matcher
does not change, so these tests pin the LABEL: every `rows[].candidates[]`
entry carries `date_gap_days` and `date_gap_zone`, both absent (not null)
when either date is missing, and `date_pct` stays exactly what it was.

Route-level through `GET /api/runs/{id}`, on a seeded snapshot, plus the
reviewer's hand match through `POST /api/runs/{id}/manual-match`, because
that candidate is built by a second emission site with `date_pct: None`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    DATE_GAP_ZONES,
    date_gap_zone,
)
from expense_recon.web.store import RunStore  # noqa: E402

CHARGE_DAY = date(2026, 4, 15)

# charge id -> (receipt date, vendor, amount). The gap is charge minus
# receipt, so a receipt dated BEFORE the charge is a positive gap.
SEEDED = {
    "t_0": (date(2026, 4, 15), "ZERO CAFE", "10.00"),
    "t_plus1": (date(2026, 4, 14), "ANTHROPIC", "47.23"),
    "t_minus1": (date(2026, 4, 16), "LATE TAB", "24.88"),
    "t_plus3": (date(2026, 4, 12), "AMAZON SHIPPED", "315.56"),
    "t_minus3": (date(2026, 4, 18), "PRINTED LATER", "51.38"),
    "t_plus9": (date(2026, 4, 6), "FAR AWAY", "99.10"),
    "t_nodate": (None, "UNDATED SHOP", "12.34"),
}


def _tx(tx_id: str, amount: str, vendor: str, day: date | None = CHARGE_DAY):
    return Transaction(
        transaction_id=tx_id, legal_entity_id="le1", account_id="amex-usd",
        transaction_date=day, posting_date=None, amount=Decimal(amount),
        transaction_currency="USD", account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def _rec(doc_id: str, day: date | None, vendor: str, amount: str) -> Receipt:
    return Receipt(
        document_id=doc_id, legal_entity_id="le1", detected_date=day,
        detected_total=Decimal(amount), detected_currency="USD",
        detected_vendor=vendor, detected_reference="R" + doc_id,
    )


def _match(tx_id: str, doc_id: str) -> Match:
    return Match(
        transaction_id=tx_id, document_id=doc_id,
        match_type=MatchType.PROBABLE, confidence=0.8, reason="seeded",
        score=80, amount_score=1.0, date_score=0.8, vendor_score=1.0,
    )


def _seed(tmp_path) -> None:
    transactions, receipts, matches = [], [], []
    for tx_id, (rec_day, vendor, amount) in SEEDED.items():
        doc_id = "d" + tx_id[1:]
        transactions.append(_tx(tx_id, amount, vendor))
        receipts.append(_rec(doc_id, rec_day, vendor, amount))
        matches.append(_match(tx_id, doc_id))
    # A charge with no transaction date, against a dated receipt.
    transactions.append(_tx("t_undated_charge", "7.77", "NO DATE", day=None))
    receipts.append(_rec("d_undated_charge", CHARGE_DAY, "NO DATE", "7.77"))
    matches.append(_match("t_undated_charge", "d_undated_charge"))
    # Left unmatched on both sides, for the reviewer's hand match: the
    # receipt is dated 4 days before the charge.
    transactions.append(_tx("t_manual", "63.00", "HAND PICKED"))
    receipts.append(_rec("d_manual", date(2026, 4, 11), "HAND PICKED", "63.00"))

    outcome = MatchOutcome(
        matches=matches, unmatched_transactions=["t_manual"],
        unmatched_receipts=["d_manual"], ambiguous=[],
    )
    snapshot = snapshot_to_dict(transactions, receipts, outcome, [])
    store = RunStore(tmp_path / "recon-web.sqlite")
    store.create_run(
        run_id="gap-run", created_at="2026-09-16T00:00:00", label="gaps",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir=str(tmp_path), llm_enabled=False, has_coa=False,
    )
    store.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _seed(tmp_path)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _candidate(view: dict, tx_id: str) -> dict:
    row = next(r for r in view["rows"] if r["transaction_id"] == tx_id)
    (cand,) = row["candidates"]
    return cand


@pytest.mark.parametrize(
    "tx_id, days, zone",
    [
        ("t_0", 0, "none"),
        ("t_plus1", 1, "none"),
        ("t_minus1", -1, "none"),
        ("t_plus3", 3, "lag"),
        ("t_minus3", -3, "lag"),
        ("t_plus9", 9, "mismatch"),
    ],
    ids=["0d", "plus1d", "minus1d", "plus3d", "minus3d", "plus9d"],
)
def test_a_dated_pair_carries_its_gap_and_zone(client, tx_id, days, zone):
    cand = _candidate(client.get("/api/runs/gap-run").json(), tx_id)
    assert cand["date_gap_days"] == days, cand
    assert cand["date_gap_zone"] == zone, cand


def test_a_missing_date_leaves_both_fields_absent(client):
    view = client.get("/api/runs/gap-run").json()
    for tx_id in ("t_nodate", "t_undated_charge"):
        cand = _candidate(view, tx_id)
        assert "date_gap_days" not in cand, (tx_id, cand)
        assert "date_gap_zone" not in cand, (tx_id, cand)


def test_the_matcher_scores_are_untouched(client):
    """The label only: `date_pct` still reports the matcher's own score."""
    view = client.get("/api/runs/gap-run").json()
    for tx_id in SEEDED:
        assert _candidate(view, tx_id)["date_pct"] == 80, tx_id


def test_a_hand_match_carries_the_gap(client):
    """The second emission site: a manual match synthesizes its candidate
    with `date_pct: None`, and still carries the gap it actually has."""
    before = _candidate_or_none(client.get("/api/runs/gap-run").json(), "t_manual")
    assert before is None
    resp = client.post(
        "/api/runs/gap-run/manual-match",
        json={"transaction_id": "t_manual", "document_id": "d_manual"},
    )
    assert resp.status_code == 200, resp.text
    cand = _candidate(client.get("/api/runs/gap-run").json(), "t_manual")
    assert cand["match_type"] == "manual"
    assert cand["date_pct"] is None
    assert cand["date_gap_days"] == 4
    assert cand["date_gap_zone"] == "lag"


def _candidate_or_none(view: dict, tx_id: str) -> dict | None:
    row = next(r for r in view["rows"] if r["transaction_id"] == tx_id)
    return row["candidates"][0] if row["candidates"] else None


@pytest.mark.parametrize(
    "days, zone",
    [(-4, "mismatch"), (-3, "lag"), (-2, "lag"), (-1, "none"), (0, "none"),
     (1, "none"), (2, "lag"), (7, "lag"), (8, "mismatch"), (-30, "mismatch")],
)
def test_zone_bounds_are_the_owner_ruling(days, zone):
    """The edges of the one constant, so a later edit to it is a visible
    change to the ruling rather than a quiet one."""
    assert date_gap_zone(days) == zone
    assert {z for z, _lo, _hi in DATE_GAP_ZONES} == {"none", "lag"}
