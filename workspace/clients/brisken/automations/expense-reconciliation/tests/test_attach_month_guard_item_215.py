"""Backlog item 215 (owner decision 2026-09-25): a statement attach keeps
only the month's own charges.

Criss's SharePoint card files are lifetime sheets (9693 since 2024, 724
rows; 1176, 154; the 2838 family, 2,729), and she uploads them into a month
herself. Before this the attach folded every row of the file into the month,
so one weekly upload would have copied two years of charges into it.

Now a company month keeps the rows whose POST date falls in its calendar
month (the transaction date when the file prints none), leaves out a row a
neighbouring month or another of its own files already holds under a
different reading, and says what it left out: on the `statements[]` entry
(`month_filter`), on the job's `result`, and in the job's warning sentence.
A label naming no month folds the whole file as before, and a re-read
applies the filter only to entries that carry it.

Every test here drives the real routes (attach, job poll, re-read).
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
POSTED = "Transaction Date,Post Date,Amount,Vendor\n"
PLAIN = "Date,Amount,Vendor\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="7.77", currency="USD",
                vendor="Corner Cafe", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * 12,
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1, implied_rate=1.0,
                converted_amount=Decimal("7.77"), reasoning="no",
            )
        ] * 60,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    return client.get(f"/jobs/{resp.json()['job_id']}").json()


def _batch(client, label: str) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert _done(client, resp)["status"] == "done"
    batch_id = resp.json()["batch_id"]
    added = _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"{label}.jpg", JPG + label.encode(),
                          "application/octet-stream"))],
    ))
    assert added["status"] == "done", added
    return batch_id


def _posted(*rows: tuple[str, str, str, str]) -> bytes:
    """Transaction date, post date, amount, vendor per row."""
    return (POSTED + "".join(f"{t},{p},{a},{v}\n" for t, p, a, v in rows)).encode()


def _plain(*rows: tuple[str, str, str]) -> bytes:
    return (PLAIN + "".join(f"{d},{a},{v}\n" for d, a, v in rows)).encode()


def _attach(client, batch_id, body: bytes, *, account: str, name: str,
            posted: bool = True) -> dict:
    data = {
        "account_id": account,
        "account_legal_entities": f'{{"{account}": "Corporate Services"}}',
        "account_card_currency": "USD",
        "map_amount": "Amount",
        "map_vendor": "Vendor",
    }
    if posted:
        data["map_transaction_date"] = "Transaction Date"
        data["map_posting_date"] = "Post Date"
    else:
        data["map_transaction_date"] = "Date"
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data=data,
    ))


def _attach_before_the_guard(client, monkeypatch, batch_id, body, **kw) -> dict:
    """An attach as it ran before item 215: the whole file folds. That is
    how the live cycle PDFs in August and September were attached, so it is
    how a neighbour holds another month's charges."""
    guard = service.month_calendar_range
    monkeypatch.setattr(service, "month_calendar_range", lambda run: None)
    try:
        return _attach(client, batch_id, body, **kw)
    finally:
        monkeypatch.setattr(service, "month_calendar_range", guard)


def _stored(client, batch_id):
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    snap = run.snapshot or {}
    return (
        Path(run.work_dir),
        list(snap.get("statements") or []),
        sorted(
            (t["transaction_date"], t["amount"], t["vendor_from_statement"])
            for t in snap.get("transactions") or []
        ),
    )


# A lifetime sheet: two years of one card, three rows of them April's.
LIFETIME = _posted(
    ("2024-11-03", "2024-11-04", "12.00", "OLD SHOP"),
    ("2026-03-30", "2026-03-31", "20.00", "MARCH SHOP"),
    ("2026-03-31", "2026-04-01", "30.00", "POSTED IN APRIL"),
    ("2026-04-15", "2026-04-16", "40.00", "MID APRIL"),
    ("2026-04-29", "2026-04-30", "50.00", "LATE APRIL"),
    ("2026-04-30", "2026-05-01", "60.00", "POSTED IN MAY"),
    ("2026-06-10", "2026-06-11", "70.00", "JUNE SHOP"),
)


