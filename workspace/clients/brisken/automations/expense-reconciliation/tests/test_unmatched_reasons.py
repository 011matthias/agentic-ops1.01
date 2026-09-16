"""Items 83 + 75: the unmatched lists tell the truth (notes #40, #46).

Route-level through the FastAPI app on a seeded month:

* a DECIDED duplicate copy leaves `unmatched_receipts`, the hand-match picker
  and `n_unmatched_rec` for `copies_set_aside` / `n_copies_set_aside`, keeps
  its marker, and is no near miss for another charge; a "Not a copy" ruling
  returns both receipts as ordinary unmatched receipts; a copy a reviewer
  hand-matched renders as that match;
* every receipt still sits in exactly one place (held, unmatched, settled
  outside, set aside), and the counts add up to `n_receipts`;
* `duplicate_groups` and `duplicate_receipts` keep their by-index pairing;
* every unmatched receipt and charge carries a `reason_code`, and no other
  row does.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.duplicates import duplicate_group_id  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.unmatched_reasons import (  # noqa: E402
    CHARGE_REASON_CODES,
    RECEIPT_REASON_CODES,
    charge_reason_code,
    receipt_reason_code,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


def _tx(tid, d, vendor, amount, **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=d, posting_date=None, amount=Decimal(amount),
        transaction_currency="USD", account_card_currency="USD",
        vendor_from_statement=vendor, card_last4="2838", **kw,
    )


def _rc(doc, vendor, total, d, payment_mode=None) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=d,
        detected_total=Decimal(total), detected_currency="USD",
        detected_vendor=vendor, payment_mode=payment_mode,
    )


# The statement runs 2026-04-01 .. 2026-04-30 (its first and last charge).
CHARGES = [
    _tx("t_open", date(2026, 4, 1), "AMAZON", "180.00"),
    _tx("t_cafe", date(2026, 4, 15), "CAFE", "20.00"),
    _tx("t_cafe2", date(2026, 4, 16), "CAFE", "20.50"),
    _tx("t_booked", date(2026, 4, 10), "YELLOW ROW", "50.00", entry_status="posted"),
    _tx("t_fee", date(2026, 4, 30), "ANNUAL MEMBERSHIP FEE", "150.00", row_type="fee"),
]
RECEIPTS = [
    # m1 settled t_cafe; m2 is its copy (vendor + date + total), set aside
    _rc("m1", "Cafe", "20.00", date(2026, 4, 15)),
    _rc("m2", "Cafe", "20.00", date(2026, 4, 15)),
    # p1/p2: a copy pair nothing settled; p2 is set aside, p1 stays unmatched
    _rc("p1", "Pressmaster", "135.00", date(2026, 4, 20)),
    _rc("p2", "Pressmaster", "135.00", date(2026, 4, 20)),
    _rc("r_card", "OpenAI", "80.12", date(2026, 4, 12), "BCS Chase Visa ...9693"),
    _rc("r_loaded", "Store", "11.00", date(2026, 4, 12), "Visa Debit ...2838"),
    _rc("r_tender", "Moghul Mahal", "241.80", date(2026, 4, 12), "EC-Karte"),
    _rc("r_edge", "Lovable", "25.00", date(2026, 4, 30)),
    _rc("r_before", "Anthropic", "100.00", date(2026, 3, 21)),
    _rc("r_old", "360Crossmedia", "900.00", date(2026, 1, 10)),
]
EXPECTED_RECEIPT_REASONS = {
    "p1": "no_charge_on_any_loaded_statement",
    "r_card": "card_statement_not_loaded",
    "r_loaded": "no_charge_on_any_loaded_statement",
    "r_tender": "not_a_card_charge",
    "r_edge": "charge_in_neighbouring_period",
    "r_before": "charge_in_neighbouring_period",
    "r_old": "no_charge_on_any_loaded_statement",
}
GID_M = duplicate_group_id("receipt", ["m1", "m2"])
GID_P = duplicate_group_id("receipt", ["p1", "p2"])


def _snapshot() -> dict:
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_cafe", document_id="m1", match_type=MatchType.EXACT,
            confidence=0.99, reason="exact", score=95,
            amount_score=1.0, date_score=1.0, vendor_score=1.0,
        )],
        unmatched_transactions=["t_open", "t_cafe2", "t_booked", "t_fee"],
        unmatched_receipts=[r.document_id for r in RECEIPTS if r.document_id != "m1"],
    )
    return snapshot_to_dict(CHARGES, RECEIPTS, outcome, [])


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(client, resolutions=None, decisions=None) -> dict:
    db = RunStore(client._data_root / "recon-web.sqlite")
    db.create_run(
        run_id="run1", created_at="2026-05-02T00:00:00", label="April 2026",
        operator=None, summary={}, snapshot=_snapshot(), config={},
        work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    for gid, resolution in (resolutions or {}).items():
        db.set_duplicate_resolution("run1", gid, resolution, "2026-05-02T00:00:00")
    for tx_id, doc in (decisions or {}).items():
        db.set_decision("run1", tx_id, "confirmed", doc, "2026-05-02T00:00:00")
    db.close()
    resp = client.get("/api/runs/run1")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _ids(items) -> set[str]:
    return {i["document_id"] for i in items}


# ── item 83: a decided copy leaves the open lists ───────────────────────


def test_a_decided_copy_leaves_every_open_list_for_the_set_aside_record(client):
    view = _seed(client)
    assert _ids(view["copies_set_aside"]) == {"m2", "p2"}
    assert not _ids(view["unmatched_receipts"]) & {"m2", "p2"}
    assert not _ids(view["assignable_receipts"]) & {"m2", "p2"}, "the picker offered a copy"
    for copy in view["copies_set_aside"]:
        assert copy["duplicate"]["is_extra"] is True
        assert copy["reason_code"] == "duplicate_copy"
    s = view["summary"]
    assert s["n_copies_set_aside"] == 2
    assert s["n_unmatched_rec"] == len(view["unmatched_receipts"]) == 7
    # n_duplicate_copies keeps its question: every redundant copy
    assert s["n_duplicate_copies"] == 2


def test_every_receipt_sits_in_exactly_one_place_and_the_counts_add_up(client):
    view = _seed(client)
    s = view["summary"]
    held = {
        r["chosen_document_id"] for r in view["rows"]
        if r["effective_bucket"] in ("reconciled", "review") and r["chosen_document_id"]
    }
    unmatched, copies = _ids(view["unmatched_receipts"]), _ids(view["copies_set_aside"])
    assert not (held & unmatched or held & copies or unmatched & copies)
    assert held | unmatched | copies == {r.document_id for r in RECEIPTS}
    assert s["n_receipts"] == (
        s["n_receipts_matched"] + s["n_unmatched_rec"]
        + s["n_settled_outside"] + s["n_copies_set_aside"]
    )
    assert s["n_receipts_matched"] == len(held) == 1
    assert s["invariant_ok"] is True


def test_a_set_aside_copy_is_no_near_miss_for_another_charge(client):
    """t_cafe2 (20.50) sits 0.50 from the set-aside copy m2 (20.00), the only
    CAFE receipt not holding a charge. Offering it would invite the reviewer
    to settle a second charge with a copy of a receipt already used."""
    view = _seed(client)
    row = next(r for r in view["rows"] if r["transaction_id"] == "t_cafe2")
    assert row["near_miss"] is None


def test_not_a_copy_returns_both_receipts_as_ordinary_unmatched_receipts(client):
    view = _seed(client, resolutions={GID_P: "ignore"})
    assert _ids(view["copies_set_aside"]) == {"m2"}
    by_id = {r["document_id"]: r for r in view["unmatched_receipts"]}
    assert {"p1", "p2"} <= set(by_id)
    assert by_id["p1"]["duplicate"] is None and by_id["p2"]["duplicate"] is None
    assert {"p1", "p2"} <= _ids(view["assignable_receipts"])
    assert by_id["p2"]["reason_code"] != "duplicate_copy"


def test_a_copy_a_reviewer_hand_matched_renders_as_that_match(client):
    view = _seed(client, decisions={"t_open": "p2"})
    assert "p2" not in _ids(view["copies_set_aside"])
    row = next(r for r in view["rows"] if r["transaction_id"] == "t_open")
    assert row["chosen_document_id"] == "p2"
    assert "reason_code" not in row


def test_the_duplicate_lists_keep_their_by_index_pairing(client):
    view = _seed(client)
    groups = [g for g in view["duplicate_groups"] if g["kind"] == "receipt"]
    assert len(groups) == len(view["duplicate_receipts"]) == 2
    assert [_ids(grp) for grp in view["duplicate_receipts"]] == [
        set(g["members"]) for g in groups
    ]


# ── item 75: every unmatched receipt and charge says why ────────────────


def test_every_unmatched_receipt_carries_its_reason(client):
    view = _seed(client)
    assert {
        r["document_id"]: r["reason_code"] for r in view["unmatched_receipts"]
    } == EXPECTED_RECEIPT_REASONS
    assert all("reason_code" not in a for a in view["assignable_receipts"])


def test_every_unmatched_charge_carries_its_reason_and_no_other_row_does(client):
    view = _seed(client)
    by_tx = {r["transaction_id"]: r for r in view["rows"]}
    assert by_tx["t_fee"]["reason_code"] == "not_a_purchase"
    assert by_tx["t_booked"]["reason_code"] == "already_booked"
    assert by_tx["t_open"]["reason_code"] == "no_receipt_found"
    assert by_tx["t_cafe2"]["reason_code"] == "no_receipt_found"
    assert "reason_code" not in by_tx["t_cafe"], "a reconciled row has nothing to explain"
    assert {
        t["transaction_id"]: t["reason_code"] for t in view["unmatched_transactions"]
    } == {
        tx_id: row["reason_code"] for tx_id, row in by_tx.items()
        if row["effective_bucket"] == "unmatched"
    }


# ── the classifier's rules, one at a time ───────────────────────────────


APRIL = (date(2026, 4, 1), date(2026, 4, 30))


@pytest.mark.parametrize(("d", "mode", "cards", "elsewhere", "code"), [
    (date(2026, 4, 12), None, {"2838"}, True, "charge_in_neighbouring_period"),
    (date(2026, 4, 12), "DEBIT MASTERCARD", {"2838"}, False, "not_a_card_charge"),
    (date(2026, 4, 30), "EC-Karte", {"2838"}, False, "not_a_card_charge"),
    (date(2026, 4, 12), "Visa Debit ...2838", {"2838"}, False,
     "no_charge_on_any_loaded_statement"),
    (date(2026, 4, 30), "Visa ...9129", {"2838"}, False, "charge_in_neighbouring_period"),
    (date(2026, 4, 2), None, {"2838"}, False, "charge_in_neighbouring_period"),
    (date(2026, 4, 3), None, {"2838"}, False, "no_charge_on_any_loaded_statement"),
    (date(2026, 5, 31), None, {"2838"}, False, "charge_in_neighbouring_period"),
    (date(2026, 6, 1), None, {"2838"}, False, "no_charge_on_any_loaded_statement"),
    (date(2026, 3, 1), None, {"2838"}, False, "charge_in_neighbouring_period"),
    (date(2026, 2, 28), None, {"2838"}, False, "no_charge_on_any_loaded_statement"),
    (date(2026, 4, 12), "Visa ...9693", {"2838"}, False, "card_statement_not_loaded"),
    (None, "Visa ...9693", set(), False, "card_statement_not_loaded"),
    (None, None, set(), False, "no_charge_on_any_loaded_statement"),
])
def test_receipt_reason_rules(d, mode, cards, elsewhere, code):
    receipt = _rc("x", "V", "1.00", d, mode)
    assert code in RECEIPT_REASON_CODES
    assert receipt_reason_code(
        receipt, loaded_cards=cards, period=APRIL, settled_elsewhere=elsewhere,
    ) == code


def test_no_period_means_no_date_reason():
    receipt = _rc("x", "V", "1.00", date(2026, 4, 30))
    assert receipt_reason_code(
        receipt, loaded_cards=set(), period=None,
    ) == "no_charge_on_any_loaded_statement"


@pytest.mark.parametrize(("row_type", "entry_status", "candidates", "code"), [
    ("fee", "posted", [{"held_by": "t9"}], "not_a_purchase"),
    ("purchase", "posted", [{"held_by": "t9"}], "receipt_held_by_another_charge"),
    ("purchase", "posted", [{"held_by": "t9"}, {}], "already_booked"),
    ("purchase", "subscription", [], "no_receipt_found"),
    (None, None, [], "no_receipt_found"),
])
def test_charge_reason_rules(row_type, entry_status, candidates, code):
    assert code in CHARGE_REASON_CODES
    assert charge_reason_code(
        row_type=row_type, entry_status=entry_status, candidates=candidates,
    ) == code
