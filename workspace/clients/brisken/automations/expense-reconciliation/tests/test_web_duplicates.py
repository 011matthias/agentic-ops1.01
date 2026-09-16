"""§18 duplicate surfacing + resolve, as item 74 left it (2026-09-16).

Owner rulings, notes #37/#41/#45/#46: charge-side duplicate detection is
deleted (two charges to one vendor are two charges); the tool decides every
receipt group and never asks; a decided group leaves the to-do area.

Route-level through the FastAPI app:

* no charge group reaches the payload, the counts or a charge row;
* every receipt group carries `state` / `decided_by` / `verdict` beside its
  `resolution`, and a reviewer's saved ruling maps onto them (`confirmed` ->
  copy, `ignore` -> distinct, both `decided_by: reviewer`) without moving the
  tool's `basis`;
* every group stays in the payload, decided or not, in the order
  `duplicate_receipts` lists them, because the SPA pairs the two lists BY
  INDEX within a kind.
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
    MatchOutcome,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


def _tx(tid, day, vendor="AMAZON", amount="180") -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
    )


def _rc(doc, vendor, total, day, reference=None, payment_mode=None) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=date(2026, 4, day),
        detected_total=Decimal(total), detected_currency="USD",
        detected_vendor=vendor, detected_reference=reference,
        payment_mode=payment_mode,
    )


# Four receipt groups, one of each shape the payload has to keep in order:
#   p1/p2  vendor + date + total, nothing disagreeing       -> copy (vendor_date)
#   g1/g2  two different document numbers, no file to read  -> distinct (distinct_reference)
#   c1/c2  two different cards                              -> distinct (receipt_card)
#   i1/i2  a copy the reviewer ruled "not a duplicate"      -> distinct (reviewer)
RECEIPTS = [
    _rc("p1", "Pressmaster FZCO", "135.00", 15),
    _rc("p2", "Pressmaster FZCO", "135.00", 15),
    _rc("g1", "Google LLC", "71.64", 1, reference="5608449734"),
    _rc("g2", "Google LLC", "71.64", 1, reference="5614551183"),
    _rc("c1", "Posto Santos", "50.00", 18, payment_mode="Visa ...2838"),
    _rc("c2", "Posto Santos", "50.00", 18, payment_mode="Visa ...1672"),
    _rc("i1", "Aposto", "80.00", 13),
    _rc("i2", "Aposto", "80.00", 13),
]
GID = {k: duplicate_group_id("receipt", [f"{k}1", f"{k}2"]) for k in "pgci"}


def _snapshot() -> dict:
    # Two same-merchant, same-amount charges a day apart: the shape the
    # deleted charge detector used to raise as a "duplicate charge".
    t1, t2 = _tx("t1", 7), _tx("t2", 8)
    outcome = MatchOutcome(
        unmatched_transactions=["t1", "t2"],
        unmatched_receipts=[r.document_id for r in RECEIPTS],
    )
    return snapshot_to_dict([t1, t2], RECEIPTS, outcome, [])


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(client, resolutions: dict[str, str] | None = None) -> str:
    db = RunStore(client._data_root / "recon-web.sqlite")
    db.create_run(
        run_id="run1", created_at="2026-07-21T00:00:00", label="test",
        operator=None, summary={}, snapshot=_snapshot(), config={},
        work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    for gid, resolution in (resolutions or {}).items():
        db.set_duplicate_resolution("run1", gid, resolution, "2026-09-16T00:00:00")
    db.close()
    return "run1"


def _groups(view) -> dict[str, dict]:
    return {g["group_id"]: g for g in view["duplicate_groups"]}


# ── (a) charge-side detection is gone ────────────────────────────────


def test_two_same_vendor_charges_raise_no_group_anywhere(client):
    run_id = _seed(client)
    view = client.get(f"/api/runs/{run_id}").json()
    assert view["duplicate_charges"] == []
    assert {g["kind"] for g in view["duplicate_groups"]} == {"receipt"}
    assert [r["duplicate"] for r in view["rows"]] == [None, None]
    # the counts read receipt groups only: four groups, and one extra copy in
    # each of the two the tool calls a copy (Pressmaster, Aposto)
    assert view["summary"]["n_duplicate_groups"] == 4
    assert view["summary"]["n_duplicate_copies"] == 2


# ── (d) state / decided_by / verdict ─────────────────────────────────


def test_the_tool_decides_every_group_and_nothing_is_open(client):
    run_id = _seed(client)
    view = client.get(f"/api/runs/{run_id}").json()
    groups = _groups(view)
    assert {
        k: (groups[GID[k]]["basis"], groups[GID[k]]["verdict"],
            groups[GID[k]]["decided_by"], groups[GID[k]]["state"])
        for k in "pgci"
    } == {
        "p": ("vendor_date", "copy", "tool", "decided"),
        "g": ("distinct_reference", "distinct", "tool", "decided"),
        "c": ("receipt_card", "distinct", "tool", "decided"),
        "i": ("vendor_date", "copy", "tool", "decided"),
    }
    assert view["summary"]["n_duplicate_groups_open"] == 0
    # only a copy carries row markers; a distinct pair is not a duplicate
    marked = {r["document_id"] for r in view["unmatched_receipts"] if r["duplicate"]}
    assert marked == {"p1", "p2", "i1", "i2"}


def test_a_saved_resolution_maps_onto_verdict_and_decided_by(client):
    """The live months hold rulings saved before item 74: `confirmed` ("Real
    duplicate") reads as a copy, `ignore` ("Not a duplicate") as two
    purchases, both decided by the reviewer, and the reviewer outranks the
    tool in both directions (July's Google group is a `confirmed` on a pair
    the tool calls distinct). `resolution` keeps its value and `basis` keeps
    what the tool found."""
    run_id = _seed(client, {GID["g"]: "confirmed", GID["i"]: "ignore"})
    view = client.get(f"/api/runs/{run_id}").json()
    groups = _groups(view)

    google = groups[GID["g"]]
    assert (google["resolution"], google["verdict"], google["decided_by"],
            google["state"], google["basis"]) == (
        "confirmed", "copy", "reviewer", "decided", "distinct_reference")
    aposto = groups[GID["i"]]
    assert (aposto["resolution"], aposto["verdict"], aposto["decided_by"],
            aposto["state"], aposto["basis"]) == (
        "ignore", "distinct", "reviewer", "decided", "vendor_date")
    assert groups[GID["p"]]["resolution"] is None
    assert groups[GID["p"]]["decided_by"] == "tool"
    assert view["summary"]["n_duplicate_groups_open"] == 0
    marked = {r["document_id"] for r in view["unmatched_receipts"] if r["duplicate"]}
    assert marked == {"p1", "p2", "g1", "g2"}, "the reviewer's copy is marked, the ignored pair is not"


def test_the_resolve_route_moves_the_verdict_and_the_undo_moves_it_back(client):
    run_id = _seed(client)
    resp = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": GID["p"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True
    group = _groups(client.get(f"/api/runs/{run_id}").json())[GID["p"]]
    assert (group["resolution"], group["verdict"], group["decided_by"]) == (
        "ignore", "distinct", "reviewer")

    resp = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": GID["p"], "action": "confirmed"},
    )
    assert resp.status_code == 200, resp.text
    group = _groups(client.get(f"/api/runs/{run_id}").json())[GID["p"]]
    assert (group["resolution"], group["verdict"], group["decided_by"]) == (
        "confirmed", "copy", "reviewer")


def test_resolve_rejects_invalid_resolution(client):
    run_id = _seed(client)
    r = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": GID["p"], "resolution": "delete-it"},
    )
    assert r.status_code == 400


def test_resolving_a_month_with_no_statement_moves_no_bucket(client):
    """A resolution on a run with nothing to re-match changes the group and
    nothing else: no bucket, no invariant."""
    run_id = _seed(client)
    before = client.get(f"/api/runs/{run_id}").json()["summary"]
    client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": GID["p"], "resolution": "confirmed"},
    )
    after = client.get(f"/api/runs/{run_id}").json()["summary"]
    assert before["invariant_ok"] == after["invariant_ok"]
    assert before["n_reconciled"] == after["n_reconciled"]
    assert before["n_unmatched_tx"] == after["n_unmatched_tx"]


# ── the index alignment ──────────────────────────────────────────────


def test_every_group_stays_listed_in_the_order_duplicate_receipts_lists_them(client):
    """The SPA pairs `duplicate_groups[i]` with `duplicate_receipts[i]` within
    a kind (round A pinned it). Decided groups are NOT filtered out of either
    list: dropping one would shift every later group onto another group's
    receipts."""
    run_id = _seed(client, {GID["i"]: "ignore"})
    view = client.get(f"/api/runs/{run_id}").json()
    receipt_groups = [g for g in view["duplicate_groups"] if g["kind"] == "receipt"]
    assert len(receipt_groups) == len(view["duplicate_receipts"]) == 4
    assert [
        [r["document_id"] for r in grp] for grp in view["duplicate_receipts"]
    ] == [g["members"] for g in receipt_groups]
    assert {g["verdict"] for g in receipt_groups} == {"copy", "distinct"}
