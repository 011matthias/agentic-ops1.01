"""Daily FX reference rates, polled from OpenTickers (feedback note #79).

Owner directive 2026-09-23, anchored on Settings > FX reference rates: "fx
rates should be polled daily via open tickers API". OpenTickers
(https://opentickers.com, `api.opentickers.com/api/public/exchange_rates`)
aggregates central-bank reference rates; `/latest` answers one record per
source for a pair and `/historical` a date range (the account's plan allows
it, checked 2026-09-23: 200 with ECB daily rates for September; the public
page's "free accounts are limited to /latest" did not apply to this key).

Rates are stored the way the ECB monthly table is (item 82): units of each
currency per ONE EUR, the provider's own digits as text, keyed by the rate's
effective day. The matcher crosses through EUR for the CHARGE's own date
(`MatchingConfig.daily_rate`), the grain a card network locks the rate at
(authorization), one rung above the ECB monthly average and below a typed
Settings rate and the run's self-derived rates.

Source per (day, currency): the ECB record when the provider carries one
(the same series the monthly table averages, `D.{CCY}.EUR.SP00.A`), else the
median of the `mid` records the other sources give. A record whose
`scalingFactor` is not 1, whose value is not positive, or whose day or
currency is malformed is skipped, never guessed at.

The poll is one daemon thread, the backup scheduler's shape: at boot and
every 24 h it fetches the latest record for every currency the estate needs
(`needed_currencies`) and, once, backfills the days the live months span
through `/historical`. Fail-open by contract: a fetch that fails, or a plan
that refuses `/historical`, leaves the table as it was and the next round
tries again; no month creation, attach or re-match ever waits on the
provider. Off when `OPENTICKERS_API_KEY` is unset or `EXPENSE_RECON_FX_POLL=0`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

OPENTICKERS_URL = "https://api.opentickers.com/api/public/exchange_rates"
FETCH_TIMEOUT_S = 6.0
POLL_INTERVAL_S = 24 * 3600.0
# Currencies the estate reconciles in besides the euro the table is quoted
# against: every live card settles in USD and the Brazilian receipts are BRL.
# `needed_currencies` grows the set from Settings and the live months.
DEFAULT_CURRENCIES = ("USD", "BRL")
PREFERRED_SOURCE = "ECB"
HISTORY_PAGE = 100
# With no month to anchor on, how far back the first backfill reaches.
BACKFILL_DEFAULT_DAYS = 90

META_BACKFILLED_FROM = "backfilled_from"
META_LAST_FETCHED_AT = "last_fetched_at"
META_LAST_ERROR = "last_error"
META_HISTORY_REFUSED = "history_refused"

_DAY = re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
_CCY = re.compile(r"[A-Z]{3}")


def api_key() -> str:
    return os.environ.get("OPENTICKERS_API_KEY", "").strip()


def enabled() -> bool:
    return bool(api_key()) and os.environ.get(
        "EXPENSE_RECON_FX_POLL", "1"
    ).strip() != "0"


class HistoryRefused(Exception):
    """The account's plan does not include `/historical` (HTTP 403)."""


# ── the provider ──────────────────────────────────────────────────────────


def _get(path: str, params: dict, *, key: str, timeout: float):
    url = f"{OPENTICKERS_URL}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_latest(
    currency: str, *, key: str, timeout: float = FETCH_TIMEOUT_S
) -> list[dict]:
    """Every source's newest EUR->`currency` record. Raises on a network or
    HTTP failure; `poll_once` is the fail-open caller. Tests replace this."""
    body = _get(
        "latest",
        {"base_currency": "EUR", "quote_currency": currency},
        key=key, timeout=timeout,
    )
    return list(body) if isinstance(body, list) else []


def fetch_historical(
    currency: str, start: str, end: str, *, key: str,
    timeout: float = FETCH_TIMEOUT_S,
) -> list[dict]:
    """Every source's EUR->`currency` records for start..end inclusive, all
    pages. Raises `HistoryRefused` on the plan's 403, else as `fetch_latest`.
    Tests replace this."""
    out: list[dict] = []
    offset = 0
    while True:
        try:
            body = _get(
                "historical",
                {
                    "start_date": start, "end_date": end,
                    "base_currency": "EUR", "quote_currency": currency,
                    "limit": HISTORY_PAGE, "offset": offset,
                },
                key=key, timeout=timeout,
            )
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise HistoryRefused(
                    "the OpenTickers plan does not include /historical"
                ) from exc
            raise
        data = list((body or {}).get("data") or []) if isinstance(body, dict) else []
        out.extend(data)
        total = int((((body or {}).get("metadata") or {}).get("total") or 0)) if isinstance(body, dict) else 0
        offset += len(data)
        if not data or offset >= total:
            return out


