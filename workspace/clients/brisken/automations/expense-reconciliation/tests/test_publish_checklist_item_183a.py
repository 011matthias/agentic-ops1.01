"""Item 183 half A: Publish shows what it will remember, one tick per lesson.

Route-level through `GET /api/runs/{id}/memory-plan` then
`POST /api/runs/{id}/publish` with `keep` / `skip`:

* every lesson carries a stable id, a plain description and its rows;
* a skipped lesson reaches neither the learning store nor the merchant list,
  a kept one does, and the journal holds exactly the kept writes;
* a skipped lesson is offered again, and ticking it later saves it;
* nothing ticked still publishes;
* a conflict is offered as unticked candidates, saved by no default, and a
  ticked candidate is written through the real learner;
* on a GL month a kept account correction lands in that company's
  `merchants[].accounts` entry;
* OpenAI, Anthropic and Lovable are never written to the merchant list.

Owner decisions 2026-09-25: corrections start ticked, conflicts unticked;
an unticked lesson is dropped and offered again; zero ticked publishes.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
PAID = "field_correction:Corporate Services|staples|paid_through"
VENDOR = "field_correction:Corporate Services|staples|vendor"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


@pytest.fixture
def gl_client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": []},
        CLOUD_ORG: {"org": {"name": CLOUD}, "accounts": []},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _batch(client, monkeypatch, vendors=("Staples",)) -> tuple[str, list[str]]:
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-07-01", total=f"4{i}.50", currency="USD", vendor=v,
            reference="", line_items=(), confidence=0.9, notes="",
        )
        for i, v in enumerate(vendors)
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=[
        ("files", (f"r{i}.jpg", JPG + bytes([i]) * (i + 1), "application/octet-stream"))
        for i in range(len(vendors))
    ])
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    rows = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return batch, [r["document_id"] for r in rows]


def _edit(client, batch, doc, field, value) -> None:
    resp = client.put(f"/api/runs/{batch}/expenses/{doc}", json={"field": field, "value": value})
    assert resp.status_code == 200, resp.text


def _plan(client, batch) -> dict:
    resp = client.get(f"/api/runs/{batch}/memory-plan")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _lessons(client, batch) -> dict[str, dict]:
    return {lsn["id"]: lsn for lsn in _plan(client, batch)["lessons"]}


def _publish(client, batch, **ticks) -> dict:
    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True, **ticks})
    assert resp.status_code == 200, resp.text
    assert resp.json()["published"] is True
    return resp.json()["memory"]


def _fields(client) -> set[str]:
    return {c["field"] for c in client.get("/api/memory").json()["field_corrections"]}


def _categories(client) -> dict[tuple, dict]:
    return {
        (c["entity"], c["vendor"]): c
        for c in client.get("/api/memory").json()["categories"]
    }


def _merchants(client) -> dict:
    return client.get("/api/settings").json()["merchants"]


def test_each_lesson_has_an_id_a_description_and_its_rows(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")

    lessons = _lessons(client, batch)
    paid = lessons[PAID]
    assert paid["kind"] == "correction" and paid["default_keep"] is True
    assert paid["key"] == {
        "legal_entity_id": CORP, "vendor_norm": "staples", "field": "paid_through"}
    assert "1010 Chase" in paid["description"]
    assert [s["document_id"] for s in paid["sources"]] == [doc]
    registry = lessons["registry:Staples Inc"]
    assert "new spelling Staples" in registry["description"]
    # The ids are stable: the same corrections offer the same ids.
    assert set(_lessons(client, batch)) == set(lessons)


def test_a_skipped_lesson_is_not_saved_and_the_kept_ones_are(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch)
    _edit(client, batch, doc, "vendor", "Staples Inc")
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    plan = _plan(client, batch)

    memory = _publish(client, batch, skip=[PAID, "registry:Staples Inc"])
    assert memory["saved"] is True
    assert memory["learned"]["lessons"]["skipped"] == [PAID, "registry:Staples Inc"]
    assert _fields(client) == {"vendor"}, "the skipped field correction was saved"
    assert "Staples Inc" not in _merchants(client), "the skipped registry entry was saved"
    assert memory["learned"]["field_corrections"] == 1, "the toast counts what was written"

    # The journal holds exactly the kept lessons' keys, as the plan named them.
    (commit,) = client.get("/api/memory/commits").json()["commits"]
    kept_keys = [
        (w["table"], w["key"]) for w in plan["writes"]
        if f"{w['table']}:{'|'.join(w['key'].values())}" in memory["learned"]["lessons"]["kept"]
    ]
    assert [(r["table"], r["key"]) for r in commit["rows"]] == kept_keys
    assert commit["n_merchants_changed"] == 0


def test_a_skipped_lesson_is_offered_again_and_ticking_it_later_saves_it(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    _publish(client, batch, keep=[])
    assert _fields(client) == set()

    assert client.post(f"/api/runs/{batch}/unpublish").status_code == 200
    assert PAID in _lessons(client, batch), "the unticked lesson is offered again"
    memory = _publish(client, batch, keep=[PAID])
    assert memory["saved"] is True and memory["learned"]["lessons"]["kept"] == [PAID]
    assert _fields(client) == {"paid_through"}

    # And a third publish with the same ticks teaches nothing twice.
    assert client.post(f"/api/runs/{batch}/unpublish").status_code == 200
    assert _publish(client, batch, keep=[PAID]) == {"saved": False, "reason": "unchanged"}


def test_nothing_ticked_still_publishes(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch)
    _edit(client, batch, doc, "paid_through", "1010 Chase")
    memory = _publish(client, batch, keep=[])
    assert memory["learned"]["lessons"]["kept"] == []
    assert memory["learned"]["lessons"]["skipped"] == [PAID]
    assert _fields(client) == set()


def test_an_account_only_fix_does_not_teach_the_models_category(client, monkeypatch):
    """The registry learner read `ov["category"]` raw, so an account-only fix
    (which re-stores the model's category as `inherited`) taught the model's
    category into the merchant list. Only her own category teaches."""
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=[ClassificationResult(
            "Office Supplies & Consumables", None, 0.9, "mock")] * 4,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": CORP})
    batch = resp.json()["batch_id"]
    resp = client.post(f"/api/expense-batches/{batch}/receipts",
                       files=[("files", ("s.jpg", JPG, "application/octet-stream"))])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    (row,) = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    _edit(client, batch, row["document_id"], "zoho_account", "6000 Office")

    _publish(client, batch)
    staples = _merchants(client)["Staples"]
    assert staples["zoho_account"] == "6000 Office"
    assert staples["category"] is None, "the model's category was taught as hers"


def test_a_conflict_is_offered_unticked_and_not_saved_by_default(client, monkeypatch):
    batch, (a, b) = _batch(client, monkeypatch, vendors=("Staples", "Staples"))
    _edit(client, batch, a, "category", "Office Supplies & Consumables")
    _edit(client, batch, b, "category", "Equipment & Hardware")

    lessons = _lessons(client, batch)
    assert "merchant_category:Corporate Services|staples" not in lessons
    conflicts = [lsn for lsn in lessons.values() if lsn["kind"] == "conflict"
                 and lsn["table"] == "merchant_category"]
    assert len(conflicts) == 2 and not any(c["default_keep"] for c in conflicts)
    assert len({c["conflict_group"] for c in conflicts}) == 1
    assert {c["sources"][0]["document_id"] for c in conflicts} == {a, b}

    _publish(client, batch)
    assert (CORP, "staples") not in _categories(client), "a conflict was auto-saved"
    assert "Staples" not in _merchants(client)

    # Ticking ONE candidate writes it, through the learner, with its value.
    pick = next(c for c in conflicts if "Equipment" in c["description"])
    reg_pick = next(lsn for lsn in lessons.values() if lsn["kind"] == "conflict"
                    and lsn["table"] == "registry" and "Equipment" in lsn["description"])
    assert client.post(f"/api/runs/{batch}/unpublish").status_code == 200
    memory = _publish(client, batch, keep=[pick["id"], reg_pick["id"]])
    assert memory["learned"]["lessons"]["unresolved_conflicts"] == []
    assert _categories(client)[(CORP, "staples")]["category"] == "Equipment & Hardware"
    assert _merchants(client)["Staples"]["category"] == "Equipment & Hardware"


def test_two_candidates_of_one_conflict_kept_together_teach_nothing(client, monkeypatch):
    batch, (a, b) = _batch(client, monkeypatch, vendors=("Staples", "Staples"))
    _edit(client, batch, a, "category", "Office Supplies & Consumables")
    _edit(client, batch, b, "category", "Equipment & Hardware")
    both = [lsn["id"] for lsn in _lessons(client, batch).values()
            if lsn["kind"] == "conflict" and lsn["table"] == "merchant_category"]
    memory = _publish(client, batch, keep=both)
    assert memory["learned"]["lessons"]["unresolved_conflicts"] == [
        "merchant_category:Corporate Services|staples"]
    assert (CORP, "staples") not in _categories(client)


def test_an_owner_gated_merchant_is_never_written_to_the_list(client, monkeypatch):
    batch, (doc,) = _batch(client, monkeypatch, vendors=("Anthropic, PBC",))
    _edit(client, batch, doc, "vendor", "Anthropic")
    lesson = _lessons(client, batch)["registry:Anthropic"]
    assert lesson["owner_gated"] is True and lesson["default_keep"] is False

    memory = _publish(client, batch, keep=["registry:Anthropic", VENDOR.replace(
        "staples", "anthropic pbc")])
    assert memory["learned"]["lessons"]["refused_owner_gated"] == ["registry:Anthropic"]
    assert "Anthropic" not in _merchants(client)


def _gl_pick(gl_client, monkeypatch, entity: str, code: str) -> str:
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
        reference="", line_items=(), confidence=0.9, notes="")])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = gl_client.post("/api/expense-batches", data={"legal_entity": entity})
    batch = resp.json()["batch_id"]
    resp = gl_client.post(f"/api/expense-batches/{batch}/receipts",
                          files=[("files", ("a.jpg", JPG, "application/octet-stream"))])
    assert gl_client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    body = gl_client.get(f"/api/expense-batches/{batch}").json()
    assert body["category_vocabulary"] == "gl", "precondition: a GL month"
    doc = body["expenses"][0]["document_id"]
    resp = gl_client.post(f"/api/runs/{batch}/categories",
                          json={"document_id": doc, "line_index": 0, "category": code})
    assert resp.status_code == 200, resp.text
    return batch


def test_a_kept_gl_account_correction_lands_in_that_companys_accounts(gl_client, monkeypatch):
    code = sorted(curated_leaves.postable_codes(CORP_ORG))[0]
    batch = _gl_pick(gl_client, monkeypatch, CORP, code)
    lesson = _lessons(gl_client, batch)["registry:Acme"]
    assert f"account in {CORP} {code}" in lesson["description"]

    _publish(gl_client, batch)
    acme = _merchants(gl_client)["Acme"]
    assert acme["accounts"] == {CORP: code}
    assert not acme.get("zoho_account"), "a GL account never becomes the single account"
    assert not acme.get("category"), "a leaf code is the account, not the default"


def test_a_skipped_gl_account_correction_writes_no_account(gl_client, monkeypatch):
    code = sorted(curated_leaves.postable_codes(CORP_ORG))[0]
    batch = _gl_pick(gl_client, monkeypatch, CORP, code)
    _publish(gl_client, batch, skip=["registry:Acme"])
    assert "Acme" not in _merchants(gl_client)
