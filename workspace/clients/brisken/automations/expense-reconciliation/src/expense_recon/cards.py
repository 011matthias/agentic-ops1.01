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
        "currency": "USD"
      }
    }

``person`` (backlog item 40, owner directive 2026-09-06) is who a card's
expenses belong to: "each card is attributed to a name and therefore
every expense can be attributed to a person. Even the ones injected via
email." Person attribution rides the SAME card chain as ``entity`` — the
LAST link, resolved from whichever card the chain lands on — and NEVER
the mail sender: ``submitted_by`` stays ingest provenance (a claim about
who mailed a file), by explicit owner ruling.

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
from .matching.deterministic import _card_keys, _normalize

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
    if _card_keys(text):
        return False
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    words = _normalize(folded).split()
    return (
        any(w in GENERIC_TENDER_WORDS for w in words)
        and all(
            w in GENERIC_TENDER_WORDS
            or (w.isdigit() and len(w) < _DIGIT_MIN)
            for w in words
        )
    )


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
    runs = re.findall(r"\d{3,8}", text)
    return runs[-1] if runs else None


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
        "zoho_account": card.zoho_account,
        "currency": card.currency,
        "active": card.active,
        "source": card.source,
    }


def normalize_cards_setting(raw: object) -> dict:
    """Validate + clean a ``settings["cards"]`` payload at the edge.

    Same contract family as ``normalize_merchants_setting``: the whole map
    replaces the stored one; a blank card key is silently dropped; a
    malformed entry raises ``ValueError`` (the API answers 400). Stored
    shape keeps only meaningful fields (no empty strings, ``active`` only
    when False) so the settings blob stays small and diffs stay honest.
    """
    if not isinstance(raw, dict):
        raise ValueError("cards must be an object")
    cleaned: dict[str, dict] = {}
    for key, entry in raw.items():
        slug = str(key).strip()
        if not slug:
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"cards[{slug!r}] must be an object")
        out: dict = {}
        for skey in ("label", "label_pt", "entity", "person", "zoho_account"):
            value = str(entry.get(skey) or "").strip()
            if value:
                out[skey] = value
        currency = str(entry.get("currency") or "").strip().upper()
        if currency:
            out["currency"] = currency
        digits_raw = entry.get("digits")
        if digits_raw is not None and not isinstance(digits_raw, list):
            raise ValueError(f"cards[{slug!r}].digits must be a list")
        digits: list[str] = []
        for d in digits_raw or []:
            token = str(d).strip()
            if not token:
                continue
            if not token.isdigit() or not (_DIGIT_MIN <= len(token) <= _DIGIT_MAX):
                raise ValueError(
                    f"cards[{slug!r}].digits entries must be"
                    f" {_DIGIT_MIN}-{_DIGIT_MAX} digit strings, got {token!r}"
                )
            if token not in digits:
                digits.append(token)
        if digits:
            out["digits"] = digits
        aliases_raw = entry.get("aliases")
        if aliases_raw is not None and not isinstance(aliases_raw, list):
            raise ValueError(f"cards[{slug!r}].aliases must be a list")
        aliases: list[str] = []
        seen_alias: set[str] = set()
        for a in aliases_raw or []:
            alias = str(a).strip()
            norm = _normalize(alias)
            if not alias or not norm or norm in seen_alias:
                continue
            if is_generic_tender(alias):
                raise ValueError(
                    f"cards[{slug!r}].aliases: {alias!r} is a generic tender "
                    "word and cannot identify one card (it would auto-resolve "
                    "every receipt paying by that tender)"
                )
            seen_alias.add(norm)
            aliases.append(alias)
        if aliases:
            out["aliases"] = aliases
        if entry.get("active") is False:
            out["active"] = False
        cleaned[slug] = out
    return cleaned


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
    runs = re.findall(r"\d{3,8}", text)
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
    exact_only = strict_alias_with_digits and bool(obs_keys)
    obs_norm = _normalize(observed)
    obs_tokens = set(obs_norm.split())
    alias_hits: list[Card] = []
    for card in live.values():
        for alias in card.aliases:
            a = _normalize(alias)
            if not a or is_generic_tender(alias):
                continue
            if obs_norm == a or (
                not exact_only
                and (
                    obs_norm.endswith(" " + a)
                    or (" " not in a and a in obs_tokens)
                )
            ):
                alias_hits.append(card)
                break
    if len(alias_hits) == 1:
        return alias_hits[0]
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