# ── the table ─────────────────────────────────────────────────────────────


def pick(records) -> list[tuple[str, str, str, str]]:
    """Store rows `(day, currency, units per EUR, source)` from provider
    records, one per (day, currency).

    The ECB record wins when present; otherwise the median of the other
    sources' `mid` values, and the source names them (`median:BCCR,BDI`).
    Values keep the provider's digits as text. A record with another base
    currency, a scaling factor other than 1, a non-positive value or a
    malformed day / currency is skipped."""
    grouped: dict[tuple[str, str], dict[str, list[Decimal]]] = {}
    for rec in records or ():
        if not isinstance(rec, dict):
            continue
        if str(rec.get("baseCurrency") or "").upper() != "EUR":
            continue
        day = str(rec.get("effectiveDate") or "")[:10]
        ccy = str(rec.get("quoteCurrency") or "").upper().strip()
        source = str(rec.get("sourceCode") or "").upper().strip() or "?"
        if not _DAY.fullmatch(day) or not _CCY.fullmatch(ccy) or ccy == "EUR":
            continue
        try:
            scale = Decimal(str(rec.get("scalingFactor", 1)))
            value = Decimal(str(rec.get("value")))
        except (InvalidOperation, ValueError, TypeError):
            continue
        if scale != 1 or not value > 0 or not value.is_finite():
            continue
        if source != PREFERRED_SOURCE and str(rec.get("type") or "mid").lower() != "mid":
            continue
        grouped.setdefault((day, ccy), {}).setdefault(source, []).append(value)
    rows: list[tuple[str, str, str, str]] = []
    for (day, ccy), by_source in sorted(grouped.items()):
        if PREFERRED_SOURCE in by_source:
            value, source = by_source[PREFERRED_SOURCE][0], PREFERRED_SOURCE
        else:
            values = sorted(v for vals in by_source.values() for v in vals)
            value = Decimal(statistics.median(values))
            source = "median:" + ",".join(sorted(by_source))
        rows.append((day, ccy, format(value.normalize(), "f"), source))
    return rows


def as_table(rows) -> dict[str, dict[str, str]]:
    """`{day: {currency: units per EUR}}` from store rows."""
    out: dict[str, dict[str, str]] = {}
    for day, ccy, per_eur, _source in rows:
        out.setdefault(day, {})[ccy] = per_eur
    return dict(sorted(out.items()))


def needed_currencies(settings: dict | None, runs=()) -> list[str]:
    """The currencies to poll, besides EUR: the defaults, every card
    currency in Settings, and the statement currency of every month.
    Sorted, EUR excluded.

    A rate typed in Settings used to name currencies here too. That key
    was retired on 2026-09-23 (item 168) and is stripped from the stored
    settings, so the cards and the months are what the poll follows."""
    want = set(DEFAULT_CURRENCIES)
    settings = settings or {}
    for entry in (settings.get("cards") or {}).values():
        if isinstance(entry, dict):
            ccy = str(entry.get("currency") or "").upper().strip()
            if _CCY.fullmatch(ccy):
                want.add(ccy)
    for run in runs or ():
        cfg = getattr(run, "config", None) or {}
        stmt = cfg.get("statement") if isinstance(cfg, dict) else None
        ccy = str((stmt or {}).get("account_card_currency") or "").upper().strip()
        if _CCY.fullmatch(ccy):
            want.add(ccy)
    want.discard("EUR")
    return sorted(want)


def backfill_start(runs, today: date) -> str:
    """The first day the table should cover: the month before the earliest
    labelled month (a charge on the 1st reads the last fix of the month
    before), else `BACKFILL_DEFAULT_DAYS` back from today."""
    from ..batch_period import month_from_label

    months = [
        m for m in (month_from_label(getattr(r, "label", None)) for r in runs or ())
        if m is not None
    ]
    if months:
        y, m = min(months)
        idx = y * 12 + (m - 1) - 1
        return f"{idx // 12:04d}-{idx % 12 + 1:02d}-01"
    return (today - timedelta(days=BACKFILL_DEFAULT_DAYS)).isoformat()


# ── the poll ──────────────────────────────────────────────────────────────


