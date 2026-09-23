"""The Zoho COA pull is complete, or it says so.

The negative cases are the contract. Backlog item 182 read the short chart
as a pull that stopped paginating, and the fix that reading implies (walk
`has_more_page`, fail on a short page) does not work here: measured live on
2026-09-24, org 697686691 returns 199 rows on per_page=200, 89 on
per_page=100 and 47 on per_page=50, reporting `has_more_page: false` every
time. So the fake transport below LIES exactly the way the real one does,
and the tests assert that completeness is decided against the curated
answer key rather than against anything the listing said about itself.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "pull-brisken-zoho-coa.py"
_spec = importlib.util.spec_from_file_location("pull_brisken_zoho_coa", MODULE_PATH)
pull = importlib.util.module_from_spec(_spec)
sys.modules["pull_brisken_zoho_coa"] = pull
_spec.loader.exec_module(pull)


BCS = "697686691"


def _acct(aid, name, atype="expense", code="", active=True, parent=None):
    return {
        "account_id": aid,
        "account_name": name,
        "account_code": code,
        "account_type": atype,
        "parent_account_name": parent,
        "is_active": active,
        "description": "",
    }


class FakeZoho:
    """A listing that under-reports and still claims to be finished.

    `by_plan` maps a plan key ("default" / "showbalance") to the rows that
    plan returns. `by_id` is what the single-account endpoint can produce,
    which on the real tenant is a strict superset of every listing.
    """

    def __init__(self, by_plan, by_id=None, page_size=200):
        self.by_plan = by_plan
        self.by_id = by_id or {}
        self.page_size = page_size
        self.calls = []

    def __call__(self, path, **params):
        self.calls.append((path, dict(params)))
        if path.startswith("/chartofaccounts/"):
            aid = path.rsplit("/", 1)[1]
            row = self.by_id.get(aid)
            return {"chart_of_account": row} if row else {}
        plan = "showbalance" if params.get("showbalance") else "default"
        rows = self.by_plan.get(plan, [])
        page = int(params.get("page", 1))
        start = (page - 1) * self.page_size
        chunk = rows[start : start + self.page_size]
        return {
            "chartofaccounts": chunk,
            "page_context": {
                # The lie, reproduced: a page shorter than per_page is
                # reported as the last one, which is how the real endpoint
                # hides 55 accounts behind a confident "false".
                "has_more_page": len(chunk) == self.page_size
                and start + len(chunk) < len(rows),
                "per_page": self.page_size,
            },
        }


# ── merge_listings ────────────────────────────────────────────────────────


def test_the_two_listings_are_merged_because_neither_contains_the_other():
    only_default = _acct("1", "Rent Expense")
    only_showbalance = _acct("2", "COGS - DEV Infra", atype="cost_of_goods_sold")
    both = _acct("3", "Travel Expense | Food")
    fetch = FakeZoho(
        {"default": [only_default, both], "showbalance": [only_showbalance, both]}
    )

    merged, by_plan = pull.merge_listings(fetch, BCS)

    assert set(merged) == {"1", "2", "3"}
    assert by_plan == {"default": 2, "showbalance": 2}


def test_a_short_page_claiming_no_more_is_accepted_not_retried():
    """The real endpoint does this on every call; treating it as an error
    would make the tool fail permanently instead of merging what it can."""
    fetch = FakeZoho({"default": [_acct(str(i), f"a{i}") for i in range(5)]})

    merged, by_plan = pull.merge_listings(fetch, BCS)

    assert len(merged) == 5
    assert by_plan["default"] == 5


def test_pagination_is_still_followed_where_the_server_admits_it():
    rows = [_acct(str(i), f"a{i}") for i in range(7)]
    fetch = FakeZoho({"default": rows}, page_size=3)

    merged, _ = pull.merge_listings(fetch, BCS, per_page=3)

    assert len(merged) == 7
    pages = [p["page"] for path, p in fetch.calls if path == "/chartofaccounts"]
    assert pages[:3] == [1, 2, 3]


def test_a_server_claiming_endless_pages_aborts_rather_than_looping():
    class Endless:
        def __call__(self, path, **params):
            return {
                "chartofaccounts": [_acct("x", "x")],
                "page_context": {"has_more_page": True},
            }

    with pytest.raises(pull.PullError, match="more than 60 pages"):
        pull.merge_listings(Endless(), BCS, per_page=1)


# ── top_up_by_id ──────────────────────────────────────────────────────────


def test_an_account_no_listing_returns_is_recovered_by_id():
    """`2031056000023745007 E600010-30-10 Marketing Expenses - people` is
    real, active and typed `expense`, and appears in none of the eight
    listing parameterizations measured on 2026-09-24."""
    hidden = "2031056000023745007"
    fetch = FakeZoho(
        {"default": [_acct("1", "Rent Expense")]},
        by_id={hidden: _acct(hidden, "Marketing Expenses - people")},
    )
    merged, _ = pull.merge_listings(fetch, BCS)

    recovered, unrecoverable = pull.top_up_by_id(fetch, BCS, merged, {"1", hidden})

    assert recovered == [hidden]
    assert unrecoverable == []
    assert merged[hidden]["account_name"] == "Marketing Expenses - people"


def test_an_account_by_id_cannot_produce_is_reported_not_invented():
    fetch = FakeZoho({"default": []}, by_id={})

    recovered, unrecoverable = pull.top_up_by_id(fetch, BCS, {}, {"999"})

    assert recovered == []
    assert unrecoverable == ["999"]


def test_top_up_asks_only_for_what_the_listing_missed():
    present = _acct("1", "Rent Expense")
    fetch = FakeZoho({"default": [present]}, by_id={"2": _acct("2", "Other")})
    merged, _ = pull.merge_listings(fetch, BCS)
    fetch.calls.clear()

    pull.top_up_by_id(fetch, BCS, merged, {"1", "2"})

    asked = [p for p, _ in fetch.calls if p.startswith("/chartofaccounts/")]
    assert asked == ["/chartofaccounts/2"]


# ── curated_answer_key ────────────────────────────────────────────────────


def test_the_answer_key_is_postable_bindings_only():
    leaves = {
        "E1": ((), {BCS: ("11", "Postable here", True, "")}),
        "E2": ((), {BCS: ("22", "Marked N here", False, "not_expense_relevant")}),
    }

    want = pull.curated_answer_key(leaves)

    assert want[BCS] == {"11": ("E1", "Postable here")}


def test_the_answer_key_is_per_org_because_one_code_is_many_accounts():
    """The code is stable across entities; the account_id is not. A key that
    collapsed them would assert a Cloud Services id against Consulting."""
    leaves = {
        "E100010-31": (
            (),
            {
                BCS: ("11", "Travel Expense | Food", True, ""),
                "808232536": ("22", "Travel Expense | Food", True, ""),
                "822741658": ("33", "CorpServ | Travel Expense | Food", True, ""),
            },
        )
    }

    want = pull.curated_answer_key(leaves)

    assert want[BCS] == {"11": ("E100010-31", "Travel Expense | Food")}
    assert want["808232536"] == {"22": ("E100010-31", "Travel Expense | Food")}
    assert set(want) == {BCS, "808232536", "822741658"}


def test_the_real_compiled_taxonomy_yields_dirks_counts():
    """67 / 64 / 68 is Dirk's own marking, and it is the only number in this
    tool that did not come from a pull."""
    sys.path.insert(
        0,
        str(
            pathlib.Path(__file__).resolve().parents[2]
            / "workspace/clients/brisken/automations/expense-reconciliation/src"
        ),
    )
    from expense_recon.zoho import _curated_leaves_data as curated

    want = pull.curated_answer_key(curated.LEAVES)

    assert {k: len(v) for k, v in sorted(want.items())} == {
        "697686691": 67,
        "808232536": 64,
        "822741658": 68,
    }


# ── the whole loop, through main() ────────────────────────────────────────


def _patch(monkeypatch, fetch, orgs):
    monkeypatch.setattr(pull, "read_env", lambda path: {})
    monkeypatch.setattr(pull, "make_fetch", lambda env: fetch)
    monkeypatch.setattr(pull, "organizations", lambda f, fallback_ids=(): orgs)


# ── organizations, and the scope it must not depend on ────────────────────


def test_the_org_directory_is_used_when_the_token_can_read_it():
    def fetch(path, **params):
        assert path == "/organizations"
        return {"organizations": [{"organization_id": BCS, "name": "BCS"}]}

    assert pull.organizations(fetch, fallback_ids=["zzz"]) == [
        {"organization_id": BCS, "name": "BCS"}
    ]


def test_a_401_on_the_org_directory_falls_back_instead_of_killing_the_pull(capsys):
    """`/organizations` needs settings.READ, which the token lost in 2026-08;
    `/chartofaccounts` needs accountants.READ, which it kept. Failing the
    whole pull on the scope the pull does not use would be a tool broken for
    a reason unrelated to its job."""

    def fetch(path, **params):
        raise pull.PullError("/organizations -> HTTP 401 code=57")

    orgs = pull.organizations(fetch, fallback_ids=[BCS, "808232536"])

    assert [o["organization_id"] for o in orgs] == [BCS, "808232536"]
    assert "using known org ids" in capsys.readouterr().out


def test_an_empty_org_directory_also_falls_back():
    """A 200 with no orgs is the same practical answer as a 401, and reading
    it as 'this tenant has no organizations' would write an empty snapshot."""

    def fetch(path, **params):
        return {"organizations": []}

    assert pull.organizations(fetch, fallback_ids=[BCS]) == [
        {"organization_id": BCS, "name": None}
    ]


def test_main_fails_when_a_curated_account_cannot_be_obtained_at_all(
    tmp_path, monkeypatch, capsys
):
    """The assertion that has ground truth: an account Dirk marked postable
    that neither listing nor by-id produces means the snapshot is short, and
    a short snapshot must not be promoted silently."""
    fetch = FakeZoho({"default": [_acct("1", "Rent Expense")]}, by_id={})
    _patch(monkeypatch, fetch, [{"organization_id": BCS, "name": "BCS"}])
    monkeypatch.setattr(
        pull,
        "curated_answer_key",
        lambda leaves: {BCS: {"1": ("E1", "Rent"), "404": ("E2", "Ghost")}},
    )

    rc = pull.main(
        ["--env", "x", "--out", str(tmp_path / "o.json"), "--compare", "nope"]
    )

    out = capsys.readouterr().out
    assert rc == 1
    assert "UNRECOVERABLE: 404 E2 'Ghost'" in out
    assert "do not promote it" in out


def test_main_passes_once_by_id_has_filled_the_gap(tmp_path, monkeypatch, capsys):
    fetch = FakeZoho(
        {"default": [_acct("1", "Rent Expense")]},
        by_id={"404": _acct("404", "Ghost")},
    )
    _patch(monkeypatch, fetch, [{"organization_id": BCS, "name": "BCS"}])
    monkeypatch.setattr(
        pull,
        "curated_answer_key",
        lambda leaves: {BCS: {"1": ("E1", "Rent"), "404": ("E2", "Ghost")}},
    )
    out_path = tmp_path / "o.json"

    rc = pull.main(["--env", "x", "--out", str(out_path), "--compare", "nope"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "every curated postable account is present" in out
    written = __import__("json").loads(out_path.read_text(encoding="utf-8"))
    assert {a["account_id"] for a in written[BCS]["accounts"]} == {"1", "404"}


def test_a_name_the_directory_cannot_supply_is_carried_from_the_old_snapshot(
    tmp_path, monkeypatch
):
    """The org directory is exactly what a token without settings.READ cannot
    read, so the fallback supplies ids and no names. Writing those nulls over
    the names the old snapshot had would be the pull losing data while
    reporting +56 -0."""
    import json as _json

    compare = tmp_path / "old.json"
    compare.write_text(
        _json.dumps(
            {BCS: {"org": {"organization_id": BCS, "name": "BRISKEN CLOUD SERVICES"},
                   "accounts": []}}
        ),
        encoding="utf-8",
    )
    fetch = FakeZoho({"default": [_acct("1", "Rent Expense")]})
    _patch(monkeypatch, fetch, [{"organization_id": BCS, "name": None}])
    monkeypatch.setattr(pull, "curated_answer_key", lambda leaves: {})
    out_path = tmp_path / "o.json"

    pull.main(["--env", "x", "--out", str(out_path), "--compare", str(compare)])

    written = _json.loads(out_path.read_text(encoding="utf-8"))
    assert written[BCS]["org"]["name"] == "BRISKEN CLOUD SERVICES"


def test_an_org_with_no_answer_key_is_merged_and_never_asserted(
    tmp_path, monkeypatch, capsys
):
    """Five of the eight orgs are not curated. Calling those complete would
    be the unfounded confidence this tool removes, so they are reported."""
    fetch = FakeZoho({"default": [_acct("1", "Something")]})
    _patch(monkeypatch, fetch, [{"organization_id": "903213149", "name": "DN"}])
    monkeypatch.setattr(pull, "curated_answer_key", lambda leaves: {BCS: {}})

    rc = pull.main(
        ["--env", "x", "--out", str(tmp_path / "o.json"), "--compare", "nope"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "no curated answer key for this org" in out
    assert not [p for p, _ in fetch.calls if p.startswith("/chartofaccounts/")]


def test_main_sends_both_listing_plans_for_every_org(tmp_path, monkeypatch):
    """If only one plan were sent, 55 Cloud Services accounts would vanish
    and nothing in the output would say so."""
    fetch = FakeZoho({"default": [_acct("1", "a")], "showbalance": [_acct("2", "b")]})
    _patch(monkeypatch, fetch, [{"organization_id": BCS, "name": "BCS"}])
    monkeypatch.setattr(pull, "curated_answer_key", lambda leaves: {})

    pull.main(["--env", "x", "--out", str(tmp_path / "o.json"), "--compare", "nope"])

    plans = {
        "showbalance" if p.get("showbalance") else "default"
        for path, p in fetch.calls
        if path == "/chartofaccounts"
    }
    assert plans == {"default", "showbalance"}
