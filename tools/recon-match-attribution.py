# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openpyxl==3.1.5",
#     "openai==2.38.0",
#     "pypdf==6.13.2",
#     "pypdfium2==5.9.0",
#     "pillow==12.2.0",
# ]
# ///
"""Failure attribution for the expense-recon matcher: which gate lost each receipt.

For every receipt a month holds, name what the deterministic matcher did with
it and, when a human label says which charge it belongs to, the ONE gate that
kept it from resolving cleanly, in the order the code applies them. The output
is a class table (count, money, examples) per month, which is what decides
where a matching round is worth spending.

Two inputs, one attribution:

* a LIVE month, replayed locally from the hosted app's own snapshot with no
  model call (`--live DB --run-id ID`): the candidate pool is assembled the
  way `service.rematch_month` assembles it (reviewer edits baked, charge
  entities stamped from the card registry, foreign claims out, duplicate
  copies collapsed, trip receipts borrowed), the deterministic matcher runs,
  and the judgment layer answers from the snapshot's judgment cache.
* a LABEL BUNDLE (`--bundle DIR [--asset TUNING.json]`): the six scorer
  bundles and the live-month bundles built through `expense-recon label`,
  replayed exactly as `tools/scorers/recon-match-accuracy.py` replays them.

Labels (`labels.csv`, the `expense-recon label` vocabulary: confirmed /
no_charge / excluded) decide correctness. Without labels the tool still
reports buckets, duplicate copies and the coverage heuristics, but no receipt
can be called correct or wrong.

Classes, in the order the matcher applies its gates:

  resolved_clean            correct charge, deterministic (the goal)
  wrong_*                   a deterministic match to the WRONG charge, or a
                            match for a receipt that has no charge
  matched_unverifiable      matched, but the label excluded the receipt
  dup_copy_collapsed        a duplicate copy item 56 already keeps out
  dup_copy_undetected       a duplicate copy the detector did not see
  dup_false_positive        collapsed as a duplicate, but a real purchase
  currency_unknown          receipt currency not read
  no_date                   receipt date not read (FX needs one)
  entity_mismatch           receipt names another legal entity
  card_scope                receipt names a card present in the statement,
                            but not this charge's
  date_window               true charge outside the date window
  amount_band               true charge outside the amount band / no evidence
  demoted_uniqueness        clean rate-derived pair, another clean pair rivals it
  demoted_card              clean rate-derived pair, receipt names an absent card
  fx_judgment_review_zone   FX evidence in the review zone only (3-13%)
  fx_judgment_band_only     FX pair inside the band, no rate evidence
  rival_won_greedy          correct pair was a candidate, the assignment gave
                            the receipt or the charge to another pair
  ambiguous_tie             correct charge tied between candidates
  llm_suppressed            the model rejected the (correct) pair below the floor
  coverage_unloaded_card    receipt paid on a card whose statement is not loaded
  coverage_non_card_tender  cash / debit / bank transfer: never posts to a card
  coverage_boundary         receipt dated at the statement's edge; its charge
                            posts in the neighbouring period (item 61)
  coverage_no_charge        no charge on any loaded statement, no further hint
  excluded_ambiguous        the label excluded it; not counted either way

Deterministic: no LLM, no network. Same input, same table.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_MODULE_SRC_DEFAULT = REPO / "workspace/clients/brisken/automations/expense-reconciliation/src"
MODULE_SRC = Path(os.environ.get("RECON_MODULE_SRC") or _MODULE_SRC_DEFAULT)

RATE_DERIVED = ("fx_base_amount", "fx_reference")
NON_CARD_TENDER = re.compile(
    r"\b(debit|ec[- ]?karte|girocard|maestro|cash|dinheiro|pix|bank transfer|"
    r"transfer[êe]ncia|boleto|paypal|cheque|check)\b",
    re.IGNORECASE,
)
BOUNDARY_DAYS = 2


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _import_module():
    if not MODULE_SRC.is_dir():
        raise SystemExit(f"ERROR: module src not found: {MODULE_SRC}")
    if str(MODULE_SRC) not in sys.path:
        sys.path.insert(0, str(MODULE_SRC))


class _CacheOnlyClient:
    """Answers judgments from the snapshot's cache; a miss gets the no-LLM
    stub and is counted, never a model call."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.misses = 0

    def judge_fx_match(self, **kw):
        from expense_recon.llm.client import FxJudgmentResult

        self.misses += 1
        return FxJudgmentResult(
            is_match=False, same_purchase_confidence=0.5, implied_rate=None,
            converted_amount=None, reasoning="LOCAL-UNJUDGED",
        )

    def judge_ambiguous(self, **kw):
        from expense_recon.llm.client import AmbiguousJudgmentResult

        self.misses += 1
        return AmbiguousJudgmentResult(chosen_index=0, confidence=0.0, reasoning="LOCAL-UNJUDGED")


