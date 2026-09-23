"""Two category vocabularies are live at once, and every write path takes both.

Receipts are moving from the eight coarse buckets to Dirk's curated per-entity
Zoho GL leaves. The transition's whole risk is silence: a path that quietly
stops accepting one vocabulary looks exactly like working software. So the
contract is asserted from both directions here, at the gate and through each
route that used to refuse by name.

The negative cases are the contract. A bare account NAME must NOT be
recognised (it means different accounts in different entities) and a string
from neither vocabulary must never be stored.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.category_vocabulary import recognize  # noqa: E402
from expense_recon.learning import LearningStore, normalize_vendor  # noqa: E402
from expense_recon.matching.types import EXPENSE_CATEGORIES  # noqa: E402
from expense_recon.merchant_registry import (  # noqa: E402
    normalize_merchants_setting,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

LE = "brisken-llc"
# Consulting LLC, the entity whose curated chart the compile verified against
# the live pull. Any curated org would do; the code is stable across all three.
ORG = "808232536"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _a_leaf() -> tuple[str, str]:
    """One postable curated code and this org's own name for it."""
    code = sorted(curated_leaves.postable_codes(ORG))[0]
    return code, curated_leaves.binding(code, ORG).name


# ── the gate ────────────────────────────────────────────────────────────


def test_both_vocabularies_are_recognised():
    code, _name = _a_leaf()
    assert recognize(EXPENSE_CATEGORIES[0]) == EXPENSE_CATEGORIES[0]
    assert recognize(code) == code


def test_a_labelled_leaf_reduces_to_its_bare_code():
    """`"CODE name"` is what the model is shown and what a client echoes.

    It stores as the code alone: the name is one entity's presentation, and
    storing it would make one account read as several.
    """
    label = curated_leaves.llm_leaf_labels(ORG)[0]
    assert " " in label, "the label is CODE + name"
    assert recognize(label) == label.split(None, 1)[0]


def test_a_bare_account_name_is_not_recognised():
    """The org-blind safety property, and the reason names never key here.

    `E100010-31` is `Travel Expense | Food` in two orgs and `CorpServ |
    Travel Expense | Food` in the third. Resolving a name without an entity
    is how a Cloud Services account reaches a Corporate Services expense.
    """
    _code, name = _a_leaf()
    assert recognize(name) is None


def test_neither_vocabulary_is_none():
    for value in ("Groceries", "", "   ", None, "E-NOPE-404"):
        assert recognize(value) is None


def test_recognising_a_code_does_not_make_it_postable():
    """The gate is storage tolerance, never a posting decision.

    Whether THIS entity may post to a leaf is `account_id_for`, which is
    org-scoped; a code Dirk marked N is still recognised as a category and
    still yields no account.
    """
    code, _name = _a_leaf()
    assert recognize(code) == code
    assert curated_leaves.account_id_for("822116290", code) is None, (
        "the sandbox org is not curated, so nothing resolves in it"
    )


# ── the write paths take a leaf code ────────────────────────────────────


def test_memory_upsert_stores_a_leaf_code(client):
    code, _name = _a_leaf()
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Anthropic", "category": code,
    })
    assert r.status_code == 200, r.text
    assert r.json()["category"] == code
    assert "ignored" not in r.json()
    with LearningStore(client._data_root / "learning.sqlite") as s:
        row = s.get_merchant_category(LE, normalize_vendor("Anthropic"))
    assert row.category == code


def test_memory_upsert_stores_a_labelled_leaf_as_its_code(client):
    label = curated_leaves.llm_leaf_labels(ORG)[0]
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Anthropic", "category": label,
    })
    assert r.status_code == 200, r.text
    assert r.json()["category"] == label.split(None, 1)[0]


def test_a_dropped_category_leaves_a_stored_rule_untouched(client):
    """The drop is not a clear. Durable memory keeps what it had."""
    code, _name = _a_leaf()
    client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Anthropic", "category": code,
    })
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Anthropic", "category": "Groceries",
    })
    assert r.status_code == 200, r.text
    assert r.json()["ignored"] == {"category": "Groceries"}
    assert r.json()["category"] == code
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.get_merchant_category(
            LE, normalize_vendor("Anthropic")).category == code


def test_settings_merchants_take_a_leaf_code(client):
    code, _name = _a_leaf()
    r = client.put("/api/settings", json={"merchants": {
        "Anthropic": {"aliases": ["ANTHROPIC"], "category": code},
    }})
    assert r.status_code == 200, r.text
    assert r.json()["ignored"] == []
    got = client.get("/api/settings").json()["merchants"]
    assert got["Anthropic"]["category"] == code


def test_one_unknown_merchant_category_no_longer_fails_the_whole_save(client):
    """The failure this change exists to remove.

    The SPA sends the entire settings map back on every save. One merchant
    holding a string the server no longer knows used to 400 the request,
    taking the cards and entities tabs down with it.
    """
    code, _name = _a_leaf()
    r = client.put("/api/settings", json={
        "merchants": {
            "Stale": {"category": "Groceries"},
            "Anthropic": {"category": code},
        },
        "cards": {"amex-1234": {"label": "Amex", "digits": ["1234"]}},
    })
    assert r.status_code == 200, r.text
    assert r.json()["ignored"] == ["merchants.Stale.category"]
    assert "cards" in r.json()["applied"], "the untouched tab still saved"
    settings = client.get("/api/settings").json()
    assert settings["merchants"]["Stale"]["category"] is None
    assert settings["merchants"]["Anthropic"]["category"] == code
    assert settings["cards"]["amex-1234"]["digits"] == ["1234"]


def test_the_registry_normaliser_keeps_a_leaf_code():
    code, _name = _a_leaf()
    out = normalize_merchants_setting({"A": {"category": code}})
    assert out["A"]["category"] == code
