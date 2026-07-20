"""Chase credit-card statement PDF parser (2026-06-16).

The bank side of the workflow: the monthly Chase statement enters as the
original PDF and is parsed (text layer, via pypdf) into `Transaction`
objects ready for matching. Verified against real 2838 statements.

Statement structure:

* **ACCOUNT ACTIVITY** lists one charge per line:

      MM/DD   <merchant + location>   <USD amount>

  Amounts are USD (the card settles USD), comma-grouped, optional `-` for
  payments / credits.

* A **foreign purchase** prints a two-line FX detail under its charge:

      MM/DD   <CURRENCY NAME>
      <original amount> X <rate> (EXCHG RATE)

  giving the original currency, the original amount, and the rate the bank
  applied. The detail can split across a page break (the rate line lands at
  the top of the next page, after page-header noise), so pages are
  concatenated and a small state machine carries the currency forward until
  its rate line appears.

* Charges are grouped **per card**; each group ends with a marker:

      TRANSACTIONS THIS CYCLE (CARD  2838) $...

  The card number in the marker is the `account_id` for the charges above
  it. One statement spans several cards (2838 / 3645 / 0340).

* The **statement period** (`Opening/Closing Date MM/DD/YY - MM/DD/YY`) on
  page 1 resolves the MM/DD charge dates to a full year, including the
  Dec -> Jan boundary.

Reconciliation-guarantee posture (v2 spec §25.5): every parseable charge
line becomes a Transaction (payments, credits, interest included); nothing
is silently dropped. A line that looks like a charge but fails to parse, an
unmapped FX currency name, or charges with no trailing card marker land in
the tolerant issues list. The original bank line is preserved in `raw_text`
(Dirk 2026-06-16: "all data from the bank statement must stay as it was").
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..matching.types import Transaction
from ._common import ParseIssue, StatementParseError, parse_amount

__all__ = [
    "parse_statement_pdf",
    "parse_statement_pdf_tolerant",
    "parse_statement_text",
]


# Foreign-currency NAME (as the statement prints it) -> ISO code, so a
# foreign receipt (whose currency is an ISO code) matches. Extend as new
# currencies appear; an unmapped name is kept verbatim and flagged.
_CCY_NAMES: dict[str, str] = {
    "EURO": "EUR",
    "BRAZILIAN REAL": "BRL",
    "DANISH KRONE": "DKK",
    "BRITISH POUND": "GBP",
    "POUND STERLING": "GBP",
    "CANADIAN DOLLAR": "CAD",
    "SWISS FRANC": "CHF",
    "MEXICAN PESO": "MXN",
    "JAPANESE YEN": "JPY",
    "AUSTRALIAN DOLLAR": "AUD",
}

# A charge line: date, description, trailing USD amount (2 decimals).
_TX = re.compile(r"^(\d{2})/(\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})$")
# FX detail line B: "<original amount> X <rate> (EXCHG RATE)".
_FX_RATE = re.compile(r"^([\d,]+\.\d+)\s+X\s+([\d.]+)\s+\(EXCHG\s*RATE\)")
# FX detail line A: a date + an all-caps currency name, no amount.
_FX_CCY = re.compile(r"^(\d{2})/(\d{2})\s+([A-Z][A-Z ]+?)\s*$")
# Per-card cycle-total marker; the card number is the account_id.
_CARD = re.compile(r"TRANSACTIONS THIS CYCLE\s*\(CARD\s+(\w+)\)")
# Statement period for year resolution.
_PERIOD = re.compile(
    r"Opening/Closing Date\s+(\d{2})/(\d{2})/(\d{2})\s*-\s*(\d{2})/(\d{2})/(\d{2})"
)


def parse_statement_pdf(
    path: str | Path,
    *,
    legal_entity_id: str,
    account_card_currency: str = "USD",
) -> list[Transaction]:
    """Strict mode: raise on the first parse issue. Backward-compatible
    wrapper around the tolerant variant; production uses the tolerant form
    and surfaces issues on the Errors sheet."""
    txs, issues = parse_statement_pdf_tolerant(
        path,
        legal_entity_id=legal_entity_id,
        account_card_currency=account_card_currency,
    )
    if issues:
        raise issues[0].to_error()
    return txs


def parse_statement_pdf_tolerant(
    path: str | Path,
    *,
    legal_entity_id: str,
    account_card_currency: str = "USD",
) -> tuple[list[Transaction], list[ParseIssue]]:
    """Parse a Chase statement PDF into transactions, collecting issues.

    `account_id` is taken from the per-card markers, not the caller (one
    statement spans several cards). `legal_entity_id` is the caller's
    (one company per statement)."""
    path = Path(path)
    return parse_statement_text(
        _extract_text(path),
        file_name=path.name,
        legal_entity_id=legal_entity_id,
        account_card_currency=account_card_currency,
    )


def parse_statement_text(
    text: str,
    *,
    file_name: str,
    legal_entity_id: str,
    account_card_currency: str = "USD",
) -> tuple[list[Transaction], list[ParseIssue]]:
    """The text-layer parsing core, separated from PDF extraction so tests
    can feed synthetic statement text directly (real Chase statements are
    client financial data and are never committed as fixtures)."""
    lines = text.splitlines()

    period = _parse_period(text)

    transactions: list[Transaction] = []
    issues: list[ParseIssue] = []
    pending: list[dict] = []          # charges awaiting their card marker
    pending_fx_ccy: str | None = None
    seq = 0

    def flush(card: str) -> None:
        nonlocal seq
        for p in pending:
            seq += 1
            transactions.append(
                _build_tx(p, card, seq, legal_entity_id, account_card_currency)
            )
        pending.clear()

    for i, raw in enumerate(lines):
        ln = raw.strip()
        if not ln:
            continue

        rate_m = _FX_RATE.match(ln)
        if rate_m:
            _attach_fx(pending, pending_fx_ccy, rate_m, file_name, i + 1, issues)
            pending_fx_ccy = None
            continue

        card_m = _CARD.search(ln)
        if card_m:
            flush(card_m.group(1))
            pending_fx_ccy = None
            continue

        tx_m = _TX.match(ln)
        if tx_m:
            mo, da, desc, amt = tx_m.groups()
            try:
                amount = parse_amount(amt)
                year = _resolve_year(int(mo), period)
                txdate = date(year, int(mo), int(da))
            except (ValueError, InvalidOperation) as exc:
                issues.append(ParseIssue(file_name, i + 1, f"{exc}: {ln!r}"))
                pending_fx_ccy = None
                continue
            pending.append(
                {"date": txdate, "vendor": desc.strip(), "amount": amount, "raw": ln}
            )
            pending_fx_ccy = None
            continue

        ccy_m = _FX_CCY.match(ln)
        if ccy_m:
            name = ccy_m.group(3).strip()
            pending_fx_ccy = _CCY_NAMES.get(name, name)
            if name not in _CCY_NAMES:
                issues.append(
                    ParseIssue(file_name, i + 1, f"unmapped FX currency name {name!r}")
                )
            continue
        # Any other line is noise (headers, totals, itineraries). Do NOT
        # clear pending_fx_ccy here: a page break inserts header lines
        # between the currency line and its rate line.

    if pending:
        n = len(pending)
        flush("UNKNOWN")
        issues.append(
            ParseIssue(
                file_name,
                len(lines),
                f"{n} charge(s) had no trailing card marker; account set to 'UNKNOWN'",
            )
        )

    if not transactions and not issues:
        issues.append(
            ParseIssue(file_name, 0, "No charges found; is this a Chase statement PDF?")
        )

    return transactions, issues


def _extract_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency declared
        raise StatementParseError(
            "pypdf is required to read PDF statements"
        ) from exc
    if not path.exists():
        raise StatementParseError(f"statement PDF not found: {path}")
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _parse_period(text: str) -> tuple[int, int, int, int] | None:
    """(open_month, open_year, close_month, close_year) with 4-digit years,
    or None when the Opening/Closing Date line is absent."""
    m = _PERIOD.search(text)
    if not m:
        return None
    m1, _d1, y1, m2, _d2, y2 = (int(g) for g in m.groups())
    return (m1, 2000 + y1, m2, 2000 + y2)


def _resolve_year(month: int, period: tuple[int, int, int, int] | None) -> int:
    """Resolve a MM/DD charge to a full year using the statement period.
    Across a Dec->Jan boundary, a month at/after the opening month belongs
    to the opening year, otherwise the closing year."""
    if period is None:
        raise ValueError("statement period (Opening/Closing Date) not found")
    open_month, open_year, _close_month, close_year = period
    if open_year == close_year:
        return open_year
    return open_year if month >= open_month else close_year


def _attach_fx(
    pending: list[dict],
    currency: str | None,
    rate_m: "re.Match[str]",
    file_name: str,
    line_no: int,
    issues: list[ParseIssue],
) -> None:
    """Attach a parsed FX detail to the most recent pending charge."""
    if not pending:
        issues.append(
            ParseIssue(file_name, line_no, "FX rate line with no preceding charge")
        )
        return
    try:
        original = parse_amount(rate_m.group(1))
        rate = Decimal(rate_m.group(2))
    except (ValueError, InvalidOperation) as exc:
        issues.append(ParseIssue(file_name, line_no, f"bad FX rate line: {exc}"))
        return
    pending[-1]["original_amount"] = original
    pending[-1]["fx_rate"] = rate
    pending[-1]["original_currency"] = currency
    if currency is None:
        issues.append(
            ParseIssue(
                file_name, line_no, "FX rate line without a preceding currency name"
            )
        )


def _build_tx(
    p: dict, card: str, seq: int, legal_entity_id: str, ccy: str
) -> Transaction:
    return Transaction(
        transaction_id=f"{card}:{seq}",
        legal_entity_id=legal_entity_id,
        account_id=card,
        transaction_date=p["date"],
        posting_date=None,
        amount=p["amount"],
        transaction_currency=ccy.upper(),       # USD: the card posts USD
        account_card_currency=ccy.upper(),
        vendor_from_statement=p["vendor"],
        raw_text=p["raw"],
        original_amount=p.get("original_amount"),
        original_currency=p.get("original_currency"),
        fx_rate=p.get("fx_rate"),
        # The statement PDF already prints the canonical convention
        # (purchases positive, payments/credits negative), so a negative
        # amount IS a credit (3.15 / LD-5 A5).
        is_credit=p["amount"] < 0,
    )
