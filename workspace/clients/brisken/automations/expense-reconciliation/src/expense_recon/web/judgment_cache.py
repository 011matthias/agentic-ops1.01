"""Never buy the same LLM judgment twice (PR 2b-1 of the living month).

A month used to be matched exactly once, at statement-attach time, so
every FX and ambiguous-tie judgment was paid for once by construction.
The living month re-matches on every receipt arrival and every statement
append, which without a cache means re-asking the model about pairs it
has already judged, on every single add, on Dirk's key.

The cache sits between the judgment layer and the LLM client. Both
judgment entry points (`matching.judgment.judge_fx_match` and
`judge_ambiguous`) reach the model through exactly two client methods,
so wrapping those two covers every judgment call without the judgment
layer knowing a cache exists.

**Keyed by CONTENT, not by `(transaction_id, document_id)`.** The plan
specified the id pair; the content of the call is strictly better here,
for a reason that matters: a reviewer can correct a receipt's amount,
currency, date or vendor after it was judged. Under an id key the
corrected pair would return the stale verdict the model gave for the
OLD numbers, silently. Under a content key it misses and re-judges,
which is the honest outcome. Since PR 2a the transaction id is itself
content-derived, so the two keys agree everywhere except exactly the
case where disagreeing is correct.

Entries are stored in the run snapshot under `llm_judgments` and reload
with it, so the saving survives a restart and a re-match days later.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any


# Bump when a cached payload's SHAPE changes, so old entries miss
# instead of being read back into a dataclass that no longer fits.
_SCHEMA = "1"

_FX = "judge_fx_match"
_AMBIGUOUS = "judge_ambiguous"


def _plain(value: Any) -> Any:
    """A JSON-safe, order-stable view of one call argument."""
    if isinstance(value, Decimal):
        # str() rather than float(): the point is a stable key, and
        # float() would make 0.1 + 0.2 problems part of the identity.
        return f"D:{value}"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in sorted(asdict(value).items())}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    # Fallback for a type this function has not been taught. `repr` can
    # embed a memory address, which would make the key unstable across
    # processes. That is deliberately the SAFE direction: an unstable key
    # can only ever miss and re-buy a judgment, never return the wrong
    # one. Every argument the two judgment calls actually take is handled
    # above; if a new one lands here, teach it rather than rely on this.
    return repr(value)


def call_key(method: str, kwargs: dict, model: str = "") -> str:
    payload = json.dumps(
        [
            _SCHEMA,
            method,
            model,
            {k: _plain(v) for k, v in sorted(kwargs.items())},
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


class JudgmentCache:
    """Content-keyed store of judgments already paid for on this run."""

    def __init__(
        self, entries: dict[str, dict] | None = None, *, model: str = ""
    ) -> None:
        self._entries: dict[str, dict] = dict(entries or {})
        # The judging model is part of the key. A deployment that moves
        # to a stronger model (as the vision path did on 2026-08-24)
        # must re-judge rather than hand back the old model's verdicts
        # forever; entries keyed to the previous model simply stop
        # matching.
        self._model = model or ""
        self.hits = 0
        self.misses = 0

    @classmethod
    def from_snapshot(
        cls, snapshot: dict | None, *, model: str = ""
    ) -> "JudgmentCache":
        raw = (snapshot or {}).get("llm_judgments")
        return cls(raw if isinstance(raw, dict) else None, model=model)

    def to_dict(self) -> dict[str, dict]:
        return dict(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, method: str, kwargs: dict) -> dict | None:
        entry = self._entries.get(call_key(method, kwargs, self._model))
        if entry is None:
            self.misses += 1
            return None
        self.hits += 1
        return entry

    def put(self, method: str, kwargs: dict, payload: dict) -> None:
        self._entries[call_key(method, kwargs, self._model)] = payload

    def wrap(self, client):
        """A stand-in for `client` that answers a repeat judgment from
        the cache. `None` in, `None` out: no client means no judgments,
        and the judgment layer already treats that as "leave it for a
        human", which must stay true."""
        if client is None:
            return None
        if not self._model:
            self._model = str(getattr(client, "model", "") or "")
        return _CachingJudgmentClient(client, self)


class _CachingJudgmentClient:
    """Delegates everything to the real client except the two judgment
    calls, which it memoizes.

    Attribute delegation is deliberate rather than a full interface
    re-declaration: the client protocol carries extraction and
    categorization methods too, and this proxy must stay invisible to
    them. A method added to the protocol later keeps working here
    without an edit, uncached, which is the safe default.
    """

    def __init__(self, inner, cache: JudgmentCache) -> None:
        self._inner = inner
        self._cache = cache

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def judge_fx_match(self, **kwargs):
        from ..llm.client import FxJudgmentResult

        cached = self._cache.get(_FX, kwargs)
        if cached is not None:
            return FxJudgmentResult(
                is_match=bool(cached["is_match"]),
                same_purchase_confidence=float(
                    cached["same_purchase_confidence"]
                ),
                implied_rate=(
                    None if cached.get("implied_rate") is None
                    else float(cached["implied_rate"])
                ),
                converted_amount=(
                    None if cached.get("converted_amount") is None
                    else Decimal(str(cached["converted_amount"]))
                ),
                reasoning=str(cached.get("reasoning") or ""),
            )
        result = self._inner.judge_fx_match(**kwargs)
        self._cache.put(
            _FX,
            kwargs,
            {
                "is_match": bool(result.is_match),
                "same_purchase_confidence": float(
                    result.same_purchase_confidence
                ),
                "implied_rate": (
                    None if result.implied_rate is None
                    else float(result.implied_rate)
                ),
                "converted_amount": (
                    None if result.converted_amount is None
                    else str(result.converted_amount)
                ),
                "reasoning": str(result.reasoning or ""),
            },
        )
        return result

    def judge_ambiguous(self, **kwargs):
        from ..llm.client import AmbiguousJudgmentResult

        cached = self._cache.get(_AMBIGUOUS, kwargs)
        if cached is not None:
            return AmbiguousJudgmentResult(
                chosen_index=int(cached["chosen_index"]),
                confidence=float(cached["confidence"]),
                reasoning=str(cached.get("reasoning") or ""),
            )
        result = self._inner.judge_ambiguous(**kwargs)
        self._cache.put(
            _AMBIGUOUS,
            kwargs,
            {
                "chosen_index": int(result.chosen_index),
                "confidence": float(result.confidence),
                "reasoning": str(result.reasoning or ""),
            },
        )
        return result
