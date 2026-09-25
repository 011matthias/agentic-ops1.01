"""Harvest confirmed reviewer decisions into the learning store — PR 2a.

`learn_from_run` is the capture half of Phase 2: it reads a finalized run
(the reviewer's confirmed matches + explicit category reclassifications)
and writes the durable facts the consult paths will read in 2b / 2c.

What counts as a teachable, EXPLICIT signal (the finalize-gate honors
decision #2: a half-reviewed month must never teach wrong facts):

* **vendor_alias** and **merchant_fx** come from CONFIRMED matches only.
  Confirming a match is Chris asserting "this charge IS this receipt", so
  the (statement-vendor, receipt-vendor) equivalence and the implied FX
  rate are ground truth.
* **merchant_category** comes from explicit category OVERRIDES only (a
  reclassification). Confirming a match does NOT by itself confirm the
  category the LLM guessed for that receipt, so an un-reclassified Tier-1/
  Tier-2 category is left unlearned. A vendor whose overridden lines
  disagree on category is skipped (counted), never taught a wrong single
  mapping. Item 109: an override on a receiptless CHARGE teaches the same
  way, keyed on the bank's description, so next month's same subscription
  arrives pre-filled; the model's own guess on such a charge writes no
  override and so still teaches nothing.

The function is pure w.r.t. the web layer: it takes matching-domain types
plus the already-computed `confirmed_tx_ids` set and the raw overrides
map, so `learning` never imports `web`. The caller (web.service) owns the
translation from reviewer state to those inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..matching.types import ClassificationSource, MatchOutcome, Receipt, Transaction
from .store import LearningStore, category_is_human, normalize_vendor

# Line-item category sources we treat as a real, learnable category. After
# an override, web.service rewrites the line as source=LINE with reasoning
# "reclassified by reviewer", so reclassifications land here; REVIEW /
# UNCLASSIFIED never do.
_CONCRETE_SOURCES = (ClassificationSource.LINE, ClassificationSource.VENDOR)


def charge_pseudo_receipts(transactions) -> dict[str, Receipt]:
    """Item 109: every charge as the receipt-shaped row `_learn_categories`
    reads, keyed by the pseudo-receipt document id the charge-category edit
    is stored under (`charge:{tx_id}`).

    The pseudo-receipt carries the bank's own description as its vendor and
    the charge's legal entity, so a category the reviewer set on a CHARGE is
    learned under exactly the normalized description the charge categorizer
    will consult next month, through the one shared pass that already holds
    the conflict-skip rule. Charges the reviewer never edited contribute no
    override, so a model guess still teaches nothing."""
    from ..categorize_charges import CHARGE_DOC_PREFIX, build_charge_pseudo_receipt

    return {
        f"{CHARGE_DOC_PREFIX}{t.transaction_id}": build_charge_pseudo_receipt(t)
        for t in (transactions or ())
    }


@dataclass(frozen=True)
class LearnSummary:
    confirmed_pairs: int          # confirmed matches inspected
    vendor_aliases: int           # alias rows written
    merchant_fx: int              # FX samples written
    merchant_categories: int      # category mappings written (from overrides)
    skipped_mixed_category: int   # vendors whose overrides disagreed -> skipped

    def as_dict(self) -> dict:
        return {
            "confirmed_pairs": self.confirmed_pairs,
            "vendor_aliases": self.vendor_aliases,
            "merchant_fx": self.merchant_fx,
            "merchant_categories": self.merchant_categories,
            "skipped_mixed_category": self.skipped_mixed_category,
        }


def learn_from_run(
    store: LearningStore,
    *,
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    confirmed_tx_ids: set[str],
    category_overrides: dict[tuple[str, int], dict],
    source_run: str,
    now_iso: str,
    identity=None,
) -> LearnSummary:
    """Write the teachable facts from one finalized run. `outcome` is the
    decision-applied (effective) outcome; `confirmed_tx_ids` are the
    transactions the reviewer explicitly confirmed; `category_overrides`
    is the raw (document_id, line_index) -> {category, zoho_account} map."""
    rec_by_id = {r.document_id: r for r in receipts}
    confirmed_pairs, n_alias, n_fx = learn_confirmed_pairs(
        store,
        transactions=transactions,
        receipts=receipts,
        outcome=outcome,
        confirmed_tx_ids=confirmed_tx_ids,
        source_run=source_run,
        now_iso=now_iso,
    )

    n_category, n_skipped = _learn_categories(
        store,
        {**rec_by_id, **charge_pseudo_receipts(transactions)},
        category_overrides,
        source_run,
        now_iso,
        identity=identity,
    )

    return LearnSummary(
        confirmed_pairs=confirmed_pairs,
        vendor_aliases=n_alias,
        merchant_fx=n_fx,
        merchant_categories=n_category,
        skipped_mixed_category=n_skipped,
    )


def learn_confirmed_pairs(
    store: LearningStore,
    *,
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    confirmed_tx_ids: set[str],
    source_run: str,
    now_iso: str,
) -> tuple[int, int, int]:
    """Teach the vendor spellings and exchange rates a month's CONFIRMED
    charge/receipt pairs prove. Returns (pairs, aliases, FX samples).

    Split out of `learn_from_run` for item 115: every live month is
    receipt-first WITH a statement, and that sign-off path taught the
    category half only, so the bank's truncated descriptions came back
    unmatched every month while the contract promised otherwise.

    An alias whose statement description or receipt vendor names no
    merchant ("SUPERMERCADO", "Comida e Bebida") is refused, the guard item
    117 put on merchant aliases: those strings identify a KIND of shop, and
    what the matcher would learn from one is a name it cannot tell two
    merchants apart by."""
    from ..merchant_registry import is_generic_alias

    tx_by_id = {t.transaction_id: t for t in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    confirmed_pairs = n_alias = n_fx = 0

    for m in outcome.matches:
        if m.transaction_id not in confirmed_tx_ids:
            continue
        tx = tx_by_id.get(m.transaction_id)
        r = rec_by_id.get(m.document_id)
        if tx is None or r is None:
            continue
        confirmed_pairs += 1

        # vendor alias: teaches the truncated-name equivalence the matcher
        # re-fuzzes every month. Only when both sides carry a vendor.
        if tx.vendor_from_statement and r.detected_vendor:
            sv = normalize_vendor(tx.vendor_from_statement)
            rv = normalize_vendor(r.detected_vendor)
            generic = is_generic_alias(tx.vendor_from_statement) or is_generic_alias(
                r.detected_vendor
            )
            if sv and rv and not generic:
                store.record_vendor_alias(tx.legal_entity_id, sv, rv, now_iso, source_run)
                n_alias += 1

        # per-merchant FX: record the implied rate for a currency-mismatch
        # pair so 2c can refine the band score toward this merchant's DCC.
        if (
            r.detected_currency
            and r.detected_currency != tx.transaction_currency
            and r.detected_total is not None
            and r.detected_total > 0
            and tx.amount > 0
        ):
            vnorm = normalize_vendor(r.detected_vendor or tx.vendor_from_statement or "")
            if vnorm:
                implied = tx.amount / r.detected_total
                store.record_merchant_fx(
                    tx.legal_entity_id,
                    vnorm,
                    r.detected_currency,
                    tx.transaction_currency,
                    implied,
                    now_iso,
                    source_run,
                )
                n_fx += 1

    return confirmed_pairs, n_alias, n_fx


@dataclass(frozen=True)
class AliasCandidate:
    """A merchant spelling a person's pairing proves (item 216 cause 3): the
    registry merchant one side of the pair resolves to, and the other side's
    name, which the registry does not resolve yet."""

    canonical: str
    alias: str
    transaction_id: str
    document_id: str


def identity_alias_candidates(
    *,
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    person_confirmed_tx_ids: set[str],
    identity,
) -> tuple[list[AliasCandidate], int]:
    """The alias learner: what a month's person-confirmed pairs prove about
    merchant IDENTITY. Returns `(candidates, conflicts)`.

    A pair a person confirmed says "this charge IS this receipt", so when one
    side resolves to a registry merchant and the other does not (the bank's
    "ANTHROPIC* CLAUDE SUB" against a receipt from "Anthropic, PBC"), the
    unresolved name is that merchant's spelling. That is identity, not a
    category, so the owner's ruling that only corrections are memorized is
    kept: nothing here says what the merchant is booked to.

    Only a PERSON's confirmation counts (the 2026-09-24 leak-3 ruling): the
    caller passes the ids `reviewer_confirmed_tx_ids` returns, which leaves
    out every pairing the tool confirmed itself (`decided_by` tool).

    Candidates are returned, never written: the caller puts them on the
    memory plan as registry lessons, where Publish shows them and a person
    keeps or drops each (item 183 half A). Both sides resolving to two
    DIFFERENT registry merchants is counted as a conflict and teaches
    nothing; neither side resolving teaches nothing either, because a new
    merchant is a person's call, not a pairing's."""
    from ..merchant_registry import is_generic_alias

    tx_by_id = {t.transaction_id: t for t in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    out: list[AliasCandidate] = []
    seen: set[tuple[str, str]] = set()
    conflicts = 0
    for m in outcome.matches:
        if m.transaction_id not in person_confirmed_tx_ids:
            continue
        tx = tx_by_id.get(m.transaction_id)
        r = rec_by_id.get(m.document_id)
        if tx is None or r is None:
            continue
        rid = identity.resolve(getattr(r, "vendor_clean", None), r.detected_vendor)
        tid = identity.resolve(None, tx.vendor_from_statement)
        if rid is None or tid is None or rid.key == tid.key:
            continue
        r_reg, t_reg = rid.source == "registry", tid.source == "registry"
        if r_reg and t_reg:
            conflicts += 1
            continue
        if r_reg:
            canonical, alias = rid.canonical, tx.vendor_from_statement
        elif t_reg:
            canonical, alias = tid.canonical, r.detected_vendor
        else:
            continue
        alias = (alias or "").strip()
        if not alias or is_generic_alias(alias):
            continue
        key = (canonical, normalize_vendor(alias))
        if key in seen:
            continue
        seen.add(key)
        out.append(AliasCandidate(canonical, alias, m.transaction_id, m.document_id))
    return out, conflicts


@dataclass(frozen=True)
class ExpenseLearnSummary:
    """What one finalized expense batch taught (receipt-first, Phase 6)."""

    merchant_categories: int      # category mappings written (from overrides)
    skipped_mixed_category: int   # vendors whose overrides disagreed -> skipped
    merchant_entities: int        # vendor -> entity mappings written
    field_corrections: int        # (vendor, field) -> value corrections written

    def as_dict(self) -> dict:
        return {
            "merchant_categories": self.merchant_categories,
            "skipped_mixed_category": self.skipped_mixed_category,
            "merchant_entities": self.merchant_entities,
            "field_corrections": self.field_corrections,
        }


# Header fields a reviewer edit teaches as a per-merchant correction. The
# key is the ORIGINAL extracted vendor (what OCR will read again next
# month); `vendor` teaches the canonical spelling itself.
# `card_key` (item 87): a reviewer's per-row card fix, remembered per vendor.
_LEARNABLE_FIELDS = ("vendor", "tax_label", "paid_through", "card_key")


def learn_from_expense_run(
    store: LearningStore,
    *,
    receipts: list[Receipt],
    effective_receipts: list[Receipt],
    field_overrides: dict[str, dict[str, str]],
    category_overrides: dict[tuple[str, int], dict],
    manual_payloads: dict[str, dict] | None = None,
    transactions: list[Transaction] | None = None,
    source_run: str,
    now_iso: str,
    identity=None,
) -> ExpenseLearnSummary:
    """Harvest one finalized expense batch (receipt-first, Phase 6).

    Only EXPLICIT edits teach — the same finalize-gate discipline as
    `learn_from_run`; an untouched LLM guess and the batch-level default
    entity never do:

    * **merchant_category** — explicit line reclassifications, via the
      shared `_learn_categories`, keyed on the EFFECTIVE (post-edit)
      vendor + entity so a corrected spelling learns under its canon.
      Item 109: `transactions` (the month's charges, absent on a batch with
      no statement yet) carries the charge categories she set with no
      receipt, learned under the bank's normalized description.
    * **merchant_entity** — a per-expense entity OVERRIDE, or a manual
      add whose payload names the entity. The batch default is a bulk
      choice, not a per-merchant judgment; it teaches nothing.
    * **field_correction** — vendor / tax_label / paid_through edits,
      keyed on the ORIGINAL extracted vendor (what OCR will produce
      again) under the expense's effective entity.

    `receipts` is the ORIGINAL snapshot pool (pre-overlay); the caller
    passes `effective_receipts` (post `apply_expense_edits`) so both
    vendor spellings are visible here without re-deriving the overlay.
    """
    orig_by_id = {r.document_id: r for r in receipts}
    eff_by_id = {r.document_id: r for r in effective_receipts}

    n_entity = n_field = 0

    for document_id, fields in field_overrides.items():
        eff = eff_by_id.get(document_id)
        if eff is None:
            continue  # edit on a deleted / unknown expense teaches nothing
        orig = orig_by_id.get(document_id)
        # Per-expense entity override -> merchant -> entity mapping, keyed
        # on BOTH the original extracted vendor (what OCR will read again
        # next month) and the effective one (the canonical spelling), so
        # the mapping hits whether or not a vendor correction also applies.
        if fields.get("legal_entity"):
            keys = {
                normalize_vendor(v)
                for v in (
                    (orig.detected_vendor if orig else None),
                    eff.detected_vendor,
                )
                if v
            } - {""}
            for vnorm in keys:
                store.record_merchant_entity(
                    vnorm, fields["legal_entity"].strip(), now_iso, source_run
                )
                n_entity += 1
        # Header corrections, keyed on the ORIGINAL extracted vendor. A
        # manual add has no OCR original to correct — skipped by design.
        if orig is None or not orig.detected_vendor:
            continue
        okey = normalize_vendor(orig.detected_vendor)
        if not okey:
            continue
        for f in _LEARNABLE_FIELDS:
            value = (fields.get(f) or "").strip()
            if value:
                store.record_field_correction(
                    eff.legal_entity_id, okey, f, value, now_iso, source_run
                )
                n_field += 1

    # A manual add that names its entity is an explicit vendor -> entity
    # statement too.
    for document_id, payload in (manual_payloads or {}).items():
        entity = str(payload.get("legal_entity") or "").strip()
        vendor = str(payload.get("vendor") or "").strip()
        if not entity or not vendor:
            continue
        vnorm = normalize_vendor(vendor)
        if vnorm:
            store.record_merchant_entity(vnorm, entity, now_iso, source_run)
            n_entity += 1

    # Item 109: a month is an expense batch with a statement attached, so THIS
    # is the sign-off path a real month takes, and the charge categories she
    # set are learned here beside the receipt ones.
    n_category, n_skipped = _learn_categories(
        store,
        expense_category_sources(effective_receipts, transactions),
        category_overrides,
        source_run,
        now_iso,
        identity=identity,
    )

    return ExpenseLearnSummary(
        merchant_categories=n_category,
        skipped_mixed_category=n_skipped,
        merchant_entities=n_entity,
        field_corrections=n_field,
    )


def expense_category_sources(
    effective_receipts: list[Receipt], transactions=None,
) -> dict[str, Receipt]:
    """The rows an expense month's category overrides are keyed against:
    its effective receipts, and each charge as its pseudo-receipt (item 109).
    One builder, so the learner and item 183's checklist read the same map."""
    return {
        **{r.document_id: r for r in effective_receipts},
        **charge_pseudo_receipts(transactions),
    }


