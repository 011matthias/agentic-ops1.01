"""Excel statement parser — v2 spec §7.1 (sibling to `statement_csv.py`).

Reads an .xlsx statement Brisken downloads today and produces a list
of `Transaction` objects. Same interface, same `StatementParseError`
posture, same column-map shape as the CSV parser; the only behavioral
differences are the Excel-native cell type handling described below.

Cell-type handling
------------------
openpyxl returns native Python objects from cells:

* `datetime.datetime` / `datetime.date` for real date cells → used
  directly via `.date()` (no string parsing).
* `int` / `float` for numeric cells → routed through
  ``Decimal(str(value))`` so the IEEE-754 binary noise that bites
  ``Decimal(5.75)`` is avoided.
* `str` for text cells → routed through the shared `parse_date` /
  `parse_amount` helpers so the same date formats and
  ``$ / , / (50.00)`` tolerances apply as in CSV.
* `None` / empty string → empty.

Row-numbering convention matches CSV: header is row 1, first data row
is row 2. ``StatementParseError.line_number`` is consistent across
formats.

Fill-color annotation (L1, 2026-07-15 walkthrough)
--------------------------------------------------
Chris's per-card workbook uses cell fill as data: a YELLOW row is
already entered in Zoho, a GRAY row is a subscription. The parser reads
the fills of the mapped columns' cells and annotates each transaction
with ``entry_status`` ("posted" / "subscription" / None). This needs
real ``Cell`` objects, so the workbook is loaded in normal (not
read-only, not values-only) mode; her sheets are small, memory is a
non-issue. The classification is tolerant of rgb / indexed / theme+tint
color types and errs toward None (an untagged row is always safe).

Formula-column scan (L6)
------------------------
``data_only=True`` collapses a formula cell to its cached value, which
is indistinguishable from typed bank data downstream. Her sheet's
running-amount column IS a formula she copy-pastes. A light second pass
(read-only, ``data_only=False``) checks the MAPPED columns for formula
cells and emits one ``ParseIssue(severity="warning")`` per affected
column, so a formula-derived column mapped as ``amount`` is visibly
flagged instead of silently trusted. Warnings never abort a run.

Sign canonicalization (3.15, added here 2026-09-11)
---------------------------------------------------
Same two paths as the CSV sibling, because the Excel export of the same
bank prints the same convention: a mapped ``type`` column decides per
row (``Sale`` is a purchase, ``Payment`` / ``Return`` / ``Refund`` /
``Credit`` a credit); without one the file's sign majority is inferred
and surfaced as a warning. Canonical is purchase = positive, credit =
negative, and ``is_credit`` follows the canonical sign. Before this the
Excel parser kept the printed sign verbatim, so Criss's Chase workbooks
(purchases printed negative) reached the matcher as ``-15.00`` against
a ``15.00`` receipt and July and August 2026 reconciled 0 of 111 each
while the receipts sat in the pool unmatched.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from ..matching.types import CellFill, Transaction
from ._common import (
    OPTIONAL_KEYS,
    REQUIRED_KEYS,
    ParseIssue,
    StatementParseError,
    assign_content_ids,
    infer_sign_flip,
    is_credit_type,
    is_known_type,
    parse_amount,
    parse_date,
    row_type_for_label,
    unknown_type_issues,
    validate_required_map,
)

__all__ = [
    "OPTIONAL_KEYS",
    "REQUIRED_KEYS",
    "StatementParseError",
    "parse_statement_xlsx",
    "parse_statement_xlsx_tolerant",
]

# ── L1 fill classification ────────────────────────────────────────────
#
# The reader NAMES every fill it can read, and infers meaning from exactly
# two of those names. Owner directive 2026-09-20: "dont attribute colors in
# the statements or receipts any deeper meaning, all i need you to be able
# to do, is get the classifier to read all these colors and more." So the
# families below are a vocabulary of shades, not a vocabulary of verdicts;
# `_FAMILY_ENTRY_STATUS` is the whole of the meaning, and it is the same two
# marks the 2026-07-15 walkthrough established.
#
# Measured on the live workbooks 2026-09-20 (in-machine, read-only): July
# carries eight distinct fills and August five, of which the pre-directive
# thresholds could name only the yellows and the neutrals. 84 of July's 112
# rows carried a colour the reader could not see at all (48 orange + 35 blue
# + 1 blue/green), every one of them in the `Card` column, which is a THIRD
# annotation channel beside the yellow `Amount` and the gray `Description`.
# Naming them changes no verdict; see `_FAMILY_ENTRY_STATUS`.
#
# Hue bands (HSV) replace the ad-hoc RGB arithmetic they grew out of, so a
# shade Criss has not used yet still lands in the right family instead of
# falling off the edge of a hand-tuned inequality. Two carve-outs keep the
# two MEANINGFUL families exactly where they were:
#
#  * amber: hue 45-52 at high saturation is gold (FFC000), not the pale
#    yellow highlight (FFE699, same theme colour two tints lighter). The
#    old thresholds already split that ramp; the saturation cap is that
#    split, stated in the terms that actually separate the two.
#  * olive: a yellow-hued fill below `_YELLOW_MIN_VALUE` is a dark olive,
#    not a highlighter. This is the old `r >= 180` floor, unchanged.
_NEUTRAL_MAX_CHROMA = 24
_GRAY_MIN_MEAN = 110
_GRAY_MAX_MEAN = 224
_YELLOW_MIN_HUE = 45.0
_YELLOW_MAX_HUE = 61.0          # above 60 green dominates: a chartreuse
_YELLOW_MIN_VALUE = 180         # was `_YELLOW_MIN_RED`
_AMBER_MAX_HUE = 52.0
_AMBER_MIN_SAT = 0.72

# Upper edge of each chromatic band, in hue degrees. Yellow is handled
# before this table because of the two carve-outs above.
_HUE_BANDS: tuple[tuple[float, str], ...] = (
    (15.0, "red"),
    (45.0, "orange"),
    (61.0, "yellow"),
    (165.0, "green"),
    (195.0, "cyan"),
    (255.0, "blue"),
    (290.0, "purple"),
    (330.0, "pink"),
)

# The ONLY meaning any colour carries. A family absent from this map is
# recorded on the row and votes on nothing (`_row_entry_status`), which is
# what keeps "read more colours" from silently re-classifying a month.
_FAMILY_ENTRY_STATUS: dict[str, str] = {
    "yellow": "posted",
    "gray": "subscription",
}

# Default-Office theme colors (index -> RGB hex) for `theme`-typed fills.
# 10 / 11 are the hyperlink pair, added 2026-09-20 with the rest of the
# widening: neither is yellow or neutral, so neither can move a verdict.
# An unknown index still resolves to None (unnamed is always safe).
_THEME_RGB = {
    0: "FFFFFF", 1: "000000", 2: "E7E6E6", 3: "44546A", 4: "4472C4",
    5: "ED7D31", 6: "A5A5A5", 7: "FFC000", 8: "5B9BD5", 9: "70AD47",
    10: "0563C1", 11: "954F72",
}


def _hue(r: int, g: int, b: int) -> float:
    """Hue in degrees (0-360). Undefined for a neutral; callers check
    chroma first."""
    hi, lo = max(r, g, b), min(r, g, b)
    delta = hi - lo
    if delta == 0:
        return 0.0
    if hi == r:
        hue = 60.0 * (((g - b) / delta) % 6.0)
    elif hi == g:
        hue = 60.0 * (((b - r) / delta) + 2.0)
    else:
        hue = 60.0 * (((r - g) / delta) + 4.0)
    return hue % 360.0


def colour_family(r: int, g: int, b: int) -> str:
    """The fill's colour family: a NAME, never a verdict.

    Total over the RGB cube — every readable fill gets a family, so the
    payload can tell "coloured, and this is the shade" apart from "not
    coloured", which before 2026-09-20 were both `None`.
    """
    hi, lo = max(r, g, b), min(r, g, b)
    chroma = hi - lo
    if chroma <= _NEUTRAL_MAX_CHROMA:
        mean = (r + g + b) / 3
        if mean > _GRAY_MAX_MEAN:
            return "white"
        if mean < _GRAY_MIN_MEAN:
            return "black"
        return "gray"
    hue = _hue(r, g, b)
    if _YELLOW_MIN_HUE <= hue < _YELLOW_MAX_HUE:
        saturation = chroma / hi if hi else 0.0
        if hue < _AMBER_MAX_HUE and saturation >= _AMBER_MIN_SAT:
            return "orange"
        return "yellow" if hi >= _YELLOW_MIN_VALUE else "olive"
    for edge, name in _HUE_BANDS:
        if hue < edge:
            return name
    return "red"


def _classify_rgb(r: int, g: int, b: int) -> str | None:
    """The two marks Criss's workbook carries, and nothing else."""
    return _FAMILY_ENTRY_STATUS.get(colour_family(r, g, b))


