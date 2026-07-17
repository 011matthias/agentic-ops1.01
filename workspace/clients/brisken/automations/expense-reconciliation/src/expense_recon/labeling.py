"""Ground-truth pairing labels for matcher calibration (optimize-loop prep).

Builds the labeled statement-row <-> receipt fixture that the future
`recon-match-accuracy` scorer measures against. Three subcommands under
`expense-recon label`, forming a propose -> human-edit -> accept flow:

  propose --config run.json [--out labels-proposed.csv]
      Load the bundle, generate candidate pairs from independent evidence,
      write a review CSV. Rows with one conclusive candidate are verdict
      AUTO (decision prefilled); the rest are PICK (human chooses) or NONE.
  accept --config run.json [--proposal labels-proposed.csv] [--out labels.csv]
      Read the (human-edited) proposal's `decision` column and write the
      canonical labels.csv, hard-failing on unknown ids or a transaction
      claimed twice. Blank decisions are skipped (unlabeled, reported).
  check --config run.json [--labels labels.csv]
      Structural validation of an existing labels.csv against the bundle:
      ids resolve, one transaction per receipt, evidence re-derivable.
      Exit 1 on structural violations. This is the fixture-integrity core
      the scorer will reuse.

The proposal logic is DELIBERATELY independent of matching/deterministic.py:
labels ranked by the matcher's own scoring would inherit its blind spots and
make the accuracy metric circular (the tuned matcher would be graded by
itself). Evidence here uses only bank-printed and report-carried facts:

  E1 original-amount hit  tx.original_currency == receipt currency AND
                          tx.original_amount == receipt total exactly
                          (the Chase PDF FX detail lines; strongest signal)
  E2 same-currency exact  tx.transaction_currency == receipt currency AND
                          tx.amount == receipt total exactly
  E3 base-amount hit      receipt.base_amount (Zoho's own conversion) within
                          BASE_AMOUNT_TOL_PCT of tx.amount (Zoho ER sources)
  E4 reference hit        receipt.detected_reference (>= MIN_REF_LEN chars,
                          normalized) appears in the tx raw text / vendor

E1/E2 are conclusive tiers; a receipt with exactly ONE tier-1 candidate that
is itself no other receipt's only tier-1 candidate goes AUTO. E3/E4 only
rank PICK candidates. Sources without FX detail or provenance (the slice-1
CSV bridge bundles) simply light up fewer tiers; propose prints which tiers
were active so evidence-poor bundles are visible, not silently thin.

Ambiguity discipline (docs/optimize/RECIPES.md constructed-metric protocol):
an ambiguous receipt is EXCLUDED from ground truth by the human (decision
`exclude`), never guessed. A receipt legitimately absent from the statement
(paid cash / another card) is `no_charge`.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from .matching.types import Receipt, Transaction

# Wide by design: labeling wants recall, the matcher wants precision.
DATE_WINDOW_DAYS = 14
BASE_AMOUNT_TOL_PCT = Decimal("0.02")
MIN_REF_LEN = 5
MAX_LISTED_CANDIDATES = 3

_NORM = re.compile(r"[^A-Z0-9]+")

PROPOSAL_FIELDS = [
    "document_id", "verdict", "decision", "receipt_date", "receipt_total",
    "receipt_currency", "receipt_vendor", "report_number", "n_candidates",
]
for _i in range(1, MAX_LISTED_CANDIDATES + 1):
    PROPOSAL_FIELDS += [
        f"cand{_i}_tx_id", f"cand{_i}_date", f"cand{_i}_amount",
        f"cand{_i}_vendor", f"cand{_i}_evidence",
    ]

LABEL_FIELDS = ["document_id", "transaction_id", "status", "source", "evidence"]
VALID_STATUSES = ("confirmed", "excluded", "no_charge")


@dataclass(frozen=True)
class Candidate:
    tx: Transaction
    evidence: tuple[str, ...]   # e.g. ("E1:original-amount", "E4:ref")

    @property
    def conclusive(self) -> bool:
        return any(e.startswith(("E1:", "E2:")) for e in self.evidence)


def _norm(text: str | None) -> str:
    return _NORM.sub("", (text or "").upper())


def _dates_plausible(tx: Transaction, receipt: Receipt) -> bool:
    if receipt.detected_date is None:
        return True  # date-less receipt: amount evidence must carry it
    window = timedelta(days=DATE_WINDOW_DAYS)
    anchors = [tx.transaction_date] + (
        [tx.posting_date] if tx.posting_date else []
    )
    return any(abs(receipt.detected_date - a) <= window for a in anchors)


def evidence_for(tx: Transaction, receipt: Receipt) -> tuple[str, ...]:
    """Independent evidence that THIS receipt belongs to THIS transaction.

    Empty tuple = not a candidate. Order: conclusive tiers first.
    """
    if not _dates_plausible(tx, receipt):
        return ()
    found: list[str] = []
    r_cur = (receipt.detected_currency or "").upper()
    r_total = receipt.detected_total

    if (
        r_total is not None
        and tx.original_amount is not None
        and (tx.original_currency or "").upper() == r_cur
        and tx.original_amount == r_total
    ):
        found.append("E1:original-amount")
    if (
        r_total is not None
        and tx.transaction_currency.upper() == r_cur
        and tx.amount == r_total
    ):
        found.append("E2:amount-exact")
    if (
        receipt.base_amount is not None
        and tx.amount
        and abs(tx.amount - receipt.base_amount) / abs(tx.amount)
        <= BASE_AMOUNT_TOL_PCT
    ):
        found.append("E3:base-amount")
    ref = _norm(receipt.detected_reference)
    if len(ref) >= MIN_REF_LEN and ref in _norm(
        tx.raw_text + " " + tx.vendor_from_statement
    ):
        found.append("E4:ref")
    return tuple(found)


def build_candidates(
    transactions: list[Transaction], receipts: list[Receipt]
) -> dict[str, list[Candidate]]:
    """document_id -> candidates, conclusive tiers first, then by date gap."""
    out: dict[str, list[Candidate]] = {}
    for r in receipts:
        cands = []
        for tx in transactions:
            ev = evidence_for(tx, r)
            if ev:
                cands.append(Candidate(tx=tx, evidence=ev))

        def _gap(c: Candidate) -> int:
            if r.detected_date is None:
                return 999
            return abs((r.detected_date - c.tx.transaction_date).days)

        cands.sort(key=lambda c: (not c.conclusive, _gap(c), c.tx.transaction_id))
        out[r.document_id] = cands
    return out


def auto_pairs(candidates: dict[str, list[Candidate]]) -> dict[str, str]:
    """document_id -> transaction_id for conclusive, mutually-unique pairs.

    AUTO requires uniqueness BOTH ways: the receipt has exactly one
    conclusive candidate, and that transaction is no other receipt's
    conclusive candidate. Two identical charges (same amount, same window)
    therefore demote each other to PICK - correct, a human decides.
    """
    doc_tier1: dict[str, list[str]] = {
        doc: [c.tx.transaction_id for c in cands if c.conclusive]
        for doc, cands in candidates.items()
    }
    tx_claims: dict[str, list[str]] = {}
    for doc, txs in doc_tier1.items():
        for t in txs:
            tx_claims.setdefault(t, []).append(doc)
    return {
        doc: txs[0]
        for doc, txs in doc_tier1.items()
        if len(txs) == 1 and len(tx_claims[txs[0]]) == 1
    }


def _load_bundle(config_path: Path):
    """(transactions, receipts, config_dir) via the CLI's own loaders."""
    from .cli import ConfigError, _load_receipts, _load_statement

    config_path = config_path.resolve()
    if not config_path.exists():
        raise SystemExit(f"ERROR: config file not found: {config_path}")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    config_dir = config_path.parent
    try:
        transactions, _ = _load_statement(cfg, config_dir)
        receipts, _ = _load_receipts(
            cfg, config_dir,
            legal_entity_id=cfg["statement"]["legal_entity_id"],
            llm_client=None,
        )
    except ConfigError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    return transactions, receipts, config_dir