def load_live(db: Path, run_id: str, learning: Path | None) -> dict:
    """A live month's pool, config and outcomes, assembled as rematch_month does."""
    _import_module()
    from expense_recon.cli import _apply_ambiguous_judgment, _apply_judgment, build_match_cfg
    from expense_recon.duplicates import collapsed_duplicate_copies
    from expense_recon.learning.consult import MatchMemory
    from expense_recon.matching.deterministic import MatchingConfig, match_month
    from expense_recon.web import service
    from expense_recon.web.judgment_cache import JudgmentCache
    from expense_recon.web.serialize import snapshot_from_dict
    from expense_recon.web.store import RunStore

    store = RunStore(db)
    run = store.get_run(run_id)
    if run is None:
        raise SystemExit(f"ERROR: no run {run_id} in {db}")
    cfg = run.config or {}
    batch_entity = (cfg.get("expense") or {}).get("legal_entity_id", "")
    transactions, receipts0, stored_outcome, _ = snapshot_from_dict(run.snapshot)
    overrides = store.get_category_overrides(run_id)
    field_overrides = store.get_expense_field_overrides(run_id)
    edits = store.get_expense_edits(run_id)
    receipts = service.apply_expense_edits(
        receipts0, field_overrides, edits,
        category_overrides=overrides, default_entity=batch_entity,
    )
    receipts = service.apply_overrides(receipts, overrides)
    card_res = service.resolve_batch_row_cards(receipts, cfg, field_overrides)
    receipts = [
        (
            replace(r, legal_entity_id=res["entity"])
            if (res := card_res.get(r.document_id)) is not None
            and res["entity"] != r.legal_entity_id
            else r
        )
        for r in receipts
    ]
    transactions = service.stamp_charge_entities(transactions, service._batch_cards(cfg))
    foreign = {
        doc: c for doc, c in store.get_claims_on_receipts(run_id).items()
        if c["claimed_by_run_id"] != run_id
    }
    pool = [r for r in receipts if r.document_id not in foreign] if foreign else receipts
    collapsed = collapsed_duplicate_copies(pool, store.get_duplicate_resolutions(run_id))
    if collapsed:
        pool = [r for r in pool if r.document_id not in collapsed]
    borrowed, origins = service.trip_pool_for_month(
        store, run, transactions, own_doc_ids={r.document_id for r in receipts},
    )
    # Item 61 (2026-09-15): the pool spans the adjacent company months too.
    adjacent_pool = getattr(service, "adjacent_pool_for_month", None)
    if adjacent_pool is not None:
        adjacent, adjacent_origins = adjacent_pool(
            store, run, transactions,
            own_doc_ids={r.document_id for r in receipts} | set(origins),
        )
        if adjacent:
            borrowed = [*borrowed, *adjacent]
    match_input = [*pool, *borrowed] if borrowed else pool
    memory = MatchMemory.from_db_path(learning) if learning and Path(learning).exists() else None
    match_cfg = build_match_cfg(cfg, Path(run.work_dir), memory) or MatchingConfig()

    raw = match_month(transactions, match_input, match_cfg)
    judged = match_month(transactions, match_input, match_cfg)
    model = str(((cfg.get("llm") or {}).get("model")) or "gpt-4o-mini")
    stub = _CacheOnlyClient(model)
    cache = JudgmentCache.from_snapshot(run.snapshot)
    client = cache.wrap(stub)
    tx_by_id = {t.transaction_id: t for t in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    for br in borrowed:
        rec_by_id.setdefault(br.document_id, br)
    _apply_judgment(judged, tx_by_id, rec_by_id, client, suggest_floor=match_cfg.fx_judgment_suggest_floor)
    _apply_ambiguous_judgment(judged, tx_by_id, rec_by_id, client)
    for o in (raw, judged):
        in_pool = {r.document_id for r in receipts}
        have = set(o.unmatched_receipts)
        o.unmatched_receipts.extend(
            d for d in (*foreign, *sorted(collapsed)) if d in in_pool and d not in have
        )
    decisions = store.get_decisions(run_id)
    effective = service.apply_decisions(judged, transactions, receipts, decisions)
    return {
        "label": run.label, "id": run_id, "cfg": cfg, "match_cfg": match_cfg,
        "transactions": transactions, "receipts": receipts, "match_input": match_input,
        "collapsed": collapsed, "foreign": foreign,
        "raw": raw, "judged": judged, "effective": effective, "stored": stored_outcome,
        "judgment_hits": cache.hits, "judgment_misses": stub.misses,
        "n_decisions": len(decisions),
    }


def load_bundle(bundle: Path, asset: Path | None) -> dict:
    """A label bundle replayed the way the pinned scorer replays it."""
    _import_module()
    from expense_recon.cli import build_match_cfg
    from expense_recon.labeling import _load_bundle
    from expense_recon.matching.deterministic import MatchingConfig, match_month

    run_json = bundle / "run.json"
    if not run_json.exists():
        raise SystemExit(f"ERROR: {bundle} has no run.json")
    transactions, receipts, config_dir = _load_bundle(run_json)
    cfg = json.loads(run_json.read_text(encoding="utf-8"))
    if asset is not None:
        match_cfg = MatchingConfig.from_file(asset)
    else:
        match_cfg = build_match_cfg(cfg, config_dir) or MatchingConfig()
    raw = match_month(transactions, receipts, match_cfg)
    return {
        "label": bundle.name, "id": bundle.name, "cfg": cfg, "match_cfg": match_cfg,
        "transactions": transactions, "receipts": receipts, "match_input": receipts,
        "collapsed": set(), "foreign": {},
        "raw": raw, "judged": raw, "effective": raw, "stored": None,
        "judgment_hits": 0, "judgment_misses": 0, "n_decisions": 0,
    }


def load_labels(path: Path | None) -> dict[str, tuple[str, str, str]]:
    """document_id -> (status, transaction_id, evidence). A no_charge row's
    evidence may carry the labeler's coverage kind as `no_charge:<kind>`."""
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            r["document_id"]: (
                (r.get("status") or "").strip(),
                (r.get("transaction_id") or "").strip(),
                (r.get("evidence") or "").strip(),
            )
            for r in csv.DictReader(fh)
        }