def _apply_tint(component: int, tint: float) -> int:
    # The standard OOXML tint formula.
    if tint > 0:
        return round(component + (255 - component) * tint)
    if tint < 0:
        return round(component * (1 + tint))
    return component


def _fill_rgb(fill) -> tuple[int, int, int] | None:
    """The solid fill's RGB, or None when there is no classifiable solid
    fill (no fill, hatch patterns, system colors, unknown theme slots)."""
    try:
        if fill is None or fill.patternType != "solid":
            return None
        color = fill.fgColor
        if color is None:
            return None
        hex_rgb: str | None = None
        if color.type == "rgb" and isinstance(color.rgb, str):
            raw = color.rgb
            if len(raw) == 8:
                if raw == "00000000":  # the no-fill placeholder
                    return None
                raw = raw[2:]
            if len(raw) != 6:
                return None
            hex_rgb = raw
        elif color.type == "indexed":
            from openpyxl.styles.colors import COLOR_INDEX

            idx = color.indexed
            if idx is None or idx >= len(COLOR_INDEX) or idx in (64, 65):
                return None
            raw = COLOR_INDEX[idx]
            hex_rgb = raw[2:] if len(raw) == 8 else raw
        elif color.type == "theme":
            base = _THEME_RGB.get(color.theme)
            if base is None:
                return None
            r = int(base[0:2], 16)
            g = int(base[2:4], 16)
            b = int(base[4:6], 16)
            tint = float(color.tint or 0.0)
            return (_apply_tint(r, tint), _apply_tint(g, tint), _apply_tint(b, tint))
        if hex_rgb is None:
            return None
        return (int(hex_rgb[0:2], 16), int(hex_rgb[2:4], 16), int(hex_rgb[4:6], 16))
    except Exception:  # noqa: BLE001 - a weird color object is never fatal
        return None


