"""The precedence chain that decides which curated GL leaf a receipt posts to.

The refusals are the contract, not the happy path. Both silent mis-posts this
design removes were confident wrong answers, so every test that asserts a
resolution is paired with one asserting that the chain declines instead of
guessing.
"""
from __future__ import annotations

import pytest

from expense_recon.learning.consult import MerchantCategoryLookup
from expense_recon.learning.store import MerchantCategory
from expense_recon.zoho import curated_leaves
from expense_recon.zoho.posting_resolution import (
    ACCOUNT_UNRESOLVED,
    SOURCE_LEARNED_RULE,
    SOURCE_LLM_LEAF,
    SOURCE_REFUSED,
    TIER2_DEFERRED,
    PostingResolution,
    resolve_posting_account,
)

# Consulting LLC, the org the compile verified account-by-account against the
# live pull. NOT the TEST-BTS sandbox 822116290, which is a clone of it.
ORG = "808232536"
SANDBOX = "822116290"
LE = "Consulting LLC"


def _postable() -> str:
    return sorted(curated_leaves.postable_codes(ORG))[0]


def _unpostable() -> tuple[str, str]:
    """A code the compiled asset knows and this org may not post to."""
    for code in sorted(curated_leaves._leaves()):
        b = curated_leaves.binding(code, ORG)
        if b is not None and not b.postable:
            return code, b.reason
    raise AssertionError("the asset carries no non-postable leaf for this org")


def _rule(category=None, account=None, entity=LE, vendor_norm="acme"):
    return MerchantCategory(
        legal_entity_id=entity, vendor_norm=vendor_norm, category=category,
        zoho_account=account, decision_count=1,
        last_confirmed_at="2026-09-01T00:00:00", source_run="r1",
    )


def _resolve(**kw):
    kw.setdefault("org_id", ORG)
    kw.setdefault("legal_entity_id", LE)
    kw.setdefault("vendor", "Acme")
    return resolve_posting_account(**kw)


# ── an uncovered entity never guesses ───────────────────────────────────


def test_an_uncovered_org_refuses_before_anything_else():
    """The rollout and rollback lever.

    A new entity is opted in by a reviewed diff, never by a receipt
    arriving, so even a perfectly good leaf code resolves to nothing here.
    """
    out = _resolve(org_id=SANDBOX, llm_leaf=_postable())
    assert out.source == SOURCE_REFUSED
    assert out.reason == curated_leaves.NOT_COVERED
    assert out.account_id is None


# ── Tier 1: the rule a person taught ────────────────────────────────────


def test_a_learned_leaf_code_wins():
    code = _postable()
    lookup = MerchantCategoryLookup([_rule(category=code)])
    out = _resolve(lookup=lookup, llm_leaf=None)
    assert out.source == SOURCE_LEARNED_RULE
    assert out.code == code
    assert out.account_id == curated_leaves.account_id_for(ORG, code)


def test_a_learned_rule_outranks_the_model():
    """Memory is consulted first; the model never overrides a person."""
    learned, other = sorted(curated_leaves.postable_codes(ORG))[:2]
    lookup = MerchantCategoryLookup([_rule(category=learned)])
    out = _resolve(lookup=lookup, llm_leaf=other)
    assert out.code == learned
    assert out.source == SOURCE_LEARNED_RULE


def test_a_legacy_rule_naming_the_account_resolves_within_this_org():
    """Older rules carry the posting account as this org's account NAME."""
    code = _postable()
    name = curated_leaves.binding(code, ORG).name
    lookup = MerchantCategoryLookup([
        _rule(category="Travel & Transport", account=name)
    ])
    out = _resolve(lookup=lookup)
    assert out.code == code
    assert out.source == SOURCE_LEARNED_RULE


def test_a_learned_rule_on_an_unpostable_leaf_refuses_it_does_not_fall_back():
    """The substitution this module exists to prevent.

    Falling through to the model here would silently replace a human's
    decision with a machine's, which is what the translation table did one
    layer up. The refusal carries the reason, so the right person is sent to
    look at it.
    """
    bad, reason = _unpostable()
    good = _postable()
    lookup = MerchantCategoryLookup([_rule(category=bad, account=bad)])
    out = _resolve(lookup=lookup, llm_leaf=good)
    assert out.source == SOURCE_REFUSED
    assert out.reason == reason
    assert out.code == bad
    assert out.account_id is None


