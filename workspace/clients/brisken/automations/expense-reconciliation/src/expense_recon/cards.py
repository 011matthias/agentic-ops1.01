"""The card registry: the tool's own card identity model (2026-08-21).

Owner direction (feedback wave 2026-08-21): "cards do not need zoho
accounts since we want to gain independence from zoho, we must create our
own identification system". Until now a card existed only as a side effect
of the Zoho maps: ``settings["card_entities"]`` (card -> legal entity) and
``settings["card_accounts"]`` (card -> Zoho bank account), plus the
``/data`` presets file (`cards_provision.CardPreset`) the upload form
renders. Three key spaces, three matchers, and no way to say "this is the
corporate Chase card" without naming a Zoho account.

This module gives cards one home: ``settings["cards"]``.

    "cards": {
      "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
        "aliases": ["CorpServ"],
        "entity": "Corporate Services",
        "person": "Nicolas",
        "zoho_account": "1010 Chase Corporate",
        "currency": "USD",
        "default_cost_center": "Lidar"
      }
    }

``person`` (backlog item 40, owner directive 2026-09-06) is who a card's
expenses belong to: "each card is attributed to a name and therefore
every expense can be attributed to a person. Even the ones injected via
email." Person attribution rides the SAME card chain as ``entity`` — the
LAST link, resolved from whichever card the chain lands on — and NEVER
the mail sender: ``submitted_by`` stays ingest provenance (a claim about
who mailed a file), by explicit owner ruling.

``default_cost_center`` (backlog item 47) is the card's standing project
or purpose, for a card that belongs to one of them. It is the WEAKEST
link of the cost-center chain (override > trip > merchant > card), and it
is stored as a plain string that is NOT validated against the cost-center
registry here, on purpose: cards and cost centers are edited
independently, so requiring the centre to exist first would make the edit
ORDER matter. A name the registry does not define simply fails to resolve
when the chain runs (``CostCenterRegistry.resolve`` ignores what it cannot
canonicalize), which leaves the row unresolved rather than stamping
something invented.

``parent`` (backlog item 147, owner directive 2026-09-18) is the ACCOUNT a
card sits under: "card 2838 for example should be an account with others as
subcards". It holds another card's KEY, the same key space this map is
indexed by, because an account IS one of these cards rather than a separate
thing. The tree is exactly one level deep, and it is DATA a person sets:
nothing in the tool derives it. Sharing a statement file is evidence, not
proof (the four cards on July 2026's one Chase file belong to three different
people), so the registry is told the parentage and never asked to guess it.

Two design facts carried from production evidence:

* The SAME physical card has multiple digit identities. The Chase
  statement marks charges with the cycle-marker number ("2838") while the
  plastic prints a different last-4 ("1672"); Zoho payment-mode labels
  name both ("1 - CorpServ 2838/1672 (Chase)"). ``digits`` is therefore a
  LIST; any of its tokens identifies the card.
* ``zoho_account`` is OPTIONAL. It is only consumed by the Zoho exports;
  a card without one still resolves its legal entity and label, and the
  export balances to a visible placeholder (never a hard failure).

Migration is read-time composition, not a rewrite: ``effective_cards``
starts from ``settings["cards"]`` and folds in the legacy maps and the
presets file, so the seeded 2026-08-06 master data keeps working with
``settings["cards"]`` empty, and an explicit card entry wins field by
field the moment one exists. Nothing writes the legacy keys here.

Accepted divergences from the deleted per-map matchers (all verified
against the seeded production shape, which is digit-keyed and disjoint,
where none of them fire):

* Non-digit legacy keys match normalized (case-insensitive equality,
  suffix, whole-word token) instead of raw case-sensitive exact/endswith.
* Legacy digit keys shorter than 3 digits no longer act as endswith
  wildcards ("1" matching any label ending in 1) — deny-by-default.
* When one observed label matches two account-bearing cards (a
  double-mapped config), the winner is composed-order-first, which can
  differ from the old map-order-first; both are deterministic picks over
  ambiguous operator input.
* Two legacy entity keys sharing a digit token (a conflicting
  double-mapping like "2838" and "2838/1672" to different entities)
  merge fill-only: the first entity wins everywhere, including the
  available-entities picker.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

from .cards_provision import CardPreset
from .error_codes import CodedValueError
from .matching.deterministic import _MASK_CHARS, _card_keys, _normalize

# Digit tokens accepted in a card entry: 3-8 digits, matching the token
# extractor's floor (`_card_keys` only sees runs of 3+). A shorter token
# would be inert for pipeline resolution while flattening into the batch
# snapshot map, where the export's endswith-fuzzy matching would treat it
# as a 2-char wildcard — rejected at the edge instead.
_DIGIT_MIN, _DIGIT_MAX = 3, 8

# Composition sources, in field-priority order (earlier wins).
SOURCE_SETTINGS = "settings"
SOURCE_LEGACY = "legacy"
SOURCE_PRESET = "preset"

# Generic tender vocabulary (EN + PT + DE, the extractor's observed
# languages): a payment hint built ONLY of network / tender-type words
# identifies no specific card, so it must never resolve one and must
# never be stored as a card alias — that would auto-resolve every future
# "Visa" (or "Visa Credit", or "Kreditkarte") receipt onto one arbitrary
# card (owner ruling 2026-08-21: generic tender words never auto-resolve;
# review, not guess). The check is word-subset, not exact-phrase, so
# compound tenders ("Visa Credit", "cartao visa") stay generic while any
# distinctive word ("CorpServ") makes the hint identifying. A hint with a
# 3+ digit run ("Visa ...1672") is never generic — those digits identify;
# a SHORTER number word ("30" in "Cartao Credito 30 Dias") is below the
# extractor's floor, identifies nothing, and does not block genericity
# (backlog item 35, 2026-08-28: three real April tender phrases rendered
# as assignable cards because of vocabulary gaps + the "30").
# The last group (owner ruling 2026-09-24, card-attribution case 6) holds
# the neutral "a card was used" words real receipts print ("saved payment
# method", "Link", "VENDA CREDITO VISA", "OUTRO", "Kartenzahlung
# erhalten"), so "Remember for future months" can never turn one of those
# phrases into a card alias.
GENERIC_TENDER_WORDS = frozenset({
    # networks
    "visa", "mastercard", "master", "amex", "american", "express", "elo",
    "maestro", "discover", "diners", "club", "girocard",
    # EN tender types
    "credit", "debit", "card", "cash", "check", "cheque", "paypal",
    "pix", "wire", "transfer", "bank", "apple", "google", "pay",
    "contactless", "chip",
    # PT
    "cartao", "credito", "debito", "dinheiro", "boleto",
    "transferencia", "de", "tef", "compra", "dias",
    # DE
    "kreditkarte", "karte", "ec", "bar", "lastschrift", "girokarte",
    "uberweisung", "ueberweisung", "zahlung", "kredit",
    # "a card was used" (case 6)
    "saved", "payment", "method", "link", "venda", "outro", "outros",
    "kartenzahlung", "erhalten", "olv", "stored", "wallet", "pagamento",
    "recebido", "forma", "paid", "received",
})


def is_generic_tender(text: str | None) -> bool:
    """True when a hint names only a tender type / card network: no digit
    token, at least one vocabulary word, and EVERY word is either generic
    tender vocabulary or a number too short to be a card digit run
    (< _DIGIT_MIN, e.g. the "30" of "cartao credito 30 dias"). Diacritics
    fold first ("Cartão de crédito" -> "cartao de credito"): `_normalize`
    is ASCII-alnum and would split accented letters."""
    if not text or not text.strip():
        return False
    if _card_keys(text) or masked_short_ending(text):
        return False
    words = payment_words(text)
    return (
        any(w in GENERIC_TENDER_WORDS for w in words)
        and all(
            w in GENERIC_TENDER_WORDS
            or (w.isdigit() and len(w) < _DIGIT_MIN)
            for w in words
        )
    )


# Card-attribution case 6 (owner ruling 2026-09-24): receipts glue words
# together. "CreditCard" is "credit card" and "girocardOLV" is a girocard
# (OLV, the German signature variant), so every payment-hint classifier here
# reads the same split words. A token splits at a lower-to-upper case
# boundary, and a known network or kind word of 5+ letters splits off the
# FRONT of a longer token ("CREDITCARD"). Shorter words (bar, ec, pay, de,
# elo, visa) never prefix-split, or "Barbecue" would read as cash and
# "Visagem" as a Visa; a remainder under 3 letters keeps the token whole, so
# "creditos" and "creditor" stay single words.
_CASE_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])")
_PREFIX_WORDS = (
    "mastercard", "girocard", "maestro", "credito", "debito", "credit",
    "kredit", "cartao", "debit",
)
_PREFIX_REST_MIN = 3


def payment_words(text: str) -> list[str]:
    """Lower-case ASCII words of a payment hint: diacritics folded ("Cartão
    de crédito" -> cartao, de, credito), glued words split ("CreditCard" ->
    credit, card; "girocardOLV" -> girocard, olv). A token that is itself a
    known word stays whole ("PayPal", "PagSeguro", "Kreditkarte")."""
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    words: list[str] = []
    for raw in re.split(r"[^A-Za-z0-9]+", folded):
        if not raw:
            continue
        if raw.lower() in _WHOLE_WORDS:
            words.append(raw.lower())
            continue
        for part in _CASE_BOUNDARY.split(raw):
            words.extend(_split_prefix(part.lower()))
    return words


def _split_prefix(token: str) -> list[str]:
    if token in _WHOLE_WORDS:
        return [token]
    for word in _PREFIX_WORDS:
        if token.startswith(word) and len(token) - len(word) >= _PREFIX_REST_MIN:
            return [word, *_split_prefix(token[len(word):])]
    return [token]


# The card networks and kinds, read two ways. `registry_card_types` reads
# Brisken's own from the registry's wording (case 5, 2026-09-24: "VISA
# CREDIT" on a receipt is no evidence against a Visa credit card), and
# `positive_non_brisken_evidence` reads a hint's against them. "express" and
# "club" count toward amex / diners in the registry's controlled wording
# only; anywhere in a receipt's free text they are ordinary words.
CARD_NETWORK_WORDS = {
    "visa": "visa",
    "mastercard": "mastercard", "master": "mastercard",
    "amex": "amex", "american": "amex", "express": "amex",
    "elo": "elo",
    "maestro": "maestro",
    "discover": "discover",
    "diners": "diners", "club": "diners",
    "girocard": "girocard", "girokarte": "girocard", "ec": "girocard",
}
CARD_KIND_WORDS = {
    "credit": "credit", "credito": "credit", "kredit": "credit",
    "kreditkarte": "credit",
    "debit": "debit", "debito": "debit", "lastschrift": "debit",
}
# The words a hint must carry for its network to count, anywhere in it:
# CARD_NETWORK_WORDS without the fragments, plus the full amex name.
_HINT_NETWORK_WORDS = {
    w: n for w, n in CARD_NETWORK_WORDS.items()
    if w not in ("american", "express", "club")
}
_HINT_NETWORK_PHRASES = {"american express": "amex"}
# Today's cash words: the settled-outside chip's cash tender
# (`web.service._TENDER_PATTERNS`, pinned equal by test) plus "bar" as a
# whole word. Not widened here (out of scope of case 6).
CASH_WORDS = frozenset({
    "cash", "dinheiro", "especes", "contanti", "bargeld", "bar",
})
_CASH_PHRASES = {"em especie": "cash"}
# Card issuers and banks that are NOT Brisken's: a conservative starting
# list (owner ruling 2026-09-24). A name counts as evidence only while no
# active card's label or account names it. Whole words only; "db" and
# "deutsche bank" are deliberately absent, because DB on these receipts is
# Deutsche Bahn.
NON_BRISKEN_ISSUERS = (
    "nubank", "revolut", "n26", "wise", "sparkasse", "volksbank",
    "raiffeisen", "commerzbank", "dkb", "comdirect", "ing", "itau",
    "bradesco", "santander", "caixa", "banco do brasil", "banco inter",
    "c6 bank", "picpay", "mercado pago",
)
# The issuer names Brisken's registry is read for (live 2026-09-24: Chase,
# GSBANK / Goldman Sachs for the Apple card, the United co-brand). Brisken's
# issuers are whatever of these, or of NON_BRISKEN_ISSUERS, an active card's
# wording names; this list only teaches the reader the names.
_ISSUER_IDS = {
    "chase": "chase", "gsbank": "goldman", "goldman sachs": "goldman",
    "apple": "apple", "united": "united",
    **{name: name for name in NON_BRISKEN_ISSUERS},
}
# POS acquirers and wallets print the terminal operator or the wallet, never
# the card behind it, so they are NEUTRAL: never evidence either way. Taken
# out of a hint before issuers are read ("Apple Pay" is not the Apple card).
NEUTRAL_PAYMENT_NAMES = (
    "cielo", "rede", "stone", "getnet", "pagseguro", "sumup", "adyen",
    "worldline", "stripe", "square", "apple pay", "google pay",
)
_WHOLE_WORDS = GENERIC_TENDER_WORDS | frozenset(
    name for name in (*_ISSUER_IDS, *NEUTRAL_PAYMENT_NAMES) if " " not in name
)


def registry_card_types(
    cards: "dict[str, Card]",
) -> tuple[frozenset[str], frozenset[str]]:
    """The card networks and kinds the ACTIVE cards carry, read from each
    card's own `label` and `zoho_account` wording ("Credit Card Chase Visa -
    3645" -> visa, credit; "GSBANK Apple Master Card 0113" -> mastercard).
    Derived, never stored: the Settings cards editor replaces the whole map
    on save, so a new card field would be erased by the published screen."""
    networks: set[str] = set()
    kinds: set[str] = set()
    for card in (cards or {}).values():
        if not card.active:
            continue
        for word in payment_words(f"{card.label} {card.zoho_account or ''}"):
            if word in CARD_NETWORK_WORDS:
                networks.add(CARD_NETWORK_WORDS[word])
            if word in CARD_KIND_WORDS:
                kinds.add(CARD_KIND_WORDS[word])
    return frozenset(networks), frozenset(kinds)


def registry_issuers(cards: "dict[str, Card]") -> frozenset[str]:
    """The issuers the ACTIVE cards come from, read from each card's `label`
    and `zoho_account` wording like `registry_card_types` ("Chase United
    Visa 8311" -> chase, united; "GSBANK Apple Master Card" -> goldman,
    apple). Derived, never stored, for the same reason."""
    found: set[str] = set()
    for card in (cards or {}).values():
        if card.active:
            words = payment_words(f"{card.label} {card.zoho_account or ''}")
            found |= _phrases_in(words, _ISSUER_IDS)
    return frozenset(found)


def _phrases_in(words: list[str], names: "dict[str, str]") -> set[str]:
    """The ids of every name in `names` (one or more words) that `words`
    holds as consecutive whole words."""
    found: set[str] = set()
    for name, ident in names.items():
        parts = name.split()
        n = len(parts)
        if any(words[i:i + n] == parts for i in range(len(words) - n + 1)):
            found.add(ident)
    return found


def _without_phrases(words: list[str], names: "tuple[str, ...]") -> list[str]:
    """`words` with every occurrence of the given names cut out."""
    out = list(words)
    for name in sorted(names, key=len, reverse=True):
        parts = name.split()
        n = len(parts)
        i = 0
        while i <= len(out) - n:
            if out[i:i + n] == parts:
                del out[i:i + n]
            else:
                i += 1
    return out


def positive_non_brisken_evidence(
    hint: str | None, cards: "dict[str, Card]"
) -> str | None:
    """What in a payment hint proves the payment did NOT come from Brisken,
    or None when nothing does (owner ruling 2026-09-24, card-attribution
    case 6). A private expense is SUGGESTED only on such evidence; every
    other payment text waits for the statement charge, the remembered card,
    the merchant's card and Criss's own assignment, including phrases nobody
    has seen yet. Supersedes item 41's trigger ("not defined in the system"
    became "positively not Brisken's").

    The reasons, first match wins:

    * ``"number"``: a 3+ digit card number naming no active Brisken card
      (a number always outranks words: "DEBIT-MASTERCARD 3281" is decided
      by 3281). A number or alias that does name a Brisken card, or two of
      them, is None.
    * ``"ending"``: a masked two-digit ending no active card ends in.
    * ``"cash"``: a cash word (`CASH_WORDS`).
    * ``"network"`` / ``"kind"``: a network (girocard, EC, maestro, amex,
      elo, diners, discover) or a kind (debit) no active card carries, read
      anywhere in the hint ("Visa Debit" is a debit card, not Brisken's).
    * ``"issuer"``: an issuer from `NON_BRISKEN_ISSUERS` no active card
      names.

    Conflict means wait: a hint naming, within networks, kinds or issuers,
    one that is Brisken's AND one that is not ("credit or debit card", a
    checkout's list of options), or a cash word beside anything Brisken's,
    is None. Acquirers and wallets (`NEUTRAL_PAYMENT_NAMES`) say nothing.
    Pure: the registry is the batch's own snapshot, and nothing is stored.
    """
    text = (hint or "").strip()
    if not text:
        return None
    card, ambiguous = resolve_hinted_card_ex(text, cards)
    if card is not None or ambiguous:
        return None
    if _card_keys(text):
        return "number"
    ending = masked_short_ending(text)
    if ending:
        return None if cards_ending_in(ending, cards) else "ending"
    words = _without_phrases(payment_words(text), NEUTRAL_PAYMENT_NAMES)
    networks, kinds = registry_card_types(cards)
    named = {
        "network": {_HINT_NETWORK_WORDS[w] for w in words
                    if w in _HINT_NETWORK_WORDS}
        | _phrases_in(words, _HINT_NETWORK_PHRASES),
        "kind": {CARD_KIND_WORDS[w] for w in words if w in CARD_KIND_WORDS},
        "issuer": _phrases_in(words, _ISSUER_IDS),
    }
    brisken = {
        "network": networks, "kind": kinds, "issuer": registry_issuers(cards),
    }
    ours = {dim: named[dim] & brisken[dim] for dim in named}
    theirs = {dim: named[dim] - brisken[dim] for dim in named}
    theirs["issuer"] &= set(NON_BRISKEN_ISSUERS)
    if any(ours[dim] and theirs[dim] for dim in named):
        return None
    if any(w in CASH_WORDS for w in words) or _phrases_in(words, _CASH_PHRASES):
        return None if any(ours.values()) else "cash"
    for dim in ("network", "kind", "issuer"):
        if theirs[dim]:
            return dim
    return None


# ── the private-card list (owner direction 2026-09-24, cases 2 + 4) ────
#
# "fuze items 2 and 4 together, fix a) by setting up private card
# memory/registry and b) any credit card types or numbers that dont belong
# to brisken will then be suggested as private expenses". Case 6 above is
# half (b); the list below is half (a): a card that is NOT Brisken's, known
# by its last four digits and the person it belongs to, so a personal card
# that recurs (3281 every month) is confirmed private once, in Settings or
# from the unknown-card strip, and never again by hand.
#
# It is `settings["private_cards"]`, a SEPARATE key from `cards`: every
# company-card consumer iterates `cards` (the matcher's card scope, the
# coverage rows, the months strip, the Cards overview, statement linking,
# `/api/cards`), and the SPA's Cards editor replaces that whole map on save,
# so a flag on a company card would be read as a company card everywhere
# and erased by the published screen. Read LIVE at view time (like the
# remembered card since item 169 and the merchant registry since M2), never
# snapshotted into a batch, so an entry reaches every existing month at
# once with no refresh and no write to any month.


@dataclass(frozen=True)
class PrivateCard:
    """One entry of `settings["private_cards"]`."""

    digits: str
    person: str
    note: str = ""
    active: bool = True


PRIVATE_SOURCE_ROW = "row"
PRIVATE_SOURCE_MONTH = "month"
PRIVATE_SOURCE_LIST = "private_card_list"
PRIVATE_SOURCES = (PRIVATE_SOURCE_ROW, PRIVATE_SOURCE_MONTH, PRIVATE_SOURCE_LIST, "")


def private_card_digits(text: str | None) -> str | None:
    """The four digits a private-card entry is keyed on: the last 4 of the
    LAST 4+ digit run in `text`, read with the matcher's own extraction
    (`hint_digit_run`: a run followed by a mask is a BIN and is skipped), the
    leading zero kept ("0340" stays "0340"). None for text with no such run
    and for a two-digit ending: money owed to a person needs the full last
    4, so "xx78" never names a private card."""
    run = hint_digit_run(text)
    if not run or not run.isdigit() or len(run) < 4:
        return None
    return run[-4:]


def private_cards_from_setting(raw: object) -> dict[str, PrivateCard]:
    """`{last4: PrivateCard}` from the stored map. Tolerant: read-time never
    400s, so an entry that cannot be read is dropped rather than raised."""
    out: dict[str, PrivateCard] = {}
    if not isinstance(raw, dict):
        return out
    for key, entry in raw.items():
        digits = private_card_digits(str(key))
        if digits is None or not isinstance(entry, dict):
            continue
        person = str(entry.get("person") or "").strip()
        if not person:
            continue
        out[digits] = PrivateCard(
            digits=digits,
            person=person,
            note=str(entry.get("note") or "").strip(),
            active=entry.get("active", True) is not False,
        )
    return out


def normalize_private_cards_setting(
    raw: object, *, company_cards: "dict[str, Card] | None" = None
) -> dict:
    """Validate + clean a ``settings["private_cards"]`` payload at the edge.

    Same contract family as ``normalize_cards_setting``: the whole map
    replaces the stored one; a malformed entry raises ``CodedValueError``
    (the API answers 400 with the code). Keys normalize to the four digits
    (`private_card_digits`), so "***3281" and "3281" are one entry, and
    `person` is required and trimmed. Refused, by code:

    * ``private_card_digits_short``: the key holds no 4+ digit run (a
      two-digit ending, a word). Money owed to a person needs the full
      last 4.
    * ``private_card_person_required``: no person to reimburse.
    * ``private_card_duplicate``: two keys normalize to the same digits.
    * ``private_card_is_company_card``: an ACTIVE company card in
      `company_cards` carries the digits. A card is Brisken's OR private,
      never both (the same rule the per-row routes enforce), and the
      company-card PUT refuses the reverse with the same code.
    """
    if not isinstance(raw, dict):
        raise CodedValueError(
            "private_cards must be an object", code="invalid_body"
        )
    cleaned: dict[str, dict] = {}
    for key, entry in raw.items():
        label = str(key).strip()
        if not label:
            continue
        digits = private_card_digits(label)
        if digits is None:
            raise CodedValueError(
                f"private card {label!r} needs the full last 4 digits of "
                "the card",
                code="private_card_digits_short", private_card=label,
            )
        if not isinstance(entry, dict):
            raise CodedValueError(
                f"private_cards[{label!r}] must be an object",
                code="invalid_body", private_card=label,
            )
        person = str(entry.get("person") or "").strip()
        if not person:
            raise CodedValueError(
                f"private card {digits} needs the person to reimburse",
                code="private_card_person_required", private_card=digits,
            )
        if digits in cleaned:
            raise CodedValueError(
                f"private card {digits} is listed twice ({label!r})",
                code="private_card_duplicate", private_card=digits,
            )
        cleaned[digits] = {
            "person": person,
            "note": str(entry.get("note") or "").strip(),
            "active": entry.get("active", True) is not False,
        }
    hit = private_company_collision(
        company_cards or {}, private_cards_from_setting(cleaned)
    )
    if hit is not None:
        digits, card_key = hit
        raise CodedValueError(
            f"private card {digits} is the company card {card_key!r}; a "
            "card is Brisken's or private, never both",
            code="private_card_is_company_card",
            private_card=digits, card=card_key,
        )
    return cleaned


def private_company_collision(
    company_cards: "dict[str, Card]", private_cards: dict[str, PrivateCard]
) -> tuple[str, str] | None:
    """`(private digits, company card key)` of the first ACTIVE private
    entry an ACTIVE company card also carries, else None. Both directions
    of the "company OR private, never both" rule read this: the private
    list's PUT (and the strip's learn path) against the composed registry,
    and the company cards' PUT against the stored list."""
    for digits, entry in private_cards.items():
        if not entry.active:
            continue
        keys = _card_keys(digits)
        for key, card in (company_cards or {}).items():
            if card.active and (card.digit_keys() & keys):
                return digits, key
    return None