def _classify_fill(cell) -> str | None:
    rgb = _fill_rgb(getattr(cell, "fill", None))
    if rgb is None:
        return None
    return _classify_rgb(*rgb)


def _row_fills(row_cells, headers: list[str]) -> tuple[CellFill, ...]:
    """Every readable fill on the row, as `CellFill(column, index, hex,
    family)`, left to right.

    Records EVERY column, not only the mapped ones. The verdict still reads
    mapped columns alone (`_row_entry_status`), but seeing is not voting:
    July's `Memo` column carries a gray and a green the mapped-column scan
    never reached, and the directive is that the reader sees them. A column
    header can repeat (both live workbooks have two `Memo` columns), so the
    index is what identifies the cell.
    """
    fills: list[CellFill] = []
    for index, cell in enumerate(row_cells):
        rgb = _fill_rgb(getattr(cell, "fill", None))
        if rgb is None:
            continue
        fills.append(
            CellFill(
                column=headers[index] if index < len(headers) else "",
                index=index,
                hex="%02X%02X%02X" % rgb,
                family=colour_family(*rgb),
            )
        )
    return tuple(fills)


def _row_entry_status(row_cells, mapped_indices: list[int]) -> str | None:
    """Classify a row from the fills of its MAPPED columns' cells (a
    full-row fill covers them; unmapped decoration columns don't vote).
    Majority over non-None classifications; a tie goes to "posted" (the
    annotation is display-plus-export-skip, so the stronger flag is the
    safe tie-break: a skipped-but-visible row beats a double-post)."""
    votes: dict[str, int] = {}
    for idx in mapped_indices:
        if idx < len(row_cells):
            label = _classify_fill(row_cells[idx])
            if label is not None:
                votes[label] = votes.get(label, 0) + 1
    if not votes:
        return None
    top = max(votes.values())
    winners = sorted(k for k, v in votes.items() if v == top)
    return "posted" if "posted" in winners else winners[0]


