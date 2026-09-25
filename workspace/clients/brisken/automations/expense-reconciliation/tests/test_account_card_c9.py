"""A receipt with no card takes the card its billing account has always been
paid with (backlog item 204, step 4; owner decision D4, 2026-09-25).

The account is the Stripe customer prefix of the invoice number
(`WWT1PNYP-0016` -> `WWT1PNYP`). Its card is derived on every read from the
account's OTHER purchases: at least two on one card, none on any other.
Printed numbers, statement charges and reviewer picks count; two-digit
endings may only contradict; remembered and merchant cards are no evidence.

Pinned route-level, through `GET /api/expense-batches/{id}`:

* two earlier purchases printed on one card carry a third, card-less one,
  with the card's company and person (`card_source: "account"`), and the
  CSV, the card tabs and `/api/cards/status` say the same;
* an account seen on two cards, one purchase of evidence, a pick on a
  sibling (D6), two copies of one purchase, two-digit endings and an
  all-digit number all decide nothing;
* a printed number, a pick and the settling charge each outrank it;
* publishing never teaches an account-carded row to the merchant registry.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.billing_account import account_key, decide  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-c9-4"

CARDS = {
    "3876": {
        "label": "Nicolas card",
        "digits": ["3876"],
        "entity": "Corporate Services",
        "person": "Nicolas Neumann",
        "zoho_account": "Chase 3876",
    },
    "3645": {
        "label": "Dirk card",
        "digits": ["3645"],
        "entity": "Corporate Services",
        "person": "Dirk Neumann",
        "zoho_account": "Chase 3645",
    },
    "card-9693": {
        "label": "Cloud card",
        "digits": ["9693"],
        "entity": "Cloud Services",
        "person": "Criss",
        "zoho_account": "Chase 9693",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.put("/api/settings", json={"cards": CARDS}).status_code == 200
        yield c


def _ff(invoice: str | None, *, hint: str | None = None, day: str = "2026-07-10",
        total: str = "18.00", vendor: str = "Fireflies.ai Corp",
        reference: str = "") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=hint, invoice_number=invoice,
    )


_SEQ = [0]


def _month(client, monkeypatch, label: str, *extractions) -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"c9-4-{_SEQ[0]}.jpg",
                                JPG + bytes([_SEQ[0] % 256, 7]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, batch_id) -> list[dict]:
    return _grid(client, batch_id)["expenses"]


def _only(client, batch_id) -> dict:
    rows = _rows(client, batch_id)
    assert len(rows) == 1, [(e["vendor"]["display"], e["total"]) for e in rows]
    return rows[0]


def _pick(client, batch_id, doc, key) -> None:
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": "card_key", "value": key}
    )
    assert resp.status_code == 200, resp.text


def _july_on_3876(client, monkeypatch, account: str = "HQXED19R") -> str:
    """Two earlier purchases of the account, each printing card 3876."""
    return _month(
        client, monkeypatch, "July 2026",
        _ff(f"{account}-0007", hint="Visa ...3876", day="2026-07-10"),
        _ff(f"{account}-0008", hint="Visa ...3876", day="2026-07-24", total="5.00"),
    )


def _blank(row: dict) -> None:
    assert row["card"] is None and row["card_source"] == "none", row["card_source"]
    assert row["person"] == ""


# ── the rule ───────────────────────────────────────────────────────────


def test_two_purchases_on_one_card_carry_a_third_that_prints_none(client, monkeypatch):
    """Fireflies' account HQXED19R was paid with 3876 in July, twice, and on
    no other card; May's receipt of the same account prints nothing and
    takes 3876, with the card's company and person."""
    _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    row = _only(client, may)
    assert row["card_source"] == "account"
    assert row["card"]["key"] == "3876"
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["entity_source"] == "card"
    assert row["person"] == "Nicolas Neumann" and row["person_source"] == "card"
    # Memory about the account, not a decision about the row.
    assert row["can_mark_private"] is True
    assert row["suggested_private"] is False
    # The card tabs file it where the grid shows it.
    assert row["card_section"] == "3876"


