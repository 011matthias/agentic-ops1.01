"""Per-card coverage on a living month (PR 3).

`statements[]` (PR 2b-2b-2) answers the FILE question: which uploads has
this month taken, over what span, and what did each contribute. It cannot
answer the CARD question, which is the one the work is organized around,
because a card is loaded across several files and a file can print charges
from several cards. `coverage[]` is that answer.

The live January 2026 month is the argument for it: 80 charges, three card
identities (2838 / 3645 / 0340), zero reconciled, USD 20,228.68
unreconciled. Flat, that is one number nobody can act on. Split per card it
is three, and two of the three cards are ones the registry has never met.

Four things are under test, and the last two are the ones that make the
surface trustworthy rather than decorative:

1. **The grouping.** One physical card is one row even when the statement
   and the plastic print different digits; a card the registry never met is
   its OWN row rather than being folded into an "other" bucket; a registry
   card with nothing loaded still gets a row, because "which cards have I
   not loaded yet" is only answerable from a list that includes them.
2. **The joins.** An entry names the uploads that covered it, found both
   from what the operator typed and from what the file actually printed.
3. **One meaning.** The grid and the workbench report the same coverage for
   the same month, and both move when the reviewer rejects a match. Two
   screens reporting a month at two different stages of done is the
   `n_categorized` failure of 2026-08-22 with money attached.
4. **Nothing is lost.** Every charge counts in exactly one row and the rows
   sum to the month's own summary, so a card table can be added up against
   the headline and must agree.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=4):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _cards(client, **cards) -> None:
    """Seed the card registry BEFORE the batch is created: a batch
    snapshots the composed registry into its own config at creation, and
    coverage reads that snapshot, not live settings."""
    client.put("/api/settings", json={"cards": cards})


def _batch(client, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


# ── statement bodies ────────────────────────────────────────────────────
#
# Written here rather than taken from `examples/` because every test below
# turns on one specific difference between two files (which card a row is
# on, which card an upload names), and a shared fixture cannot say which
# difference is the one under test.


def _csv(*rows: tuple[str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v}\n" for d, a, v in rows)
    return ("Date,Amount,Vendor\n" + body).encode()


def _carded_csv(*rows: tuple[str, str, str, str]) -> bytes:
    """A statement whose rows each name their own card, which is the shape
    of Criss's real corpserv export: one account id over the whole file and
    a Card column that spans four cards."""
    body = "".join(f"{d},{a},{v},{c}\n" for d, a, v, c in rows)
    return ("Date,Amount,Vendor,Card\n" + body).encode()


def _upload(client, batch_id, body: bytes, name="statement.csv", **data):
    form = {
        "account_id": "amex-9001",
        "account_legal_entities": '{"amex-9001": "Corporate Services"}',
        "account_card_currency": "USD",
        "map_transaction_date": "Date",
        "map_amount": "Amount",
        "map_vendor": "Vendor",
    }
    form.update({k: v for k, v in data.items() if v is not None})
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data=form,
    )
    assert resp.status_code == 200, resp.text
    done = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert done["status"] == "done", done
    return resp


def _coverage(client, batch_id) -> list[dict]:
    return client.get(f"/api/runs/{batch_id}").json()["coverage"]


def _by_label(coverage: list[dict]) -> dict[str, dict]:
    return {c["label"]: c for c in coverage}


def _run(client, batch_id):
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        return store.get_run(batch_id)


# ── 1. the grouping ─────────────────────────────────────────────────────


def test_two_cards_in_one_month_are_two_rows_that_sum_to_the_month(
    client, monkeypatch
):
    """The shape of the real corpserv export: one account, several cards.
    Flat it is one unreconciled figure; per card it says which plastic the
    missing receipts belong to."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
        ("2026-04-22", "31.10", "UBER", "3645"),
    ), map_card="Card")

    view = client.get(f"/api/runs/{batch_id}").json()
    rows = _by_label(view["coverage"])
    assert set(rows) == {"2838", "3645"}
    assert rows["3645"]["n_transactions"] == 2
    assert rows["2838"]["n_transactions"] == 1
    assert sum(c["n_transactions"] for c in view["coverage"]) == (
        view["summary"]["n_transactions"]
    )
    # The period is this CARD's span, not the month's.
    assert (rows["3645"]["period_start"], rows["3645"]["period_end"]) == (
        "2026-04-05", "2026-04-22",
    )
    assert (rows["2838"]["period_start"], rows["2838"]["period_end"]) == (
        "2026-04-03", "2026-04-03",
    )