def _is_cell_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _coerce_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_date(_coerce_str(value))


def _coerce_amount(value: object) -> Decimal:
    # bool is a subclass of int in Python — reject explicitly so a stray
    # TRUE/FALSE cell never becomes Decimal(1) / Decimal(0).
    if isinstance(value, bool):
        raise ValueError(f"Not a number: {value!r}")
    if isinstance(value, (int, float)):
        # Decimal(str(5.75)) == Decimal("5.75"); Decimal(5.75) doesn't.
        return Decimal(str(value))
    return parse_amount(_coerce_str(value))


def parse_statement_xlsx(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
    sheet_name: str | None = None,
) -> list[Transaction]:
    """Strict mode: raise on the first row-level ERROR. Warnings (e.g.
    the L6 formula-column advisory) never raise.

    See `_common.py` module docstring for the header-vs-row error
    distinction. Backward-compatible with slice-1 callers.
    """
    transactions, issues = parse_statement_xlsx_tolerant(
        path, column_map, account_id, legal_entity_id, account_card_currency, sheet_name
    )
    hard = [i for i in issues if i.severity == "error"]
    if hard:
        raise hard[0].to_error()
    return transactions


def parse_statement_xlsx_tolerant(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
    sheet_name: str | None = None,
) -> tuple[list[Transaction], list[ParseIssue]]:
    """Tolerant mode (ANNEALING B1): collect row-level errors, continue."""
    validate_required_map(column_map)

    path = Path(path)
    file_name = path.name
    transactions: list[Transaction] = []
    issues: list[ParseIssue] = []
    # item 64: {Type label the parser does not recognise: rows carrying it}.
    unknown_types: dict[str, int] = {}
    # Normal (not read-only) load: L1 needs real Cell objects with full
    # style access for the fill classification. data_only=True gives the
    # cached VALUE of a formula cell (the L6 scan below flags those).
    wb = load_workbook(filename=path, data_only=True)
    try:
        ws = wb[sheet_name] if sheet_name is not None else wb.active

        rows = ws.iter_rows()
        try:
            header_cells = next(rows)
        except StopIteration:
            raise StatementParseError("Excel sheet has no rows") from None

        headers: list[str] = []
        for cell in header_cells:
            value = cell.value
            if value is None:
                headers.append("")
            elif isinstance(value, str):
                headers.append(value.strip())
            else:
                headers.append(str(value))

        if not any(headers):
            raise StatementParseError("Excel sheet has no header row")

        header_index: dict[str, int] = {}
        for i, h in enumerate(headers):
            if h:
                # First occurrence wins on duplicate headers; same as csv.DictReader.
                header_index.setdefault(h, i)

        for logical_key, source_col in column_map.items():
            if source_col not in header_index:
                raise StatementParseError(
                    f"Excel missing column {source_col!r} "
                    f"(mapped from logical key {logical_key!r}). "
                    f"Available columns: {[h for h in headers if h]}"
                )

        mapped_indices = sorted(
            {header_index[source_col] for source_col in column_map.values()}
        )

        for row_index, row_cells in enumerate(rows, start=2):
            row_values = tuple(c.value for c in row_cells)
            mapped: dict[str, object] = {}
            for logical, source_col in column_map.items():
                idx = header_index[source_col]
                mapped[logical] = row_values[idx] if idx < len(row_values) else None

            if all(_is_cell_empty(v) for v in mapped.values()):
                continue  # blank row, common at EOF

            try:
                txdate = _coerce_date(mapped["transaction_date"])
                amount = _coerce_amount(mapped["amount"])
                vendor = _coerce_str(mapped["vendor"])

                posting: date | None = None
                if "posting_date" in column_map and not _is_cell_empty(
                    mapped.get("posting_date")
                ):
                    posting = _coerce_date(mapped["posting_date"])

                tx_currency = account_card_currency.upper()
                if "transaction_currency" in column_map:
                    raw_cur = _coerce_str(mapped.get("transaction_currency"))
                    if raw_cur:
                        tx_currency = raw_cur.upper()

                # L5: optional per-charge FX detail (BRL on the USD card).
                original_amount: Decimal | None = None
                if "original_amount" in column_map and not _is_cell_empty(
                    mapped.get("original_amount")
                ):
                    original_amount = _coerce_amount(mapped["original_amount"])
                original_currency: str | None = None
                if "original_currency" in column_map:
                    raw_orig = _coerce_str(mapped.get("original_currency"))
                    if raw_orig:
                        original_currency = raw_orig.upper()
                fx_rate: Decimal | None = None
                if "fx_rate" in column_map and not _is_cell_empty(
                    mapped.get("fx_rate")
                ):
                    fx_rate = _coerce_amount(mapped["fx_rate"])

                # WS3: the per-row card, when the workbook prints one.
                card_last4: str | None = None
                if "card" in column_map:
                    card_last4 = _coerce_str(mapped.get("card")) or None

                # 3.15 sign canonicalization, Type-column path (mirrors
                # statement_csv): the export's own debit/credit label
                # decides, not the printed sign. A row with an empty Type
                # cell keeps its printed sign and derives is_credit from it,
                # and since item 64 so does a row whose label this parser
                # does not recognise.
                is_credit = False
                # Item 73 (mirrors statement_csv): the label's row type.
                row_type: str | None = None
                if "type" in column_map:
                    raw_type = _coerce_str(mapped.get("type"))
                    if not raw_type:
                        is_credit = amount < 0
                    elif is_known_type(raw_type):
                        is_credit = is_credit_type(raw_type)
                        amount = -abs(amount) if is_credit else abs(amount)
                        row_type = row_type_for_label(raw_type)
                    else:
                        is_credit = amount < 0
                        unknown_types[raw_type] = (
                            unknown_types.get(raw_type, 0) + 1
                        )
            except (KeyError, ValueError) as exc:
                issues.append(
                    ParseIssue(
                        file_name=file_name,
                        line_number=row_index,
                        message=str(exc),
                    )
                )
                continue

            raw_row = dict(
                zip(
                    [h for h in headers],
                    list(row_values) + [None] * max(0, len(headers) - len(row_values)),
                )
            )
            transactions.append(
                Transaction(
                    # Stamped by `assign_content_ids` at the end of the
                    # parse, so CSV / Excel / PDF share one identity rule.
                    transaction_id="",
                    source_row=row_index,
                    legal_entity_id=legal_entity_id,
                    account_id=account_id,
                    transaction_date=txdate,
                    posting_date=posting,
                    amount=amount,
                    transaction_currency=tx_currency,
                    account_card_currency=account_card_currency.upper(),
                    vendor_from_statement=vendor,
                    raw_text=str(raw_row),
                    original_amount=original_amount,
                    original_currency=original_currency,
                    fx_rate=fx_rate,
                    entry_status=_row_entry_status(row_cells, mapped_indices),
                    fills=_row_fills(row_cells, headers),
                    is_credit=is_credit,
                    card_last4=card_last4,
                    row_type=row_type,
                )
            )
    finally:
        wb.close()

    # item 64 (mirrors statement_csv): one advisory per distinct label the
    # Type column carried that this parser could not read.
    issues.extend(unknown_type_issues(unknown_types, file_name))

    # 3.15 sign canonicalization, no-Type path (mirrors statement_csv):
    # without a debit/credit column the file's convention is inferred from
    # the sign majority. A majority-negative workbook prints purchases as
    # negatives (the Chase export Criss uploads), so every sign flips to
    # reach the canonical convention; the inference is surfaced as a
    # warning, never silent. After canonicalization, credit = negative.
    if "type" not in column_map and transactions:
        flip = infer_sign_flip([t.amount for t in transactions])
        if flip:
            n_neg = sum(1 for t in transactions if t.amount < 0)
            issues.append(
                ParseIssue(
                    file_name=file_name,
                    line_number=1,
                    message=(
                        f"sign convention inferred: {n_neg} of "
                        f"{len(transactions)} amounts are negative, so this "
                        f"export prints purchases as negatives; all signs "
                        f"flipped to canonical (purchase = positive, credit "
                        f"= negative). Map a 'type' column to make this "
                        f"explicit."
                    ),
                    severity="warning",
                )
            )
            transactions = [replace(t, amount=-t.amount) for t in transactions]
        transactions = [
            replace(t, is_credit=t.amount < 0) if (t.amount < 0) != t.is_credit
            else t
            for t in transactions
        ]

    issues.extend(
        _scan_formula_columns(path, sheet_name, column_map, file_name)
    )
    return assign_content_ids(transactions), issues


