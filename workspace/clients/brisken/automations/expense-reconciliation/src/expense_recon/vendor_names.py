"""Deterministic vendor-name cleaning: strip legal-entity suffixes and
distributor / comercio tails to recover the short storefront brand.

The vision extractor (`llm.client._EXTRACT_INSTRUCTIONS`) returns a
`vendor_clean` brand directly. This module is the deterministic fallback
for every path that carries only a raw statement / summary vendor and
never sees the vision model (the ER-PDF text-layer summary, the receipts
CSV, the Zoho Expense CSV), and the normalizer the merchant-registry
resolver applies when a receipt carries no extracted `vendor_clean`.

Pure text, no third-party imports, so ingest and the registry can both
depend on it without a cycle.
"""
from __future__ import annotations

import re

# Trailing legal-entity suffix tokens (compared punctuation- and
# case-insensitively: "S.A." -> "sa", "Ltda." -> "ltda", "GmbH" -> "gmbh").
# Stripped repeatedly from the tail, so "X Comercio Ltda ME" -> "X".
_LEGAL_SUFFIXES = frozenset(
    {
        "ltda", "ltd", "limited", "inc", "incorporated", "llc", "llp", "lp",
        "plc", "corp", "corporation", "co", "company", "gmbh", "mbh", "ag",
        "kg", "ohg", "gbr", "ug", "kgaa", "sa", "sas", "sarl", "srl", "sl",
        "spa", "bv", "nv", "oy", "ab", "as", "aps", "pty", "eireli", "me",
        "epp", "sac", "cia", "sociedad", "sociedade", "sro", "doo",
    }
)

# Multi-word connective tails that mark a Latin/Brazilian trading- or
# distributor-company style name. Once a brand token sits in front of the
# marker, everything from the marker onward is dropped. Ordered so the
# earliest match in the string wins (searched by index, not list order).
_TAIL_MARKERS = (
    "industria e comercio",
    "comercio de",
    "comercio e",
    "comercio",
    "com de",
    "industria de",
    "industria",
    "distribuidora de",
    "distribuidora",
    "distribuicao",
    "importacao e exportacao",
    "importacao",
    "exportacao",
    "empreendimentos",
    "servicos de",
    "servico de",
)

_STRIP_EDGE = " ,-/&.\t"


def clean_vendor_name(raw: str | None) -> str | None:
    """Return the short brand for a raw vendor string, or None when the
    input is empty. Never returns an empty string: if stripping would
    erase everything, the pre-strip value is kept (a name that IS only a
    legal form, e.g. "Ltda", stays as-is rather than vanishing)."""
    if not raw:
        return None
    s = re.sub(r"\s+", " ", str(raw)).strip()
    if not s:
        return None

    # 1) Cut a distributor / comercio tail, keeping the brand in front.
    lowered = s.lower()
    cut: int | None = None
    for marker in _TAIL_MARKERS:
        idx = lowered.find(" " + marker)
        if idx > 0 and (cut is None or idx < cut):
            cut = idx
    if cut is not None:
        s = s[:cut].strip(_STRIP_EDGE)

    pre = s or None

    # 2) Drop trailing legal-entity suffix tokens (and dangling separators).
    tokens = s.split()
    while tokens:
        bare = re.sub(r"[^a-z0-9]", "", tokens[-1].lower())
        if bare in _LEGAL_SUFFIXES or not bare:
            tokens.pop()
        else:
            break

    cleaned = " ".join(tokens).strip(_STRIP_EDGE)
    return cleaned or pre or (re.sub(r"\s+", " ", str(raw)).strip() or None)
