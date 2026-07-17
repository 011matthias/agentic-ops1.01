"""Zoho Expense report PDF ingest -- receipts source "expense_report_pdf"
(2026-07-16).

Chris's real receipt-side artifact is often the consolidated Zoho
Expense report PDF (ER-NNNNN) rather than a CSV export: a normalized
EXPENSE SUMMARY table (one row per submitted expense -- date,
description, merchant, payment mode, amount) followed by a REPORT
SUMMARY BY CURRENCY total and pages of the receipt images / forwarded
email confirmations the report was built from. This adapter reads only
the EXPENSE SUMMARY table (deterministic, text-layer, pypdf) into the
same `Receipt` objects the matcher already consumes; the receipt-image
pages are not OCR'd here (see routing note below).

Verified against 5 real Brisken ER PDFs fetched via Graph 2026-07-16
(rule_brisken_graph_first): ER-00002 (EUR per-diem + Bahn), ER00009 /
ER-D-0016 (EUR per-diem + Airbnb), ER-00101 (USD+EUR multi-currency
travel, 12 rows), ER-00139 (USD single-line flight); and against the
6 by-month labeling bundles 2026-07-17 (ER-00181 DKK+EUR, ER-00183,
ER-00194, ER-00214/00215 BRL, ER-00216), all six to the cent against
the printed per-currency totals. Row shapes observed and covered:

* Row start: "<n>. MM/DD/YYYY" (numbered), "MM/DD/YY [1] [2]"
  (per-diem, trailing policy-violation footnotes), or a bare
  "MM/DD/YY" (continuation row after a page break, no number). A
  NUMBERED row may carry the merchant and amounts inline on the same
  line ("3. 05/17/2026 FLiX $155.61 $155.61") when they fit; a bare
  date with trailing text is NOT a row start (it is row content).
* Metadata lines: "Ref# :", "Payment Mode :", "Paid Through :",
  "Location :" / "Expense Location :" (normalized to Location),
  "Attendees :", "Customer :", "Project :", "Per diem Name :",
  "Day(s) :", "Tax Name :" -- label-prefixed, any subset, any order.
* The merchant name may wrap across up to 2 lines before the amount,
  or share a line with the amount ("Uber $60.85 $60.85"); per-diem
  rows carry no merchant at all.
* Amounts print either symbol-prefixed ("$60.85", "€2,80") or
  ISO-code-prefixed with no symbol ("BRL3,099.99", "DKK35.00").
  Number format varies BY TOKEN, not by currency: EUR uses EU format
  (comma decimal), BRL/DKK print US format (comma thousands, dot
  decimal) -- so the format is sniffed per token from its separators,
  never assumed from the currency.
* Multi-currency reports print the original-currency amount on the
  merchant line ("DB €2,80"), then a "1 EUR = <rate> USD" FX line,
  then the USD-converted amount alone on its own line. Single-currency
  reports print one amount only (both columns collapse to the same
  value: "Uber $60.85 $60.85").
* "Non Reimbursable" / " Includes Tax €X.XX" are per-row markers,
  not part of the amount.

`detected_total` / `detected_currency` carry the ORIGINAL-currency
amount, matching the by-month OCR ground-truth convention (e.g.
ER-00194's EUR line items); `base_amount` / `exchange_rate` carry the
report's own USD conversion when present (the Zoho-report-fields
extension on `Receipt`, 2026-06-16).

Every parsed row's original-currency amount is summed by currency and
cross-checked against the report's own printed "Total Expense Amount"
line in REPORT SUMMARY BY CURRENCY (to the cent); a mismatch lands as
a `ParseIssue`, never a silent drop.

Routing note: NEVER route a report PDF through `receipts_folder.py` --
its `MAX_PDF_PAGES` cap (4) and vision-OCR path exist for a folder of
individual receipt files, not a multi-page consolidated report; a
report PDF would either be truncated or burn a vision call on a table
that is already machine-readable text. A PDF with no extractable
EXPENSE SUMMARY text layer (scanned, or genuinely not a Zoho report)
raises a clean `StatementParseError` -- no rasterize-and-guess
fallback.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..matching.types import Receipt
from ._common import ParseIssue, StatementParseError, parse_date

__all__ = [
    "parse_expense_report_pdf",
    "parse_expense_report_pdf_tolerant",
    "parse_expense_report_text",
]


_SYMBOL_CCY: dict[str, str] = {"$": "USD", "€": "EUR", "£": "GBP"}

# ISO codes that may prefix an amount with no symbol ("BRL3,099.99").
# A closed whitelist, not [A-Z]{3}: an open pattern would money-match
# uppercase merchant fragments that happen to end in 3 letters + digit.
_ISO_CODES = (
    "USD|EUR|GBP|BRL|DKK|SEK|NOK|CHF|CAD|AUD|NZD|JPY|CNY|INR|PLN|CZK|"
    "HUF|RON|BGN|ILS|AED|SGD|HKD|MXN|ZAR|TRY|THB|MYR|IDR|PHP|KRW|TWD"
)

_ROW_START = re.compile(
    r"^(?:(\d+)\.\s+)?(\d{1,2}/\d{1,2}/\d{2,4})\s*((?:\[\d+\]\s*)*)(.*)$"
)
_META = re.compile(
    r"^(Ref#|Payment Mode|Paid Through|Expense Location|Location|Attendees|"
    r"Customer|Project|Per diem Name|Day\(s\)|Tax Name)\s*:\s*(.*)$"
)
_FX_RATE = re.compile(r"^1\s+([A-Z]{3})\s*=\s*([\d.]+)\s+([A-Z]{3})$")
_NON_REIMB = re.compile(r"^Non Reimbursable$")
_INCLUDES_TAX = re.compile(
    rf"^Includes Tax\s+(?:[€$£]|{_ISO_CODES})\s?[\d.,]+$"
)
_SUB_TOTAL = re.compile(r"^Sub Total\b")
_TABLE_HEADER = re.compile(r"^(?:S\.No\s+)?Expense Details\s+Merchant\s+Amount")
_SECTION_END = re.compile(r"^REPORT SUMMARY BY CURRENCY$")
_PAGE_NUMBER = re.compile(r"^\d{1,3}$")
_MONEY = re.compile(
    rf"(?:([€$£])|(?<![A-Z])({_ISO_CODES}))\s?(\d[\d.,]*)"
)
_TOTAL_CCY_LINE = re.compile(r"^TOTAL\s+([A-Z]{3}(?:\s+[A-Z]{3})*)$")
_TOTAL_AMOUNT_LINE = re.compile(r"^Total Expense Amount\s+(.+)$")


def parse_expense_report_pdf(
    path: str | Path,
    *,
    legal_entity_id: str,
    default_currency: str | None = None,
) -> list[Receipt]:
    """Strict mode: raise on the first parse issue. Backward-compatible
    wrapper around the tolerant variant; production uses the tolerant
    form and surfaces issues on the Errors sheet."""
    receipts, issues = parse_expense_report_pdf_tolerant(
        path, legal_entity_id=legal_entity_id, default_currency=default_currency
    )
    if issues:
        raise issues[0].to_error()
    return receipts


def parse_expense_report_pdf_tolerant(
    path: str | Path,
    *,
    legal_entity_id: str,
    default_currency: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    path = Path(path)
    return parse_expense_report_text(
        _extract_text(path),
        file_name=path.name,
        legal_entity_id=legal_entity_id,
        default_currency=default_currency,
    )


def parse_expense_report_text(
    text: str,
    *,
    file_name: str,
    legal_entity_id: str,
    default_currency: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """The text-layer parsing core, separated from PDF extraction so tests
    can feed synthetic report text directly (real ER PDFs are client
    financial data and are never committed as fixtures)."""
    lines = [ln.strip() for ln in text.splitlines()]

    report_number = _extract_report_number(lines)
    if report_number is None:
        raise StatementParseError(
            f"{file_name}: no 'Expense Report' / report number found; is this "
            "a Zoho Expense report PDF?"
        )

    try:
        start = next(i for i, ln in enumerate(lines) if ln == "EXPENSE SUMMARY")
    except StopIteration as exc:
        raise StatementParseError(
            f"{file_name}: no EXPENSE SUMMARY table found; is this a Zoho "
            "Expense report PDF with a text layer (not a scanned image)?"
        ) from exc
    try:
        end = next(
            i for i, ln in enumerate(lines) if i > start and _SECTION_END.match(ln)
        )
    except StopIteration as exc:
        raise StatementParseError(
            f"{file_name}: EXPENSE SUMMARY found but no REPORT SUMMARY BY "
            "CURRENCY; report PDF may be truncated"
        ) from exc

    row_specs = _split_rows(lines[start + 1 : end])

    receipts: list[Receipt] = []
    issues: list[ParseIssue] = []
    seen_ids: set[str] = set()
    totals_by_ccy: dict[str, Decimal] = {}

    for idx, (category, row) in enumerate(row_specs, start=1):
        try:
            detected_date = _parse_row_date(row["date_raw"])
            classified = _classify_row(row["lines"])
            resolved = _resolve_amounts(classified)
            amount = resolved["original_amount"]
            if amount is None:
                raise ValueError("no amount found for this expense row")
            currency = resolved["original_currency"] or default_currency
        except ValueError as exc:
            issues.append(ParseIssue(file_name, idx, f"{report_number} row {idx}: {exc}"))
            continue

        document_id = f"{report_number}#{idx:03d}"
        if document_id in seen_ids:
            issues.append(ParseIssue(file_name, idx, f"duplicate document_id {document_id!r}"))
            continue
        seen_ids.add(document_id)

        if currency:
            totals_by_ccy[currency] = totals_by_ccy.get(currency, Decimal("0")) + amount

        receipts.append(
            Receipt(
                document_id=document_id,
                legal_entity_id=legal_entity_id,
                detected_date=detected_date,
                detected_total=amount,
                detected_currency=currency,
                detected_vendor=resolved["merchant"],
                detected_reference=classified["meta"].get("Ref#"),
                report_number=report_number,
                payment_mode=classified["meta"].get("Payment Mode"),
                paid_through=classified["meta"].get("Paid Through"),
                zoho_category=category,
                exchange_rate=resolved["exchange_rate"],
                base_amount=resolved["base_amount"],
                reimbursable=not classified["non_reimbursable"],
                expense_location=classified["meta"].get("Location"),
            )
        )

    _validate_currency_totals(lines[end:], totals_by_ccy, file_name, issues)

    # Unconditional (not "and not issues"): a totals-validation warning
    # doesn't explain a zero-row result, so it must not suppress this.
    if not receipts:
        issues.append(ParseIssue(file_name, 0, f"No expense rows found in {report_number}"))

    return receipts, issues


def _extract_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency declared
        raise StatementParseError("pypdf is required to read report PDFs") from exc
    if not path.exists():
        raise StatementParseError(f"expense report PDF not found: {path}")
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_report_number(lines: list[str]) -> str | None:
    for i, ln in enumerate(lines):
        if ln == "Expense Report":
            for j in range(i + 1, min(i + 3, len(lines))):
                candidate = lines[j].strip()
                if candidate:
                    return candidate
            break
    return None


def _split_rows(body: list[str]) -> list[tuple[str | None, dict]]:
    """Split the EXPENSE SUMMARY body into (category, row) pairs. Handles
    page-break noise: bare page-number lines and repeated table-header
    rows are dropped; a category header is recognized by lookahead (the
    line immediately preceding a table-header row)."""
    rows: list[tuple[str | None, dict]] = []
    current_category: str | None = None
    current: dict | None = None
    n = len(body)
    i = 0
    while i < n:
        line = body[i]
        if not line:
            i += 1
            continue
        if _PAGE_NUMBER.match(line):
            i += 1
            continue
        if _TABLE_HEADER.match(line):
            i += 1
            continue
        row_m = _ROW_START.match(line)
        # A bare (unnumbered) date with trailing text is row CONTENT --
        # only the numbered form may carry the merchant/amounts inline.
        if row_m and (row_m.group(1) or not row_m.group(4).strip()):
            if current is not None:
                rows.append((current_category, current))
            current = {"date_raw": row_m.group(2), "lines": []}
            rest = row_m.group(4).strip()
            if rest:
                current["lines"].append(rest)
            i += 1
            continue
        if _SUB_TOTAL.match(line):
            if current is not None:
                rows.append((current_category, current))
                current = None
            i += 1
            continue
        # A category header is only recognized BETWEEN rows (current is
        # None). Mid-row, a page break can land a table-header line
        # right after the row's last content line with no blank/page-
        # number line between them (no leading page-number on some
        # pages) -- that content line belongs to the open row, not a
        # new category.
        if current is None and i + 1 < n and _TABLE_HEADER.match(body[i + 1]):
            current_category = line
            i += 1
            continue
        if current is not None:
            current["lines"].append(line)
        i += 1
    if current is not None:
        rows.append((current_category, current))
    return rows


def _classify_row(lines: list[str]) -> dict:
    desc_parts: list[str] = []
    merchant_parts: list[str] = []
    meta: dict[str, str] = {}
    amount_entries: list[tuple[str, list[tuple[str, str]]]] = []
    fx: tuple[str, Decimal, str] | None = None
    non_reimbursable = False
    seen_meta_or_amount = False

    for line in lines:
        if _NON_REIMB.match(line):
            non_reimbursable = True
            continue
        if _INCLUDES_TAX.match(line):
            continue
        m = _META.match(line)
        if m:
            key = m.group(1)
            if key == "Expense Location":
                key = "Location"
            meta[key] = m.group(2).strip()
            seen_meta_or_amount = True
            continue
        m = _FX_RATE.match(line)
        if m:
            fx = (m.group(1), Decimal(m.group(2)), m.group(3))
            seen_meta_or_amount = True
            continue
        monies = [
            (_SYMBOL_CCY.get(sym, sym) if sym else code, raw)
            for sym, code, raw in _MONEY.findall(line)
        ]
        if monies:
            prefix = _MONEY.sub("", line).strip()
            amount_entries.append((prefix, monies))
            seen_meta_or_amount = True
            continue
        if seen_meta_or_amount:
            merchant_parts.append(line)
        else:
            desc_parts.append(line)

    return {
        "description": " ".join(desc_parts).strip(),
        "merchant_frags": merchant_parts,
        "meta": meta,
        "amount_entries": amount_entries,
        "fx": fx,
        "non_reimbursable": non_reimbursable,
    }


def _resolve_amounts(classified: dict) -> dict:
    amount_entries = classified["amount_entries"]
    fx = classified["fx"]
    merchant_parts = list(classified["merchant_frags"])

    if not amount_entries:
        return {
            "merchant": " ".join(merchant_parts).strip() or None,
            "original_currency": None,
            "original_amount": None,
            "base_amount": None,
            "exchange_rate": fx[1] if fx else None,
        }

    first_prefix, first_monies = amount_entries[0]
    if first_prefix:
        merchant_parts.append(first_prefix)
    merchant = " ".join(merchant_parts).strip() or None

    ccy1, raw1 = first_monies[0]
    original_amount = _parse_amount(raw1)
    original_currency = ccy1
    base_amount = None
    exchange_rate = fx[1] if fx else None

    if len(first_monies) >= 2:
        # Dual-column same-currency line: "Uber $60.85 $60.85"
        base_amount = _parse_amount(first_monies[1][1])
    elif len(amount_entries) >= 2:
        # A separate USD line after an FX-rate line ("DB €2,80" / rate / "$3.01")
        _prefix2, monies2 = amount_entries[1]
        if monies2:
            base_amount = _parse_amount(monies2[0][1])

    return {
        "merchant": merchant,
        "original_currency": original_currency,
        "original_amount": original_amount,
        "base_amount": base_amount,
        "exchange_rate": exchange_rate,
    }


def _parse_amount(raw: str) -> Decimal:
    """Parse a money token sniffing the number format from its own
    separators. The format is per-token, not per-currency: the same
    report prints EUR EU-style ("2,80", "1.950,00") and BRL/DKK
    US-style ("3,099.99", "35.00"), so a currency->format map would
    mis-read one or the other."""
    raw = raw.strip()
    if "," in raw and "." in raw:
        # Both separators: the rightmost one is the decimal mark.
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        # "1,950" (groups of 3) is thousands; "18,50" is a decimal comma.
        if re.fullmatch(r"\d{1,3}(,\d{3})+", raw):
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
    elif "." in raw:
        # "1.950" (groups of 3) is EU thousands; money never has
        # 3-digit fractions. "60.85" stays a decimal point.
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
            raw = raw.replace(".", "")
    return Decimal(raw)


def _parse_row_date(raw: str) -> date:
    try:
        return parse_date(raw)
    except ValueError:
        pass
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2})$", raw)
    if not m:
        raise ValueError(f"Unrecognized date format: {raw!r}")
    mo, da, yy = (int(x) for x in m.groups())
    year = 2000 + yy if yy < 70 else 1900 + yy
    return date(year, mo, da)


def _validate_currency_totals(
    summary_lines: list[str],
    totals_by_ccy: dict[str, Decimal],
    file_name: str,
    issues: list[ParseIssue],
) -> None:
    """Cross-check the parsed rows' per-currency sum against the report's
    own printed 'Total Expense Amount' line, to the cent. A row-level
    parse issue already explains a missing row; this catches the case
    where every row parsed but the sum still drifts (a row silently
    mis-attributed to the wrong currency, a merchant/amount split bug)."""
    ccy_line: list[str] | None = None
    amount_line: list[str] | None = None
    for raw in summary_lines:
        line = raw.strip()
        m = _TOTAL_CCY_LINE.match(line)
        if m:
            ccy_line = m.group(1).split()
            continue
        m = _TOTAL_AMOUNT_LINE.match(line)
        if m and ccy_line is not None:
            amount_line = m.group(1).split()
            break

    if ccy_line is None or amount_line is None:
        issues.append(
            ParseIssue(
                file_name, 0,
                "REPORT SUMMARY BY CURRENCY totals not found; skipped the "
                "printed-total cross-check",
                severity="warning",
            )
        )
        return
    if len(ccy_line) != len(amount_line):
        issues.append(
            ParseIssue(
                file_name, 0,
                "REPORT SUMMARY BY CURRENCY currency/amount count mismatch; "
                "skipped the printed-total cross-check",
                severity="warning",
            )
        )
        return

    for ccy, raw in zip(ccy_line, amount_line):
        try:
            printed = _parse_amount(raw)
        except InvalidOperation:
            issues.append(
                ParseIssue(file_name, 0, f"could not parse printed total for {ccy}: {raw!r}",
                           severity="warning")
            )
            continue
        parsed = totals_by_ccy.get(ccy, Decimal("0"))
        if parsed != printed:
            issues.append(
                ParseIssue(
                    file_name, 0,
                    f"parsed {ccy} total {parsed} does not match the report's "
                    f"printed Total Expense Amount {printed}",
                )
            )
