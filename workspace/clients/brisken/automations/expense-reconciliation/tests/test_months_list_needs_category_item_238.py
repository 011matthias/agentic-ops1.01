"""Item 238: the months list counts "needs a category" the way the month does.

Found 2026-09-27 while checking item 236 live: on the three months moved to
the GL accounts, each month's cards added up to 4 more rows needing a
category than the months list showed (September 38 on its page, 34 on the
list). The list counted `apply_overrides` over its own pool; the page reads
each row through the grid's card chain and the live merchant read, which
turns a model suggestion stored before today's refusals (a summary account
with postable accounts under it, another vendor's product account) into a
refusal. So the page asked for a category and the list counted an answer.

Now both read `grid_posting`. The list is kept in memory under the data
folder's key, so the second half of this file pins that an edit still reaches
it at the next read.

Fixtures copied from test_front3_identity_live, never imported (a shared
fixture import is an F811 in CI).
"""
from __future__ import annotations

import json

import pytest

from expense_recon.zoho import curated_leaves

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

CORP = "Corporate Services"
CORP_ORG = "822741658"
CODE = "criss-code-item238"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
ZOHO_ERP = "E500010-10"
PARENT = "E500010"


def _leaves(org: str) -> list[str]:
    return sorted(
        c for c in curated_leaves.postable_codes(org)
        if not curated_leaves.has_postable_children(org, c)
    )


LEAF = _leaves(CORP_ORG)[0]


def _label(code: str) -> str:
    return f"{code} {curated_leaves.binding(code, CORP_ORG).name}"


def _chart_accounts(org: str) -> list[dict]:
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b
    ]


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODES", f"{CODE}:criss")
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": _chart_accounts(CORP_ORG)},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    with TestClient(create_app(tmp_path)) as c:
        login = c.post("/api/login", json={"code": CODE})
        assert login.status_code == 200, login.text
        c.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _one_receipt(web, monkeypatch, vendor: str, answer: str) -> str:
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor=vendor,
            reference="", confidence=0.9, notes="",
            line_items=(ExtractedLineItem("Workspace seat, August", "40.00"),))],
        responses=[ClassificationResult(_label(answer), None, 0.9, "mock")],
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    _done(web, web.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("r.jpg", JPG, "application/octet-stream"))]))
    return batch


def _stale_month(web, monkeypatch, vendor: str, answer: str) -> str:
    """A suggestion stored before the guards existed (both switched off for
    the ingest only), the live shape of the rows that parted the counts."""
    with monkeypatch.context() as m:
        m.setattr("expense_recon.categorize.vendor_may_post", lambda *a: True)
        m.setattr("expense_recon.categorize.curated_leaves.has_postable_children",
                  lambda *a: False)
        return _one_receipt(web, monkeypatch, vendor, answer)


def _pairs(web, batch: str) -> tuple[tuple, tuple]:
    """(the months list's pair, the month page's pair), each
    (n_categorized, n_uncategorized)."""
    listed = next(
        b["summary"] for b in web.get("/api/expense-batches").json()["batches"]
        if b["batch_id"] == batch
    )
    page = web.get(f"/api/expense-batches/{batch}").json()
    assert page["category_vocabulary"] == "gl", "precondition: a GL month"
    s = page["summary"]
    return (
        (listed["n_categorized"], listed["n_uncategorized"]),
        (s["n_categorized"], s["n_uncategorized"]),
    )


@pytest.mark.parametrize("answer, vendor", [
    (PARENT, "Acme Cloud"),
    (ZOHO_ERP, "Acme Cloud"),
])
def test_a_stale_suggestion_needs_a_category_on_the_list_too(
    web, monkeypatch, answer, vendor,
):
    batch = _stale_month(web, monkeypatch, vendor, answer)
    listed, page = _pairs(web, batch)
    assert page == (0, 1), "the page refuses the stored suggestion"
    assert listed == page


def test_an_answer_that_stands_counts_as_categorized_on_both(web, monkeypatch):
    """Differential: a leaf the model may give stays an answer on both, so
    the list is not simply counting everything as needing a category."""
    batch = _one_receipt(web, monkeypatch, "Acme Cloud", LEAF)
    listed, page = _pairs(web, batch)
    assert page == (1, 0)
    assert listed == page


def test_an_edit_reaches_the_kept_list_at_the_next_read(web, monkeypatch):
    """The list body is kept between reads; a person's pick must still move
    it on the very next read, not after some refresh."""
    batch = _stale_month(web, monkeypatch, "Acme Cloud", PARENT)
    assert _pairs(web, batch)[0] == (0, 1)
    doc = web.get(f"/api/expense-batches/{batch}").json()["expenses"][0]["document_id"]
    r = web.post(f"/api/runs/{batch}/categories",
                 json={"document_id": doc, "line_index": 0, "category": LEAF})
    assert r.status_code == 200, r.text
    listed, page = _pairs(web, batch)
    assert page == (1, 0)
    assert listed == page
