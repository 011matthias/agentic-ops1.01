"""A receipt and its invoice with one document number: the receipt counts and
nobody is asked (backlog item 256, Dirk 2026-10-29, relayed by the owner: "if
duplicate set has same item ID number then default to receipt not invoice and
dont ask user for verification").

Three ways such a pair still reached a person on the live months:

- an invoice the tool's own match held stayed the kept copy at every later
  re-match (item 217 moved only groups no charge held; September 2026,
  ElevenLabs 5.00);
- the statement check split the pair into two purchases when the statement
  lists the charge twice (September 2026, card 9693's PDF and xlsx), putting
  both documents back in front of a reviewer;
- the set-aside invoice kept its own review prompt and counted in
  `n_review` (October 2026: 4 of 27).

A PERSON's confirmed pick of the invoice still keeps it, and "Not a copy"
still outranks the tool.
"""
from __future__ import annotations

import io
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    BASIS_REFERENCE,
    BASIS_VENDOR_DATE,
    DECIDED_BY_TOOL,
    STATE_DECIDED,
    VERDICT_COPY,
    ReceiptGroupDecision,
    choose_kept,
    is_number_pair,
    number_settled_copies,
    with_kept_first,
)
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import SELF_CONFIRM_RULE  # noqa: E402
from expense_recon.web.store import STATUS_CONFIRMED, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
PAYMENT = (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16)
CHARGE = (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(reference):
    return ExtractedReceipt(
        date="2026-08-31", total="15.00", currency="USD",
        vendor="Lovable Labs Incorporated", reference=reference, line_items=(),
        confidence=0.9, notes="", payment_hint=None,
    )


def _wire(monkeypatch, reference):
    mock = MockLLMClient(
        extraction_responses=[_extraction(reference), _extraction(reference)],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("15.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, *, charges=(CHARGE,), reference="HMVWDWIL-0029"):
    """Stripe's order: the invoice arrives first, so it sorts first. Both
    documents read the invoice's number, as a Stripe receipt prints it."""
    _wire(monkeypatch, reference)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "August 2026"})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("Invoice-HMVWDWIL-0029.jpg", JPG + b"1", "application/octet-stream")),
            ("files", ("Receipt-2167-5718.jpg", JPG + b"2", "application/octet-stream")),
        ],
    ))
    if charges:
        wb = Workbook()
        ws = wb.active
        ws.append(list(HEADERS))
        for row in (*charges, PAYMENT):
            ws.append(list(row))
        buf = io.BytesIO()
        wb.save(buf)
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/statement",
            files={"statement": (
                "August2026.xlsx", buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )},
            data={
                "account_id": "card-2838",
                "account_legal_entities": '{"card-2838": "Corporate Services"}',
                "account_card_currency": "USD",
            },
        ))
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _pair(grid):
    inv = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    rec = next(e for e in grid["expenses"] if "Receipt-" in e["document_id"])
    return inv, rec


def _rematch(client, batch_id):
    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text


def test_the_pair_is_one_group_by_its_number(client, monkeypatch):
    batch_id = _month(client, monkeypatch)
    (group,) = _run(client, batch_id)["duplicate_groups"]
    assert (group["basis"], group["verdict"], group["decided_by"]) == (
        BASIS_REFERENCE, VERDICT_COPY, DECIDED_BY_TOOL)


