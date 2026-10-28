"""The private-card list: a card that is NOT Brisken's, known by its last
four digits and the person it belongs to (owner direction 2026-09-24, cases
2 + 4 of the card-attribution map).

Owner: "fuze items 2 and 4 together, fix a) by setting up private card
memory/registry and b) any credit card types or numbers that dont belong to
brisken will then be suggested as private expenses". Case 6 (item 203) is
half (b); this is half (a). The list is `settings["private_cards"]`, a
separate key from `cards`, read LIVE at view time, and a printed number on
it makes the row private, reimbursed to the listed person, on every surface
a row Criss confirmed reaches.

Pinned here, all route-level through the FastAPI app:
* a listed 3281 turns a "DEBIT-MASTERCARD ... 3281" row private, with the
  person, `person_source` "private" and `private_source`
  "private_card_list", and the row reaches the report's reimbursements
  section and the CSV; the list is read live (an entry reaches an existing
  month with no refresh);
* an inactive entry falls back to case 6's suggestion;
* both collision refusals (a private entry an active company card carries;
  a company card carrying a listed number), the two-digit refusal and the
  person requirement;
* the strip's `private_to` with learn true (writes settings) and learn
  false (batch only), and its refusals;
* both row exits: undo stores an explicit opt-out the list cannot undo; a
  per-row company-card pick wins and is not refused, while the refusal
  stays on a row Criss confirmed herself;
* the shallow-merge survival (a `cards` save after `private_cards` exist);
* the printed-number guard (a listed number never takes the merchant card);
* a golden table proving the one-entry-point refactor leaves every other
  branch of the decision order unchanged (case 6's own rows).

Harness mirrors test_private_expense (fixtures copied, never imported: a
shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    PrivateCard,
    cards_from_setting,
    classify_payment_evidence,
    normalize_private_cards_setting,
    private_card_digits,
    private_card_for,
    private_cards_from_setting,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
COL_PAID_THROUGH = EXPENSE_COLUMNS.index("Paid Through")
COL_ENTITY = EXPENSE_COLUMNS.index("Legal Entity")
COL_VENDOR = EXPENSE_COLUMNS.index("Vendor")

# Two company cards in the live registry's wording (Chase Visa credit).
CORP = {
    "corp-1672": {"label": "Credit Card Chase Visa - 1672", "digits": ["1672"],
                  "entity": "Corporate Services", "person": "Nicolas"},
    "corp-3645": {"label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
                  "entity": "Corporate Services"},
}
CARDS = cards_from_setting(CORP)
# September's DB Fernverkehr row, verbatim (live 2026-09-24).
DB_3281 = "DEBIT-MASTERCARD ***** ***** ***** 3281"
LISTED = {"3281": {"person": "Dirk Neumann", "note": "personal DKB card"}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-09-01", total="42.50", currency="EUR",
                vendor="DB Fernverkehr", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, n_files=1, label="September 2026", seed=0):
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i, seed]),
                   "application/octet-stream"))
        for i in range(n_files)
    ]
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts",
                       files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_vendor(client, batch) -> dict:
    return {e["vendor"]["display"]: e for e in _grid(client, batch)["expenses"]}


def _set_category(client, batch_id, doc):
    r = client.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": doc, "line_index": 0,
        "category": "Travel & Transport",
    })
    assert r.status_code == 200, r.text


def _put_settings(client, **groups):
    r = client.put("/api/settings", json=groups)
    assert r.status_code == 200, r.text
    return r.json()


def _store(client) -> RunStore:
    return RunStore(client._data_root / "recon-web.sqlite")


def _stored_private(client, batch, doc) -> str | None:
    with _store(client) as store:
        return (store.get_expense_field_overrides(batch).get(doc) or {}).get("private")


# ── a listed number makes the row private, on every surface ─────────


def test_a_listed_number_makes_the_row_private_with_the_person(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _put_settings(client, private_cards=LISTED)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=DB_3281),
        _extraction(vendor="Staples", total="9.00", payment_hint="Visa ...1672"),
    )
    batch = _create_batch(client, n_files=2)
    rows = _by_vendor(client, batch)
    row = rows["DB Fernverkehr"]
    assert row["private"] is True
    assert row["reimburse_to"] == "Dirk Neumann"
    assert row["person"] == "Dirk Neumann"
    assert row["person_source"] == "private"
    assert row["private_source"] == "private_card_list"
    assert row["suggested_private"] is False
    assert row["can_mark_private"] is False
    assert row["card"] is None
    assert row["posting_paid_through"]["account"] == "Private (Dirk Neumann)"
    assert row["posting_paid_through"]["source"] == "private"
    assert row["legal_entity_id"] == ""
    assert "private" in row["boxes"] and "needs_entity" not in row["boxes"]
    # the company-card row is untouched, with an empty source
    assert rows["Staples"]["private"] is False
    assert rows["Staples"]["private_source"] == ""

    grid = _grid(client, batch)
    assert grid["summary"]["n_private"] == 1
    assert grid["summary"]["n_suggested_private"] == 0
    assert grid["summary"]["n_needs_entity"] == 0
    strip = grid["card_review"]
    assert strip["n_private"] == 1 and strip["n_suggested_private"] == 0
    # item 214 (owner ruling 2026-09-25): the printed number resolves, so the
    # strip has no card question left; the row counts as a private strip row
    assert strip["unresolved_hints"] == []
    assert strip["n_private_rows"] == 1

    for doc in (row["document_id"], rows["Staples"]["document_id"]):
        _set_category(client, batch, doc)
    resp = client.get(f"/runs/{batch}/expenses.csv")
    assert resp.status_code == 200, resp.text
    csv_rows = {r[COL_VENDOR]: r for r in list(csv.reader(io.StringIO(resp.text)))[1:]}
    assert csv_rows["DB Fernverkehr"][COL_ENTITY] == "(private expense)"
    assert csv_rows["DB Fernverkehr"][COL_PAID_THROUGH] == "Private (Dirk Neumann)"
    assert csv_rows["Staples"][COL_ENTITY] == "Corporate Services"

    pypdf = pytest.importorskip("pypdf")
    resp = client.get(f"/runs/{batch}/expense-report.pdf")
    assert resp.status_code == 200
    first_page = pypdf.PdfReader(io.BytesIO(resp.content)).pages[0].extract_text() or ""
    assert "Reimbursements owed" in first_page
    assert "Reimburse Dirk Neumann" in first_page
    assert "Owed to Dirk Neumann: EUR 42.50" in first_page
    assert "1 expenses" in first_page


def test_the_list_is_read_live_by_an_existing_month(client, monkeypatch):
    """An entry reaches every existing month at once: no refresh, no write
    to the month (the batch snapshot never holds the list)."""
    _put_settings(client, cards=CORP)
    _patch_ocr(monkeypatch, _extraction(payment_hint=DB_3281))
    batch = _create_batch(client)
    before = _grid(client, batch)["expenses"][0]
    assert before["private"] is False and before["suggested_private"] is True
    assert before["private_source"] == ""
    _put_settings(client, private_cards=LISTED)
    after = _grid(client, batch)["expenses"][0]
    assert after["private"] is True
    assert after["private_source"] == "private_card_list"
    assert after["suggested_private"] is False
    with _store(client) as store:
        cfg = store.get_run(batch).config
    assert "private_cards" not in (cfg.get("expense") or {})
    assert "private_cards" not in cfg


def test_an_inactive_entry_falls_back_to_the_case_6_suggestion(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _put_settings(client, private_cards={
        "3281": {"person": "Dirk Neumann", "active": False},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint=DB_3281))
    row = _grid(client, _create_batch(client))["expenses"][0]
    assert row["private"] is False
    assert row["private_source"] == ""
    assert row["suggested_private"] is True
    assert row["can_mark_private"] is True


def test_a_listed_number_never_takes_the_merchant_card(client, monkeypatch):
    """The printed-number guard: a receipt printing a number takes no card
    from the merchant registry (nor a settled charge or a remembered card),
    listed or not. Pinned so the list can never lend a company card to a
    private receipt through the merchant link."""
    _put_settings(client, cards=CORP)
    _put_settings(client, merchants={
        "DB Fernverkehr": {"aliases": [], "card_key": "corp-3645"},
    })
    _put_settings(client, private_cards=LISTED)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=DB_3281),
        _extraction(vendor="DB Fernverkehr", total="5.00", payment_hint=""),
    )
    grid = _grid(client, _create_batch(client, n_files=2))
    by_hint = {e["payment_hint"]: e for e in grid["expenses"]}
    listed = by_hint[DB_3281]
    assert listed["private"] is True and listed["card"] is None
    # the control: the same merchant with no number printed takes the card
    bare = by_hint[""]
    assert bare["card"]["key"] == "corp-3645" and bare["card_source"] == "merchant"
    assert bare["private"] is False


# ── validation and the two collision refusals ────────────────────────


def test_private_cards_setting_is_validated_at_the_edge(client):
    _put_settings(client, cards=CORP)
    r = client.put("/api/settings", json={"private_cards": {"xx78": {"person": "Dirk"}}})
    assert r.status_code == 400 and r.json()["code"] == "private_card_digits_short"
    assert r.json()["setting"] == "private_cards"
    r = client.put("/api/settings", json={"private_cards": {"3281": {"person": " "}}})
    assert r.status_code == 400 and r.json()["code"] == "private_card_person_required"
    r = client.put("/api/settings", json={"private_cards": {
        "3281": {"person": "Dirk"}, "***3281": {"person": "Dirk"},
    }})
    assert r.status_code == 400 and r.json()["code"] == "private_card_duplicate"
    r = client.put("/api/settings", json={"private_cards": []})
    assert r.status_code == 400 and r.json()["code"] == "invalid_body"
    # stored shape: the four digits (a leading zero kept), trimmed person,
    # note, active
    body = _put_settings(client, private_cards={
        "VISA ***0340": {"person": " Ana ", "note": "x"},
        "0501-1462-9129": {"person": "Bo", "active": False},
    })
    assert body["applied"] == ["private_cards"]
    assert body["private_cards"] == {
        "0340": {"person": "Ana", "note": "x", "active": True},
        "9129": {"person": "Bo", "note": "", "active": False},
    }
    assert client.get("/api/settings").json()["private_cards"] == body["private_cards"]


def test_a_company_card_number_is_refused_on_the_private_list(client):
    _put_settings(client, cards=CORP)
    r = client.put("/api/settings", json={"private_cards": {"3645": {"person": "Dirk"}}})
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "private_card_is_company_card"
    assert r.json()["card"] == "corp-3645" and r.json()["private_card"] == "3645"
    # an INACTIVE company card is not a company card anyone pays with
    _put_settings(client, cards={
        **CORP, "corp-3645": {**CORP["corp-3645"], "active": False},
    })
    _put_settings(client, private_cards={"3645": {"person": "Dirk"}})


def test_a_listed_number_is_refused_on_a_company_card(client):
    _put_settings(client, private_cards=LISTED)
    r = client.put("/api/settings", json={"cards": {
        **CORP, "dkb-3281": {"digits": ["3281"], "entity": "Cloud Services"},
    }})
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "private_card_is_company_card"
    assert r.json()["setting"] == "cards"
    assert r.json()["card"] == "dkb-3281"
    # the list is untouched and a clean cards save still lands
    assert client.get("/api/settings").json()["private_cards"] == {
        "3281": {"person": "Dirk Neumann", "note": "personal DKB card", "active": True},
    }
    _put_settings(client, cards=CORP)


def test_a_cards_save_does_not_erase_the_private_list(client):
    """`store.set_settings` merges top-level keys shallowly, so the Cards
    editor's whole-map save (which never carries `private_cards`) keeps
    the list. The reason the list is its own key."""
    _put_settings(client, private_cards=LISTED)
    body = _put_settings(client, cards=CORP)
    assert body["applied"] == ["cards"]
    settings = client.get("/api/settings").json()
    assert settings["private_cards"]["3281"]["person"] == "Dirk Neumann"
    assert set(settings["cards"]) == set(CORP)


# ── the unknown-card strip: "Private card of ..." ────────────────────


def test_the_strip_assigns_a_hint_private_for_this_month(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _patch_ocr(monkeypatch, _extraction(payment_hint=DB_3281))
    batch = _create_batch(client)
    r = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": DB_3281, "private_to": "Dirk Neumann"}],
        "learn": False,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["results"] == [{
        "hint": DB_3281, "private_to": "Dirk Neumann", "n_rows": 1,
        "learned": False, "digits": "",
    }]
    assert body["learned_to_settings"] is False
    row = body["batch"]["expenses"][0]
    assert row["private"] is True and row["private_source"] == "month"
    assert row["reimburse_to"] == "Dirk Neumann"
    assert row["can_mark_private"] is False
    # recorded on the batch, beside the card hints; nothing in settings
    with _store(client) as store:
        exp = store.get_run(batch).config["expense"]
    assert exp["private_hints"] == {DB_3281: "Dirk Neumann"}
    assert client.get("/api/settings").json()["private_cards"] == {}


def test_the_strip_remembers_a_private_card_into_the_list(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _patch_ocr(monkeypatch, _extraction(payment_hint=DB_3281))
    batch = _create_batch(client)
    r = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": DB_3281, "private_to": "Dirk Neumann"}],
        "learn": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["results"][0]["learned"] is True
    assert body["results"][0]["digits"] == "3281"
    assert body["learned_to_settings"] is True
    assert client.get("/api/settings").json()["private_cards"] == {
        "3281": {"person": "Dirk Neumann", "note": "", "active": True},
    }
    # and a SECOND month printing the number is private at once
    _patch_ocr(monkeypatch, _extraction(vendor="Bahn again", payment_hint=DB_3281))
    other = _grid(client, _create_batch(client, label="October 2026", seed=1))
    assert other["expenses"][0]["private_source"] == "private_card_list"
    assert other["expenses"][0]["reimburse_to"] == "Dirk Neumann"


def test_the_strip_refuses_what_cannot_be_a_private_card(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=DB_3281),
        _extraction(vendor="Word Co", total="3.00", payment_hint="EC-Karte"),
        _extraction(vendor="Corp Co", total="4.00", payment_hint="Visa ...3645"),
    )
    batch = _create_batch(client, n_files=3)
    url = f"/api/expense-batches/{batch}/cards"
    # exactly one target
    r = client.post(url, json={"assignments": [
        {"hint": DB_3281, "card": "corp-1672", "private_to": "Dirk"},
    ]})
    assert r.status_code == 400 and r.json()["code"] == "assignment_two_targets"
    r = client.post(url, json={"assignments": [{"hint": DB_3281}]})
    assert r.status_code == 400 and r.json()["code"] == "assignment_incomplete"
    # a generic word names no card to remember; month-only is still fine
    r = client.post(url, json={
        "assignments": [{"hint": "EC-Karte", "private_to": "Dirk"}], "learn": True,
    })
    assert r.status_code == 400 and r.json()["code"] == "private_card_needs_digits"
    r = client.post(url, json={
        "assignments": [{"hint": "EC-Karte", "private_to": "Dirk"}], "learn": False,
    })
    assert r.status_code == 200, r.text
    assert _by_vendor(client, batch)["Word Co"]["private_source"] == "month"
    # a company card's number is never private
    r = client.post(url, json={
        "assignments": [{"hint": "Visa ...3645", "private_to": "Dirk"}], "learn": True,
    })
    assert r.status_code == 400 and r.json()["code"] == "private_card_is_company_card"
    assert client.get("/api/settings").json()["private_cards"] == {}
    # and a card assignment may not fold a LISTED number into a company card
    _put_settings(client, private_cards=LISTED)
    r = client.post(url, json={
        "assignments": [{"hint": DB_3281, "card": "corp-1672"}], "learn": False,
    })
    assert r.status_code == 400 and r.json()["code"] == "private_card_is_company_card"


# ── the two row exits ───────────────────────────────────────────────


def test_undo_on_a_listed_row_stores_an_opt_out_the_list_cannot_undo(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _put_settings(client, private_cards=LISTED)
    _patch_ocr(monkeypatch, _extraction(payment_hint=DB_3281))
    batch = _create_batch(client)
    doc = _grid(client, batch)["expenses"][0]["document_id"]
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private", json={"private": False})
    assert r.status_code == 200, r.text
    row = _grid(client, batch)["expenses"][0]
    assert row["private"] is False and row["private_source"] == ""
    assert row["reimburse_to"] == ""
    # the number is still not Brisken's, so case 6's suggestion returns
    assert row["suggested_private"] is True and row["can_mark_private"] is True
    assert _stored_private(client, batch, doc) == "0"
    # Criss can still confirm it herself afterwards, as her own decision
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True, "reimburse_to": "Ana"})
    assert r.status_code == 200, r.text
    row = _grid(client, batch)["expenses"][0]
    assert row["private_source"] == "row" and row["reimburse_to"] == "Ana"
    # and a row only she marked clears as before: no opt-out stored
    _patch_ocr(monkeypatch, _extraction(vendor="Cash Co", payment_hint="Bar"))
    other = _create_batch(client, label="October 2026", seed=1)
    odoc = _grid(client, other)["expenses"][0]["document_id"]
    client.post(f"/api/runs/{other}/expenses/{odoc}/private",
                json={"private": True, "reimburse_to": "Ana"})
    r = client.post(f"/api/runs/{other}/expenses/{odoc}/private", json={"private": False})
    assert r.status_code == 200, r.text
    assert _stored_private(client, other, odoc) is None
    assert _grid(client, other)["expenses"][0]["suggested_private"] is True


def test_a_company_card_pick_wins_over_a_listed_number(client, monkeypatch):
    _put_settings(client, cards=CORP)
    _put_settings(client, private_cards=LISTED)
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint=DB_3281),
        _extraction(vendor="Own Co", total="6.00", payment_hint="EC-Karte"),
    )
    batch = _create_batch(client, n_files=2)
    rows = _by_vendor(client, batch)
    listed_doc = rows["DB Fernverkehr"]["document_id"]
    pick = {"field": "card_key", "value": "corp-1672"}
    r = client.put(f"/api/runs/{batch}/expenses/{listed_doc}", json=pick)
    assert r.status_code == 200, r.text
    row = _by_vendor(client, batch)["DB Fernverkehr"]
    assert row["card"]["key"] == "corp-1672" and row["card_source"] == "override"
    assert row["private"] is False and row["private_source"] == ""
    assert row["person"] == "Nicolas"
    # the refusal stays on a row Criss confirmed herself
    own_doc = rows["Own Co"]["document_id"]
    r = client.post(f"/api/runs/{batch}/expenses/{own_doc}/private",
                    json={"private": True, "reimburse_to": "Dirk"})
    assert r.status_code == 200, r.text
    r = client.put(f"/api/runs/{batch}/expenses/{own_doc}", json=pick)
    assert r.status_code == 400 and r.json()["code"] == "private_card"


# ── the pure half: one entry point, the other branches unchanged ─────

# Case 6's own table (`tests/test_private_needs_evidence.py`), the golden
# rows: through `classify_payment_evidence` with an EMPTY list every row
# answers exactly what `positive_non_brisken_evidence` answered.
SUGGESTS = [
    ("VISA ***2598", "number"), ("COMPRA CREDITO VISA ********1340", "number"),
    ("VISA CREDIT xxxxxxxxxxxx4167", "number"), ("CARTAO: XXXXXXXXXXXX3976", "number"),
    (DB_3281, "number"), ("...2544", "number"), ("0501-1462-9129", "number"),
    ("Mastercard xxxx.xxxx.xxxx.78", "ending"),
    ("DINHEIRO", "cash"), ("Bar", "cash"), ("pago em espécie", "cash"),
    ("girocard", "network"), ("EC-Karte", "network"), ("Maestro", "network"),
    # this registry is Visa-only, so Mastercard is a network it lacks
    ("Mastercard", "network"),
    ("DEBIT", "kind"), ("Visa Debit", "kind"),
    ("Nubank", "issuer"), ("Apple Pay Nubank", "issuer"),
]
WAITS = [
    "VENDA CREDITO VISA", "Link", "OUTRO", "CreditCard", "saved payment method",
    "Kartenzahlung erhalten", "VISA CREDIT", "Cartão de Crédito", "TEF",
    "credit card", "Chase Visa", "Visa ...3645", "xx45",
    "credit or debit card", "Visa ou Dinheiro", "CIELO", "Apple Pay",
    "DB Fernverkehr", "paid via the usual method", "",
]


@pytest.mark.parametrize("hint,reason", SUGGESTS)
def test_with_an_empty_list_the_evidence_branch_is_unchanged(hint, reason):
    assert classify_payment_evidence(hint, CARDS, {}) == (None, reason), hint


@pytest.mark.parametrize("hint", WAITS)
def test_with_an_empty_list_the_waiting_branch_is_unchanged(hint):
    assert classify_payment_evidence(hint, CARDS, {}) == (None, None), hint


def test_the_list_sits_between_brisken_and_the_evidence():
    listed = private_cards_from_setting({"3281": {"person": "Dirk"}})
    entry = PrivateCard(digits="3281", person="Dirk")
    # step 3: a listed number, before step 4's `number` reason; the number
    # outranks the type word beside it
    assert classify_payment_evidence(DB_3281, CARDS, listed) == (entry, None)
    assert classify_payment_evidence("Visa ...3281", CARDS, listed) == (entry, None)
    # steps 1-2 first: a Brisken number is never looked up, even if listed
    # (the PUT refuses that state; the function refuses it too)
    collided = private_cards_from_setting({"3645": {"person": "Dirk"}})
    assert classify_payment_evidence("Visa ...3645", CARDS, collided) == (None, None)
    assert classify_payment_evidence("VISA CREDIT", CARDS, listed) == (None, None)
    # a two-digit ending is never looked up; one two Brisken cards share
    # stays unguessed and is not private
    two_share = cards_from_setting({
        "a": {"digits": ["3876"], "entity": "X"}, "b": {"digits": ["1176"], "entity": "Y"},
    })
    assert private_card_for("xx76", listed) is None
    assert classify_payment_evidence("Mastercard xxxx.xxxx.xxxx.76", two_share, listed) == (None, None)
    # an inactive entry decides nothing: the evidence branch answers
    off = private_cards_from_setting({"3281": {"person": "Dirk", "active": False}})
    assert classify_payment_evidence(DB_3281, CARDS, off) == (None, "number")
    # an assigned hint is a Brisken card (step 1), whatever the list says
    assert classify_payment_evidence(
        DB_3281, CARDS, listed, {DB_3281: "corp-1672"}
    ) == (None, None)


def test_private_card_digits_reads_the_last_four_of_the_last_run():
    assert private_card_digits("3281") == "3281"
    assert private_card_digits("***3281") == "3281"
    assert private_card_digits("0340") == "0340"
    assert private_card_digits("0501-1462-9129") == "9129"
    assert private_card_digits("42463153XXXXXX38") is None  # a BIN, then two digits
    assert private_card_digits("xx78") is None
    assert private_card_digits("340") is None
    assert private_card_digits("EC-Karte") is None
    assert private_card_digits("") is None
    with pytest.raises(ValueError):
        normalize_private_cards_setting({"78": {"person": "Dirk"}})
