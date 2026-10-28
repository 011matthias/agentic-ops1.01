"""Item 147 (owner, 2026-09-18): "card 2838 for example should be an account
with others as subcards, same thing goes for the other cards with subcards",
and, asked which cards: "only 2838 has subcards, no where else".

The nine cards were a flat list, so an account's spend was never one figure
and the one Chase file covering four of them was named on four tabs. A card
now carries an optional `parent` (another card's key), the registry validates
the tree, and both month pages and both PDFs render it: an account's figures
are the group's, its subcards sit under it, and the statement is stated once.

Route-level throughout, plus the two documents. The month below carries every
row class the live month has, because item 146's lesson was that an equality
assertion on a fixture missing a population tests equality-in-its-absence: a
subcard whose charges arrive on the account's own file, a subcard whose
statement is its OWN file, a subcard with zero charges, a standalone card that
is not under the account, a receipt no charge holds, and a receipt with no
card at all.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    Card,
    card_parents,
    cards_from_setting,
    cards_to_setting,
    normalize_cards_setting,
)
from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.output._pdf_common import card_sections  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    _done,
    _expense,
    _extraction,
    _grid,
    _month,
    _wire,
    _xlsx,
)
from tests.test_reconciliation_report_by_card_item_138 import (  # noqa: E402
    _first,
    _pages,
    _png,
)

ACCOUNT = "Credit Card - 2838"
L3876 = "Credit Card Chase Visa - 3876"
L3645 = "Credit Card Chase Visa - 3645"
L0340 = "Credit Card Chase Visa - 0340"
L1176 = "Credit Card Chase Visa - 1176"

# The owner's tree, as the live registry will hold it: 2838 is the account,
# three cards sit under it, and 1176 stands alone even though it has a
# statement file of its own ("only 2838 has subcards, no where else").
FLAT_CARDS = {
    "corp-2838": {
        "label": ACCOUNT, "digits": ["2838"], "entity": "Corporate Services",
        "person": "Dirk Neumann - Corp Services",
    },
    "corp-3876": {
        "label": L3876, "digits": ["3876"], "entity": "Corporate Services",
        "person": "Nicolas Neumann",
    },
    "corp-3645": {
        "label": L3645, "digits": ["3645"], "entity": "Corporate Services",
        "person": "Dirk Neumann - Corp Services",
    },
    "corp-0340": {
        "label": L0340, "digits": ["0340"], "entity": "Corporate Services",
        "person": "Criss Neumann",
    },
    "corp-1176": {
        "label": L1176, "digits": ["1176"], "entity": "Corporate Services",
        "person": "Brisken Consulting",
    },
}
TREE_CARDS = {
    key: ({**entry, "parent": "corp-2838"}
          if key in ("corp-3876", "corp-3645", "corp-0340") else dict(entry))
    for key, entry in FLAT_CARDS.items()
}

# The fields a section carried before accounts existed (item 138). A month
# whose registry names no parent must still carry exactly these: the tree is
# the only thing that adds a key, which is what leaves every other month, and
# the SPA reading it, untouched.
BASE_FIELDS = {
    "key", "label", "digits", "statement", "statements", "period_start",
    "period_end", "n_charges", "n_matched", "unreconciled_by_ccy",
    "n_booked_without_receipt", "booked_without_receipt_by_ccy",
    "n_receipts", "n_receipts_without_charge",
}
EXPENSE_FIELDS = {"n_expenses", "totals_by_ccy"}

JULY_RECEIPTS = (
    _extraction("Pressmaster", "135.00", "2026-07-23"),
    _extraction("Github", "40.00", "2026-07-14", "Visa ending 3876"),
    _extraction("Lovable", "25.00", "2026-07-05", "Visa ending 3645"),
    _extraction("Apple", "9.99", "2026-07-08", "Visa ending 0340"),
    _extraction("Regus", "36.00", "2026-07-02", "Visa ending 1176"),
    _extraction("Taxi", "30.00", "2026-07-12"),
)
# The account's own file, covering the account card and one subcard. This is
# the live shape: one Chase statement, several cards on it.
SHARED_FILE = "July2026.xlsx"
SHARED_ROWS = [
    ("2838", datetime(2026, 7, 23), "PRESSMASTER DMCC", "Sale", -135.00),
    ("2838", datetime(2026, 7, 20), "AWS", "Sale", -80.00),
    ("3876", datetime(2026, 7, 14), "GITHUB", "Sale", -40.00),
]
OWN_FILE = "July2026-3645.xlsx"
OWN_ROWS = [("3645", datetime(2026, 7, 5), "LOVABLE", "Sale", -25.00)]
ALONE_FILE = "July2026-1176.xlsx"
ALONE_ROWS = [("1176", datetime(2026, 7, 2), "REGUS", "Sale", -36.00)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _attach_named(client, batch: str, name: str, account: str, rows) -> None:
    resp = client.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": (
            name, _xlsx(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": account,
            "account_legal_entities": '{"%s": "Corporate Services"}' % account,
            "account_card_currency": "USD",
        },
    )
    _done(client, resp)


def _registry(client, monkeypatch, cards: dict) -> None:
    """The registry and the OCR stub, both before the batch is created: a
    batch snapshots the composed registry at creation."""
    client.put("/api/settings", json={"cards": cards})
    _wire(monkeypatch, *JULY_RECEIPTS)


def _attach_all(client, batch: str) -> None:
    _attach_named(client, batch, SHARED_FILE, "card-2838", SHARED_ROWS)
    _attach_named(client, batch, OWN_FILE, "card-3645", OWN_ROWS)
    _attach_named(client, batch, ALONE_FILE, "card-1176", ALONE_ROWS)


def _july(client, monkeypatch, cards: dict) -> str:
    _registry(client, monkeypatch, cards)
    batch = _month(client, len(JULY_RECEIPTS), label="July 2026")
    _attach_all(client, batch)
    return batch


def _july_with_images(client) -> str:
    """The same month with real images, so each receipt renders to a page and
    the documents' section order can be read off the pages."""
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "July 2026"}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    files = [
        ("files", (f"receipt-{c}.png", _png(c), "image/png"))
        for c in ("red", "green", "blue", "yellow", "orange", "purple")
    ]
    _done(client, client.post(f"/api/expense-batches/{batch}/receipts", files=files))
    return batch


