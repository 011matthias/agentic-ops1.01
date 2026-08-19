"""Canonical merchant registry — settings-backed, seeded, self-improving.

A human-editable registry stored under `settings["merchants"]` (like
`card_accounts` / `entities`), the highest-priority DETERMINISTIC source
for two facts about a receipt's merchant:

  * the canonical DISPLAY name, so "COMERCIO DE X LTDA", "X Ltda", and a
    fuzzy OCR variant all read as one brand on the grid and the export, and
  * a default category / Zoho account for that brand.

Consulted in `generate_expenses` ONLY (mirrors the Phase-6 `ExpenseMemory`
contract); `reconcile()` never sees it. It sits ABOVE the learned SQLite
tables in precedence: registry -> learned -> LLM, and a reviewer override
always wins over all three. An empty registry resolves nothing, so a
tenant with no `merchants` key behaves exactly as before.

Shape:
    settings["merchants"] = {
        "<canonical name>": {
            "aliases": ["raw pattern", ...],   # extra strings to match on
            "category": "<one of EXPENSE_CATEGORIES>" | None,
            "zoho_account": "<chart label>" | None,
            "multi_category": True,            # optional (2026-08-19)
        },
        ...
    }

A `multi_category` merchant (backlog item 8) decouples the registry's two
facts: the canonical NAME still resolves (spelling stability), but no
default category/account is stamped — the vendor legitimately books to
different categories, so each receipt is judged on its own contents
(learned/LLM path) and the grid's variance chip makes the outcome
auditable.

Matching (`resolve`): normalized-exact on the canonical name or any alias,
then rapidfuzz `token_set_ratio >= threshold` over the same strings, else
unmatched. Both the receipt's extracted `vendor_clean` and its raw
`detected_vendor` (plus a deterministic clean of the raw) are tried as
probes, so a path that never produced a `vendor_clean` still resolves.
"""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from .matching.deterministic import _normalize as normalize_vendor
from .matching.types import EXPENSE_CATEGORIES
from .vendor_names import clean_vendor_name

# token_set_ratio (0-100) at or above this counts as a confident brand
# match. High enough that only a genuine spelling / OCR variant of a known
# alias clears it, not an unrelated merchant sharing one common token.
DEFAULT_FUZZY_THRESHOLD = 88.0


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
        # (normalized, original, canonical) triples for the fuzzy sweep
        self._candidates: list[tuple[str, str, str]] = []

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
            for raw in (canonical, *(entry.get("aliases") or [])):
                s = str(raw or "").strip()
                if not s:
                    continue
                norm = normalize_vendor(s)
                if not norm:
                    continue
                self._exact.setdefault(norm, (canonical, s))
                self._candidates.append((norm, s, canonical))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def _probes(self, vendor_clean: str | None, vendor_raw: str | None) -> list[str]:
        """Ordered, de-duped normalized probe strings for one receipt:
        extracted brand first, then a deterministic clean of the raw name,
        then the raw name itself."""
        seen: set[str] = set()
        out: list[str] = []
        for raw in (vendor_clean, clean_vendor_name(vendor_raw), vendor_raw):
            norm = normalize_vendor(str(raw)) if raw else ""
            if norm and norm not in seen:
                seen.add(norm)
                out.append(norm)
        return out

    def resolve(
        self, vendor_clean: str | None, vendor_raw: str | None
    ) -> MerchantMatch | None:
        """Return the registry match for a receipt's merchant, or None when
        nothing clears the bar. Exact (normalized-equality) wins over fuzzy;
        the earlier probe (vendor_clean before raw) wins within a tier."""
        if not self._entries:
            return None
        probes = self._probes(vendor_clean, vendor_raw)
        if not probes:
            return None

        # 1) Exact: normalized equality on any canonical / alias string.
        for norm in probes:
            hit = self._exact.get(norm)
            if hit:
                canonical, original = hit
                return self._match(canonical, original, 100.0, "exact")

        # 2) Fuzzy: best token_set_ratio across probe x candidate. Strict `>`
        # over the sorted-canonical candidate list keeps ties deterministic.
        best_score = -1.0
        best_canonical: str | None = None
        best_original: str | None = None
        for norm in probes:
            for cand_norm, cand_orig, canonical in self._candidates:
                score = fuzz.token_set_ratio(norm, cand_norm)
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
            )
        category = (entry.get("category") or None)
        return MerchantMatch(
            canonical_name=canonical,
            category=category if category in EXPENSE_CATEGORIES else None,
            zoho_account=(entry.get("zoho_account") or None),
            matched_alias=original,
            score=float(score),
            kind=kind,
        )

    @classmethod
    def from_settings(
        cls, settings: dict | None, *, threshold: float = DEFAULT_FUZZY_THRESHOLD
    ) -> "MerchantRegistry":
        merchants = settings.get("merchants") if isinstance(settings, dict) else None
        return cls(merchants, threshold=threshold)


def normalize_merchants_setting(raw: object) -> dict:
    """Validate + clean a `merchants` settings payload into the stored shape.

    Raises ValueError on a malformed structure (the settings PUT surfaces it
    as HTTP 400). Mirrors the `entities` map contract: the whole map replaces
    the stored one, a blank canonical name is dropped, and each entry must be
    a dict. Aliases are trimmed + de-duplicated on their normalized key; a
    category, when given, must be one of the fixed expense categories."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("merchants must be an object of {canonical_name: entry}")
    out: dict[str, dict] = {}
    for name, entry in raw.items():
        canonical = str(name or "").strip()
        if not canonical:
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"merchant {canonical!r} must be an object")
        aliases: list[str] = []
        seen: set[str] = set()
        for a in entry.get("aliases") or []:
            s = str(a or "").strip()
            key = normalize_vendor(s)
            if s and key and key not in seen:
                seen.add(key)
                aliases.append(s)
        category = str(entry.get("category") or "").strip() or None
        if category is not None and category not in EXPENSE_CATEGORIES:
            raise ValueError(
                f"merchant {canonical!r} category {category!r} is not one of the "
                "expense categories"
            )
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
        out[canonical] = cleaned
    return out