def test_one_card_with_two_digit_identities_is_one_row(client, monkeypatch):
    """The design fact the whole registry exists for: the Chase statement
    marks charges "2838" while the plastic prints "1672", and they are one
    piece of plastic. Grouping on raw digits would report the month as two
    half-done cards."""
    _wire(monkeypatch)
    _cards(client, **{"corp-1672": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
        "entity": "Corporate Services",
    }})
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "1672"),
    ), map_card="Card")

    covered = [c for c in _coverage(client, batch_id) if c["n_transactions"]]
    assert len(covered) == 1, covered
    assert covered[0]["label"] == "Corporate card (Chase)"
    assert covered[0]["card_key"] == "corp-1672"
    assert covered[0]["known"] is True
    assert covered[0]["entity"] == "Corporate Services"
    assert covered[0]["n_transactions"] == 2


def test_a_card_the_registry_never_met_gets_its_own_row(client, monkeypatch):
    """Cards 3645 and 0340 are real charges on real plastic the registry is
    simply missing (backlog item 26). Folding them into an "other" bucket
    would bury the gap; a row of their own is what surfaces it."""
    _wire(monkeypatch)
    _cards(client, **{"corp-2838": {
        "label": "Corporate card (Chase)", "digits": ["2838"],
        "entity": "Corporate Services",
    }})
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
    ), map_card="Card")

    stranger = next(
        c for c in _coverage(client, batch_id) if c["label"] == "3645"
    )
    assert stranger["card_key"] == ""
    assert stranger["known"] is False
    assert stranger["digits"] == ["3645"]
    assert stranger["n_transactions"] == 1


def test_a_registry_card_with_nothing_loaded_still_has_a_row(
    client, monkeypatch
):
    """The whole point of the panel. "Which cards have statements" is only
    answerable from a list that includes the ones that do not."""
    _wire(monkeypatch)
    _cards(
        client,
        **{
            "corp-2838": {"label": "Corporate card", "digits": ["2838"],
                          "entity": "Corporate Services"},
            "travel-6013": {"label": "Travel card", "digits": ["6013"],
                            "entity": "Corporate Services"},
        },
    )
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), map_card="Card")

    rows = _by_label(_coverage(client, batch_id))
    assert "Travel card" in rows
    empty = rows["Travel card"]
    assert (empty["n_transactions"], empty["statements"]) == (0, [])
    assert empty["period_start"] is None
    assert empty["unreconciled_by_ccy"] == {}
    # ...and it sorts below the card that actually has charges.
    labels = [c["label"] for c in _coverage(client, batch_id)]
    assert labels.index("Corporate card") < labels.index("Travel card")


def test_a_month_with_no_statement_reports_no_coverage(client, monkeypatch):
    """Empty means "nothing loaded", which is the same thing `statements[]`
    says. A receipt-only month must not open with a column of registry cards
    it has no business asking about yet."""
    _wire(monkeypatch)
    _cards(client, **{"corp-2838": {"label": "Corporate card",
                                    "digits": ["2838"]}})
    batch_id = _batch(client)

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["coverage"] == []
    assert grid["statements"] == []
    assert client.get(f"/api/runs/{batch_id}").json()["coverage"] == []


def test_a_charge_naming_no_card_is_never_folded_into_one(
    client, monkeypatch
):
    """"Unknown card" is not "some card we already listed" — the same rule
    the matcher's `_tx_card_keys` states. A charge with no card-like digits
    anywhere gets the no-card row, with prose the SPA can render as-is."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")),
            account_id="corporate-amex",
            account_legal_entities='{"corporate-amex": "Corporate Services"}')

    covered = [c for c in _coverage(client, batch_id) if c["n_transactions"]]
    assert len(covered) == 1
    assert covered[0]["key"] == ""
    assert covered[0]["card_key"] == ""
    assert covered[0]["label"] == "No card on the charge"
    assert covered[0]["digits"] == []


def test_a_card_named_only_by_an_alias_still_resolves(client, monkeypatch):
    """Not every card-bearing string carries digits. Criss's Zoho payment
    modes name cards by word ("CorpServ"), and the registry holds aliases for
    exactly that. Falling straight to the no-card row on a digit-less string
    would put a named card's charges under "No card on the charge"."""
    _wire(monkeypatch)
    _cards(client, **{"corp": {
        "label": "Corporate card", "aliases": ["CorpServ"],
        "entity": "Corporate Services",
    }})
    batch_id = _batch(client)
    _upload(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")),
            account_id="CorpServ",
            account_legal_entities='{"CorpServ": "Corporate Services"}')

    covered = [c for c in _coverage(client, batch_id) if c["n_transactions"]]
    assert [c["label"] for c in covered] == ["Corporate card"]
    assert covered[0]["card_key"] == "corp"


