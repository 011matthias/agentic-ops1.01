"""The three learning leaks, closed 2026-09-24.

Owner ruling: publish-time learning may keep teaching, but ONLY human
corrections may be memorized. Five learners fire on the Publish path and
three of them taught things nobody had said:

* **Leak 1** the note-#62 Confirm ("keep this guess as it is") wrote the
  LLM's own category into `category_overrides` and sign-off then taught it
  as a correction. A person clicked; no person stated a category.
* **Leak 2** an account-only `PUT .../expenses/{id}` re-stored the line's
  current category beside the account she did name, so fixing only the
  ACCOUNT persisted the model's category as her word.
* **Leak 3** `apply_self_confirmations` writes STATUS_CONFIRMED with
  `decided_by=tool` after every re-match, and both alias/FX learners
  filtered on the status alone, so pairings nobody looked at taught durable
  vendor aliases and per-merchant exchange rates.

Leaks 1 and 2 are closed by `category_overrides.category_source`
(human | inherited), leak 3 by `reviewer_confirmed_tx_ids`. The negative
cases here are the contract: an explicit pick still teaches, and her
ACCOUNT still teaches even when the category riding along is the model's,
because that is the correction she actually made.
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.learning import (  # noqa: E402
    CATEGORY_SOURCE_HUMAN,
    CATEGORY_SOURCE_INHERITED,
    LearningStore,
    category_is_human,
    learn_from_expense_run,
    normalize_vendor,
)
from expense_recon.learning.capture import _learn_categories  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import (  # noqa: E402
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import reviewer_confirmed_tx_ids  # noqa: E402
from expense_recon.web.store import Decision, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-leaks-0924"
_SEQ = [0]

CARDS = {
    "corp-2838": {
        "label": "Credit Card Chase Visa - 2838",
        "digits": ["2838"],
        "entity": "Corporate Services",
        "person": "Dirk Neumann - Corp Services",
        "zoho_account": "Credit Card - 2838",
    },
}


# ── harness (same shape as test_feedback_notes_52_53_62_63) ──────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, day, payment_hint=None, **kw) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency=kw.pop("currency", "USD"), vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint, **kw,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("1.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    return mock


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, n_files: int, label="August 2026", entity="") -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": entity, "label": label}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    files = []
    for _ in range(n_files):
        _SEQ[0] += 1
        files.append(("files", (
            f"L{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 7]),
            "application/octet-stream",
        )))
    if files:
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts", files=files
        ))
    return batch_id


def _expense(client, batch_id, vendor) -> dict:
    rows = client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    hit = [e for e in rows if e["vendor"]["display"] == vendor]
    assert len(hit) == 1, [e["vendor"] for e in rows]
    return hit[0]


def _overrides(client, batch_id) -> dict:
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        return store.get_category_overrides(batch_id)
    finally:
        store.close()


def _learned(client) -> dict:
    return client.get("/api/memory").json()


def _learned_company(client, vendor="uber") -> dict:
    """The one learned (entity, vendor) row the memory page shows.

    `by_vendor[].category` is the REGISTRY's default; the learned row lives
    under `companies[]`, and the view renders a NULL category / account as
    `""` (service.py:5303), so that is what "nothing learned" looks like."""
    rows = [r for r in _learned(client)["by_vendor"] if r["vendor"] == vendor]
    assert len(rows) == 1, _learned(client)["by_vendor"]
    (company,) = rows[0]["companies"]
    return company


def _uber_month(client, monkeypatch):
    """A month holding one Uber receipt whose category is a VENDOR guess --
    the live shape of note #62 (it was OpenAI 80.04) and the one state the
    Confirm is offered on."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Uber", "22.30", "2026-08-20", "Visa ...2838"))
    batch = _month(client, 1)
    row = _expense(client, batch, "Uber")
    assert row["posting_category"]["category"] == "Travel & Transport"
    assert row["review"]["reason_code"] == "vendor_guess"
    assert row["category_confirmable"] is True
    return batch, row["document_id"]


# ── leak 1: confirming a guess is not stating a category ────────────


