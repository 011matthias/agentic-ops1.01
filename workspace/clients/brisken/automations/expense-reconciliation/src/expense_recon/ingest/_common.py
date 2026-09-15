"""Shared helpers for statement parsers (CSV, Excel, ...).

Lifted from `statement_csv.py` when the Excel sibling parser landed;
both parsers share the same column-map shape, the same error type,
and the same date/amount tolerance rules (v2 spec §7.1).

Row-number convention is identical across formats: header row is
line 1, the first data row is line 2. `StatementParseError.line_number`
points the caller at the offending row regardless of file format.

Two parse modes per ANNEALING B1:

* **Strict** — `parse_X(path, ...)` raises `StatementParseError` on
  the first bad row. Backward-compatible with the slice-1 behavior;
  used by tests that pin parser semantics.
* **Tolerant** — `parse_X_tolerant(path, ...)` returns
  `tuple[list[Obj], list[ParseIssue]]`. Header-level errors (missing
  column, no header) still raise (nothing to recover). Row-level
  errors (bad date, bad amount, dup id) land in the issues list and
  the parser continues. The CLI uses tolerant mode and surfaces
  issues on the Errors sheet — first real Brisken month is expected
  to have at least one malformed row, and stack-tracing on row 5 of
  500 would lose all the good data.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


REQUIRED_KEYS: tuple[str, ...] = ("transaction_date", "amount", "vendor")
# L5 (2026-07-15): original_amount / original_currency / fx_rate let a
# tabular statement carry per-charge foreign-currency detail (BRL on the
# USD card), the same fields the Chase PDF parser populates. The matcher
# already consumes them (deterministic.py FX-detail path).
# 3.15 (2026-07-20): "type" maps the export's debit/credit column (Chase
# activity CSV "Type": Sale / Payment / Return / ...) so the row's sign
# can be canonicalized per source instead of trusted blindly.
# WS3 (2026-07-21): "card" maps the per-row card column a tabular export
# prints beside every charge (Chase activity CSV "Card": 2838 / 3645 /
# 3876 / 0340) into `Transaction.card_last4`. The statement PDF has always
# carried this identity in `account_id` via its per-card cycle markers; on
# the CSV / xlsx path `account_id` names the whole account, so without this
# key a multi-card export looks like one card and card-scoped matching
# silently does nothing.
OPTIONAL_KEYS: tuple[str, ...] = (
    "posting_date",
    "transaction_currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "type",
    "card",
)

# Type-column values that mark a CREDIT (money back to the card): the
# canonical sign is negative and the transaction is partitioned into the
# refunds bucket, never pair-matched to a purchase receipt (LD-5 A5).
# A recognised label that is NOT here (Sale, Fee) is a purchase; see
# DEBIT_TYPE_VALUES below for the other half of that vocabulary, and for
# what a label in neither set now does.
CREDIT_TYPE_VALUES: frozenset[str] = frozenset(
    {"payment", "return", "refund", "credit", "reversal"}
)


def is_credit_type(type_value: str) -> bool:
    """True when a statement Type-column value marks a credit/refund."""
    return type_value.strip().lower() in CREDIT_TYPE_VALUES


# Type-column values that mark a DEBIT (a purchase on the card): canonical
# sign positive. This set exists so that "recognised" has a definition wider
# than "is a credit" (backlog item 64). Until 2026-09-15 both parsers read
# ANY label `is_credit_type` did not claim as a purchase and abs'd the row,
# so a German export's "Lastschrift" would have had every credit flipped
# into a purchase, silently. A label in NEITHER set is one this parser does
# not know, and an unknown label is not evidence of direction: the row keeps
# the sign the export printed. "adjustment" stays a DEBIT deliberately, as
# before: ambiguous, but read as a purchase so it surfaces for review rather
# than landing in refunds.
DEBIT_TYPE_VALUES: frozenset[str] = frozenset(
    {"sale", "purchase", "charge", "debit", "fee", "interest", "adjustment"}
)

# A Type column mapped to the wrong source column (a Description, say) makes
# every row its own unknown label. Cap the per-label notes so a mis-mapped
# column reports once as a summary rather than five hundred times.
UNKNOWN_TYPE_ISSUE_CAP = 10


def is_known_type(type_value: str) -> bool:
    """True when a Type-column value is a label this parser recognises,
    credit or debit. False means the parser has no opinion on the row's
    direction, so the printed sign stands."""
    value = type_value.strip().lower()
    return value in CREDIT_TYPE_VALUES or value in DEBIT_TYPE_VALUES


def infer_sign_flip(amounts: "list[Decimal]") -> bool:
    """True when a statement's sign convention is inverted (purchases
    printed negative), detected by strict majority of nonzero amounts
    being negative. A normal month is dominated by purchases, so a
    majority-negative export (the Chase activity CSV: Type=Sale prints
    -10.32) is printing debits as negatives and every sign must flip to
    reach the canonical convention (purchase = positive, credit =
    negative). At least 3 negatives are required before inferring: a
    tiny export that happens to hold only a refund or two is kept
    verbatim rather than wrongly flipped. Used only when no Type column
    is mapped; the caller emits a warning ParseIssue so the inference
    is never silent."""
    nonzero = [a for a in amounts if a != 0]
    if not nonzero:
        return False
    negatives = sum(1 for a in nonzero if a < 0)
    return negatives >= 3 and negatives * 2 > len(nonzero)


class StatementParseError(ValueError):
    """Raised when a statement file cannot be parsed.

    `line_number` is the 1-indexed row number (the header row is
    line 1; the first data row is line 2). Use it to point the user
    at the exact problematic row.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number


