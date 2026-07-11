"""Server-side COA-gate provisioning tests.

Synthetic charts + provisioning files only (the real Books COA JSON is
sensitive client data, never in this repo). These cover the injection helper
that makes the Phase-5 gate fire on the hosted web workbench: a per-entity
`coa_validation` block is added to a web run's config from the /data
provisioning file, keyed on the run's legal entity, fail-open throughout.
"""
from __future__ import annotations

import json

from expense_recon.cli import _build_coa_gate
from expense_recon.coa_gate import CoaVerdict
from expense_recon.coa_provision import (
    PROVISION_ENV,
    apply_to_config,
    coa_validation_for,
    load_provisioning,
)
from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)

# Two-entity synthetic COA JSON in the real shape
# `{ "<org_id>": { "org": {...}, "accounts": [...] }, ... }`.
_COA_JSON = {
    "822741658": {
        "org": {"name": "Corporate Services"},
        "accounts": [
            {"account_id": "1", "account_name": "Office Supplies", "account_code": "E500",
             "account_type": "expense", "parent_account_name": "MS | OpeEx", "is_active": True},
            {"account_id": "2", "account_name": "MS | OpeEx", "account_code": "E5",
             "account_type": "expense", "parent_account_name": None, "is_active": True},
            {"account_id": "3", "account_name": "Payroll Tax", "account_code": "E300",
             "account_type": "expense", "parent_account_name": "CorpServ | OpeEx", "is_active": True},
            {"account_id": "4", "account_name": "CorpServ | OpeEx", "account_code": "E3",
             "account_type": "expense", "parent_account_name": None, "is_active": True},
        ],
    },
    "697686691": {
        "org": {"name": "Cloud Services"},
        "accounts": [
            {"account_id": "9", "account_name": "Cloud Only Travel", "account_code": "C100",
             "account_type": "expense", "parent_account_name": None, "is_active": True},
        ],
    },
}


def _provision_dict(chart_path: str) -> dict:
    return {
        "chart_path": chart_path,
        "entities": {
            "Corporate Services": {
                "org_id": "822741658",
                "scope_groups": ["MS | OpeEx", "Bank Fees and Charges"],
            },
            "Cloud Services": {
                "org_id": "697686691",
                "scope_groups": ["Travel Expense"],
            },
        },
    }


def _write_provision(tmp_path) -> str:
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps(_COA_JSON), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps(_provision_dict(str(chart))), encoding="utf-8")
    return str(prov)


# ── load_provisioning ───────────────────────────────────────────────


def test_load_provisioning_missing_file_is_none(tmp_path):
    assert load_provisioning(tmp_path / "nope.json") is None