def private_card_for(
    hint: str | None, private_cards: dict[str, PrivateCard] | None
) -> PrivateCard | None:
    """The ACTIVE private-card entry a hint's printed number names, else
    None. The number is read with the matcher's extraction (`_card_keys`:
    3+ digit runs, a masked BIN skipped, "0340" and "340" one key), so the
    list is consulted exactly where the company registry would have been.
    A two-digit ending never reaches it (the extraction floor), and a
    hint printing no number never does."""
    text = (hint or "").strip()
    if not text or not private_cards:
        return None
    keys = _card_keys(text)
    if not keys:
        return None
    for digits, entry in private_cards.items():
        if entry.active and (_card_keys(digits) & keys):
            return entry
    return None


def classify_payment_evidence(
    hint: str | None,
    cards: "dict[str, Card]",
    private_cards: dict[str, PrivateCard] | None,
    hints: dict | None = None,
) -> "tuple[PrivateCard | None, str | None]":
    """Whose money a payment hint says paid, steps 1-4 of the decision
    order (`docs/api-contract.md`, "Whose money paid"), as ONE entry point
    so the resolver reaches the private-card answer and the private
    suggestion through one function and not two sets of conditions:

    1. a printed number (or an assigned hint, `hints`) naming a Brisken
       card, or 2. a Brisken card type with no number: `(None, None)`, no
       private answer of any kind (the card chain decides);
    3. a printed number on the PRIVATE-CARD LIST: `(entry, None)`, the row
       is private and the listed person is reimbursed;
    4. positive evidence the payment was not Brisken's
       (`positive_non_brisken_evidence`): `(None, reason)`, suggested
       private.

    Everything else is `(None, None)` and waits. A number always outranks a
    type word in the same hint, so step 3 is read before step 4's `number`
    reason ("DEBIT-MASTERCARD 3281" is decided by 3281). A two-digit ending
    is never looked up on the list; one two Brisken cards share stays
    unguessed and is not private. Pure, like its parts."""
    text = (hint or "").strip()
    if not text:
        return None, None
    card, ambiguous = resolve_hinted_card_ex(text, cards, hints)
    if card is not None or ambiguous:
        return None, None
    listed = private_card_for(text, private_cards)
    if listed is not None:
        return listed, None
    return None, positive_non_brisken_evidence(text, cards)