def test_a_bucket_only_rule_names_no_leaf_and_does_fall_through():
    """The other half of the rule above, and the reason it is not the same.

    A bucket-only rule answers "which bucket", not "which account". Passing
    it on overrides no decision, because none about an account was made.
    """
    code = _postable()
    lookup = MerchantCategoryLookup([_rule(category="Travel & Transport")])
    out = _resolve(lookup=lookup, llm_leaf=code)
    assert out.source == SOURCE_LLM_LEAF
    assert out.code == code


def test_a_vendor_only_recall_never_decides_an_account():
    """An account belongs to ONE company's chart.

    A vendor-only recall aggregates rules saved under other companies.
    Agreeing on a category says nothing about agreeing on an account id, so
    the chain declines to take the account even when the rules agree.
    """
    code = _postable()
    lookup = MerchantCategoryLookup([
        _rule(category=code, entity="Cloud Services", vendor_norm="acme"),
        _rule(category=code, entity="Corporate Services", vendor_norm="acme"),
    ])
    recall = lookup.recall("", "Acme")
    assert recall is not None and recall.kind == "vendor_only", (
        "the fixture has to actually produce a vendor-only recall"
    )
    out = _resolve(legal_entity_id="", lookup=lookup)
    assert out.source == SOURCE_REFUSED
    assert out.reason == ACCOUNT_UNRESOLVED


# ── Tier 2: deferred, and refusing rather than absent ───────────────────


def test_a_trip_row_refuses_instead_of_letting_the_model_do_tier_2():
    """A purpose cannot pick a leaf: each family splits three ways.

    Conferences, CRM and general Travel each split into Transportation,
    Accommodation and Food, so inheriting a leaf from a trip's purpose would
    silently choose one of three. Deferred until Dirk rules, and refusing in
    the meantime rather than quietly handing the job to the model.
    """
    out = _resolve(cost_center="Rome 2026", llm_leaf=_postable())
    assert out.source == SOURCE_REFUSED
    assert out.reason == TIER2_DEFERRED
    assert out.account_id is None


def test_a_learned_rule_still_outranks_the_tier_2_refusal():
    """Tier 2 sits BELOW memory: a taught trip expense still posts."""
    code = _postable()
    lookup = MerchantCategoryLookup([_rule(category=code)])
    out = _resolve(lookup=lookup, cost_center="Rome 2026")
    assert out.source == SOURCE_LEARNED_RULE
    assert out.code == code


# ── Tier 3: the model, against this entity's own leaves ─────────────────


def test_the_model_may_name_a_code_or_a_label():
    label = curated_leaves.llm_leaf_labels(ORG)[2]
    code = label.split(None, 1)[0]
    assert _resolve(llm_leaf=label).code == code
    assert _resolve(llm_leaf=code).code == code


def test_the_model_naming_an_unpostable_leaf_refuses_with_the_reason():
    bad, reason = _unpostable()
    out = _resolve(llm_leaf=bad)
    assert out.source == SOURCE_REFUSED
    assert out.reason == reason


def test_a_model_answer_that_resolves_to_nothing_refuses():
    for named in (None, "", "Groceries", "E-NOPE-404"):
        out = _resolve(llm_leaf=named)
        assert out.source == SOURCE_REFUSED
        assert out.reason == ACCOUNT_UNRESOLVED, named


def test_an_account_name_is_never_resolved_across_entities():
    """The trap the whole taxonomy is keyed on codes to avoid.

    Corporate Services names a leaf `CorpServ | Travel Expense | Food` where
    the other two orgs call the same code `Travel Expense | Food`. A name
    offered to the wrong org must resolve to nothing, not to that org's
    similarly-named account.
    """
    corp = "822741658"
    for code in sorted(curated_leaves.postable_codes(corp)):
        name = curated_leaves.binding(code, corp).name
        if name.lower().startswith("corpserv |"):
            assert curated_leaves.code_of(name, ORG) is None
            assert _resolve(llm_leaf=name).source == SOURCE_REFUSED
            return
    pytest.skip("this revision carries no CorpServ-prefixed name")


# ── what may leave here ─────────────────────────────────────────────────


def test_a_resolution_can_never_carry_a_name_as_an_account_id():
    """The assertion that would have caught the 2026-09-22 mis-post.

    An account arrived as a NAME where a numeric id was expected. It did not
    error, it defaulted, and 6 of 9 rows landed in `Office Infra and Admin`.
    """
    with pytest.raises(ValueError):
        PostingResolution(
            account_id="Office Infra and Admin", code="E1",
            source=SOURCE_LEARNED_RULE,
        )


def test_every_resolved_answer_carries_digits():
    for code in sorted(curated_leaves.postable_codes(ORG))[:10]:
        out = _resolve(llm_leaf=code)
        assert out.resolved and out.account_id.isdigit()