def cmd_propose(config: Path, out: Path | None) -> int:
    transactions, receipts, config_dir = _load_bundle(config)
    candidates = build_candidates(transactions, receipts)
    autos = auto_pairs(candidates)
    out = out or (config_dir / "labels-proposed.csv")

    tiers_active: set[str] = set()
    rows = []
    for r in sorted(receipts, key=lambda r: r.document_id):
        cands = candidates[r.document_id]
        for c in cands:
            tiers_active.update(e.split(":")[0] for e in c.evidence)
        verdict = ("AUTO" if r.document_id in autos
                   else "PICK" if cands else "NONE")
        row = {
            "document_id": r.document_id,
            "verdict": verdict,
            "decision": autos.get(r.document_id, ""),
            "receipt_date": r.detected_date or "",
            "receipt_total": r.detected_total if r.detected_total is not None else "",
            "receipt_currency": r.detected_currency or "",
            "receipt_vendor": r.detected_vendor or "",
            "report_number": r.report_number or "",
            "n_candidates": len(cands),
        }
        for i, c in enumerate(cands[:MAX_LISTED_CANDIDATES], start=1):
            amount = f"{c.tx.amount} {c.tx.transaction_currency}"
            if c.tx.original_amount is not None:
                amount += f" (orig {c.tx.original_amount} {c.tx.original_currency})"
            row[f"cand{i}_tx_id"] = c.tx.transaction_id
            row[f"cand{i}_date"] = c.tx.transaction_date
            row[f"cand{i}_amount"] = amount
            row[f"cand{i}_vendor"] = c.tx.vendor_from_statement
            row[f"cand{i}_evidence"] = "+".join(c.evidence)
        rows.append(row)

    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PROPOSAL_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    n = {"AUTO": 0, "PICK": 0, "NONE": 0}
    for row in rows:
        n[row["verdict"]] += 1
    print("LABEL PROPOSAL")
    print(f"  Receipts:      {len(receipts)}")
    print(f"  Transactions:  {len(transactions)}")
    print(f"  AUTO:          {n['AUTO']}  (conclusive + mutually unique)")
    print(f"  PICK:          {n['PICK']}  (human decides)")
    print(f"  NONE:          {n['NONE']}  (no plausible charge in window)")
    print(f"  Evidence tiers active: "
          f"{', '.join(sorted(tiers_active)) or 'none'}")
    print(f"  Proposal written: {out}")
    print("  Edit the `decision` column (tx id | exclude | no_charge), "
          "then run `label accept`.")
    return 0


