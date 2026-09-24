"""Item 4b: on a GL batch the export's chart gate judges postable by Dirk's
marking, the same one the engine picks leaves from and the API poster checks.

Before, the gate applied the chart's parent rule plus the provisioned
`scope_groups` to every batch. Against the live provisioning that diverted 56
of Dirk's 194 Y accounts on a GL batch (the 35 roll-ups he marked postable,
and `COGS - DEV Infrastructure` among the rest) and passed 105 he marked N:
the engine would categorize a receipt into a leaf the export then blanked.

Everything here goes through `cli._build_coa_gate`, the builder the hosted
grid and export both call, and through `gated_for_posting` /
`build_expense_row_groups`, what the CSV is written from. A bucket batch (no
`gl_entity_orgs`) must keep today's verdicts byte for byte; that is pinned
against a gate built the pre-4b way.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from expense_recon.cli import _build_coa_gate
from expense_recon.coa_gate import CoaGate, CoaVerdict, classify_account
from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)
from expense_recon.output.posting_common import _UNMAPPED
from expense_recon.output.zoho_expense_export import (
    EXPENSE_COLUMNS,
    build_expense_row_groups,
    gated_for_posting,
)
from expense_recon.zoho import curated_leaves
from expense_recon.zoho._curated_leaves_data import LEAVES
from expense_recon.zoho.accounts import ResolvedAccount, resolve_account_id

CLOUD = "697686691"
LABEL = "Cloud Services"
IT_PARENT = "IT: Computer and Internet Expenses"
COGS_PARENT = "COGS - RECURRING BUSINESS"


def _acct(account_id, name, code, parent=None):
    return {
        "account_id": account_id, "account_name": name, "account_code": code,
        "account_type": "expense", "is_active": True,
        "parent_account_name": parent,
    }


# Cloud Services' own ids, codes and names, and the parent chain its chart
# carries, so the chart rule has the roll-ups and roots it has live.
CHART = [
    _acct("2031056000000104391", IT_PARENT, "E500010", "MS | OpeEx"),
    _acct("2031056000000106807", "IT: Cloud Subscriptions-Others", "E500010-30", IT_PARENT),
    _acct("2031056000000034003", COGS_PARENT, "E700030"),
    _acct("2031056000014161139", "COGS - DEV Infrastructure (SAP Apps & others)",
          "E700030-19", COGS_PARENT),
    _acct("2031056000000403080", "Payroll Taxes: Medicare", "E300000-10"),
    _acct("2031056000099999999", "Unlisted Expense", "E999990"),
]
SCOPE = ["MS | OpeEx", "Payroll Taxes: Medicare"]

# document id -> the account its one line is categorized to.
LINES = {
    "parent": IT_PARENT,  # Y, and a roll-up in the chart
    "child": "IT: Cloud Subscriptions-Others",  # Y leaf, in scope
    "cogs": "COGS - DEV Infrastructure (SAP Apps & others)",  # Y, out of scope
    "medicare": "Payroll Taxes: Medicare",  # N, in scope
    "unlisted": "Unlisted Expense",  # not on the list at all
}

BUCKET_VERDICTS = {
    "parent": CoaVerdict.NON_LEAF,
    "child": CoaVerdict.OK,
    "cogs": CoaVerdict.OUT_OF_SCOPE,
    "medicare": CoaVerdict.OK,
    "unlisted": CoaVerdict.OUT_OF_SCOPE,
}
GL_VERDICTS = {
    "parent": CoaVerdict.OK,
    "child": CoaVerdict.OK,
    "cogs": CoaVerdict.OK,
    "medicare": CoaVerdict.NOT_EXPENSE_RELEVANT,
    "unlisted": CoaVerdict.OUTSIDE_CURATED_LIST,
}


def _receipts():
    out = []
    for doc, account in LINES.items():
        cat = Categorization(
            category=curated_leaves.code_of(account, CLOUD) or "Software & Subscriptions",
            zoho_account=account, confidence=0.9,
            source=ClassificationSource.LINE, reasoning="read",
        )
        out.append(Receipt(
            document_id=doc, legal_entity_id=LABEL, detected_date=None,
            detected_total=Decimal("10.00"), detected_currency="USD",
            detected_vendor="Vendor " + doc,
            line_items=(LineItem(description=doc, line_total=Decimal("10.00"),
                                 categorization=cat),),
        ))
    return out


def _cfg(tmp_path, *, gl, form="entities"):
    path = tmp_path / "coa.json"
    path.write_text(json.dumps({CLOUD: {"org": {}, "accounts": CHART}}), encoding="utf-8")
    entry = {"chart_path": str(path), "org_id": CLOUD, "entity_label": LABEL,
             "scope_groups": SCOPE}
    block = ({"enabled": True, "entities": [entry]} if form == "entities"
             else {"enabled": True, **entry})
    cfg = {"coa_validation": block}
    if gl:
        cfg["gl_entity_orgs"] = {LABEL: CLOUD}
    return cfg


def _verdicts(gate, receipts):
    return {v.document_id: v.verdict for v in gate.validate(receipts).verdicts}


def _account_cells(gate, receipts):
    col = EXPENSE_COLUMNS.index("Expense Account")
    return {doc: [row[col] for row in rows]
            for doc, rows in build_expense_row_groups(receipts, coa_gate=gate)}


# ── GL batch: Dirk's marking decides ────────────────────────────────


@pytest.mark.parametrize("form", ["entities", "single"])
def test_a_gl_batch_is_judged_by_the_curated_marking(tmp_path, form):
    gate = _build_coa_gate(_cfg(tmp_path, gl=True, form=form), tmp_path)
    assert _verdicts(gate, _receipts()) == GL_VERDICTS


def test_the_gl_export_keeps_the_accounts_dirk_approved(tmp_path):
    """Through the CSV fan-out: the roll-up and the COGS leaf he marked Y
    post under their own names; the N account and the off-list one are
    blanked to the assign marker."""
    gate = _build_coa_gate(_cfg(tmp_path, gl=True), tmp_path)
    cells = _account_cells(gate, _receipts())
    assert cells["parent"] == [IT_PARENT]
    assert cells["cogs"] == ["COGS - DEV Infrastructure (SAP Apps & others)"]
    assert cells["medicare"] == [_UNMAPPED]
    assert cells["unlisted"] == [_UNMAPPED]


def test_a_diverted_gl_line_names_dirks_reason(tmp_path):
    gate = _build_coa_gate(_cfg(tmp_path, gl=True), tmp_path)
    gated = {r.document_id: r for r in gated_for_posting(_receipts(), gate)}
    note = gated["medicare"].line_items[0].categorization.reasoning
    assert "NOT_EXPENSE_RELEVANT" in note
    assert "not expense relevant for this company" in note


def test_the_hosted_injector_yields_a_curated_gate(tmp_path):
    """The real chain a hosted batch takes: `apply_to_config` injects both
    `gl_entity_orgs` and the per-entity gate block, and the gate built from
    that config judges by the marking."""
    from expense_recon.coa_provision import apply_to_config

    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({CLOUD: {"org": {}, "accounts": CHART}}), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({"chart_path": str(chart), "entities": {
        LABEL: {"org_id": CLOUD, "scope_groups": SCOPE}}}), encoding="utf-8")
    cfg = apply_to_config({"receipts": {}}, "", path=str(prov))
    gate = _build_coa_gate(cfg, tmp_path)
    assert gate.gates[LABEL].curated_org == CLOUD
    assert _verdicts(gate, _receipts()) == GL_VERDICTS


# ── bucket batch: unchanged, byte for byte ──────────────────────────


@pytest.mark.parametrize("form", ["entities", "single"])
def test_a_bucket_batch_keeps_the_chart_rule_byte_for_byte(tmp_path, form):
    """No `gl_entity_orgs`: the verdicts are the chart rule's, and the gated
    receipts equal what a gate built the pre-4b way produces, every field."""
    receipts = _receipts()
    gate = _build_coa_gate(_cfg(tmp_path, gl=False, form=form), tmp_path)
    assert _verdicts(gate, receipts) == BUCKET_VERDICTS

    chart = ChartOfAccounts.from_api(CHART)
    pre_4b = CoaGate(chart=chart, scope_groups=tuple(SCOPE), entity=LABEL)
    assert gated_for_posting(receipts, gate) == gated_for_posting(receipts, pre_4b)
    cells = _account_cells(gate, receipts)
    assert cells["parent"] == [_UNMAPPED]
    assert cells["medicare"] == ["Payroll Taxes: Medicare"]


def test_a_gl_batch_on_an_org_nobody_curated_keeps_the_chart_rule(tmp_path):
    cfg = _cfg(tmp_path, gl=True, form="single")
    (tmp_path / "coa.json").write_text(
        json.dumps({"822116290": {"org": {}, "accounts": CHART}}), encoding="utf-8")
    cfg["coa_validation"]["org_id"] = "822116290"
    gate = _build_coa_gate(cfg, tmp_path)
    assert gate.curated_org is None
    assert _verdicts(gate, _receipts()) == BUCKET_VERDICTS


# ── the gate and the API poster agree ───────────────────────────────


def _curated_chart(org_id):
    return ChartOfAccounts.from_api([
        _acct(b[org_id][0], b[org_id][1], code)
        for code, (_branch, b) in LEAVES.items() if org_id in b
    ])


@pytest.mark.parametrize("org_id", curated_leaves.curated_orgs())
def test_the_gl_gate_passes_exactly_what_the_poster_accepts(org_id):
    """Every account on Dirk's sheet for each curated org: the export gate
    passes it iff `resolve_account_id` resolves it for that org."""
    chart = _curated_chart(org_id)
    disagree = []
    for account in chart.accounts:
        verdict, _ = classify_account(account.name, chart, curated_org=org_id)
        posts = isinstance(
            resolve_account_id(account.name, chart, org_id=org_id), ResolvedAccount)
        if (verdict is CoaVerdict.OK) != posts:
            disagree.append((account.code, verdict.value, posts))
    assert disagree == []
    assert sum(1 for a in chart.accounts
               if classify_account(a.name, chart, curated_org=org_id)[0] is CoaVerdict.OK
               ) == len(curated_leaves.postable_codes(org_id))


def test_a_chart_loaded_for_another_org_diverts_on_a_gl_batch():
    """E100010-31 is on the sheet in Cloud Services and Corporate Services
    under different ids. Cloud's chart judged as Corporate's must not pass."""
    chart = ChartOfAccounts.from_api(
        [_acct("2031056000000104265", "Travel Expense | Food", "E100010-31")])
    verdict, _ = classify_account("Travel Expense | Food", chart, curated_org="822741658")
    assert verdict is CoaVerdict.CHART_ORG_MISMATCH
