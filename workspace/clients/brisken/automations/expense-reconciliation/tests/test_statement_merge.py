"""Folding a statement upload into a month's charges (PR 2b-2b-1).

The foundation under gradual statement uploads: parse, content-id, dedupe.
A statement arrives in pieces now -- one card at a time, a mid-month partial
then the full cycle, the same file twice by accident -- so every upload
overlaps what the month already holds and the fold has to be by identity.

`merge_transactions` is that fold, and it is deliberately the ONLY new rule
here: sameness is `transaction_id`, which has been content-derived since
PR 2a. These tests pin the four properties the append route will lean on
(first-write-wins, `existing` untouched, occurrence counting across uploads,
a sign contradiction surfacing as two rows) and then prove the one-shot
attach actually runs through the same path rather than beside it.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.ingest._common import assign_content_ids, merge_transactions
from expense_recon.matching.types import Transaction

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _tx(vendor="STAPLES", amount="42.50", day=15, row=None, **kw):
    return Transaction(
        transaction_id="",
        legal_entity_id="Corporate Services",
        account_id="amex-9001",
        transaction_date=date(2026, 4, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        source_row=row,
        **kw,
    )


def _parse(*txs):
    """What a parser hands back: content ids stamped in file order."""
    return assign_content_ids(list(txs))


def test_the_same_file_uploaded_twice_adds_nothing():
    """The accident the append route exists to survive. Re-parsing one file
    reproduces its ids exactly, so the second upload is all duplicate."""
    first = _parse(_tx(), _tx(vendor="AWS", amount="12.00"))
    second = _parse(_tx(), _tx(vendor="AWS", amount="12.00"))

    merged = merge_transactions(first, second)

    assert merged.added == []
    assert len(merged.duplicates) == 2
    assert [t.transaction_id for t in merged.transactions] == [
        t.transaction_id for t in first
    ]


def test_a_partial_then_the_full_cycle_keeps_one_row_per_charge():
    """The real shape of a gradual upload: the mid-month partial's rows come
    back inside the full cycle, and only the charges after it are new."""
    partial = _parse(_tx(day=3), _tx(vendor="AWS", amount="12.00", day=5))
    full = _parse(
        _tx(day=3),
        _tx(vendor="AWS", amount="12.00", day=5),
        _tx(vendor="UBER", amount="31.10", day=22),
    )

    merged = merge_transactions(partial, full)

    assert len(merged.added) == 1
    assert len(merged.duplicates) == 2
    assert len(merged.transactions) == 3
    assert merged.transactions[-1].vendor_from_statement == "UBER"


def test_a_second_card_does_not_collide_with_the_first():
    """Per-card uploads are the point. `account_id` is part of identity, so
    an identical-looking charge on another card stays its own row."""
    amex = _parse(_tx())
    chase = _parse(replace(_tx(), account_id="chase-2838"))

    merged = merge_transactions(amex, chase)

    assert len(merged.added) == 1
    assert len(merged.transactions) == 2


def test_two_identical_coffees_survive_as_two_charges():
    """The occurrence suffix has to hold ACROSS uploads, not just within a
    parse: a month that already knows one coffee must still accept the
    second when the fuller file arrives."""
    one = _parse(_tx(vendor="COFFEE", amount="4.00"))
    two = _parse(
        _tx(vendor="COFFEE", amount="4.00"),
        _tx(vendor="COFFEE", amount="4.00"),
    )

    merged = merge_transactions(one, two)

    assert len(merged.added) == 1
    assert len(merged.duplicates) == 1
    assert len(merged.transactions) == 2
    assert len({t.transaction_id for t in merged.transactions}) == 2


def test_a_sign_contradiction_surfaces_as_two_rows():
    """Pinned deliberately in 2a and still the call: when two uploads
    disagree about which way the money went, the printed row gets two ids
    and BOTH land. Deduping would pick a winner arbitrarily."""
    charge = _parse(_tx(amount="42.50"))
    credit = _parse(_tx(amount="-42.50"))

    merged = merge_transactions(charge, credit)

    assert len(merged.added) == 1
    assert len(merged.transactions) == 2


def test_a_re_supplied_row_keeps_the_object_the_month_committed():
    """First-write-wins. Operator decisions and `source_row` key on the row
    already stored; a byte-equal copy parsed out of a different file would
    re-point `source_row` into the wrong workbook and buy nothing."""
    stored = _parse(_tx(row=2))
    reparsed = _parse(_tx(row=57))
    assert stored[0].transaction_id == reparsed[0].transaction_id

    merged = merge_transactions(stored, reparsed)

    assert len(merged.transactions) == 1
    assert merged.transactions[0].source_row == 2


def test_existing_passes_through_untouched():
    """The fold filters what an upload CONTRIBUTES; it never edits the
    month. Even an `existing` that repeats an id keeps both rows -- silently
    changing a month's charge count is not a merge's business."""
    one = _parse(_tx())[0]
    existing = [one, one]

    merged = merge_transactions(existing, _parse(_tx()))

    assert len(merged.transactions) == 2
    assert merged.added == []


def test_an_upload_that_repeats_itself_still_lands_once():
    """A parser cannot produce this (`assign_content_ids` counts
    occurrences), but the fold must not depend on that to stay sound."""
    one = _parse(_tx())[0]

    merged = merge_transactions([], [one, one])

    assert len(merged.transactions) == 1
    assert len(merged.added) == 1
    assert len(merged.duplicates) == 1


def test_an_empty_month_takes_the_upload_whole():
    """The degenerate case the one-shot attach runs: nothing to fold into,
    so the merged set IS the parse, in order."""
    parsed = _parse(_tx(day=3), _tx(vendor="AWS", amount="12.00"))

    merged = merge_transactions([], parsed)

    assert merged.transactions == parsed
    assert len(merged.added) == 2
    assert merged.duplicates == []


# ---------------------------------------------------------------------------
# Against the live service.
#
# Say plainly what these can and cannot prove. On the attach path `existing`
# is empty by construction -- `prepare_statement_attach` still refuses a
# second upload -- so the fold there IS the identity function, and no test
# can distinguish an attach that routes through it from one that does not.
# That inertness is the neutrality this round is meant to establish, not a
# wiring claim dressed up as one (the 2026-08-24 verification-theater row is
# exactly a suite that could not tell a shipped fix from an unwired one).
#
# So: the first test pins neutrality, the second exercises the fold against
# real stored charges rather than hand-built rows. The fold becomes
# load-bearing when the append route lands, and that round owns proving it.
# ---------------------------------------------------------------------------

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


def _wire(monkeypatch):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("42.50"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _batch(client):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": "April 2026"},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _attach(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    job_id = resp.json().get("job_id") if resp.status_code == 200 else None
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _stored_transactions(client, batch_id):
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {}).get("transactions") or []


def test_the_one_shot_attach_still_stores_exactly_what_the_file_held(
    client, monkeypatch
):
    """Neutrality. The attach now reads through `read_statement_upload` and
    folds into an empty month, and the month ends up holding the parse --
    same ids, same order. This is what makes the round a split rather than a
    rewrite; it does NOT prove the fold is wired (see the note above)."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    assert _attach(client, batch_id).status_code == 200

    stored = _stored_transactions(client, batch_id)
    parsed_ids = [
        t.transaction_id
        for t in _parse_example_statement(client, batch_id)
    ]
    assert [t["transaction_id"] for t in stored] == parsed_ids
    assert len(parsed_ids) == len(set(parsed_ids))


def _parse_example_statement(client, batch_id):
    """Read the same file the attach read, through the same loader and the
    config the attach itself stored, so the comparison above is against the
    real parse rather than against a copy of the expected answer (a test
    that asserts a constant does not bite)."""
    from expense_recon.cli import _load_statement

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    transactions, _ = _load_statement(run.config or {}, Path(run.work_dir))
    return transactions


def test_charges_the_month_already_holds_are_not_doubled(client, monkeypatch):
    """The property the append route is built on, proven against the live
    service rather than against hand-built rows: fold the month's own stored
    charges back in and nothing moves."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id)

    from expense_recon.web.serialize import snapshot_from_dict

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        stored, _, _, _ = snapshot_from_dict(store.get_run(batch_id).snapshot)

    assert stored
    merged = merge_transactions(stored, _parse_example_statement(client, batch_id))
    assert merged.added == []
    assert len(merged.transactions) == len(stored)
