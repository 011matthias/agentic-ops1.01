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
# direction: maximize
"""Scorer: expense-recon match accuracy vs the human-labelled month fixture.

Measures how well `match_month` under the ASSET tuning file
(config/match-tuning.json) reproduces the 95 human-confirmed
(receipt, charge) pairs across six real Brisken months. Per confirmed
label: +1.0 when the matcher resolves the pair DETERMINISTICALLY
(outcome.matches — the business win: no human, no LLM), +0.3 when the
correct pair is teed up in judgment_required (right answer, deferred),
-2.0 when the receipt is deterministically matched to the WRONG charge
(silently mis-files money). A no_charge-labelled receipt that lands in
matches is also -2.0 (false positive). `excluded` labels are ignored —
a human declared those ambiguous. A naive matched-vs-labels metric has
no gradient here because the shipped matcher defers ~95% of FX pairs;
this composite prices resolution, deferral, and wrongness separately.

SCORE is the TRAIN-split composite (four 2025-26 months, 73 confirmed).
The two 2024 months are HELD OUT and never contribute to SCORE — the
optimize run's guard (tools/recon-accuracy-guard.py) owns them, so the
hill-climb cannot fit the holdout. `--split holdout|all` exist for guard
and human reporting. Split membership is hard-coded on purpose: the
scorer is hash-pinned, so the split cannot be moved by the optimizing
agent.

Notes above the SCORE line carry per-bundle counts and a per-evidence-
tier breakdown (E1 statement-FX-exact / E2 same-ccy-exact / E3
zoho-base-amount / E4 reference). The tier table is the circularity
diagnostic: most confirmed labels were human-accepted off E3 evidence,
so a gain confined to the E3 tier means the matcher is parroting the
labeling heuristic rather than getting better at bank-grade evidence.

Deterministic: pure file reads + the deterministic matcher (no LLM, no
network, no API key; llm_client=None on the load path). Same asset =
same score, byte for byte.

Fixture location: the six bundles live under the repo's gitignored
client context, which exists only in the MAIN clone working directory.
When this scorer runs from a git worktree (the optimize engine's normal
home) the repo-relative path is absent, so it falls back to the
canonical absolute clone path. Same data either way; missing data is
exit 2, never a score.

Contract (tools/scorers/README.md):
  - last stdout line is exactly `SCORE: <number>`
  - exit 0 ONLY on a real measurement; any failure exits non-zero
  - `# direction: maximize` above must match PINS.json AND the manifest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODULE_SRC = (
    REPO / "workspace/clients/brisken/automations/expense-reconciliation/src"
)
_FIXTURE_REL = (
    "workspace/clients/brisken/context/expense-reconciliation/"
    "expense-reports/csv/by-month"
)
# Canonical main-clone home of the gitignored fixture (worktree fallback).
_FIXTURE_CANONICAL = Path(
    "C:/Users/neuma_p1qrsic/Repo/agentic-ops1"
) / _FIXTURE_REL

# Hard-coded split (pinned with the scorer; the optimizing agent cannot
# move it). Train = the four 2025-26 months; holdout = the two 2024 months.
TRAIN_BUNDLES = (
    "01-06-2025_ER-00194",
    "01-03-2026_ER-00214",
    "01-04-2026_ER-00215",
    "01-05-2026_ER-00216",
)
HOLDOUT_BUNDLES = (
    "01-10-2024_ER-00181",
    "01-11-2024_ER-00183",
)

POINTS_DETERM_OK = 1.0
POINTS_DEFERRED_OK = 0.3
POINTS_DETERM_WRONG = -2.0
POINTS_NO_CHARGE_MATCHED = -2.0

_TIER_ORDER = ("E1", "E2", "E3", "E4")

_TOTAL_KEYS = (
    "confirmed", "determ_ok", "determ_wrong", "deferred_ok",
    "ambiguous", "unresolved", "no_charge", "nc_determ_matched",
    "nc_deferred", "double_bound_receipts",
)


def _fixture_root() -> Path:
    local = REPO / _FIXTURE_REL
    if local.is_dir():
        return local
    return _FIXTURE_CANONICAL


def _strongest_tier(evidence: str) -> str:
    """The strongest evidence tier named on a label row ('E1' beats 'E4');
    'none' when the row carries no parsable tier."""
    tiers = {
        part.split(":", 1)[0].strip()
        for part in (evidence or "").split("+")
        if part.strip()
    }
    for t in _TIER_ORDER:
        if t in tiers:
            return t
    return "none"


def _load_labels(path: Path) -> list[dict]:
    import csv

    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def evaluate_bundle(bundle_dir: Path, match_cfg) -> dict:
    """Replay one bundle's run.json under `match_cfg` and score its labels.

    Returns a stats dict; raises SystemExit(2) on unloadable inputs or a
    label whose ids do not resolve (a broken fixture must never be scored
    as a bad asset)."""
    from expense_recon.labeling import _load_bundle
    from expense_recon.matching.deterministic import match_month

    run_json = bundle_dir / "run.json"
    labels_csv = bundle_dir / "labels.csv"
    if not run_json.exists() or not labels_csv.exists():
        raise SystemExit(
            f"ERROR: bundle incomplete: {bundle_dir} "
            "(need run.json + labels.csv)"
        )
    transactions, receipts, _ = _load_bundle(run_json)
    labels = _load_labels(labels_csv)

    tx_ids = {t.transaction_id for t in transactions}
    doc_ids = {r.document_id for r in receipts}

    outcome = match_month(transactions, receipts, match_cfg)
    determ_by_doc = {m.document_id: m.transaction_id for m in outcome.matches}
    deferred_pairs = {
        (m.transaction_id, m.document_id) for m in outcome.judgment_required
    }
    deferred_docs = {d for _, d in deferred_pairs}
    ambiguous_docs = {m.document_id for m in outcome.ambiguous}

    stats: dict = {"bundle": bundle_dir.name, "composite": 0.0,
                   "tiers": {}, "invariant_ok": True}
    for k in _TOTAL_KEYS:
        stats[k] = 0

    # Reconciliation invariant under this asset: every purchase tx in
    # exactly one bucket, and no receipt claimed twice in matches.
    bucketed: list[str] = [m.transaction_id for m in outcome.matches]
    bucketed += [m.transaction_id for m in outcome.judgment_required]
    bucketed += list(outcome.unmatched_transactions)
    bucketed += list(outcome.refunds)
    ambiguous_txs = {m.transaction_id for m in outcome.ambiguous}
    seen = set(bucketed)
    stats["invariant_ok"] = (
        len(bucketed) == len(seen)
        and (seen | ambiguous_txs) == tx_ids
        and not (ambiguous_txs & seen)
    )
    match_docs = [m.document_id for m in outcome.matches]
    stats["double_bound_receipts"] = len(match_docs) - len(set(match_docs))

    for row in labels:
        status = (row.get("status") or "").strip()
        doc = (row.get("document_id") or "").strip()
        tx = (row.get("transaction_id") or "").strip()
        if status == "excluded":
            continue
        if doc not in doc_ids:
            raise SystemExit(
                f"ERROR: label document_id {doc!r} does not resolve in "
                f"{bundle_dir.name} — fixture/ingest drift, not a score"
            )
        if status == "no_charge":
            stats["no_charge"] += 1
            if doc in determ_by_doc:
                stats["nc_determ_matched"] += 1
                stats["composite"] += POINTS_NO_CHARGE_MATCHED
            elif doc in deferred_docs:
                stats["nc_deferred"] += 1
            continue
        if status != "confirmed":
            raise SystemExit(
                f"ERROR: unknown label status {status!r} in {bundle_dir.name}"
            )
        if tx not in tx_ids:
            raise SystemExit(
                f"ERROR: label transaction_id {tx!r} does not resolve in "
                f"{bundle_dir.name} — labels must replay against their own "
                "run.json"
            )
        stats["confirmed"] += 1
        tier = _strongest_tier(row.get("evidence") or "")
        t = stats["tiers"].setdefault(tier, [0, 0])
        t[1] += 1

        got = determ_by_doc.get(doc)
        if got == tx:
            stats["determ_ok"] += 1
            stats["composite"] += POINTS_DETERM_OK
            t[0] += 1
        elif got is not None:
            stats["determ_wrong"] += 1
            stats["composite"] += POINTS_DETERM_WRONG
        elif (tx, doc) in deferred_pairs:
            stats["deferred_ok"] += 1
            stats["composite"] += POINTS_DEFERRED_OK
        elif doc in ambiguous_docs:
            stats["ambiguous"] += 1
        else:
            stats["unresolved"] += 1
    return stats


def evaluate(asset: Path, bundles: tuple[str, ...]) -> list[dict]:
    from expense_recon.matching.deterministic import MatchingConfig

    match_cfg = MatchingConfig.from_file(asset)
    root = _fixture_root()
    out = []
    for name in bundles:
        bundle_dir = root / name
        if not bundle_dir.is_dir():
            raise SystemExit(f"ERROR: bundle missing: {bundle_dir}")
        out.append(evaluate_bundle(bundle_dir, match_cfg))
    return out


def totals(stats: list[dict]) -> dict:
    tot: dict = {k: sum(s[k] for s in stats) for k in _TOTAL_KEYS}
    tot["composite"] = round(sum(s["composite"] for s in stats), 2)
    tot["invariant_ok"] = all(s["invariant_ok"] for s in stats)
    tiers: dict = {}
    for s in stats:
        for tier, (ok, n) in s["tiers"].items():
            cur = tiers.setdefault(tier, [0, 0])
            cur[0] += ok
            cur[1] += n
    tot["tiers"] = tiers
    return tot


def main(argv: list[str]) -> int:
    split = "train"
    as_json = False
    positional: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            as_json = True
        elif a == "--split":
            if i + 1 >= len(argv):
                print("ERROR: --split needs a value", file=sys.stderr)
                return 2
            split = argv[i + 1]
            i += 1
        elif a.startswith("--split="):
            split = a.split("=", 1)[1]
        elif a.startswith("--"):
            print(f"ERROR: unknown flag {a!r}", file=sys.stderr)
            return 2
        else:
            positional.append(a)
        i += 1

    if len(positional) != 1:
        print(
            "usage: recon-match-accuracy.py ASSET.json "
            "[--split train|holdout|all] [--json]",
            file=sys.stderr,
        )
        return 2
    if split not in ("train", "holdout", "all"):
        print(f"ERROR: bad --split {split!r}", file=sys.stderr)
        return 2
    asset = Path(positional[0])
    if not asset.is_file():
        print(f"ERROR: asset not found: {asset}", file=sys.stderr)
        return 2
    if not MODULE_SRC.is_dir():
        print(f"ERROR: module src not found: {MODULE_SRC}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(MODULE_SRC))

    bundles = {
        "train": TRAIN_BUNDLES,
        "holdout": HOLDOUT_BUNDLES,
        "all": TRAIN_BUNDLES + HOLDOUT_BUNDLES,
    }[split]
    stats = evaluate(asset, bundles)
    tot = totals(stats)

    if as_json:
        print(json.dumps({"split": split, "bundles": stats, "totals": tot},
                         default=str, indent=1))
    else:
        for s in stats:
            print(
                f"{s['bundle']}: confirmed={s['confirmed']} "
                f"determ_ok={s['determ_ok']} determ_wrong={s['determ_wrong']} "
                f"deferred_ok={s['deferred_ok']} ambiguous={s['ambiguous']} "
                f"unresolved={s['unresolved']} no_charge={s['no_charge']} "
                f"nc_matched={s['nc_determ_matched']} "
                f"invariant={'OK' if s['invariant_ok'] else 'BROKEN'} "
                f"composite={s['composite']:+.1f}"
            )
        tier_bits = []
        for tier in (*_TIER_ORDER, "none"):
            if tier in tot["tiers"]:
                ok, n = tot["tiers"][tier]
                tier_bits.append(f"{tier}:{ok}/{n}")
        print(f"evidence-tier determ_ok: {'  '.join(tier_bits)}")
        print(
            f"{split} totals: determ_ok={tot['determ_ok']}/{tot['confirmed']} "
            f"determ_wrong={tot['determ_wrong']} "
            f"deferred_ok={tot['deferred_ok']} "
            f"nc_matched={tot['nc_determ_matched']} "
            f"invariant={'OK' if tot['invariant_ok'] else 'BROKEN'}"
        )

    print(f"SCORE: {tot['composite']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
