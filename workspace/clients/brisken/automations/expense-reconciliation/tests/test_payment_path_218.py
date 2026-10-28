"""Build 4 / backlog item 218 (owner decisions 2026-09-25): the pure rules in
`payment_path`, which row takes the bill path and why.

The negative cases are the contract. A card receipt, a transfer that names
its card, the Brazilian card terminal's TEF, an invoice's payment OFFER and a
reminder that only says "remittance" must all stay on the card path, because
a bill leaves the card counts and the month's total by itself. All values
here are synthetic TEST data: no real account number, IBAN, SWIFT/ABA code
or supplier text.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from expense_recon import payment_path as pp


@dataclass
class _R:
    document_id: str
    payment_mode: str | None = None
    ocr_text: str = ""


# ── stated_bank_payment: the automatic trigger ──────────────────────────


@pytest.mark.parametrize("mode", [
    "Wire Transfer",
    "Payment Method: Wire Transfer",
    "Bank transfer",
    "Paid by electronic funds transfer",
    "Transferência bancária",
    "Transferencia",
    "Überweisung",
    "SEPA",
    "ACH",
    "Virement bancaire",
    "Bonifico",
    "Boleto",
    "PIX",
    "wire",
])
def test_a_stated_bank_payment_takes_the_bill_path(mode):
    assert pp.stated_bank_payment(mode) == mode
    assert pp.resolve_payment_path(
        override=None, settled_entry=None, payment_mode=mode,
        held_by_charge=False,
    ) == (pp.PATH_BILL, pp.SOURCE_STATED)


@pytest.mark.parametrize("mode", [
    "",
    None,
    # a transfer that names the card it posted to
    "Electronic Funds Transfer ...2838",
    "Visa ...3645",
    "Mastercard",
    "Cartão de crédito",
    "Débito",
    # the Brazilian card terminal, not a bank transfer
    "TEF",
    # an invoice's payment OFFER: a suggestion, never a move
    "Pay $15.00 with a bank transfer",
    "Pay by bank transfer",
    "Cash",
    "PayPal",
])
def test_everything_else_stays_on_the_card(mode):
    assert pp.stated_bank_payment(mode) is None
    assert pp.resolve_payment_path(
        override=None, settled_entry=None, payment_mode=mode,
        held_by_charge=False,
    ) == (pp.PATH_CARD, pp.SOURCE_NONE)


def test_stated_is_a_superset_of_the_services_bank_transfer_tender():
    """The docstring's promise: every mode the settled-outside chip reads as
    a bank transfer (minus an offer) is a stated bank payment here too, so
    the two screens cannot route one string two ways."""
    from expense_recon.web.service import bank_transfer_tender

    for mode in (
        "Wire Transfer", "Bank transfer", "Electronic funds transfer",
        "Transferência", "Überweisung", "SEPA", "ACH", "Virement", "Bonifico",
        "TEF", "Electronic Funds Transfer ...2838", "Visa", "",
    ):
        if bank_transfer_tender(mode):
            assert pp.stated_bank_payment(mode), mode


def test_the_card_token_rule_is_the_services_own():
    from expense_recon.web.service import _CARD_TOKEN_RE

    assert pp._CARD_TOKEN_RE.pattern == _CARD_TOKEN_RE.pattern
    assert pp._CARD_TOKEN_RE.flags == _CARD_TOKEN_RE.flags


# ── printed_bank_details: the suggestion ────────────────────────────────


@pytest.mark.parametrize("text", [
    "Please pay to:\nIBAN LU00 TEST 0000 0000 0000\nThank you",
    "Account LU00TEST000000000000",
    "SWIFT Code for International Wires: TESTUS33",
    "BIC: TESTDEFF",
    "ABA No. for Wire Transfers: 000000000",
    "Routing Number ACH Transfer: 000000000",
    "Bank Account Number: 0000000000",
    "Bankverbindung: Testbank",
    "Dados bancários: Banco Teste",
])
def test_printed_bank_details_are_found(text):
    hit = pp.printed_bank_details(text)
    assert hit
    assert len(hit) <= pp.EVIDENCE_MAX
    assert "\n" not in hit


@pytest.mark.parametrize("text", [
    "",
    # the Redis reminder's shape: "remittance" alone never fires
    "Our records show that the following invoice remains unpaid.\n"
    "Please send payment remittance to the address below.",
    # an ordinary card receipt
    "LOVABLE LABS\nVisa ending 3645\nTotal 25.00 USD\nThank you",
    # a German VAT id is not an IBAN
    "USt-IdNr. DE123456789",
])
def test_ordinary_documents_print_no_bank_details(text):
    assert pp.printed_bank_details(text) is None


def test_the_evidence_is_the_first_matching_line_trimmed():
    text = "Invoice 1\n" + "IBAN " + "LU00 TEST 0000 0000 0000 " * 10
    hit = pp.printed_bank_details(text)
    assert hit.startswith("IBAN LU00 TEST")
    assert len(hit) == pp.EVIDENCE_MAX


# ── precedence ──────────────────────────────────────────────────────────


def test_a_charge_that_holds_the_receipt_wins_over_everything():
    for override in (None, "bill", "card"):
        assert pp.resolve_payment_path(
            override=override, settled_entry={"how": "bank_transfer"},
            payment_mode="Wire Transfer", held_by_charge=True,
        ) == (pp.PATH_CARD, pp.SOURCE_STATEMENT)


def test_a_person_wins_over_the_disposition_and_the_document():
    assert pp.resolve_payment_path(
        override="card", settled_entry={"how": "bank_transfer"},
        payment_mode="Wire Transfer", held_by_charge=False,
    ) == (pp.PATH_CARD, pp.SOURCE_PERSON)
    assert pp.resolve_payment_path(
        override="bill", settled_entry=None, payment_mode="Visa ...3645",
        held_by_charge=False,
    ) == (pp.PATH_BILL, pp.SOURCE_PERSON)


def test_only_a_bank_transfer_disposition_makes_a_bill():
    assert pp.resolve_payment_path(
        override=None, settled_entry={"how": "bank_transfer"},
        payment_mode="", held_by_charge=False,
    ) == (pp.PATH_BILL, pp.SOURCE_SETTLED_OUTSIDE)
    for how in ("cash", "paypal", "other"):
        assert pp.resolve_payment_path(
            override=None, settled_entry={"how": how},
            payment_mode="", held_by_charge=False,
        ) == (pp.PATH_CARD, pp.SOURCE_NONE)


def test_an_unknown_override_value_is_no_override():
    assert pp.normalize_override("Bill") == "bill"
    assert pp.normalize_override("sometimes") == ""
    assert pp.normalize_override(None) == ""


# ── the month: effective and displayed maps ─────────────────────────────


def test_the_effective_map_adds_bills_and_drops_an_overruled_disposition():
    receipts = [
        _R("stated", "Wire Transfer"),
        _R("settled"),
        _R("moved_back"),
        _R("cash"),
        _R("plain", "Visa ...3645"),
    ]
    stored = {
        "settled": {"how": "bank_transfer", "note": "wire 07-30", "at": "t"},
        "moved_back": {"how": "bank_transfer", "note": "", "at": "t"},
        "cash": {"how": "cash", "note": "", "at": "t"},
    }
    overrides = {"moved_back": {pp.OVERRIDE_FIELD: "card"}}
    month = pp.month_paths(receipts, overrides, stored, held=())

    assert month.bills == {"stated": "stated", "settled": "settled_outside"}
    assert month.paths["moved_back"] == ("card", "person")
    assert set(month.displayed_settled) == {"settled", "cash"}, (
        "the overruled disposition does not display"
    )
    assert month.effective_settled["stated"] == {
        "how": "bank_transfer", "note": "", "at": None, "derived": "stated",
    }
    assert month.effective_settled["settled"]["note"] == "wire 07-30", (
        "a stored disposition is kept as written, never re-derived"
    )
    assert "moved_back" not in month.effective_settled
    assert month.effective_settled["cash"]["how"] == "cash"
    assert "plain" not in month.effective_settled


def test_the_holds_are_read_only_for_a_row_carrying_a_signal():
    calls = []

    def held():
        calls.append(1)
        return {"plain", "stated"}

    month = pp.month_paths(
        [_R("plain", "Visa ...3645")], {}, {}, held=held,
    )
    assert calls == [], "no signal, no read"
    assert month.paths["plain"] == ("card", "")

    month = pp.month_paths(
        [_R("plain", "Visa ...3645"), _R("stated", "Wire Transfer")], {}, {},
        held=held,
    )
    assert calls == [1]
    assert month.paths["stated"] == ("card", "statement")
    assert month.bills == {}


# ── the suggestion's eligibility ────────────────────────────────────────


def _suggest(receipt, **kw):
    base = dict(
        path="card", source="", has_card=False, private=False,
        suggested_private=False, settled_entry=None, held=frozenset(),
    )
    base.update(kw)
    return pp.bill_suggestion(receipt, **base)


def test_the_suggestion_fires_on_an_open_card_less_row_only():
    doc = _R("inv", ocr_text="Remit to\nIBAN LU00 TEST 0000 0000 0000")
    assert _suggest(doc) == {"evidence": "IBAN LU00 TEST 0000 0000 0000"}
    assert _suggest(doc, has_card=True) is None
    assert _suggest(doc, private=True) is None
    assert _suggest(doc, suggested_private=True) is None
    assert _suggest(doc, settled_entry={"how": "cash"}) is None
    assert _suggest(doc, held=frozenset({"inv"})) is None
    assert _suggest(doc, source="person") is None, "a person moved it back"
    assert _suggest(doc, path="bill", source="stated") is None


def test_apply_card_to_this_vendor_never_writes_a_bill():
    """`POST .../cards/by-vendor` reads its targets off the resolved rows; a
    bill has no card to take, whatever else the row says."""
    from expense_recon.card_suggestion import card_by_vendor_targets

    row = {
        "document_id": "d1", "vendor": {"display": "TEST Vendor"}, "card": None,
        "card_source": "none", "payment_hint": "", "payment_path": "bill",
    }
    assert card_by_vendor_targets([row], "TEST Vendor") == []
    assert card_by_vendor_targets(
        [{**row, "payment_path": "card"}], "TEST Vendor"
    ) == ["d1"]


def test_an_invoice_payment_offer_suggests_and_never_moves():
    doc = _R("offer", payment_mode="Pay $15.00 with a bank transfer")
    assert _suggest(doc) == {"evidence": "Pay $15.00 with a bank transfer"}
    assert pp.month_paths([doc], {}, {}).bills == {}
