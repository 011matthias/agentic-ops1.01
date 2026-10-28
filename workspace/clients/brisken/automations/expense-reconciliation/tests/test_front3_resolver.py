"""Front 3 steps 2 and 3 (2026-09-25): the merchant list's resolver on bank
descriptors, and the containment guard on its close-spelling tier.

Step 2. The close-spelling tier discounts every word a bank line carries that
the listed name does not, so a product, a country, a code or Chase's cut at 22
characters sent a known merchant to "no merchant": 15 charge lines on 13
descriptors missed even under the planned list ('GOOGLE *Workspace_bris',
'HOSTINGER US INC', 'ZOHO* ZOHO-ONE', the Google product lines). A third
tier, after exact and close spelling, reads the line's merchant words and
matches the listed name's lead word, plus the product word on a platform
brand. It never runs where the first two tiers answered, so it cannot move a
hit they already make.

Step 3. token_set_ratio scores a name that says less than a listed one as a
full match: 'Twilio Inc' filed as 'Sendgrid - Twilio INC', 'Google LLC' as
Google Ads. Both pinned here, beside the live fuzzy hits that must stay
(LOVABLE, WWW.BRAVE.COM, ZOHO Corporation).

The negative cases are the contract.
"""
from __future__ import annotations

import pytest

from expense_recon.merchant_registry import MerchantRegistry

PLANNED = {
    "Google Workspace": {"aliases": []},
    "Google Cloud": {"aliases": []},
    "Google Ads": {"aliases": ["google"]},
    "Hostinger": {"aliases": []},
    "ZOHO Corp.": {"aliases": []},
    "Sendgrid - Twilio INC": {"aliases": ["TWILIO SENDGRID"]},
    "Lovable Labs": {"aliases": []},
    "Lovable Labs Incorporated": {"aliases": []},
    "Brave Software, Inc.": {"aliases": []},
    "Supermercado Fenix": {"aliases": []},
}


def _hit(reg, text):
    m = reg.resolve(None, text)
    return (m.canonical_name, m.kind) if m else None


@pytest.mark.parametrize("line, merchant", [
    ("GOOGLE *Workspace_bris", "Google Workspace"),   # Chase's cut + product
    ("GOOGLE *CLOUD B2vMDX", "Google Cloud"),         # a short code survives
    ("HOSTINGER US INC", "Hostinger"),                # a country code
    ("ZOHO* ZOHO-ONE", "ZOHO Corp."),                 # the brand echoed
])
def test_a_bank_line_names_its_listed_merchant_through_the_descriptor_tier(line, merchant):
    assert _hit(MerchantRegistry(PLANNED), line) == (merchant, "descriptor")


@pytest.mark.parametrize("line", [
    "GOOGLE*PLAY",        # a Google product nobody listed is no Google product
    "Google LLC",         # the brand alone names none of its products
    "Twilio Inc",         # not SendGrid through the alias 'TWILIO SENDGRID'
    "FENIX TURISMO",      # another business sharing a merchant's one word
    "ZOHO_BOOKS",         # a whole word the listed name does not carry
])
def test_a_line_that_says_less_or_other_than_the_listed_name_names_no_merchant(line):
    assert _hit(MerchantRegistry(PLANNED), line) is None


def test_the_live_close_spelling_hits_are_unchanged():
    """The 12 live rows through the close-spelling tier (LOVABLE 9, ZOHO
    Corporation 2, WWW.BRAVE.COM 1) were all right; they stay where they
    were, and exact hits stay exact."""
    reg = MerchantRegistry(PLANNED)
    assert _hit(reg, "LOVABLE") == ("Lovable Labs", "fuzzy")
    assert _hit(reg, "ZOHO Corporation") == ("ZOHO Corp.", "fuzzy")
    assert _hit(reg, "WWW.BRAVE.COM") == ("Brave Software, Inc.", "fuzzy")
    assert _hit(reg, "TWILIO SENDGRID WWW.TWILIO.CO CA") == (
        "Sendgrid - Twilio INC", "exact")
    assert _hit(reg, "GOOGLE *ADS9208169978") == ("Google Ads", "exact")


def test_a_shorter_listed_name_covering_the_same_words_wins_the_close_spelling_tier():
    reg = MerchantRegistry({
        "Twilio": {"aliases": []},
        "Sendgrid - Twilio INC": {"aliases": ["TWILIO SENDGRID"]},
    })
    assert _hit(reg, "Twilio Inc.")[0] == "Twilio"
    assert _hit(reg, "TWILIO") == ("Twilio", "exact")


def test_two_merchants_matching_a_line_equally_is_no_answer():
    reg = MerchantRegistry({
        "NOBRE ATACADO SAO JOSE DA C": {"aliases": []},
        "NOBRE ATACADO SAO JOSE DA COROA GRANDE": {"aliases": []},
    })
    assert _hit(reg, "NOBRE ATACAREJO SAO JOS") is None
