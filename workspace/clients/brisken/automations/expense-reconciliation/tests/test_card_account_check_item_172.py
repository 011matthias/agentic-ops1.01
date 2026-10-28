"""Item 172: each card's paid-through account, checked against its chart.

Card 3645's `zoho_account` held another CARD's label ("Credit Card - 2838")
where the Zoho account's name belongs, and nothing said so until a drive saw
the wrong name printed. `GET /api/settings` now carries, per card in
`cards_effective[]`, an `account_check` held to item 184's standard
(`zoho.accounts.resolve_paid_through`), with the account it most likely
meant. Route-level through the settings read, over a provisioned chart file.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon import category_vocabulary  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
TRAVEL = "CHASE VISA - 2838 - TRAVEL"
APPLE = "GSBANK Apple Master Card 0113 | Dirk Neumann"


def _acct(account_id, name, account_type="credit_card", active=True):
    return {"account_id": account_id, "account_name": name, "account_code": "",
            "account_type": account_type, "is_active": active,
            "parent_account_name": None}


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": [
            _acct("111", TRAVEL),
            _acct("112", APPLE),
            _acct("222", "Office Supplies", account_type="expense"),
            _acct("333", "Chase Visa 4700 | old", active=False),
        ]},
        CLOUD_ORG: {"org": {"name": CLOUD}, "accounts": [
            _acct("444", "Chase Visa | 9693 | Cloud Expenses"),
        ]},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    category_vocabulary._CHARTS_CACHE.clear()
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _checks(web, cards: dict) -> dict[str, dict]:
    r = web.put("/api/settings", json={"cards": cards})
    assert r.status_code == 200, r.text
    body = web.get("/api/settings").json()
    return {c["key"]: c["account_check"] for c in body["cards_effective"]}


def _card(digits, account, entity=CORP):
    return {"label": f"Card {digits}", "digits": [digits], "entity": entity,
            "zoho_account": account}


def test_a_real_credit_card_account_passes(web):
    check = _checks(web, {"card-2838": _card("2838", TRAVEL)})["card-2838"]
    assert check["status"] == "ok"
    assert check["account_id"] == "111"
    assert check["closest"] == ""


def test_a_name_not_in_the_chart_fails_with_the_closest_card_account(web):
    """Card 3645's live shape: another card's label in the account field."""
    check = _checks(web, {"3645": _card("3645", "Credit Card - 2838")})["3645"]
    assert check["status"] == "not_in_chart"
    assert check["closest"] == TRAVEL, "the 2838 in the name points at the account"
    assert check["company_org"] == CORP_ORG


def test_the_suggestion_follows_the_cards_digits_over_a_similar_name(web):
    """"Master Card" reads closest to the Apple account by name alone; the
    card's own digits (2838) name the account it really pays through."""
    check = _checks(web, {"card-2838": _card("2838", "Master Card")})["card-2838"]
    assert check["status"] == "not_in_chart"
    assert check["closest"] == TRAVEL


def test_an_expense_account_fails_wrong_type(web):
    check = _checks(web, {"card-x": _card("1111", "Office Supplies")})["card-x"]
    assert check["status"] == "wrong_type"
    assert check["account_id"] == "222"
    assert check["closest"] in {TRAVEL, APPLE}


def test_an_inactive_card_account_fails_inactive(web):
    check = _checks(web, {"card-4700": _card("4700", "Chase Visa 4700 | old")})["card-4700"]
    assert check["status"] == "inactive"
    assert check["closest"] in {TRAVEL, APPLE}, "an inactive account is never suggested"


def test_another_companys_card_account_is_not_in_this_companys_chart(web):
    check = _checks(web, {"card-9693": _card(
        "9693", "Chase Visa | 9693 | Cloud Expenses", entity=CORP)})["card-9693"]
    assert check["status"] == "not_in_chart"
    assert CLOUD_ORG in check["detail"]


def test_an_unverified_chart_says_it_may_be_the_chart(web):
    """The fixture chart lacks Dirk's curated accounts, so `chart_coverage`
    reads not ok: a failing card must say the chart may be what is stale."""
    check = _checks(web, {"3645": _card("3645", "Credit Card - 2838")})["3645"]
    assert check["chart_verified"] is False
    assert "may be the chart that is stale" in check["detail"]