def test_load_provisioning_malformed_is_none(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_provisioning(bad) is None


def test_load_provisioning_non_dict_is_none(tmp_path):
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_provisioning(arr) is None


# ── coa_validation_for ──────────────────────────────────────────────


def test_coa_validation_for_known_entity():
    block = coa_validation_for("Corporate Services", _provision_dict("/data/coa.json"))
    assert block is not None
    assert block["org_id"] == "822741658"
    assert block["chart_path"] == "/data/coa.json"
    assert block["entity_label"] == "Corporate Services"
    assert block["scope_groups"] == ["MS | OpeEx", "Bank Fees and Charges"]
    assert block["enabled"] is True


def test_coa_validation_for_is_case_insensitive():
    block = coa_validation_for("  corporate SERVICES ", _provision_dict("/data/c.json"))
    assert block is not None and block["org_id"] == "822741658"


def test_coa_validation_for_unknown_entity_is_none():
    assert coa_validation_for("Holding LLC", _provision_dict("/data/c.json")) is None


def test_coa_validation_for_missing_org_id_is_none():
    prov = {"chart_path": "/data/c.json", "entities": {"X": {"scope_groups": ["A"]}}}
    assert coa_validation_for("X", prov) is None


def test_coa_validation_for_missing_chart_path_is_none():
    prov = {"entities": {"Corporate Services": {"org_id": "822741658"}}}
    assert coa_validation_for("Corporate Services", prov) is None


# ── apply_to_config ─────────────────────────────────────────────────


def test_apply_injects_block_for_known_entity(tmp_path):
    prov = _write_provision(tmp_path)
    cfg = {"statement": {}, "receipts": {}}
    out = apply_to_config(cfg, "Corporate Services", path=prov)
    assert out is not cfg  # new dict, original untouched
    assert "coa_validation" not in cfg
    assert out["coa_validation"]["org_id"] == "822741658"
    assert out["coa_validation"]["scope_groups"] == ["MS | OpeEx", "Bank Fees and Charges"]


def test_apply_unknown_entity_leaves_config_unchanged(tmp_path):
    prov = _write_provision(tmp_path)
    cfg = {"statement": {}}
    out = apply_to_config(cfg, "Some Unmapped Account", path=prov)
    assert out == cfg
    assert "coa_validation" not in out


def test_apply_no_path_and_no_env_leaves_config_unchanged(monkeypatch):
    monkeypatch.delenv(PROVISION_ENV, raising=False)
    cfg = {"statement": {}}
    assert apply_to_config(cfg, "Corporate Services") == cfg


def test_apply_reads_env_var_when_no_path(tmp_path, monkeypatch):
    prov = _write_provision(tmp_path)
    monkeypatch.setenv(PROVISION_ENV, prov)
    out = apply_to_config({"receipts": {}}, "Cloud Services")
    assert out["coa_validation"]["org_id"] == "697686691"


def test_apply_does_not_overwrite_existing_block(tmp_path):
    prov = _write_provision(tmp_path)
    cfg = {"coa_validation": {"org_id": "OTHER", "chart_path": "x", "enabled": True}}
    out = apply_to_config(cfg, "Corporate Services", path=prov)
    assert out["coa_validation"]["org_id"] == "OTHER"


def test_apply_malformed_provisioning_is_fail_open(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{broken", encoding="utf-8")
    cfg = {"statement": {}}
    assert apply_to_config(cfg, "Corporate Services", path=str(bad)) == cfg


# ── end-to-end: the injected block actually wires the gate ───────────


def _receipt(zoho_account: str) -> Receipt:
    cat = Categorization(
        category="Office", zoho_account=zoho_account, confidence=0.9,
        source=ClassificationSource.LINE, reasoning="",
    )
    return Receipt(
        document_id="d1", legal_entity_id="e", detected_date=None,
        detected_total=None, detected_currency="USD", detected_vendor="V",
        line_items=(LineItem(description="x", line_total=None, categorization=cat),),
    )


def test_injected_block_builds_a_gate_that_diverts_bad_accounts(tmp_path):
    """The full chain: provisioning file -> injected coa_validation block ->
    `_build_coa_gate` -> a gate that passes the in-scope leaf and diverts a
    DO-NOT-USE / wrong-entity / out-of-scope account before export."""
    prov = _write_provision(tmp_path)
    cfg = apply_to_config({"receipts": {}}, "Corporate Services", path=prov)
    gate = _build_coa_gate(cfg, tmp_path)  # chart_path is absolute -> tmp_path ignored
    assert gate is not None

    # In-scope active leaf -> OK (posts); out-of-scope payroll leaf -> diverted.
    report = gate.validate([_receipt("E500 Office Supplies"), _receipt("E300 Payroll Tax")])
    by_acct = {v.zoho_account: v.verdict for v in report.verdicts}
    assert by_acct["E500 Office Supplies"] is CoaVerdict.OK
    assert by_acct["E300 Payroll Tax"] is CoaVerdict.OUT_OF_SCOPE

    # Wrong-entity account (exists only in Cloud Services) -> UNKNOWN, diverted.
    wrong = gate.validate([_receipt("C100 Cloud Only Travel")])
    assert wrong.verdicts[0].verdict is CoaVerdict.UNKNOWN
    gated, _ = gate.run([_receipt("C100 Cloud Only Travel")])
    assert gated[0].line_items[0].categorization.zoho_account is None
    assert gated[0].line_items[0].categorization.source is ClassificationSource.REVIEW