# Note #60 (owner, 2026-09-17): some receipts print only the last TWO
# digits of the card ("42463153XXXXXX38" on the June Fenix and August SARL
# TRAIN'S receipts). Two digits sit below the matcher's 3-digit floor, so
# the hint carried no card at all and every such row needed a hand fix.
# Two digits are still evidence when a MASK or an ending word introduces
# them: they are the card's own tail, not a quantity. A bare two-digit
# number ("Cartao Credito 30 Dias", "$15.00") is not, so it never counts.
# A single "x" is not a mask here ("3x" is an instalment count); "xx" is.
_ENDING_MASKS = r"[Xx]{2,}|[*#•●]+|\.{2,}|…"
# Item 199 (owner, 2026-09-24): the ending words, one EXPLICIT phrase per
# entry, matched on diacritic-folded text. September's GoDaddy printed "card
# ending with the last two digits: 38", which the old two-word list missed.
# A lead is followed only by separators and the two digits, never by other
# words: allowing words in between is what would read "ending balance 38" or
# "final total 38" as a card. A new wording is one line here.
_ENDING_LEADS = (
    # EN ("card no. ending" is covered by "ending")
    r"ending(?:\s+(?:in|with))?(?:\s+the\s+digits)?",
    r"ends\s+(?:in|with)",
    r"(?:the\s+)?last\s+(?:two|2)\s+digits",
    r"last\s+digits",
    # PT ("com final" is covered by "final")
    r"final",
    r"terminad[oa]\s+em",
    r"terminacao(?:\s+em)?",
    r"(?:os\s+)?ultimos\s+(?:dois|2)\s+digitos",
    # DE
    r"endet\s+auf",
    r"endend\s+auf",
    r"(?:mit\s+)?endung",
    r"endziffern",
    r"letzten?\s+(?:zwei|2)\s+(?:ziffern|stellen)",
    # FR
    r"(?:se\s+)?terminant\s+par",
    r"finissant\s+par",
    r"(?:les\s+)?(?:deux|2)\s+derniers\s+chiffres",
    r"derniers\s+chiffres",
    # ES
    r"termina(?:da)?\s+en",
    r"(?:los\s+)?ultimos\s+(?:dos|2)\s+digitos",
)
# Two digits followed by a decimal separator and a digit are an amount
# ("valor final 38,00"), never an ending: the `(?![.,]\d)` guard.
_ENDING_DIGITS = r"(?<!\d)(\d{2})(?!\d)(?![.,]\d)"
_SHORT_ENDING = re.compile(
    rf"(?:{_ENDING_MASKS}|\b(?:{'|'.join(_ENDING_LEADS)}))"
    rf"\s*[:.…]*\s*{_ENDING_DIGITS}",
    re.IGNORECASE,
)
# "last two digits: 38 and 49" prints two endings, which name nothing: the
# number after a list word counts as a second ending.
_SECOND_ENDING = re.compile(
    rf"\s*(?:[,;/&]|\s(?:and|or|e|ou|und|oder|et|y|o)\s)\s*{_ENDING_DIGITS}",
    re.IGNORECASE,
)