# ---------------------------------------------------------------------------
# The matcher's gates, traced per pair
# ---------------------------------------------------------------------------

def trace_candidates(transactions, receipts, cfg) -> dict:
    """Every candidate pair the matcher generated, with the status it had
    going into the assignment: clean | judgment | demoted_uniqueness |
    demoted_card. Mirrors `match_month` up to the assignment pass."""
    from expense_recon.matching.deterministic import (
        _card_keys, _signal, _tx_card_keys, derive_fx_reference_rates, match_one,
    )
    from expense_recon.matching.types import MatchType

    purchases = [t for t in transactions if not t.is_credit]
    tx_card_keys = {t.transaction_id: _tx_card_keys(t) for t in purchases}
    present: set[str] = set()
    for keys in tx_card_keys.values():
        present |= keys
    scope: dict[str, set[str]] = {}
    if cfg.card_scoping:
        for r in receipts:
            pm = _card_keys(r.payment_mode)
            if pm and (pm & present):
                scope[r.document_id] = pm
    derived = derive_fx_reference_rates(purchases, receipts, cfg)

    cands: dict[tuple[str, str], dict] = {}
    for tx in purchases:
        for r in receipts:
            if r.legal_entity_id and tx.legal_entity_id and r.legal_entity_id != tx.legal_entity_id:
                continue
            sc = scope.get(r.document_id)
            if sc is not None and not (sc & tx_card_keys[tx.transaction_id]):
                continue
            m = match_one(tx, r, cfg, derived)
            if m is None:
                continue
            ref_sig, card_sig, vendor_sig = _signal(tx, r, cfg)
            cands[(tx.transaction_id, r.document_id)] = {
                "match": m,
                "type": m.match_type.value,
                "is_determ": m.match_type != MatchType.FX_JUDGMENT,
                "card_signal": card_sig,
                "vendor_signal": vendor_sig,
                "status": "clean" if m.match_type != MatchType.FX_JUDGMENT else "judgment",
            }
    claimants: dict[str, set[str]] = defaultdict(set)
    docs: dict[str, set[str]] = defaultdict(set)
    for (tx_id, doc), c in cands.items():
        if c["type"] in RATE_DERIVED:
            claimants[doc].add(tx_id)
            docs[tx_id].add(doc)
    for (tx_id, doc), c in cands.items():
        if c["type"] not in RATE_DERIVED:
            continue
        unique = len(claimants[doc]) == 1 and len(docs[tx_id]) == 1
        contradicts = cfg.card_scoping and c["card_signal"] == 0.0
        if contradicts:
            c["status"] = "demoted_card"
        elif not unique:
            c["status"] = "demoted_uniqueness"
            c["rivals"] = (sorted(claimants[doc] - {tx_id}), sorted(docs[tx_id] - {doc}))
    return {"cands": cands, "present": present, "scope": scope, "derived": derived, "purchases": purchases}


