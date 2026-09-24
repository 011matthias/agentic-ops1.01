"""Dirk's curated leaves: the identity is the code, and only an id may leave.

Every assertion here is a failure that has actually happened or was one step
away, not a restatement of the implementation.
"""
from __future__ import annotations

import pytest

from expense_recon.zoho import curated_leaves as cl

CLOUD = "697686691"      # BCS
CONSULTING = "808232536"  # BTS
CORPSERV = "822741658"
SANDBOX = "822116290"

# The Client-BD food leaf. One code, three orgs, three different account ids.
CRM_FOOD = "E600010-10-20-30"
# The general travel food leaf. CorpServ names it differently from the others.
TRAVEL_FOOD = "E100010-31"
# Anthropic's target under Cloud Services, and one of the 19 accounts missing
# from the truncated chart pull. Its presence here is why the asset is compiled
# from Dirk's sheet rather than from that pull.
DEV_INFRA = "E700030-19"


def test_the_three_curated_orgs_are_the_real_ones_and_not_the_sandbox():
    """BTS reads like the sandbox and is Consulting LLC.

    The tab label is `BTS`, and `TEST-BTS` 822116290 is a clone of that company.
    Trusting the label would aim the entire mapping at a test company.
    """
    assert set(cl.curated_orgs()) == {CLOUD, CONSULTING, CORPSERV}
    assert SANDBOX not in cl.curated_orgs()
    assert cl.covers_org(CONSULTING)
    assert not cl.covers_org(SANDBOX)


def test_an_uncovered_org_refuses_rather_than_falling_back():
    assert cl.account_id_for(SANDBOX, CRM_FOOD) is None
    assert cl.refusal_reason(SANDBOX, CRM_FOOD) == cl.NOT_COVERED
    assert cl.postable_codes(SANDBOX) == frozenset()
    assert cl.llm_leaf_labels(SANDBOX) == ()
    assert not cl.is_postable(SANDBOX, CRM_FOOD)


def test_none_org_is_not_a_wildcard():
    """An unassigned receipt must not silently borrow some entity's chart."""
    assert cl.account_id_for(None, CRM_FOOD) is None
    assert cl.code_of(CRM_FOOD, None) is None
    assert not cl.is_postable(None, CRM_FOOD)


def test_one_code_resolves_to_a_different_account_id_per_entity():
    """The cross-entity case the whole design turns on."""
    ids = {org: cl.account_id_for(org, CRM_FOOD)
           for org in (CLOUD, CONSULTING, CORPSERV)}
    assert all(v for v in ids.values()), ids
    assert len(set(ids.values())) == 3, ids


def test_only_a_numeric_account_id_is_ever_returned():
    """A NAME where an id was expected does not error in Zoho, it defaults.

    That is the 2026-09-22 mis-post: 6 of 9 sandbox rows silently landed in
    `Office Infra and Admin`.
    """
    for org in cl.curated_orgs():
        for code in sorted(cl.postable_codes(org)):
            got = cl.account_id_for(org, code)
            assert got is not None and got.isdigit(), (org, code, got)


def test_the_name_differs_across_entities_where_the_code_does_not():
    """Keying on the name would silently skip Corporate Services."""
    corp = cl.binding(TRAVEL_FOOD, CORPSERV)
    cloud = cl.binding(TRAVEL_FOOD, CLOUD)
    assert corp is not None and cloud is not None
    assert corp.name != cloud.name
    assert corp.name.startswith("CorpServ")
    # Same code, both postable, different ids.
    assert corp.postable and cloud.postable
    assert corp.account_id != cloud.account_id


def test_a_name_resolves_only_within_its_own_entity():
    """Resolving a name globally is how one org's account reaches another's row."""
    corp_name = cl.binding(TRAVEL_FOOD, CORPSERV).name
    assert cl.code_of(corp_name, CORPSERV) == TRAVEL_FOOD
    # The CorpServ wording does not exist in Cloud Services.
    assert cl.code_of(corp_name, CLOUD) is None


def test_the_llm_label_shape_round_trips_back_to_its_code():
    """Tier 3 hands the model these labels and gets one back."""
    labels = cl.llm_leaf_labels(CLOUD)
    assert labels
    for label in labels[:25]:
        code = cl.code_of(label, CLOUD)
        assert code is not None, label
        assert cl.account_id_for(CLOUD, code) is not None