def _by_key(sections: list[dict]) -> dict[str, dict]:
    return {s["key"]: s for s in sections}


@pytest.fixture
def tree(client, monkeypatch):
    """The owner's tree on the July-shaped month: (run payload, grid payload)."""
    batch = _july(client, monkeypatch, TREE_CARDS)
    run = client.get(f"/api/runs/{batch}")
    grid = client.get(f"/api/expense-batches/{batch}")
    assert run.status_code == 200, run.text
    assert grid.status_code == 200, grid.text
    return run.json(), grid.json()


@pytest.fixture
def flat(client, monkeypatch):
    """The same month with the same cards and NO parent anywhere."""
    batch = _july(client, monkeypatch, FLAT_CARDS)
    run = client.get(f"/api/runs/{batch}")
    grid = client.get(f"/api/expense-batches/{batch}")
    assert run.status_code == 200, run.text
    assert grid.status_code == 200, grid.text
    return run.json(), grid.json()


# ── the registry field ───────────────────────────────────────────────────


def test_a_card_carries_its_account_and_the_api_says_so(client):
    resp = client.put("/api/settings", json={"cards": TREE_CARDS})
    assert resp.status_code == 200, resp.text
    assert "cards" in resp.json()["applied"]

    cards = {c["key"]: c for c in client.get("/api/cards").json()["cards"]}
    assert cards["corp-2838"]["parent"] == ""
    assert [k for k, c in cards.items() if c["parent"] == "corp-2838"] == [
        "corp-3876", "corp-3645", "corp-0340"
    ]
    assert cards["corp-1176"]["parent"] == "", "only 2838 has subcards"


def test_the_parent_survives_the_settings_round_trip_and_the_snapshot():
    stored = normalize_cards_setting(TREE_CARDS)
    assert stored["corp-3876"]["parent"] == "corp-2838"
    assert "parent" not in stored["corp-2838"], "an empty field is not stored"
    composed = cards_from_setting(stored)
    assert composed["corp-3645"].parent == "corp-2838"
    # The batch snapshot is the registry a month resolves cards from, so the
    # tree has to survive it or a month would render flat after the snapshot.
    assert cards_to_setting(composed) == stored