def _scan_formula_columns(
    path: Path,
    sheet_name: str | None,
    column_map: Mapping[str, str],
    file_name: str,
) -> list[ParseIssue]:
    """L6 — one warning per MAPPED column whose cells are formula-derived.

    The primary load uses data_only=True, which silently collapses a
    formula to its cached value; this streaming second pass (read-only,
    data_only=False) sees ``cell.data_type == 'f'`` and flags the column.
    Advisory only: never raises, never blocks the run."""
    issues: list[ParseIssue] = []
    try:
        wb = load_workbook(filename=path, read_only=True, data_only=False)
    except Exception:  # noqa: BLE001 - the primary load already succeeded
        return issues
    try:
        ws = wb[sheet_name] if sheet_name is not None else wb.active
        rows = ws.iter_rows()
        try:
            header_cells = next(rows)
        except StopIteration:
            return issues
        header_index: dict[str, int] = {}
        for i, cell in enumerate(header_cells):
            value = cell.value
            h = value.strip() if isinstance(value, str) else (str(value) if value is not None else "")
            if h:
                header_index.setdefault(h, i)
        watch: dict[int, str] = {}
        for logical, source_col in column_map.items():
            idx = header_index.get(source_col)
            if idx is not None:
                watch[idx] = source_col
        flagged: set[int] = set()
        for row_index, row_cells in enumerate(rows, start=2):
            for idx, source_col in watch.items():
                if idx in flagged or idx >= len(row_cells):
                    continue
                if row_cells[idx].data_type == "f":
                    flagged.add(idx)
                    issues.append(
                        ParseIssue(
                            file_name=file_name,
                            line_number=row_index,
                            message=(
                                f"column {source_col!r} is formula-derived: "
                                "cell values are cached formula results, not "
                                "bank statement data"
                            ),
                            severity="warning",
                        )
                    )
            if len(flagged) == len(watch):
                break
    except Exception:  # noqa: BLE001 - advisory scan must never break a parse
        return issues
    finally:
        wb.close()
    return issues
