"""Canonical merchant registry — settings-backed, seeded, self-improving.

A human-editable registry stored under `settings["merchants"]` (like
`card_accounts` / `entities`), the highest-priority DETERMINISTIC source
for three facts about a receipt's merchant:

  * the canonical DISPLAY name, so "COMERCIO DE X LTDA", "X Ltda", and a
    fuzzy OCR variant all read as one brand on the grid and the export,
  * a default category / Zoho account for that brand, and
  * a default COST CENTER for it (backlog item 47), the project or purpose
    this brand's spend belongs to.

Consulted in `generate_expenses` and, since note item M1 (2026-09-18), for
a month's receiptless charges (`categorize_charges`); `reconcile()` itself
never sees it. Precedence for the CATEGORY: a reviewer override > the
registry default > learned memory > the model. The ACCOUNT of a merchant
with a registry default comes from the (company, vendor) rule memory holds
for the receipt's company (`categorize._registry_account`), so one
merchant keeps one category while its account varies by company, which is
Dirk's 2026-09-18 description of how the books work. An empty registry
resolves nothing, so a tenant with no `merchants` key behaves exactly as
before.

Shape:
    settings["merchants"] = {
        "<canonical name>": {
            "aliases": ["raw pattern", ...],   # extra strings to match on
            "category": "<a bucket, or a curated GL leaf code>" | None,
            "zoho_account": "<chart label>" | None,
            "multi_category": True,            # optional (2026-08-19)
            "cost_center": "<defined name>" | None,   # optional (item 47)
            "card_key": "<card key>",          # optional (note item M2)
            "card_key_learned": True,          # optional, machine-set
            "cards_seen": ["<card key>", ...], # optional, machine-kept
            "profile": "<free prose>",         # optional (note item M4)
        },
        ...
    }

A `multi_category` merchant (backlog item 8) decouples the registry's two
facts: the canonical NAME still resolves (spelling stability), but no
default category/account is stamped — the vendor legitimately books to
different categories, so each receipt is judged on its own contents
(learned/LLM path) and the grid's variance chip makes the outcome
auditable. It does NOT suppress ``cost_center``: a vendor that books to
several categories can still belong wholly to one project, and the two
dimensions are deliberately independent (item 47 D2 refuses category as a
cost-center resolver for exactly that reason).

``cost_center`` is stored as typed and is NOT checked against the
cost-center registry here: merchants and cost centers are edited
independently, so the edit ORDER must not matter. A name the registry does
not define fails to resolve at resolution time and leaves the row
unassigned, rather than stamping a centre nobody defined.

``card_key`` (note item M2, 2026-09-18) is the card this brand's spend is
exclusively on, when it has one: the last link of the row's card chain
(`web/service.resolve_batch_row_cards`), consulted only for a receipt that
prints no card number, names no assigned hint word, and is not remembered
from an earlier month. Like ``cost_center`` it is stored as typed and is NOT
checked against the card registry, so the edit ORDER of cards and merchants
does not matter; a key no card defines resolves to nothing and the row stays
uncarded rather than being stamped with a card nobody has.

``cards_seen`` is the machine's own record of every card this merchant's
receipts actually resolved to, accumulated at sign-off, and ``card_key_learned``
marks a ``card_key`` the machine wrote from it rather than a person. The
learner sets a key only while ``cards_seen`` holds exactly ONE card, drops a
learned key the moment a second card appears, and never touches a key an
editor typed. Two cards are a fact about the merchant, not a conflict to
resolve by guessing.

``profile`` (note item M4, 2026-09-20) is the unstructured knowledge beside
all of the above: what the business actually buys from this merchant, on
which card and for which company, anything Criss or Dirk would tell a new
bookkeeper on their first day. Free prose, because the whole point is the
part that does not fit a field. It is read by the categorizer as CONTEXT for
that merchant's receipts and by nothing else: no resolver keys on it, no
review state fires on it, and it never carries a category or an account of
its own. Per `rule_untrusted_inbound` it is fenced as untrusted data in
every prompt that carries it (`llm/client._merchant_profile_block`) — a
profile informs the category, it never instructs the model — because the
learning path may append to it and a machine line is only as trustworthy as
the receipts it was read from. Lines a person wrote and lines the tool
appended are told apart by the ``[tool YYYY-MM-DD]`` prefix
(`append_machine_note`); the tool only ever appends, so an editor's prose is
never rewritten by the machine.

Matching (`resolve`): normalized-exact on the canonical name or any alias,
then rapidfuzz `token_set_ratio >= threshold` over the same strings, else
unmatched. Both the receipt's extracted `vendor_clean` and its raw
`detected_vendor` (plus a deterministic clean of the raw) are tried as
probes, so a path that never produced a `vendor_clean` still resolves.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from .matching.deterministic import _normalize as normalize_vendor
from .category_vocabulary import recognize as recognize_category
from .error_codes import CodedValueError
from .vendor_names import _LEGAL_SUFFIXES, clean_vendor_name

# token_set_ratio (0-100) at or above this counts as a confident brand
# match. High enough that only a genuine spelling / OCR variant of a known
# alias clears it, not an unrelated merchant sharing one common token.
DEFAULT_FUZZY_THRESHOLD = 88.0

# Backlog item 117 (2026-09-17 voids audit). token_set_ratio scores 100
# whenever one side's words are a subset of the other's, so a one-word
# alias like "Mercado" made every vendor containing that word a certain
# hit: "Mercado Livre" filed as NOBRE ATACADO / Meals, "Gasolina Comum" as
# RAC. The rules below close it, mirroring the card registry's generic
# tender words (cards.GENERIC_TENDER_WORDS):
#
#   * An alias built only of generic words (a kind of shop, a product, a
#     fuel) names no merchant. The resolver ignores it and the settings
#     PUT refuses to add a new one. A merchant's CANONICAL name is never
#     ignored: that is the name somebody chose for it.
#   * A fuzzy hit needs the merchant's FIRST distinctive word (where the
#     brand sits; place names trail) in the vendor, and is discounted by
#     the share of the vendor's distinctive words the merchant does not
#     cover. Generic words, joining words, legal forms, single letters and
#     bare numbers are not distinctive, so "O Castelinho Bar" still reads
#     as O CASTELINHO and "Auto Posto Pimentel" as AUTO POSTO PIMENTEL SAO
#     JOSE, while "Auto Posto Shell" and "Posto Sao Jose" no longer do.
#   * A vendor whose distinctive words are exactly the merchant's also
#     matches, whatever generic words surround them ("KI-MASSA CAFE" is
#     PADARIA E PASTELARIA KI-MASSA).
#
# Trade-offs, named: every one-word alias the live registry carried is a
# generic word, so none of them matches on its own any more (the merchants
# still resolve by their canonical names); a brand plus a place the merchant
# does not carry ("Starbucks Paulista") and a vendor naming only part of a
# longer merchant plus a shop word ("NOBRE ATACADO E VAREJO" for NOBRE
# ATACADO SAO JOSE DA C) fall through to the model instead of guessing,
# because the same shape also reads "Farmacia Pimentel" as the petrol station.
GENERIC_MERCHANT_WORDS = frozenset({
    # PT kinds of shop
    "supermercado", "supermecado", "hipermercado", "mercado",
    "mercadinho", "minimercado", "mercearia", "atacado", "atacadao",
    "varejo", "padaria", "pastelaria", "confeitaria", "lanchonete",
    "restaurante", "bar", "boteco", "cafe", "cafeteria", "sorveteria",
    "pizzaria", "churrascaria", "farmacia", "drogaria", "posto", "auto",
    "loja", "comercio", "comercial", "distribuidora", "conveniencia",
    "acougue", "hortifruti", "feira", "quiosque", "hotel", "pousada",
    "estacionamento", "borracharia", "rotisse", "rotisserie",
    "rotisseria",
    # PT products
    "comida", "bebida", "drink", "doce", "bolo", "pao", "paes", "pastel",
    "pasteis", "coxinha", "salgado", "sushi", "peixe", "sorvete", "feijao",
    "tapioca", "caipirinha", "cerveja", "lanche", "almoco", "jantar",
    "gasolina", "alcool", "etanol", "diesel", "combustivel",
    "combustiveis", "esporte", "caldinho", "espetinho", "churrasco",
    # EN
    "sport", "restaurant", "coffee", "pub", "grocery", "market",
    "supermarket", "store", "shop", "gas", "fuel", "food", "bakery",
    "pharmacy", "parking", "taxi",
    # DE / ES / FR
    "supermarkt", "markt", "baeckerei", "backerei", "tankstelle",
    "kiosk", "apotheke", "tienda", "supermarche", "marche", "epicerie",
    "boulangerie", "pharmacie",
})

# Joining words that carry no brand (PT / EN / ES / FR / DE).
_STOPWORDS = frozenset({
    "de", "do", "da", "dos", "das", "e", "o", "a", "os", "as", "em",
    "the", "and", "of", "y", "del", "la", "el", "le", "les", "des", "du",
    "et", "und", "von", "der", "die",
})


def _tokens(text: str | None) -> list[str]:
    """Diacritic-folded normalized words ("SÃO JOSÉ" -> ["sao", "jose"]).
    `normalize_vendor` is ASCII-alnum and would split accented letters."""
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return normalize_vendor(folded).split()


def _is_generic_word(t: str) -> bool:
    """A listed generic word, or its plural ("mercados", "lojas")."""
    return t in GENERIC_MERCHANT_WORDS or (
        len(t) > 3 and t.endswith("s") and t[:-1] in GENERIC_MERCHANT_WORDS
    )


def _distinctive(tokens: list[str]) -> list[str]:
    """The words that can identify a merchant: not a joining word, a legal
    form ("Inc", "Ltda"), a generic word, a single letter or a bare number."""
    return [
        t for t in tokens
        if len(t) > 1 and not t.isdigit()
        and t not in _STOPWORDS and t not in _LEGAL_SUFFIXES
        and not _is_generic_word(t)
    ]


def _key_words(tokens: list[str]) -> list[str]:
    """The distinctive words, else the numbers: a brand that IS a number
    ("99", "Posto 10") is identified by it."""
    return _distinctive(tokens) or [
        t for t in tokens if t.isdigit() and len(t) > 1
    ]


def is_generic_alias(text: str | None) -> bool:
    """True when an alias names no merchant: at least one generic word and
    nothing distinctive ("Mercado", "Supermercado", "Comida e Bebida")."""
    tokens = _tokens(text)
    return (
        any(_is_generic_word(t) for t in tokens)
        and not _distinctive(tokens)
    )


# One word covers another when it is the same word or a spelling variant of
# it. Looser than the whole-name threshold on purpose: a one-letter OCR slip
# in a six-letter word ("openal" / "openai") is 83, and the whole name must
# still clear DEFAULT_FUZZY_THRESHOLD (or share every distinctive word).
_WORD_VARIANT_RATIO = 80.0


def _covers(
    word: str, words: list[str] | set[str],
    ratio: float = _WORD_VARIANT_RATIO,
) -> bool:
    return word in words or any(fuzz.ratio(word, w) >= ratio for w in words)


def _fuzzy_score(
    probe_norm: str, cand_norm: str,
    probe_tokens: list[str], cand_tokens: list[str], threshold: float,
) -> float:
    """The fuzzy tier's score for one probe x candidate (0-100)."""
    probe_keys = _key_words(probe_tokens)
    cand_keys = _key_words(cand_tokens)
    if not probe_keys or not cand_keys:
        return 0.0
    if not _covers(cand_keys[0], probe_keys):
        return 0.0
    probe_distinct = _distinctive(probe_tokens)
    cand_distinct = _distinctive(cand_tokens)
    # Same distinctive words on both sides. No whole-name score backs this
    # rule, so a word variant must clear the full threshold here: at 80,
    # "Cafe Americano" (a coffee on an expense report) read as Americanas.
    if probe_distinct and cand_distinct and all(
        _covers(t, cand_distinct, threshold) for t in probe_distinct
    ) and all(_covers(t, probe_distinct, threshold) for t in cand_distinct):
        return 100.0
    score = fuzz.token_set_ratio(probe_norm, cand_norm)
    if score < threshold:
        return score
    cand = set(cand_tokens)
    covered = total = 0
    for t in probe_keys:
        total += len(t)
        if _covers(t, cand):
            covered += len(t)
    return score * covered / total


