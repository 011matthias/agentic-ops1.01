"""Item 220 step 3 (front 2): a statement upload's DECLARED period, and a
family's subcards covered only by what an upload printed or declared.

Live on 2026-09-27: September's `Chase9693_2026-09_posted_0906-0915_from-
SharePoint.xlsx` printed charges 09-04 to 09-14, so a 9693 receipt dated
09-15 waited for a statement the file had already asked for; and August's
`August2026.xlsx` printed no 0340 charge while August's two card-less rows
read 0340 as covered, because one printed 2838 charge covered the whole
family. The April 2026 activity CSV of the 2838 account carried no 3876
charge at all, so an upload that did not print a subcard and declares no
period says nothing about it.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon import statement_declared as sd  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.unmatched_reasons import (  # noqa: E402
    CARD_STATEMENT_NOT_LOADED,
    CHARGE_IN_NEIGHBOURING_PERIOD,
    NO_CHARGE_ON_ANY_LOADED_STATEMENT,
    STATEMENT_NOT_LOADED_FOR_DATE,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

CARD_9693 = {"card-9693": {"label": "BCS Chase Visa - 9693", "digits": ["9693"],
                           "entity": "Consulting"}}
FAMILY = {
    "card-2838": {"label": "Corp Chase - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "card-0340": {"label": "Corp Chase Visa - 0340", "digits": ["0340"],
                  "entity": "Corporate Services", "parent": "card-2838"},
}
LABEL_9693 = "BCS Chase Visa - 9693"
LABEL_0340 = "Corp Chase Visa - 0340"


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
    client = TestClient(create_app(tmp_path))
    client._data_root = tmp_path
    return client


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


def _csv(client, batch_id, name, account, rows):
    body = "Date,Amount,Vendor,Card\n" + "".join(f"{d},{a},{v},{c}\n" for d, a, v, c in rows)
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body.encode(), "application/octet-stream")},
        data={
            "account_id": account,
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    ))


def _by_vendor(client, month):
    run = client.get(f"/api/runs/{month}").json()
    unmatched = {str(r.get("vendor")): r for r in run["unmatched_receipts"]}
    batch = client.get(f"/api/expense-batches/{month}").json()
    expenses = {str((e.get("vendor") or {}).get("raw") or (e.get("vendor") or {}).get("display")): e
                for e in batch["expenses"]}
    return run, unmatched, expenses


# ── the posted range a SharePoint export names ──────────────────────────

SEPT_9693 = (
    ("2026-09-04", "10.00", "STAPLES", "9693"),
    ("2026-09-14", "11.00", "UBER", "9693"),
)
READ_9693 = [
    # The day after the last printed charge, inside the posted range.
    _receipt("2026-09-15", "50.00", "Day After", hint="Visa ...9693"),
    # After the posted range too.
    _receipt("2026-09-16", "51.00", "Two Days After", hint="Visa ...9693"),
]


def test_a_posted_range_in_the_name_covers_the_days_it_asked_for(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_9693) as client:
        assert client.put("/api/settings", json={"cards": CARD_9693}).status_code == 200
        sept = _month(client, "September 2026", len(READ_9693))
        _csv(client, sept, "Chase9693_2026-09_posted_0906-0915_from-SharePoint.csv",
             "card-9693", SEPT_9693)
        run, rec, _exp = _by_vendor(client, sept)
        (entry,) = run["statements"]
        assert entry["period_start"] == "2026-09-04"
        assert entry["period_end"] == "2026-09-14"
        assert entry["period_declared_start"] == "2026-09-06"
        assert entry["period_declared_end"] == "2026-09-15"
        # 09-15 is inside what the file asked for: read at the edge, not waiting.
        assert rec["Day After"]["reason_code"] == CHARGE_IN_NEIGHBOURING_PERIOD
        assert "waits_for_statements" not in rec["Day After"]
        assert rec["Two Days After"]["reason_code"] == STATEMENT_NOT_LOADED_FOR_DATE
        assert rec["Two Days After"]["waits_for_statements"] == [LABEL_9693]
        assert run["summary"]["n_receipts_waiting_statement"] == 1


def test_an_unnamed_export_declares_nothing(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_9693) as client:
        assert client.put("/api/settings", json={"cards": CARD_9693}).status_code == 200
        sept = _month(client, "September 2026", len(READ_9693))
        _csv(client, sept, "export.csv", "card-9693", SEPT_9693)
        run, rec, _exp = _by_vendor(client, sept)
        (entry,) = run["statements"]
        assert "period_declared_start" not in entry
        assert "period_declared_end" not in entry
        assert rec["Day After"]["reason_code"] == STATEMENT_NOT_LOADED_FOR_DATE


def test_a_stored_workbook_entry_reads_its_range_off_the_name(tmp_path, monkeypatch):
    """An entry attached before the fields existed: the range comes off
    `upload_name` at read time, no re-read (a write on Criss's month)."""
    with _client(tmp_path, monkeypatch, READ_9693) as client:
        assert client.put("/api/settings", json={"cards": CARD_9693}).status_code == 200
        sept = _month(client, "September 2026", len(READ_9693))
        _csv(client, sept, "Chase9693_2026-09_posted_0906-0915_from-SharePoint.csv",
             "card-9693", SEPT_9693)
        with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
            run = store.get_run(sept)
            snap = dict(run.snapshot)
            snap["statements"] = [
                {k: v for k, v in e.items() if not k.startswith("period_declared")}
                for e in snap["statements"]
            ]
            store.update_run_snapshot(sept, snap)
        run, rec, _exp = _by_vendor(client, sept)
        assert "period_declared_end" not in run["statements"][0]
        assert rec["Day After"]["reason_code"] == CHARGE_IN_NEIGHBOURING_PERIOD


# ── a family's subcards: printed or declared, never assumed ─────────────

FAMILY_ROWS = (
    ("2026-09-02", "20.00", "STAPLES", "2838"),
    ("2026-09-28", "21.00", "UBER", "2838"),
)
READ_BLANK = [_receipt("2026-09-10", "60.00", "Blank Card")]


def test_a_subcard_the_upload_did_not_print_is_not_covered(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_BLANK) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        sept = _month(client, "September 2026", 1)
        _csv(client, sept, "September2026.csv", "card-2838", FAMILY_ROWS)
        run, rec, exp = _by_vendor(client, sept)
        # 0340 has no statement anywhere and the 2838 file printed none of it.
        assert rec["Blank Card"]["reason_code"] == CARD_STATEMENT_NOT_LOADED
        assert rec["Blank Card"]["waits_for_statements"] == [LABEL_0340]
        assert exp["Blank Card"]["waits_for_statements"] == [LABEL_0340]
        assert run["summary"]["receipts_waiting_cards"] == [LABEL_0340]


def test_a_family_upload_that_declares_its_period_covers_the_subcards(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_BLANK) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        sept = _month(client, "September 2026", 1)
        _csv(client, sept, "Chase2838_2026-09_posted_0901-0930_from-SharePoint.csv",
             "card-2838", FAMILY_ROWS)
        run, rec, exp = _by_vendor(client, sept)
        assert rec["Blank Card"]["reason_code"] == NO_CHARGE_ON_ANY_LOADED_STATEMENT
        assert "waits_for_statements" not in rec["Blank Card"]
        assert "waits_for_statements" not in exp["Blank Card"]
        assert run["summary"]["n_receipts_waiting_statement"] == 0


def test_a_subcard_the_upload_printed_is_covered_for_its_span(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_BLANK) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        sept = _month(client, "September 2026", 1)
        _csv(client, sept, "September2026.csv", "card-2838",
             FAMILY_ROWS + (("2026-09-20", "22.00", "LYFT", "0340"),))
        _run, rec, _exp = _by_vendor(client, sept)
        assert rec["Blank Card"]["reason_code"] == NO_CHARGE_ON_ANY_LOADED_STATEMENT


# ── a cycle PDF records its Opening/Closing Date ─────────────────────────

PDF_1176 = """\
Opening/Closing Date 07/06/26 - 08/04/26
ACCOUNT ACTIVITY
07/10 AWS CLOUD SERVICES 100.00
07/12 GITHUB INC 21.00
TRANSACTIONS THIS CYCLE (CARD 1176) $121.00
"""
CARD_1176 = {"card-1176": {"label": "BCS Chase Visa - 1176", "digits": ["1176"],
                           "entity": "Consulting"}}


def test_a_cycle_pdf_records_the_period_it_prints(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages", lambda path: [PDF_1176]
    )
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-08-03", "70.00", "Cycle End", hint="Visa ...1176"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": CARD_1176}).status_code == 200
        aug = _month(client, "August 2026", 1)
        _done(client, client.post(
            f"/api/expense-batches/{aug}/statement",
            files={"statement": ("20260804-statements-1176-.pdf",
                                 b"%PDF-1.4 synthetic", "application/pdf")},
            data={"account_id": "card-1176", "account_card_currency": "USD"},
        ))
        run, rec, _exp = _by_vendor(client, aug)
        (entry,) = run["statements"]
        assert entry["period_end"] == "2026-07-12"
        assert entry["period_declared_start"] == "2026-07-06"
        assert entry["period_declared_end"] == "2026-08-04"
        # 08-03 sits inside the cycle the PDF closes on 08-04.
        assert rec["Cycle End"]["reason_code"] != STATEMENT_NOT_LOADED_FOR_DATE
        assert "waits_for_statements" not in rec["Cycle End"]


