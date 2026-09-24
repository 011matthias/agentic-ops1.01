"""Phase 1, item 3: the engine categorizes straight into curated GL leaves.

Three things this file pins, each at the CALLER rather than the helper:

* the org id, never the legal-entity name, reaches `llm_leaf_labels`: a name
  there answers with no labels, silently, and every row would refuse;
* `bool(cat.category)` is False exactly when the engine refused, and a
  refusal carries its reason to the review the reviewer reads;
* the category write route clears on "" / null and drops a string from
  neither vocabulary under `ignored` (3c).
"""
from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from expense_recon.categorize import (
    categorize_receipts,
    categorize_receipts_with_registry,
)
from expense_recon.learning.consult import RECALL_COMPANY
from expense_recon.llm.client import ClassificationResult
from expense_recon.matching.types import (
    ClassificationSource,
    LineItem,
    Receipt,
)
from expense_recon.zoho import curated_leaves
from expense_recon.zoho.posting_resolution import (
    ACCOUNT_UNRESOLVED,
    ENTITY_MISSING,
)

CORP = "Corporate Services"
CORP_ORG = "822741658"
CLOUD_ORG = "697686691"
ENTITY_ORGS = {CORP: CORP_ORG, "Cloud Services": CLOUD_ORG}


def _receipt(entity=CORP, *, vendor="Acme", lines=True, doc="r1") -> Receipt:
    items = (
        (LineItem(description="Laptop stand, aluminium", line_total=Decimal("40")),)
        if lines else ()
    )
    return Receipt(
        document_id=doc,
        legal_entity_id=entity,
        detected_date=None,
        detected_total=Decimal("40"),
        detected_currency="USD",
        detected_vendor=vendor,
        line_items=items,
    )


def _postable_in(org: str) -> str:
    return sorted(curated_leaves.postable_codes(org))[0]


def _postable_here_not_there(here: str, there: str) -> str:
    """A code this org may post to that the other org cannot, because it
    marks it N or has no such account. Prefers the N case when one exists."""
    candidates = [
        c for c in sorted(curated_leaves.postable_codes(here))
        if not curated_leaves.is_postable(there, c)
    ]
    assert candidates, "fixture: every code is postable in both orgs"
    marked = [c for c in candidates if curated_leaves.binding(c, there)]
    return (marked or candidates)[0]


class _LeafClient:
    """Answers with the label whose code is `code` (or `reply` verbatim), and
    records the choice list it was handed."""

    def __init__(self, code=None, *, reply=None, confidence=0.9):
        self.code, self.reply, self.confidence = code, reply, confidence
        self.calls: list[list[str]] = []

    def _pick(self, categories):
        self.calls.append(list(categories))
        if self.reply is not None:
            return self.reply
        return next(c for c in categories if c.split(None, 1)[0] == self.code)

    def classify_line_items(self, items, categories, chart_of_accounts=None, **_):
        label = self._pick(categories)
        return [ClassificationResult(label, None, self.confidence, "fake")
                for _ in items]

    def classify_by_vendor(self, vendor, total, categories,
                           chart_of_accounts=None, **_):
        return ClassificationResult(
            self._pick(categories), None, self.confidence, "fake")


def _cats(receipts):
    return [li.categorization for r in receipts for li in r.line_items]


def _assert_invariant(cats):
    for c in cats:
        assert bool(c.category) == (c.refusal is None), c
        if c.refusal:
            assert c.category is None and c.zoho_account is None
            assert c.source is ClassificationSource.REVIEW


# ── the org id, never the name, reaches the leaf list ──────────────────