def test_confirm_marks_the_category_inherited_not_hers(client, monkeypatch):
    batch, doc = _uber_month(client, monkeypatch)

    assert client.post(
        f"/api/runs/{batch}/expenses/{doc}/confirm-category"
    ).status_code == 200

    # The row still reads ready -- the point of the Confirm is unchanged.
    row = _expense(client, batch, "Uber")
    assert row["review"]["state"] == "ready"
    assert row["category_confirmable"] is False

    # ...but the stored line says the category is the MODEL's.
    ov = _overrides(client, batch)[(doc, 0)]
    assert ov["category"] == "Travel & Transport"
    assert ov["category_source"] == CATEGORY_SOURCE_INHERITED
    assert category_is_human(ov) is False


def test_confirmed_guess_teaches_no_category(client, monkeypatch):
    batch, doc = _uber_month(client, monkeypatch)
    assert client.post(
        f"/api/runs/{batch}/expenses/{doc}/confirm-category"
    ).status_code == 200

    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert resp.json()["learned"]["merchant_categories"] == 0
    assert _learned(client)["by_vendor"] == []


def test_an_explicit_pick_still_teaches(client, monkeypatch):
    """The negative case. The fix must not make sign-off stop learning: a
    category she NAMED is still memorized, exactly as before."""
    batch, doc = _uber_month(client, monkeypatch)
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "category", "value": "Office Supplies & Consumables"},
    ).status_code == 200

    ov = _overrides(client, batch)[(doc, 0)]
    assert ov["category_source"] == CATEGORY_SOURCE_HUMAN

    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.json()["learned"]["merchant_categories"] == 1
    assert _learned_company(client)["category"] == "Office Supplies & Consumables"


# ── leak 2: fixing the account says nothing about the category ──────


def test_account_only_fix_teaches_the_account_and_not_the_category(
    client, monkeypatch
):
    batch, doc = _uber_month(client, monkeypatch)

    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "zoho_account", "value": "Travel Expense: Airfare"},
    ).status_code == 200

    ov = _overrides(client, batch)[(doc, 0)]
    # The category rode along so `apply_overrides` fires at all...
    assert ov["category"] == "Travel & Transport"
    assert ov["zoho_account"] == "Travel Expense: Airfare"
    # ...and is marked as the model's, not hers.
    assert ov["category_source"] == CATEGORY_SOURCE_INHERITED

    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    learned = _learned_company(client)
    # Her correction WAS the account, and the direct-to-GL chain needs it.
    assert learned["zoho_account"] == "Travel Expense: Airfare"
    # The model's category is not her word and must not be stored as one.
    assert learned["category"] == ""


def test_account_fix_after_her_own_category_keeps_her_category(
    client, monkeypatch
):
    """A category she picked earlier is HERS, and a later account-only fix
    must not downgrade it to the model's."""
    batch, doc = _uber_month(client, monkeypatch)
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "category", "value": "Office Supplies & Consumables"},
    ).status_code == 200
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "zoho_account", "value": "Office Infra and Admin"},
    ).status_code == 200

    ov = _overrides(client, batch)[(doc, 0)]
    assert ov["category_source"] == CATEGORY_SOURCE_HUMAN

    client.post(f"/api/runs/{batch}/commit-memory")
    learned = _learned_company(client)
    assert learned["category"] == "Office Supplies & Consumables"
    assert learned["zoho_account"] == "Office Infra and Admin"


def test_confirm_does_not_downgrade_a_category_she_picked(client, monkeypatch):
    """The confirm route rewrites every line; a line already carrying her
    pick keeps its own provenance."""
    batch, doc = _uber_month(client, monkeypatch)
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "category", "value": "Office Supplies & Consumables"},
    ).status_code == 200
    # The row is no longer a guess, so the Confirm is refused outright --
    # which is itself the guarantee: it cannot reach her line to downgrade.
    assert client.post(
        f"/api/runs/{batch}/expenses/{doc}/confirm-category"
    ).status_code == 400
    assert _overrides(client, batch)[(doc, 0)]["category_source"] == (
        CATEGORY_SOURCE_HUMAN
    )


# ── the store + collapse, at the unit the routes drive ──────────────


def _receipt(doc="r1", vendor="Staples", entity="Corporate Services") -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=None,
        detected_total=Decimal("42.50"), detected_currency="USD",
        detected_vendor=vendor,
    )