# ── the readers, pure ───────────────────────────────────────────────────


@pytest.mark.parametrize("name, want", [
    ("Chase9693_2026-09_posted_0906-0915_from-SharePoint.xlsx",
     (date(2026, 9, 6), date(2026, 9, 15))),
    ("Chase1176_2026-07_posted_0701-0702_from-SharePoint-2.xlsx",
     (date(2026, 7, 1), date(2026, 7, 2))),
    ("chase1176_2026-12_posted_1215-0105.csv", (date(2026, 12, 15), date(2027, 1, 5))),
    ("Chase1176_2027-01_posted_1230-0105.csv", (date(2026, 12, 30), date(2027, 1, 5))),
    ("July2026.xlsx", None),
    ("20260904-statements-9693-.pdf", None),
    ("Chase9693_2026-02_posted_0230-0231.xlsx", None),
    ("", None),
])
def test_the_posted_range_reader(name, want):
    assert sd.from_upload_name(name) == want


def test_the_pdf_period_keeps_its_days():
    assert sd.from_pdf_text(PDF_1176) == (date(2026, 7, 6), date(2026, 8, 4))
    assert sd.from_pdf_text("ACCOUNT ACTIVITY") is None


def test_an_entry_reads_recorded_fields_first_and_a_pdf_name_never():
    recorded = {"file": "x.xlsx", "period_declared_start": "2026-09-01",
                "period_declared_end": "2026-09-03"}
    assert sd.of_entry(recorded) == (date(2026, 9, 1), date(2026, 9, 3))
    stored = {"file": "Chase9693_2026-09_posted_0906-0915_from-SharePoint-2.xlsx",
              "upload_name": "Chase9693_2026-09_posted_0906-0915_from-SharePoint.xlsx"}
    assert sd.of_entry(stored) == (date(2026, 9, 6), date(2026, 9, 15))
    assert sd.of_entry({"file": "20260904-statements-9693-.pdf"}) is None
    assert sd.entry_fields(None) == {}


