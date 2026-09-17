"""One currency for a month's receipts (backlog item 98).

July's expense report closes with three totals (USD, EUR, BRL) and nothing
that says what the month cost in one currency, while the `Exchange Rate`
column the export already carries is empty on every row because a scanned
receipt prints no rate. The owner confirmed on 2026-09-08 that US filing
applies, so the deductible figure is the USD one, and an accountant has been
converting by hand.

This module is the conversion, and nothing else: no store, no config object,
no document. It takes amounts and a way to look a rate up, and hands back a
figure per listing row plus the total over them.

One rule, two documents, and they do NOT always print the same figure: the
CSV exports every expense while the month report's listing holds company
expenses only and partitions private ones into their own reimbursements
section. So a month with a private expense totals differently in the two,
correctly, because each figure covers exactly the rows of the document it
sits in. What is shared is the per-row conversion, which is why the same
purchase can never be converted at two different rates.

Three rungs, in this order, because they are in order of how much they know
about what actually happened:

1. **Same currency.** A USD receipt is already the figure. No rate, no
   rounding, nothing to get wrong.
2. **The statement.** A receipt a charge of this month settled converts at
   that charge's own amount: it IS the money that left the account, rate and
   fees included, which no published average reproduces. The rate printed on
   the row is the one the charge implies (charge / receipt total), so the
   reader can see what the card did.
3. **A reference rate.** Everything else (an unmatched receipt, a pair still
   in review) converts at the rate the MATCHER would use for it, looked up
   through the caller's `reference_rate`: Settings' typed rate first, then
   the ECB monthly average. Reusing the matcher's own precedence is the
   point; a document that converted at a rate the matcher does not use would
   disagree with the FX block on the screen for the same purchase.

A row that reaches rung 3 with no rate available converts at nothing. It
keeps its own currency, gets no figure, and its listing number goes in
`unconverted` so the caller can say so on the page. A silent omission here
would understate a month's cost, which is the failure this item exists to
end; "no figure and a line saying which rows" is the honest shape, the same
one item 65 chose for an unreadable amount.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# The filing currency (owner, 2026-09-08; docs/us-substantiation-criteria.md
# section 1). One name, so a caller that wants the label and a caller that
# wants the conversion cannot drift apart.
BASE_CURRENCY = "USD"

_CENT = Decimal("0.01")

# What produced a row's figure, in the order the rungs above run. The strings
# are the ones `_reference_rate_for` already returns for its own rungs
# ("configured", "statement", "receipts", "ecb_month"), plus the two this
# module adds, so one vocabulary covers both.
SOURCE_SAME = "same"
SOURCE_CHARGE = "charge"

_SOURCE_TEXT = {
    SOURCE_SAME: "",
    SOURCE_CHARGE: "the charge",
    "configured": "your rate",
    "statement": "statement FX",
    "receipts": "receipt rates",
    "ecb_month": "ECB",
}


@dataclass(frozen=True)
class RowConversion:
    """One listing row's figure in the base currency.

    `amount` is None only when nothing could convert the row; every other
    field is then empty too, and the row's number is in `unconverted`.
    `rate` is the rate actually applied (absent on a same-currency row,
    where there is no conversion to show). `month` names the ECB month a
    rate came from and is empty otherwise, because the ECB rung may fall
    back to a neighbouring month and a reader owes no guess about which.
    """

    amount: Decimal | None
    rate: Decimal | None
    source: str
    month: str = ""

    def caption(self, base: str = BASE_CURRENCY) -> str:
        """The one short line a document prints under the row's amount, or
        "" when there is nothing to say (an unconvertible row, or a row
        already in the base currency).

        Reads as "= USD 320.88 at 1.162275, ECB 2026-07": the figure, then
        how it was reached. A reader who disagrees with the figure can see
        which rate to argue with, which is the whole reason the rate is on
        the row rather than in a footnote (item 98's proposed change)."""
        if self.amount is None or self.source == SOURCE_SAME:
            return ""
        text = f"= {base} {self.amount:,.2f}"
        if self.rate is not None:
            text += f" at {_rate_text(self.rate)}"
        how = _SOURCE_TEXT.get(self.source, self.source)
        if self.month:
            how = f"{how} {self.month}".strip()
        return f"{text}, {how}" if how else text


def _rate_text(rate: Decimal) -> str:
    """A rate as a document prints it: trailing zeros dropped, so 1.162275
    keeps its six decimals and a flat 5 does not read "5.000000"."""
    trimmed = rate.normalize()
    # `normalize()` renders a whole number in exponent form (5 -> "5E+1"
    # for 50), which is not a rate anyone recognizes.
    return f"{trimmed:f}"


def parse_money(text) -> Decimal | None:
    """One amount cell to a Decimal, or None when it cannot be read.

    The same rule `_pdf_common.parse_amount` applies, and for the same
    reason: a blank cell is zero (it has always counted as nothing) and a
    non-finite value is unreadable rather than a number, because
    `Decimal("NaN")` parses happily and one bad row would turn the month's
    single total into "nan". Kept here rather than imported so this module
    stays free of the PDF stack; the two are pinned to each other by test.
    """
    raw = str(text if text is not None else "").strip().replace(",", "")
    if not raw:
        return Decimal("0")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def allocate(amounts: Sequence[Decimal], rate: Decimal) -> list[Decimal]:
    """`amounts` converted at `rate`, rounded to cents, summing EXACTLY to
    the rounded conversion of their own total.

    A receipt whose lines book to two accounts writes two listing rows, and
    rounding each one on its own lets the pair miss the receipt's own
    converted total by a cent. That matters more here than it looks: on a
    settled receipt the total IS the charge on the statement, so a cent of
    drift turns "this receipt is that charge" into a figure that does not
    tie out. The remainder lands on the last row carrying an amount, so a
    zero-amount split never acquires a figure out of nowhere.
    """
    parts = [(a * rate).quantize(_CENT, rounding=ROUND_HALF_UP) for a in amounts]
    target = (sum(amounts, Decimal("0")) * rate).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    drift = target - sum(parts, Decimal("0"))
    if drift:
        last = next(
            (i for i in range(len(parts) - 1, -1, -1) if amounts[i]), None
        )
        if last is not None:
            parts[last] += drift
    return parts


def needs_conversion(
    rows: Sequence[Sequence[str]],
    columns: Sequence[str],
    *,
    base: str = BASE_CURRENCY,
) -> bool:
    """Whether this listing has anything to convert: does any row carry a
    currency other than `base`?

    The gate on the whole feature, and it earns its place. A month whose
    receipts are all in the filing currency already answers "what did this
    month cost" on the line above; adding "Total in USD: 2,033.86" beside
    "USD 2,033.86" states the same number twice and teaches the reader that
    this part of the document can be skipped. The conversion exists for the
    months that mix currencies, and it appears on exactly those.
    """
    want = (base or "").upper()
    i = {name: n for n, name in enumerate(columns)}.get("Currency Code")
    if i is None:
        return False
    for row in rows:
        ccy = (str(row[i]).strip().upper() if i < len(row) else "")
        if ccy and ccy != want:
            return True
    return False


def convert_rows(
    rows: Sequence[Sequence[str]],
    columns: Sequence[str],
    *,
    numbers_by_doc: Mapping[str, Sequence[int]],
    settled_amounts: Mapping[str, tuple[Decimal, str]] | None = None,
    reference_rate: Callable[[str, str], tuple[Decimal, str, str] | None]
    | None = None,
    base: str = BASE_CURRENCY,
    skip: "set[int] | None" = None,
) -> tuple[dict[int, RowConversion], dict[str, Decimal], list[int]]:
    """Every listing row's figure in `base`, the month's total, and the rows
    that could not convert.

    `rows` are export rows in `columns` order (`EXPENSE_COLUMNS`), numbered
    from 1 as the listing numbers them. `numbers_by_doc` maps each document
    to the listing numbers it wrote, which is what makes a split receipt one
    conversion rather than two: it is the same map the month report already
    builds to caption receipt pages, so the two cannot describe different
    rows for one purchase.

    `settled_amounts` is `{document_id: (charge amount, charge currency)}`
    for the receipts a charge of this month settles (rung 2). A charge in
    some currency other than `base` lends nothing and the row falls through
    to the reference rate, because converting through two rates would print
    a figure neither document can source.

    `reference_rate(from_currency, on_date)` is rung 3, returning
    `(rate, source, month)` or None. Injected rather than imported so this
    module never reaches into the matching config; the caller passes the
    matcher's own lookup, which is what keeps the printed rate and the
    matched rate the same number.

    `skip` are listing numbers to leave out entirely: the rows whose amount
    could not be read (item 97). They are already captioned and already out
    of the per-currency totals, so a single-currency total that counted them
    as zero would be the only total on the page pretending they are free.

    The returned totals carry the base total under `base`; `unconverted` is
    the listing numbers no rate could price.
    """
    idx = {name: i for i, name in enumerate(columns)}

    def cell(row: Sequence[str], name: str) -> str:
        i = idx.get(name)
        return str(row[i]) if i is not None and i < len(row) else ""

    skipped = set(skip or ())
    base_ccy = (base or "").upper()
    out: dict[int, RowConversion] = {}
    totals: dict[str, Decimal] = {}
    unconverted: list[int] = []
    no_amount: list[int] = []

    for doc, numbers in numbers_by_doc.items():
        wanted = [n for n in numbers if n not in skipped and 1 <= n <= len(rows)]
        if not wanted:
            continue
        amounts: list[Decimal] = []
        live: list[int] = []
        for n in wanted:
            raw = str(cell(rows[n - 1], "Expense Amount")).strip()
            value = parse_money(raw)
            if not raw or value is None:
                # Two different events, one outcome. A row whose total nobody
                # could read (item 97 writes it with the cell blank) has no
                # amount to convert, so it takes no figure AND no rate: a
                # rate stamped on an empty amount is a claim about a number
                # that was never read. It is not "no rate for its currency"
                # either, so it is reported separately and never as zero.
                no_amount.append(n)
                continue
            amounts.append(value)
            live.append(n)
        if not live:
            continue
        ccy = (cell(rows[live[0] - 1], "Currency Code") or "").upper()
        on = cell(rows[live[0] - 1], "Expense Date")

        if ccy == base_ccy:
            for n, amount in zip(live, amounts):
                out[n] = RowConversion(amount, None, SOURCE_SAME)
                totals[base_ccy] = totals.get(base_ccy, Decimal("0")) + amount
            continue

        rate, source, month = None, "", ""
        charge = (settled_amounts or {}).get(doc)
        total = sum(amounts, Decimal("0"))
        if charge is not None and (charge[1] or "").upper() == base_ccy and total > 0:
            # Rung 2. The implied rate is what the card actually did; the
            # allocation below then reproduces the charge to the cent.
            implied = charge[0] / total
            if implied > 0:
                rate, source = implied, SOURCE_CHARGE
        if rate is None and reference_rate is not None and ccy:
            # Rung 3, reached whenever rung 2 produced nothing USABLE and not
            # merely when no charge was present. A charge that cannot yield a
            # positive rate (a credit, a zero) is not evidence of what the
            # purchase cost, and refusing the fallback there would report "no
            # rate" for a currency the month has a perfectly good rate for.
            hit = reference_rate(ccy, on)
            if hit is not None:
                rate, source, month = hit

        if rate is None or rate <= 0:
            unconverted.extend(live)
            continue

        shown = rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        for n, amount in zip(live, allocate(amounts, rate)):
            out[n] = RowConversion(amount, shown, source, month)
            totals[base_ccy] = totals.get(base_ccy, Decimal("0")) + amount

    return out, totals, sorted(unconverted), sorted(no_amount)


def total_for(
    converted: Mapping[int, RowConversion], numbers: "Sequence[int]"
) -> Decimal | None:
    """The base-currency sum over a slice of listing numbers, or None when
    the slice converted nothing.

    None rather than zero, so a per-card or per-cost-center section whose
    rows all failed to convert prints nothing instead of claiming the card
    cost nothing. A section that converted SOME of its rows reports what it
    has; the footer note names the rest.
    """
    parts = [
        converted[n].amount
        for n in numbers
        if n in converted and converted[n].amount is not None
    ]
    return sum(parts, Decimal("0")) if parts else None


def unconverted_note(
    numbers: Sequence[int],
    base: str = BASE_CURRENCY,
    labels: Mapping[int, str] | None = None,
    reason: str = "no rate for their currency",
) -> str:
    """The footer line naming the rows with no figure in `base`, or "" when
    every row converted.

    Same shape and same reason as `_pdf_common.excluded_note`: a clean month
    says nothing rather than "0 receipts not converted", and a month with a
    gap names the rows so the reader can go to them instead of hunting a
    total that is quietly short.

    `labels` decides HOW they are named. The month report numbers its
    listing, so there "expense 4" is a thing the reader can find. The CSV
    numbers nothing, and its listing numbers are not even the report's (the
    report renumbers after partitioning private rows out), so a bare number
    there would point at a different purchase in the other document. Given
    labels, the line names each row the way the CSV's own copies line does,
    by vendor and date.
    """
    listed = sorted(set(int(n) for n in numbers))
    if not listed:
        return ""
    one = len(listed) == 1
    if labels:
        named = "; ".join(labels.get(n, f"expense {n}") for n in listed)
    else:
        named = ("expense " if one else "expenses ") + ", ".join(
            str(n) for n in listed
        )
    count = "1 expense has" if one else f"{len(listed)} expenses have"
    why = reason.replace("their", "its") if one else reason
    return f"{count} no {base} figure ({why}): {named}."


def summary_lines(
    totals: Mapping[str, Decimal],
    unconverted: Sequence[int],
    converted: Mapping[int, RowConversion],
    base: str = BASE_CURRENCY,
    no_amount: Sequence[int] = (),
    labels: Mapping[int, str] | None = None,
) -> list[str]:
    """The lines a document writes under its rows: the figure, then the note
    naming what the figure leaves out. Both absent when the figure would say
    nothing the document does not already say.

    Two ways it says nothing, and both are silent:

    * **Nothing priced at all.** There is then no figure for a note to
      qualify, and "4 expenses have no USD figure" on every document of
      every month nobody has given a rate is a standing complaint rather
      than information. A document that nags is one people stop reading.
    * **Nothing actually converted.** If every row that got a figure was
      already in the base currency, this "total" is the base subtotal the
      per-currency line prints one line above. `needs_conversion` asks
      whether there is foreign money in the month; this asks whether any of
      it could be priced, which is the question that decides whether the
      reader learns anything.
    """
    if not any(c.source != SOURCE_SAME for c in converted.values()):
        return []
    missing = list(unconverted) + list(no_amount)
    line = total_line(totals, missing, len(converted), base)
    if not line:
        return []
    out = [line]
    for numbers, reason in (
        (unconverted, "no rate for their currency"),
        (no_amount, "their amount could not be read"),
    ):
        note = unconverted_note(numbers, base, labels, reason)
        if note:
            out.append(note)
    return out


def total_line(
    totals: Mapping[str, Decimal],
    unconverted: Sequence[int],
    priced: int | None = None,
    base: str = BASE_CURRENCY,
) -> str:
    """The month's single-currency figure as a document states it, or "" when
    nothing converted.

    When every row priced, this is the month's total and says so. When some
    row did not, it is NOT the total and must not be labelled as one: a
    figure headed "Total in USD" that quietly leaves an expense out is the
    exact failure item 65 exists to prevent, and a parenthetical caveat does
    not undo a heading, because the heading is what a reader carries away.
    So the label itself changes to "Partial total", with how many of how
    many expenses it covers; the footer note then names which ones.

    `priced` is how many listing rows got a figure, needed only for that
    partial wording.
    """
    amount = totals.get((base or "").upper())
    if amount is None:
        return ""
    missing = len(set(int(n) for n in unconverted))
    if not missing:
        return f"Total in {base}: {amount:,.2f}"
    if priced is None:
        return f"Partial total in {base}: {amount:,.2f}"
    whole = priced + missing
    return (
        f"Partial total in {base}: {amount:,.2f} "
        f"({priced} of {whole} expenses; the notes below say which are out "
        f"and why)"
    )