@dataclass(frozen=True)
class MerchantMatch:
    """A registry hit for one receipt's merchant."""

    canonical_name: str
    category: str | None
    zoho_account: str | None
    matched_alias: str        # the registry string (canonical or alias) that matched
    score: float              # 100.0 for an exact hit, else the token_set_ratio
    kind: str                 # "exact" | "fuzzy"
    source: str = "registry"
    # Item 47: the brand's default project / purpose. None when unset, and
    # unaffected by `multi_category` (which decouples CATEGORY only).
    cost_center: str | None = None
    # Item 115: whether this merchant is marked multi-category. `category`
    # is None for that merchant AND for a naming-only one, and the two are
    # not the same instruction: a multi-category merchant says "judge every
    # receipt on its own items", so a remembered category must not flatten
    # its lines either.
    multi_category: bool = False
    # Note item M2: the card this brand's spend is exclusively on, when the
    # registry carries one. None when unset, and unaffected by
    # `multi_category` (which decouples CATEGORY only) for the same reason
    # `cost_center` is: a vendor can book to several categories and still be
    # paid from one card.
    card_key: str | None = None
    # Note item M4: the merchant's free-prose profile, when it carries one.
    # Context for the categorizer's prompts and nothing else; never a
    # resolver. Carried on a `multi_category` merchant too, where it is worth
    # the most: a vendor that books to several categories is exactly the one
    # whose receipts need the background a field cannot hold.
    profile: str | None = None


