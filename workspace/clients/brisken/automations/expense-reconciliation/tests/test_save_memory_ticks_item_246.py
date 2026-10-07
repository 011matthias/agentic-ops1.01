"""Item 246: "Save corrections to memory" saves only what is ticked, and a save
overwrites the rule memory holds for that case (owner 2026-10-07).

Route-level through `GET /api/runs/{id}/memory-plan` and
`POST /api/runs/{id}/commit-memory`:

* the button takes the same `keep` / `skip` lesson ids as Publish; no body
  still saves the defaults;
* every lesson says what it does to the rule memory holds (`effect`,
  `replaces`), and one this month already saved starts unticked and is not
  written twice;
* a changed correction overwrites the rule it saved earlier, and one from
  another month;
* a category save replaces the rules stored for the same merchant in the
  same company under another spelling, carrying over the half it did not
  name, and the undo brings them back.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.learning import LearningStore, MerchantCategoryLookup  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CORP = "Corporate Services"
PAID = "field_correction:Corporate Services|staples|paid_through"
VENDOR = "field_correction:Corporate Services|staples|vendor"
CATEGORY = "merchant_category:Corporate Services|staples"
OFFICE, EQUIPMENT = "Office Supplies & Consumables", "Equipment & Hardware"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _batch(client, monkeypatch, total="42.50") -> tuple[str, str]:
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-07-01", total=total, currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="")])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=[
        ("files", (f"{total}.jpg", JPG + total.encode(), "application/octet-stream"))])
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    (row,) = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return batch, row["document_id"]


def _edit(client, batch, doc, field, value) -> None:
    resp = client.put(f"/api/runs/{batch}/expenses/{doc}", json={"field": field, "value": value})
    assert resp.status_code == 200, resp.text


def _lessons(client, batch) -> dict[str, dict]:
    resp = client.get(f"/api/runs/{batch}/memory-plan")
    assert resp.status_code == 200, resp.text
    return {lsn["id"]: lsn for lsn in resp.json()["lessons"]}


def _save(client, batch, **body) -> dict:
    resp = client.post(f"/api/runs/{batch}/commit-memory", json=body or None)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _memory(client) -> dict:
    return client.get("/api/memory").json()


def _paid(client) -> list[dict]:
    return [c for c in _memory(client)["field_corrections"] if c["field"] == "paid_through"]


def _categories(client) -> dict[tuple, dict]:
    return {(c["entity"], c["vendor"]): c for c in _memory(client)["categories"]}


def _seed_rule(client, vendor_norm, category, account=None) -> None:
    """A rule a person saved in an earlier month, under its own spelling."""
    with LearningStore(client.app.state.learning_db_path) as s:
        s.record_merchant_category(
            CORP, vendor_norm, category, account, "2026-06-30T00:00:00Z", "run-june")


# ── the button saves what is ticked ─────────────────────────────────────


def test_the_button_saves_only_the_ticked_lessons(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    assert {PAID, VENDOR, "registry:Staples Inc"} <= set(_lessons(client, batch))

    body = _save(client, batch, keep=[PAID])
    assert body["saved"] is True
    assert body["lessons"]["kept"] == [PAID]
    assert VENDOR in body["lessons"]["skipped"]
    assert {c["field"] for c in _memory(client)["field_corrections"]} == {"paid_through"}
    assert "Staples Inc" not in client.get("/api/settings").json()["merchants"]


def test_the_button_without_ticks_saves_the_defaults(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert {c["field"] for c in _memory(client)["field_corrections"]} == {"vendor", "paid_through"}
    assert "Staples Inc" in client.get("/api/settings").json()["merchants"]


def test_a_malformed_tick_list_is_refused(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    resp = client.post(f"/api/runs/{batch}/commit-memory", json={"keep": PAID})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_body"
    assert _paid(client) == [], "a refused save wrote anyway"


# ── what this month already saved ───────────────────────────────────────


def test_a_saved_lesson_starts_unticked_and_is_not_written_twice(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    _save(client, batch, keep=[PAID])

    lessons = _lessons(client, batch)
    assert lessons[PAID]["already_saved"] is True
    assert lessons[PAID]["default_keep"] is False
    assert lessons[PAID]["effect"] == "same"
    assert lessons[VENDOR]["already_saved"] is False
    assert lessons[VENDOR]["default_keep"] is True

    body = _save(client, batch, keep=[PAID, VENDOR])
    assert body["lessons"]["kept"] == [VENDOR]
    assert body["lessons"]["already_saved"] == [PAID]
    assert [c["count"] for c in _paid(client)] == [1], "the same correction counted twice"


def test_a_second_click_with_nothing_new_records_no_save(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    first = _save(client, batch, keep=[PAID])
    assert isinstance(first["journal_id"], int)

    again = _save(client, batch, keep=[PAID])
    assert again["saved"] is False and again["reason"] == "nothing_to_save"
    assert again["journal_id"] is None
    commits = client.get("/api/memory/commits").json()["commits"]
    assert [c["id"] for c in commits] == [first["journal_id"]], "an empty save was journaled"


def test_publish_skips_what_the_button_already_saved(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    _save(client, batch, keep=[PAID])

    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    lessons = resp.json()["memory"]["learned"]["lessons"]
    assert PAID not in lessons["kept"] and VENDOR in lessons["kept"]
    assert [c["count"] for c in _paid(client)] == [1]


# ── a save overwrites the rule for that case ────────────────────────────


def test_a_changed_correction_overwrites_the_rule_it_saved(client, monkeypatch):
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    _save(client, batch, keep=[PAID])

    _edit(client, batch, doc, "paid_through", "2020 Amex")
    lesson = _lessons(client, batch)[PAID]
    assert lesson["effect"] == "replaces"
    assert lesson["already_saved"] is False and lesson["default_keep"] is True
    assert [r["value"] for r in lesson["replaces"]] == ["1010 Chase"]
    assert "Replaces 1010 Chase." in lesson["description"]

    _save(client, batch, keep=[PAID])
    assert [c["value"] for c in _paid(client)] == ["2020 Amex"]


def test_a_rule_from_another_month_is_overwritten(client, monkeypatch):
    june, doc = _batch(client, monkeypatch)
    _edit(client, june, doc, "category", OFFICE)
    _save(client, june)
    assert _categories(client)[(CORP, "staples")]["category"] == OFFICE

    july, doc = _batch(client, monkeypatch, total="17.00")
    _edit(client, july, doc, "category", EQUIPMENT)
    lessons = _lessons(client, july)
    assert lessons[CATEGORY]["effect"] == "replaces"
    assert OFFICE in lessons[CATEGORY]["replaces"][0]["value"]
    assert lessons["registry:Staples"]["effect"] == "replaces"

    _save(client, july, keep=[CATEGORY, "registry:Staples"])
    assert _categories(client)[(CORP, "staples")]["category"] == EQUIPMENT
    assert client.get("/api/settings").json()["merchants"]["Staples"]["category"] == EQUIPMENT


def test_a_save_replaces_the_rule_under_another_spelling(client, monkeypatch):
    """Recall folds `staples inc` and `staples` into one merchant, and folds
    nothing when they disagree: each spelling then keeps answering for
    itself, so the older rule kept filing every receipt spelled its way."""
    _seed_rule(client, "staples inc", OFFICE)
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "category", EQUIPMENT)

    lesson = _lessons(client, batch)[CATEGORY]
    assert lesson["effect"] == "replaces"
    (gone,) = [r for r in lesson["replaces"] if r["removed"]]
    assert gone["key"] == {"legal_entity_id": CORP, "vendor_norm": "staples inc"}
    assert "the rule saved as staples inc" in lesson["description"]

    journal_id = _save(client, batch, keep=[CATEGORY])["journal_id"]
    rules = _categories(client)
    assert (CORP, "staples inc") not in rules, "the old spelling's rule survived the save"
    assert rules[(CORP, "staples")]["category"] == EQUIPMENT
    with LearningStore(client.app.state.learning_db_path) as s:
        recall = MerchantCategoryLookup.from_store(s).recall(CORP, "Staples Inc")
    assert recall is not None and recall.category == EQUIPMENT

    # The undo puts the replaced rule back and takes the new one out.
    assert client.post(f"/api/memory/commits/{journal_id}/undo").status_code == 200
    rules = _categories(client)
    assert rules[(CORP, "staples inc")]["category"] == OFFICE
    assert (CORP, "staples") not in rules


def test_the_half_a_save_did_not_name_comes_from_the_replaced_rule(client, monkeypatch):
    _seed_rule(client, "staples inc", OFFICE, "6000 Office")
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "zoho_account", "7000 Equipment")
    _save(client, batch, keep=[CATEGORY])

    rules = _categories(client)
    assert (CORP, "staples inc") not in rules
    assert rules[(CORP, "staples")]["zoho_account"] == "7000 Equipment"
    assert rules[(CORP, "staples")]["category"] == OFFICE, \
        "an account-only fix dropped the category the replaced rule held"


def test_spellings_that_disagree_on_the_unnamed_half_are_left_alone(client, monkeypatch):
    _seed_rule(client, "staples inc", OFFICE)
    _seed_rule(client, "staples llc", EQUIPMENT)
    batch, doc = _batch(client, monkeypatch)
    _edit(client, batch, doc, "zoho_account", "7000 Equipment")

    lesson = _lessons(client, batch)[CATEGORY]
    assert not [r for r in lesson["replaces"] if r["removed"]]
    _save(client, batch, keep=[CATEGORY])
    rules = _categories(client)
    assert rules[(CORP, "staples inc")]["category"] == OFFICE
    assert rules[(CORP, "staples llc")]["category"] == EQUIPMENT