def test_keep_category_preserves_a_stored_category(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(
            "Corporate Services", "staples", "Office Supplies & Consumables",
            "Office Infra and Admin", "t0", "run1",
        )
        s.record_merchant_category(
            "Corporate Services", "staples", "Travel & Transport",
            "Travel Expense: Airfare", "t1", "run2", keep_category=True,
        )
        row = s.get_merchant_category("Corporate Services", "staples")
    # The category she stated survives; the account moves.
    assert row.category == "Office Supplies & Consumables"
    assert row.zoho_account == "Travel Expense: Airfare"


def test_keep_category_inserts_an_account_only_row(tmp_path):
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(
            "Corporate Services", "staples", "Travel & Transport",
            "Travel Expense: Airfare", "t0", "run1", keep_category=True,
        )
        row = s.get_merchant_category("Corporate Services", "staples")
    assert row.category is None
    assert row.zoho_account == "Travel Expense: Airfare"


def test_inherited_category_gets_no_vote_in_the_conflict_test(tmp_path):
    """A machine guess disagreeing with a human statement is not a
    disagreement, so the vendor must still be taught -- HER value."""
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        n_cat, n_skipped = _learn_categories(
            s,
            {"r1": _receipt("r1"), "r2": _receipt("r2")},
            {
                ("r1", 0): {
                    "category": "Office Supplies & Consumables",
                    "zoho_account": None,
                    "category_source": CATEGORY_SOURCE_HUMAN,
                },
                ("r2", 0): {
                    "category": "Travel & Transport",
                    "zoho_account": None,
                    "category_source": CATEGORY_SOURCE_INHERITED,
                },
            },
            "run1", "t0",
        )
        row = s.get_merchant_category("Corporate Services", normalize_vendor("Staples"))
    assert (n_cat, n_skipped) == (1, 0)
    assert row.category == "Office Supplies & Consumables"


def test_two_human_categories_still_conflict(tmp_path):
    """The item-183 skip is untouched by the provenance change."""
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        n_cat, n_skipped = _learn_categories(
            s,
            {"r1": _receipt("r1"), "r2": _receipt("r2")},
            {
                ("r1", 0): {
                    "category": "Office Supplies & Consumables",
                    "zoho_account": None,
                    "category_source": CATEGORY_SOURCE_HUMAN,
                },
                ("r2", 0): {
                    "category": "Travel & Transport",
                    "zoho_account": None,
                    "category_source": CATEGORY_SOURCE_HUMAN,
                },
            },
            "run1", "t0",
        )
        row = s.get_merchant_category("Corporate Services", normalize_vendor("Staples"))
    assert (n_cat, n_skipped) == (0, 1)
    assert row is None


def test_absent_provenance_reads_as_hers(tmp_path):
    """Back-compat: every override row written before the column existed is
    overwhelmingly an explicit pick, and reading NULL as the model's would
    stop every already-reviewed month teaching what it legitimately taught."""
    assert category_is_human({"category": "Travel & Transport"}) is True
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        n_cat, _ = _learn_categories(
            s, {"r1": _receipt("r1")},
            {("r1", 0): {"category": "Travel & Transport", "zoho_account": None}},
            "run1", "t0",
        )
    assert n_cat == 1


def test_store_refuses_an_unknown_provenance(tmp_path):
    store = RunStore(tmp_path / "recon-web.sqlite")
    try:
        with pytest.raises(ValueError, match="invalid category_source"):
            store.set_category_override(
                "r", "d", 0, "Travel & Transport", None, "t0",
                category_source="maybe",
            )
    finally:
        store.close()


# ── leak 3: the tool's own confirmations are not reviewed ────────────


def _decision(status="confirmed", decided_by=None, chosen="r1") -> Decision:
    return Decision(
        status=status, chosen_document_id=chosen, updated_at="t0",
        decided_by=decided_by,
    )


def test_reviewer_confirmed_excludes_the_tools_own_verdicts():
    decisions = {
        "t-person": _decision(decided_by="reviewer"),
        "t-tool": _decision(decided_by="tool"),
        "t-legacy": _decision(decided_by=None),      # predates the column
        "t-pending": _decision(status="pending", decided_by="reviewer"),
    }
    # A legacy NULL row was written by a person; a pending one is no verdict.
    assert reviewer_confirmed_tx_ids(decisions) == {"t-person", "t-legacy"}
    assert reviewer_confirmed_tx_ids(None) == set()


def _pair():
    tx = Transaction(
        transaction_id="t1", legal_entity_id="Corporate Services",
        account_id="card-2838", transaction_date=date(2026, 8, 20),
        posting_date=None, amount=Decimal("22.30"),
        transaction_currency="USD", account_card_currency="USD",
        vendor_from_statement="UBER TRIP 8NKQ2",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="Corporate Services",
        detected_date=None, detected_total=Decimal("22.30"),
        detected_currency="USD", detected_vendor="Uber Technologies",
    )
    return tx, rec


def test_a_tool_confirmed_pair_teaches_no_alias(tmp_path):
    from expense_recon.learning import learn_confirmed_pairs
    from expense_recon.matching.types import Match

    tx, rec = _pair()
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t1", document_id="r1",
            match_type=MatchType.EXACT, confidence=1.0, reason="amount+date",
        )],
    )
    decisions = {"t1": _decision(decided_by="tool")}
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        pairs, alias, fx = learn_confirmed_pairs(
            s, transactions=[tx], receipts=[rec], outcome=outcome,
            confirmed_tx_ids=reviewer_confirmed_tx_ids(decisions),
            source_run="run1", now_iso="t0",
        )
        assert (pairs, alias, fx) == (0, 0, 0)
        assert s.get_vendor_aliases() == []

    # The negative case: the same pair, confirmed by a PERSON, still teaches.
    db2 = tmp_path / "learning2.sqlite"
    with LearningStore(db2) as s:
        pairs, alias, fx = learn_confirmed_pairs(
            s, transactions=[tx], receipts=[rec], outcome=outcome,
            confirmed_tx_ids=reviewer_confirmed_tx_ids(
                {"t1": _decision(decided_by="reviewer")}
            ),
            source_run="run1", now_iso="t0",
        )
        assert (pairs, alias) == (1, 1)
        assert len(s.get_vendor_aliases()) == 1