def test_a_lifetime_sheet_folds_only_the_months_own_charges(client):
    batch_id = _batch(client, "April 2026")

    job = _attach(client, batch_id, LIFETIME, account="card-9693",
                  name="Chase9693_Activity2024_Start.csv")

    assert job["status"] == "done", job
    _work, statements, charges = _stored(client, batch_id)
    assert [v for _d, _a, v in charges] == [
        "POSTED IN APRIL", "MID APRIL", "LATE APRIL",
    ]
    entry = statements[0]
    assert entry["month_filter"] == {
        "month": "2026-04",
        "n_file_rows": 7,
        "n_kept": 3,
        "n_left_out": 4,
        "outside_month": {"2024-11": 1, "2026-03": 1, "2026-05": 1, "2026-06": 1},
        "already_held": {},
    }
    assert entry["n_rows"] == 3 and entry["n_new"] == 3
    # The filter decided the month, so there is no month to suggest.
    assert "month_suggestion" not in entry
    assert entry["advisory"] is None
    # The reply says it in numbers and in the sentence the SPA already shows.
    assert job["result"]["month_filter"] == entry["month_filter"]
    assert job["stage"] == (
        "warning: Kept 3 of this file's 7 charges for April 2026: 4 belong "
        "to other months (November 2024 to June 2026)."
    )


def test_the_post_date_decides_not_the_transaction_date(client):
    """The measured rule: the loaded months split by POST date exactly. A
    charge made on 31 March that posted on 1 April is April's; one made on
    30 April that posted on 1 May is not."""
    batch_id = _batch(client, "April 2026")

    _attach(client, batch_id, LIFETIME, account="card-9693", name="life.csv")

    _work, _statements, charges = _stored(client, batch_id)
    assert ("2026-03-31", "30.00", "POSTED IN APRIL") in charges
    assert not any(v == "POSTED IN MAY" for _d, _a, v in charges)


def test_a_file_with_no_post_date_folds_whole(client):
    """A Chase cycle PDF prints no post date and spans two calendar months
    by design (August's 9693 PDF runs Jul 3 to Aug 4). Cut by transaction
    date, its July rows would leave August and land nowhere, so a file
    without post dates folds whole, as before."""
    batch_id = _batch(client, "August 2026")

    job = _attach(client, batch_id, _plain(
        ("2026-07-03", "118.52", "TWILIO SENDGRID"),
        ("2026-08-04", "39.99", "BLOOMBERG"),
    ), account="9693", name="20260804-statements-9693-.csv", posted=False)

    assert job["status"] == "done", job
    _work, statements, charges = _stored(client, batch_id)
    assert len(charges) == 2
    assert "month_filter" not in statements[0]
    assert "result" not in job


def test_a_row_a_neighbour_holds_under_another_reading_is_left_out(
    client, monkeypatch
):
    """The 9693 shape: May's cycle PDF (account `9693`, long vendor text)
    already holds the charge made on 29 April; the SharePoint export
    (account `card-9693`, short text) posts it on 30 April. Same charge, two
    ids, and before this it would have landed in both months."""
    may = _batch(client, "May 2026")
    _attach_before_the_guard(client, monkeypatch, may, _plain(
        ("2026-04-29", "50.00", "LATE APRIL ANTHROPIC.COM CA"),
        ("2026-05-03", "80.00", "MAY SHOP"),
    ), account="9693", name="20260504-statements-9693-.csv", posted=False)
    april = _batch(client, "April 2026")

    job = _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    _work, statements, charges = _stored(client, april)
    assert [v for _d, _a, v in charges] == ["POSTED IN APRIL", "MID APRIL"]
    mf = statements[0]["month_filter"]
    assert mf["already_held"] == {"2026-05": 1}
    assert mf["n_left_out"] == 5 and mf["n_kept"] == 2
    assert job["stage"].endswith("; 1 are already in May 2026.")


def test_a_row_another_file_of_the_month_holds_is_left_out(client):
    """September's shape: the month's own cycle PDF prints the first days of
    the month too, under a different reading."""
    april = _batch(client, "April 2026")
    _attach(client, april, _plain(
        ("2026-04-15", "40.00", "MID APRIL WWW.SHOP.COM"),
    ), account="9693", name="cycle.csv", posted=False)

    _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    _work, statements, charges = _stored(client, april)
    assert sorted(v for _d, _a, v in charges) == [
        "LATE APRIL", "MID APRIL WWW.SHOP.COM", "POSTED IN APRIL",
    ]
    assert statements[1]["month_filter"]["already_held"] == {"2026-04": 1}


def test_a_neighbour_holding_one_of_two_identical_charges_leaves_the_other(
    client, monkeypatch
):
    may = _batch(client, "May 2026")
    _attach_before_the_guard(client, monkeypatch, may, _plain(
        ("2026-04-29", "5.00", "COFFEE ANTHROPIC CA"),
    ), account="9693", name="cycle.csv", posted=False)
    april = _batch(client, "April 2026")

    _attach(client, april, _posted(
        ("2026-04-29", "2026-04-30", "5.00", "COFFEE"),
        ("2026-04-29", "2026-04-30", "5.00", "COFFEE"),
    ), account="card-9693", name="two.csv")

    _work, statements, charges = _stored(client, april)
    assert charges == [("2026-04-29", "5.00", "COFFEE")]
    assert statements[0]["month_filter"]["already_held"] == {"2026-05": 1}


