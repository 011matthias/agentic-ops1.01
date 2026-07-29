"""Phase 6: receipt-first learning — the batch that teaches the next one.

Only explicit edits teach (the statement-mode finalize-gate discipline):
a per-expense entity override teaches merchant -> entity; vendor /
tax_label / paid_through edits teach per-merchant field corrections keyed
on the ORIGINAL extracted vendor; category reclassifications teach
merchant -> category via the shared `_learn_categories`. The batch-level
default entity and untouched LLM guesses teach nothing. Consult happens
ONLY in `generate_expenses` (never `reconcile`), and every auto-fill
carries a grid-visible provenance note. `/api/memory` shows the new rows;
forget stops the auto-fill.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.learning import (  # noqa: E402
    ExpenseMemory,
    LearningStore,
    learn_from_expense_run,
    normalize_vendor,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, name="a.jpg", data=JPG, legal_entity="Corporate Services"):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", (name, data, "application/octet-stream"))],
        data={"legal_entity": legal_entity},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return resp.json()["batch_id"]


def _row(client, batch_id) -> dict:
    return client.get(f"/api/expense-batches/{batch_id}").json()["expenses"][0]


# ── store primitives ────────────────────────────────────────────────


def test_store_merchant_entity_and_field_correction(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_entity("staples", "Cloud Services", "t0", "run1")
        s.record_merchant_entity("staples", "Corporate Services", "t1", "run2")
        ent = s.get_merchant_entity("staples")
        assert ent.legal_entity_id == "Corporate Services"  # latest wins
        assert ent.decision_count == 2

        s.record_field_correction(
            "Corporate Services", "staples", "paid_through", "1010 Chase", "t0", "run1"
        )
        assert s.get_field_corrections("Corporate Services", "staples") == {
            "paid_through": "1010 Chase"
        }
        # Forgetting the vendor in that entity clears both.
        counts = s.forget_vendor("Corporate Services", "staples")
        assert counts["merchant_entity"] == 1
        assert counts["field_correction"] == 1
        assert s.get_merchant_entity("staples") is None


def test_forget_in_other_entity_keeps_entity_mapping(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_entity("staples", "Cloud Services", "t0", "r")
        # Forgetting staples FROM Corporate Services must not drop its
        # explicit mapping TO Cloud Services.
        counts = s.forget_vendor("Corporate Services", "staples")
        assert counts["merchant_entity"] == 0
        assert s.get_merchant_entity("staples").legal_entity_id == "Cloud Services"


# ── capture (unit) ──────────────────────────────────────────────────


def _receipt(doc="r1", vendor="Staples", entity="Corporate Services") -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=None,
        detected_total=Decimal("42.50"), detected_currency="USD",
        detected_vendor=vendor,
    )


def test_capture_teaches_only_explicit_edits(tmp_path):
    db = tmp_path / "learning.sqlite"
    original = [_receipt()]
    effective = [_receipt(vendor="Staples Inc", entity="Cloud Services")]
    with LearningStore(db) as s:
        summary = learn_from_expense_run(
            s,
            receipts=original,
            effective_receipts=effective,
            field_overrides={"r1": {
                "legal_entity": "Cloud Services",
                "vendor": "Staples Inc",
                "paid_through": "1010 Chase",
            }},
            category_overrides={},
            source_run="run1",
            now_iso="t0",
        )
        # Entity keyed on BOTH spellings, so next month's OCR (original)
        # and the canonical name both resolve.
        assert summary.merchant_entities == 2
        assert s.get_merchant_entity(normalize_vendor("Staples")).legal_entity_id == "Cloud Services"
        assert s.get_merchant_entity(normalize_vendor("Staples Inc")).legal_entity_id == "Cloud Services"
        # Corrections keyed on the ORIGINAL vendor under the effective entity.
        assert summary.field_corrections == 2
        assert s.get_field_corrections("Cloud Services", normalize_vendor("Staples")) == {
            "vendor": "Staples Inc", "paid_through": "1010 Chase",
        }


def test_capture_no_edits_teaches_nothing(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        summary = learn_from_expense_run(
            s,
            receipts=[_receipt()],
            effective_receipts=[_receipt()],
            field_overrides={},
            category_overrides={},
            source_run="run1",
            now_iso="t0",
        )
    assert summary.as_dict() == {
        "merchant_categories": 0, "skipped_mixed_category": 0,
        "merchant_entities": 0, "field_corrections": 0,
    }


def test_capture_manual_add_with_entity_teaches_mapping(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        summary = learn_from_expense_run(
            s,
            receipts=[],
            effective_receipts=[],
            field_overrides={},
            category_overrides={},
            manual_payloads={"manual:abc": {
                "vendor": "Taxi Roma", "legal_entity": "Cloud Services",
            }},
            source_run="run1",
            now_iso="t0",
        )
        assert summary.merchant_entities == 1
        assert s.get_merchant_entity(normalize_vendor("Taxi Roma")).legal_entity_id == "Cloud Services"


# ── consult (unit): ExpenseMemory.apply ─────────────────────────────


def test_expense_memory_apply_corrects_and_notes(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_entity(normalize_vendor("Staples"), "Cloud Services", "t0", "r")
        s.record_field_correction(
            "Cloud Services", normalize_vendor("Staples"), "vendor", "Staples Inc", "t0", "r"
        )
        s.record_field_correction(
            "Cloud Services", normalize_vendor("Staples"), "paid_through", "1010 Chase", "t0", "r"
        )
    memory = ExpenseMemory.from_db_path(db)
    (out,) = memory.apply([_receipt()])
    assert out.legal_entity_id == "Cloud Services"
    assert out.detected_vendor == "Staples Inc"
    assert out.paid_through == "1010 Chase"
    assert "Auto-filled from a prior correction" in out.data_quality_note
    # An unknown vendor passes through untouched.
    (other,) = memory.apply([_receipt(doc="r2", vendor="Cafe")])
    assert other.detected_vendor == "Cafe"
    assert other.data_quality_note is None


def test_empty_memory_is_a_no_op():
    r = _receipt()
    assert ExpenseMemory.from_db_path(None).apply([r]) == [r]


# ── the full loop: edit -> commit -> auto-fill -> forget ────────────


def test_commit_then_next_batch_autofills_then_forget_stops(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch1 = _create_batch(client)
    doc = _row(client, batch1)["document_id"]

    # Explicit edits: vendor spelling, paid-through, entity, category.
    for body in (
        {"field": "vendor", "value": "Staples Inc"},
        {"field": "paid_through", "value": "1010 Chase"},
        {"field": "category", "value": "Office Supplies & Consumables"},
    ):
        assert client.put(
            f"/api/runs/{batch1}/expenses/{doc}", json=body
        ).status_code == 200
    assert client.put(
        f"/api/runs/{batch1}/expenses/{doc}/entity",
        json={"legal_entity": "Cloud Services"},
    ).status_code == 200

    resp = client.post(f"/api/runs/{batch1}/commit-memory")
    assert resp.status_code == 200, resp.text
    learned = resp.json()["learned"]
    assert learned["merchant_entities"] >= 1
    assert learned["field_corrections"] == 2
    assert learned["merchant_categories"] == 1
    # The same edits also seed the canonical registry (2026-07-29): the raw
    # "Staples" becomes an alias of "Staples Inc", the category its default.
    assert learned["registry"]["aliases_added"] >= 1
    assert learned["registry"]["categories_set"] == 1

    # /api/memory shows the new rows.
    memory = client.get("/api/memory").json()
    assert any(e["entity"] == "Cloud Services" for e in memory["entities"])
    fields_learned = {c["field"] for c in memory["field_corrections"]}
    assert fields_learned == {"vendor", "paid_through"}
    assert memory["counts"]["merchant_entity"] >= 1

    # A NEW batch with the same OCR output auto-fills everything. The vendor
    # spelling + category now resolve via the REGISTRY (the correction seeded
    # settings["merchants"], which outranks the learned SQLite); the entity +
    # paid-through still come from the learned memory (ExpenseMemory).
    _patch_ocr(monkeypatch, _extraction())
    batch2 = _create_batch(client, name="again.jpg", data=JPG + b"x")
    row = _row(client, batch2)
    assert row["vendor"]["display"] == "Staples Inc"
    assert row["vendor"]["source"] == "registry"
    assert row["legal_entity_id"] == "Cloud Services"
    assert row["paid_through"] == "1010 Chase"
    assert "Auto-filled from a prior correction" in row["data_quality_note"]
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    assert row["posting_category"]["source"] == "registry"

    # Forget the merchant -> the LEARNED memory (entity + paid-through) reverts,
    # but the registry canonicalization persists: it is the durable, human-
    # editable store, cleared from the Merchants editor, not /memory/forget.
    resp = client.post("/api/memory/forget", json={
        "legal_entity_id": "Cloud Services", "vendor": "Staples",
    })
    assert resp.status_code == 200
    assert resp.json()["forgotten"]["field_correction"] == 2
    _patch_ocr(monkeypatch, _extraction())
    batch3 = _create_batch(client, name="third.jpg", data=JPG + b"y")
    row = _row(client, batch3)
    # Entity reverted (learned memory forgotten), the auto-fill note is gone...
    assert row["legal_entity_id"] == "Corporate Services"
    assert "Auto-filled from a prior correction" not in (row["data_quality_note"] or "")
    # ...but the registry still canonicalizes the vendor + its category.
    assert row["vendor"]["display"] == "Staples Inc"
    assert row["vendor"]["source"] == "registry"
    assert row["posting_category"]["source"] == "registry"


def test_batch_default_entity_never_teaches(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch = _create_batch(client)  # default entity, no edits at all
    assert client.post(f"/api/runs/{batch}/commit-memory").status_code == 200
    memory = client.get("/api/memory").json()
    assert memory["entities"] == []
    assert memory["field_corrections"] == []