def poll_once(
    store, *, today: date | None = None, currencies=None,
    now_iso: str | None = None,
) -> dict:
    """One round: backfill once (the days the live months span, when the
    table does not reach them yet and the plan allows it), then the latest
    record for every needed currency. Stores what came back, records the
    round in the meta rows, and answers a summary the route and the log
    print. Never raises for a provider failure."""
    key = api_key()
    if not enabled():
        return {
            "ok": False,
            "code": "fx_poll_disabled",
            "reason": (
                "OPENTICKERS_API_KEY is not set" if not key
                else "EXPENSE_RECON_FX_POLL=0"
            ),
        }
    today = today or date.today()
    now_iso = now_iso or datetime.now(timezone.utc).isoformat(timespec="seconds")
    settings = store.get_settings()
    runs = store.list_runs()
    currencies = list(currencies or needed_currencies(settings, runs))
    rows: list[tuple[str, str, str, str]] = []
    errors: list[str] = []

    start = backfill_start(runs, today)
    done_from = store.get_fx_meta(META_BACKFILLED_FROM)
    backfilled = None
    if not store.get_fx_meta(META_HISTORY_REFUSED) and (
        done_from is None or done_from > start
    ):
        try:
            for ccy in currencies:
                rows.extend(pick(fetch_historical(
                    ccy, start, today.isoformat(), key=key,
                )))
            store.set_fx_meta(META_BACKFILLED_FROM, start)
            backfilled = start
        except HistoryRefused as exc:
            store.set_fx_meta(META_HISTORY_REFUSED, now_iso)
            errors.append(f"history: {exc}")
        except Exception as exc:  # noqa: BLE001 - fail-open, the next round retries
            errors.append(f"history: {exc}")

    for ccy in currencies:
        try:
            rows.extend(pick(fetch_latest(ccy, key=key)))
        except Exception as exc:  # noqa: BLE001 - fail-open, the next round retries
            errors.append(f"latest {ccy}: {exc}")

    n_stored = store.upsert_fx_daily_rates(rows, now_iso) if rows else 0
    if rows:
        store.set_fx_meta(META_LAST_FETCHED_AT, now_iso)
    store.set_fx_meta(META_LAST_ERROR, "; ".join(errors))
    status = store.fx_daily_rates_status()
    return {
        "ok": n_stored > 0 or not errors,
        "n_stored": n_stored,
        "currencies": currencies,
        "backfilled_from": backfilled,
        "errors": errors,
        "fetched_at": now_iso if rows else store.get_fx_meta(META_LAST_FETCHED_AT),
        **status,
    }


def settings_view(store) -> dict:
    """The derived `fx_daily_rates` block of `GET /api/settings`: the poll's
    state and the newest day's rates, as units per EUR and as every ordered
    pair among the polled currencies and EUR (six decimals, the precision a
    typed rate carries), so the screen can set them beside the typed ones."""
    status = store.fx_daily_rates_status()
    latest: dict = {}
    last_day = status.get("last_day")
    if last_day:
        per_eur = (store.fx_daily_rates(last_day, last_day).get(last_day)) or {}
        ccys = sorted(set(per_eur) | {"EUR"})
        pairs: dict[str, str] = {}
        for src in ccys:
            for dst in ccys:
                if src == dst:
                    continue
                u_src = Decimal(1) if src == "EUR" else Decimal(per_eur[src])
                u_dst = Decimal(1) if dst == "EUR" else Decimal(per_eur[dst])
                if u_src <= 0 or u_dst <= 0:
                    continue
                pairs[f"{src}:{dst}"] = format(
                    (u_dst / u_src).quantize(Decimal("0.000001")), "f"
                )
        latest = {"day": last_day, "per_eur": dict(per_eur), "pairs": pairs}
    return {
        "provider": "opentickers",
        "enabled": enabled(),
        "poll_interval_hours": int(POLL_INTERVAL_S // 3600),
        "last_fetched_at": store.get_fx_meta(META_LAST_FETCHED_AT),
        "last_error": store.get_fx_meta(META_LAST_ERROR) or "",
        "backfilled_from": store.get_fx_meta(META_BACKFILLED_FROM),
        "history_refused": bool(store.get_fx_meta(META_HISTORY_REFUSED)),
        **status,
        "latest": latest,
    }


def start_poll_thread(db_path, *, interval_s: float = POLL_INTERVAL_S):
    """The in-app schedule. None unless `enabled()`; one daemon thread that
    polls at boot and every `interval_s`. A failed round logs and waits for
    the next one; a round never kills the app."""
    if not enabled():
        return None
    from .store import RunStore

    def _loop() -> None:
        while True:
            try:
                with RunStore(db_path) as store:
                    result = poll_once(store)
                if result.get("errors"):
                    logger.warning("fx poll: %s", "; ".join(result["errors"]))
                else:
                    logger.info(
                        "fx poll stored %s rate(s), table %s..%s (%s days)",
                        result.get("n_stored"), result.get("first_day"),
                        result.get("last_day"), result.get("n_days"),
                    )
            except Exception:  # noqa: BLE001 - a poll never kills the app
                logger.exception("fx poll failed")
            time.sleep(max(60.0, interval_s))

    thread = threading.Thread(
        target=_loop, daemon=True, name="expense-recon-fx-poll"
    )
    thread.start()
    logger.info("fx poll on, every %s h", int(interval_s // 3600))
    return thread
