"""LLMClient protocol + OpenAI + Mock implementations.

The protocol carries the categorization shape (slice 2 part 1), the
FX/ambiguous judgment calls (D1b / 2.4), and receipt extraction
(slice 2.2: vision for images, text for PDFs with a text layer). The
provider swap is one class with the same method signatures.

LD-2 invariants the LLM call must honour:

* Line-item classification reads ONLY the line item's description.
  Vendor name is NEVER in the prompt. Prompts that drift from this
  are a Tier-1 contract violation.
* `confidence < 0.6` routes to REVIEW (caller responsibility, but the
  prompt instructs the LLM to use the full 0.0–1.0 range honestly).
* Vendor fallback is a separate call (Tier 2) with its own prompt;
  vendor name IS the input here, and the result is marked
  `Source: VENDOR`.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .cost import CostTracker, TokenUsage
from .extraction_cache import ExtractionCache, extraction_cache_key, prompt_fingerprint

logger = logging.getLogger("expense_recon")


@dataclass(frozen=True)
class LineItemInput:
    """One line item to classify. Vendor is NOT carried here on purpose
    (LD-2: per-line classification reads description only)."""

    description: str
    line_total: Decimal
    quantity: Decimal | None = None


@dataclass(frozen=True)
class ClassificationResult:
    """One classification decision from the LLM.

    `category` is None when the LLM is not confident enough; the
    caller routes that to REVIEW. `zoho_account` is populated only
    when a chart-of-accounts was supplied (slice 4).
    """

    category: str | None
    zoho_account: str | None
    confidence: float
    reasoning: str


@dataclass(frozen=True)
class FxJudgmentResult:
    """One FX-judgment decision from the LLM (v2 spec §15.2).

    The hard case Dirk specified on the call: a receipt paid in one
    currency (e.g. EUR) against a card transaction posted in another
    (e.g. USD). The amounts never match 1:1, so the model FX-converts
    the receipt into the transaction currency and judges whether the
    two are the same purchase, weighing the converted amount against
    vendor / reference / date signal.

    `same_purchase_confidence` is the model's probability (0.0–1.0)
    that the receipt and the transaction are the SAME purchase.
    `implied_rate` and `converted_amount` are the model's APPROXIMATION
    (receipt currency → transaction currency), surfaced for the
    reviewer to sanity-check. They are an estimate, never an
    authoritative rate (the rate source is §38-TBD), so an FX judgment
    always goes to human review.
    """

    is_match: bool
    same_purchase_confidence: float
    implied_rate: float | None
    converted_amount: Decimal | None
    reasoning: str


@dataclass(frozen=True)
class ExtractedLineItem:
    """One line item as read off a receipt by the vision/text extractor.

    Amounts arrive as strings (the model returns them as strings to
    avoid IEEE-754 noise); the ingest layer casts to Decimal. A
    line_total of None means the model could not read the amount —
    ingest keeps the item with total 0 and the vague-description
    check routes it to REVIEW.
    """

    description: str
    line_total: str | None
    quantity: str | None = None
    unit_price: str | None = None


@dataclass(frozen=True)
class ExtractedReceipt:
    """Header fields + line items extracted from one receipt file
    (BLUEPRINT 2.2). All fields are the model's raw reading; the
    ingest layer parses dates/amounts and applies defaults.

    `line_items` is empty when the receipt shows only a final total
    with no itemization — the extractor must NEVER invent items
    (LD-2; the vendor-fallback path triggers downstream instead).
    """

    date: str | None            # ISO YYYY-MM-DD or None
    total: str | None
    currency: str | None        # ISO 4217 code or None
    vendor: str | None
    reference: str | None
    line_items: tuple[ExtractedLineItem, ...]
    confidence: float
    notes: str = ""
    # Receipt-first parity (2026-07-27): tax/VAT + paying-card hint, raw
    # model readings. None when the receipt does not print them.
    tax: str | None = None
    tax_label: str | None = None
    payment_hint: str | None = None
    # Merchant registry (2026-07-29): the short storefront brand with legal
    # suffixes / distributor tails stripped ("COMERCIO DE X LTDA" -> "X"),
    # so the registry can canonicalize consistently. `vendor` stays the raw
    # reading for audit; None when the model gave no brand.
    vendor_clean: str | None = None
    # Non-receipt quarantine (2026-08-13): the model's classification of what
    # the file IS. Anything but "receipt" (statement page, expense-report
    # summary page, unrelated image) must not become an expense row; the
    # generation path excludes it loudly. Defaults to "receipt" so text-only
    # mocks and older callers keep their behavior.
    document_type: str = "receipt"


@dataclass(frozen=True)
class AmbiguousCandidate:
    """One candidate receipt for a transaction that the deterministic
    layer could not disambiguate (multiple equally-strong matches)."""

    document_id: str
    amount: Decimal | None
    currency: str | None
    date: str | None
    vendor: str | None
    reference: str | None


@dataclass(frozen=True)
class AmbiguousJudgmentResult:
    """The LLM's pick among tied candidates (v2 spec §15.2).

    `chosen_index` is 1-based into the candidate list, or 0 when the
    model is not confident enough to pick — in which case the tie
    stands and all candidates remain for human review.
    """

    chosen_index: int
    confidence: float
    reasoning: str


class LLMClient(Protocol):
    """Provider-agnostic client interface used by the categorizer and
    the FX-judgment layer."""

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        """Tier 1 path (LD-2). One batched call per receipt."""
        ...

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        """Tier 2 fallback (LD-2). Triggered only when line items are
        absent or all vague."""
        ...

    def judge_fx_match(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        receipt_amount: Decimal,
        receipt_currency: str,
        receipt_date: str | None,
        receipt_vendor: str | None,
        receipt_reference: str | None,
        tx_card: str | None = None,
        receipt_payment_mode: str | None = None,
    ) -> FxJudgmentResult:
        """FX judgment (v2 spec §15.2). One call per FX-mismatch
        candidate pair. Unlike LD-2 categorization, vendor name IS a
        legitimate input here — this is a matching task, not a
        line-item classification.

        `tx_card` / `receipt_payment_mode` (WS3) are the two systems'
        records of which card paid — the statement's card column or
        account id, and the Zoho expense's payment-mode label. Optional
        so an older client implementation still satisfies the protocol;
        omitted means "unknown card", never "different card"."""
        ...

    def judge_ambiguous(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        candidates: list[AmbiguousCandidate],
    ) -> AmbiguousJudgmentResult:
        """Pick the best of several tied candidate receipts for one
        transaction (v2 spec §15.2). Returns `chosen_index=0` when no
        candidate is a confident pick."""
        ...

    def extract_receipt(
        self,
        *,
        file_name: str,
        images: list[tuple[bytes, str]] | None = None,
        text: str | None = None,
    ) -> ExtractedReceipt:
        """Receipt OCR (BLUEPRINT 2.2). Exactly one of `images` (list
        of (bytes, mime_type) pages) or `text` (a PDF's text layer)
        is supplied per call."""
        ...


# ── OpenAI implementation ────────────────────────────────────────────


_LINE_ITEMS_PROMPT_TEMPLATE = """You categorize line items from a business expense receipt.

Categories (pick exactly one per line item, or null if you're not confident):
{categories_block}
{accounts_block}
Rules:
- Classify each line item from its DESCRIPTION ALONE.
- Do NOT consider vendor name or any other context. The description must justify the category by itself.
- If a line item is too vague to classify confidently (e.g., "Item 1", "Service charge", short or generic text), set category to null and confidence below 0.6.
- Confidence is your honest assessment in the range 0.0 to 1.0.
- Reasoning is one short sentence (max ~15 words) explaining your pick.

Line items to classify:
{items_block}

Return a JSON object with key "results" whose value is an array of {n_items} objects, one per input item, in the same order. Each object has: index (1-based, matching the input), category (one of the listed names or null), confidence (number), reasoning (string), zoho_account (copy the exact label of the single best-matching GL account from the account list above, or null if no account list was given or none clearly fits).
"""

_VENDOR_PROMPT_TEMPLATE = """You categorize a business expense receipt using only the vendor name and total amount. The receipt has no line-item breakdown.

Categories (pick exactly one, or null if you cannot infer with reasonable confidence):
{categories_block}

Rules:
- The vendor name is your only clue. Use it conservatively — if multiple categories are plausible, prefer the most common business interpretation but lower your confidence.
- Confidence is your honest assessment in 0.0–1.0.
- Reasoning is one short sentence (max ~15 words).

Vendor: {vendor}
Total: {total}
{accounts_block}
Return a single JSON object with: category (one of the listed names or null), confidence (number), reasoning (string), zoho_account (copy the exact label of the single best-matching GL account from the account list above, or null if no account list was given or none clearly fits).
"""


_LINE_ITEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "category": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "zoho_account": {"type": ["string", "null"]},
                },
                "required": ["index", "category", "confidence", "reasoning", "zoho_account"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

_VENDOR_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "zoho_account": {"type": ["string", "null"]},
    },
    "required": ["category", "confidence", "reasoning", "zoho_account"],
    "additionalProperties": False,
}


_FX_JUDGMENT_PROMPT_TEMPLATE = """You reconcile a card-statement transaction against a receipt that was paid in a different currency.

Because the currencies differ, the amounts will not match 1:1; an FX conversion is needed. Judge whether the receipt is plausibly the SAME purchase as the transaction.

Transaction (from the card statement):
  amount: {tx_amount} {tx_currency}
  date: {tx_date}
  vendor as printed on the statement: {tx_vendor}
  card it was charged to: {tx_card}

Receipt:
  amount: {receipt_amount} {receipt_currency}
  date: {receipt_date}
  vendor: {receipt_vendor}
  reference: {receipt_reference}
  card the expense report says paid it: {receipt_payment_mode}

How to judge:
- Convert the receipt amount from {receipt_currency} to {tx_currency} using your best estimate of the exchange rate around {tx_date}. Card networks usually add a small FX fee (roughly 1 to 3 percent), so the statement amount is often slightly higher than the raw converted amount.
- Compare the converted amount to the transaction amount, then weigh vendor-name similarity, reference overlap, and how close the dates are.
- Check the two card labels. They come from different systems and are written differently, so compare the card numbers inside them rather than the whole string. Matching numbers corroborate the pair. Numbers that clearly disagree are strong evidence these are two different purchases, even when the converted amounts land close, because a small amount in one currency often coincides with a small amount in another. Say so in your reasoning when the cards decide it. When either label names no card, treat the card as unknown and judge on the other signals; unknown is not disagreement.
- Weigh the vendors as evidence too. A recurring software subscription, a cloud bill, or another charge that clearly is not a travel purchase does not belong to a restaurant, taxi, or toll receipt however well the amounts convert.
- Be honest about uncertainty. Your exchange-rate estimate is approximate and this judgment always goes to a human for review, so do not overstate confidence.

Return a JSON object with:
- is_match: true if the receipt is plausibly the same purchase, false otherwise
- same_purchase_confidence: your probability from 0.0 to 1.0 that they are the same purchase
- implied_rate: the {receipt_currency}-to-{tx_currency} rate you used as a number, or null
- converted_amount: the receipt amount converted to {tx_currency} as a number, or null
- reasoning: one or two short sentences explaining the judgment
"""


_FX_JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_match": {"type": "boolean"},
        "same_purchase_confidence": {"type": "number"},
        "implied_rate": {"type": ["number", "null"]},
        "converted_amount": {"type": ["number", "null"]},
        "reasoning": {"type": "string"},
    },
    "required": [
        "is_match",
        "same_purchase_confidence",
        "implied_rate",
        "converted_amount",
        "reasoning",
    ],
    "additionalProperties": False,
}


_AMBIGUOUS_PROMPT_TEMPLATE = """A card-statement transaction has several candidate receipts that all match on amount and date, so a deterministic rule cannot tell them apart. Pick the one most likely to be the same purchase, or decline if none is a confident pick.

Transaction (from the card statement):
  amount: {tx_amount} {tx_currency}
  date: {tx_date}
  vendor as printed on the statement: {tx_vendor}

Candidate receipts:
{candidates_block}

How to judge:
- The amounts and dates are already close (that is why they tie). Use vendor-name similarity to the statement vendor, reference-number overlap, and any small date difference to break the tie.
- Only pick a candidate if one is clearly more likely than the others. If they remain genuinely indistinguishable, decline (chosen_index 0) so a human decides.

Return a JSON object with:
- chosen_index: the 1-based number of the best candidate, or 0 if none is a confident pick
- confidence: your probability from 0.0 to 1.0 that the chosen candidate is correct (0 when chosen_index is 0)
- reasoning: one or two short sentences explaining the pick or why you declined
"""


_AMBIGUOUS_SCHEMA = {
    "type": "object",
    "properties": {
        "chosen_index": {"type": "integer"},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["chosen_index", "confidence", "reasoning"],
    "additionalProperties": False,
}


_EXTRACT_INSTRUCTIONS = """You extract structured data from a business expense receipt.

Extract:
- document_type: what this document actually is. One of:
  "receipt" = a purchase receipt, invoice, taxi/card slip, or ticket for ONE purchase.
  "statement" = a bank or credit-card statement page (a table of many transactions, often with running balances or a card summary).
  "report_summary" = an expense-report page that AGGREGATES other expenses (report totals, "Report Summary", reimbursable totals, approval/signature pages) with no single purchase of its own.
  "other" = none of the above (a photo, a blank page, an unrelated document).
  Only a "receipt" becomes an expense; classify honestly. If genuinely unsure, use "receipt".
- date: the purchase/transaction date as YYYY-MM-DD, or null if not visible. Read the year exactly as printed and never shift it toward a year that seems more plausible: a two-digit year NN means 20NN, so 26 is 2026. Field order varies, so decide it from the document rather than assuming: 15.01.2026 is day-first (January 15), while card-terminal slips often print year-first (26-04-22 is 22 April 2026). When a receipt shows the date twice, the full printed date in the fiscal/invoice block ("Data: 2026-04-22") outranks the compressed date on the card slip. Never read a time or a sequence number as part of the date.
- total: the final amount charged, as a plain number string like "24.50", or null. Prefer the grand total including tax/tip over any subtotal.
- currency: the ISO 4217 code (USD, EUR, GBP...), or null if not determinable. Infer from symbols ($, €, £) only when unambiguous.
- vendor: the merchant/issuer name as printed, or null. When the document shows both the merchant and a card-terminal / acquiring bank or payment processor (CREDIT AGRICOLE, SumUp, Cielo, PagSeguro...), the vendor is the MERCHANT being paid, never the bank or processor operating the terminal.
- vendor_clean: the short storefront brand for that merchant, or null. Strip legal-entity suffixes (LTDA, S.A., GmbH, Inc, LLC, Ltd, Co) and distributor/trading tails ("COMERCIO DE X LTDA" -> "X", "X INDUSTRIA E COMERCIO" -> "X"); prefer the storefront/brand a person would recognize. Keep it faithful to `vendor`; do not invent a brand that is not on the receipt.
- reference: an invoice/ticket/booking/order number if one is printed, else null.
- line_items: every purchased line item with description, quantity, unit_price, line_total (all amounts as plain number strings, quantity/unit_price null when not shown). If the receipt shows only a final total with NO itemization (taxi slips, card slips, simple tickets), return an empty array. NEVER invent line items. If a line item is illegible, include it with description "(illegible)" and line_total null.
- tax: the total tax/VAT amount as a plain number string like "3.80", or null if the receipt does not show tax separately. Do NOT compute it; only report a printed tax figure.
- tax_label: the tax name if printed (VAT, GST, Sales Tax, IVA, MwSt...), else null.
- payment_hint: the last 4 digits of the paying card, or the tender type (Visa ...1234, Amex, Mastercard, Cash, PayPal), exactly as printed, or null.
- confidence: your honest 0.0-1.0 confidence that the header fields (date, total, vendor) are read correctly.
- notes: one short sentence on anything unusual (illegible areas, multiple currencies, handwriting), or "".

Source file name (may hint at the vendor or date, but trust the document over the name): {file_name}
"""

_EXTRACT_TEXT_SUFFIX = """
The receipt content below is the text layer extracted from a PDF; layout may be flattened.

--- RECEIPT TEXT START ---
{text}
--- RECEIPT TEXT END ---
"""

_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "enum": ["receipt", "statement", "report_summary", "other"],
        },
        "date": {"type": ["string", "null"]},
        "total": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
        "vendor": {"type": ["string", "null"]},
        "vendor_clean": {"type": ["string", "null"]},
        "reference": {"type": ["string", "null"]},
        "tax": {"type": ["string", "null"]},
        "tax_label": {"type": ["string", "null"]},
        "payment_hint": {"type": ["string", "null"]},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": ["string", "null"]},
                    "unit_price": {"type": ["string", "null"]},
                    "line_total": {"type": ["string", "null"]},
                },
                "required": ["description", "quantity", "unit_price", "line_total"],
                "additionalProperties": False,
            },
        },
        "confidence": {"type": "number"},
        "notes": {"type": "string"},
    },
    "required": [
        "document_type",
        "date", "total", "currency", "vendor", "vendor_clean", "reference",
        "tax", "tax_label", "payment_hint",
        "line_items", "confidence", "notes",
    ],
    "additionalProperties": False,
}


# Extraction-cache fingerprint: any edit to the extraction prompt(s) or
# response schema changes this value, making previously cached readings
# unreachable (they answer a prompt that no longer exists). The file name
# placeholder stays UNformatted here on purpose — the cache key excludes it.
_EXTRACT_FINGERPRINT = prompt_fingerprint(
    _EXTRACT_INSTRUCTIONS + _EXTRACT_TEXT_SUFFIX, _EXTRACT_SCHEMA
)


def _accounts_block(chart_of_accounts: list[str] | None) -> str:
    """Render the in-scope GL account list for the prompt, or '' when no
    chart of accounts was supplied (the model then returns zoho_account
    null). Slice 4.2."""
    if not chart_of_accounts:
        return ""
    listed = "\n".join(f"  - {label}" for label in chart_of_accounts)
    return (
        "\nGL accounts (pick the single best match; copy the label "
        "EXACTLY, or null if none clearly fits):\n"
        f"{listed}\n"
    )


class OpenAIClient:
    """OpenAI-backed implementation. Provider swap = subclass with the
    same method signatures and instantiate that instead.

    The API key comes from the `OPENAI_API_KEY` environment variable
    by default; pass `api_key=` to override (mostly for tests).
    Never accept the key value via a committed config file.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        vision_model: str | None = None,
        api_key: str | None = None,
        cost_tracker: CostTracker | None = None,
        extraction_cache: ExtractionCache | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package not installed; run `uv sync`"
            ) from exc

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OpenAI API key missing — set OPENAI_API_KEY env var or "
                "pass api_key= to OpenAIClient(...)."
            )
        self._client = OpenAI(api_key=key)
        self.model = model
        # Vision OCR may want a stronger model than text categorization;
        # defaults to the text model when not set (BLUEPRINT 2.2).
        self.vision_model = vision_model or model
        self.cost_tracker = cost_tracker or CostTracker()
        # "Same photo, same answer": optional raw-payload store consulted by
        # extract_receipt only. None = every call goes to the API (unchanged).
        self.extraction_cache = extraction_cache

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        if not items:
            return []

        items_block = "\n".join(
            f"  {i+1}. {it.description!r} — total {it.line_total}"
            for i, it in enumerate(items)
        )
        prompt = _LINE_ITEMS_PROMPT_TEMPLATE.format(
            categories_block="\n".join(f"  - {c}" for c in categories),
            accounts_block=_accounts_block(chart_of_accounts),
            items_block=items_block,
            n_items=len(items),
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "line_item_classifications",
                    "schema": _LINE_ITEMS_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)

        payload = json.loads(response.choices[0].message.content or "{}")
        raw_results = payload.get("results", [])

        # Index the results by the LLM's reported index, then re-emit
        # in input order — defends against the model returning a
        # reordered list.
        by_index = {r["index"]: r for r in raw_results}
        out: list[ClassificationResult] = []
        for i, _ in enumerate(items, start=1):
            r = by_index.get(i)
            if r is None:
                out.append(_review_result("LLM did not return a result for this item"))
                continue
            out.append(
                ClassificationResult(
                    category=_opt_label(r.get("category")),
                    zoho_account=_opt_label(r.get("zoho_account")),
                    confidence=float(r.get("confidence", 0.0)),
                    reasoning=str(r.get("reasoning", "")),
                )
            )
        return out

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        prompt = _VENDOR_PROMPT_TEMPLATE.format(
            categories_block="\n".join(f"  - {c}" for c in categories),
            vendor=vendor,
            total=total,
            accounts_block=_accounts_block(chart_of_accounts),
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "vendor_classification",
                    "schema": _VENDOR_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)

        payload = json.loads(response.choices[0].message.content or "{}")
        return ClassificationResult(
            category=_opt_label(payload.get("category")),
            zoho_account=_opt_label(payload.get("zoho_account")),
            confidence=float(payload.get("confidence", 0.0)),
            reasoning=str(payload.get("reasoning", "")),
        )

    def judge_fx_match(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        receipt_amount: Decimal,
        receipt_currency: str,
        receipt_date: str | None,
        receipt_vendor: str | None,
        receipt_reference: str | None,
        tx_card: str | None = None,
        receipt_payment_mode: str | None = None,
    ) -> FxJudgmentResult:
        prompt = _FX_JUDGMENT_PROMPT_TEMPLATE.format(
            tx_amount=tx_amount,
            tx_currency=tx_currency,
            tx_date=tx_date,
            tx_vendor=tx_vendor or "(unknown)",
            receipt_amount=receipt_amount,
            receipt_currency=receipt_currency or "(unknown)",
            receipt_date=receipt_date or "(unknown)",
            receipt_vendor=receipt_vendor or "(unknown)",
            receipt_reference=receipt_reference or "(none)",
            tx_card=tx_card or "(unknown)",
            receipt_payment_mode=receipt_payment_mode or "(unknown)",
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "fx_judgment",
                    "schema": _FX_JUDGMENT_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)
        payload = json.loads(response.choices[0].message.content or "{}")
        return _fx_result_from_payload(payload)

    def judge_ambiguous(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        candidates: list[AmbiguousCandidate],
    ) -> AmbiguousJudgmentResult:
        candidates_block = "\n".join(
            f"  {i}. vendor {c.vendor or '(unknown)'}, "
            f"{c.amount} {c.currency or ''}, date {c.date or '(unknown)'}, "
            f"reference {c.reference or '(none)'}"
            for i, c in enumerate(candidates, start=1)
        )
        prompt = _AMBIGUOUS_PROMPT_TEMPLATE.format(
            tx_amount=tx_amount,
            tx_currency=tx_currency,
            tx_date=tx_date,
            tx_vendor=tx_vendor or "(unknown)",
            candidates_block=candidates_block,
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ambiguous_judgment",
                    "schema": _AMBIGUOUS_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)
        payload = json.loads(response.choices[0].message.content or "{}")
        return _ambiguous_result_from_payload(payload)

    def extract_receipt(
        self,
        *,
        file_name: str,
        images: list[tuple[bytes, str]] | None = None,
        text: str | None = None,
    ) -> ExtractedReceipt:
        if (images is None) == (text is None):
            raise ValueError("extract_receipt needs exactly one of images= or text=")

        model = self.model if text is not None else self.vision_model

        # Same photo, same answer: identical document content (under the same
        # model + prompt fingerprint) is answered from the raw-payload cache
        # instead of the API. The payload is re-parsed live below, so parser
        # fixes apply to cached readings too. A cache hit records no usage —
        # it costs nothing.
        cache = self.extraction_cache
        cache_key: str | None = None
        if cache is not None:
            cache_key = extraction_cache_key(
                fingerprint=_EXTRACT_FINGERPRINT, model=model,
                images=images, text=text,
            )
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("extraction cache hit: %s", file_name)
                return _extraction_from_payload(cached)

        instructions = _EXTRACT_INSTRUCTIONS.format(file_name=file_name)
        if text is not None:
            content: object = instructions + _EXTRACT_TEXT_SUFFIX.format(text=text)
        else:
            import base64

            parts: list[dict] = [{"type": "text", "text": instructions}]
            for raw, mime in images or []:
                b64 = base64.b64encode(raw).decode("ascii")
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                    }
                )
            content = parts

        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "receipt_extraction",
                    "schema": _EXTRACT_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response, model=model)
        raw_payload = response.choices[0].message.content or "{}"
        extraction = _extraction_from_payload(json.loads(raw_payload))
        # Store only after a successful parse: a payload the parser rejects
        # must not be pinned as this document's answer forever.
        if cache is not None and cache_key is not None:
            cache.put(cache_key, raw_payload, model=model, file_name=file_name)
        return extraction

    def _record_usage(self, response, model: str | None = None) -> None:
        try:
            usage = response.usage
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
        except AttributeError:
            input_tokens = 0
            output_tokens = 0
        self.cost_tracker.record(
            TokenUsage.from_counts(model or self.model, input_tokens, output_tokens)
        )