def cmd_accept(config: Path, proposal: Path | None, out: Path | None) -> int:
    transactions, receipts, config_dir = _load_bundle(config)
    proposal = proposal or (config_dir / "labels-proposed.csv")
    out = out or (config_dir / "labels.csv")
    if not proposal.exists():
        raise SystemExit(f"ERROR: proposal not found: {proposal} - run "
                         "`label propose` first")
    tx_ids = {t.transaction_id for t in transactions}
    doc_ids = {r.document_id for r in receipts}
    candidates = build_candidates(transactions, receipts)
    autos = auto_pairs(candidates)

    labels, claimed, skipped = [], {}, 0
    with open(proposal, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            doc = row["document_id"]
            decision = (row.get("decision") or "").strip()
            if doc not in doc_ids:
                raise SystemExit(f"ERROR: unknown document_id {doc!r} in "
                                 "proposal (stale file for this bundle?)")
            if not decision:
                skipped += 1
                continue
            if decision in ("exclude", "no_charge"):
                labels.append({"document_id": doc, "transaction_id": "",
                               "status": decision, "source": "human",
                               "evidence": ""})
                continue
            if decision not in tx_ids:
                raise SystemExit(f"ERROR: decision {decision!r} for {doc} is "
                                 "not a transaction id in this bundle")
            if decision in claimed:
                raise SystemExit(f"ERROR: transaction {decision} claimed by "
                                 f"both {claimed[decision]} and {doc}")
            claimed[decision] = doc
            ev = next((c.evidence for c in candidates[doc]
                       if c.tx.transaction_id == decision), ())
            source = "auto" if autos.get(doc) == decision else "human"
            labels.append({"document_id": doc, "transaction_id": decision,
                           "status": "confirmed", "source": source,
                           "evidence": "+".join(ev)})

    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        w.writeheader()
        w.writerows(sorted(labels, key=lambda r: r["document_id"]))

    by_status: dict[str, int] = {}
    for lab in labels:
        by_status[lab["status"]] = by_status.get(lab["status"], 0) + 1
    print("LABELS ACCEPTED")
    for status in VALID_STATUSES:
        print(f"  {status:<10} {by_status.get(status, 0)}")
    print(f"  unlabeled  {skipped}  (blank decision - not in ground truth)")
    print(f"  Labels written: {out}")
    return 0


def cmd_check(config: Path, labels_path: Path | None) -> int:
    transactions, receipts, config_dir = _load_bundle(config)
    labels_path = labels_path or (config_dir / "labels.csv")
    if not labels_path.exists():
        raise SystemExit(f"ERROR: labels file not found: {labels_path}")
    tx_by_id = {t.transaction_id: t for t in transactions}
    r_by_id = {r.document_id: r for r in receipts}

    errors, warns, claimed = [], [], {}
    n_rows = 0
    by_status: dict[str, int] = {}
    with open(labels_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            n_rows += 1
            doc, tx_id = row["document_id"], row["transaction_id"]
            status = row["status"]
            by_status[status] = by_status.get(status, 0) + 1
            if status not in VALID_STATUSES:
                errors.append(f"{doc}: invalid status {status!r}")
                continue
            if doc not in r_by_id:
                errors.append(f"{doc}: unknown document_id")
                continue
            if status != "confirmed":
                if tx_id:
                    errors.append(f"{doc}: status {status} must not carry a "
                                  "transaction_id")
                continue
            if tx_id not in tx_by_id:
                errors.append(f"{doc}: unknown transaction_id {tx_id!r}")
                continue
            if tx_id in claimed:
                errors.append(f"{doc}: transaction {tx_id} already claimed "
                              f"by {claimed[tx_id]}")
                continue
            claimed[tx_id] = doc
            if not evidence_for(tx_by_id[tx_id], r_by_id[doc]):
                warns.append(f"{doc} -> {tx_id}: no evidence re-derivable "
                             "(confirm this pair is intentional)")

    print("LABEL CHECK")
    print(f"  Rows:      {n_rows}")
    for status in VALID_STATUSES:
        print(f"  {status:<10} {by_status.get(status, 0)}")
    print(f"  Receipt coverage: {n_rows}/{len(receipts)}")
    for w in warns:
        print(f"  WARN: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    print(f"  Result: {'FAIL' if errors else 'OK'}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon label",
        description="Build ground-truth pairing labels for matcher calibration.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--out", type=Path, default=None)
    p = sub.add_parser("accept")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--proposal", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p = sub.add_parser("check")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--labels", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.cmd == "propose":
        return cmd_propose(args.config, args.out)
    if args.cmd == "accept":
        return cmd_accept(args.config, args.proposal, args.out)
    return cmd_check(args.config, args.labels)


if __name__ == "__main__":
    raise SystemExit(main())