def masked_short_ending(text: str | None) -> str | None:
    """The two-digit card ending a hint prints behind a mask or an ending
    phrase ("XXXXXX38", "**38", "••38", "ending in 38", "final 38", "last
    two digits: 38", "endet auf 38"), or None.

    Only consulted for a hint that carries NO card number the matcher can
    use (`_card_keys` empty): a printed last-4 always outranks two digits.
    Two different endings in one hint ("xx38; xx49", "last two digits: 38
    and 49") name nothing. Diacritics fold first, so "últimos dígitos" and
    "terminação" match their ASCII leads."""
    if not text or _card_keys(text):
        return None
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    endings: set[str] = set()
    for m in _SHORT_ENDING.finditer(folded):
        endings.add(m.group(1))
        second = _SECOND_ENDING.match(folded, m.end())
        if second:
            endings.add(second.group(1))
    return endings.pop() if len(endings) == 1 else None


def cards_ending_in(ending: str, cards: "dict[str, Card]") -> "list[Card]":
    """Active cards with a printed number ending in `ending`, registry order."""
    return [
        c for c in cards.values()
        if c.active and any(str(d).endswith(ending) for d in c.digits)
    ]


def hint_digit_run(text: str | None) -> str | None:
    """The digit run that identifies a payment hint's card, VERBATIM.

    The strict masked-PAN rule from `resolve_card`, generalized (backlog
    item 35): of the 3-8 digit runs in a hint, the LAST is taken — on a
    masked PAN the earlier runs are BIN/middle fragments that cross-match
    unrelated cards (R3 adversarial review), and on any other multi-run
    hint the pick is display-only determinism for a string the resolver
    refused to resolve anyway. Returns the run as printed (leading zero
    preserved): "0340" stays
    "0340", because this feeds the review strip's display grouping,
    where a human knows the card as the statement prints it. The
    zero-stripped match-key equivalence is the caller's business
    (`_card_keys` semantics).
    """
    if not text:
        return None
    # A run followed by a mask is the issuer's BIN, which `_card_keys`
    # already ignores (item 69 round B); grouping the strip on it would
    # show "42463153" as if it were the card.
    runs = [
        m.group()
        for m in re.finditer(r"\d{3,8}", text)
        if not (m.end() < len(text) and text[m.end()] in _MASK_CHARS)
    ]
    if runs:
        return runs[-1]
    return masked_short_ending(text)


