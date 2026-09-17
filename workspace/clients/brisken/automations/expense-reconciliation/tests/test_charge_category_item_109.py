"""Item 109: a category can be set on a charge, and sign-off learns it.

71 of July's 112 charges and 98 of August's 111 hold no receipt, each with a
category the model guessed from the bank's description and no control to
correct it: every category route needs a receipt, and learning read receipts
only. So the guess went into the reconciled CSV as it was and the same
subscription was guessed again the next month.

Route-level through the real app, behind the password gate:

* the guess says it is a guess and that the row can be edited;
* `PUT /api/runs/{id}/charges/{tx}/category` stores the reviewer's pick under
  the charge (the one `category_overrides` table, at the charge's own
  pseudo-receipt id), it reads `EDITED` like a receipt's own edit, and the row
  stops counting as a guess;
* the pick outlives a re-match that rewrites the whole snapshot, and reaches
  the reconciled CSV and the reconciliation report;
* sign-off (Publish) teaches it under the bank's normalized description, so
  the next month recalls it -- while a model guess teaches nothing, and two
  charges of one vendor given two categories teach nothing either (the
  conflict-skip rule categories already use).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-109"
CRISS_CODE = "criss-code-109"

HEADERS = ("Date", "Description", "Type", "Amount")
LOVABLE = (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00)
# The vendor keyword table names a category for an Uber vendor, so the fee
# carries a guess with no receipt behind it. A fee needs no receipt, so the
# guess is the only thing holding the month open.
FEE = (datetime(2026, 8, 20), "UBER ONE ANNUAL FEE", "Fee", -95.00)
FEE_2 = (datetime(2026, 8, 22), "UBER ONE ANNUAL FEE", "Fee", -95.00)
# No keyword matches it, so this charge carries no guess at all.
PRESSMASTER = (datetime(2026, 8, 18), "PRESSMASTER FZCO", "Sale", -220.00)
PAYMENT = (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 111.00)

SEPT_FEE = (datetime(2026, 9, 20), "UBER ONE ANNUAL FEE", "Fee", -95.00)
SEPT_PAYMENT = (datetime(2026, 9, 4), "Payment Thank You-Mobile", "Payment", 95.00)

ENTITY = "Corporate Services"
PICK = "Professional Services"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODES", f"{CRISS_CODE}:criss")
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        login = c.post("/api/login", json={"code": CRISS_CODE})
        assert login.status_code == 200, login.text
        c.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
        yield c


def _extraction(vendor, total, date, currency="USD"):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create_batch(client, n_receipts, label="August 2026", seed=0):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": ENTITY, "label": label}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if n_receipts:
        _add_receipts(client, batch_id, n_receipts, seed)
    return batch_id


def _add_receipts(client, batch_id, n, seed=0):
    files = [
        ("files", (f"r{seed}-{i}.jpg", JPG + bytes([seed, i]),
                   "application/octet-stream"))
        for i in range(n)
    ]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts", files=files
    ))


def _attach(client, batch_id, rows, name="August2026.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            name, buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


def _rows(view, vendor):
    return [r for r in view["rows"] if r["vendor"] == vendor]


def _decide(client, batch_id, tx_id, status):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": status},
    )
    assert resp.status_code == 200, resp.text


def _month(client, monkeypatch, rows, *extractions, label="August 2026",
           name="August2026.xlsx", seed=0):
    _wire(monkeypatch, *extractions)
    batch_id = _create_batch(client, len(extractions), label=label, seed=seed)
    _attach(client, batch_id, rows, name=name)
    for r in _view(client, batch_id)["rows"]:
        if r["turn"] == "decide":
            _decide(client, batch_id, r["transaction_id"], "confirmed")
    return batch_id


def _set_category(client, batch_id, tx_id, category, zoho_account=None):
    body: dict = {"category": category}
    if zoho_account is not None:
        body["zoho_account"] = zoho_account
    return client.put(
        f"/api/runs/{batch_id}/charges/{tx_id}/category", json=body
    )


def _publish(client, batch_id):
    resp = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _learned_categories(client):
    resp = client.get("/api/memory")
    assert resp.status_code == 200, resp.text
    return {
        (r["entity"], r["vendor"]): r["category"]
        for r in resp.json()["categories"]
    }


# ── the guess says it is a guess ───────────────────────────────────────


def test_a_receiptless_guess_says_it_was_guessed_and_that_the_row_is_editable(
    client, monkeypatch
):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    view = _view(client, batch)
    fee = _row(view, "UBER ONE ANNUAL FEE")
    assert fee["charge_category"]["category"] == "Travel & Transport"
    assert fee["charge_category"]["source"] == "VENDOR"
    assert "is_edited" not in fee["charge_category"]
    assert fee["review"]["reason_code"] == "receiptless_suggested"
    reason = fee["review"]["reason"].lower()
    assert "guessed" in reason, fee["review"]
    assert "pick the right one on the row" in reason, fee["review"]
    assert view["summary"]["n_charges_category_guessed"] == 1

    # A charge no keyword matches carries no guess and no question.
    press = _row(view, "PRESSMASTER FZCO")
    assert press["charge_category"] is None
    assert press["review"]["state"] == "none"


# ── the edit ───────────────────────────────────────────────────────────


def test_a_category_set_on_a_charge_reads_as_an_edit_and_is_no_longer_a_guess(
    client, monkeypatch
):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    fee = _row(_view(client, batch), "UBER ONE ANNUAL FEE")
    assert _set_category(client, batch, fee["transaction_id"], PICK).status_code == 200

    view = _view(client, batch)
    fee = _row(view, "UBER ONE ANNUAL FEE")
    assert fee["charge_category"]["category"] == PICK
    assert fee["charge_category"]["source"] == "EDITED"
    assert fee["charge_category"]["is_edited"] is True
    assert fee["posting_category"]["category"] == PICK
    assert fee["posting_category"]["source"] == "EDITED"
    assert fee["review"]["state"] == "none", "an answer is not a question"
    assert view["summary"]["n_charges_category_guessed"] == 0


def test_a_charge_with_no_guess_at_all_can_be_given_one(client, monkeypatch):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    press = _row(_view(client, batch), "PRESSMASTER FZCO")
    assert press["charge_category"] is None
    resp = _set_category(
        client, batch, press["transaction_id"], "Software & Subscriptions"
    )
    assert resp.status_code == 200, resp.text

    press = _row(_view(client, batch), "PRESSMASTER FZCO")
    assert press["charge_category"]["category"] == "Software & Subscriptions"
    assert press["charge_category"]["source"] == "EDITED"
    assert press["posting_category"]["category"] == "Software & Subscriptions"


def test_clearing_the_pick_brings_the_tools_guess_back(client, monkeypatch):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    tx = _row(_view(client, batch), "UBER ONE ANNUAL FEE")["transaction_id"]
    assert _set_category(client, batch, tx, PICK).status_code == 200
    assert _set_category(client, batch, tx, "").status_code == 200

    fee = _row(_view(client, batch), "UBER ONE ANNUAL FEE")
    assert fee["charge_category"]["category"] == "Travel & Transport"
    assert fee["charge_category"]["source"] == "VENDOR"
    assert _view(client, batch)["summary"]["n_charges_category_guessed"] == 1


def test_the_route_refuses_what_it_should(client, monkeypatch):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    view = _view(client, batch)
    fee = _row(view, "UBER ONE ANNUAL FEE")

    outside = _set_category(client, batch, fee["transaction_id"], "Groceries")
    assert outside.status_code == 400, outside.text

    unknown = _set_category(client, batch, "no-such-charge", PICK)
    assert unknown.status_code == 404, unknown.text

    lovable = _row(view, "LOVABLE")
    assert lovable["effective_bucket"] == "reconciled"
    held = _set_category(client, batch, lovable["transaction_id"], PICK)
    assert held.status_code == 400, held.text
    assert "holds a receipt" in held.json()["error"]

    gone = client.put(f"/api/runs/nope/charges/{fee['transaction_id']}/category",
                      json={"category": PICK})
    assert gone.status_code == 404, gone.text


# ── it outlives a re-match ─────────────────────────────────────────────


def test_the_pick_survives_a_re_match(client, monkeypatch):
    """A re-match rewrites the whole snapshot, `charge_categorizations`
    included. The pick lives in `category_overrides`, which only deleting
    the month clears, so it is laid over the fresh guess again."""
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    tx = _row(_view(client, batch), "UBER ONE ANNUAL FEE")["transaction_id"]
    assert _set_category(client, batch, tx, PICK).status_code == 200

    before = client.get("/api/operator/state").json()
    n_before = len([e for e in before["rematches"] if e["run_id"] == batch])
    _wire(monkeypatch, _extraction("Redis Inc.", "13200.00", "2026-08-12"))
    _add_receipts(client, batch, 1, seed=9)
    after = client.get("/api/operator/state").json()
    triggers = [e["trigger"] for e in after["rematches"] if e["run_id"] == batch]
    assert len(triggers) > n_before, ("the month never re-matched", triggers)

    fee = _row(_view(client, batch), "UBER ONE ANNUAL FEE")
    assert fee["transaction_id"] == tx
    assert fee["charge_category"]["category"] == PICK
    assert fee["charge_category"]["source"] == "EDITED"


# ── it reaches the documents ───────────────────────────────────────────


def test_the_pick_reaches_the_reconciled_csv_and_the_report(client, monkeypatch):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    tx = _row(_view(client, batch), "UBER ONE ANNUAL FEE")["transaction_id"]
    assert _set_category(client, batch, tx, PICK).status_code == 200

    resp = client.get(f"/runs/{batch}/reconciled.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    fee_row = next(r for r in rows if r["Description"] == "UBER ONE ANNUAL FEE")
    assert fee_row["Charge Category"] == PICK
    assert fee_row["Charge Category Source"] == "EDITED"
    # A matched line keeps its blank charge columns: the pick is a charge's.
    lovable_row = next(r for r in rows if r["Description"] == "LOVABLE")
    assert lovable_row["Charge Category"] == ""

    resp = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    pages = [
        " ".join((p.extract_text() or "").split())
        for p in PdfReader(io.BytesIO(resp.content)).pages
    ]
    assert any(PICK in p for p in pages), "the report never printed the pick"
    assert not any("Travel & Transport" in p for p in pages), (
        "the report still prints the guess the reviewer replaced"
    )


def test_the_pick_posts_to_the_journal_where_a_learned_one_does(
    client, monkeypatch
):
    """The journal's receiptless rows are the Tier-1 ones behind the opt-in
    `zoho.export_receiptless_learned` flag. A category the reviewer set is
    Tier-1 too, so it joins them; a guess still stays out."""
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch)
        config = dict(run.config or {})
        config["zoho"] = {**(config.get("zoho") or {}), "export_receiptless_learned": True}
        assert store.update_run_config(batch, config)

    guessed = client.get(f"/runs/{batch}/zoho.csv")
    assert guessed.status_code == 200, guessed.text
    assert "UBER ONE ANNUAL FEE" not in guessed.text, "a guess posted itself"

    tx = _row(_view(client, batch), "UBER ONE ANNUAL FEE")["transaction_id"]
    assert _set_category(client, batch, tx, PICK).status_code == 200
    posted = client.get(f"/runs/{batch}/zoho.csv")
    assert posted.status_code == 200, posted.text
    assert "UBER ONE ANNUAL FEE" in posted.text
    assert PICK in posted.text


# ── sign-off teaches it, and teaches only it ───────────────────────────


def test_a_model_guess_on_a_charge_is_not_learned_at_sign_off(client, monkeypatch):
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    assert _row(_view(client, batch), "UBER ONE ANNUAL FEE")[
        "charge_category"]["source"] == "VENDOR"

    reply = _publish(client, batch)
    assert reply["memory"]["saved"] is True, reply
    assert (ENTITY, "uber one annual fee") not in _learned_categories(client)


def test_a_reviewer_category_is_learned_at_sign_off_and_recalled_next_month(
    client, monkeypatch
):
    august = _month(
        client, monkeypatch, [LOVABLE, FEE, PRESSMASTER, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    tx = _row(_view(client, august), "UBER ONE ANNUAL FEE")["transaction_id"]
    assert _set_category(client, august, tx, PICK).status_code == 200

    reply = _publish(client, august)
    assert reply["memory"]["learned"]["merchant_categories"] >= 1, reply
    assert _learned_categories(client)[(ENTITY, "uber one annual fee")] == PICK

    september = _month(
        client, monkeypatch, [SEPT_FEE, SEPT_PAYMENT],
        label="September 2026", name="September2026.xlsx", seed=3,
    )
    fee = _row(_view(client, september), "UBER ONE ANNUAL FEE")
    assert fee["charge_category"]["category"] == PICK, (
        "next month guessed again instead of recalling the correction"
    )
    assert fee["charge_category"]["source"] == "LEARNED"
    assert fee["charge_category"]["is_learned"] is True


def test_two_charges_of_one_vendor_given_two_categories_teach_nothing(
    client, monkeypatch
):
    """The conflict-skip rule categories already use: a vendor whose
    overrides disagree is counted and skipped, never taught one of the two."""
    batch = _month(
        client, monkeypatch, [LOVABLE, FEE, FEE_2, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
    )
    first, second = _rows(_view(client, batch), "UBER ONE ANNUAL FEE")
    assert _set_category(client, batch, first["transaction_id"], PICK).status_code == 200
    assert _set_category(
        client, batch, second["transaction_id"], "Software & Subscriptions"
    ).status_code == 200

    reply = _publish(client, batch)
    assert reply["memory"]["learned"]["skipped_mixed_category"] == 1, reply
    assert (ENTITY, "uber one annual fee") not in _learned_categories(client)