def gate_for(tx, r, cfg, trace) -> str:
    """The first gate that dropped (tx, receipt), in code order."""
    from expense_recon.matching.deterministic import _tx_card_keys, match_one

    if tx.is_credit:
        return "amount_band"  # a credit never pairs; nothing a receipt can do
    if r.detected_currency is None:
        return "currency_unknown"
    if r.legal_entity_id and tx.legal_entity_id and r.legal_entity_id != tx.legal_entity_id:
        return "entity_mismatch"
    sc = trace["scope"].get(r.document_id)
    if sc is not None and not (sc & _tx_card_keys(tx)):
        return "card_scope"
    if match_one(tx, r, cfg, trace["derived"]) is not None:
        return "candidate"
    fx = r.detected_currency != tx.transaction_currency
    dates = [tx.transaction_date] + ([tx.posting_date] if tx.posting_date else [])
    if fx:
        if r.detected_date is None:
            return "no_date"
        gap = min(abs((r.detected_date - d).days) for d in dates)
        if gap > cfg.fx_date_window_days:
            return "date_window"
        return "amount_band"
    if r.detected_total is None:
        return "amount_band"
    diff = abs(tx.amount - r.detected_total)
    if diff > cfg.amount_exact_tolerance and (tx.amount <= 0 or diff / tx.amount > cfg.amount_probable_tolerance_pct):
        return "amount_band"
    if r.detected_date is not None:
        gap = min(abs((r.detected_date - d).days) for d in dates)
        if gap > cfg.date_probable_window_days:
            return "date_window"
    return "amount_band"


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def _usd(r, tx_ccy: str, cfg, derived) -> Decimal | None:
    if r.detected_total is None:
        return None
    ccy = (r.detected_currency or "").upper()
    if r.base_amount is not None and r.base_amount > 0:
        return r.base_amount
    if not ccy or ccy == tx_ccy:
        return r.detected_total
    rate = cfg.fx_reference_rate(ccy, tx_ccy)
    if rate is None:
        hit = derived.get((ccy, tx_ccy))
        rate = hit[0] if hit else None
    if rate is None:
        band = cfg.fx_band(ccy, tx_ccy)
        rate = (band[0] + band[1]) / 2 if band else None
    return (r.detected_total * rate).quantize(Decimal("0.01")) if rate is not None else None


def _norm_ref(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]+", "", (s or "").upper())


def _reference_twins(receipts) -> dict[str, list[str]]:
    """document_id -> other documents with the same (reference, total, currency)."""
    by_key: dict[tuple, list[str]] = defaultdict(list)
    for r in receipts:
        ref = _norm_ref(r.detected_reference)
        if len(ref) >= 5 and r.detected_total is not None:
            by_key[(ref, str(r.detected_total), (r.detected_currency or "").upper())].append(r.document_id)
    out: dict[str, list[str]] = {}
    for docs in by_key.values():
        if len(docs) >= 2:
            for d in docs:
                out[d] = [x for x in docs if x != d]
    return out