class MerchantRegistry:
    """Read-model over `settings["merchants"]`. Immutable after construction;
    rebuild it when settings change (cheap — the registry is small)."""

    def __init__(
        self,
        merchants: dict | None = None,
        *,
        threshold: float = DEFAULT_FUZZY_THRESHOLD,
    ):
        self.threshold = threshold
        # canonical -> entry (category / zoho_account)
        self._entries: dict[str, dict] = {}
        # normalized string -> (canonical, original string) for exact lookup
        self._exact: dict[str, tuple[str, str]] = {}
        # (normalized, original, canonical, folded words) for the fuzzy sweep
        self._candidates: list[tuple[str, str, str, list[str]]] = []

        # Deterministic ordering: sort by canonical so a first-wins result on
        # any normalized-key or fuzzy-score collision is stable across runs.
        source = merchants if isinstance(merchants, dict) else {}
        for canonical_raw in sorted(source.keys(), key=str):
            entry = source[canonical_raw]
            if not isinstance(entry, dict):
                continue
            canonical = str(canonical_raw).strip()
            if not canonical:
                continue
            self._entries[canonical] = entry
            aliases = [
                a for a in (entry.get("aliases") or [])
                if not is_generic_alias(str(a or ""))
            ]
            for raw in (canonical, *aliases):
                s = str(raw or "").strip()
                if not s:
                    continue
                norm = normalize_vendor(s)
                if not norm:
                    continue
                self._exact.setdefault(norm, (canonical, s))
                self._candidates.append((norm, s, canonical, _tokens(s)))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def _probes(self, vendor_clean: str | None, vendor_raw: str | None) -> list[str]:
        """Ordered, de-duped normalized probe strings for one receipt:
        extracted brand first, then a deterministic clean of the raw name,
        then the raw name itself."""
        return [norm for norm, _raw in self._probe_pairs(vendor_clean, vendor_raw)]

    def _probe_pairs(
        self, vendor_clean: str | None, vendor_raw: str | None
    ) -> list[tuple[str, str]]:
        """`_probes` with each probe's source string kept, so the coverage
        rule can fold its diacritics before `normalize_vendor` splits them."""
        seen: set[str] = set()
        out: list[tuple[str, str]] = []
        for raw in (vendor_clean, clean_vendor_name(vendor_raw), vendor_raw):
            norm = normalize_vendor(str(raw)) if raw else ""
            if norm and norm not in seen:
                seen.add(norm)
                out.append((norm, str(raw)))
        return out

    def resolve(
        self, vendor_clean: str | None, vendor_raw: str | None
    ) -> MerchantMatch | None:
        """Return the registry match for a receipt's merchant, or None when
        nothing clears the bar. Exact (normalized-equality) wins over fuzzy;
        the earlier probe (vendor_clean before raw) wins within a tier."""
        if not self._entries:
            return None
        probes = self._probe_pairs(vendor_clean, vendor_raw)
        if not probes:
            return None

        # 1) Exact: normalized equality on any canonical / alias string.
        for norm, _raw in probes:
            hit = self._exact.get(norm)
            if hit:
                canonical, original = hit
                return self._match(canonical, original, 100.0, "exact")

        # 2) Fuzzy: best `_fuzzy_score` across probe x candidate (item 117:
        # token_set_ratio gated on the merchant's lead word and discounted by
        # the vendor's uncovered distinctive words). Strict `>` over the
        # sorted-canonical candidate list keeps ties deterministic.
        best_score = -1.0
        best_canonical: str | None = None
        best_original: str | None = None
        for norm, raw in probes:
            probe_tokens = _tokens(raw)
            for cand_norm, cand_orig, canonical, cand_tokens in self._candidates:
                score = _fuzzy_score(
                    norm, cand_norm, probe_tokens, cand_tokens, self.threshold
                )
                if score > best_score:
                    best_score = score
                    best_canonical = canonical
                    best_original = cand_orig
        if best_canonical is not None and best_score >= self.threshold:
            return self._match(best_canonical, best_original, best_score, "fuzzy")
        return None

    def _match(
        self, canonical: str, original: str, score: float, kind: str
    ) -> MerchantMatch:
        entry = self._entries.get(canonical, {})
        # A multi-category merchant resolves its NAME but never a default
        # category/account: the categorize pass keys the registry stamp on
        # `match.category`, so a None here routes the receipt to the
        # per-receipt judgment (learned/LLM) while the display name stays
        # canonical.
        if entry.get("multi_category"):
            return MerchantMatch(
                canonical_name=canonical,
                category=None,
                zoho_account=None,
                matched_alias=original,
                score=float(score),
                kind=kind,
                cost_center=(entry.get("cost_center") or None),
                multi_category=True,
                card_key=(entry.get("card_key") or None),
                profile=(entry.get("profile") or None),
            )
        category = (entry.get("category") or None)
        return MerchantMatch(
            canonical_name=canonical,
            # Re-validate our OWN store against the vocabulary that store is
            # allowed to hold. `normalize_merchants_setting` has accepted
            # curated leaf codes since #1236 (:532), so filtering here on the
            # eight buckets threw away exactly what the write path had just
            # saved: the rule went inert, the receipt fell through to the LLM
            # at full cost, and nothing errored or logged. That is the shape
            # this whole change set exists to remove, so it may not sit in the
            # reader of the registry.
            category=recognize_category(category),
            zoho_account=(entry.get("zoho_account") or None),
            matched_alias=original,
            score=float(score),
            kind=kind,
            cost_center=(entry.get("cost_center") or None),
            card_key=(entry.get("card_key") or None),
            profile=(entry.get("profile") or None),
        )

    @classmethod
    def from_settings(
        cls, settings: dict | None, *, threshold: float = DEFAULT_FUZZY_THRESHOLD
    ) -> "MerchantRegistry":
        merchants = settings.get("merchants") if isinstance(settings, dict) else None
        return cls(merchants, threshold=threshold)