def taught_value(ov: dict | None) -> tuple[str | None, str | None]:
    """What one override row teaches: `(category, account)`. The category
    only when it is hers (`category_is_human`, the 2026-09-24 ruling); the
    account always, because naming it is the correction she made."""
    ov = ov or {}
    category = ov.get("category") if category_is_human(ov) else None
    return (category or None), (ov.get("zoho_account") or None)


def category_key(r: Receipt | None, identity=None) -> tuple[str, str] | None:
    """The `(legal_entity_id, merchant key)` a row's category lesson is
    stored under, or None when the row names no vendor.

    Item 216 cause 3: the key is the merchant IDENTITY
    (`merchant_identity`), the same key recall asks under, so a correction on
    "Anthropic, PBC" is stored as `anthropic` and two spellings of one
    merchant in one month are one lesson (and one conflict test), not two.
    `identity` carries the registry when the caller has one; without it the
    name-only identity applies."""
    if r is None or not r.detected_vendor:
        return None
    if identity is None:
        from ..merchant_identity import identity_key

        vnorm = identity_key(r.detected_vendor)
    else:
        vnorm = identity.key(r.detected_vendor)
    vnorm = vnorm or normalize_vendor(r.detected_vendor)
    if not vnorm:
        return None
    return (r.legal_entity_id, vnorm)


