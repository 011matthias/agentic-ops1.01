"""Item 220 (front 2): an unmatched receipt's reason names the statement it
waits for, read card before date edge, and the month's completeness sentence
counts those receipts apart.

September 2026 on 2026-09-25: 44 unmatched receipts read "the charge is
likely in the previous or next month" and 38 of them were dated after the
last loaded charge (09-14); the Expenses tab said "waiting for the
statement" for the same rows, and the publish refusal said "49 receipts have
no charge". The fixtures here are one card (9693) with a statement that
stops on 09-14.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.unmatched_reasons import (  # noqa: E402
    CARD_STATEMENT_NOT_LOADED,
    CHARGE_IN_NEIGHBOURING_PERIOD,
    NO_CHARGE_ON_ANY_LOADED_STATEMENT,
    NON_CARD_TENDER,
    NOT_A_CARD_CHARGE,
    RECEIPT_REASON_CODES,
    RECEIPT_REASON_SHORT,
    RECEIPT_REASON_TEXT,
    STATEMENT_NOT_LOADED_FOR_DATE,
    receipt_reason_code,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.month_readiness import not_complete_detail  # noqa: E402

CARD = {"card-9693": {"label": "BCS Chase Visa - 9693", "digits": ["9693"],
                      "entity": "Consulting"}}
LABEL = "BCS Chase Visa - 9693"
# The statement stops on 09-14, as September's 9693 export did.
SEPT_EXPORT = (
    ("2026-09-01", "10.00", "STAPLES", "9693"),
    ("2026-09-14", "11.00", "UBER", "9693"),
)


def _receipt(day, total, vendor, hint=None):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


def _client(tmp_path, monkeypatch, readings):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=list(readings),
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1, implied_rate=1.0,
                converted_amount=Decimal("0"), reasoning="no",
            )
        ] * 40,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    return TestClient(create_app(tmp_path))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, label, n_receipts) -> str:
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(n_receipts):
        blob = b"\xff\xd8\xff\xe0" + f"{label}-{i}".encode() * 8
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", blob, "application/octet-stream"))],
        ))
    return batch_id


def _statement(client, batch_id, rows):
    body = "Date,Amount,Vendor,Card\n" + "".join(f"{d},{a},{v},{c}\n" for d, a, v, c in rows)
    return client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("export.csv", body.encode(), "application/octet-stream")},
        data={
            "account_id": "card-9693",
            "account_legal_entities": '{"card-9693": "Consulting"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    )


READINGS = [
    # Dated after the statement's last charge, printing its card.
    _receipt("2026-09-20", "50.00", "Late Printed", hint="Visa ...9693"),
    # Printing no card at all, also after the last charge.
    _receipt("2026-09-22", "51.00", "Late Blank"),
    # Inside the last two days the statement covers: the charge can post
    # on the next statement.
    _receipt("2026-09-13", "52.00", "Edge Printed", hint="Visa ...9693"),
    # Well inside: no charge on a statement that covers the date.
    _receipt("2026-09-05", "53.00", "Inside Printed", hint="Visa ...9693"),
    # German till word for cash.
    _receipt("2026-09-20", "54.00", "Bakery", hint="Bar"),
]


def _unmatched(client, month) -> dict[str, dict]:
    run = client.get(f"/api/runs/{month}").json()
    by_vendor = {}
    for rec in run["unmatched_receipts"]:
        by_vendor[str(rec.get("vendor"))] = rec
    return run, by_vendor


def test_a_receipt_after_the_last_loaded_charge_waits_for_the_statement(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READINGS) as client:
        assert client.put("/api/settings", json={"cards": CARD}).status_code == 200
        sept = _month(client, "September 2026", len(READINGS))
        _done(client, _statement(client, sept, SEPT_EXPORT))
        run, rec = _unmatched(client, sept)
        assert rec["Late Printed"]["reason_code"] == STATEMENT_NOT_LOADED_FOR_DATE
        assert rec["Late Printed"]["waits_for_statements"] == [LABEL]
        assert rec["Late Blank"]["reason_code"] == STATEMENT_NOT_LOADED_FOR_DATE
        assert rec["Late Blank"]["waits_for_statements"] == [LABEL]
        assert rec["Edge Printed"]["reason_code"] == CHARGE_IN_NEIGHBOURING_PERIOD
        assert rec["Inside Printed"]["reason_code"] == NO_CHARGE_ON_ANY_LOADED_STATEMENT
        assert rec["Bakery"]["reason_code"] == NOT_A_CARD_CHARGE
        for vendor in ("Edge Printed", "Inside Printed", "Bakery"):
            assert "waits_for_statements" not in rec[vendor], vendor
        summary = run["summary"]
        assert summary["n_receipts_need_charge"] == 5
        assert summary["n_receipts_waiting_statement"] == 2
        assert summary["receipts_waiting_cards"] == [LABEL]


def test_the_publish_refusal_names_the_receipts_that_wait(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READINGS) as client:
        assert client.put("/api/settings", json={"cards": CARD}).status_code == 200
        sept = _month(client, "September 2026", len(READINGS))
        _done(client, _statement(client, sept, SEPT_EXPORT))
        resp = client.post(f"/api/runs/{sept}/publish", json={})
        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert body["code"] == "month_not_complete"
        assert f"2 receipts wait for a statement (cards {LABEL})" in body["error"]
        assert "3 receipts have no charge on any loaded statement" in body["error"]
        assert body["readiness"]["n_receipts_waiting_statement"] == 2
        assert body["readiness"]["n_receipts_need_charge"] == 5


def test_a_month_with_no_waiting_receipt_carries_no_card_list(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-09-05", "53.00", "Inside Printed", hint="Visa ...9693"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": CARD}).status_code == 200
        sept = _month(client, "September 2026", 1)
        _done(client, _statement(client, sept, SEPT_EXPORT))
        run, _rec = _unmatched(client, sept)
        assert run["summary"]["n_receipts_waiting_statement"] == 0
        assert "receipts_waiting_cards" not in run["summary"]


# ── the rule, pure ──────────────────────────────────────────────────────


def _r(day, mode=""):
    return SimpleNamespace(detected_date=date.fromisoformat(day), payment_mode=mode)


PERIOD = (date(2026, 8, 5), date(2026, 9, 14))


def test_card_before_edge_with_coverage():
    covered = {"cards": ["card-9693"], "waits_for": [], "never_loaded": []}
    late = {"cards": ["card-9693"], "waits_for": [LABEL], "never_loaded": []}
    never = {"cards": ["card-0113"], "waits_for": ["Apple 0113"], "never_loaded": ["Apple 0113"]}
    loaded = {"9693"}
    code = lambda rec, cov: receipt_reason_code(  # noqa: E731
        rec, loaded_cards=loaded, period=PERIOD, coverage=cov
    )
    # 09-15 is inside the old 31-day edge, so the old order said "neighbouring".
    assert code(_r("2026-09-15", "Visa ...9693"), late) == STATEMENT_NOT_LOADED_FOR_DATE
    assert code(_r("2026-09-15", "Apple Card ...0113"), never) == CARD_STATEMENT_NOT_LOADED
    assert code(_r("2026-09-13", "Visa ...9693"), covered) == CHARGE_IN_NEIGHBOURING_PERIOD
    assert code(_r("2026-09-01", "Visa ...9693"), covered) == NO_CHARGE_ON_ANY_LOADED_STATEMENT
    # Covered by another month's statement, not on this page: neighbouring.
    other = {"cards": ["3876"], "waits_for": [], "never_loaded": []}
    assert code(_r("2026-09-01", "Visa ...3876"), other) == CHARGE_IN_NEIGHBOURING_PERIOD
    # Waiting partly on a card with statements elsewhere: for this date.
    mixed = {"cards": ["a", "b"], "waits_for": ["A", "B"], "never_loaded": ["B"]}
    assert code(_r("2026-09-20"), mixed) == STATEMENT_NOT_LOADED_FOR_DATE


def test_without_coverage_the_order_stays_date_first():
    """No evidence, or digits no registry card names (August's Google
    invoices print account numbers): the pre-220 order."""
    rec = _r("2026-09-15", "...2544")
    assert receipt_reason_code(
        rec, loaded_cards={"9693"}, period=PERIOD
    ) == CHARGE_IN_NEIGHBOURING_PERIOD


@pytest.mark.parametrize("mode", [
    "Bar", "BAR", "Barzahlung", "girocardOLV", "girocard", "Kartenzahlung erhalten",
    "EC-Karte", "Debit",
])
def test_german_till_words_are_not_card_charges(mode):
    assert NON_CARD_TENDER.search(mode), mode


@pytest.mark.parametrize("mode", ["Barcelona", "Bargain Visa", "Barbara", "Kartenzahlung"])
def test_tender_words_stay_word_bounded(mode):
    assert not NON_CARD_TENDER.search(mode), mode


def test_the_new_code_has_its_words():
    assert STATEMENT_NOT_LOADED_FOR_DATE in RECEIPT_REASON_CODES
    assert STATEMENT_NOT_LOADED_FOR_DATE in RECEIPT_REASON_TEXT
    assert STATEMENT_NOT_LOADED_FOR_DATE in RECEIPT_REASON_SHORT


def test_the_sentence_without_waiting_keeps_its_old_words():
    s = not_complete_detail({"n_receipts_need_charge": 3})
    assert "3 receipts have no charge;" in s or "3 receipts have no charge." in s
    s = not_complete_detail({
        "n_receipts_need_charge": 3, "n_receipts_waiting_statement": 3,
        "receipts_waiting_cards": ["X"],
    })
    assert "3 receipts wait for a statement (cards X)" in s
    assert "no charge" not in s
