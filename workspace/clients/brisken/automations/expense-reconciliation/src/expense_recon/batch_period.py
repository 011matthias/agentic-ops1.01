"""Which month a batch is, and whether an expense's date belongs in it.

Backlog item 25 (2026-08-23). The live April 2026 batch carried eleven
expenses dated 2020-2023. The stored raw extractions already held those
years, so nothing downstream mangled them; the vision read was wrong at the
source, twice over:

* `receipt_33` prints its true date twice. The fiscal block says
  `Data: 2026-04-22`; the card slip above it says `26-04-22`, which is
  YY-MM-DD. The model read the slip day-first and returned 2022-04-26.
* `receipt_03` prints `02/04/2026` in full and `02.04.26` on the slip. The
  model returned 2023-04-02 -- day and month right, the two-digit `26`
  resolved to a year that is not 2026.

A better prompt narrows that (and the prompt was changed in the same round),
but no prompt makes a faded thermal slip legible, and a re-issued invoice can
genuinely print an old date. The date decides which month an expense belongs
to and whether a statement charge can ever match it, so the durable fix is
not a better read: it is that an implausible date stops being silently
accepted.

This module answers the one question the guard needs -- what month is this
batch? -- and refuses to guess:

* The operator's own label wins ("April 2026"). She names the month; a row
  that contradicts her label is exactly the contradiction worth surfacing.
* Failing a label, the batch's own dates decide by strict plurality, so an
  unlabelled batch is still guarded.
* Failing both, there is no period and nothing is ever flagged. Silence
  beats a guessed month, because every flag costs the reviewer a look.

The window is the period month plus its two neighbours: a folder for one
month legitimately holds a purchase from the last days of the month before
and the first of the month after. Anything years away is what this catches.
"""
from __future__ import annotations

import calendar
import re
from collections import Counter
from datetime import date

# Month names the operator actually types. English because the tool is in
# English; Portuguese because the reviewer is Brazilian and the receipts are.
_MONTHS: dict[str, int] = {}
for _i, (_en, _pt) in enumerate(
    (
        ("january", "janeiro"), ("february", "fevereiro"), ("march", "marco"),
        ("april", "abril"), ("may", "maio"), ("june", "junho"),
        ("july", "julho"), ("august", "agosto"), ("september", "setembro"),
        ("october", "outubro"), ("november", "novembro"), ("december", "dezembro"),
    ),
    start=1,
):
    for _name in (_en, _pt):
        _MONTHS[_name] = _i
        _MONTHS[_name[:3]] = _i
# "mar" is March in both languages; "mai"/"marco" are the PT spellings that
# would otherwise be lost to the 3-letter collision above.
_MONTHS["sept"] = 9
_MONTHS["março"] = 3

_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_ISO_MONTH_RE = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$")

# A batch needs this many dated expenses before its own dates may vote, and
# the winning month needs this share of them. Below either bar the batch has
# no consensus and the guard stays silent.
_MIN_DATED_FOR_CONSENSUS = 4
_MIN_CONSENSUS_SHARE = 0.4


def month_from_label(label: str | None) -> tuple[int, int] | None:
    """`(year, month)` when the label unambiguously names ONE month, else None.

    Accepts "April 2026", "abril 2026", "2026 Apr", and a bare "2026-04".
    Refuses everything else on purpose -- notably a label that merely carries
    a full date ("chase-2838 2026-07-24"), which stamps when a statement run
    was created and says nothing about which month its expenses are.
    """
    raw = (label or "").strip()
    if not raw:
        return None

    iso = _ISO_MONTH_RE.match(raw)
    if iso:
        return int(iso.group(1)), int(iso.group(2))

    lowered = raw.lower()
    # A day-bearing date in the label means the label is a timestamp, not a
    # month; refuse rather than read its year-month half as the period.
    if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", lowered):
        return None

    months = {
        _MONTHS[word]
        for word in re.findall(r"[a-zçã]+", lowered)
        if word in _MONTHS
    }
    if len(months) != 1:
        return None
    years = {int(y) for y in _YEAR_RE.findall(lowered)}
    if len(years) != 1:
        return None
    return years.pop(), months.pop()


def month_from_dates(dates: list[date]) -> tuple[int, int] | None:
    """`(year, month)` the batch's own dates agree on, else None.

    A strict plurality with substance behind it: the winning month needs at
    least `_MIN_CONSENSUS_SHARE` of the dated expenses and strictly more than
    the runner-up. A near-tie is a genuinely mixed batch, and a mixed batch
    has no period to be outside of.
    """
    if len(dates) < _MIN_DATED_FOR_CONSENSUS:
        return None
    counts = Counter((d.year, d.month) for d in dates)
    ranked = counts.most_common(2)
    (top, n_top) = ranked[0]
    if len(ranked) > 1 and ranked[1][1] >= n_top:
        return None
    # At least three receipts must agree, whatever the share works out to:
    # two votes out of four is a coin toss, not a month.
    if n_top < max(3, len(dates) * _MIN_CONSENSUS_SHARE):
        return None
    return top


def batch_period(
    label: str | None, dates: list[date]
) -> tuple[date, date] | None:
    """The window an expense in this batch is expected to fall in, or None.

    The period month plus one month either side, inclusive. None means the
    batch has no knowable month, and the caller must flag nothing.
    """
    ym = month_from_label(label) or month_from_dates(dates)
    if ym is None:
        return None
    year, month = ym
    start_y, start_m = (year - 1, 12) if month == 1 else (year, month - 1)
    end_y, end_m = (year + 1, 1) if month == 12 else (year, month + 1)
    return (
        date(start_y, start_m, 1),
        date(end_y, end_m, calendar.monthrange(end_y, end_m)[1]),
    )


def outside_period(value: date | None, period: tuple[date, date] | None) -> bool:
    """True only when there IS a period and the date falls outside it."""
    if value is None or period is None:
        return False
    return value < period[0] or value > period[1]