def attribute(month: dict, labels: dict[str, tuple[str, str]]) -> list[dict]:
    from expense_recon.matching.deterministic import _card_keys

    cfg = month["match_cfg"]
    transactions = month["transactions"]
    receipts = month["receipts"]
    tx_by_id = {t.transaction_id: t for t in transactions}
    tx_ccy = Counter(t.transaction_currency for t in transactions).most_common(1)[0][0] if transactions else "USD"
    trace = trace_candidates(transactions, month["match_input"], cfg)
    cands = trace["cands"]
    raw, effective = month["raw"], month["effective"]

    def buckets(o):
        m = {x.document_id: x for x in o.matches}
        j: dict[str, list] = defaultdict(list)
        for x in o.judgment_required:
            j[x.document_id].append(x)
        a: dict[str, list] = defaultdict(list)
        for x in o.ambiguous:
            a[x.document_id].append(x)
        return m, j, a

    e_match, e_judg, e_amb = buckets(effective)
    r_match, r_judg, r_amb = buckets(raw)
    tx_holder = {x.transaction_id: x.document_id for x in effective.matches}
    tx_amb = {x.transaction_id for x in effective.ambiguous}
    dates = [t.transaction_date for t in transactions if t.transaction_date]
    span = (min(dates), max(dates)) if dates else None
    twins = _reference_twins(receipts)
    collapsed = month["collapsed"]

    rows = []
    for r in receipts:
        doc = r.document_id
        status, ltx, evidence = labels.get(doc, ("", "", ""))
        usd = _usd(r, tx_ccy, cfg, trace["derived"])
        bucket, held = "unmatched", None
        if doc in e_match:
            bucket, held = "match", e_match[doc]
        elif doc in e_judg:
            bucket, held = "judgment", e_judg[doc]
        elif doc in e_amb:
            bucket, held = "ambiguous", e_amb[doc]
        row = {
            "document_id": doc, "date": r.detected_date.isoformat() if r.detected_date else None,
            "total": str(r.detected_total) if r.detected_total is not None else None,
            "currency": r.detected_currency, "usd": str(usd) if usd is not None else None,
            "vendor": r.detected_vendor, "payment_mode": r.payment_mode,
            "label": status or "unlabeled", "label_tx": ltx or None,
            "bucket": bucket, "teed_up": False, "cls": None, "detail": "",
        }
        pm_keys = _card_keys(r.payment_mode)
        absent_card = bool(pm_keys) and not (pm_keys & trace["present"])

        def held_desc(m):
            t = tx_by_id.get(m.transaction_id)
            return (f"{t.transaction_date} {t.vendor_from_statement!r} {t.amount} card={t.card_last4}"
                    if t else m.transaction_id)

        # 1. duplicate copies, whatever the label
        if doc in collapsed:
            if status == "confirmed":
                row["cls"], row["detail"] = "dup_false_positive", f"collapsed, but labelled to {ltx}"
            else:
                row["cls"], row["detail"] = "dup_copy_collapsed", "item 56 keeps it out of the pool"
            rows.append(row)
            continue
        live_twins = [d for d in twins.get(doc, []) if d not in collapsed]
        if status == "excluded" and live_twins:
            # The label excluded it and another live copy of the same purchase
            # is in the pool: this is the copy item 56's detector did not see
            # (vendor spelled differently across a Stripe invoice + receipt).
            other = live_twins[0]
            if bucket == "match":
                row["cls"] = "wrong_dup_copy"
                row["detail"] = f"copy of {other}; the copy consumed {held_desc(held)}"
            else:
                row["cls"] = "dup_copy_undetected"
                row["detail"] = f"same reference/total as {other}; " + (
                    f"in judgment with {held_desc(held[0])}" if bucket == "judgment" else "unmatched")
            rows.append(row)
            continue

        # 2. no label: report the bucket only
        if not status:
            row["cls"] = {"match": "unlabeled_matched", "judgment": "unlabeled_judgment",
                          "ambiguous": "unlabeled_ambiguous"}.get(bucket, "unlabeled_unmatched")
            row["detail"] = held_desc(held) if bucket == "match" else ""
            rows.append(row)
            continue

        # 3. excluded (ambiguous by the labeler)
        if status == "excluded":
            if bucket == "match":
                row["cls"], row["detail"] = "matched_unverifiable", f"matched to {held_desc(held)}"
            else:
                row["cls"], row["detail"] = "excluded_ambiguous", bucket
            rows.append(row)
            continue

        # 4. no charge on this statement
        if status == "no_charge":
            if bucket == "match":
                m = held
                kind = "probable" if m.match_type.value == "probable" else m.match_type.value
                row["cls"] = f"wrong_{kind}_no_charge"
                row["detail"] = f"matched to {held_desc(m)} (vendor_score {m.vendor_score:.2f})"
            elif bucket in ("judgment", "ambiguous"):
                row["cls"] = "review_no_charge"
                row["detail"] = f"offered {held_desc(held[0])}"
            elif evidence.startswith("no_charge:"):
                kind = evidence.split(":", 1)[1]
                row["cls"] = f"coverage_{kind}"
                row["detail"] = f"labeler: {kind}; payment mode {r.payment_mode!r}"
            elif absent_card:
                row["cls"], row["detail"] = "coverage_unloaded_card", f"payment mode {r.payment_mode!r}"
            elif r.payment_mode and NON_CARD_TENDER.search(r.payment_mode):
                row["cls"], row["detail"] = "coverage_non_card_tender", f"payment mode {r.payment_mode!r}"
            elif span and r.detected_date and (
                r.detected_date < span[0] + timedelta(days=BOUNDARY_DAYS)
                or r.detected_date > span[1] - timedelta(days=BOUNDARY_DAYS)
            ):
                row["cls"], row["detail"] = "coverage_boundary", f"dated {r.detected_date}, statement spans {span[0]}..{span[1]}"
            else:
                row["cls"], row["detail"] = "coverage_no_charge", f"payment mode {r.payment_mode!r}"
            rows.append(row)
            continue

        # 5. confirmed: the label names the charge
        T = tx_by_id.get(ltx)
        if T is None:
            row["cls"], row["detail"] = "label_error", f"label names unknown charge {ltx}"
            rows.append(row)
            continue
        row["teed_up"] = bucket == "judgment" and any(m.transaction_id == ltx for m in held)
        if bucket == "match" and held.transaction_id == ltx:
            row["cls"] = "resolved_clean"
            row["detail"] = f"{held.match_type.value}{' (review-flagged)' if held.requires_review else ''}: {held_desc(held)}"
            rows.append(row)
            continue
        if bucket == "match":
            m = held
            kind = m.match_type.value
            row["cls"] = f"wrong_{kind}"
            row["detail"] = (f"matched to {held_desc(m)} (vendor_score {m.vendor_score:.2f}); "
                             f"truth {T.transaction_date} {T.vendor_from_statement!r} {T.amount} card={T.card_last4}")
            rows.append(row)
            continue
        # not resolved: which gate lost (T, r)?
        c = cands.get((ltx, doc))
        if c is None:
            g = gate_for(T, r, cfg, trace)
            row["cls"] = g if g != "candidate" else "amount_band"
            row["detail"] = f"truth {T.transaction_date} {T.vendor_from_statement!r} {T.amount} card={T.card_last4}"
            if bucket == "judgment":
                row["detail"] += f"; in review with {held_desc(held[0])}"
            rows.append(row)
            continue
        st = c["status"]
        suppressed = doc in r_judg and doc not in e_judg and bucket == "unmatched"
        if st == "demoted_uniqueness":
            rival_tx, rival_docs = c["rivals"]
            names = [f"{tx_by_id[x].vendor_from_statement!r} {tx_by_id[x].amount}" for x in rival_tx[:2]]
            row["cls"] = "demoted_uniqueness"
            row["detail"] = f"{c['type']} {c['match'].reason.split(':')[0][:40]}; rival charges {names}; rival receipts {[d[:30] for d in rival_docs[:2]]}"
        elif st == "demoted_card":
            row["cls"], row["detail"] = "demoted_card", f"{c['type']}; receipt names {r.payment_mode!r}"
        elif st == "judgment":
            reason = c["match"].reason
            row["cls"] = "fx_judgment_review_zone" if "above" in reason and "deviation" in reason else "fx_judgment_band_only"
            row["detail"] = reason[:110]
        else:  # a clean deterministic candidate that lost the assignment
            if ltx in tx_holder and tx_holder[ltx] != doc:
                row["cls"], row["detail"] = "rival_won_greedy", f"charge taken by {tx_holder[ltx][:40]}"
            elif ltx in tx_amb:
                row["cls"], row["detail"] = "ambiguous_tie", "tied candidates"
            else:
                row["cls"], row["detail"] = "rival_won_greedy", f"candidate {c['type']} not assigned"
        if suppressed:
            row["cls"] = "llm_suppressed"
            row["detail"] = "model rejected the pair below the suggest floor; " + row["detail"]
        elif bucket == "judgment" and not row["teed_up"]:
            row["detail"] += f"; in review with the WRONG charge {held_desc(held[0])}"
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

