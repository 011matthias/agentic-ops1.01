"""ECB monthly reference rates for the matcher (backlog item 82).

Owner ruling 2026-09-16: the reference rate is per month, from the ECB, and a
rate the operator types in Settings still wins. The ECB Data API publishes a
monthly average of its daily reference rates per currency against the euro
(`EXR/M.{CCY}.EUR.SP00.A`, units of the currency per one EUR). One wildcard
query returns every currency for a span of months (29 currencies, about 20 KB,
half a second, measured 2026-09-17); the matcher crosses through EUR, so
BRL:USD is USD-per-EUR over BRL-per-EUR.

A month's average exists only after the month ends, so a month created early
reads its neighbour until the statement attach fetches again
(`MatchingConfig.ecb_monthly_rate` picks the nearest month and says which).

Fail-open by contract: a fetch that fails, times out or parses to nothing
returns `{}` and the caller keeps the config it had. Creating a month or
attaching a statement never waits on, or breaks on, the ECB.
`EXPENSE_RECON_ECB_RATES=0` switches the fetch off.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import re
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

ECB_MONTHLY_URL = "https://data-api.ecb.europa.eu/service/data/EXR/M..EUR.SP00.A"
FETCH_TIMEOUT_S = 4.0
_MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
_CCY = re.compile(r"[A-Z]{3}")


def enabled() -> bool:
    return os.environ.get("EXPENSE_RECON_ECB_RATES", "1").strip() != "0"


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def month_from_index(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def months_around(month: str, before: int = 1, after: int = 1) -> list[str]:
    """`month` and its neighbours, oldest first ("2026-07" -> 06, 07, 08)."""
    if not _MONTH.fullmatch(month or ""):
        return []
    i = month_index(month)
    return [month_from_index(j) for j in range(i - before, i + after + 1)]


def parse_csv(text: str) -> dict[str, dict[str, str]]:
    """The ECB `csvdata` body as {month: {currency: units per EUR}}.

    Values stay the ECB's own digits as text (a Decimal keeps them exact); a
    row with a malformed period, currency or a non-positive value is skipped,
    never guessed at."""
    out: dict[str, dict[str, str]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if (row.get("CURRENCY_DENOM") or "EUR") != "EUR":
            continue
        month = (row.get("TIME_PERIOD") or "").strip()
        ccy = (row.get("CURRENCY") or "").strip().upper()
        raw = (row.get("OBS_VALUE") or "").strip()
        if not _MONTH.fullmatch(month) or not _CCY.fullmatch(ccy):
            continue
        try:
            if not Decimal(raw) > 0:
                continue
        except (InvalidOperation, ValueError):
            continue
        out.setdefault(month, {})[ccy] = raw
    return out


def fetch_monthly(start: str, end: str, *, timeout: float = FETCH_TIMEOUT_S) -> dict[str, dict[str, str]]:
    """One ECB request for every currency's monthly average, start..end
    inclusive. Raises on a network or HTTP failure; `rates_for_months` is the
    fail-open wrapper the app calls. Tests replace this function."""
    url = (
        f"{ECB_MONTHLY_URL}?startPeriod={start}&endPeriod={end}"
        "&format=csvdata&detail=dataonly"
    )
    req = urllib.request.Request(url, headers={"Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
        return parse_csv(resp.read().decode("utf-8", errors="replace"))


def rates_for_months(months, *, today: date | None = None) -> dict[str, dict[str, str]]:
    """The published monthly averages covering `months`, or {} on any failure.

    Months after the current one are dropped before asking (nothing is
    published for them). The span is fetched in one request."""
    if not enabled():
        return {}
    wanted = sorted({m for m in months if _MONTH.fullmatch(str(m or ""))})
    if not wanted:
        return {}
    now = (today or date.today()).strftime("%Y-%m")
    wanted = [m for m in wanted if month_index(m) <= month_index(now)]
    if not wanted:
        return {}
    try:
        return fetch_monthly(wanted[0], wanted[-1])
    except Exception as exc:  # noqa: BLE001 - fail-open: the ECB never blocks a month
        logger.warning("ECB monthly rates unavailable for %s..%s: %s", wanted[0], wanted[-1], exc)
        return {}