def test_card_parents_reads_only_the_links_that_hold():
    live = cards_from_setting(normalize_cards_setting(TREE_CARDS))
    assert card_parents(live) == {
        "corp-3876": "corp-2838",
        "corp-3645": "corp-2838",
        "corp-0340": "corp-2838",
    }
    assert card_parents(cards_from_setting(FLAT_CARDS)) == {}
    # A blob that never met the validator: the read side drops what it cannot
    # stand behind rather than rendering a broken tree.
    broken = {
        "a": Card(key="a", parent="ghost"),
        "b": Card(key="b", parent="b"),
        "c": Card(key="c", parent="dead"),
        "dead": Card(key="dead", active=False),
        "d": Card(key="d", parent="e"),
        "e": Card(key="e", parent="f"),
        "f": Card(key="f"),
    }
    assert card_parents(broken) == {"e": "f"}


@pytest.mark.parametrize("payload,code,fields", [
    ({"a": {"parent": "a"}}, "card_parent_self", {"card": "a"}),
    ({"a": {"parent": "nope"}}, "card_parent_unknown",
     {"card": "a", "parent": "nope"}),
    ({"a": {"parent": "b"}, "b": {"active": False}}, "card_parent_inactive",
     {"card": "a", "parent": "b"}),
    ({"a": {"parent": "b"}, "b": {"parent": "c"}, "c": {}},
     "card_parent_not_top_level",
     {"card": "a", "parent": "b", "grandparent": "c"}),
    ({"a": {"parent": "b"}, "b": {"parent": "a"}}, "card_parent_cycle",
     {"card": "a", "parent": "b", "through": "a"}),
])
def test_a_tree_the_registry_cannot_stand_behind_is_refused_by_code(
    client, payload, code, fields
):
    resp = client.put("/api/settings", json={"cards": payload})
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["code"] == code, body
    assert body["setting"] == "cards"
    assert body["error"], "the English sentence never leaves (item 130)"
    for name, value in fields.items():
        assert body[name] == value, body


def test_learning_a_hint_on_a_subcard_does_not_trip_the_parent_check(
    client, monkeypatch
):
    """The batch-cards route normalizes only the entries it touched. A subcard
    whose account is stored but untouched must still validate, or teaching a
    hint on any card under an account would 400."""
    batch = _july(client, monkeypatch, TREE_CARDS)
    resp = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": "Visa ending 3876", "card": "corp-3876"}],
        "learn": True,
    })
    assert resp.status_code == 200, resp.text
    (result,) = resp.json()["results"]
    assert result["learned"] is True, result
    cards = {c["key"]: c for c in client.get("/api/cards").json()["cards"]}
    assert cards["corp-3876"]["parent"] == "corp-2838"


# ── card_sections: the tree, and the month that has none ─────────────────


def test_the_account_comes_first_and_its_subcards_follow_it(tree):
    run, grid = tree
    assert [s["key"] for s in run["card_sections"]] == [
        "corp-2838", "corp-3645", "corp-3876", "corp-0340", "corp-1176", ""
    ]
    assert [s["key"] for s in grid["card_sections"]] == [
        s["key"] for s in run["card_sections"]
    ]
    by = _by_key(run["card_sections"])
    assert by["corp-2838"]["subcards"] == [
        "corp-3645", "corp-3876", "corp-0340"
    ]
    for key in ("corp-3645", "corp-3876", "corp-0340"):
        assert by[key]["parent"] == "corp-2838"
        assert "subcards" not in by[key], "the tree is one level deep"
    assert "parent" not in by["corp-1176"], "1176 stands alone"
    assert "subcards" not in by["corp-1176"]
    assert "parent" not in by[""] and "subcards" not in by[""]


def test_the_accounts_figures_are_the_sum_of_itself_and_its_subcards(tree):
    run, _grid = tree
    by = _by_key(run["card_sections"])
    account = by["corp-2838"]
    parts = [account["own"]] + [by[k] for k in account["subcards"]]

    assert account["n_charges"] == sum(p["n_charges"] for p in parts) == 4
    assert account["n_matched"] == sum(p["n_matched"] for p in parts) == 3
    assert account["n_receipts"] == sum(p["n_receipts"] for p in parts) == 4
    assert account["n_receipts_without_charge"] == sum(
        p["n_receipts_without_charge"] for p in parts
    ) == 1
    # AWS 80.00 is open on the account card itself and nowhere else, so the
    # group's open money is the account's own here.
    assert account["unreconciled_by_ccy"] == {"USD": "80.00"}
    assert account["period_start"] == "2026-07-05", "the group's earliest"
    assert account["period_end"] == "2026-07-23"

    # The subcard with zero charges: a section because it holds a receipt, and
    # its zeros are what make the sum a real test rather than a restatement.
    apple = by["corp-0340"]
    assert (apple["n_charges"], apple["n_matched"]) == (0, 0)
    assert (apple["n_receipts"], apple["n_receipts_without_charge"]) == (1, 1)
    assert apple["statement"] == "not_loaded"