def test_the_model_is_handed_this_entitys_leaves_by_org_id(monkeypatch):
    seen: list = []
    real = curated_leaves.llm_leaf_labels

    def spy(org_id):
        seen.append(org_id)
        return real(org_id)

    monkeypatch.setattr(curated_leaves, "llm_leaf_labels", spy)
    code = _postable_in(CORP_ORG)
    client = _LeafClient(code)

    (out,) = categorize_receipts(
        [_receipt()], client=client, entity_orgs=ENTITY_ORGS)

    assert seen and set(seen) == {CORP_ORG}, seen
    assert client.calls == [list(real(CORP_ORG))]
    (cat,) = _cats([out])
    assert cat.category == code
    assert cat.zoho_account == curated_leaves.binding(code, CORP_ORG).name
    assert cat.source is ClassificationSource.LINE
    _assert_invariant([cat])


def test_an_entity_with_no_org_id_refuses_without_asking_the_model(monkeypatch):
    seen: list = []
    monkeypatch.setattr(
        curated_leaves, "llm_leaf_labels",
        lambda org_id: seen.append(org_id) or ())
    client = _LeafClient(reply="anything")

    (out,) = categorize_receipts(
        [_receipt("Consulting")], client=client, entity_orgs=ENTITY_ORGS)

    (cat,) = _cats([out])
    assert cat.refusal == curated_leaves.NOT_COVERED
    assert client.calls == [] and seen == []
    _assert_invariant([cat])


def test_a_receipt_with_no_company_refuses_as_entity_missing():
    client = _LeafClient(reply="anything")
    (out,) = categorize_receipts(
        [_receipt("")], client=client, entity_orgs=ENTITY_ORGS)
    (cat,) = _cats([out])
    assert cat.refusal == ENTITY_MISSING
    assert client.calls == []


def test_an_empty_leaf_list_is_a_refusal_not_a_prompt(monkeypatch):
    monkeypatch.setattr(curated_leaves, "llm_leaf_labels", lambda org_id: ())
    client = _LeafClient(reply="anything")
    (out,) = categorize_receipts(
        [_receipt()], client=client, entity_orgs=ENTITY_ORGS)
    assert _cats([out])[0].refusal == curated_leaves.NOT_COVERED
    assert client.calls == []


# ── the invariant, across every way a row can refuse ───────────────────


def test_a_leaf_the_entity_cannot_post_to_refuses_by_name():
    code = _postable_here_not_there(CLOUD_ORG, CORP_ORG)
    client = _LeafClient(reply=code)
    (out,) = categorize_receipts(
        [_receipt()], client=client, entity_orgs=ENTITY_ORGS)
    (cat,) = _cats([out])
    assert cat.refusal == curated_leaves.refusal_reason(CORP_ORG, code)
    _assert_invariant([cat])


def test_an_unsure_model_and_a_name_it_invented_both_refuse_unresolved():
    unsure = _LeafClient(_postable_in(CORP_ORG), confidence=0.3)
    invented = _LeafClient(reply="Office party balloons")
    for client in (unsure, invented):
        (out,) = categorize_receipts(
            [_receipt(lines=False)], client=client, entity_orgs=ENTITY_ORGS)
        (cat,) = _cats([out])
        assert cat.refusal == ACCOUNT_UNRESOLVED
        _assert_invariant([cat])


def test_no_client_and_no_rule_refuses_rather_than_taking_a_bucket():
    (out,) = categorize_receipts(
        [_receipt()], client=None, entity_orgs=ENTITY_ORGS)
    (cat,) = _cats([out])
    assert cat.refusal == ACCOUNT_UNRESOLVED
    assert cat.category is None


def test_without_the_map_the_bucket_path_is_unchanged():
    (out,) = categorize_receipts([_receipt()], client=None)
    (cat,) = _cats([out])
    assert cat.refusal is None
    assert cat.category == "Equipment & Hardware" or cat.category is None


# ── tier 1 and the registry answer through the same resolver ───────────