# ── provenance travels: undo and a cross-month move ─────────────────


def test_undo_restores_the_provenance_not_just_the_value(client, monkeypatch):
    """An undo puts back the value the row held; promoting the model's
    category to hers on the way back would re-open leak 2 through the
    ledger."""
    batch, doc = _uber_month(client, monkeypatch)
    # Account-only fix -> the row now carries the model's category.
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "zoho_account", "value": "Travel Expense: Airfare"},
    ).status_code == 200
    # Then a real pick, which is what we undo.
    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "category", "value": "Office Supplies & Consumables"},
    ).status_code == 200
    assert _overrides(client, batch)[(doc, 0)]["category_source"] == (
        CATEGORY_SOURCE_HUMAN
    )

    history = client.get(f"/api/runs/{batch}/history").json()["entries"]
    entry = next(
        e for e in history
        if e.get("field") == "receipt_category" and e.get("undoable")
    )
    resp = client.post(f"/api/runs/{batch}/history/{entry['id']}/undo")
    assert resp.status_code == 200, resp.text

    ov = _overrides(client, batch)[(doc, 0)]
    assert ov["category"] == "Travel & Transport"
    assert ov["category_source"] == CATEGORY_SOURCE_INHERITED

    # ...so sign-off after the undo teaches the account only.
    client.post(f"/api/runs/{batch}/commit-memory")
    assert _learned_company(client)["category"] == ""


def test_a_month_with_no_edits_still_teaches_nothing(client, monkeypatch):
    """Guard against the fix inverting: an untouched month must not start
    writing account-only rows for every vendor the model guessed."""
    batch, _doc = _uber_month(client, monkeypatch)
    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert resp.json()["learned"]["merchant_categories"] == 0
    assert _learned(client)["by_vendor"] == []


def test_capture_summary_shape_is_unchanged(tmp_path):
    """The SPA reads these keys; the fix must not rename or drop one."""
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        summary = learn_from_expense_run(
            s, receipts=[_receipt()], effective_receipts=[_receipt()],
            field_overrides={}, category_overrides={},
            source_run="run1", now_iso="t0",
        )
    assert set(summary.as_dict()) == {
        "merchant_categories", "skipped_mixed_category",
        "merchant_entities", "field_corrections",
    }


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
