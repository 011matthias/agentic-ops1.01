"""Item 107: the month knows which receipts to chase and from whom.

Chasing receipts is the biggest thing Criss does by hand each month. She
reads the month for charges with nothing behind them, works out whose card
each one is, and mails Dirk and Nicolas herself; the tool knew every part of
that and offered none of it. Live 2026-09-17, August held 61 charges needing
a receipt across three card holders and there was no list, no request, no
"asked on this date", and no way to say a charge will never have one.

Route-level through the FastAPI app, because the contract is the payload and
the routes, not the helpers underneath them:

* the list groups the month's open charges by card holder and its groups sum
  to `summary.n_charges_need_receipt`, so the page and the count read one
  rule;
* "requested on {date}" closes nothing: the charge still needs a receipt and
  the month stays incomplete;
* "no receipt expected", with its reason, closes the charge, takes its money
  out of `unreconciled_by_ccy` into a total of its own, and `month_complete`
  follows;
* both states survive a re-match, because they live on the charge's own
  `decisions` row;
* the composer returns the mail and NOTHING sends: the send route refuses
  with the flag off and refuses with the flag on, because no sender is wired
  in this build at all.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CRISS_CODE = "criss-code-1"

DIRK = "Dirk Neumann"
NICOLAS = "Nicolas Neumann"
DIRK_ADDRESS = "dirk.neumann@brisken.com"

CARDS = {
    "corp-2838": {
        "label": "Corporate card 2838", "digits": ["2838"],
        "person": DIRK, "entity": "Corporate Services",
    },
    "nico-3876": {
        "label": "Card 3876", "digits": ["3876"],
        "person": NICOLAS, "entity": "Corporate Services",
    },
}
MERCHANTS = {
    "OpenAI": {
        "aliases": ["OPENAI *CHATGPT SUBSCR"],
        "receipt_portal": "platform.openai.com",
    },
}
# One matched pair (LOVABLE) so the month has nothing left to decide, and
# three charges with nothing behind them: two of Nicolas's, one of Dirk's.
CHARGES = (
    ("08/05/2026", "20.00", "OPENAI *CHATGPT SUBSCR", "3876"),
    ("08/06/2026", "96.00", "OBSIDIAN", "2838"),
    ("08/07/2026", "31.00", "SUPABASE", "3876"),
    ("08/12/2026", "15.00", "LOVABLE", "2838"),
)


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


def _settings(client, payload):
    for key, value in payload.items():
        resp = client.put("/api/settings", json={key: value})
        assert resp.status_code == 200, resp.text


def _create_batch(client, n_receipts, label="August 2026", seed=0):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if n_receipts:
        files = [
            ("files", (f"r{seed}-{i}.jpg", JPG + bytes([seed, i]),
                       "application/octet-stream"))
            for i in range(n_receipts)
        ]
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts", files=files))
    return batch_id


def _attach_csv(client, batch_id, *rows):
    """A statement whose own Card column names the card per row, which is
    how the live Chase export arrives and how a month ends up holding more
    than one holder's charges."""
    body = "Date,Amount,Vendor,Card\n" + "".join(
        f"{d},{a},{v},{c}\n" for d, a, v, c in rows
    )
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("statement.csv", body.encode(),
                             "application/octet-stream")},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    ))


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


def _tx(client, batch_id, vendor):
    return _row(_view(client, batch_id), vendor)["transaction_id"]


def _group(view, holder):
    return next(g for g in view["receipt_chase"] if g["holder"] == holder)