def merge_taught(values) -> tuple[str | None, str | None, bool]:
    """Fold several rows' `(category, account)` into one, with the conflict
    flag. Absence is not disagreement: the first NAMED value wins over rows
    naming none, and only two named, different values conflict (item 183)."""
    category = account = None
    conflict = False
    for cat, acct in values:
        if cat:
            if not category:
                category = cat
            elif category != cat:
                conflict = True
        if acct:
            if not account:
                account = acct
            elif account != acct:
                conflict = True
    return category, account, conflict


def category_groups(
    rec_by_id: dict[str, Receipt],
    category_overrides: dict[tuple[str, int], dict],
    identity=None,
) -> dict[tuple[str, str], list[tuple[tuple[str, int], tuple]]]:
    """Every override row that teaches something, grouped by the key it
    teaches: `{(entity, vendor_norm): [((doc, line), (category, account))]}`.
    `_learn_categories` writes one row per group; item 183's checklist names
    each group's rows and splits a conflicting group into its candidates."""
    groups: dict[tuple[str, str], list] = {}
    for (document_id, line_index), ov in category_overrides.items():
        value = taught_value(ov)
        if not any(value):
            continue
        key = category_key(rec_by_id.get(document_id), identity)
        if key is None:
            continue
        groups.setdefault(key, []).append(((document_id, line_index), value))
    return groups