def test_an_invoice_the_tools_own_match_holds_gives_way_to_its_receipt(client, monkeypatch):
    """The ElevenLabs shape: the tool confirmed the charge onto the INVOICE
    (a month matched before item 217, or an invoice paired first). Before
    item 256 that hold kept the invoice at every re-match; now the receipt
    is the real expense and the invoice the copy."""
    batch_id = _month(client, monkeypatch)
    tx_id = next(r for r in _run(client, batch_id)["rows"] if r["vendor"] == "LOVABLE")["transaction_id"]
    invoice_id = _pair(_grid(client, batch_id))[0]["document_id"]
    db = Path(client._data_root) / "recon-web.sqlite"
    with RunStore(db) as store:
        assert store.set_tool_decision(
            batch_id, tx_id, STATUS_CONFIRMED, invoice_id,
            datetime.now(timezone.utc).isoformat(timespec="seconds"), SELF_CONFIRM_RULE,
        )

    _rematch(client, batch_id)

    run = _run(client, batch_id)
    (aside,) = run["copies_set_aside"]
    assert "Invoice-" in aside["document_id"], "the invoice is the copy"
    row = next(r for r in run["rows"] if r["vendor"] == "LOVABLE")
    assert "Receipt-" in (row["chosen_document_id"] or ""), row
    inv, rec = _pair(_grid(client, batch_id))
    assert rec["duplicate"]["is_extra"] is False
    assert inv["duplicate"]["is_extra"] is True
    assert inv["counts_in_total"] is False
    assert _grid(client, batch_id)["summary"]["totals_by_ccy"] == {"USD": "15.00"}


def test_a_persons_pick_of_the_invoice_still_stands(client, monkeypatch):
    """A reviewer matched the charge to the invoice by hand. Moving that
    would leave her decision naming a set-aside copy and count both."""
    batch_id = _month(client, monkeypatch)
    tx_id = next(r for r in _run(client, batch_id)["rows"] if r["vendor"] == "LOVABLE")["transaction_id"]
    invoice_id = _pair(_grid(client, batch_id))[0]["document_id"]
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": tx_id, "document_id": invoice_id},
    )
    assert resp.status_code == 200, resp.text

    _rematch(client, batch_id)

    run = _run(client, batch_id)
    row = next(r for r in run["rows"] if r["vendor"] == "LOVABLE")
    assert row["chosen_document_id"] == invoice_id
    (aside,) = run["copies_set_aside"]
    assert "Receipt-" in aside["document_id"]
    assert _grid(client, batch_id)["summary"]["totals_by_ccy"] == {"USD": "15.00"}


def test_a_second_statement_line_does_not_split_the_pair(client, monkeypatch):
    """The Anthropic shape: the statement lists the same amount twice on the
    day. The statement check used to call the invoice a second purchase and
    match it to the second line; one number is one purchase, so the receipt
    holds one charge and the other line waits for its own receipt."""
    batch_id = _month(client, monkeypatch, charges=(CHARGE, CHARGE))

    run = _run(client, batch_id)
    (group,) = run["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_REFERENCE, VERDICT_COPY)
    (aside,) = run["copies_set_aside"]
    assert "Invoice-" in aside["document_id"]
    assert run["summary"]["n_reconciled"] == 1
    assert run["summary"]["n_duplicate_copies"] == 1


def test_the_set_aside_invoice_asks_nothing(client, monkeypatch):
    """No statement: the rule applies as the page is read. The invoice copy
    is out of `n_review`; the receipt keeps whatever its own row needs."""
    batch_id = _month(client, monkeypatch, charges=())
    grid = _grid(client, batch_id)
    inv, rec = _pair(grid)
    assert inv["counts_in_total"] is False
    assert inv["review"]["state"] == "none"
    asking = [
        e for e in grid["expenses"] if e["review"]["state"] in ("check", "pick")
    ]
    assert inv not in asking
    assert grid["summary"]["n_review"] == len(asking)


def test_two_scans_with_no_number_still_ask_as_before(client, monkeypatch):
    """A vendor/date copy is not settled by a number: its copy row keeps its
    review state (the change is scoped to one-number pairs)."""
    batch_id = _month(client, monkeypatch, charges=(), reference="")
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["basis"] == BASIS_VENDOR_DATE
    inv, _rec = _pair(grid)
    assert inv["counts_in_total"] is False
    assert inv["review"]["state"] != "none"


# ── the rule itself ─────────────────────────────────────────────────────


def _r(doc, total="5.00", **kw):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 9, 10),
        detected_total=Decimal(total) if total is not None else None,
        detected_currency="USD", detected_vendor="ElevenLabs", **kw,
    )