def test_a_statement_that_covers_the_account_is_named_once(tree):
    run, _grid = tree
    by = _by_key(run["card_sections"])
    account = by["corp-2838"]
    # The account states both files that settle the group, once each.
    assert account["statements"] == [SHARED_FILE, OWN_FILE]
    assert account["own"]["statements"] == [SHARED_FILE]

    # 3876's charges arrived on the account's own file: it points at the
    # account instead of printing the same file name a second time.
    assert by["corp-3876"]["statements"] == [SHARED_FILE]
    assert by["corp-3876"]["statement_on_account"] is True
    # 3645 arrived on a file of its own, which the account does not carry, so
    # dropping its line would lose the only place that file is named.
    assert by["corp-3645"]["statements"] == [OWN_FILE]
    assert by["corp-3645"]["statement_on_account"] is False
    assert by["corp-0340"]["statement_on_account"] is False


def test_the_expenses_page_rolls_its_rows_up_the_same_way(tree):
    _run, grid = tree
    by = _by_key(grid["card_sections"])
    account = by["corp-2838"]
    assert (account["own"]["n_expenses"], account["own"]["totals_by_ccy"]) == (
        1, {"USD": "135.00"}
    )
    assert account["n_expenses"] == 4
    assert account["totals_by_ccy"] == {"USD": "209.99"}
    assert sum(
        s["n_expenses"] for s in grid["card_sections"] if "parent" not in s
    ) == grid["summary"]["n_expenses"] == 6, (
        "a consumer sums the top level, or it counts a subcard twice"
    )


def test_every_row_still_files_on_the_card_that_paid(tree):
    """The tree groups the tabs; it never moves a charge. A subcard's charges
    stay the subcard's, which is what keeps matching out of this change."""
    run, grid = tree
    assert {
        row["vendor"]: row["card_section"] for row in run["rows"]
    } == {
        "PRESSMASTER DMCC": "corp-2838", "AWS": "corp-2838",
        "GITHUB": "corp-3876", "LOVABLE": "corp-3645", "REGUS": "corp-1176",
    }
    assert {
        e["vendor"]["display"]: e["card_section"] for e in grid["expenses"]
    } == {
        "Pressmaster": "corp-2838", "Github": "corp-3876",
        "Lovable": "corp-3645", "Apple": "corp-0340", "Regus": "corp-1176",
        "Taxi": "",
    }


def test_a_registry_with_no_parent_renders_exactly_what_it_did(flat, tree):
    """The negative case is the contract: nothing about a month whose cards
    name no account changes. Same sections, same fields, same figures, and the
    figures are precisely what the tree month reports as each card's OWN."""
    flat_run, flat_grid = flat
    tree_run, tree_grid = tree

    assert [s["key"] for s in flat_run["card_sections"]] == [
        "corp-2838", "corp-1176", "corp-3645", "corp-3876", "corp-0340", ""
    ], "coverage order, untouched by the tree"
    for sec in flat_run["card_sections"]:
        assert set(sec) == BASE_FIELDS, sec
    for sec in flat_grid["card_sections"]:
        assert set(sec) == BASE_FIELDS | EXPENSE_FIELDS, sec

    named = {"key", "label", "digits"}
    for payload, tree_payload in ((flat_run, tree_run), (flat_grid, tree_grid)):
        flat_by, tree_by = _by_key(payload["card_sections"]), _by_key(
            tree_payload["card_sections"]
        )
        for key, sec in flat_by.items():
            figures = {k: v for k, v in sec.items() if k not in named}
            other = tree_by[key]
            expected = other["own"] if key == "corp-2838" else {
                k: v for k, v in other.items()
                if k not in named | {"parent", "statement_on_account"}
            }
            assert figures == expected, (key, figures, expected)