@dataclass(frozen=True)
class Card:
    """One card identity, composed from all sources."""

    key: str
    label: str = ""
    label_pt: str | None = None
    digits: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    entity: str = ""
    person: str = ""
    parent: str = ""
    default_cost_center: str = ""
    zoho_account: str | None = None
    currency: str = ""
    active: bool = True
    source: str = SOURCE_SETTINGS

    @property
    def display_label(self) -> str:
        return self.label or self.key

    def digit_keys(self) -> set[str]:
        """The normalized digit tokens that identify this card, using the
        SAME extraction the matcher uses so statement markers, payment-mode
        labels, and stored digits land on one key space."""
        keys: set[str] = set()
        for d in self.digits:
            keys |= _card_keys(d)
        return keys


def card_to_dict(card: Card) -> dict:
    """JSON shape for the API (stable, includes the composition source)."""
    return {
        "key": card.key,
        "label": card.display_label,
        "label_pt": card.label_pt,
        "digits": list(card.digits),
        "aliases": list(card.aliases),
        "entity": card.entity,
        "person": card.person,
        "parent": card.parent,
        "default_cost_center": card.default_cost_center,
        "zoho_account": card.zoho_account,
        "currency": card.currency,
        "active": card.active,
        "source": card.source,
    }


def normalize_cards_setting(raw: object, *, known: dict | None = None) -> dict:
    """Validate + clean a ``settings["cards"]`` payload at the edge.

    Same contract family as ``normalize_merchants_setting``: the whole map
    replaces the stored one; a blank card key is silently dropped; a
    malformed entry raises ``ValueError`` (the API answers 400). Stored
    shape keeps only meaningful fields (no empty strings, ``active`` only
    when False) so the settings blob stays small and diffs stay honest.

    ``known`` is the stored map this payload will be merged OVER, for the
    one caller that normalizes a PARTIAL map (the batch-cards learn path,
    which validates only the entries it touched). A ``parent`` may then name
    a card that is stored but absent from the payload. The settings PUT
    passes nothing: it replaces the whole map, so the payload IS the
    registry and a parent it does not contain does not exist.
    """
    if not isinstance(raw, dict):
        raise CodedValueError("cards must be an object", code="invalid_body")
    cleaned: dict[str, dict] = {}
    for key, entry in raw.items():
        slug = str(key).strip()
        if not slug:
            continue
        if not isinstance(entry, dict):
            raise CodedValueError(
                f"cards[{slug!r}] must be an object",
                code="invalid_body", field=f"cards[{slug}]",
            )
        out: dict = {}
        for skey in (
            "label", "label_pt", "entity", "person", "parent",
            "default_cost_center", "zoho_account",
        ):
            value = str(entry.get(skey) or "").strip()
            if value:
                out[skey] = value
        currency = str(entry.get("currency") or "").strip().upper()
        if currency:
            out["currency"] = currency
        digits_raw = entry.get("digits")
        if digits_raw is not None and not isinstance(digits_raw, list):
            raise CodedValueError(
                f"cards[{slug!r}].digits must be a list",
                code="invalid_body", field=f"cards[{slug}].digits",
            )
        digits: list[str] = []
        for d in digits_raw or []:
            token = str(d).strip()
            if not token:
                continue
            if not token.isdigit() or not (_DIGIT_MIN <= len(token) <= _DIGIT_MAX):
                raise CodedValueError(
                    f"cards[{slug!r}].digits entries must be"
                    f" {_DIGIT_MIN}-{_DIGIT_MAX} digit strings, got {token!r}",
                    code="card_digits_invalid",
                    card=slug, value=token,
                    min_digits=_DIGIT_MIN, max_digits=_DIGIT_MAX,
                )
            if token not in digits:
                digits.append(token)
        if digits:
            out["digits"] = digits
        aliases_raw = entry.get("aliases")
        if aliases_raw is not None and not isinstance(aliases_raw, list):
            raise CodedValueError(
                f"cards[{slug!r}].aliases must be a list",
                code="invalid_body", field=f"cards[{slug}].aliases",
            )
        aliases: list[str] = []
        seen_alias: set[str] = set()
        for a in aliases_raw or []:
            alias = str(a).strip()
            norm = _normalize(alias)
            if not alias or not norm or norm in seen_alias:
                continue
            if is_generic_tender(alias):
                raise CodedValueError(
                    f"cards[{slug!r}].aliases: {alias!r} is a generic tender "
                    "word and cannot identify one card (it would auto-resolve "
                    "every receipt paying by that tender)",
                    code="card_alias_generic",
                    card=slug, alias=alias,
                )
            seen_alias.add(norm)
            aliases.append(alias)
        if aliases:
            out["aliases"] = aliases
        if entry.get("active") is False:
            out["active"] = False
        cleaned[slug] = out
    _validate_card_parents(cleaned, known)
    return cleaned


