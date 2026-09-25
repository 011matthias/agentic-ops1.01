"""Item 204, case 9, build 5 (steps 1 and 5): a receipt that names no card.

Four rules, each route-level through the FastAPI app:

1. **Waiting status.** A card-less, non-private row whose date some active
   card's loaded statements (any month) do not cover reads
   `waits_for_statement` ahead of `needs_entity`, with
   `waits_for_statements: [card labels]`; the run payload's unmatched
   receipt reads `card_statement_not_loaded` for the same fact. When every
   active card covers the date, `needs_entity` stands.
2. **Recurring-charge suggestion.** `card_suggestion` names the one card
   every nearby same-vendor, same-amount charge sits on. Never applied.
3. **Apply to this vendor.** `POST /api/expense-batches/{id}/cards/by-vendor`
   writes the row PUT's card override to the vendor's other card-less rows.
4. **A statement says which month it belongs to.** `statements[]
   .month_suggestion` plus the `statement_month_differs` advisory.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.card_suggestion import card_by_vendor_targets  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

FAMILY = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "3645": {"label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
             "entity": "Corporate Services", "parent": "card-2838"},
    # A subcard with no charge in the export: covered through its family.
    "card-0340": {"label": "Credit Card Chase Visa - 0340", "digits": ["0340"],
                  "entity": "Corporate Services", "parent": "card-2838"},
}
CYCLE = {"card-9693": {"label": "BCS Chase Visa - 9693", "digits": ["9693"],
                       "entity": "Consulting"}}


def _receipt(date, total, vendor, hint=None, reference=""):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
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
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return TestClient(create_app(tmp_path))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, label, n_receipts) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(n_receipts):
        # Distinct bytes per file: identical files are deduped at upload.
        blob = b"\xff\xd8\xff\xe0" + f"{label}-{i}".encode() * 8
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", blob, "application/octet-stream"))],
        ))
    return batch_id


def _statement(client, batch_id, rows, name="export.csv"):
    body = "Date,Amount,Vendor,Card\n" + "".join(
        f"{d},{a},{v},{c}\n" for d, a, v, c in rows
    )
    return client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body.encode(), "application/octet-stream")},
        data={
            "account_id": "chase-2838",
            "account_legal_entities": '{"chase-2838": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    )


def _rows(client, batch_id) -> dict[str, dict]:
    view = client.get(f"/api/expense-batches/{batch_id}").json()
    return {str((e["vendor"] or {}).get("display")): e for e in view["expenses"]}


# July's 2838 family export: charges on 2838 and 3645 only, Jul 1 to Jul 31.
JULY_EXPORT = (
    ("2026-07-01", "42.50", "STAPLES", "2838"),
    ("2026-07-05", "2.76", "NETWORK SOLUTIONS", "3645"),
    ("2026-07-31", "15.00", "UBER", "3645"),
)


# ── 1. waiting status ───────────────────────────────────────────────────


def test_a_cardless_row_no_statement_covers_waits_for_those_cards(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-07-15", "88.00", "Acme Tools"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": {**FAMILY, **CYCLE}}).status_code == 200
        july = _month(client, "July 2026", 2)
        _done(client, _statement(client, july, JULY_EXPORT))
        row = _rows(client, july)["Acme Tools"]
        assert row["card"] is None and row["card_source"] == "none"
        # 0340 printed nothing, and its family's export still covers it.
        assert row["waits_for_statements"] == ["BCS Chase Visa - 9693"]
        assert row["review"]["reason_code"] == "waits_for_statement"
        assert row["review"]["waits_for_statements"] == ["BCS Chase Visa - 9693"]
        # The run payload says the same about the same receipt.
        run = client.get(f"/api/runs/{july}").json()
        reasons = {
            r["document_id"]: r["reason_code"] for r in run["unmatched_receipts"]
        }
        assert reasons[row["document_id"]] == "card_statement_not_loaded"


def test_a_covered_date_keeps_needs_entity(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-07-15", "88.00", "Acme Tools"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 2)
        _done(client, _statement(client, july, JULY_EXPORT))
        row = _rows(client, july)["Acme Tools"]
        assert "waits_for_statements" not in row
        assert row["review"]["reason_code"] == "needs_entity"
        run = client.get(f"/api/runs/{july}").json()
        reasons = {
            r["document_id"]: r["reason_code"] for r in run["unmatched_receipts"]
        }
        assert reasons[row["document_id"]] == "no_charge_on_any_loaded_statement"


def test_coverage_is_read_from_any_month(tmp_path, monkeypatch):
    """August holds no statement; July's export runs to Aug 3, so an August
    receipt dated Aug 2 is covered and one dated Aug 20 waits."""
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-08-02", "11.00", "Early Cafe"),
        _receipt("2026-08-20", "12.00", "Late Cafe"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, (
            *JULY_EXPORT, ("2026-08-03", "9.00", "UBER", "3645"),
        )))
        august = _month(client, "August 2026", 2)
        rows = _rows(client, august)
        assert rows["Early Cafe"]["review"]["reason_code"] == "needs_entity"
        assert "waits_for_statements" not in rows["Early Cafe"]
        late = rows["Late Cafe"]
        assert late["review"]["reason_code"] == "waits_for_statement"
        assert late["waits_for_statements"] == sorted(
            c["label"] for c in FAMILY.values()
        )


def test_a_row_with_a_card_or_private_does_not_wait(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-08-10", "20.00", "Printed Shop", hint="Visa ending 2838"),
        _receipt("2026-08-11", "21.00", "Private Shop"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        august = _month(client, "August 2026", 2)
        rows = _rows(client, august)
        assert rows["Printed Shop"]["card"]["key"] == "card-2838"
        doc = rows["Private Shop"]["document_id"]
        resp = client.post(
            f"/api/runs/{august}/expenses/{doc}/private",
            json={"private": True, "reimburse_to": "Nicolas"},
        )
        assert resp.status_code == 200, resp.text
        rows = _rows(client, august)
        for vendor in ("Printed Shop", "Private Shop"):
            assert "waits_for_statements" not in rows[vendor]
            assert rows[vendor]["review"]["reason_code"] != "waits_for_statement"


# ── 2. recurring-charge suggestion ──────────────────────────────────────


def test_a_recurring_charge_on_one_card_is_suggested_never_applied(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-08-05", "2.76", "Network Solutions"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, JULY_EXPORT))
        august = _month(client, "August 2026", 1)
        row = _rows(client, august)["Network Solutions"]
        assert row["card_suggestion"] == {
            "card_key": "3645",
            "label": "Credit Card Chase Visa - 3645",
            "evidence": [{
                "month": "2026-07", "date": "2026-07-05", "amount": "2.76",
                "currency": "USD", "description": "NETWORK SOLUTIONS",
            }],
        }
        # A suggestion: the row keeps no card and still asks a person.
        assert row["card"] is None and row["card_source"] == "none"
        assert row["legal_entity_id"] == ""


def test_charges_on_two_cards_suggest_nothing(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-08-05", "2.76", "Network Solutions"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, (
            *JULY_EXPORT, ("2026-07-20", "2.75", "NETWORK SOLUTIONS", "2838"),
        )))
        august = _month(client, "August 2026", 1)
        assert "card_suggestion" not in _rows(client, august)["Network Solutions"]


def test_a_decided_copy_gets_no_suggestion(tmp_path, monkeypatch):
    # Live 2026-09-25: two of six suggestions sat on copies (May 86929f2a909a,
    # July 50622baec444), where a click writes an override on a row that
    # counts for nothing. The row the copy repeats carries the suggestion.
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-08-05", "2.76", "Network Solutions", reference="INV-7"),
        _receipt("2026-08-05", "2.76", "Network Solutions", reference="INV-7"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, JULY_EXPORT))
        august = _month(client, "August 2026", 2)
        expenses = client.get(f"/api/expense-batches/{august}").json()["expenses"]
        counting = [e for e in expenses if e.get("counts_in_total", True)]
        copies = [e for e in expenses if e.get("counts_in_total") is False]
        assert len(counting) == 1 and len(copies) == 1, "one original, one copy"
        assert counting[0]["card_suggestion"]["card_key"] == "3645"
        assert "card_suggestion" not in copies[0]
        # The copy's review stays honest: it keeps no card either way.
        assert copies[0]["card"] is None


# ── 3. apply to this vendor ─────────────────────────────────────────────


def test_apply_to_vendor_writes_only_the_open_cardless_rows(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-08-01", "30.00", "Lovable"),                           # picked
        _receipt("2026-08-02", "31.00", "Lovable"),                           # target
        _receipt("2026-08-03", "32.00", "Lovable", hint="Visa ending 2838"),  # printed
        _receipt("2026-08-04", "33.00", "Lovable"),                           # private
        _receipt("2026-08-05", "34.00", "Lovable", reference="INV-9"),        # target
        _receipt("2026-08-05", "34.00", "Lovable", reference="INV-9"),        # copy
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        august = _month(client, "August 2026", 6)
        view = client.get(f"/api/expense-batches/{august}").json()
        by_total = {e["total"]: e["document_id"] for e in view["expenses"]
                    if e.get("counts_in_total", True)}
        copies = [e["document_id"] for e in view["expenses"]
                  if e.get("counts_in_total") is False]
        assert len(copies) == 1, "the fixture must hold one decided copy"
        picked, target, printed, private, target2 = (
            by_total[t] for t in ("30.00", "31.00", "32.00", "33.00", "34.00")
        )
        assert client.post(
            f"/api/runs/{august}/expenses/{private}/private",
            json={"private": True, "reimburse_to": "Nicolas"},
        ).status_code == 200
        # Criss picks one row, the way the row PUT always has.
        assert client.put(
            f"/api/runs/{august}/expenses/{picked}",
            json={"field": "card_key", "value": "card-0340"},
        ).status_code == 200

        # The dry run names the same rows and writes nothing.
        dry = client.post(
            f"/api/expense-batches/{august}/cards/by-vendor",
            json={"vendor": "Lovable", "card_key": "3645", "dry_run": True},
        )
        assert dry.status_code == 200 and dry.json()["n_changed"] == 0
        assert sorted(dry.json()["documents"]) == sorted([target, target2])
        after_dry = {e["document_id"]: e for e in client.get(
            f"/api/expense-batches/{august}").json()["expenses"]}
        assert after_dry[target]["card"] is None and after_dry[target2]["card"] is None

        resp = client.post(
            f"/api/expense-batches/{august}/cards/by-vendor",
            json={"vendor": "lovable ", "card_key": "3645"},
        )
        assert resp.status_code == 200, resp.text
        assert sorted(resp.json()["documents"]) == sorted([target, target2])
        assert resp.json()["n_changed"] == 2

        rows = {e["document_id"]: e for e in client.get(
            f"/api/expense-batches/{august}").json()["expenses"]}
        for doc in (target, target2):
            assert rows[doc]["card"]["key"] == "3645"
            assert rows[doc]["card_source"] == "override"
        assert rows[picked]["card"]["key"] == "card-0340"
        assert rows[printed]["card"]["key"] == "card-2838"
        assert rows[private]["private"] is True and rows[private]["card"] is None
        assert rows[copies[0]]["card"] is None

        # Idempotent: nothing is left to write.
        again = client.post(
            f"/api/expense-batches/{august}/cards/by-vendor",
            json={"vendor": "Lovable", "card_key": "3645"},
        )
        assert again.status_code == 200 and again.json()["documents"] == []


def test_apply_to_vendor_refuses_an_undefined_card_and_a_bad_body(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [_receipt("2026-08-01", "30.00", "Lovable")]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        august = _month(client, "August 2026", 1)
        bad = client.post(
            f"/api/expense-batches/{august}/cards/by-vendor",
            json={"vendor": "Lovable", "card_key": "card-4242"},
        )
        assert bad.status_code == 400 and bad.json()["code"] == "card_not_defined"
        empty = client.post(
            f"/api/expense-batches/{august}/cards/by-vendor", json={"vendor": "Lovable"},
        )
        assert empty.json()["code"] == "vendor_and_card_required"
        row = next(iter(_rows(client, august).values()))
        assert row["card"] is None


def test_targets_skip_copies_and_printed_digits():
    rows = [
        {"document_id": "a", "vendor": {"display": "Proton"}, "card": None, "card_source": "none"},
        {"document_id": "b", "vendor": {"display": "Proton"}, "card": None, "card_source": "none",
         "counts_in_total": False},
        {"document_id": "c", "vendor": {"display": "Proton"}, "card": None, "card_source": "none",
         "payment_hint": "card ending 1234"},
        {"document_id": "d", "vendor": {"display": "Proton AG"}, "card": None, "card_source": "none"},
    ]
    assert card_by_vendor_targets(rows, "PROTON") == ["a"]


# ── 4. a statement says which month it belongs to ───────────────────────


def test_a_cycle_file_names_its_majority_month_and_advises(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [_receipt("2026-08-10", "5.00", "Cafe")]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        august = _month(client, "August 2026", 1)
        _done(client, _statement(client, august, (
            ("2026-07-06", "1.00", "A", "2838"),
            ("2026-07-10", "2.00", "B", "2838"),
            ("2026-07-20", "3.00", "C", "3645"),
            ("2026-08-01", "4.00", "D", "3645"),
            ("2026-08-04", "5.00", "E", "3645"),
        ), name="cycle-20260804.csv"))
        entry = client.get(f"/api/runs/{august}").json()["statements"][-1]
        assert entry["month_suggestion"] == {
            "month": "2026-07", "label_month": "2026-08",
            "n_dates": 5, "n_in_month": 3,
        }
        assert "July 2026" in entry["advisory"] and "August 2026" in entry["advisory"]
        assert entry["advisory_detail"]["code"] == "statement_month_differs"


def test_a_file_for_its_own_month_gets_no_advisory(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [_receipt("2026-07-01", "42.50", "Staples")]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, JULY_EXPORT))
        entry = client.get(f"/api/runs/{july}").json()["statements"][-1]
        assert entry["month_suggestion"]["month"] == "2026-07"
        assert entry["month_suggestion"]["label_month"] == "2026-07"
        assert entry["advisory"] is None