def test_the_grouping_helper_is_the_same_list_when_nothing_names_a_parent():
    """`card_sections` is where the tree is applied, so the no-parent path is
    pinned at the helper too: no argument, an empty map, and a map naming
    cards this month has no section for all return the untouched list."""
    view = {
        "coverage": [
            {"key": "a", "label": "A", "n_transactions": 1, "statements": []},
            {"key": "b", "label": "B", "n_transactions": 1, "statements": []},
        ],
        "rows": [
            {"transaction_id": "t1", "coverage_key": "a"},
            {"transaction_id": "t2", "coverage_key": "b"},
        ],
    }
    plain = card_sections(view, {})
    assert [s["key"] for s in card_sections(view, {}, None)] == ["a", "b"]
    assert card_sections(view, {}, {}) == plain
    assert card_sections(view, {}, {"ghost": "a", "b": "ghost"}) == plain
    assert all(
        set(s) == {"key", "label", "coverage", "rows", "receipt_docs"}
        for s in plain
    ), plain


# ── the money figures, on a month that carries every row class ───────────


def _tx(tid, day, vendor, amount, last4, currency="USD", **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=date(2026, 7, day), posting_date=None,
        amount=Decimal(amount), transaction_currency=currency,
        account_card_currency=currency, vendor_from_statement=vendor,
        card_last4=last4, **kw,
    )


def _rc(doc, vendor, total, day) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=date(2026, 7, day),
        detected_total=Decimal(total), detected_currency="USD",
        detected_vendor=vendor,
    )