CLASS_ORDER = [
    "resolved_clean",
    "wrong_exact", "wrong_probable", "wrong_possible", "wrong_fx_reference", "wrong_fx_base_amount",
    "wrong_exact_no_charge", "wrong_probable_no_charge", "wrong_possible_no_charge",
    "wrong_fx_reference_no_charge", "wrong_fx_base_amount_no_charge", "wrong_dup_copy",
    "matched_unverifiable",
    "dup_copy_collapsed", "dup_copy_undetected", "dup_false_positive",
    "currency_unknown", "no_date", "entity_mismatch", "card_scope",
    "date_window", "amount_band",
    "demoted_uniqueness", "demoted_card",
    "fx_judgment_review_zone", "fx_judgment_band_only",
    "rival_won_greedy", "ambiguous_tie", "llm_suppressed",
    "review_no_charge",
    "coverage_unloaded_card", "coverage_neighbour_period", "coverage_non_card_tender",
    "coverage_bank_transfer", "coverage_unknown_card", "coverage_boundary", "coverage_no_charge",
    "excluded_ambiguous", "label_error",
    "unlabeled_matched", "unlabeled_judgment", "unlabeled_ambiguous", "unlabeled_unmatched",
]
MATCHING_GAP = {
    "demoted_uniqueness", "demoted_card", "fx_judgment_review_zone", "fx_judgment_band_only",
    "rival_won_greedy", "ambiguous_tie", "llm_suppressed", "date_window", "amount_band",
    "currency_unknown", "no_date", "entity_mismatch", "card_scope", "dup_false_positive",
}
COVERAGE = {
    "coverage_unloaded_card", "coverage_neighbour_period", "coverage_non_card_tender",
    "coverage_bank_transfer", "coverage_unknown_card", "coverage_boundary", "coverage_no_charge",
}