def _month(client, monkeypatch, *, holders=None, merchants=True):
    """A live-shaped month: two card holders, one matched pair, three
    charges with no receipt behind them."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-12"))
    settings = {"cards": CARDS}
    if merchants:
        settings["merchants"] = MERCHANTS
    if holders is not None:
        settings["receipt_requests"] = {"enabled": False, "holders": holders}
    _settings(client, settings)
    batch_id = _create_batch(client, 1)
    _attach_csv(client, batch_id, *CHARGES)
    for r in _view(client, batch_id)["rows"]:
        if r["turn"] == "decide":
            resp = client.post(
                f"/api/runs/{batch_id}/decisions",
                json={"transaction_id": r["transaction_id"], "status": "confirmed"},
            )
            assert resp.status_code == 200, resp.text
    return batch_id


def _request(client, batch_id, tx_id, **body):
    resp = client.post(
        f"/api/runs/{batch_id}/receipt-requested",
        json={"transaction_id": tx_id, **body},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _not_expected(client, batch_id, tx_id, **body):
    resp = client.post(
        f"/api/runs/{batch_id}/no-receipt-expected",
        json={"transaction_id": tx_id, **body},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── 1. the list ──────────────────────────────────────────────────────


def test_the_list_groups_by_holder_and_sums_to_the_month_count(
    client, monkeypatch
):
    batch = _month(client, monkeypatch, holders={DIRK: DIRK_ADDRESS})
    view = _view(client, batch)
    summary = view["summary"]
    assert summary["ready_to_post"] is True
    assert summary["n_charges_need_receipt"] == 3
    assert summary["month_complete"] is False

    chase = view["receipt_chase"]
    # The biggest chase first, and nobody else in the list: the LOVABLE
    # charge holds its receipt and is not chased.
    assert [g["holder"] for g in chase] == [NICOLAS, DIRK]
    assert sum(g["n_charges"] for g in chase) == summary["n_charges_need_receipt"]

    nicolas = _group(view, NICOLAS)
    assert nicolas["n_charges"] == 2
    assert nicolas["amounts_by_ccy"] == {"USD": "51.00"}
    assert [c["label"] for c in nicolas["cards"]] == ["Card 3876"]
    assert nicolas["holder_address"] is None, "no address on file, never guessed"
    assert [c["vendor"] for c in nicolas["charges"]] == [
        "OPENAI *CHATGPT SUBSCR", "SUPABASE",
    ]
    openai = nicolas["charges"][0]
    assert openai["date"] == "2026-08-05"
    assert openai["amount"] == "20.00"
    assert openai["currency"] == "USD"
    assert openai["card_label"] == "Card 3876"
    # The portal hint the merchant registry carries, so the chase says where
    # the invoice can be downloaded again.
    assert openai["portal_hint"] == "platform.openai.com"
    assert "portal_hint" not in nicolas["charges"][1], "no hint, no key"

    dirk = _group(view, DIRK)
    assert dirk["n_charges"] == 1
    assert dirk["holder_address"] == DIRK_ADDRESS
    assert dirk["amounts_by_ccy"] == {"USD": "96.00"}
    assert [c["vendor"] for c in dirk["charges"]] == ["OBSIDIAN"]


def test_a_month_with_nothing_to_chase_lists_nothing(client, monkeypatch):
    """July 2026's live shape: every charge closed, so the list is empty
    rather than a header with no rows under it."""
    batch = _month(client, monkeypatch)
    for vendor in ("OPENAI *CHATGPT SUBSCR", "OBSIDIAN", "SUPABASE"):
        _not_expected(
            client, batch, _tx(client, batch, vendor), reason="paid by transfer"
        )
    view = _view(client, batch)
    assert view["summary"]["n_charges_need_receipt"] == 0
    assert view["receipt_chase"] == []


# ── 2. the two states ────────────────────────────────────────────────


def test_a_requested_charge_still_needs_its_receipt(client, monkeypatch):
    """Asking is not getting. The charge stays in the list, stays in
    `n_charges_need_receipt`, and the month stays incomplete; what changes
    is that the page can now say the chase is already out."""
    batch = _month(client, monkeypatch, holders={DIRK: DIRK_ADDRESS})
    tx_id = _tx(client, batch, "OBSIDIAN")
    body = _request(client, batch, tx_id, to=DIRK_ADDRESS)
    assert body["summary"]["n_charges_need_receipt"] == 3, "asking closes nothing"
    assert body["summary"]["n_charges_receipt_requested"] == 1
    assert body["summary"]["month_complete"] is False

    view = _view(client, batch)
    row = _row(view, "OBSIDIAN")
    assert row["receipt_requested_at"]
    assert row["requested_to"] == DIRK_ADDRESS
    assert "no_receipt_expected" not in row
    dirk = _group(view, DIRK)
    assert dirk["n_charges"] == 1 and dirk["n_requested"] == 1
    assert dirk["charges"][0]["requested_to"] == DIRK_ADDRESS

    # Untouched rows carry neither key, so a month nobody chased renders as
    # it did before the fields existed.
    assert "receipt_requested_at" not in _row(view, "SUPABASE")
    assert _view(client, batch)["summary"]["n_charges_receipt_requested"] == 1

    # And the record can be taken back.
    body = _request(client, batch, tx_id, clear=True)
    assert body["summary"]["n_charges_receipt_requested"] == 0
    assert "receipt_requested_at" not in _row(_view(client, batch), "OBSIDIAN")


def test_no_receipt_expected_closes_the_charge_and_moves_its_money(
    client, monkeypatch
):
    batch = _month(client, monkeypatch)
    before = _view(client, batch)["summary"]
    assert before["unreconciled_by_ccy"] == {"USD": "147.00"}

    tx_id = _tx(client, batch, "OBSIDIAN")
    body = _not_expected(client, batch, tx_id, reason="bank never issues one")
    summary = body["summary"]
    assert summary["n_charges_need_receipt"] == 2, "the verdict closes the charge"
    assert summary["n_charges_no_receipt_expected"] == 1
    # The money leaves the unreconciled total and keeps its own name, the
    # way a booked charge's does (item 102's shape).
    assert summary["unreconciled_by_ccy"] == {"USD": "51.00"}
    assert summary["no_receipt_expected_by_ccy"] == {"USD": "96.00"}

    view = _view(client, batch)
    assert _row(view, "OBSIDIAN")["no_receipt_expected"] == "bank never issues one"
    assert [g["holder"] for g in view["receipt_chase"]] == [NICOLAS]

    # Closing the last two completes the month: nothing to decide, no charge
    # owing a receipt, no receipt owing a charge.
    for vendor in ("OPENAI *CHATGPT SUBSCR", "SUPABASE"):
        _not_expected(client, batch, _tx(client, batch, vendor), reason="fee")
    summary = _view(client, batch)["summary"]
    assert summary["n_charges_need_receipt"] == 0
    assert summary["n_charges_no_receipt_expected"] == 3
    assert summary["month_complete"] is True
    resp = client.post(f"/api/runs/{batch}/publish")
    assert resp.status_code == 200, resp.text
    assert resp.json()["published_override"] is False


def test_the_mark_needs_a_reason_and_can_be_taken_back(client, monkeypatch):
    batch = _month(client, monkeypatch)
    tx_id = _tx(client, batch, "OBSIDIAN")
    resp = client.post(
        f"/api/runs/{batch}/no-receipt-expected",
        json={"transaction_id": tx_id, "reason": "   "},
    )
    assert resp.status_code == 400, resp.text
    assert _view(client, batch)["summary"]["n_charges_need_receipt"] == 3

    _not_expected(client, batch, tx_id, reason="annual card fee")
    body = _not_expected(client, batch, tx_id, clear=True)
    assert body["summary"]["n_charges_need_receipt"] == 3
    assert body["summary"]["no_receipt_expected_by_ccy"] == {}
    assert "no_receipt_expected" not in _row(_view(client, batch), "OBSIDIAN")


def test_both_states_survive_a_re_match(client, monkeypatch):
    """They live on the charge's own `decisions` row, beside the pairing
    verdict, which is what carries them through a re-pairing of the month."""
    batch = _month(client, monkeypatch, holders={DIRK: DIRK_ADDRESS})
    requested = _tx(client, batch, "SUPABASE")
    closed = _tx(client, batch, "OBSIDIAN")
    _request(client, batch, requested, to="nicolas@example.com")
    _not_expected(client, batch, closed, reason="bank never issues one")

    resp = client.post(
        f"/api/runs/{batch}/expenses", json={"vendor": "Zed Ltd", "total": "7.77"}
    )
    assert resp.status_code == 200, resp.text
    assert "rematch" in resp.json(), "the month really was re-paired"

    view = _view(client, batch)
    assert _row(view, "SUPABASE")["receipt_requested_at"]
    assert _row(view, "SUPABASE")["requested_to"] == "nicolas@example.com"
    assert _row(view, "OBSIDIAN")["no_receipt_expected"] == "bank never issues one"
    summary = view["summary"]
    assert summary["n_charges_need_receipt"] == 2
    assert summary["n_charges_receipt_requested"] == 1
    assert summary["n_charges_no_receipt_expected"] == 1


# ── 3. the mail: composed, never sent ────────────────────────────────


def test_the_composer_returns_the_mail_and_nothing_sends(client, monkeypatch):
    batch = _month(client, monkeypatch, holders={DIRK: DIRK_ADDRESS})
    resp = client.get(f"/api/runs/{batch}/receipt-requests")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["enabled"] is False
    assert body["can_send"] is False
    assert body["send_blocked_reason"] == "receipt_requests_disabled"
    assert body["intake_address"] == "receipts@expenses.brisken.com"
    assert body["n_charges_need_receipt"] == 3
    assert [m["holder"] for m in body["mails"]] == [NICOLAS, DIRK]

    dirk = next(m for m in body["mails"] if m["holder"] == DIRK)
    assert dirk["to"] == DIRK_ADDRESS
    assert dirk["from_address"] == "receipts@expenses.brisken.com"
    assert dirk["reply_to"] == "receipts@expenses.brisken.com"
    assert dirk["subject"] == "August 2026: 1 receipt still missing"
    assert "OBSIDIAN" in dirk["body"] and "Corporate card 2838" in dirk["body"]
    assert "receipts@expenses.brisken.com" in dirk["body"]
    assert "blocked" not in dirk
    # Both languages, composed together, so the page never has to translate a
    # body the backend wrote.
    assert dirk["subject_pt"] == "August 2026: 1 recibo ainda faltando"
    assert "OBSIDIAN" in dirk["body_pt"]
    assert "Responda a este e-mail" in dirk["body_pt"]

    nicolas = next(m for m in body["mails"] if m["holder"] == NICOLAS)
    assert nicolas["subject"] == "August 2026: 2 receipts still missing"
    assert "platform.openai.com" in nicolas["body"]
    assert "platform.openai.com" in nicolas["body_pt"]

    # Nothing has been asked for: composing a preview is not a request.
    assert _view(client, batch)["summary"]["n_charges_receipt_requested"] == 0

    # And the send route refuses, with the flag off and with the flag on.
    resp = client.post(f"/api/runs/{batch}/receipt-requests/send")
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "receipt_requests_disabled"

    _settings(client, {"receipt_requests": {
        "enabled": True, "holders": {DIRK: DIRK_ADDRESS},
    }})
    resp = client.post(f"/api/runs/{batch}/receipt-requests/send")
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "receipt_send_not_wired"
    preview = client.get(f"/api/runs/{batch}/receipt-requests").json()
    assert preview["enabled"] is True
    assert preview["can_send"] is False
    assert preview["send_blocked_reason"] == "receipt_send_not_wired"


def test_a_holder_with_no_address_is_named_not_guessed(client, monkeypatch):
    batch = _month(client, monkeypatch, holders={DIRK: DIRK_ADDRESS})
    mails = client.get(f"/api/runs/{batch}/receipt-requests").json()["mails"]
    nicolas = next(m for m in mails if m["holder"] == NICOLAS)
    assert nicolas["to"] is None
    assert nicolas["blocked"] == "no_address"
    assert nicolas["body"], "the mail is still composed, it just has nobody to go to"


def test_no_send_path_exists_for_a_request_mail(client):
    """The structural half of "nothing can send today": the module that
    composes the chase mail imports no transport and calls nothing that
    could deliver one. A future sender is a deliberate edit here, not a flag
    flip. Read off the parsed module, so its own prose about the absent
    sender cannot pass for the absence."""
    import ast
    import inspect

    from expense_recon.web import receipt_chase

    tree = ast.parse(inspect.getsource(receipt_chase))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(a.name for a in node.names)
    banned = {
        "graph_notify", ".graph_notify", "smtplib", "urllib", "urllib.request",
        "httpx", "requests", "intake_mail", ".intake_mail",
    }
    assert not (imported & banned), sorted(imported & banned)
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute)
        else getattr(node.func, "id", "")
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "send_mail" not in called


# ── the settings key ─────────────────────────────────────────────────


def test_the_flag_is_off_by_default_and_a_non_boolean_is_refused(client):
    stored = client.get("/api/settings").json()
    assert stored["receipt_requests"] == {"enabled": False, "holders": {}}

    resp = client.put(
        "/api/settings", json={"receipt_requests": {"enabled": "yes"}}
    )
    assert resp.status_code == 400, resp.text
    assert "true or false" in resp.json()["error"]

    resp = client.put("/api/settings", json={"receipt_requests": {
        "enabled": True, "holders": {DIRK: "dirk@brisken.com, someone@else"},
    }})
    assert resp.status_code == 400, resp.text
    assert "plain e-mail address" in resp.json()["error"]
    assert client.get("/api/settings").json()["receipt_requests"]["enabled"] is False


def test_the_states_are_stored_beside_the_pairing_verdict(client, monkeypatch):
    """Not a table of their own: the same `decisions` row, which is why a
    statement re-read's id rekey carries them and why neither upsert can
    clobber the other's column."""
    batch = _month(client, monkeypatch)
    tx_id = _tx(client, batch, "OBSIDIAN")
    _request(client, batch, tx_id, to=DIRK_ADDRESS)
    _not_expected(client, batch, tx_id, reason="annual card fee")
    resp = client.post(
        f"/api/runs/{batch}/decisions",
        json={"transaction_id": tx_id, "status": "already_posted"},
    )
    assert resp.status_code == 200, resp.text

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        decision = store.get_decisions(batch)[tx_id]
    assert decision.status == "already_posted", "the verdict still wrote"
    assert decision.receipt_requested_at
    assert decision.receipt_requested_to == DIRK_ADDRESS
    assert decision.no_receipt_expected == "annual card fee"