def test_a_cards_slug_cannot_swallow_another_cards_charges(
    client, monkeypatch
):
    """Cards are keyed by an operator-chosen slug, and nothing stops that
    slug from being digits that are not the card's own. A charge on the REAL
    2838 must not land in a card merely KEYED "2838", or its money would be
    reported against the wrong plastic and the wrong entity."""
    _wire(monkeypatch)
    _cards(client, **{"2838": {
        "label": "A card keyed 2838 that is not card 2838",
        "digits": ["9999"], "entity": "Cloud Services",
    }})
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), map_card="Card")

    rows = _by_label(_coverage(client, batch_id))
    assert rows["A card keyed 2838 that is not card 2838"]["n_transactions"] == 0
    real = rows["2838"]
    assert (real["n_transactions"], real["card_key"], real["entity"]) == (1, "", "")


# ── 2. the joins: which uploads covered which card ──────────────────────


def test_each_card_names_the_upload_the_operator_loaded_it_from(
    client, monkeypatch
):
    """Per-card uploads are how the month is actually loaded. Each entry
    names its own files and not the other card's."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")),
            name="amex.csv", card_key="9001")
    _upload(client, batch_id, _csv(("2026-04-04", "80.00", "HERTZ")),
            name="chase.csv", card_key="2838", account_id="chase-2838",
            account_legal_entities='{"chase-2838": "Corporate Services"}')

    rows = _by_label(_coverage(client, batch_id))
    assert rows["amex-9001"]["statements"] == ["amex.csv"]
    assert rows["chase-2838"]["statements"] == ["chase.csv"]


def test_an_upload_covers_the_cards_it_actually_printed(client, monkeypatch):
    """The second join, and the one that carries the common case: an upload
    made through the plain form names no card preset at all, so the only
    thing that says which cards it covered is the rows it put in the month.
    Here one file covers two cards and says so."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
    ), name="cycle.csv", map_card="Card")

    rows = _by_label(_coverage(client, batch_id))
    assert rows["2838"]["statements"] == ["cycle.csv"]
    assert rows["3645"]["statements"] == ["cycle.csv"]


def test_a_partial_and_the_closing_cycle_both_count_for_the_card(
    client, monkeypatch
):
    """A card is loaded across files, which is the whole reason the coverage
    question exists. Both uploads are named against it, and the charge they
    share is counted once."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), name="partial.csv", map_card="Card")
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-22", "31.10", "UBER", "2838"),
    ), name="cycle.csv", map_card="Card")

    entry = next(c for c in _coverage(client, batch_id) if c["label"] == "2838")
    assert entry["statements"] == ["partial.csv", "cycle.csv"]
    assert entry["n_transactions"] == 2


# ── 3. one meaning: the grid and the workbench, and the reviewer ────────


def test_the_grid_and_the_workbench_report_the_same_coverage(
    client, monkeypatch
):
    """The month page and the reconciliation screen are two views of one
    month. Reporting it at two different stages of done is the
    `n_categorized` failure (docs/api-contract.md) with money on it."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-15", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
    ), map_card="Card")

    grid = client.get(f"/api/expense-batches/{batch_id}").json()["coverage"]
    workbench = client.get(f"/api/runs/{batch_id}").json()["coverage"]
    assert grid == workbench
    assert [c["label"] for c in grid] == ["2838", "3645"]


