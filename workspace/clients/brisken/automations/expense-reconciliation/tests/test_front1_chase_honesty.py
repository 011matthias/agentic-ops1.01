"""Front 1 (2026-09-25): charges with nothing behind them say what they are.

The verified gap map of 2026-09-25 found the charge side of the month
disagreeing with itself. Live, July read 24 and August 40 gray-closed charges
as "no receipt found" while the month gate counted them closed; the
reviewer's "already booked" click moved the row's turn but not
`n_already_posted` or the reason; `n_already_posted` counted card payments;
"0 charges need a receipt" said nothing about the 3 / 4 / 7 cards with no
statement; the chase listed July charges as August's; and an ask had no age.

Route-level through the FastAPI app on one seeded month:

* the charge `reason_code` names every verdict the month gate closes on
  (`already_booked` from the fill OR the reviewer, `closed_recurring`,
  `no_receipt_expected`), a derived subscription mark stays open, and every
  code carries its `reason_label`;
* `n_already_posted` counts booked purchases from either source and no
  payment line;
* `summary.n_cards_uncovered` / `cards_uncovered` name the active card with
  nothing loaded, and the Publish refusal says so;
* `receipt_chase[]` carries `date_range` and per-charge `charge_month`, and
  the composed mail groups a straddling holder's charges by their month;
* an ask carries `days_since_requested` and `overdue`, against the settings
  threshold; the bulk mark stamps one holder's open charges and no other.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import MatchOutcome, Transaction  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

DIRK = "Dirk Neumann"
NICOLAS = "Nicolas Neumann"
CARDS = {
    "corp-2838": {"label": "Corporate card 2838", "digits": ["2838"],
                  "person": DIRK, "entity": "Corporate Services"},
    "nico-3876": {"label": "Card 3876", "digits": ["3876"],
                  "person": NICOLAS, "entity": "Corporate Services"},
    # Active, and nothing of it is loaded: the card "0 need a receipt"
    # cannot see.
    "apple-0113": {"label": "Apple card 0113", "digits": ["0113"],
                   "person": DIRK, "entity": "Corporate Services"},
}


def _tx(tid, d, vendor, amount, card="2838", **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=d, posting_date=None, amount=Decimal(amount),
        transaction_currency="USD", account_card_currency="USD",
        vendor_from_statement=vendor, card_last4=card, **kw,
    )


CHARGES = [
    _tx("t_gray", date(2026, 8, 3), "OPENAI *CHATGPT", "20.00",
        entry_status="subscription"),
    _tx("t_derived", date(2026, 8, 4), "BLOOMBERG", "30.00",
        entry_status="subscription", entry_status_source="derived"),
    _tx("t_reviewer", date(2026, 8, 5), "SAP", "40.00"),
    _tx("t_payment", date(2026, 8, 6), "PAYMENT THANK YOU", "-500.00",
        entry_status="posted", row_type="payment", is_credit=True),
    _tx("t_yellow", date(2026, 8, 7), "MICROSOFT", "50.00", entry_status="posted"),
    _tx("t_nre", date(2026, 8, 8), "CARD SERVICE CHARGE", "95.00"),
    # Nicolas's card: a charge from the previous cycle month and two asks.
    _tx("t_jul", date(2026, 7, 28), "GITHUB", "10.00", card="3876"),
    _tx("t_old_ask", date(2026, 8, 10), "SUPABASE", "25.00", card="3876"),
    _tx("t_new_ask", date(2026, 8, 11), "OBSIDIAN", "96.00"),
]
OPEN_REASONS = {
    "t_gray": "closed_recurring",
    "t_derived": "no_receipt_found",
    "t_reviewer": "already_booked",
    "t_yellow": "already_booked",
    "t_nre": "no_receipt_expected",
    "t_jul": "no_receipt_found",
    "t_old_ask": "no_receipt_found",
    "t_new_ask": "no_receipt_found",
}


def _stamp(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(client, *, overdue_days=None) -> str:
    outcome = MatchOutcome(
        unmatched_transactions=[t.transaction_id for t in CHARGES
                                if t.transaction_id != "t_payment"],
        refunds=["t_payment"],
    )
    db = RunStore(client._data_root / "recon-web.sqlite")
    db.create_run(
        run_id="aug", created_at="2026-09-02T00:00:00", label="August 2026",
        operator=None, summary={}, snapshot=snapshot_to_dict(CHARGES, [], outcome, []),
        config={"mode": "expense_generation", "expense": {"cards": CARDS}},
        work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    now = _stamp(0)
    db.set_decision("aug", "t_reviewer", "already_posted", None, now)
    db.set_no_receipt_expected("aug", "t_nre", "the bank's own service charge", now)
    db.set_receipt_requested("aug", "t_old_ask", _stamp(20), None, now)
    db.set_receipt_requested("aug", "t_new_ask", _stamp(3), None, now)
    db.close()
    if overdue_days is not None:
        resp = client.put("/api/settings", json={"receipt_requests": {
            "enabled": False, "holders": {}, "overdue_days": overdue_days,
        }})
        assert resp.status_code == 200, resp.text
    return "aug"


def _view(client, run_id="aug") -> dict:
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _group(view, holder) -> dict:
    return next(g for g in view["receipt_chase"] if g["holder"] == holder)


# ── step 1: the reason names the verdict ─────────────────────────────


def test_every_closing_verdict_names_the_charge_and_carries_a_label(client):
    view = _view(client, _seed(client))
    rows = {r["transaction_id"]: r for r in view["rows"]}
    assert {
        tx: rows[tx]["reason_code"] for tx in OPEN_REASONS
    } == OPEN_REASONS
    # Same code, same label, on the list the page renders beside the rows.
    listed = {t["transaction_id"]: t for t in view["unmatched_transactions"]}
    for tx, code in OPEN_REASONS.items():
        assert listed[tx]["reason_code"] == code
        assert listed[tx]["reason_label"] == rows[tx]["reason_label"]
        assert rows[tx]["reason_label"].strip()
    assert "gray" in rows["t_gray"]["reason_label"]
    assert "reason_label" not in rows["t_payment"], "no reason, no label"
    # The gate and the list agree: every charge the list calls owed is one
    # the gate counts, and nothing it calls closed is.
    owed = {tx for tx, c in OPEN_REASONS.items() if c == "no_receipt_found"}
    assert view["summary"]["n_charges_need_receipt"] == len(owed)


def test_already_posted_counts_booked_purchases_from_either_source(client):
    summary = _view(client, _seed(client))["summary"]
    # yellow MICROSOFT + the reviewer's SAP; the yellow payment line is not
    # a booked charge.
    assert summary["n_already_posted"] == 2
    assert summary["n_booked_no_receipt"] == 2


# ── step 2: a card with nothing loaded is named ──────────────────────


def test_an_active_card_with_nothing_loaded_is_named_and_the_refusal_says_so(client):
    run_id = _seed(client)
    summary = _view(client, run_id)["summary"]
    assert summary["n_cards_uncovered"] == 1
    assert summary["cards_uncovered"] == ["Apple card 0113"]
    resp = client.post(f"/api/runs/{run_id}/publish", json={})
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["code"] == "month_not_complete"
    assert "1 active card has no statement loaded for this month (Apple card 0113)" in body["error"]
    assert body["readiness"]["n_cards_uncovered"] == 1


# ── step 3: the chase names its dates ────────────────────────────────


def test_the_chase_names_each_charge_month_and_the_mail_groups_by_it(client):
    run_id = _seed(client)
    nicolas = _group(_view(client, run_id), NICOLAS)
    assert nicolas["date_range"] == {"start": "2026-07-28", "end": "2026-08-10"}
    assert [(c["vendor"], c["charge_month"]) for c in nicolas["charges"]] == [
        ("GITHUB", "2026-07"), ("SUPABASE", "2026-08"),
    ]
    mails = client.get(f"/api/runs/{run_id}/receipt-requests").json()["mails"]
    mail = next(m for m in mails if m["holder"] == NICOLAS)
    assert mail["subject"] == (
        "August 2026: 2 receipts still missing "
        "(charges dated 2026-07-28 to 2026-08-10)"
    )
    body = mail["body"]
    assert body.index("July 2026 (1 charge):") < body.index("GITHUB")
    assert body.index("GITHUB") < body.index("August 2026 (1 charge):")
    assert body.index("August 2026 (1 charge):") < body.index("SUPABASE")
    assert "julho de 2026 (1 lançamento):" in mail["body_pt"]
    # A holder whose charges sit in one month gets a flat list.
    dirk = next(m for m in mails if m["holder"] == DIRK)
    assert "(2 charges):" not in dirk["body"] and "August 2026 (" not in dirk["body"]


# ── step 4: an ask has an age ────────────────────────────────────────


def test_an_ask_carries_its_age_and_turns_overdue_at_the_threshold(client):
    view = _view(client, _seed(client))
    charges = {
        c["transaction_id"]: c
        for g in view["receipt_chase"] for c in g["charges"]
    }
    assert charges["t_old_ask"]["days_since_requested"] == 20
    assert charges["t_old_ask"]["overdue"] is True
    assert charges["t_new_ask"]["days_since_requested"] == 3
    assert charges["t_new_ask"]["overdue"] is False
    assert "days_since_requested" not in charges["t_jul"], "never asked, no age"
    assert _group(view, NICOLAS)["n_overdue"] == 1
    assert _group(view, DIRK)["n_overdue"] == 0


def test_the_overdue_threshold_is_a_setting(client):
    view = _view(client, _seed(client, overdue_days=2))
    charges = {c["transaction_id"]: c for g in view["receipt_chase"] for c in g["charges"]}
    assert charges["t_new_ask"]["overdue"] is True
    bad = client.put("/api/settings", json={"receipt_requests": {"overdue_days": 0}})
    assert bad.status_code == 400, bad.text


def test_mark_all_stamps_one_holders_open_charges_and_keeps_earlier_asks(client):
    run_id = _seed(client)
    before = {c["transaction_id"]: c for c in _group(_view(client, run_id), NICOLAS)["charges"]}
    resp = client.post(f"/api/runs/{run_id}/receipt-requests/mark-all",
                       json={"holder": NICOLAS})
    assert resp.status_code == 200, resp.text
    assert resp.json()["n_marked"] == 1, "only the charge nobody had asked for"
    after_view = _view(client, run_id)
    after = {c["transaction_id"]: c for c in _group(after_view, NICOLAS)["charges"]}
    assert after["t_jul"]["days_since_requested"] == 0
    assert after["t_old_ask"]["receipt_requested_at"] == before["t_old_ask"]["receipt_requested_at"]
    # Dirk's charges are untouched: one holder, one mail.
    dirk = {c["transaction_id"]: c for c in _group(after_view, DIRK)["charges"]}
    assert "receipt_requested_at" not in dirk["t_derived"]
    # Asking closes nothing.
    assert after_view["summary"]["n_charges_need_receipt"] == 4
    assert after_view["summary"]["n_charges_receipt_requested"] == 3
    unknown = client.post(f"/api/runs/{run_id}/receipt-requests/mark-all",
                          json={"holder": "Somebody Else"})
    assert unknown.status_code == 400
    assert unknown.json()["code"] == "holder_has_no_open_charge"