def test_the_account_is_read_off_the_reference_when_no_invoice_number(client, monkeypatch):
    """The reference field stores the number without its dash
    (`WWT1PNYP0012` on the live May row); it keys the account the same way."""
    _july_on_3876(client, monkeypatch, account="WWT1PNYP")
    may = _month(client, monkeypatch, "May 2026",
                 _ff(None, reference="WWT1PNYP0012", day="2026-05-03",
                     vendor="Anthropic"))

    row = _only(client, may)
    assert row["card_source"] == "account"
    assert row["card"]["key"] == "3876"


def test_the_csv_and_the_cards_overview_name_the_account_card(client, monkeypatch):
    """Every surface with live settings resolves the same link: the Zoho CSV
    books the row to the card's account, and the cross-month card roll-up
    lists May among the months holding a receipt on 3876."""
    _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))
    assert _only(client, may)["card_source"] == "account"

    csv_text = client.get(f"/runs/{may}/expenses.csv")
    assert csv_text.status_code == 200, csv_text.text
    assert "Chase 3876" in csv_text.text

    status = client.get("/api/cards/status")
    assert status.status_code == 200, status.text
    card = next(c for c in status.json()["cards"] if c["key"] == "3876")
    assert may in {m.get("run_id") for m in card["receipt_months"]}, card["receipt_months"]


# ── what decides nothing ───────────────────────────────────────────────


def test_an_account_seen_on_two_cards_stays_blank(client, monkeypatch):
    """Accounts do switch cards (DZ9BH3VA went 3645 -> 1176): two cards in the
    evidence means the tool cannot say which one paid."""
    _july_on_3876(client, monkeypatch)
    _month(client, monkeypatch, "August 2026",
           _ff("HQXED19R-0009", hint="Visa ...9693", day="2026-08-10"))
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_one_purchase_of_evidence_decides_nothing(client, monkeypatch):
    _month(client, monkeypatch, "July 2026",
           _ff("HQXED19R-0007", hint="Visa ...3876"))
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_a_pick_on_one_row_does_not_reach_its_siblings(client, monkeypatch):
    """Owner D6 (September's OpenAI rows): Criss's pick stays on its own row,
    and the rows beside it keep the no-payment-info logic. One pick is one
    purchase of evidence, which decides nothing."""
    september = _month(
        client, monkeypatch, "September 2026",
        _ff("58596F4C-0063", day="2026-09-03", total="80.20", vendor="OpenAI"),
        _ff("58596F4C-0064", day="2026-09-07", total="80.04", vendor="OpenAI"),
        _ff("58596F4C-0065", day="2026-09-11", total="80.24", vendor="OpenAI"),
    )
    rows = _rows(client, september)
    _pick(client, september, rows[0]["document_id"], "3645")

    after = {e["document_id"]: e for e in _rows(client, september)}
    assert after[rows[0]["document_id"]]["card_source"] == "override"
    for sibling in rows[1:]:
        _blank(after[sibling["document_id"]])