def test_the_account_anthropic_posts_to_in_cloud_services_is_present():
    """It is absent from the chart pull; compiling from the sheet is why.

    If this goes missing, the asset was rebuilt from `zoho-books-coa.json`,
    which truncates Cloud Services at a page boundary.
    """
    assert cl.is_postable(CLOUD, DEV_INFRA)
    assert cl.account_id_for(CLOUD, DEV_INFRA) == "2031056000014161139"


def test_the_branch_comes_from_names_not_from_the_code_prefix():
    """`Business Travel Expenses - CRM` is E600010-20; its children are
    E600010-10-20-*, nested under the CONFERENCES parent E600010-10.

    A prefix-derived hierarchy puts CRM travel under Conferences.
    """
    crm = cl.leaf(CRM_FOOD)
    assert crm is not None
    assert "Business Travel Expenses - CRM" in crm.branch
    assert not any("Conferences" in part for part in crm.branch), crm.branch


def test_a_non_postable_code_says_which_of_four_facts_it_hit():
    """`unknown reference` would send the wrong person to look."""
    reasons = set()
    for code, lf in cl._leaves().items():
        for org, b in lf.bindings.items():
            if not b.postable:
                r = cl.refusal_reason(org, code)
                assert r, (org, code)
                reasons.add(r)
    # Dirk's N is the bulk of it; the vocabulary must stay closed.
    assert "not_expense_relevant" in reasons
    assert reasons <= {"not_expense_relevant", "inactive", "do_not_use", "roll_up"}


def test_a_code_absent_from_one_org_is_distinguishable_from_a_bad_code():
    missing = [c for c, lf in cl._leaves().items() if CLOUD not in lf.bindings]
    if missing:
        assert cl.refusal_reason(CLOUD, missing[0]) == cl.NO_SUCH_CODE
    assert cl.refusal_reason(CLOUD, "NOT-A-REAL-CODE") == cl.NO_SUCH_CODE
    assert cl.leaf("NOT-A-REAL-CODE") is None


def test_the_postable_counts_are_dirks_own():
    """Guards a silent partial load. 68/67/64 are his marks, not ours."""
    assert len(cl.postable_codes(CORPSERV)) == 68
    assert len(cl.postable_codes(CLOUD)) == 67
    assert len(cl.postable_codes(CONSULTING)) == 64


def test_the_asset_records_which_sheet_it_came_from():
    """Two runs are only comparable if the chart behind them is identified."""
    assert cl.curated_revision() == "2026-09-23"
    assert len(cl.source_sha256()) == 64


def test_every_postable_leaf_carries_a_display_category():
    """Kept so a classification can group without a translation table."""
    for org in cl.curated_orgs():
        for code in sorted(cl.postable_codes(org)):
            assert cl.display_category_for(code), code


def test_a_root_account_dirk_marked_postable_is_its_own_category():
    """Eight postable leaves have no parent, and that is his convention.

    Outside the COGS tree a parent is postable, and Corporate Services' chart
    is coarse enough that an OpeEx header is the whole card-expense operating
    tree. Treating these as uncategorised would drop real accounts.
    """
    assert cl.display_category_for("E000010") == "R&D"
    assert cl.leaf("E000010").branch == ()
    # The entity prefix is presentation: it never becomes the category.
    assert cl.display_category_for("E100000") == "OpeEx"


def test_a_display_category_does_not_depend_on_which_entity_is_asked():
    """One code, one grouping, or a month spanning entities would double-count."""
    for code, lf in cl._leaves().items():
        if len(lf.bindings) > 1:
            assert cl.display_category_for(code) == lf.display_category


def test_an_empty_or_junk_reference_resolves_to_nothing():
    for ref in ("", None, "   ", "E999999-99", "Some Account That Is Not There"):
        assert cl.code_of(ref, CLOUD) is None


def test_the_loader_refuses_an_asset_whose_declared_count_is_wrong(monkeypatch):
    """A partial load reads exactly like a small chart.

    The pull this asset replaced truncated silently at a page boundary, so the
    count is checked on build rather than trusted.
    """
    from expense_recon.zoho import _curated_leaves_data as data

    monkeypatch.setattr(
        data, "POSTABLE_COUNTS", dict(data.POSTABLE_COUNTS, **{CLOUD: 999}))
    with pytest.raises(cl.CuratedLeavesError, match="materialised"):
        cl._build()