def test_rejecting_a_match_moves_the_charge_on_both_views(client, monkeypatch):
    """Coverage is the reviewer's EFFECTIVE state, not the matcher's first
    guess. A rejected match un-matches a charge, and a card row that ignored
    that would report the month as further along than it is."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-15", "42.50", "STAPLES", "2838"),
    ), map_card="Card")

    before = _coverage(client, batch_id)[0]
    assert (before["n_reconciled"], before["n_unmatched_tx"]) == (1, 0)
    assert before["unreconciled_by_ccy"] == {}

    tx_id = client.get(f"/api/runs/{batch_id}").json()["rows"][0]["transaction_id"]
    resp = client.post(f"/api/runs/{batch_id}/decisions",
                       json={"transaction_id": tx_id, "status": "rejected"})
    assert resp.status_code == 200, resp.text

    after = _coverage(client, batch_id)[0]
    assert (after["n_reconciled"], after["n_unmatched_tx"]) == (0, 1)
    assert after["unreconciled_by_ccy"] == {"USD": "42.50"}
    grid = client.get(f"/api/expense-batches/{batch_id}").json()["coverage"]
    assert grid == _coverage(client, batch_id)


# ── 4. nothing is lost ──────────────────────────────────────────────────


def test_every_charge_counts_in_exactly_one_card_row(client, monkeypatch):
    """The invariant that lets a reader add the card table up against the
    headline. Every row names a coverage entry, and the four bucket counters
    sum to the entry's own charge count the way the summary's do to the
    month's."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-15", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
        ("2026-04-22", "31.10", "UBER", "3645"),
    ), map_card="Card")

    view = client.get(f"/api/runs/{batch_id}").json()
    keys = {c["key"] for c in view["coverage"]}
    assert all(row["coverage_key"] in keys for row in view["rows"])
    for entry in view["coverage"]:
        assert entry["n_transactions"] == (
            entry["n_reconciled"] + entry["n_review"]
            + entry["n_unmatched_tx"] + entry["n_refunds"]
        ), entry
    summary = view["summary"]
    for name in ("n_transactions", "n_reconciled", "n_review",
                 "n_unmatched_tx", "n_refunds"):
        assert sum(c[name] for c in view["coverage"]) == summary[name], name


def test_a_cards_unreconciled_money_adds_up_to_the_months(
    client, monkeypatch
):
    """Same arithmetic as the summary's `unreconciled_by_ccy`, or the panel
    would quietly disagree with the headline it sits under."""
    _wire(monkeypatch, n=1)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "500.00", "NOTHING HERE", "2838"),
        ("2026-04-05", "250.00", "NOR HERE", "3645"),
    ), map_card="Card")

    view = client.get(f"/api/runs/{batch_id}").json()
    rows = _by_label(view["coverage"])
    assert rows["2838"]["unreconciled_by_ccy"] == {"USD": "500.00"}
    assert rows["3645"]["unreconciled_by_ccy"] == {"USD": "250.00"}
    assert view["summary"]["unreconciled_by_ccy"] == {"USD": "750.00"}


def test_coverage_survives_a_run_with_no_card_registry(client, monkeypatch):
    """A plain statement run, and every batch older than the card registry,
    carries no snapshot to resolve against. It still has to report coverage:
    on the real January month that degradation IS the useful answer, the
    three rows 2838 / 3645 / 0340."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-01-03", "42.50", "STAPLES", "2838"),
        ("2026-01-05", "12.00", "AWS", "3645"),
        ("2026-01-06", "8.00", "PARKING", "0340"),
    ), map_card="Card")

    run = _run(client, batch_id)
    assert not ((run.config or {}).get("expense") or {}).get("cards")
    assert sorted(c["label"] for c in _coverage(client, batch_id)) == [
        "0340", "2838", "3645",
    ]


# ── the document ────────────────────────────────────────────────────────


def test_the_document_sections_its_charges_per_card(client, monkeypatch):
    """Per-card sections in the reconciliation report. The grouping key
    comes off the row, so a section and the coverage table above it cannot
    disagree about which card a charge is on."""
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "3645"),
    ), map_card="Card")

    resp = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    path = Path(client._data_root) / "recon.pdf"
    path.write_bytes(resp.content)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    assert "Coverage by card" in text
    assert "2838" in text and "3645" in text


def test_a_one_card_month_keeps_the_one_flat_table(client, monkeypatch):
    """A one-card month is fully described by the headline already; a
    coverage table restating it would be a section the content does not
    support."""
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), map_card="Card")

    resp = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    path = Path(client._data_root) / "recon-one.pdf"
    path.write_bytes(resp.content)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    assert "Coverage by card" not in text
    assert "All charges" in text