def test_two_copies_of_one_purchase_count_once(client, monkeypatch):
    """The invoice and its receipt print the same invoice number: one
    purchase, however many copies arrive and in whichever month."""
    _month(client, monkeypatch, "July 2026",
           _ff("HQXED19R-0007", hint="Visa ...3876"))
    _month(client, monkeypatch, "August 2026",
           _ff("HQXED19R-0007", hint="Visa ...3876", day="2026-08-02",
               vendor="Fireflies.ai"))
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_a_card_printed_only_on_the_decided_copy_still_counts(client, monkeypatch):
    """The live shape of v237's wrong card (2026-09-25): a Stripe invoice
    prints no card, its receipt prints 3645 and is ruled the copy, so the
    card sits only on the document that does not count. That purchase still
    names 3645, which contradicts July's 3876, so May's invoice stays blank.
    Reading only the kept copies lent May 3876."""
    _july_on_3876(client, monkeypatch)
    september = _month(
        client, monkeypatch, "September 2026",
        _ff("HQXED19R-0009", day="2026-09-10", reference="HQXED19R-0009"),
        _ff("HQXED19R-0009", hint="Visa ...3645", day="2026-09-10",
            reference="HQXED19R-0009"),
    )
    rows = _rows(client, september)
    # Not vacuous: one copy is set aside, and the card is on a copy.
    assert sorted(str(e.get("counts_in_total")) for e in rows) == ["False", "None"], rows
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_two_digit_endings_never_count(client, monkeypatch):
    """"last two digits: 76" names card 3876 on the row (item 199) but is
    weaker than a number; it may not establish an account's card."""
    july = _month(
        client, monkeypatch, "July 2026",
        _ff("HQXED19R-0007", hint="last two digits: 76", day="2026-07-10"),
        _ff("HQXED19R-0008", hint="last two digits: 76", day="2026-07-24",
            total="5.00"),
    )
    # Not vacuous: both July rows really are on 3876, named by the ending.
    for row in _rows(client, july):
        assert row["card"]["key"] == "3876" and row["card_ending"] == "76", row
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_a_hint_word_assigned_to_a_card_never_counts(client, monkeypatch):
    """Criss assigning "Link" to 3876 on the card strip says which card that
    word means in that month; it is not the card printed on the invoice."""
    july = _month(
        client, monkeypatch, "July 2026",
        _ff("HQXED19R-0007", hint="Link", day="2026-07-10"),
        _ff("HQXED19R-0008", hint="Link", day="2026-07-24", total="5.00"),
    )
    resp = client.post(
        f"/api/expense-batches/{july}/cards",
        json={"assignments": [{"hint": "Link", "card": "3876"}], "learn": False},
    )
    assert resp.status_code == 200, resp.text
    for row in _rows(client, july):
        assert row["card"]["key"] == "3876" and row["card_source"] == "hint", row
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_a_two_digit_ending_on_another_card_contradicts(client, monkeypatch):
    _july_on_3876(client, monkeypatch)
    _month(client, monkeypatch, "August 2026",
           _ff("HQXED19R-0009", hint="last two digits: 93", day="2026-08-10"))
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))

    _blank(_only(client, may))


def test_an_all_digit_number_is_not_an_account(client, monkeypatch):
    """A Stripe RECEIPT number (`2642-9215-3921`) and any other number whose
    prefix is all digits say nothing about the account."""
    _month(
        client, monkeypatch, "July 2026",
        _ff("12345678-0001", hint="Visa ...3876", day="2026-07-10"),
        _ff("12345678-0002", hint="Visa ...3876", day="2026-07-24", total="5.00"),
    )
    may = _month(client, monkeypatch, "May 2026",
                 _ff("12345678-0003", day="2026-05-12"))

    _blank(_only(client, may))
    assert account_key(_Doc("2642-9215-3921")) is None
    assert account_key(_Doc("12345678-0003")) is None
    assert account_key(_Doc("WWT1PNYP-0016")) == ("WWT1PNYP", "WWT1PNYP0016")
    assert account_key(_Doc(None, "HMVWDWIL0023")) == ("HMVWDWIL", "HMVWDWIL0023")


class _Doc:
    def __init__(self, invoice, reference=None):
        self.invoice_number = invoice
        self.detected_reference = reference


def test_an_unreadable_batch_empties_the_whole_index(monkeypatch):
    """Evidence missing from one month can hide the card that contradicts
    another's, so a partial index is never used: the link goes silent."""
    from types import SimpleNamespace

    from expense_recon import billing_account
    from expense_recon.web.service import MODE_EXPENSE_GENERATION

    runs = [SimpleNamespace(run_id=rid, label=label,
                            config={"mode": MODE_EXPENSE_GENERATION})
            for rid, label in (("jul", "July 2026"), ("sep", "September 2026"))]
    store = SimpleNamespace(
        db_path="unreadable-batch-fake",
        list_runs=lambda: runs,
        get_run=lambda rid: next(r for r in runs if r.run_id == rid),
        run_inputs_digest=lambda rid: rid,
        get_expense_field_overrides=lambda rid: {},
        get_expense_edits=lambda rid: [],
        get_decisions=lambda rid: {},
        get_duplicate_resolutions=lambda rid: {},
    )

    def evidence(run, **_kw):
        if run.run_id == "sep":
            raise ValueError("unreadable snapshot")
        return [("HQXED19R", "HQXED19R0007", "3876", True),
                ("HQXED19R", "HQXED19R0008", "3876", True)]

    monkeypatch.setattr(billing_account, "month_evidence", evidence)
    assert billing_account.build_account_index(store) == {}