def test_open_and_booked_money_add_up_the_account_across_currencies(client):
    """Item 102's figure and the open money, per account. A yellow row no
    receipt holds counts on its own card and again in the account's total, in
    its own currency, so a reader adding the subcard lines gets the account
    line and never a currency that quietly merged into another."""
    charges = [
        _tx("t_open_2838", 20, "AWS", "80.00", "2838"),
        _tx("t_booked_2838", 10, "YELLOW ROW", "50.00", "2838",
            entry_status="posted"),
        _tx("t_open_3876", 14, "GITHUB", "40.00", "3876"),
        _tx("t_booked_3645", 5, "YELLOW EUR", "12.30", "3645", currency="EUR",
            entry_status="posted"),
        _tx("t_held_3645", 6, "CAFE", "20.00", "3645"),
        _tx("t_open_1176", 2, "REGUS", "36.00", "1176"),
    ]
    receipts = [_rc("m1", "Cafe", "20.00", 6)]
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_held_3645", document_id="m1",
            match_type=MatchType.EXACT, confidence=0.99, reason="exact",
            score=95, amount_score=1.0, date_score=1.0, vendor_score=1.0,
        )],
        unmatched_transactions=[
            "t_open_2838", "t_booked_2838", "t_open_3876", "t_booked_3645",
            "t_open_1176",
        ],
        unmatched_receipts=[],
    )
    store = RunStore(client._data_root / "recon-web.sqlite")
    store.create_run(
        run_id="july", created_at="2026-08-02T00:00:00", label="July 2026",
        operator=None, summary={},
        snapshot=snapshot_to_dict(charges, receipts, outcome, []),
        config={"expense": {"cards": normalize_cards_setting(TREE_CARDS)}},
        work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    store.close()

    sections = client.get("/api/runs/july").json()["card_sections"]
    by = _by_key(sections)
    account = by["corp-2838"]
    assert account["subcards"] == ["corp-3645", "corp-3876"]
    assert account["own"]["unreconciled_by_ccy"] == {"USD": "80.00"}
    assert by["corp-3876"]["unreconciled_by_ccy"] == {"USD": "40.00"}
    assert by["corp-3645"]["unreconciled_by_ccy"] == {}
    assert account["unreconciled_by_ccy"] == {"USD": "120.00"}

    assert account["own"]["booked_without_receipt_by_ccy"] == {"USD": "50.00"}
    assert by["corp-3645"]["booked_without_receipt_by_ccy"] == {"EUR": "12.30"}
    assert account["booked_without_receipt_by_ccy"] == {
        "EUR": "12.30", "USD": "50.00"
    }
    assert account["n_booked_without_receipt"] == 2
    assert by["corp-1176"]["unreconciled_by_ccy"] == {"USD": "36.00"}
    assert "parent" not in by["corp-1176"]


# ── both documents follow the same tree ──────────────────────────────────


def test_the_reconciliation_report_sections_the_account_then_its_subcards(
    client, monkeypatch
):
    _registry(client, monkeypatch, TREE_CARDS)
    batch = _july_with_images(client)
    _attach_all(client, batch)
    run = client.get(f"/api/runs/{batch}").json()
    resp = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    pages = _pages(resp.content)

    at = 1
    for sec in run["card_sections"]:
        at = _first(pages, sec["label"], at)
        assert pages[at].startswith(sec["label"]), (sec["label"], pages[at])
        at += 1

    account = _first(pages, ACCOUNT, 1)
    assert f"Statements: {SHARED_FILE}, {OWN_FILE}" in pages[account]
    assert "with 3 subcards" in pages[account]
    assert "4 charges · 3 matched" in pages[account]
    # The figures above are the group's; the pages behind this heading are the
    # account card's own, and the heading says which.
    assert "1 receipt on this card" in pages[account]

    # The subcard on the account's file points at the account; the one with a
    # file of its own still names it, or nothing in the document would.
    on_account = _first(pages, L3876, account)
    assert f"Statement: on {ACCOUNT}" in pages[on_account]
    assert SHARED_FILE not in pages[on_account]
    own = _first(pages, L3645, account)
    assert f"Statement: {OWN_FILE}" in pages[own]


def test_the_month_report_lists_the_account_with_a_table_per_card(
    client, monkeypatch
):
    batch = _july(client, monkeypatch, TREE_CARDS)
    resp = client.get(f"/runs/{batch}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    flat_text = " ".join(_pages(resp.content))

    assert "Listing by card" in flat_text
    # The account heads a section; its own card and its subcards are tables
    # inside it, each with its own sums line, and the section's own sums line
    # is the group's. Both lines for the account is what proves the nesting:
    # one is its table's, one is the section's.
    assert f"{ACCOUNT}: 4 expenses · USD 209.99" in flat_text, flat_text[:600]
    assert f"{ACCOUNT}: 1 expense · USD 135.00" in flat_text, "its own table"
    for label, total in ((L3876, "40.00"), (L3645, "25.00"), (L0340, "9.99")):
        assert f"{label}: 1 expense · USD {total}" in flat_text, label
    assert f"{L1176}: 1 expense · USD 36.00" in flat_text, "no account"
    assert "with 3 subcards" in flat_text, "the account's own heading line"


def test_a_month_whose_cards_name_no_account_reports_as_it_did(
    client, monkeypatch
):
    """The documents' half of the negative case: the flat registry still
    produces a section per card with no account heading over any of them."""
    batch = _july(client, monkeypatch, FLAT_CARDS)
    resp = client.get(f"/runs/{batch}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    text = " ".join(_pages(resp.content))
    assert "Listing by card" in text
    assert f"{ACCOUNT}: 1 expense" in text, "its own row only"
    assert f"{L3876}: 1 expense" in text
    assert "subcard" not in text.lower()

    recon = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert recon.status_code == 200, recon.text
    recon_text = " ".join(_pages(recon.content))
    assert "subcard" not in recon_text.lower()
    assert f"Statement: on {ACCOUNT}" not in recon_text


def test_the_grid_and_the_run_agree_about_the_tree(tree):
    """One month, one tree. The Expenses payload's sections are the Matching
    payload's with the two expense figures added, `own` included."""
    run, grid = tree
    stripped = []
    for sec in grid["card_sections"]:
        copy = {k: v for k, v in sec.items() if k not in EXPENSE_FIELDS}
        if "own" in copy:
            copy["own"] = {
                k: v for k, v in copy["own"].items() if k not in EXPENSE_FIELDS
            }
        stripped.append(copy)
    assert stripped == run["card_sections"]


def test_a_month_that_has_only_the_account_keeps_the_flat_page(
    client, monkeypatch
):
    """The two-cards-or-more rule is unchanged: an account whose subcards have
    nothing this month is one card, and one card gets no tabs."""
    client.put("/api/settings", json={"cards": TREE_CARDS})
    _wire(monkeypatch, _extraction("Pressmaster", "135.00", "2026-07-23"))
    batch = _month(client, 1, label="July 2026")
    _attach_named(client, batch, SHARED_FILE, "card-2838", SHARED_ROWS[:1])
    assert client.get(f"/api/runs/{batch}").json()["card_sections"] == []
    assert _expense(client, batch, "Pressmaster")["card_section"] == "corp-2838"
    assert _grid(client, batch)["card_sections"] == []