def parity_diffs(stored, judged) -> list[str]:
    """What the local replay would change against the outcome the hosted app
    last committed. Empty when the replay reproduces it; otherwise the pairs
    that moved, which is exactly what the next live re-match will do (the
    stored outcome predates a deploy, or a neighbouring month gained a
    receipt the pool now borrows)."""
    if stored is None:
        return []
    out: list[str] = []
    for name in ("matches", "judgment_required", "ambiguous"):
        a = {(x.transaction_id, x.document_id) for x in getattr(stored, name)}
        b = {(x.transaction_id, x.document_id) for x in getattr(judged, name)}
        for tx, doc in sorted(a - b):
            out.append(f"{name}: stored only  {doc[:44]} <-> {tx[:16]}")
        for tx, doc in sorted(b - a):
            out.append(f"{name}: replay only  {doc[:44]} <-> {tx[:16]}")
    for name in ("unmatched_receipts", "unmatched_transactions"):
        a, b = set(getattr(stored, name)), set(getattr(judged, name))
        for x in sorted(a - b):
            out.append(f"{name}: stored only  {x[:44]}")
        for x in sorted(b - a):
            out.append(f"{name}: replay only  {x[:44]}")
    return out


def summarize(rows: list[dict]) -> dict:
    c = Counter(r["cls"] for r in rows)
    wrong = sum(v for k, v in c.items() if k.startswith("wrong_"))
    return {
        "receipts": len(rows),
        "matched_clean_correct": c["resolved_clean"],
        "matched_wrong": wrong,
        "matched_unverifiable": c["matched_unverifiable"],
        "review_correct_candidate": sum(1 for r in rows if r["bucket"] == "judgment" and r["teed_up"]),
        "review_other": sum(1 for r in rows if r["bucket"] in ("judgment", "ambiguous") and not r["teed_up"]),
        "matching_gap": sum(v for k, v in c.items() if k in MATCHING_GAP),
        "coverage_gap": sum(v for k, v in c.items() if k in COVERAGE),
        "dup_copies": c["dup_copy_collapsed"] + c["dup_copy_undetected"],
        "excluded": c["excluded_ambiguous"],
        "unlabeled": sum(v for k, v in c.items() if k.startswith("unlabeled")),
    }