def test_a_month_is_re_derived_only_after_its_own_rows_change(client, monkeypatch):
    """Live 2026-09-25 every request re-derived every month (~28 s a page).
    A month's evidence is reused while its rows are unchanged, and a write
    to that month (here a pick) re-derives it, and only it, so the answer
    still follows the data: two cards in the evidence blank May's row."""
    from expense_recon import billing_account

    july = _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))
    derived: list[str] = []
    real = billing_account.month_evidence

    def counting(run, **kw):
        derived.append(run.run_id)
        return real(run, **kw)

    monkeypatch.setattr(billing_account, "month_evidence", counting)
    assert _only(client, may)["card"]["key"] == "3876"
    assert _only(client, may)["card_source"] == "account"
    derived.clear()

    assert _only(client, may)["card"]["key"] == "3876"
    assert derived == [], "nothing changed, so nothing is re-derived"

    first = next(e for e in _rows(client, july) if e["total"] == "18.00")
    _pick(client, july, first["document_id"], "card-9693")
    _blank(_only(client, may))
    assert set(derived) == {july}, derived


def test_the_judged_purchase_is_left_out_of_its_own_evidence():
    """Leave-one-out: a purchase never votes for itself."""
    purchases = {
        "A0000001X0001": (frozenset({"3876"}), frozenset()),
        "A0000001X0002": (frozenset({"3876"}), frozenset()),
    }
    assert decide(purchases, "A0000001X0003") == "3876"
    assert decide(purchases, "A0000001X0002") is None


# ── what outranks it ───────────────────────────────────────────────────


def test_a_printed_number_outranks_the_account_card(client, monkeypatch):
    _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", hint="Visa ...9693", day="2026-05-12"))

    row = _only(client, may)
    assert row["card_source"] == "hint"
    assert row["card"]["key"] == "card-9693"


def test_a_pick_outranks_the_account_card(client, monkeypatch):
    _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))
    doc = _only(client, may)["document_id"]
    assert _only(client, may)["card_source"] == "account"

    _pick(client, may, doc, "card-9693")
    row = _only(client, may)
    assert row["card_source"] == "override"
    assert row["card"]["key"] == "card-9693"


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_the_settling_charge_outranks_the_account_card(client, monkeypatch):
    """The statement is the truth: a charge on 9693 that settles the receipt
    names its card, whatever the account's history says."""
    _july_on_3876(client, monkeypatch)
    august = _month(client, monkeypatch, "August 2026",
                    _ff("HQXED19R-0009", day="2026-08-12"))
    assert _only(client, august)["card_source"] == "account"

    resp = client.post(
        f"/api/expense-batches/{august}/statement",
        files={"statement": (
            "August2026.xlsx",
            _xlsx([("9693", datetime(2026, 8, 12), "FIREFLIES.AI", "Sale", -18.00)]),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-9693",
            "account_legal_entities": '{"card-9693": "Cloud Services"}',
            "account_card_currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    charge = next(r for r in client.get(f"/api/runs/{august}").json()["rows"]
                  if r["vendor"] == "FIREFLIES.AI")
    assert charge["effective_bucket"] == "reconciled", charge

    row = _only(client, august)
    assert row["card_source"] == "settled_charge"
    assert row["card"]["key"] == "card-9693"
    assert row["person"] == "Criss"


# ── memory stays memory ────────────────────────────────────────────────


def test_publishing_never_teaches_an_account_carded_row(client, monkeypatch):
    """The sign-off learner reads observations only (`_CARD_OBSERVATION_SOURCES`:
    override, hint, settled_charge). A card the account rule lent is derived,
    never memorized, so signing off May leaves Fireflies' registry entry with
    no card seen. (`learned` is pinned the same way by
    `test_signing_off_a_remembered_card_teaches_the_registry_nothing`.)"""
    merchants = {"Fireflies": {
        "aliases": ["Fireflies.ai Corp", "Fireflies"],
        "category": None, "zoho_account": None,
    }}
    assert client.put("/api/settings", json={"merchants": merchants}).status_code == 200
    _july_on_3876(client, monkeypatch)
    may = _month(client, monkeypatch, "May 2026",
                 _ff("HQXED19R-0004", day="2026-05-12"))
    assert _only(client, may)["card_source"] == "account"

    resp = client.post(f"/api/runs/{may}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    entry = client.get("/api/settings").json()["merchants"]["Fireflies"]
    assert "3876" not in (entry.get("cards_seen") or []), entry
    assert "card_key" not in entry, entry
