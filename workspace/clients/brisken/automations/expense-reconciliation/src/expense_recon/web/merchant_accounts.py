"""Items 180/181, the read side of a merchant's account per company.

`settings["merchants"][name]["accounts"]` holds codes only (`merchant_registry`).
What a person editing it needs beside the codes is served here, derived and
read-only on `GET /api/settings`:

- `merchant_accounts`: per merchant, each company's code with that company's
  own name for it and whether it may post there. A code is one account in
  every company, but its NAME is per company, so the name is looked up at read
  time and never stored.
- `account_companies`: one row per company the curated chart covers, so a
  picker shows each company once (the app holds two spellings of each).
- `needs_account`: registry merchants that were booked to a company in a GL
  month while their map names no account for that company. This is the list
  of gaps that sends rows to the model or to a refusal; Dirk fills it.

Chart reads go through `category_vocabulary` (`web/` may not import
`..zoho`). The bookings come from the same payload the month's grid renders,
so "the company this row was booked to" is the company Criss sees, card chain
included, never a second resolver that could disagree with it.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable

from ..categorize_charges import build_charge_pseudo_receipt
from ..category_vocabulary import gl_companies, gl_leaf_status, gl_postable_ref
from ..coa_provision import GL_ENTITY_ORGS_KEY, org_id_for_entity
from ..merchant_registry import MerchantRegistry, company_account
from .serialize import snapshot_from_dict

__all__ = [
    "collect_gl_bookings",
    "merchant_accounts_view",
    "needs_account",
    "settings_account_fields",
]

# Building a month's grid is the expensive part, and the Settings page reads
# settings often. The list is advisory (it names gaps for a person to fill),
# so a month's bookings may be up to this old; the map filter below is applied
# fresh on every read, so a saved account leaves the list at once.
BOOKINGS_TTL_S = 120.0
_BOOKINGS_CACHE: dict[tuple[str, str], tuple[float, list[dict]]] = {}


def _entity_orgs(companies: list[dict]) -> dict[str, str]:
    return {lbl: c["org_id"] for c in companies for lbl in c["labels"]}


def _company_label(companies: list[dict], org_id: str | None, fallback: str) -> str:
    for c in companies:
        if c["org_id"] == org_id:
            return c["label"]
    return fallback


def merchant_accounts_view(
    settings: dict | None, companies: list[dict],
) -> dict[str, list[dict]]:
    """`{merchant: [{company, label, org_id, code, name, postable, reason}]}`
    for every merchant carrying a map. `label` is the key as stored,
    `company` the one spelling the pickers use."""
    entity_orgs = _entity_orgs(companies)
    out: dict[str, list[dict]] = {}
    for name, entry in sorted(((settings or {}).get("merchants") or {}).items()):
        accounts = entry.get("accounts") if isinstance(entry, dict) else None
        if not isinstance(accounts, dict) or not accounts:
            continue
        rows = []
        for label, code in sorted(accounts.items()):
            org_id = org_id_for_entity(label, entity_orgs)
            rows.append({
                "company": _company_label(companies, org_id, label),
                "label": label,
                "org_id": org_id or "",
                **gl_leaf_status(code, org_id),
            })
        out[name] = rows
    return out


def _covered(entry: dict, org_id: str, entity_orgs: dict[str, str]) -> bool:
    """Does the registry already give this merchant an account in this
    company? Its per-company map, or else its single `zoho_account` or its
    default category naming a leaf this company can post to: the same refs
    the engine's registry tier tries, in the same org-scoped resolution.
    Live, the Brazilian food merchants carry `E100010-31 - Travel Expense |
    Food` and book through it; listing them would bury the real gaps."""
    if company_account(entry.get("accounts") or {}, org_id, entity_orgs):
        return True
    return any(
        gl_postable_ref(ref, org_id)
        for ref in (entry.get("zoho_account"), entry.get("category"))
    )


def needs_account(
    settings: dict | None, bookings: Iterable[dict], companies: list[dict],
) -> list[dict]:
    """Registry merchants booked to a company whose map entry is missing.

    One row per (merchant, company): `{merchant, company, org_id, n_rows,
    months}`. A `multi_category` merchant is left out (it is judged per
    receipt by design), and so is a company outside the curated chart, which
    no account could fix."""
    merchants = (settings or {}).get("merchants") or {}
    entity_orgs = _entity_orgs(companies)
    agg: dict[tuple[str, str], dict] = {}
    for b in bookings:
        entry = merchants.get(b.get("merchant") or "")
        if not isinstance(entry, dict) or entry.get("multi_category"):
            continue
        org_id = org_id_for_entity(b.get("company"), entity_orgs)
        if not org_id:
            continue
        if _covered(entry, org_id, entity_orgs):
            continue
        key = (b["merchant"], org_id)
        row = agg.setdefault(key, {
            "merchant": b["merchant"],
            "company": _company_label(companies, org_id, b.get("company") or ""),
            "org_id": org_id,
            "n_rows": 0,
            "months": set(),
        })
        row["n_rows"] += 1
        if b.get("month"):
            row["months"].add(b["month"])
    return [
        {**row, "months": sorted(row["months"])}
        for _key, row in sorted(agg.items(), key=lambda kv: (kv[0][0].lower(), kv[1]["company"]))
    ]


def _run_bookings(run, view: dict, registry: MerchantRegistry) -> list[dict]:
    """The registry merchants one GL month booked, per row: its receipts as
    the grid shows them, then its receiptless charges as `categorize_charges`
    resolves them (the charge's own company, the bank's description)."""
    out: list[dict] = []
    for e in view.get("expenses") or []:
        # Resolved from the row's own vendor, as the engine resolves it,
        # never from `vendor.source`: that flag is stamped at ingest, so a
        # receipt that arrived before its merchant was added reads
        # "extraction" for good (live: 29 of 34 Anthropic rows, July to
        # September 2026).
        vendor = e.get("vendor")
        if isinstance(vendor, dict):
            display, raw = vendor.get("display"), vendor.get("raw")
        else:
            display, raw = vendor, None
        m = registry.resolve(display or None, raw or None)
        if m is not None:
            out.append({
                "merchant": m.canonical_name,
                "company": e.get("legal_entity_id") or "",
                "month": run.label,
                "kind": "receipt",
            })
    try:
        transactions, _receipts, outcome, _issues = snapshot_from_dict(run.snapshot or {})
    except (KeyError, TypeError, ValueError):
        return out
    by_id = {tx.transaction_id: tx for tx in transactions}
    for tx_id in outcome.unmatched_transactions:
        tx = by_id.get(tx_id)
        if tx is None:
            continue
        pseudo = build_charge_pseudo_receipt(tx)
        m = registry.resolve(pseudo.vendor_clean, pseudo.detected_vendor)
        if m is not None:
            out.append({
                "merchant": m.canonical_name,
                "company": pseudo.legal_entity_id or "",
                "month": run.label,
                "kind": "charge",
            })
    return out


def collect_gl_bookings(
    runs: Iterable, view_of: Callable[[object], dict], settings: dict | None,
    *, cache_key: str = "",
) -> list[dict]:
    """Every registry-merchant booking across the GL months. `view_of(run)`
    is the month's expense payload (the app's `_expense_view`). A month that
    fails to render is skipped, never a reason for Settings to fail."""
    registry = MerchantRegistry.from_settings(settings)
    now = time.monotonic()
    out: list[dict] = []
    for run in runs:
        if GL_ENTITY_ORGS_KEY not in (run.config or {}):
            continue
        key = (cache_key, run.run_id)
        hit = _BOOKINGS_CACHE.get(key)
        if hit is not None and now - hit[0] < BOOKINGS_TTL_S:
            out.extend(hit[1])
            continue
        try:
            rows = _run_bookings(run, view_of(run), registry)
        except Exception:  # noqa: BLE001 - one month must not blank Settings
            continue
        _BOOKINGS_CACHE[key] = (now, rows)
        out.extend(rows)
    return out


def canonical_account_labels(merchants: dict, companies: list[dict]) -> dict:
    """Store each per-company account under the company's one picker
    spelling (`account_companies[].label`, the label receipts carry).

    A GL month resolves a map key to its org through the month's OWN frozen
    entity map, which always holds the provisioning spelling and holds the
    settings registry's long one ("Brisken Cloud Services, LLC") only when
    that entity had an org id the day the month was created. Storing the
    picker spelling keeps a key resolvable in every month. A label no company
    knows is kept as typed (edit order must not matter), and two spellings of
    one company naming different codes are kept as typed too: that is a
    contradiction for a person to settle, and the engine reads it as silent."""
    to_label = {lbl.lower(): c["label"] for c in companies for lbl in c["labels"]}
    out = {}
    for name, entry in merchants.items():
        accounts = entry.get("accounts") if isinstance(entry, dict) else None
        if not accounts:
            out[name] = entry
            continue
        canon: dict[str, str] = {}
        clash = False
        for label, code in accounts.items():
            key = to_label.get(label.strip().lower(), label)
            if canon.get(key, code) != code:
                clash = True
            canon[key] = code
        out[name] = {**entry, "accounts": dict(sorted(
            (accounts if clash else canon).items()))}
    return out


def settings_account_fields(
    settings: dict | None, bookings: Iterable[dict] | None,
) -> dict:
    """The derived keys `GET /api/settings` adds for items 180/181."""
    companies = gl_companies(settings)
    return {
        "account_companies": companies,
        "merchant_accounts": merchant_accounts_view(settings, companies),
        "needs_account": needs_account(settings, bookings or [], companies),
    }
