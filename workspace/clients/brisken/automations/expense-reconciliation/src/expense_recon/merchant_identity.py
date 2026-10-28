"""One canonical merchant identity for memory, the registry and the export
(backlog item 216, cause 3).

Until this module, three places decided "which merchant is this" on their
own, each from the raw extracted string: memory recall and capture keyed on
`normalize_vendor(detected_vendor)`, and the registry matched
`MerchantRegistry.resolve(vendor_clean, raw)`. A rule written under
`anthropic` never reached a receipt reading `Anthropic, PBC (@anthropic)`,
the per-company account map was consulted only after a registry match, and
one merchant held a rule per spelling (item 170: three spellings, three
rules).

`MerchantIdentityResolver.resolve` is now the one answer. The registry's
curated canonical names and aliases decide first (item 170 ruled a fuzzy
key out as the identity source: 8 wrong canonicals in 8 probes); where the
registry is silent, the identity is the name with its non-merchant parts
taken off, `identity_key`. What those parts are was MEASURED over every
vendor string in the three GL months and 24 months of Zoho Books
descriptors, with Criss's own Zoho vendor name as the check on each merge
(the 2026-09-25 build record in backlog item 216 lists every merge it
makes). Taken off:

  * the trading name after `dba` is kept, the legal name before it dropped
    ("Wispr AI, Inc. (dba Wispr Flow)" is Wispr Flow);
  * a social handle (`(@anthropic)`, `@lovable`);
  * the card network's location tail, a merchant web address plus a state
    code ("OPENAI OPENAI.COM CA", "SERVERPILOT.IO SERVERPILOT.I WA");
  * a web address's `www.` and top-level domain (`BASE44.COM`, `Wix.com`);
  * a phone number (`ADOBE *800-833-6687`);
  * order and invoice references (`MICROSOFT#G172123598`,
    `LinkedIn SN P3060910829`), the same test the matcher uses, except that
    a word glued to an account number keeps the word (`GOOGLE
    *ADS9208169978` is Google Ads, which the first measurement had folded
    into Google LLC);
  * a handle or domain that only repeats the brand ("PROTON AG* PROTON AG");
  * trailing legal forms (`, PBC`, `Inc.`, `FZCO`, `DMCC`, `Ltda`, `SE`).

Deliberately NOT taken off, because the measurement showed each folds two
merchants into one: the part before a `*` (a processor prefix as often as a
brand: `MP *`, `TST*`, `WEB*`, `GOOGLE *CLOUD` against `GOOGLE*PLAY`), a `.ai`
domain (it is the brand word in `Perplexity AI`, `Fireflies AI`, and memory
already holds those rules with the word), and place names. Those spellings
reach their merchant only through a registry alias, which is a person's call
(and the owner's for OpenAI, Anthropic and Lovable).

Pure text plus the registry, no store and no I/O, so memory, the registry
and the learner can all depend on it without a cycle.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .matching.deterministic import _is_reference_token
from .matching.deterministic import _normalize as normalize_vendor
from .vendor_names import _LEGAL_SUFFIXES

# Legal forms the identity drops on top of `vendor_names._LEGAL_SUFFIXES`,
# each seen on a live receipt or a Zoho descriptor: a public-benefit corp
# (Anthropic), UAE free-zone and DMCC companies (Pressmaster), a US
# professional LLC, a European company (SAP SE).
_EXTRA_LEGAL = frozenset({"pbc", "fzco", "fze", "fzllc", "dmcc", "pllc", "se"})
_LEGAL = _LEGAL_SUFFIXES | _EXTRA_LEGAL

# Top-level domains dropped from a web-address-shaped name. `.ai` is left on
# purpose (see the module docstring); `.de` / `.eu` only where the raw text
# still shows the dot, because as bare words they are Portuguese / a region.
_RAW_TLD = re.compile(r"(?<=[A-Za-z0-9])\.(?:com|io|net|org|co|de|eu)\b", re.I)
_TOKEN_TLDS = frozenset({"com", "io", "net", "org", "co"})

# The card network's merchant-location field at the end of a descriptor: the
# merchant's web address (possibly truncated, "g.co/helppay#") or phone
# number, then a two-letter state or province code.
_LOCATION_TAIL = re.compile(
    r"\s+(?:\S*[A-Za-z0-9]\.\S*|\d[\d\-.]{5,}\d)\s+[A-Z]{2}\s*$"
)
# A phone number anywhere ("ADOBE *800-833-6687"): digits with separators,
# seven or more digits in all.
_PHONE = re.compile(r"(?<![\w.])\d{3}[\-.]\d{3}[\-.]?\d{4}(?![\w.])")
_HANDLE = re.compile(r"\(?\s*@[\w.\-]+\s*\)?")
_WWW = re.compile(r"\bwww\.", re.I)
# A word glued to an account number ("GOOGLE *ADS9208169978",
# "LinkedIn ADS2924143124"): the word is the product, the digits are not.
# Three letters at least, so an invoice prefix ("G172123598", "RN36953805")
# still reads as one reference.
_GLUED_WORD = re.compile(r"^([a-z]{3,})(\d{5,})$")


def _pre_clean(text: str) -> str:
    """The raw-text half: what the punctuation still shows."""
    s = html.unescape(str(text))
    s = _LOCATION_TAIL.sub("", s)
    s = _PHONE.sub(" ", s)
    s = _HANDLE.sub(" ", s)
    s = _WWW.sub("", s)
    return _RAW_TLD.sub("", s)


def _unglue(token: str) -> str:
    m = _GLUED_WORD.match(token)
    return m.group(1) if m else token


def _drop_trailing(tokens: list[str]) -> list[str]:
    """Trailing legal forms, bare domains and echoes of an earlier word,
    repeatedly, always keeping at least one word."""
    changed = True
    while changed and len(tokens) > 1:
        changed = False
        last = tokens[-1]
        if last in _LEGAL or last in _TOKEN_TLDS or last in tokens[:-1]:
            tokens = tokens[:-1]
            changed = True
    return tokens


def identity_key(text: str | None) -> str:
    """The key a merchant name is remembered under when the registry does not
    name it: normalized, with the non-merchant parts taken off. Works on a
    raw name and on an already-normalized stored key alike (the stored memory
    keys are normalized, so every token rule also stands without the
    punctuation). Empty for an empty name."""
    if not text:
        return ""
    tokens = normalize_vendor(_pre_clean(text)).split()
    if "dba" in tokens:
        after = tokens[len(tokens) - tokens[::-1].index("dba"):]
        if after:
            tokens = after
    tokens = [_unglue(t) for t in tokens if t != "www"]
    kept = [t for t in tokens if not _is_reference_token(t)]
    tokens = kept or tokens
    return " ".join(_drop_trailing(tokens))


@dataclass(frozen=True)
class MerchantIdentity:
    """Which merchant a name is, and how that was decided.

    `canonical` is the registry's canonical name when the registry resolves
    the merchant, else the name as given. `key` is what memory stores and
    recalls under: the registry canonical's `identity_key` when there is one,
    so every spelling the registry knows lands on one key, else the name's
    own. `source` is "registry" or "name"; `aliases_matched` names the
    registry string that matched (empty for "name")."""

    canonical: str
    key: str
    source: str
    aliases_matched: tuple[str, ...] = ()


class MerchantIdentityResolver:
    """The one merchant resolver: the registry first, else `identity_key`.

    Holds a `MerchantRegistry` (or None). Cheap to build; build one wherever
    a registry is built and hand it to memory and the learner."""

    def __init__(self, registry=None):
        self.registry = registry if registry else None
        self._key_cache: dict[str, str] = {}

    def resolve(
        self, vendor_clean: str | None, raw: str | None,
        descriptor: str | None = None,
    ) -> MerchantIdentity | None:
        """The identity of a receipt (`vendor_clean`, `raw`) or a charge
        (`raw` = the bank description). `descriptor` is a charge description
        paired with the receipt, tried after the receipt's own names. None
        when no name is given at all."""
        if self.registry is not None:
            for clean, name in ((vendor_clean, raw), (None, descriptor)):
                if not (clean or name):
                    continue
                m = self.registry.resolve(clean, name)
                if m is not None:
                    return MerchantIdentity(
                        canonical=m.canonical_name,
                        key=identity_key(m.canonical_name),
                        source="registry",
                        aliases_matched=(m.matched_alias,),
                    )
        for name in (raw, vendor_clean, descriptor):
            key = identity_key(name)
            if key:
                return MerchantIdentity(
                    canonical=str(name).strip(), key=key, source="name",
                )
        return None

    def key(self, vendor: str | None) -> str:
        """`resolve(None, vendor).key`, memoized: the key memory uses for one
        name, whether it is a receipt's vendor, a bank description or a
        stored rule's normalized key."""
        if not vendor:
            return ""
        hit = self._key_cache.get(vendor)
        if hit is None:
            ident = self.resolve(None, vendor)
            hit = ident.key if ident is not None else ""
            self._key_cache[vendor] = hit
        return hit