@dataclass(frozen=True)
class ParseIssue:
    """One row-level parse failure collected in tolerant mode.

    `file_name` is the source-file basename (e.g., "receipts.csv");
    the Errors sheet shows this so the user knows which file the
    issue came from when a run ingests multiple files. `line_number`
    follows the same convention as `StatementParseError.line_number`
    (header is row 1, data starts at row 2).

    `severity`: "error" (a row failed to parse) or "warning" (advisory,
    e.g. a mapped column is formula-derived, L6). Strict mode raises
    only on errors; warnings never abort a run.
    """

    file_name: str
    line_number: int
    message: str
    severity: str = "error"

    def to_error(self) -> StatementParseError:
        return StatementParseError(
            f"{self.file_name} row {self.line_number}: {self.message}",
            line_number=self.line_number,
        )


def unknown_type_issues(
    counts: Mapping[str, int], file_name: str
) -> list[ParseIssue]:
    """One advisory per distinct unrecognised Type label, naming the label
    and how many rows carried it (backlog item 64).

    Severity `info`: nothing failed and nothing was inferred, so this is
    neither an `error` nor the `warning` the sign inference earns. It is the
    record that the parser declined to canonicalize those rows, which is the
    only way an operator can tell a kept sign from an endorsed one.

    `line_number` 0 per the whole-file convention in `docs/api-contract.md`:
    the rows are scattered through the file, so pointing at one of them, or
    at the header, would be worse than pointing at none.
    """
    issues: list[ParseIssue] = []
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    for label, n in ordered[:UNKNOWN_TYPE_ISSUE_CAP]:
        issues.append(
            ParseIssue(
                file_name=file_name,
                line_number=0,
                message=(
                    f"Type {label!r} is not a label this parser recognises "
                    f"({n} row{'s' if n != 1 else ''}), so those rows kept "
                    f"the sign the export printed."
                ),
                severity="info",
            )
        )
    rest = ordered[UNKNOWN_TYPE_ISSUE_CAP:]
    if rest:
        issues.append(
            ParseIssue(
                file_name=file_name,
                line_number=0,
                message=(
                    f"{len(rest)} further Type labels this parser does not "
                    f"recognise ({sum(n for _, n in rest)} rows), all keeping "
                    f"the sign the export printed. A Type column this varied "
                    f"is usually mapped to the wrong source column."
                ),
                severity="info",
            )
        )
    return issues


_DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")


def parse_date(s: str) -> date:
    s = s.strip()
    if not s:
        raise ValueError("empty date")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def parse_amount(s: str) -> Decimal:
    """Parse an amount string. Tolerates `$`, commas, surrounding
    whitespace, and accounting-style negatives like `(50.00)`."""
    raw = s.strip()
    if not raw:
        raise ValueError("empty amount")
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative = True
        raw = raw[1:-1]
    raw = raw.replace("$", "").replace(",", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Not a number: {s!r}") from exc
    return -value if negative else value


def canonical_amount(value: Decimal) -> str:
    """Canonical string form of a money amount for identity purposes.

    Trailing zeros carry no monetary meaning, so `10.30` and `10.3` are
    the SAME charge and must produce the same string. `Decimal.normalize`
    does that but re-spells large round numbers in exponent form
    (`Decimal("100.00").normalize()` -> `1E+2`); re-quantizing a positive
    exponent back to an integer keeps the plain-digit spelling. Zero is
    special-cased so `-0.00` and `0.00` cannot disagree.
    """
    if value == 0:
        return "0"
    n = value.normalize()
    exponent = n.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        n = n.quantize(Decimal(1))
    return format(n, "f")


def transaction_content_id(
    *,
    account_id: str,
    card_last4: str | None,
    transaction_date: date,
    amount: Decimal,
    transaction_currency: str,
    vendor_from_statement: str,
    reference: str | None = None,
    seen: dict[str, int] | None = None,
) -> str:
    """A statement row's identity, derived from what the row SAYS.

    Transaction ids used to be positional (`f"{account_id}:{row_index}"`).
    Operator decisions key on the id (`decisions.transaction_id`), so any
    partial or appended statement upload renumbered every row and silently
    re-pointed every confirm / reject / manual-match onto a different
    charge. The living month (PR 2) makes appends routine, which turns
    that from a latent bug into a certain one. A content-derived id is
    stable under append, insert, and reordering because it does not depend
    on where in the file the row happened to sit.

    Identical rows are NOT collapsed: two identical coffees on one day are
    two real charges. Pass a per-parse `seen` dict and the second and later
    occurrences get a `-{n}` suffix, so a re-parse of the same file
    reproduces the same set of ids while distinct charges stay distinct.

    The suffix separator is `-`, deliberately NOT `:`. Two consumers care.
    `sheet_writeback._anchor_row` still recovers a sheet row from a legacy
    positional id by splitting on the LAST `:`, so an id ending `:2` would
    be read as "row 2" and write an account next to the wrong charge in
    Criss's workbook. And `transaction_id` travels as a URL path segment
    (`/api/runs/{run_id}/transactions/{transaction_id}/receipt`), which
    rules out `#`. A hex digest can never contain `-`, so the split stays
    unambiguous in the other direction too.

    Fields are joined via `json.dumps` rather than a separator string: it
    escapes deterministically (a vendor containing the separator cannot
    forge a collision) and keeps `None` distinguishable from `""`.
    """
    card = (card_last4 or "").strip().upper() or None
    payload = json.dumps(
        [
            account_id.strip(),
            card,
            transaction_date.isoformat(),
            canonical_amount(amount),
            (transaction_currency or "").strip().upper(),
            " ".join((vendor_from_statement or "").split()).casefold(),
            (reference or "").strip() or None,
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    if seen is None:
        return digest
    occurrence = seen.get(digest, 0)
    seen[digest] = occurrence + 1
    return digest if occurrence == 0 else f"{digest}-{occurrence}"


def assign_content_ids(transactions: "list") -> "list":
    """Stamp content-derived ids onto parsed transactions, in file order.

    Called ONCE per parse, at the very end, by every statement parser.
    Two reasons it is a post-pass rather than done inline:

    * **Sign canonicalization has to have happened first.** With a mapped
      `type` column the sign is canonicalized per row inside the parse
      loop; without one it is inferred from the whole file's sign majority
      and applied afterwards. Stamping inline would give the same logical
      row a different id depending on which path ran. Stamping last means
      the id always derives from the canonical amount.
    * **One definition of identity for CSV, Excel and PDF.** The occurrence
      counter for byte-identical rows only behaves consistently if every
      parser walks its rows in file order through the same code.

    A file whose sign inference differs between a partial and a full
    upload therefore yields different ids for the same printed row. That
    is deliberate: the two uploads genuinely disagree about whether the
    money went out or came back, and surfacing two rows is safer than
    silently deduping a contradiction down to whichever arrived first.
    """
    from dataclasses import replace

    seen: dict[str, int] = {}
    return [
        replace(
            t,
            transaction_id=transaction_content_id(
                account_id=t.account_id,
                card_last4=t.card_last4,
                transaction_date=t.transaction_date,
                amount=t.amount,
                transaction_currency=t.transaction_currency,
                vendor_from_statement=t.vendor_from_statement,
                seen=seen,
            ),
        )
        for t in transactions
    ]


@dataclass(frozen=True)
class TransactionMerge:
    """What one statement upload contributed to a month's charges.

    `transactions` is the month's full set after the fold, `added` the ids
    this upload put there, `duplicates` the ids it supplied that the set
    already held. The two id lists are what an append route reports back
    ("14 rows, 11 already here") and what it records per statement.
    """

    transactions: list
    added: list[str]
    duplicates: list[str]


def merge_transactions(existing: "list", incoming: "list") -> TransactionMerge:
    """Fold a freshly parsed statement into the charges a month already holds.

    The living month (PR 2b-2b) lets a statement arrive in pieces: one card
    at a time, a mid-month partial then the full cycle, the same file twice
    by accident. Every one of those overlaps what is already there, so the
    fold has to be by IDENTITY rather than by position or by file.

    `transaction_id` is that identity — content-derived since PR 2a, which
    is precisely what makes it survive an append. Nothing else here is a
    second definition of sameness: two rows are the same charge exactly when
    `transaction_content_id` says so, and the occurrence suffix already keeps
    two identical coffees on one day apart, in both the old set and the new.

    Three properties the callers depend on:

    * **First-write-wins.** A re-supplied row keeps the object the month
      already committed. Operator decisions, `source_row`, and every stored
      judgment key on that row; swapping in a byte-equal copy parsed from a
      different file would re-point `source_row` into the wrong workbook and
      buy nothing.
    * **`existing` passes through untouched, in order.** This function
      filters what an upload CONTRIBUTES; it never edits the month. An
      `existing` list that somehow repeats an id keeps both rows, because
      silently changing a month's charge count is not a merge's business.
    * **A contradiction surfaces as two rows, not one.** A file whose sign
      inference differs between a partial and a full upload gives the same
      printed row two different ids (see `assign_content_ids`), so both
      land. That is the deliberate call: the uploads genuinely disagree
      about which way the money went, and deduping one away would pick a
      winner arbitrarily.

    Note what identity includes: `account_id`. Two uploads of one card's
    statement typed against different account ids dedupe against nothing and
    the month doubles. That is honest at this layer — the rows really do
    claim to be different accounts — and it is the append route's job to
    keep the account stable across a card's uploads.
    """
    seen = {t.transaction_id for t in existing}
    merged = list(existing)
    added: list[str] = []
    duplicates: list[str] = []
    for t in incoming:
        tid = t.transaction_id
        if tid in seen:
            duplicates.append(tid)
            continue
        seen.add(tid)
        merged.append(t)
        added.append(tid)
    return TransactionMerge(
        transactions=merged, added=added, duplicates=duplicates
    )


def validate_required_map(column_map: Mapping[str, str]) -> None:
    """Raise `StatementParseError` if required column-map keys are missing."""
    missing = [k for k in REQUIRED_KEYS if k not in column_map]
    if missing:
        raise StatementParseError(
            f"column_map missing required keys: {', '.join(missing)}"
        )
