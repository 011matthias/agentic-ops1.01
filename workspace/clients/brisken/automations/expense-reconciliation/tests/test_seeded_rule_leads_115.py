"""Item 115, owner ruling 2026-09-27: a rule seeded from Zoho Books may decide
a receipt with readable lines on a GL month, and the second read of those
lines flags where they disagree.

Until the ruling a seeded rule (how the books posted, nobody validated it)
filled only a receipt with no readable items; one with lines went to the model
and the rule was never consulted. The owner accepted the consequence: about 41
unsure receipts take a rule's answer at their next categorization. Nothing is
re-run live.

Route-level through the real app: a rule saved on the Memory route, restamped
as seeded the way `memory seed-zoho` writes it, then a receipt with a readable
line uploaded into a GL month.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.categorize import DECISION_LEARNED_OVER_LINE  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-115"
CORP = "Corporate Services"
CORP_ORG = "822741658"
VENDOR = "Contoso Hardware"


def _leaves(org: str) -> list[str]:
    return [c for c in sorted(curated_leaves.postable_codes(org))
            if not curated_leaves.has_postable_children(org, c)]


RULE_CODE, READ_CODE = _leaves(CORP_ORG)[:2]


def _label(code: str) -> str:
    return next(lbl for lbl in curated_leaves.llm_leaf_labels(CORP_ORG)
                if lbl.startswith(code + " "))


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
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _seed(web, *, seeded=True):
    resp = web.put("/api/memory/categories", json={
        "legal_entity_id": CORP, "vendor": VENDOR, "category": RULE_CODE,
    })
    assert resp.status_code == 200, resp.text
    if not seeded:
        return
    conn = sqlite3.connect(str(Path(web._data_root) / "learning.sqlite"))
    with conn:
        n = conn.execute(
            "UPDATE merchant_category SET source_run = 'zoho-seed:822741658' "
            "WHERE legal_entity_id = ? AND vendor_norm = ?",
            (CORP, "contoso hardware"),
        ).rowcount
    conn.close()
    assert n == 1, "the rule the route saved was not found to restamp"


def _upload(web, monkeypatch, read_code: str) -> dict:
    """A GL month with one receipt whose one line the model reads as
    `read_code`; returns the stored line's categorization."""
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-07-02", total="120.00", currency="USD", vendor=VENDOR,
            reference="C-115", line_items=(ExtractedLineItem(
                description="Ergonomic office chair", line_total="120.00"),),
            confidence=0.9, notes="")],
        responses=[ClassificationResult(_label(read_code), None, 0.9, "mock")],
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    resp = web.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("chair.jpg", JPG, "application/octet-stream"))])
    assert resp.status_code == 200, resp.text
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    (expense,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        snap = json.loads(conn.execute(
            "SELECT snapshot FROM runs WHERE run_id = ?", (batch_id,)
        ).fetchone()["snapshot"])
    finally:
        conn.close()
    (rec,) = [r for r in snap["receipts"]
              if r["document_id"] == expense["document_id"]]
    return {"line": rec["line_items"][0]["categorization"], "row": expense}


def test_the_rule_is_really_seeded_and_the_read_really_differs(web, monkeypatch):
    """The premise: two different postable leaves, and the seeded rule is not
    a person's (so before the ruling it could not lead on a lined receipt)."""
    assert RULE_CODE != READ_CODE
    _seed(web)
    rules = web.get("/api/memory").json()["categories"]
    assert [r["category"] for r in rules] == [RULE_CODE], rules


def test_a_seeded_rule_decides_a_lined_receipt_and_flags_the_read(web, monkeypatch):
    _seed(web)
    got = _upload(web, monkeypatch, READ_CODE)
    line = got["line"]
    assert line["category"] == RULE_CODE, line
    assert line["source"] == "LEARNED", line
    assert line["decision"] == DECISION_LEARNED_OVER_LINE, line
    assert READ_CODE in line["reasoning"], line
    posting = got["row"]["posting_category"]
    assert posting["category"] == RULE_CODE, posting
    assert posting["origin"] == "rule", posting


def test_a_seeded_rule_the_read_agrees_with_is_not_flagged(web, monkeypatch):
    _seed(web)
    line = _upload(web, monkeypatch, RULE_CODE)["line"]
    assert line["category"] == RULE_CODE, line
    assert line["source"] == "LEARNED", line
    assert not line.get("decision"), line


def test_a_person_taught_rule_still_leads_as_before(web, monkeypatch):
    _seed(web, seeded=False)
    line = _upload(web, monkeypatch, READ_CODE)["line"]
    assert line["category"] == RULE_CODE, line
    assert line["source"] == "LEARNED", line
