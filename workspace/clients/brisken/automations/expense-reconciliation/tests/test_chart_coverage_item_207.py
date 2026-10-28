"""Item 207: `/healthz` names the postable accounts the export check's chart
file lacks.

The export gate checks every account against the chart file on the server's
disk. On 2026-09-25 that file was the 1 July pull, 18 of Dirk's 64 postable
Cloud Services accounts newer than it, and each one the engine picked was
blanked to "(account unmapped - assign)" with nothing saying why. The
`coa_chart` block says why: per curated company, which postable codes the
file does not hold, and `ok: false` while any are missing.

Every assertion runs through `GET /healthz`, against provisioning and chart
files written the way the server holds them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
SENDGRID_CODE = "E700030-30"


def _accounts(org: str, *, drop: frozenset[str] = frozenset()) -> list[dict]:
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b and code not in drop
    ]


def _write_chart(path: Path, *, drop_cloud: frozenset[str] = frozenset()) -> None:
    path.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": _accounts(CORP_ORG)},
        CLOUD_ORG: {"org": {"name": CLOUD},
                    "accounts": _accounts(CLOUD_ORG, drop=drop_cloud)},
    }), encoding="utf-8")


@pytest.fixture
def chart(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "zoho-books-coa.json"
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(path),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    return path


def _coa_chart(tmp_path) -> dict | None:
    with TestClient(create_app(tmp_path)) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    return body["coa_chart"]


def _by_company(block: dict) -> dict[str, dict]:
    return {c["company"]: c for c in block["companies"]}


def test_a_complete_chart_reads_ok(tmp_path, chart):
    _write_chart(chart)

    block = _coa_chart(tmp_path)

    assert block["ok"] is True
    assert block["chart_path"] == str(chart)
    assert block["chart_bytes"] == chart.stat().st_size
    companies = _by_company(block)
    assert companies[CLOUD]["missing"] == [] and companies[CORP]["missing"] == []
    assert companies[CLOUD]["n_postable"] == len(curated_leaves.postable_codes(CLOUD_ORG))


def test_a_chart_missing_a_postable_account_names_it(tmp_path, chart):
    """The live shape of 2026-09-25: the file predates SendGrid's account."""
    assert curated_leaves.is_postable(CLOUD_ORG, SENDGRID_CODE), "fixture"
    _write_chart(chart, drop_cloud=frozenset({SENDGRID_CODE}))

    block = _coa_chart(tmp_path)

    assert block["ok"] is False
    companies = _by_company(block)
    assert companies[CLOUD]["missing"] == [SENDGRID_CODE]
    assert companies[CORP]["missing"] == []


def test_replacing_the_file_is_read_on_the_next_probe(tmp_path, chart):
    """The fix is a file swap with no deploy, so the probe must not serve a
    cached answer for a file that changed."""
    _write_chart(chart, drop_cloud=frozenset({SENDGRID_CODE}))
    assert _coa_chart(tmp_path)["ok"] is False

    _write_chart(chart)
    later = chart.stat().st_mtime + 5
    os.utime(chart, (later, later))

    assert _coa_chart(tmp_path)["ok"] is True


def test_an_unreadable_chart_reports_and_never_fails_the_probe(tmp_path, chart):
    block = _coa_chart(tmp_path)  # the fixture wrote no chart file

    assert block["chart_path"] == str(chart)
    assert "error" in block


def test_nothing_provisioned_reads_null(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)

    assert _coa_chart(tmp_path) is None