def _validate_card_parents(cleaned: dict[str, dict], known: dict | None) -> None:
    """The account tree, checked once the whole map is known (item 147).

    A ``parent`` names the account a card sits under, by card key, and five
    things make it refusable. Each one is a state a person can type into
    Settings, and each gets its own code (item 130) so the screen can say
    which in Portuguese: the card itself, a key no card owns, a deactivated
    account, a loop, and a second level. The last is the owner's ruling
    rendered as a constraint: "only 2838 has subcards, no where else" means
    an account has subcards and a subcard has none, so a card that is under
    an account can never be an account.

    The checks run over the payload plus ``known`` (see the caller docstring),
    never over a card's own claim about itself.
    """
    universe: dict[str, dict] = {**(known or {}), **cleaned}

    def parent_of(slug: str) -> str:
        entry = universe.get(slug) or {}
        return str(entry.get("parent") or "").strip()

    for slug, entry in cleaned.items():
        parent = str(entry.get("parent") or "").strip()
        if not parent:
            continue
        if parent == slug:
            raise CodedValueError(
                f"cards[{slug!r}].parent cannot be the card itself",
                code="card_parent_self", card=slug,
            )
        if parent not in universe:
            raise CodedValueError(
                f"cards[{slug!r}].parent {parent!r} is not a card in this "
                "registry; define the account card first",
                code="card_parent_unknown", card=slug, parent=parent,
            )
        seen = {slug}
        walk = parent
        while walk and walk in universe:
            if walk in seen:
                raise CodedValueError(
                    f"cards[{slug!r}].parent {parent!r} closes a loop back "
                    f"onto {walk!r}",
                    code="card_parent_cycle",
                    card=slug, parent=parent, through=walk,
                )
            seen.add(walk)
            walk = parent_of(walk)
        if universe[parent].get("active") is False:
            raise CodedValueError(
                f"cards[{slug!r}].parent {parent!r} is inactive; reactivate "
                "the account before putting a card under it",
                code="card_parent_inactive", card=slug, parent=parent,
            )
        grandparent = parent_of(parent)
        if grandparent:
            raise CodedValueError(
                f"cards[{slug!r}].parent {parent!r} is itself under "
                f"{grandparent!r}; an account has subcards and a subcard has "
                "none",
                code="card_parent_not_top_level",
                card=slug, parent=parent, grandparent=grandparent,
            )


def card_parents(cards: dict[str, Card]) -> dict[str, str]:
    """``{subcard key: account key}`` for the cards that sit under an account.

    The READ side of the tree, and tolerant the way `cards_from_setting` is: a
    link survives only when the account is a different card that is present,
    active, and not itself under an account. A blob that never met the
    validator (an old batch snapshot, a hand-edited settings row) therefore
    yields a flatter registry rather than a broken view, which is the same
    bargain every other stored-shape reader here makes.
    """
    out: dict[str, str] = {}
    for key, card in cards.items():
        parent = (card.parent or "").strip()
        if not parent or parent == key or parent not in cards:
            continue
        account = cards[parent]
        if not account.active or (account.parent or "").strip():
            continue
        out[key] = parent
    return out


def cards_to_setting(cards: dict[str, Card]) -> dict:
    """Serialize a composed registry into the stored settings/config map
    shape (the inverse of `cards_from_setting`). Field storage matches
    `normalize_cards_setting`'s cleaned output: empty fields omitted,
    `active` stored only when False. Used to SNAPSHOT the composed registry
    into a batch's run config, so the batch resolves cards from a fixed,
    replayable state (settings edits reach it only via the explicit
    refresh-master-data pass)."""
    out: dict[str, dict] = {}
    for key, card in cards.items():
        entry: dict = {}
        if card.label:
            entry["label"] = card.label
        if card.label_pt:
            entry["label_pt"] = card.label_pt
        if card.digits:
            entry["digits"] = list(card.digits)
        if card.aliases:
            entry["aliases"] = list(card.aliases)
        if card.entity:
            entry["entity"] = card.entity
        if card.person:
            entry["person"] = card.person
        if card.parent:
            entry["parent"] = card.parent
        if card.default_cost_center:
            entry["default_cost_center"] = card.default_cost_center
        if card.zoho_account:
            entry["zoho_account"] = card.zoho_account
        if card.currency:
            entry["currency"] = card.currency
        if not card.active:
            entry["active"] = False
        out[key] = entry
    return out


def cards_from_setting(raw: object) -> dict[str, Card]:
    """Build Card objects from a stored cards map (settings or a batch
    config snapshot). Tolerant of a malformed blob (returns {}), because a
    stored config must never be able to break a view."""
    if not isinstance(raw, dict):
        return {}
    cards: dict[str, Card] = {}
    for slug, entry in raw.items():
        key = str(slug).strip()
        if key and isinstance(entry, dict):
            cards[key] = _card_from_setting(key, entry)
    return cards


def learnable_hint_tokens(hint: str) -> tuple[str | None, str | None, str | None]:
    """How an observed payment hint may be persisted onto a card entry:
    ``(digit, alias, refusal_reason)``.

    An operator assigning "this hint is that card" teaches the registry the
    hint's IDENTIFYING tokens — deterministic persistence, never inference:

    * A hint with exactly ONE digit run contributes that run as a card
      digit ("Visa ...1672" teaches 1672). A hint with SEVERAL runs never
      teaches a digit: there is no deterministic way to tell the card
      number from expiry / auth / BIN noise ("Visa 1672 exp 12/2026"
      would have taught 2026 and mis-resolved every future hint printing
      that year; masked-PAN BIN fragments cross-match unrelated cards —
      R3 adversarial review). Such a hint is learned as an EXACT-string
      alias instead, so the same printed hint resolves next month while
      nothing else does.
    * A digitless, non-generic hint ("CorpServ") becomes an alias.
    * A generic tender word or phrase ("Visa", "Cartão de crédito") is
      REFUSED: persisting it would auto-resolve every future receipt
      paying by that tender onto one card (owner ruling 2026-08-21). The
      batch-scoped exact assignment still applies; only the learning is
      withheld.
    """
    text = (hint or "").strip()
    if not text:
        return None, None, "empty hint"
    if is_generic_tender(text):
        return None, None, (
            "generic tender word; identifies a payment network, not one "
            "card, so the assignment applies to this batch only"
        )
    # Item 87: a run followed by a mask character is a card's leading BIN
    # ("42463153XXXXXX38"), which `_card_keys` skips since item 69 round B.
    # Taught as a digit it could never resolve the same hint again, so it
    # is not a card number here either and the hint learns as its string.
    runs = [
        m.group()
        for m in re.finditer(r"\d{3,8}", text)
        if not (m.end() < len(text) and text[m.end()] in _MASK_CHARS)
    ]
    if len(runs) == 1:
        return runs[0], None, None
    return None, text, None


def stamp_card_entities(
    receipts: list, cards: dict[str, Card], hints: dict | None = None
) -> list:
    """Receipts with each one's legal entity resolved from its own payment
    hint, where a card identifies it: an exact hint assignment
    (``hints``, the batch's operator-confirmed hint -> card key map) wins,
    then `resolve_card` on the hint with ambiguity REFUSED (two matching
    cards = review, not guess). A receipt whose card carries no entity, or
    whose hint resolves no card, keeps its current entity. Runs post-OCR
    (hints only exist after extraction), before categorization, so learned
    (entity, vendor) lookups see the card-resolved entity."""
    if not cards and not hints:
        return receipts
    out = []
    for r in receipts:
        card = resolve_hinted_card(r.payment_mode, cards, hints)
        if card is not None and card.entity and card.entity != r.legal_entity_id:
            out.append(replace(r, legal_entity_id=card.entity))
        else:
            out.append(r)
    return out