def _learn_categories(
    store: LearningStore,
    rec_by_id: dict[str, Receipt],
    category_overrides: dict[tuple[str, int], dict],
    source_run: str,
    now_iso: str,
    identity=None,
) -> tuple[int, int]:
    """Collapse per-line reclassifications to one (legal_entity, vendor) ->
    category mapping each, skipping vendors whose overrides disagree.

    Disagreement is on the category OR on the posting account (item 183):
    under the direct-to-GL design the account is the answer, so two rows
    naming different accounts are as much a conflict as two naming different
    categories, and both skip the vendor rather than letting the first row
    win. A row that names NO account is silent rather than dissenting.

    **Only a person's own category is teachable (2026-09-24 owner ruling:
    only corrections are memorized).** An override row stores a category in
    two cases where nobody stated one - the note-#62 Confirm, which keeps the
    model's guess as it stands, and an account-only PUT, which re-stores the
    line's current category beside the account she did name - and both used
    to arrive here indistinguishable from a reclassification. They now read
    `category_source=inherited` and their CATEGORY is dropped: it is not hers
    to teach, and it does not get a vote in the conflict test either (a
    machine guess disagreeing with a human statement is not a disagreement).
    Her ACCOUNT still teaches, because that is the correction she made, and
    dropping it would lose the one fact the direct-to-GL chain most needs.
    Absence of provenance reads as human, per `category_is_human`.

    Item 183, the half that matters most: this table IS Tier 1 of the
    direct-to-GL chain, consulted before the model, so two rows agreeing on
    the category and naming different accounts conflict too (`merge_taught`)
    rather than letting the first account win silently."""
    n_category = n_skipped = 0
    for (legal_entity_id, vnorm), rows in category_groups(
        rec_by_id, category_overrides, identity
    ).items():
        category, account, conflict = merge_taught(v for _row, v in rows)
        if conflict:
            n_skipped += 1
            continue
        store.record_merchant_category(
            legal_entity_id,
            vnorm,
            category,
            account,
            now_iso,
            source_run,
            # Item 183: no account named by any of this vendor's edits means
            # the reviewer said nothing about where it posts, which must not
            # read as "forget what you learned".
            keep_account=not account,
            # The mirror: no category of HERS among this vendor's edits means
            # she said nothing about the category, so a stored one survives
            # and the model's guess never replaces it.
            keep_category=not category,
        )
        n_category += 1

    return n_category, n_skipped


def learn_category_candidate(
    store: LearningStore,
    rec_by_id: dict[str, Receipt],
    category_overrides: dict[tuple[str, int], dict],
    rows: list[tuple[str, int]],
    source_run: str,
    now_iso: str,
    identity=None,
) -> tuple[int, int]:
    """Item 183: the learner run over ONE conflict candidate's rows only.

    A conflicting vendor teaches nothing at sign-off. When the reviewer picks
    one of its candidates on the Publish checklist, the write comes from the
    same `_learn_categories` over exactly those rows, never from a call built
    by hand, so what a candidate would teach and what it does teach are one
    code path. Two candidates of one vendor kept together conflict again and
    teach nothing, which is the learner's own answer."""
    subset = {k: category_overrides[k] for k in rows if k in category_overrides}
    return _learn_categories(
        store, rec_by_id, subset, source_run, now_iso, identity=identity,
    )
