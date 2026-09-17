"""Item 133 (2026-09-17 audit), the bulk-confirm half: a same-amount receipt
from ANOTHER merchant must not be booked by one click.

August 2026 produced the shape twice (a Lovable 50 invoice took BASE44 50.00
the next day, an Anthropic 100 invoice took BASE44 100.00 four days later), and
on 2026-09-17 the Lovable invoice is back on BASE44 50.00 after its card-bearing
receipt copy was deleted. The matcher still pairs on amount and date; the tool
never confirms such a pair itself (item 76), and since item 101 "Confirm all
matched" follows the owner's pairing rule (`confirmable_pair`). "Confirm all
Ready" did not: `ready` is a CATEGORY verdict, so a categorized receipt on the
wrong merchant's charge was ready, and the click booked it. Now both bulk
routes leave it for a person.

The matcher half (rule (b), built 2026-09-17): an exact-amount pair whose
merchant disagrees yields the receipt to a rival charge whose merchant agrees,
even when that rival is a few days further away; with no such rival nothing
changes (the tests at the bottom).

Route-level: the real upload and statement-attach routes (`rematch_month`,
then item 76's self-confirmation), then `GET /api/runs/{id}` and the two bulk
routes.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-item-133"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _month(client, monkeypatch, charges) -> str:
    """An "Anthropic, PBC" USD 100.00 receipt of 2026-08-21, categorized by the
    merchant book (so its category verdict is `ready` and only the pairing is
    in question), against the given charges."""
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-08-21", total="100.00", currency="USD", vendor="Anthropic, PBC",
        reference="", line_items=(), confidence=0.9, notes="",
    )])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.put("/api/settings", json={
        "entities": {"Corporate Services": {}},
        "cards": {"corp-2838": {
            "label": "Corporate card (Chase)", "digits": ["2838"],
            "entity": "Corporate Services", "currency": "USD",
        }},
        "merchants": {"Anthropic": {
            "aliases": ["ANTHROPIC", "Anthropic, PBC"],
            "category": "Software & Subscriptions", "zoho_account": "6200 Software",
        }},
    })
    assert resp.status_code == 200, resp.text
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "August 2026"},
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("anthropic.jpg", JPG, "application/octet-stream"))],
    ))
    _done(client, client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": ("August2026.xlsx", _xlsx(charges), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch


def _view(client, batch) -> dict:
    return client.get(f"/api/runs/{batch}").json()


def _row(view, vendor) -> dict:
    rows = [r for r in view["rows"] if r["vendor"] == vendor]
    assert len(rows) == 1, [r["vendor"] for r in view["rows"]]
    return rows[0]


@pytest.mark.parametrize("route", ["confirm-ready", "confirm-matched"])
@pytest.mark.parametrize("day", [datetime(2026, 8, 25), datetime(2026, 8, 21)], ids=["4-days", "same-day"])
def test_no_bulk_confirm_books_another_merchants_same_amount_charge(
    client, monkeypatch, route, day
):
    batch = _month(client, monkeypatch, [(day, "BASE44", "Sale", -100.00)])
    row = _row(_view(client, batch), "BASE44")
    (cand,) = row["candidates"]
    # The pairing the button would have booked: the receipt's category is
    # settled, the merchants disagree.
    assert (row["review"] or {}).get("state") == "ready"
    assert cand["is_chosen"] and cand["vendor_pct"] == 22
    assert row["status"] == "pending" and row["turn"] == "decide"

    resp = client.post(f"/api/runs/{batch}/decisions/{route}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["confirmed"] == 0

    after = _view(client, batch)
    row = _row(after, "BASE44")
    assert row["status"] == "pending" and row["turn"] == "decide"
    assert "decided_by" not in row
    assert after["summary"]["n_confirm_matched"] == 0
    assert after["summary"]["month_complete"] is False
    resp = client.post(f"/api/runs/{batch}/publish", json={})
    assert resp.status_code == 400 and resp.json()["code"] == "month_not_complete"


@pytest.mark.parametrize("day, match_type, self_confirms", [
    (datetime(2026, 8, 25), "probable", False),
    (datetime(2026, 8, 21), "exact", True),
])
def test_a_rival_with_the_right_merchant_at_the_same_distance_takes_the_receipt(
    client, monkeypatch, day, match_type, self_confirms
):
    batch = _month(client, monkeypatch, [
        (day, "BASE44", "Sale", -100.00),
        (day, "ANTHROPIC", "Sale", -100.00),
    ])
    view = _view(client, batch)
    right, wrong = _row(view, "ANTHROPIC"), _row(view, "BASE44")
    assert right["effective_bucket"] == "reconciled"
    (cand,) = right["candidates"]
    assert cand["is_chosen"] and cand["match_type"] == match_type and cand["vendor_pct"] == 100
    assert (right.get("decided_by") == "tool") is self_confirms
    assert wrong["effective_bucket"] == "unmatched" and wrong["candidates"] == []

    # Neither bulk route books the probable pair (the rule is exact only).
    for route in ("confirm-ready", "confirm-matched"):
        assert client.post(f"/api/runs/{batch}/decisions/{route}").status_code == 200
    right = _row(_view(client, batch), "ANTHROPIC")
    assert right["status"] == ("confirmed" if self_confirms else "pending")


# ── rule (b): the matcher half ─────────────────────────────────────────────


def test_a_same_day_other_merchant_yields_to_the_right_merchant_days_later(client, monkeypatch):
    """The shape items 76/99/100/137 left open: BASE44 100.00 the same day
    (EXACT, 0.99, vendor 22) outranked ANTHROPIC 100.00 three days later
    (PROBABLE, 0.85, vendor 100) on confidence, held the receipt, and the
    right charge listed no candidate. The wrong pair now asks for review and
    ranks at 0.55, so the right merchant takes the receipt."""
    batch = _month(client, monkeypatch, [
        (datetime(2026, 8, 21), "BASE44", "Sale", -100.00),
        (datetime(2026, 8, 24), "ANTHROPIC", "Sale", -100.00),
    ])
    view = _view(client, batch)
    right, wrong = _row(view, "ANTHROPIC"), _row(view, "BASE44")
    assert right["effective_bucket"] == "reconciled", right
    (cand,) = right["candidates"]
    assert cand["is_chosen"] and cand["match_type"] == "probable" and cand["vendor_pct"] == 100
    assert wrong["effective_bucket"] == "unmatched", wrong
    assert wrong["candidates"] == []
    assert view["unmatched_receipts"] == []


def test_with_no_agreeing_rival_the_other_merchants_exact_pair_is_unchanged(client, monkeypatch):
    """No rival, no change: the pair keeps EXACT at 0.99 and its reason, and
    item 76 keeps it on the reviewer's turn (the bulk-confirm half)."""
    batch = _month(client, monkeypatch, [(datetime(2026, 8, 21), "BASE44", "Sale", -100.00)])
    row = _row(_view(client, batch), "BASE44")
    (cand,) = row["candidates"]
    assert row["effective_bucket"] == "reconciled"
    assert cand["match_type"] == "exact" and cand["confidence"] == 0.99
    assert "merchants differ" not in cand["reason"], cand["reason"]
    assert row["turn"] == "decide"