def resolve_hinted_card_ex(
    observed: str | None, cards: dict[str, Card], hints: dict | None = None
) -> "tuple[Card | None, bool]":
    """``(card, ambiguous)`` for a batch payment hint: the batch's exact
    hint->card assignment first (operator-confirmed, matches the exact
    stored string — the only path a generic tender word can take), then
    `resolve_card` in the strict R3 contract (ambiguity refused; an alias
    cannot override contradicting digits). ``ambiguous`` is True when two
    or more cards matched and the refusal is WHY there is no card — the
    money paths use it to also refuse their own fallback guessing."""
    text = (observed or "").strip()
    if not text:
        return None, False
    key = (hints or {}).get(text)
    if key:
        card = cards.get(str(key))
        if card is not None and card.active:
            return card, False
    resolved = resolve_card(
        text, cards, on_ambiguity="none", strict_alias_with_digits=True
    )
    if resolved is not None:
        return resolved, False
    loose = resolve_card(
        text, cards, on_ambiguity="first", strict_alias_with_digits=True
    )
    return None, loose is not None


def resolve_hinted_card(
    observed: str | None, cards: dict[str, Card], hints: dict | None = None
) -> Card | None:
    """The card half of `resolve_hinted_card_ex` (None = unresolved)."""
    return resolve_hinted_card_ex(observed, cards, hints)[0]


def _card_from_setting(slug: str, entry: dict) -> Card:
    return Card(
        key=slug,
        label=str(entry.get("label") or "").strip(),
        label_pt=(str(entry["label_pt"]).strip() if entry.get("label_pt") else None),
        digits=tuple(str(d) for d in (entry.get("digits") or [])),
        aliases=tuple(str(a) for a in (entry.get("aliases") or [])),
        entity=str(entry.get("entity") or "").strip(),
        person=str(entry.get("person") or "").strip(),
        parent=str(entry.get("parent") or "").strip(),
        default_cost_center=str(
            entry.get("default_cost_center") or ""
        ).strip(),
        zoho_account=(
            str(entry["zoho_account"]).strip()
            if str(entry.get("zoho_account") or "").strip()
            else None
        ),
        currency=str(entry.get("currency") or "").strip().upper(),
        active=entry.get("active") is not False,
        source=SOURCE_SETTINGS,
    )


def _find_by_tokens(
    cards: dict[str, Card], digit_keys: set[str], alias_norm: str
) -> str | None:
    """The key of the existing card a legacy/preset identity belongs to:
    digit-token intersection first, then normalized-alias equality."""
    for key, card in cards.items():
        if digit_keys and (card.digit_keys() & digit_keys):
            return key
        if alias_norm and any(_normalize(a) == alias_norm for a in card.aliases):
            return key
    return None


def _legacy_slug(legacy_key: str) -> str:
    """A stable slug for a card synthesized from a legacy map key: keep the
    key itself when it already reads like a slug, else 'card-<key>'."""
    key = legacy_key.strip()
    return key if not key.isdigit() else f"card-{key}"


def _fill(card: Card, **updates: object) -> Card:
    """`replace`, but only into fields that are still empty (composition is
    fill-only: an earlier source's explicit value always wins)."""
    kwargs: dict = {}
    for fname, value in updates.items():
        if value in (None, "", ()):
            continue
        current = getattr(card, fname)
        if fname == "digits":
            merged = list(card.digits)
            for d in value:  # type: ignore[union-attr]
                if d not in merged:
                    merged.append(d)
            kwargs[fname] = tuple(merged)
        elif fname == "aliases":
            merged = list(card.aliases)
            norms = {_normalize(a) for a in merged}
            for a in value:  # type: ignore[union-attr]
                if _normalize(a) not in norms:
                    merged.append(a)
                    norms.add(_normalize(a))
            kwargs[fname] = tuple(merged)
        elif current in (None, "", ()):
            kwargs[fname] = value
    return replace(card, **kwargs) if kwargs else card


def effective_cards(
    settings: dict | None, presets: list[CardPreset] | None = None
) -> dict[str, Card]:
    """The composed card registry: ``settings["cards"]`` first, then the
    legacy ``card_entities`` / ``card_accounts`` maps, then the ``/data``
    presets file, merged by digit-token identity.

    Read-time composition IS the migration: with ``settings["cards"]``
    empty the result carries exactly the legacy data (equivalence is
    pinned by tests), and an explicit card entry wins field by field.
    Deterministic order: settings entries in stored order, then legacy
    keys in stored order, then presets in file order.
    """
    s = settings or {}
    cards: dict[str, Card] = {}
    for slug, entry in (s.get("cards") or {}).items():
        if isinstance(entry, dict) and str(slug).strip():
            cards[str(slug).strip()] = _card_from_setting(str(slug).strip(), entry)

    def fold(legacy_key: str, **updates: object) -> None:
        key = legacy_key.strip()
        if not key:
            return
        # A legacy key carries its digit runs as digit identity ("card-2838"
        # and "2838/1672" digit-match like "2838" did in
        # `_card_key_matches`'s token path) and, when not purely digits,
        # the full key as an alias (exact + suffix observed strings). The
        # key's OWN identity rides in `updates` so a token-merge into an
        # existing card keeps every identity the legacy map had — a
        # composite "2838/1672" account key must not lose "1672" when it
        # merges into a card the entities map created as "2838".
        updates = dict(
            updates,
            digits=tuple(re.findall(r"\d{3,}", key)),
            # A generic-tender legacy key ("Visa") must not become a
            # matchable alias — the owner ruling applies to the legacy
            # maps too (its entity/account fields still compose; only the
            # word loses identifying power).
            aliases=(
                () if key.isdigit() or is_generic_tender(key) else (key,)
            ),
        )
        digit_keys = _card_keys(key)
        alias_norm = "" if key.isdigit() else _normalize(key)
        existing = _find_by_tokens(cards, digit_keys, alias_norm)
        if existing is not None:
            cards[existing] = _fill(cards[existing], **updates)
            return
        slug = _legacy_slug(key)
        if slug in cards:  # slug collision without token identity: fill
            cards[slug] = _fill(cards[slug], **updates)
            return
        cards[slug] = _fill(Card(key=slug, source=SOURCE_LEGACY), **updates)

    for key, entity in (s.get("card_entities") or {}).items():
        if str(entity or "").strip():
            fold(str(key), entity=str(entity).strip())
    for key, account in (s.get("card_accounts") or {}).items():
        if str(account or "").strip():
            fold(str(key), zoho_account=str(account).strip())

    for preset in presets or []:
        digit_keys = _card_keys(preset.account_id) | _card_keys(preset.key)
        existing = _find_by_tokens(cards, digit_keys, _normalize(preset.key))
        acct = preset.account_id.strip()
        updates = dict(
            label=preset.label,
            label_pt=preset.label_pt,
            entity=preset.legal_entity,
            currency=preset.currency,
            # "card-2838" carries its digit runs as digit identity AND the
            # full label as an alias (exact/suffix observed strings) —
            # unless the label is a bare generic tender word.
            digits=tuple(re.findall(r"\d{3,}", acct)),
            aliases=(
                (acct,)
                if acct and not acct.isdigit() and not is_generic_tender(acct)
                else ()
            ),
        )
        if existing is not None:
            cards[existing] = _fill(cards[existing], **updates)
            continue
        if preset.key in cards:
            cards[preset.key] = _fill(cards[preset.key], **updates)
            continue
        cards[preset.key] = _fill(
            Card(key=preset.key, source=SOURCE_PRESET), **updates
        )
    return cards