def print_table(months: list[tuple[str, list[dict]]], examples: int = 3) -> None:
    names = [n for n, _ in months]
    all_cls = set()
    for _, rows in months:
        all_cls |= {r["cls"] for r in rows}
    order = [c for c in CLASS_ORDER if c in all_cls] + sorted(all_cls - set(CLASS_ORDER))
    w = max(len(c) for c in order) + 1
    head = f"{'class':<{w}}" + "".join(f"{n[:18]:>22}" for n in names)
    print(head)
    print("-" * len(head))
    for cls in order:
        cells = []
        for _, rows in months:
            sub = [r for r in rows if r["cls"] == cls]
            usd = sum(Decimal(r["usd"]) for r in sub if r["usd"])
            cells.append(f"{len(sub):>4}  ${usd:>12,.2f}" if sub else f"{'':>4}  {'':>13}")
        print(f"{cls:<{w}}" + "".join(f"{c:>22}" for c in cells))
    print()
    for cls in order:
        shown = 0
        for name, rows in months:
            for r in rows:
                if r["cls"] != cls or shown >= examples:
                    continue
                shown += 1
                print(f"  [{cls}] {name}: {r['document_id'][:48]} | {r['date']} {r['total']} {r['currency']} {(r['vendor'] or '')[:28]!r} | {r['detail'][:150]}")
    print()
    for name, rows in months:
        s = summarize(rows)
        print(f"== {name}: " + ", ".join(f"{k}={v}" for k, v in s.items()))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--live", type=Path, help="recon-web.sqlite (a copy of the hosted database)")
    ap.add_argument("--run-id", action="append", default=[], help="live run id (repeatable)")
    ap.add_argument("--learning", type=Path, help="learning.sqlite beside the live database")
    ap.add_argument("--bundle", type=Path, action="append", default=[], help="label bundle directory (repeatable)")
    ap.add_argument("--asset", type=Path, help="match-tuning.json for bundle mode (default: the bundle's inline matching block)")
    ap.add_argument("--labels", type=Path, action="append", default=[], help="labels.csv per --run-id / --bundle, in order (bundle default: <bundle>/labels.csv)")
    ap.add_argument("--json", type=Path, help="write the per-receipt rows here")
    ap.add_argument("--examples", type=int, default=3)
    a = ap.parse_args(argv)

    months: list[tuple[str, list[dict]]] = []
    label_paths = list(a.labels)
    out_rows: dict[str, list[dict]] = {}
    if a.live:
        for rid in a.run_id:
            m = load_live(a.live, rid, a.learning)
            lp = label_paths.pop(0) if label_paths else None
            rows = attribute(m, load_labels(lp))
            name = f"{m['label']} ({rid})"
            months.append((name, rows))
            out_rows[name] = rows
            stored = m["stored"]
            diffs = parity_diffs(stored, m["judged"])
            print(f"[{name}] pool={len(m['match_input'])} of {len(m['receipts'])} receipts, {len(m['transactions'])} charges; "
                  f"judgment cache hits={m['judgment_hits']} misses={m['judgment_misses']}; decisions={m['n_decisions']}; "
                  f"parity with the hosted outcome: {'OK' if not diffs else 'DIFFERS (the next live re-match will move these)'}")
            for d in diffs:
                print(f"    {d}")
    for b in a.bundle:
        m = load_bundle(b, a.asset)
        lp = label_paths.pop(0) if label_paths else (b / "labels.csv")
        rows = attribute(m, load_labels(lp))
        months.append((b.name, rows))
        out_rows[b.name] = rows
        print(f"[{b.name}] {len(m['receipts'])} receipts, {len(m['transactions'])} charges, labels={'yes' if lp and Path(lp).exists() else 'NO'}")
    if not months:
        ap.error("nothing to attribute: give --live/--run-id or --bundle")
    print()
    print_table(months, a.examples)
    if a.json:
        a.json.write_text(json.dumps(out_rows, indent=1, default=str), encoding="utf-8")
        print(f"rows written: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