# Matcher-level edges (review 2026-09-17): `match_month` is the caller the
# rule lives in; each case was reproduced against the first draft.

def _tx(i, vendor, day):
    from datetime import date
    from decimal import Decimal

    from expense_recon.matching.types import Transaction

    return Transaction(
        transaction_id=i, account_id="card-2838", legal_entity_id="",
        transaction_date=date(2026, 8, day), posting_date=None,
        amount=Decimal("100.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor, card_last4="2838",
    )


def _rec(i, vendor, day):
    from datetime import date
    from decimal import Decimal

    from expense_recon.matching.types import Receipt

    return Receipt(
        document_id=i, legal_entity_id="", detected_date=date(2026, 8, day),
        detected_total=Decimal("100.00"), detected_currency="USD", detected_vendor=vendor,
    )


def _pairs(outcome):
    return {(m.transaction_id, m.document_id): m for m in outcome.matches}


def test_a_rival_with_a_better_receipt_of_its_own_does_not_demote():
    """ANTHROPIC on the 24th has its own same-day receipt, so it never wants
    the 21st's: BASE44 keeps that receipt as it was (0.99, no flag)."""
    from expense_recon.matching.deterministic import match_month

    out = match_month(
        [_tx("t1", "BASE44", 21), _tx("t2", "ANTHROPIC", 24)],
        [_rec("R1", "Anthropic, PBC", 21), _rec("R2", "Anthropic, PBC", 24)],
    )
    pairs = _pairs(out)
    assert set(pairs) == {("t1", "R1"), ("t2", "R2")}, set(pairs)
    assert pairs[("t1", "R1")].confidence == 0.99
    assert "merchants differ" not in pairs[("t1", "R1")].reason


def test_a_spoken_for_rival_never_strands_the_receipt():
    """With a third receipt from yet another merchant three days earlier,
    the first draft moved BASE44 onto it and left R1 unmatched."""
    from expense_recon.matching.deterministic import match_month

    out = match_month(
        [_tx("t1", "BASE44", 21), _tx("t2", "ANTHROPIC", 24)],
        [_rec("R1", "Anthropic, PBC", 21), _rec("R2", "Anthropic, PBC", 24),
         _rec("R6", "Notion Labs", 18)],
    )
    assert ("t1", "R1") in _pairs(out), _pairs(out)
    assert "R1" not in out.unmatched_receipts


def test_the_rule_never_breaks_a_tie_a_person_should_settle():
    """BASE44 ties between two Anthropic receipts; ANTHROPIC on the 15th can
    reach only one of them. Before the rule the tie went to a person and it
    still does, instead of BASE44 taking the other receipt unflagged."""
    from expense_recon.matching.deterministic import match_month

    out = match_month(
        [_tx("t1", "BASE44", 21), _tx("t2", "ANTHROPIC", 15)],
        [_rec("R1", "Anthropic, PBC", 20), _rec("R7", "Anthropic, PBC", 22)],
    )
    assert {a.transaction_id for a in out.ambiguous} == {"t1"}, out.ambiguous
    assert all(m.transaction_id != "t1" for m in out.matches), out.matches
    # Item 103 (2026-09-17) changed what happens to R1 while the pick is
    # open: the tie HOLDS both receipts, so ANTHROPIC does not take R1
    # behind the pick's back. The raw outcome used to pair them, and the
    # page never showed that pairing anyway (`held_by` gave R1 to the tie
    # and called the charge "receipt held by another charge"), which is the
    # split item 103 closed. Once a person settles the tie, the next
    # re-match offers the freed receipt to this charge.
    assert ("t2", "R1") not in _pairs(out)
    assert "t2" in out.unmatched_transactions, out.unmatched_transactions
