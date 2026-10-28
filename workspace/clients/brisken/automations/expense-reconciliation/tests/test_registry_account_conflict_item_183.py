"""Item 183: a disagreeing posting account is a conflict, in both learners.

Two rows of one month that agree on the category and name DIFFERENT accounts
used to agree. The per-row cell was discarded from the second row on, so the
first account won silently, in the writers of durable memory that later runs
consult ahead of the model. Under the direct-to-GL design the account IS the
answer, so that is a nearest-plausible default in exactly the wrong place.

These tests drive the HTTP routes, not the pure helpers, because the helpers
already had unit coverage that would stay green with the wiring removed
(rule_behaviors B2, fix-bites-the-caller). Each assertion here goes through
`POST /api/runs/{id}/commit-memory`, which is the caller that folds both
learners into durable state.

Two learners are covered and they are not the same one:
  - the settings merchant registry (`registry_upserts_from_expense_run`)
  - `learning/store.merchant_category` (`_learn_categories`), which is Tier 1
    of the direct-to-GL chain and is consulted AHEAD of the registry
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.learning import LearningStore  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CAFE = "Cafe Nero"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        c._learning_db = app.state.learning_db_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-07-01", total="42.50", currency="USD", vendor=CAFE,
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _two_receipts_one_vendor(client, monkeypatch):
    """A month holding two receipts from the SAME vendor. Returns both ids."""
    mock = MockLLMClient(extraction_responses=[
        _extraction(reference="r1"), _extraction(reference="r2"),
    ])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "Corporate Services"}
    )
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    resp = client.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[
            ("files", ("a.jpg", JPG, "application/octet-stream")),
            ("files", ("b.jpg", JPG + b"2", "application/octet-stream")),
        ],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    rows = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert len(rows) == 2, f"precondition: two receipts, got {len(rows)}"
    return batch, [r["document_id"] for r in rows]


def _edit(client, batch, doc, field, value):
    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}", json={"field": field, "value": value}
    )
    assert resp.status_code == 200, resp.text


def _commit(client, batch):
    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    return resp.json()["learned"]


def _stored_rule(client, vendor_norm="cafe nero", entity="Corporate Services"):
    with LearningStore(client._learning_db) as s:
        return s.get_merchant_category(entity, vendor_norm)


# ── the defect: same category, two different accounts ───────────────────


def test_two_accounts_under_one_category_refuse_to_teach_the_registry(
    client, monkeypatch
):
    """The settings registry learns nothing, and says why."""
    batch, (d1, d2) = _two_receipts_one_vendor(client, monkeypatch)
    for doc, account in ((d1, "E100 - Meals"), (d2, "E200 - Travel")):
        _edit(client, batch, doc, "category", "Meals & Entertainment")
        _edit(client, batch, doc, "zoho_account", account)

    registry = _commit(client, batch)["registry"]

    assert registry["skipped_account_conflict"] == 1, (
        "two rows naming different accounts must conflict, not agree"
    )
    assert registry["categories_set"] == 0, (
        "nothing may be taught for a merchant whose rows disagree on the account"
    )
    merchants = client.get("/api/settings").json()["merchants"]
    assert merchants.get(CAFE, {}).get("zoho_account") in (None, ""), (
        "the first row's account won silently -- this is the item 183 bug"
    )


def test_two_accounts_under_one_category_refuse_to_teach_tier_one(
    client, monkeypatch
):
    """`merchant_category` is Tier 1 of the direct-to-GL chain, and it is
    consulted ahead of the registry, so it must refuse for the same reason."""
    batch, (d1, d2) = _two_receipts_one_vendor(client, monkeypatch)
    for doc, account in ((d1, "E100 - Meals"), (d2, "E200 - Travel")):
        _edit(client, batch, doc, "category", "Meals & Entertainment")
        _edit(client, batch, doc, "zoho_account", account)

    _commit(client, batch)

    row = _stored_rule(client)
    assert row is None or row.zoho_account in (None, ""), (
        "Tier 1 took the first row's account; the model is overruled by a guess"
    )


# ── absence is not disagreement ─────────────────────────────────────────


def test_a_row_naming_no_account_is_silent_not_dissenting(client, monkeypatch):
    """One row names an account, the other names none. That is agreement:
    refusing here would make the learner refuse nearly every real month,
    since most rows carry no account at all."""
    batch, (d1, d2) = _two_receipts_one_vendor(client, monkeypatch)
    _edit(client, batch, d1, "category", "Meals & Entertainment")
    _edit(client, batch, d1, "zoho_account", "E100 - Meals")
    _edit(client, batch, d2, "category", "Meals & Entertainment")

    registry = _commit(client, batch)["registry"]

    assert registry["skipped_account_conflict"] == 0, (
        "a row that names no account was treated as a second opinion"
    )
    assert registry["categories_set"] == 1
    merchants = client.get("/api/settings").json()["merchants"]
    assert merchants[CAFE]["zoho_account"] == "E100 - Meals"


def test_matching_accounts_still_teach(client, monkeypatch):
    """The control: two rows that genuinely agree must still learn. Without
    this, a fix that refused everything would pass the tests above."""
    batch, (d1, d2) = _two_receipts_one_vendor(client, monkeypatch)
    for doc in (d1, d2):
        _edit(client, batch, doc, "category", "Meals & Entertainment")
        _edit(client, batch, doc, "zoho_account", "E100 - Meals")

    registry = _commit(client, batch)["registry"]

    assert registry["skipped_account_conflict"] == 0
    assert registry["categories_set"] == 1
    merchants = client.get("/api/settings").json()["merchants"]
    assert merchants[CAFE]["zoho_account"] == "E100 - Meals"
    row = _stored_rule(client)
    assert row is not None and row.zoho_account == "E100 - Meals"


# ── a category-only teach must not wipe a learned account ───────────────


def test_a_category_only_month_keeps_the_learned_account(client, monkeypatch):
    """`record_merchant_category` overwrote `zoho_account` unconditionally,
    so a month whose reviewer picked a category and named no account nulled
    the account Tier 1 had learned. Its operator twin has carried a
    `keep_account` guard for exactly this; now so does it.

    Absence of an account in one month's edits is silence, not a decision to
    forget one."""
    with LearningStore(client._learning_db) as s:
        s.record_merchant_category(
            "Corporate Services", "cafe nero", "Meals & Entertainment",
            "E100 - Meals", "2026-07-01T00:00:00", "seed-run",
        )
    assert _stored_rule(client).zoho_account == "E100 - Meals", "precondition"

    batch, (d1, _d2) = _two_receipts_one_vendor(client, monkeypatch)
    _edit(client, batch, d1, "category", "Meals & Entertainment")
    _commit(client, batch)

    row = _stored_rule(client)
    assert row is not None
    assert row.zoho_account == "E100 - Meals", (
        "a category-only edit wiped the learned posting account the COA gate "
        "and the direct-to-GL chain depend on"
    )


# ── the planned-write round trip ────────────────────────────────────────


def test_a_planned_write_carries_its_keywords():
    """`RecordingStore` + `apply_plan` are the dry-run pair: the recorder
    takes the learners' calls, the replay applies them. `keep_account`
    travels as a keyword, and a plan that dropped it would preview "the
    account is kept" and then apply a write that wipes it.

    Helper-level on purpose, and it is the only level available: `apply_plan`
    is exported but has no caller in src/ today (the live preview path at
    web/service.py:15744 uses RecordingStore alone). The recorder half IS
    driven through the routes by the tests above; this pins the replay half
    so the two cannot drift apart.
    """
    from expense_recon.learning import RecordingStore, apply_plan

    rec = RecordingStore()
    rec.record_merchant_category(
        "Corporate Services", "cafe nero", "Meals & Entertainment", None,
        "2026-07-01T00:00:00", "run-1", keep_account=True,
    )
    assert rec.writes[0].kwargs == {"keep_account": True}

    seen: list[tuple] = []

    class _Spy:
        def record_merchant_category(self, *args, **kwargs):
            seen.append((args, kwargs))

    assert apply_plan(_Spy(), rec.writes) == 1
    assert seen[0][1] == {"keep_account": True}, (
        "the replay dropped the keyword, so the applied write would wipe an "
        "account the preview promised to keep"
    )