def normalize_merchants_setting(
    raw: object, *, stored: object = None,
    dropped: list[tuple[str, str]] | None = None,
) -> dict:
    """Validate + clean a `merchants` settings payload into the stored shape.

    Raises ValueError on a malformed structure (the settings PUT surfaces it
    as HTTP 400). Mirrors the `entities` map contract: the whole map replaces
    the stored one, a blank canonical name is dropped, and each entry must be
    a dict. Aliases are trimmed + de-duplicated on their normalized key; a
    category, when given, must be one the tool still knows (either of the two
    live vocabularies) and is otherwise dropped rather than refused.

    ``dropped``, when given, receives one ``(merchant, category)`` pair per
    dropped category so the caller can name the loss in its reply. Callers
    that pass nothing drop silently, which is what the internal callers
    (memory at sign-off, the seed) want.

    ``stored`` (item 117) is the merchant map already saved, passed by the
    settings PUT only. When given, an alias made only of generic words
    ("Mercado") that no stored merchant already carries is refused: it would
    name no merchant, and the resolver ignores it. Aliases already stored
    stay accepted, anywhere in the map, so an editor that sends the whole
    map back (or renames a merchant) never fails on data it did not add.
    Internal callers (memory at sign-off, the seed) pass nothing and are
    unchanged."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise CodedValueError(
            "merchants must be an object of {canonical_name: entry}",
            code="invalid_body",
        )
    already: set[str] | None = None
    if isinstance(stored, dict):
        already = {
            normalize_vendor(str(a or "").strip())
            for e in stored.values() if isinstance(e, dict)
            for a in (e.get("aliases") or [])
        }
    out: dict[str, dict] = {}
    for name, entry in raw.items():
        canonical = str(name or "").strip()
        if not canonical:
            continue
        if not isinstance(entry, dict):
            raise CodedValueError(
                f"merchant {canonical!r} must be an object",
                code="invalid_body", merchant=canonical,
            )
        aliases: list[str] = []
        seen: set[str] = set()
        for a in entry.get("aliases") or []:
            s = str(a or "").strip()
            key = normalize_vendor(s)
            if s and key and key not in seen:
                if (
                    already is not None and key not in already
                    and is_generic_alias(s)
                ):
                    raise CodedValueError(
                        f"merchant {canonical!r} alias {s!r} is a generic "
                        "word (a kind of shop or product, not a merchant "
                        "name), so it would match unrelated vendors; use "
                        "a word from the merchant's own name",
                        code="merchant_alias_generic",
                        merchant=canonical, alias=s,
                    )
                seen.add(key)
                aliases.append(s)
        category = str(entry.get("category") or "").strip() or None
        if category is not None:
            # Two vocabularies are live at once (`category_vocabulary`), and
            # a value from neither is DROPPED, not refused. A settings save
            # replaces the whole map, so one merchant holding a string the
            # server no longer knows would have 400'd the entire save, the
            # cards and entities tabs included, for an edit that never
            # touched it. `dropped` carries the loss out to the reply.
            recognized = recognize_category(category)
            if recognized is None and dropped is not None:
                dropped.append((canonical, category))
            category = recognized
        zoho_account = str(entry.get("zoho_account") or "").strip() or None
        cleaned: dict = {
            "aliases": aliases,
            "category": category,
            "zoho_account": zoho_account,
        }
        # Optional multi-category flag (backlog item 8): stored only when
        # truthy so existing entries keep their exact shape.
        if entry.get("multi_category"):
            cleaned["multi_category"] = True
        # Item 47: the brand's default cost center, stored only when set
        # for the same reason. Not validated against the cost-center
        # registry (edit order must not matter -- see the module docstring).
        cost_center = str(entry.get("cost_center") or "").strip()
        if cost_center:
            cleaned["cost_center"] = cost_center
        # Item 107: where this brand's invoice can be downloaded again
        # ("platform.openai.com", "Chase statements portal"). Stored only
        # when set, for the same reason, and free text on purpose: it is a
        # hint printed next to the charge in the chase list and the request
        # mail, not something the tool follows.
        portal = str(entry.get("receipt_portal") or "").strip()
        if portal:
            cleaned["receipt_portal"] = portal[:200]
        # Note item M2: the card this brand's spend is exclusively on, the
        # machine's record of the cards it has been seen on, and whether the
        # key was learned rather than typed. All three stored only when set,
        # so an entry that has none keeps its exact shape. `card_key` is not
        # checked against the card registry (edit order must not matter --
        # see the module docstring), and `cards_seen` is capped so a long-
        # lived merchant cannot grow the settings blob without bound.
        card_key = str(entry.get("card_key") or "").strip()
        if card_key:
            cleaned["card_key"] = card_key[:64]
        seen_keys: list[str] = []
        for c in entry.get("cards_seen") or []:
            s = str(c or "").strip()[:64]
            if s and s not in seen_keys:
                seen_keys.append(s)
        if seen_keys:
            cleaned["cards_seen"] = sorted(seen_keys)[:32]
        # Only meaningful beside a key, and only as a machine mark: an entry
        # a person typed carries no flag, which is exactly what protects it
        # from the learner.
        if card_key and entry.get("card_key_learned"):
            cleaned["card_key_learned"] = True
        # Note item M4: the merchant's free-prose profile. Stored only when
        # set, for the same reason, and capped generously rather than tightly
        # (`receipt_portal` is a hint, this is prose a bookkeeper writes).
        # Control characters are stripped because the value is rendered in a
        # page and pasted into a prompt; the newlines that separate its lines
        # survive, because the machine-note convention needs them.
        profile = _clean_profile(entry.get("profile"))
        if profile:
            cleaned["profile"] = profile
        out[canonical] = cleaned
    return out


# A profile is prose, so the cap is generous: enough for the paragraph a
# bookkeeper would write plus a year of machine lines, short enough that the
# settings blob stays a settings blob and the prompt stays affordable.
PROFILE_CHARS = 2000

_PROFILE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# A line the TOOL wrote, not a person: "[tool 2026-09-20] seen on 3 cards".
# The prefix is the whole convention — the Memory page dims these lines, the
# categorizer's prompt carries them like any other context, and `append_
# machine_note` only ever adds one, so a person's prose is never rewritten.
MACHINE_NOTE_PREFIX = "[tool "
_MACHINE_NOTE_RE = re.compile(r"^\[tool \d{4}-\d{2}-\d{2}\] ")


def _clean_profile(raw: object) -> str:
    """Normalize a profile value for storage: control characters out,
    trailing whitespace off each line, capped at `PROFILE_CHARS`."""
    text = _PROFILE_CONTROL.sub(" ", str(raw or ""))
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()[:PROFILE_CHARS]


def is_machine_note(line: str | None) -> bool:
    """True for a line the tool appended (`[tool YYYY-MM-DD] ...`)."""
    return bool(_MACHINE_NOTE_RE.match(str(line or "")))


def append_machine_note(profile: object, note: str, *, today: str) -> str:
    """Return `profile` with one machine line appended, or unchanged.

    The learning path may add an OBSERVATION to a merchant's profile; it may
    never edit what a person wrote there. So this only ever appends, and only
    a line marked `[tool <today>]` so the two are told apart on sight.

    Unchanged when the note is empty, when the same note text is already
    present (re-signing a month must not grow the field every time), or when
    the line would not fit under `PROFILE_CHARS` — a full profile keeps the
    prose it has rather than dropping the beginning of it to make room."""
    base = _clean_profile(profile)
    body = " ".join(str(note or "").split())
    if not body:
        return base
    if body in base:
        return base
    line = f"{MACHINE_NOTE_PREFIX}{today}] {body}"
    candidate = f"{base}\n{line}" if base else line
    if len(candidate) > PROFILE_CHARS:
        return base
    return candidate
