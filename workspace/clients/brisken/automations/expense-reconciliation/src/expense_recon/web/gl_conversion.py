"""Switch a bucket-era month onto the GL engine (owner directive 2026-09-25).

Months created before the GL engine (July, August and September 2026) were
categorized into the eight buckets, and the reviewer's own picks there are
bucket names. The owner ordered those months re-categorized into Brisken's
curated Zoho accounts, and ruled on the picks (AskUserQuestion, 2026-09-25):
ignore them, so the engine decides every row fresh. No bucket maps to one
account, so a pick could not be carried over anyway.

A conversion, in one locked write after the model calls:

- the month's config gains `gl_entity_orgs` and the export gate block, from
  the same `apply_to_config` call a month created today gets, so a switched
  month and October's month behave alike from here on;
- every receipt line is re-categorized on the GL engine for the company the
  row SHOWS (the grid's card chain, passed in as `entity_by_doc`), in the
  current pool, the extraction baseline and the borrowed copies alike;
- every receiptless charge is re-categorized for the charge's own company;
- the bucket-era category overrides are removed, and kept, with every
  previous categorization, under `gl_conversion` in the snapshot, so the
  switch can be reversed by hand.

It refuses a month that is already GL, a published month, a trip, a month
with no provisioned company, and a run with no model client (the engine
would then refuse every row the registry does not cover, which would read as
a result). The model calls run outside the batch lock and nothing is written
until they have all returned, so a model failure (an exhausted key) leaves
the month exactly as it was. A month that changed while the model ran (a
receipt arrived, a re-match ran) is refused rather than half-converted; run
it again.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import replace
from pathlib import Path

from ..coa_provision import GL_ENTITY_ORGS_KEY, apply_to_config
from ..learning import MerchantCategoryLookup
from ..matching.types import Receipt
from ..merchant_registry import MerchantRegistry
from .serialize import (
    categorization_to_dict,
    receipt_from_dict,
    receipt_to_dict,
    snapshot_from_dict,
)
from .service import (
    BATCH_TYPE_TRIP,
    BORROWED_RECEIPTS_KEY,
    EXTRACTED_RECEIPTS_KEY,
    RunInputError,
    _batch_llm_client,
    baseline_receipts,
    batch_type,
    batch_write_lock,
    categorized_counts,
)
from .store import RunStore

logger = logging.getLogger(__name__)

GL_CONVERSION_KEY = "gl_conversion"
_RECEIPT_LISTS = ("receipts", EXTRACTED_RECEIPTS_KEY, BORROWED_RECEIPTS_KEY)


def conversion_refusal(run) -> RunInputError | None:
    """Why this run cannot be switched, or None. Checked before the model
    runs and again inside the write lock."""
    if run is None:
        return RunInputError("run not found", code="run_not_found")
    if GL_ENTITY_ORGS_KEY in (run.config or {}):
        return RunInputError(
            "this month already uses the Zoho accounts", code="month_already_gl")
    if run.published:
        return RunInputError(
            "this month is published; unpublish it before switching it to the "
            "Zoho accounts", code="month_published")
    if batch_type(run) == BATCH_TYPE_TRIP:
        return RunInputError(
            "a trip takes its months' accounts; switch the months instead",
            code="trip_not_convertible")
    return None


def _cats(d: dict) -> list:
    return [li.get("categorization") for li in d.get("line_items") or []]


def _swap(d: dict, new: Receipt) -> dict:
    """The stored receipt with only its line categorizations replaced: its
    company, vendor and every other field stay as the month has them."""
    old = receipt_from_dict(d)
    if len(old.line_items) == len(new.line_items):
        items = tuple(
            replace(li, categorization=n.categorization)
            for li, n in zip(old.line_items, new.line_items)
        )
    else:  # a receipt with no lines gains the engine's synthesized total line
        items = new.line_items
    return receipt_to_dict(replace(old, line_items=items))


def _fingerprint(snapshot: dict) -> tuple:
    """What the model's answers were computed against: the pool's documents
    and the match outcome. A change to either between the read and the write
    means the answers may not cover the month."""
    docs = tuple(
        d.get("document_id") for key in _RECEIPT_LISTS
        for d in (snapshot.get(key) or []) if isinstance(d, dict)
    )
    return docs, json.dumps(snapshot.get("outcome"), sort_keys=True, default=str)


def convert_month_to_gl(
    db_path,
    learning_db_path: Path | None,
    run_id: str,
    now_iso: str,
    *,
    entity_by_doc: dict[str, str] | None = None,
    on_stage=None,
) -> dict:
    """Re-categorize one bucket-era month on the GL engine. Returns what
    changed; raises `RunInputError` (nothing written) when it cannot."""
    from ..categorize import categorize_receipts_with_registry
    from ..categorize_charges import categorize_charges

    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass

    with RunStore(db_path) as store:
        run = store.get_run(run_id)
        refused = conversion_refusal(run)
        if refused is not None:
            raise refused
        settings = store.get_settings()
        field_overrides = store.get_expense_field_overrides(run_id)
    cfg = dict(run.config or {})
    batch_entity = str((cfg.get("expense") or {}).get("legal_entity_id") or "")
    new_cfg = apply_to_config(dict(cfg), batch_entity, settings=settings)
    entity_orgs = new_cfg.get(GL_ENTITY_ORGS_KEY)
    if not entity_orgs:
        raise RunInputError(
            "no company has a Zoho organization set up, so there are no "
            "accounts to switch to", code="gl_not_provisioned")
    llm_client, tracker, _source = _batch_llm_client(new_cfg)
    if llm_client is None:
        raise RunInputError(
            "the AI key is not available, so the accounts cannot be chosen",
            code="llm_unavailable")
    registry = MerchantRegistry.from_settings(settings)
    learned = (
        MerchantCategoryLookup.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    shown = entity_by_doc or {}

    def _company(r: Receipt) -> str:
        return (
            shown.get(r.document_id)
            or (field_overrides.get(r.document_id) or {}).get("legal_entity")
            or r.legal_entity_id
            or batch_entity
        )

    snapshot0 = run.snapshot or {}
    _stage("receipts")
    pool = [replace(r, legal_entity_id=_company(r)) for r in baseline_receipts(run)]
    borrowed = []
    for d in snapshot0.get(BORROWED_RECEIPTS_KEY) or []:
        try:
            borrowed.append(receipt_from_dict(d))
        except (KeyError, TypeError, ValueError):
            continue
    new_pool, _ = categorize_receipts_with_registry(
        pool, registry=registry, client=llm_client, learned=learned,
        entity_orgs=entity_orgs,
    )
    new_borrowed, _ = categorize_receipts_with_registry(
        borrowed, registry=registry, client=llm_client, learned=learned,
        entity_orgs=entity_orgs,
    ) if borrowed else ([], {})

    _stage("charges")
    transactions, _receipts, outcome, _issues = snapshot_from_dict(snapshot0)
    charge_cats = categorize_charges(
        outcome, transactions, client=llm_client, learned=learned,
        registry=registry, entity_orgs=entity_orgs,
    ) if outcome.unmatched_transactions else {}

    _stage("saving")
    pool_by_doc = {r.document_id: r for r in new_pool}
    borrowed_by_doc = {r.document_id: r for r in new_borrowed}
    with batch_write_lock():
        with RunStore(db_path) as store:
            fresh = store.get_run(run_id)
            refused = conversion_refusal(fresh)
            if refused is not None:
                raise refused
            snapshot = dict(fresh.snapshot or {})
            if _fingerprint(snapshot) != _fingerprint(snapshot0):
                raise RunInputError(
                    "the month changed while its accounts were being chosen; "
                    "nothing was saved, run the switch again",
                    code="month_changed_during_conversion")
            overrides = store.get_category_overrides(run_id)
            archive = {
                "at": now_iso,
                "from": "buckets",
                "receipt_categorizations": {
                    key: {
                        d.get("document_id"): _cats(d)
                        for d in snapshot.get(key) or [] if isinstance(d, dict)
                    }
                    for key in _RECEIPT_LISTS if isinstance(snapshot.get(key), list)
                },
                "charge_categorizations": snapshot.get("charge_categorizations"),
                "category_overrides": [
                    {"document_id": doc, "line_index": line, **ov}
                    for (doc, line), ov in sorted(overrides.items())
                ],
            }
            for key, by_doc in (
                ("receipts", pool_by_doc),
                (EXTRACTED_RECEIPTS_KEY, pool_by_doc),
                (BORROWED_RECEIPTS_KEY, borrowed_by_doc),
            ):
                rows = snapshot.get(key)
                if not isinstance(rows, list):
                    continue
                snapshot[key] = [
                    _swap(d, by_doc[d.get("document_id")])
                    if isinstance(d, dict) and d.get("document_id") in by_doc else d
                    for d in rows
                ]
            if charge_cats:
                snapshot["charge_categorizations"] = {
                    tx_id: categorization_to_dict(c)
                    for tx_id, c in charge_cats.items()
                }
            else:
                snapshot.pop("charge_categorizations", None)
            snapshot[GL_CONVERSION_KEY] = archive
            store.update_run_snapshot(run_id, snapshot)
            store.update_run_config(run_id, new_cfg)
            n_retired = store.delete_category_overrides(run_id)
            n_categorized, n_uncategorized = categorized_counts(
                [receipt_from_dict(d) for d in snapshot.get("receipts") or []]
            )
            store.update_run_summary(run_id, {
                **(fresh.summary or {}),
                "n_categorized": n_categorized,
                "n_uncategorized": n_uncategorized,
            })

    lines = [li.categorization for r in new_pool for li in r.line_items]
    result = {
        "ok": True,
        "run_id": run_id,
        "label": run.label,
        "category_vocabulary": "gl",
        "n_receipts": len(new_pool),
        "n_lines": len(lines),
        "n_lines_categorized": sum(1 for c in lines if c is not None and c.category),
        "line_refusals": dict(Counter(
            c.refusal for c in lines if c is not None and c.refusal)),
        "n_borrowed": len(new_borrowed),
        "n_charges": len(charge_cats),
        "n_charges_categorized": sum(1 for c in charge_cats.values() if c.category),
        "charge_refusals": dict(Counter(
            c.refusal for c in charge_cats.values() if c.refusal)),
        "n_overrides_retired": n_retired,
        "llm_cost_usd": str(tracker.total_cost_usd) if tracker is not None else None,
    }
    logger.info("gl conversion %s (%s): %s", run_id, run.label, result)
    return result