def _review_result(reason: str) -> ClassificationResult:
    return ClassificationResult(
        category=None, zoho_account=None, confidence=0.0, reasoning=reason
    )


def _fx_result_from_payload(payload: dict) -> FxJudgmentResult:
    """Parse a raw FX-judgment JSON payload into a FxJudgmentResult.

    Numeric amounts come back as JSON numbers; `converted_amount` is
    re-cast through `Decimal(str(...))` to avoid IEEE-754 binary noise,
    consistent with the ingest parsers.
    """
    raw_amount = payload.get("converted_amount")
    converted = Decimal(str(raw_amount)) if raw_amount is not None else None
    raw_rate = payload.get("implied_rate")
    return FxJudgmentResult(
        is_match=bool(payload.get("is_match", False)),
        same_purchase_confidence=float(payload.get("same_purchase_confidence", 0.0)),
        implied_rate=float(raw_rate) if raw_rate is not None else None,
        converted_amount=converted,
        reasoning=str(payload.get("reasoning", "")),
    )


def _extraction_from_payload(payload: dict) -> ExtractedReceipt:
    """Parse a raw receipt-extraction JSON payload. Field values stay
    strings (or None); Decimal/date casting is the ingest layer's job."""
    items = []
    for raw in payload.get("line_items") or []:
        if not isinstance(raw, dict):
            continue
        desc = str(raw.get("description") or "").strip()
        if not desc:
            continue
        items.append(
            ExtractedLineItem(
                description=desc,
                line_total=_opt_str(raw.get("line_total")),
                quantity=_opt_str(raw.get("quantity")),
                unit_price=_opt_str(raw.get("unit_price")),
            )
        )
    return ExtractedReceipt(
        date=_opt_str(payload.get("date")),
        total=_opt_str(payload.get("total")),
        currency=_opt_str(payload.get("currency")),
        vendor=_opt_str(payload.get("vendor")),
        reference=_opt_str(payload.get("reference")),
        line_items=tuple(items),
        confidence=float(payload.get("confidence", 0.0) or 0.0),
        notes=str(payload.get("notes", "") or ""),
        tax=_opt_str(payload.get("tax")),
        tax_label=_opt_str(payload.get("tax_label")),
        payment_hint=_opt_str(payload.get("payment_hint")),
        vendor_clean=_opt_str(payload.get("vendor_clean")),
        document_type=_document_type(payload.get("document_type")),
    )