class _Lookup:
    def __init__(self, category, *, account=None, taught=True):
        row = SimpleNamespace(
            source_run="run-1", last_confirmed_at="2026-09-01T00:00:00",
            legal_entity_id=CORP, vendor_norm="acme")
        self._recall = SimpleNamespace(
            kind=RECALL_COMPANY, category=category, zoho_account=account,
            rows=(row,), taught_by_person=taught, validated=True)

    def recall(self, legal_entity_id, vendor):
        return self._recall


def test_a_taught_rule_naming_a_postable_leaf_wins_without_the_model():
    code = _postable_in(CORP_ORG)
    client = _LeafClient(reply="should not be asked")
    (out,) = categorize_receipts(
        [_receipt()], client=client, learned=_Lookup(code),
        entity_orgs=ENTITY_ORGS)
    (cat,) = _cats([out])
    assert cat.category == code and cat.source is ClassificationSource.LEARNED
    assert client.calls == []


def test_a_taught_rule_naming_an_unpostable_leaf_refuses_and_is_not_overruled():
    code = _postable_here_not_there(CLOUD_ORG, CORP_ORG)
    client = _LeafClient(_postable_in(CORP_ORG))
    (out,) = categorize_receipts(
        [_receipt()], client=client, learned=_Lookup(code),
        entity_orgs=ENTITY_ORGS)
    (cat,) = _cats([out])
    assert cat.refusal == curated_leaves.refusal_reason(CORP_ORG, code)
    assert client.calls == []


def test_a_bucket_only_rule_falls_through_to_the_model():
    code = _postable_in(CORP_ORG)
    client = _LeafClient(code)
    (out,) = categorize_receipts(
        [_receipt()], client=client,
        learned=_Lookup("Software & Subscriptions"), entity_orgs=ENTITY_ORGS)
    assert _cats([out])[0].category == code
    assert client.calls


class _Registry:
    def __init__(self, category, account=None):
        self.m = SimpleNamespace(
            canonical_name="Acme", category=category, zoho_account=account,
            multi_category=False, profile="")

    def resolve(self, vendor_clean, detected_vendor):
        return self.m

    def __bool__(self):
        return True


def test_a_registry_leaf_is_stamped_and_a_registry_bucket_is_not():
    code = _postable_in(CORP_ORG)
    client = _LeafClient(code)
    (leafed,), _ = categorize_receipts_with_registry(
        [_receipt()], registry=_Registry(code), client=client,
        entity_orgs=ENTITY_ORGS)
    assert _cats([leafed])[0].source is ClassificationSource.REGISTRY
    assert client.calls == []

    (bucketed,), _ = categorize_receipts_with_registry(
        [_receipt()], registry=_Registry("Software & Subscriptions"),
        client=client, entity_orgs=ENTITY_ORGS)
    cat = _cats([bucketed])[0]
    assert cat.category == code and cat.source is ClassificationSource.LINE
    assert client.calls, "a bucket default hands the receipt to the engine"


# ── the refusal reaches the review the reviewer reads ──────────────────


def test_a_refused_receipt_and_a_refused_charge_say_why():
    from expense_recon.web.service import (
        _matched_category_review,
        resolve_review,
    )

    (out,) = categorize_receipts(
        [_receipt("Consulting")], client=None, entity_orgs=ENTITY_ORGS)
    review = _matched_category_review(out, {})
    assert review["reason_code"] == "category_refused"
    assert review["refusal"] == curated_leaves.NOT_COVERED
    assert "No category yet" not in review["reason"]

    charge = resolve_review(
        is_posted=False, effective_bucket="unmatched", status="",
        matched_rec=None, overrides={}, charge_category=None,
        charge_categorization=_cats([out])[0])
    assert charge["state"] == "pick"
    assert charge["refusal"] == curated_leaves.NOT_COVERED


def test_a_bucket_path_row_keeps_the_generic_sentence():
    from dataclasses import replace

    from expense_recon.matching.types import Categorization
    from expense_recon.web.service import _matched_category_review

    no_signal = Categorization(
        category=None, zoho_account=None, confidence=0.0,
        source=ClassificationSource.REVIEW, reasoning="no signal")
    rec = _receipt()
    rec = replace(rec, line_items=tuple(
        replace(li, categorization=no_signal) for li in rec.line_items))
    review = _matched_category_review(rec, {})
    assert review["reason_code"] == "uncategorized"
    assert "refusal" not in review


