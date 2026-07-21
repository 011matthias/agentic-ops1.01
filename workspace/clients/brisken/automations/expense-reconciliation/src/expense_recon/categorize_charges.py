"""Receiptless-charge categorization — BLUEPRINT Slice 10 (Tier 2).

Criss's real month-end job is to categorize + status EVERY charge on the
statement, not only the ones an expense-report receipt reconciled
against. Before this slice, a charge with no receipt (every USD SaaS
subscription: Anthropic, Adobe, Microsoft, OpenAI) landed in
`unmatched_transactions`, got no category, and was excluded from the
Zoho journal — the biggest gap the 2026-07-20 "Using-the-data revision"
root-caused on her first real run.

Mechanism: for each unmatched transaction, build a **charge
pseudo-receipt** (a `Receipt` with EMPTY `line_items`, vendor = the
statement Description, total/currency/date from the charge, synthetic
`document_id="charge:{tx_id}"`) and delegate to the EXISTING
`categorize_receipts`. The empty line_items force the vendor-fallback
branch, so a receiptless charge resolves exactly per the LD-2
charge-level tier:

* **LEARNED first** — a confirmed merchant->category from the Phase-2
  store (free dict hit; carries the real Zoho Books account, e.g. the
  standing Anthropic -> "Other Infra and IT Costs for Cloud Business"
  rule). Tier-1 provenance, blue in the report.
* **VENDOR fallback** — keyword table or LLM vendor call when nothing
  is learned. Marked ⚠, review-only, never posted.
* **REVIEW** — no signal at all; Criss assigns.

Never LINE: a statement Description is not a line item, so the strict
LD-2 line-item rule is structurally unreachable here.

Invariant (reconciliation guarantee): this pass runs AFTER
`match_month`, only READS `outcome.unmatched_transactions`, and returns
a side-map `{transaction_id: Categorization}` stored on
`ReconcileResult.charge_categorizations`. Pseudo-receipts are never fed
to the matcher, never joined into the run's receipt list, and bucket
membership never changes — the categorization is an ANNOTATION on
charges that stay unmatched.

Slice 11 (P1) lives here too: `derive_subscription_status` marks a
charge `entry_status="subscription"` when its vendor recurs in >= 2
distinct PRIOR months of the built `StatementStore` — the source-
agnostic twin of the gray-fill channel Criss's xlsx already carries.
Annotation only; fill/operator precedence (an already-set entry_status
is never overwritten).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .categorize import categorize_receipts
from .matching.types import Categorization, MatchOutcome, Receipt, Transaction

if TYPE_CHECKING:
    from .learning import MerchantCategoryLookup
    from .llm.client import LLMClient
    from .store import StatementStore

CHARGE_DOC_PREFIX = "charge:"

# Slice 11: how many distinct prior months a vendor must appear in
# before a charge is derived as a subscription.
MIN_PRIOR_MONTHS = 2


def build_charge_pseudo_receipt(tx: Transaction) -> Receipt:
    """The charge as a receipt-shaped input for the vendor-fallback
    categorization path. Empty `line_items` is load-bearing: it routes
    `categorize_receipts` past the LINE tier (LD-2: never LINE for a
    charge)."""
    return Receipt(
        document_id=f"{CHARGE_DOC_PREFIX}{tx.transaction_id}",
        legal_entity_id=tx.legal_entity_id,
        detected_date=tx.transaction_date,
        detected_total=tx.amount,
        detected_currency=tx.transaction_currency,
        detected_vendor=tx.vendor_from_statement,
        line_items=(),
    )


def categorize_charges(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    *,
    client: "LLMClient | None" = None,
    chart_of_accounts: list[str] | None = None,
    learned: "MerchantCategoryLookup | None" = None,
    override_er_category: bool = False,
) -> dict[str, Categorization]:
    """Categorize every unmatched (receiptless) charge.

    Returns `{transaction_id: Categorization}` for the transactions in
    `outcome.unmatched_transactions`. Reads the outcome, never mutates
    it; the caller stores the map on `ReconcileResult` and the output
    writers surface it on the unmatched rows.

    `client` / `chart_of_accounts` / `learned` are passed through to
    `categorize_receipts` unchanged, so the charge path consults the
    same memory and account labels as the receipt path.
    """
    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    pseudo: list[Receipt] = []
    for tx_id in outcome.unmatched_transactions:
        tx = tx_by_id.get(tx_id)
        if tx is None:
            continue
        pseudo.append(build_charge_pseudo_receipt(tx))
    if not pseudo:
        return {}

    categorized = categorize_receipts(
        pseudo, client=client, chart_of_accounts=chart_of_accounts, learned=learned,
        override_er_category=override_er_category,
    )

    out: dict[str, Categorization] = {}
    for rec in categorized:
        if not rec.document_id.startswith(CHARGE_DOC_PREFIX):
            continue  # defensive; categorize_receipts preserves ids
        tx_id = rec.document_id[len(CHARGE_DOC_PREFIX):]
        if rec.line_items and rec.line_items[0].categorization is not None:
            out[tx_id] = rec.line_items[0].categorization
    return out


# ── Slice 11 (P1): source-agnostic subscription derivation ──────────


def derive_subscription_status(
    transactions: list[Transaction],
    store: "StatementStore",
    *,
    min_prior_months: int = MIN_PRIOR_MONTHS,
) -> list[Transaction]:
    """Mark recurring vendors as subscriptions from statement history.

    A charge whose (normalized) vendor appears in at least
    `min_prior_months` distinct months STRICTLY BEFORE the charge's own
    month in the `StatementStore` gets `entry_status="subscription"`.
    Same-month rows (including this run's own rows from a prior
    identical run) never count, so re-runs are stable.

    Precedence fill/operator > derived: a transaction that already
    carries an `entry_status` (her yellow/gray fill, a reviewer's
    already-posted mark) is returned unchanged. Annotation only —
    bucket membership and amounts are untouched.
    """
    from dataclasses import replace

    from .learning.store import normalize_vendor

    months_by_vendor: dict[tuple[str, str], set[str]] = {}
    for tx in store.transactions():
        if tx.transaction_date is None:
            continue
        vnorm = normalize_vendor(tx.vendor_from_statement or "")
        if not vnorm:
            continue
        key = (tx.legal_entity_id, vnorm)
        months_by_vendor.setdefault(key, set()).add(
            tx.transaction_date.strftime("%Y-%m")
        )

    out: list[Transaction] = []
    for tx in transactions:
        if tx.entry_status is not None or tx.transaction_date is None:
            out.append(tx)
            continue
        vnorm = normalize_vendor(tx.vendor_from_statement or "")
        months = months_by_vendor.get((tx.legal_entity_id, vnorm), set())
        own_month = tx.transaction_date.strftime("%Y-%m")
        prior = {m for m in months if m < own_month}
        if len(prior) >= min_prior_months:
            out.append(replace(tx, entry_status="subscription"))
        else:
            out.append(tx)
    return out