_DOCUMENT_TYPES = frozenset({"receipt", "statement", "report_summary", "other"})


def _document_type(value: object) -> str:
    """The classification, whitelisted. Anything unexpected (absent key,
    junk value, old cached payload) collapses to "receipt": misreading a
    real receipt as excludable loses data; a phantom row is at least
    visible. Exclusion must be earned by an explicit classification."""
    s = str(value or "").strip().lower()
    return s if s in _DOCUMENT_TYPES else "receipt"


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


_LABEL_SENTINELS = frozenset({"null", "none", "n/a", "na", "nil", "-", "(none)"})


def _opt_label(value: object) -> str | None:
    """A category / GL-account label from a raw LLM payload, or None.

    The json-schema allows JSON null, but gpt-4o-mini intermittently
    returns the STRING "null" instead. That string is truthy, so it
    slipped past every no-category guard and reached the export as a
    literal "null" Expense Account (caught live 2026-08-13, PagBank
    receipt). Sentinel spellings of "no value" collapse to real None; the
    downstream `(uncategorized - assign)` path handles it from there."""
    s = _opt_str(value)
    if s is None or s.lower() in _LABEL_SENTINELS:
        return None
    return s


def _ambiguous_result_from_payload(payload: dict) -> AmbiguousJudgmentResult:
    """Parse a raw ambiguous-judgment JSON payload."""
    try:
        chosen = int(payload.get("chosen_index", 0) or 0)
    except (TypeError, ValueError):
        chosen = 0
    return AmbiguousJudgmentResult(
        chosen_index=chosen,
        confidence=float(payload.get("confidence", 0.0)),
        reasoning=str(payload.get("reasoning", "")),
    )