def resolve_card(
    observed: str | None,
    cards: dict[str, Card],
    *,
    on_ambiguity: str = "first",
    strict_alias_with_digits: bool = False,
) -> Card | None:
    """The card an observed string identifies, or None.

    ``observed`` is any card-bearing string the pipeline sees: a statement
    account label ("2838 - May 2026"), a Zoho payment-mode label
    ("1 - CorpServ 2838/1672 (Chase)"), or an OCR payment hint
    ("Visa ...1672"). Two tiers, digit tokens first:

    1. digit-token intersection (`_card_keys`, the matcher's own
       extractor). A masked PAN ("5412 75** **** 3456") contributes ONLY
       its last digit run: the earlier runs are BIN/middle fragments that
       cross-match unrelated cards (R3 adversarial review).
    2. alias match: normalized equality, suffix, or whole-word token.
       A generic-tender alias never matches, wherever it was stored —
       the write paths reject them, and this read-side skip keeps a
       legacy/pre-existing stored one from resolving anyway.

    Generic tender words ("Visa", "Cartão de crédito", "cash") carry no
    digit token and are never matchable aliases, so they resolve to None
    by design: review, not guess. Inactive cards never resolve.

    ``on_ambiguity``: "first" keeps the legacy first-match-in-order
    semantics the old per-map loops had (used by the R1 compat shims);
    "none" returns None when 2+ distinct cards match at the winning tier
    (the review-flow contract: ambiguity surfaces instead of guessing).

    ``strict_alias_with_digits`` (the R3 hint-chain contract): when the
    observed string CARRIES digit runs but none matched a card, only an
    exact normalized-equality alias may resolve — a word-token alias must
    not override the contradicting digits ("CorpServ 2222" with card
    CorpServ=1111 is a different physical card; review, not guess).
    """
    if not observed or not observed.strip():
        return None
    live = {k: c for k, c in cards.items() if c.active}
    if not live:
        return None
    if "*" in observed:
        runs = re.findall(r"\d{3,8}", observed)
        obs_keys = _card_keys(runs[-1]) if runs else set()
    else:
        obs_keys = _card_keys(observed)
    if obs_keys:
        digit_hits = [c for c in live.values() if c.digit_keys() & obs_keys]
        if len(digit_hits) == 1:
            return digit_hits[0]
        if digit_hits:
            return digit_hits[0] if on_ambiguity == "first" else None
    # Note #60: a masked two-digit ending ("XXXXXX38") names the card when
    # exactly ONE active card ends in it. Two cards sharing the ending is a
    # contest, never a guess. The ending is printed digits, so, like a
    # contradicting last-4, it keeps a word alias from overriding it.
    ending = None if obs_keys else masked_short_ending(observed)
    ending_hits = cards_ending_in(ending, live) if ending else []
    exact_only = strict_alias_with_digits and (bool(obs_keys) or bool(ending))
    obs_norm = _normalize(observed)
    obs_tokens = set(obs_norm.split())
    alias_hits: list[Card] = []
    exact_hits: list[Card] = []
    for card in live.values():
        matched = exact = False
        for alias in card.aliases:
            a = _normalize(alias)
            if not a or is_generic_tender(alias):
                continue
            if obs_norm == a:
                matched = exact = True
                break
            if not exact_only and (
                obs_norm.endswith(" " + a)
                or (" " not in a and a in obs_tokens)
            ):
                matched = True  # keep looking: a later alias may be exact
        if matched:
            alias_hits.append(card)
        if exact:
            exact_hits.append(card)
    if ending:
        # An operator who taught this exact printed string decided it; the
        # ending is only inference, so it comes second.
        if len(exact_hits) == 1:
            return exact_hits[0]
        if len(ending_hits) == 1:
            return ending_hits[0]
        if ending_hits:
            return ending_hits[0] if on_ambiguity == "first" else None
    if len(alias_hits) == 1:
        return alias_hits[0]
    # Item 87: a whole-string alias is what an operator's assignment
    # teaches, and it names ONE card. Several cards sharing a word alias
    # ("Corp") also match "Paid via Corp Services card" by token, which
    # left the taught card ambiguous forever: the strip said "learned"
    # and the same hint came back next month.
    if len(exact_hits) == 1:
        return exact_hits[0]
    if alias_hits:
        return alias_hits[0] if on_ambiguity == "first" else None
    return None


def entity_for(observed: str | None, cards: dict[str, Card]) -> str | None:
    """The legal entity the observed card string resolves to, or None.

    Field-aware: only entity-bearing cards participate, mirroring the old
    per-map scan (an entity lookup only ever consulted `card_entities`
    keys). Without the filter, a digit hit on an accounts-only card would
    shadow an alias hit on the entity-bearing one and silently disarm the
    COA gate — the has_coa:false class the 2026-08-06 fix killed.
    """
    scoped = {k: c for k, c in cards.items() if c.entity}
    card = resolve_card(observed, scoped)
    return card.entity if card else None


def zoho_account_for(observed: str | None, cards: dict[str, Card]) -> str | None:
    """The Zoho account the observed card string resolves to, or None.
    Field-aware like `entity_for`: only account-bearing cards participate.
    """
    scoped = {k: c for k, c in cards.items() if c.zoho_account}
    card = resolve_card(observed, scoped)
    return card.zoho_account if card else None


def resolve_account_map(
    observed: str | None, mapping: dict | None
) -> str | None:
    """Conservative ``{key: account}`` resolution for MONEY paths (the
    journal's balancing credit and its advisories): exact key first, then
    BARE-DIGIT keys only, matching iff exactly one mapping key's digit
    form appears among the observed label's digit tokens.

    Deliberately narrower than `resolve_card` (Cards R2 adversarial
    review, 2026-08-21, all three scenarios executed): composing cards
    from a label-keyed map merged unrelated cards on incidental shared
    year tokens, first-match ambiguity guessed between cards, and
    single-word keys acted as wildcards — each turning the old VISIBLE
    ``Card: ...`` placeholder into a silently wrong posting. Here a
    label-shaped key keeps the exact-only semantics it always had, a
    bare-digit key ("2838") matches the label that prints its number
    ("2838 - May 2026"), and ANY ambiguity returns None so the export
    keeps the placeholder: a visible gap beats silent wrong money (B4).
    """
    if not observed or not observed.strip() or not mapping:
        return None
    exact = mapping.get(observed)
    if exact:
        return str(exact)
    obs_keys = _card_keys(observed)
    if not obs_keys:
        return None
    hits: list[str] = []
    for key, account in mapping.items():
        k = str(key).strip()
        if not (k and account and k.isdigit()):
            continue
        variants = {k.lstrip("0") or "0", k[-4:].lstrip("0") or "0"}
        if variants & obs_keys:
            hits.append(str(account))
    return hits[0] if len(set(hits)) == 1 else None


def legacy_card_accounts(cards: dict[str, Card]) -> dict[str, str]:
    """The composed registry flattened back to the ``{digit: zoho_account}``
    map shape the exports consume (`cfg["expense"]["card_accounts"]`).

    Snapshot compatibility, precisely: with settings cards empty, a
    digit-keyed legacy map ("2838") reproduces byte-identically; a
    composite key ("2838/1672") flattens to one entry PER digit run,
    which the export matches strictly wider than the old composite key
    did; a digitless key drops — it could never match in the export's
    last4 comparison anyway. An inactive settings card suppresses its
    digits by design (deactivation means "stop resolving this card").
    """
    flat: dict[str, str] = {}
    for card in cards.values():
        if not (card.active and card.zoho_account):
            continue
        for digit in card.digits:
            flat.setdefault(digit, card.zoho_account)
    return flat