def test_a_resupplied_file_is_the_folds_business_not_a_left_out(client):
    """The same export twice: the second copy's April rows are the month's
    own reading (same ids), so `n_new` says it, and nothing reads as held."""
    april = _batch(client, "April 2026")
    _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    job = _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    _work, statements, charges = _stored(client, april)
    assert len(charges) == 3
    second = statements[1]
    assert second["n_rows"] == 3 and second["n_new"] == 0
    assert second["month_filter"]["already_held"] == {}
    assert job["status"] == "done"


def test_a_file_the_month_keeps_nothing_of_is_refused(client):
    april = _batch(client, "April 2026")

    job = _attach(client, april, _posted(
        ("2026-06-10", "2026-06-11", "70.00", "JUNE SHOP"),
    ), account="card-9693", name="june.csv")

    assert job["status"] == "error", job
    assert "None of the 1 charges in june.csv belong to this month" in job["error"]
    assert job["result"] == {
        "code": "statement_outside_month", "month": "2026-04",
        "n_file_rows": 1, "outside_month": {"2026-06": 1}, "already_held": {},
    }
    work_dir, statements, charges = _stored(client, april)
    assert statements == [] and charges == []
    assert not (work_dir / "june.csv").exists()


def test_a_label_naming_no_month_folds_the_whole_file(client):
    batch_id = _batch(client, "Board offsite")

    job = _attach(client, batch_id, LIFETIME, account="card-9693", name="life.csv")

    assert job["status"] == "done", job
    _work, statements, charges = _stored(client, batch_id)
    assert len(charges) == 7
    assert "month_filter" not in statements[0]
    assert "result" not in job


# ── the upload a restart-killed attach left behind ──────────────────────


def test_a_finished_attach_leaves_no_marker(client):
    april = _batch(client, "April 2026")

    _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    work_dir, _statements, _charges = _stored(client, april)
    assert list((work_dir / service.ATTACH_PENDING_DIR).glob("*.json")) == []
    assert (work_dir / "life.csv").is_file()


def test_boot_removes_the_upload_of_an_attach_a_restart_cut_off(client):
    """What a killed attach leaves: its saved upload and its marker, no
    `statements[]` entry. The next boot discards both; the month's recorded
    file and its report outputs, which share the suffixes, stay."""
    april = _batch(client, "April 2026")
    _attach(client, april, LIFETIME, account="card-9693", name="life.csv")
    work_dir, _s, _c = _stored(client, april)
    (work_dir / "report.xlsx").write_bytes(b"output")
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(april)
    (work_dir / "killed.csv").write_bytes(LIFETIME)
    service.mark_attach_pending(run, "deadjob00001", "killed.csv")
    service.mark_attach_pending(run, "deadjob00002", "life.csv")

    create_app(Path(client._data_root))

    assert not (work_dir / "killed.csv").exists()
    assert (work_dir / "life.csv").is_file()
    assert (work_dir / "report.xlsx").is_file()
    assert list((work_dir / service.ATTACH_PENDING_DIR).glob("*.json")) == []


def _reread(client, batch_id) -> dict:
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statements/reread"
    ))


def test_a_reread_keeps_the_filter_on_an_entry_attached_under_it(client):
    april = _batch(client, "April 2026")
    _attach(client, april, LIFETIME, account="card-9693", name="life.csv")

    job = _reread(client, april)

    assert job["status"] == "done", job
    _work, statements, charges = _stored(client, april)
    assert len(charges) == 3
    assert statements[0]["month_filter"]["n_kept"] == 3


def test_a_reread_leaves_an_entry_from_before_the_filter_whole(
    client, monkeypatch
):
    """An entry attached before the guard existed recorded no filter and
    folded the whole file; the re-read must read it back the same way."""
    april = _batch(client, "April 2026")
    _attach_before_the_guard(client, monkeypatch, april, LIFETIME,
                             account="card-9693", name="life.csv")
    _work, statements, before = _stored(client, april)
    assert "month_filter" not in statements[0] and len(before) == 7

    job = _reread(client, april)

    assert job["status"] == "done", job
    _work, statements, after = _stored(client, april)
    assert after == before
    assert "month_filter" not in statements[0]