def _decision(members, basis=BASIS_REFERENCE):
    return ReceiptGroupDecision(
        members=tuple(members), group_id="g", basis=basis,
        tool_verdict=VERDICT_COPY, resolution=None, verdict=VERDICT_COPY,
        decided_by=DECIDED_BY_TOOL, state=STATE_DECIDED,
    )


INV, REC = "0019__Invoice-214D91B6-0006.pdf", "0020__Receipt-2459-0337-0793.pdf"


@pytest.mark.parametrize(
    ("receipts", "basis", "expected"),
    [
        ([_r(INV), _r(REC)], BASIS_REFERENCE, True),
        ([_r(INV), _r(REC)], "intake_twin", True),
        ([_r(INV), _r(REC)], "printed_reference", True),
        ([_r(INV), _r(REC)], "reference_digits", True),
        # not found by a number
        ([_r(INV), _r(REC)], BASIS_VENDOR_DATE, False),
        ([_r(INV), _r(REC)], "misread_digit", False),
        # two receipts, two invoices: nothing to prefer
        ([_r("0001__Receipt-a.pdf"), _r("0002__Receipt-b.pdf")], BASIS_REFERENCE, False),
        ([_r("0001__Invoice-a.pdf"), _r("0002__Invoice-b.pdf")], BASIS_REFERENCE, False),
        # amounts differ or unread
        ([_r(INV, total="50.00"), _r(REC)], "printed_reference", False),
        ([_r(INV, total=None), _r(REC, total=None)], "printed_reference", False),
        # a document that says neither
        ([_r(INV), _r(REC), _r("0021__scan.jpg")], BASIS_REFERENCE, False),
    ],
)
def test_is_number_pair(receipts, basis, expected):
    by_id = {r.document_id: r for r in receipts}
    assert is_number_pair(_decision([r.document_id for r in receipts], basis), by_id) is expected


def test_choose_kept_over_a_number_pair():
    receipts = [_r(INV), _r(REC)]
    d = _decision([INV, REC])
    # the tool's match holds the invoice: the receipt wins
    assert choose_kept([d], receipts, held={INV}, pinned=set()) == {"g": REC}
    # a person pinned the invoice: it stays
    assert choose_kept([d], receipts, held={INV}, pinned={INV}) == {"g": INV}
    # a caller that cannot tell people from the tool: item 217 as before
    assert choose_kept([d], receipts, held={INV}) == {"g": INV}
    # not a number pair: the hold decides, as before
    vd = _decision([INV, REC], basis=BASIS_VENDOR_DATE)
    assert choose_kept([vd], receipts, held={INV}, pinned=set()) == {"g": INV}


def test_a_mail_body_beside_a_number_pair_follows_the_pair():
    body = Receipt(
        document_id="0047__rendered-body.pdf", legal_entity_id="",
        detected_date=date(2026, 9, 10), detected_total=Decimal("5.00"),
        detected_currency="USD", detected_vendor="ElevenLabs",
    )
    receipts = [_r(INV), _r(REC), body]
    pair = _decision([INV, REC])
    with_body = ReceiptGroupDecision(
        members=(INV, REC, body.document_id), group_id="b", basis="body_twin",
        tool_verdict=VERDICT_COPY, resolution=None, verdict=VERDICT_COPY,
        decided_by=DECIDED_BY_TOOL, state=STATE_DECIDED,
    )
    kept = choose_kept([pair, with_body], receipts, held={INV}, pinned=set())
    assert kept == {"g": REC, "b": REC}
    ordered = with_kept_first([pair, with_body], kept)
    assert number_settled_copies(ordered, receipts) == {INV, body.document_id}
