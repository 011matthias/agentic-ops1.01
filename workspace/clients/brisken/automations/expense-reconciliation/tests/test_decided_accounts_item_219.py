"""Item 219: a merchant's decided accounts post as a rule and cannot drift.

Owner 2026-09-25: a flag on the merchant entry (`accounts_locked`) replaces
the name tuple as what protects OpenAI / Anthropic / Lovable accounts; no
learner re-points a locked entry; a person's booking against it is offered as
one unticked "change the default" lesson, and ticking it is the only learner
path that changes the account. Without the flag the three names stay refused.

Pinned at the callers: the settings route that stores the flag, a GL batch's
categorization (a model that fails if asked proves the rule decided), the
receiptless-charge path, and `memory-plan` -> `publish`.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.categorize_charges import categorize_charges  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.matching.types import (  # noqa: E402
    MatchOutcome,
    Transaction,
    answer_origin,
)
from expense_recon.merchant_registry import MerchantRegistry  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
ENTITY_ORGS = {CORP: CORP_ORG, CLOUD: CLOUD_ORG}
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _leaves(org: str) -> list[str]:
    # Leaves the model is offered and a person may pick (never a parent).
    return [c for c in sorted(curated_leaves.postable_codes(org))
            if not curated_leaves.has_postable_children(org, c)]


DECIDED, OTHER = _leaves(CORP_ORG)[:2]
CLOUD_DECIDED = _leaves(CLOUD_ORG)[0]
DRIFT = f"drift:Anthropic|{CORP}:{OTHER}"


class _NoModel(MockLLMClient):
    """Extracts as told; any categorization call is a test failure."""

    def classify_line_items(self, *a, **k):
        raise AssertionError("the model was asked")

    def classify_by_vendor(self, *a, **k):
        raise AssertionError("the model was asked")


@pytest.fixture
def web(tmp_path, monkeypatch):
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


def _anthropic(locked: bool = True) -> dict:
    entry = {"aliases": ["Anthropic, PBC"], "category": None, "zoho_account": None,
             "accounts": {CORP: DECIDED, CLOUD: CLOUD_DECIDED}}
    if locked:
        entry["accounts_locked"] = True
    return entry


def _put_merchants(web, merchants: dict) -> dict:
    r = web.put("/api/settings", json={"merchants": merchants})
    assert r.status_code == 200, r.text
    return r.json()["merchants"]


def _merchants(web) -> dict:
    return web.get("/api/settings").json()["merchants"]


def _batch(web, monkeypatch, vendor: str, lines=()) -> tuple[str, dict]:
    mock = _NoModel(extraction_responses=[ExtractedReceipt(
        date="2026-10-02", total="40.00", currency="USD", vendor=vendor,
        reference="", line_items=tuple(lines), confidence=0.9, notes="")])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    r = web.post("/api/expense-batches", data={"legal_entity": CORP})
    assert r.status_code == 200, r.text
    batch = r.json()["batch_id"]
    r = web.post(f"/api/expense-batches/{batch}/receipts",
                 files=[("files", ("r.jpg", JPG, "application/octet-stream"))])
    assert r.status_code == 200, r.text
    assert web.get(f"/jobs/{r.json()['job_id']}").json()["status"] == "done"
    body = web.get(f"/api/expense-batches/{batch}").json()
    assert body["category_vocabulary"] == "gl", "precondition: a GL month"
    (row,) = body["expenses"]
    return batch, row


def _pick(web, batch, doc, code) -> None:
    r = web.post(f"/api/runs/{batch}/categories",
                 json={"document_id": doc, "line_index": 0, "category": code})
    assert r.status_code == 200, r.text


def _lessons(web, batch) -> dict[str, dict]:
    r = web.get(f"/api/runs/{batch}/memory-plan")
    assert r.status_code == 200, r.text
    return {lsn["id"]: lsn for lsn in r.json()["lessons"]}


def _publish(web, batch, **ticks) -> dict:
    r = web.post(f"/api/runs/{batch}/publish", json={"override": True, **ticks})
    assert r.status_code == 200, r.text
    return r.json()["memory"]


def _rule(web, vendor: str) -> dict | None:
    for c in web.get("/api/memory").json()["categories"]:
        if (c["entity"], c["vendor"]) == (CORP, vendor):
            return c
    return None


# ── a decided account posts ─────────────────────────────────────────────


def test_a_locked_account_posts_on_an_itemized_receipt_without_the_model(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    _batch_id, row = _batch(web, monkeypatch, "Anthropic, PBC",
                            lines=[ExtractedLineItem("Claude Max, 1 month", "40.00")])
    posting = row["posting_category"]
    assert posting["category"] == DECIDED
    assert posting["origin"] == "rule", "a decided account posts; it is no suggestion"


def test_a_locked_account_posts_on_a_receiptless_charge():
    reg = MerchantRegistry({"Anthropic": _anthropic()})
    tx = Transaction(
        transaction_id="t1", legal_entity_id=CORP, account_id="card",
        transaction_date=date(2026, 10, 3), posting_date=None,
        amount=Decimal("20"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="ANTHROPIC",
    )
    out = categorize_charges(MatchOutcome(unmatched_transactions=["t1"]), [tx],
                             client=_NoModel(), registry=reg, entity_orgs=ENTITY_ORGS)
    assert out["t1"].category == DECIDED
    assert answer_origin(out["t1"]) == "rule"


# ── nothing learns over it ──────────────────────────────────────────────


def test_publish_never_overwrites_a_locked_account(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], OTHER)

    lessons = _lessons(web, batch)
    assert "merchant_category:Corporate Services|anthropic" not in lessons, (
        "her rule for a decided cell rides inside the drift lesson, never alone")
    assert not any(lid.startswith("conflict:") for lid in lessons)
    memory = _publish(web, batch)
    assert memory["learned"]["lessons"]["kept"] == []
    assert _merchants(web)["Anthropic"]["accounts"][CORP] == DECIDED
    assert _rule(web, "anthropic") is None


def test_the_lock_protects_any_merchant_not_only_the_three_names(web, monkeypatch):
    # The name gate cannot answer for Acme, so this pins the learner's lock.
    _put_merchants(web, {"Acme": {"aliases": [], "category": None, "zoho_account": None,
                                  "accounts": {CORP: DECIDED}, "accounts_locked": True}})
    batch, row = _batch(web, monkeypatch, "Acme")
    _pick(web, batch, row["document_id"], OTHER)
    lessons = _lessons(web, batch)
    assert "registry:Acme" not in lessons, "the learner leaves a locked entry as it is"
    assert f"drift:Acme|{CORP}:{OTHER}" in lessons

    _publish(web, batch, keep=[lid for lid in lessons if not lid.startswith("drift:")])
    assert _merchants(web)["Acme"]["accounts"] == {CORP: DECIDED}


def test_a_persons_pick_still_wins_on_her_own_row(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], OTHER)
    (after,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert after["posting_category"]["category"] == OTHER
    assert after["posting_category"]["origin"] == "person"


# ── the drift lesson ────────────────────────────────────────────────────


def test_a_booking_against_the_decided_account_is_one_unticked_lesson(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], OTHER)

    lesson = _lessons(web, batch)[DRIFT]
    assert lesson["kind"] == "drift"
    assert lesson["default_keep"] is False and lesson["owner_gated"] is False
    text = lesson["description"]
    assert text.startswith(f"Change the default for Anthropic in {CORP} to {OTHER}")
    assert "1 of this month's 1 Anthropic rows" in text
    assert f"the decided account is {DECIDED}" in text
    assert [s["document_id"] for s in lesson["sources"]] == [row["document_id"]]


def test_ticking_the_drift_lesson_is_what_changes_the_account(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], OTHER)

    memory = _publish(web, batch, keep=[DRIFT])
    assert memory["learned"]["lessons"]["kept"] == [DRIFT]
    anthropic = _merchants(web)["Anthropic"]
    assert anthropic["accounts"] == {CLOUD: CLOUD_DECIDED, CORP: OTHER}
    assert anthropic["accounts_locked"] is True, "a ticked change keeps the lock"
    assert _rule(web, "anthropic")["category"] == OTHER


def test_rows_that_agree_with_the_decision_keep_their_ordinary_lesson(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic()})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], DECIDED)
    lessons = _lessons(web, batch)
    assert not any(lid.startswith("drift:") for lid in lessons)
    assert lessons["merchant_category:Corporate Services|anthropic"]["default_keep"] is True


# ── unlocked merchants behave as before ─────────────────────────────────


def test_an_unlocked_vendor_still_learns_its_account(web, monkeypatch):
    _put_merchants(web, {"Acme": {"aliases": [], "category": None,
                                  "zoho_account": None, "accounts": {CORP: DECIDED}}})
    batch, row = _batch(web, monkeypatch, "Acme")
    _pick(web, batch, row["document_id"], OTHER)
    lessons = _lessons(web, batch)
    assert not any(lid.startswith("drift:") for lid in lessons)
    assert lessons["registry:Acme"]["default_keep"] is True

    _publish(web, batch)
    assert _merchants(web)["Acme"]["accounts"] == {CORP: OTHER}


def test_the_three_names_stay_refused_without_the_flag(web, monkeypatch):
    _put_merchants(web, {"Anthropic": _anthropic(locked=False)})
    batch, row = _batch(web, monkeypatch, "Anthropic, PBC")
    _pick(web, batch, row["document_id"], OTHER)
    lessons = _lessons(web, batch)
    assert not any(lid.startswith("drift:") for lid in lessons)
    assert lessons["registry:Anthropic"]["owner_gated"] is True

    memory = _publish(web, batch, keep=list(lessons))
    assert memory["learned"]["lessons"]["refused_owner_gated"] == ["registry:Anthropic"]
    assert _merchants(web)["Anthropic"]["accounts"][CORP] == DECIDED


# ── the flag through Settings ───────────────────────────────────────────


def test_settings_keeps_the_flag_on_a_save_that_omits_it_and_a_person_can_change_it(web):
    _put_merchants(web, {"Anthropic": _anthropic()})
    known_only = {k: v for k, v in _anthropic().items() if k != "accounts_locked"}
    moved = {**known_only, "accounts": {CORP: OTHER, CLOUD: CLOUD_DECIDED}}
    stored = _put_merchants(web, {"Anthropic": moved})["Anthropic"]
    assert stored["accounts_locked"] is True, "an editor that omits the flag keeps it"
    assert stored["accounts"][CORP] == OTHER, "a person changes a decided account on purpose"

    cleared = _put_merchants(web, {"Anthropic": {**moved, "accounts_locked": False}})
    assert "accounts_locked" not in cleared["Anthropic"]