# ── step 4: a card whose statements will never be loaded ────────────────

APPLE = {"label": "Apple Credit Card - 0113", "digits": ["0113"],
         "entity": "Consulting", "statement_expected": False}
NO_APPLE = {**CARD_9693, "card-0113": APPLE}
READ_INSIDE = [
    # Card-less, inside the 9693 export: nothing left to wait for once the
    # Apple card is known to have no statement.
    _receipt("2026-09-08", "80.00", "Blank Inside"),
    # Printing the Apple card itself.
    _receipt("2026-09-08", "81.00", "Apple Printed", hint="Apple Card ...0113"),
]


def _settings_cards(client) -> dict:
    return {c["key"]: c for c in client.get("/api/settings").json()["cards_effective"]}


def test_statement_expected_is_stored_validated_and_survives_a_save(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, []) as client:
        assert client.put("/api/settings", json={"cards": NO_APPLE}).status_code == 200
        cards = _settings_cards(client)
        assert cards["card-0113"]["statement_expected"] is False
        assert cards["card-9693"]["statement_expected"] is True
        # A Cards-editor save that does not know the field keeps it.
        unsent = {**CARD_9693, "card-0113": {k: v for k, v in APPLE.items()
                                             if k != "statement_expected"}}
        assert client.put("/api/settings", json={"cards": unsent}).status_code == 200
        assert _settings_cards(client)["card-0113"]["statement_expected"] is False
        # An explicit true clears it.
        sent = {**CARD_9693, "card-0113": {**APPLE, "statement_expected": True}}
        assert client.put("/api/settings", json={"cards": sent}).status_code == 200
        assert _settings_cards(client)["card-0113"]["statement_expected"] is True
        bad = {**CARD_9693, "card-0113": {**APPLE, "statement_expected": "no"}}
        resp = client.put("/api/settings", json={"cards": bad})
        assert resp.status_code == 400
        assert resp.json()["code"] == "invalid_body"


def test_nothing_waits_for_a_card_with_no_statement(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_INSIDE) as client:
        assert client.put("/api/settings", json={"cards": NO_APPLE}).status_code == 200
        sept = _month(client, "September 2026", len(READ_INSIDE))
        _csv(client, sept, "export.csv", "card-9693", SEPT_9693)
        run, rec, exp = _by_vendor(client, sept)
        assert rec["Blank Inside"]["reason_code"] == NO_CHARGE_ON_ANY_LOADED_STATEMENT
        assert "waits_for_statements" not in rec["Blank Inside"]
        assert "waits_for_statements" not in exp["Blank Inside"]
        assert rec["Apple Printed"]["reason_code"] == NO_CHARGE_ON_ANY_LOADED_STATEMENT
        assert "waits_for_statements" not in rec["Apple Printed"]
        assert run["summary"]["n_receipts_waiting_statement"] == 0
        assert "receipts_waiting_cards" not in run["summary"]


def test_a_card_expected_to_have_statements_is_still_waited_for(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, READ_INSIDE) as client:
        expected = {**CARD_9693, "card-0113": {**APPLE, "statement_expected": True}}
        assert client.put("/api/settings", json={"cards": expected}).status_code == 200
        sept = _month(client, "September 2026", len(READ_INSIDE))
        _csv(client, sept, "export.csv", "card-9693", SEPT_9693)
        _run, rec, exp = _by_vendor(client, sept)
        assert rec["Blank Inside"]["reason_code"] == CARD_STATEMENT_NOT_LOADED
        assert rec["Blank Inside"]["waits_for_statements"] == ["Apple Credit Card - 0113"]
        assert exp["Blank Inside"]["waits_for_statements"] == ["Apple Credit Card - 0113"]
        assert rec["Apple Printed"]["reason_code"] == CARD_STATEMENT_NOT_LOADED