# ── through the web: the map is injected, and 3c on the category route ─

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({CORP_ORG: {"org": {"name": CORP},
                                            "accounts": []}}), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _batch_with_one_receipt(web, monkeypatch, entity, reply):
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=[ClassificationResult(reply, None, 0.9, "mock")],
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": entity})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    resp = web.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("acme.jpg", JPG, "application/octet-stream"))])
    assert resp.status_code == 200, resp.text
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    (expense,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return batch_id, expense


def _stored_line(web, batch_id, document_id):
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        snap = json.loads(conn.execute(
            "SELECT snapshot FROM runs WHERE run_id = ?", (batch_id,)
        ).fetchone()["snapshot"])
        override = conn.execute(
            "SELECT category, zoho_account, category_source FROM "
            "category_overrides WHERE run_id = ? AND document_id = ?",
            (batch_id, document_id)).fetchone()
    finally:
        conn.close()
    (rec,) = [r for r in snap["receipts"] if r["document_id"] == document_id]
    return rec["line_items"][0]["categorization"], override


def test_a_web_batch_is_categorized_into_its_entitys_leaf(web, monkeypatch):
    code = _postable_in(CORP_ORG)
    label = next(lbl for lbl in curated_leaves.llm_leaf_labels(CORP_ORG)
                 if lbl.startswith(code + " "))
    batch_id, expense = _batch_with_one_receipt(web, monkeypatch, CORP, label)
    cat, _ = _stored_line(web, batch_id, expense["document_id"])
    assert cat["category"] == code, cat
    assert "refusal" not in cat


def test_a_web_batch_for_an_unprovisioned_company_refuses_and_says_so(
    web, monkeypatch,
):
    batch_id, expense = _batch_with_one_receipt(
        web, monkeypatch, "Consulting", "anything")
    cat, _ = _stored_line(web, batch_id, expense["document_id"])
    assert cat["category"] is None
    assert cat["refusal"] == curated_leaves.NOT_COVERED
    assert expense["review"]["reason_code"] == "category_refused"


def test_the_category_route_clears_on_empty_and_ignores_the_unknown(
    web, monkeypatch,
):
    code = _postable_in(CORP_ORG)
    label = next(lbl for lbl in curated_leaves.llm_leaf_labels(CORP_ORG)
                 if lbl.startswith(code + " "))
    batch_id, expense = _batch_with_one_receipt(web, monkeypatch, CORP, label)
    doc = expense["document_id"]
    url = f"/api/runs/{batch_id}/categories"

    r = web.post(url, json={"document_id": doc, "line_index": 0,
                            "category": label, "zoho_account": "Some account"})
    assert r.status_code == 200, r.text
    _, ov = _stored_line(web, batch_id, doc)
    assert ov["category"] == code, "a label is stored as its code"

    r = web.post(url, json={"document_id": doc, "line_index": 0,
                            "category": "Office party balloons"})
    assert r.json() == {"ok": True,
                        "ignored": {"category": "Office party balloons"}}
    _, ov = _stored_line(web, batch_id, doc)
    assert ov["category"] == code, "the drop leaves the stored pick alone"

    for clear in ("", None):
        web.post(url, json={"document_id": doc, "line_index": 0,
                            "category": code, "zoho_account": "Some account"})
        r = web.post(url, json={"document_id": doc, "line_index": 0,
                                "category": clear,
                                "zoho_account": "Some account"})
        assert r.status_code == 200, r.text
        _, ov = _stored_line(web, batch_id, doc)
        assert ov["category"] is None and ov["zoho_account"] is None, clear
        assert ov["category_source"] == "human"