# ── Mock for tests ───────────────────────────────────────────────────


class MockLLMClient:
    """In-memory client for tests. Configurable canned responses.

    Two modes:
    * `responses` — pre-recorded queue; each `classify_*` call pops one.
    * Default — deterministic naive mapping from description/vendor
      via simple substring match (different from production but useful
      to exercise the call shape).
    """

    def __init__(
        self,
        responses: list[list[ClassificationResult] | ClassificationResult] | None = None,
        *,
        fx_responses: list[FxJudgmentResult] | None = None,
        ambiguous_responses: list[AmbiguousJudgmentResult] | None = None,
        extraction_responses: list[ExtractedReceipt] | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self._queue = list(responses or [])
        self._fx_queue = list(fx_responses or [])
        self._ambiguous_queue = list(ambiguous_responses or [])
        self._extraction_queue = list(extraction_responses or [])
        self.calls: list[tuple[str, object]] = []
        # Last chart-of-accounts labels seen by a classify_* call, so tests
        # can assert the categorizer forwarded the in-scope account list.
        self.last_chart_of_accounts: list[str] | None = None
        # Last (tx_card, receipt_payment_mode) pair seen by judge_fx_match
        # (WS3), so tests can assert the card evidence reached the model.
        self.last_fx_cards: tuple[str | None, str | None] | None = None
        self.cost_tracker = cost_tracker or CostTracker()
        # Record a fixed nominal cost per call so tests can verify
        # cost-tracking behavior without coupling to provider pricing.
        self._per_call_cost = TokenUsage(
            model="mock", input_tokens=100, output_tokens=50, cost_usd=Decimal("0.001")
        )

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        self.calls.append(("classify_line_items", items))
        self.last_chart_of_accounts = chart_of_accounts
        self.cost_tracker.record(self._per_call_cost)

        if self._queue:
            queued = self._queue.pop(0)
            if isinstance(queued, list):
                return queued
            return [queued]
        return [_default_for_description(it.description, categories) for it in items]

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        self.calls.append(("classify_by_vendor", (vendor, total)))
        self.last_chart_of_accounts = chart_of_accounts
        self.cost_tracker.record(self._per_call_cost)

        if self._queue:
            queued = self._queue.pop(0)
            if isinstance(queued, list):
                return queued[0] if queued else _review_result("empty queue entry")
            return queued
        return _default_for_vendor(vendor, categories)

    def judge_fx_match(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        receipt_amount: Decimal,
        receipt_currency: str,
        receipt_date: str | None,
        receipt_vendor: str | None,
        receipt_reference: str | None,
        tx_card: str | None = None,
        receipt_payment_mode: str | None = None,
    ) -> FxJudgmentResult:
        self.calls.append(("judge_fx_match", (tx_vendor, receipt_vendor)))
        # WS3: the card pair is recorded on the side rather than in `calls`,
        # so the existing (vendor, vendor) call assertions stay valid while
        # a test can still assert the cards reached the model.
        self.last_fx_cards = (tx_card, receipt_payment_mode)
        self.cost_tracker.record(self._per_call_cost)

        if self._fx_queue:
            return self._fx_queue.pop(0)
        return _default_fx_judgment(
            tx_amount, tx_vendor, receipt_amount, receipt_vendor
        )

    def judge_ambiguous(
        self,
        *,
        tx_amount: Decimal,
        tx_currency: str,
        tx_date: str,
        tx_vendor: str,
        candidates: list[AmbiguousCandidate],
    ) -> AmbiguousJudgmentResult:
        self.calls.append(("judge_ambiguous", (tx_vendor, [c.document_id for c in candidates])))
        self.cost_tracker.record(self._per_call_cost)

        if self._ambiguous_queue:
            return self._ambiguous_queue.pop(0)
        return _default_ambiguous_judgment(tx_vendor, candidates)

    def extract_receipt(
        self,
        *,
        file_name: str,
        images: list[tuple[bytes, str]] | None = None,
        text: str | None = None,
    ) -> ExtractedReceipt:
        if (images is None) == (text is None):
            raise ValueError("extract_receipt needs exactly one of images= or text=")
        self.calls.append(
            ("extract_receipt", (file_name, "vision" if images is not None else "text"))
        )
        self.cost_tracker.record(self._per_call_cost)

        if self._extraction_queue:
            return self._extraction_queue.pop(0)
        return ExtractedReceipt(
            date=None, total=None, currency=None, vendor=None,
            reference=None, line_items=(), confidence=0.0,
            notes="mock: no extraction queued",
        )


def _default_for_description(
    description: str, categories: list[str]
) -> ClassificationResult:
    """Deterministic mock heuristic — not for production. Used only
    when no `responses` queue is supplied to MockLLMClient.
    """
    d = description.lower()
    if "coffee" in d or "latte" in d or "lunch" in d or "food" in d:
        cat = "Meals & Entertainment"
    elif "chair" in d or "cable" in d or "monitor" in d or "laptop" in d:
        cat = "Equipment & Hardware"
    elif "uber" in d or "taxi" in d or "flight" in d:
        cat = "Travel & Transport"
    else:
        return _review_result("mock: no description match")
    if cat not in categories:
        return _review_result(f"mock: '{cat}' not in supplied categories")
    return ClassificationResult(
        category=cat, zoho_account=None, confidence=0.9,
        reasoning=f"mock: matched on '{description}'",
    )


def _default_for_vendor(
    vendor: str, categories: list[str]
) -> ClassificationResult:
    v = vendor.lower()
    if "uber" in v or "lyft" in v:
        cat = "Travel & Transport"
    elif "starbucks" in v or "cafe" in v:
        cat = "Meals & Entertainment"
    else:
        return _review_result("mock: vendor not in defaults")
    if cat not in categories:
        return _review_result(f"mock: '{cat}' not in supplied categories")
    return ClassificationResult(
        category=cat, zoho_account=None, confidence=0.75,
        reasoning=f"mock: vendor '{vendor}' matched on keyword",
    )


def _default_fx_judgment(
    tx_amount: Decimal,
    tx_vendor: str,
    receipt_amount: Decimal,
    receipt_vendor: str | None,
) -> FxJudgmentResult:
    """Deterministic mock FX verdict — not production. Vendor-name
    overlap drives the verdict; the implied rate is the naive
    tx_amount / receipt_amount ratio. Used only when no `fx_responses`
    queue is supplied to MockLLMClient.
    """
    tv = (tx_vendor or "").lower()
    rv = (receipt_vendor or "").lower()
    overlap = bool(rv) and (rv in tv or tv in rv)
    rate = (
        float(tx_amount) / float(receipt_amount)
        if receipt_amount and receipt_amount != 0
        else None
    )
    if overlap:
        return FxJudgmentResult(
            is_match=True,
            same_purchase_confidence=0.8,
            implied_rate=rate,
            converted_amount=tx_amount,
            reasoning=f"mock: vendor overlap '{tx_vendor}' / '{receipt_vendor}'",
        )
    return FxJudgmentResult(
        is_match=False,
        same_purchase_confidence=0.3,
        implied_rate=rate,
        converted_amount=None,
        reasoning="mock: no vendor overlap",
    )


def _default_ambiguous_judgment(
    tx_vendor: str,
    candidates: list[AmbiguousCandidate],
) -> AmbiguousJudgmentResult:
    """Deterministic mock — picks the first candidate whose vendor
    overlaps the statement vendor; declines (index 0) otherwise."""
    tv = (tx_vendor or "").lower()
    for i, c in enumerate(candidates, start=1):
        cv = (c.vendor or "").lower()
        if cv and (cv in tv or tv in cv):
            return AmbiguousJudgmentResult(
                chosen_index=i,
                confidence=0.75,
                reasoning=f"mock: vendor overlap '{tx_vendor}' / '{c.vendor}'",
            )
    return AmbiguousJudgmentResult(
        chosen_index=0, confidence=0.0, reasoning="mock: no clear vendor match"
    )
