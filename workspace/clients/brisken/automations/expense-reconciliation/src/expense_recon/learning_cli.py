"""`expense-recon memory` — inspect / forget / reset the learning store
(Phase 2 PR 2d). The escape hatch: stale or wrong learned data is a real
failure mode, so Chris can correct it without hand-editing SQLite. This
lands BEFORE any consult path (2b/2c) reads the store.

    expense-recon memory list [--entity brisken-llc]
    expense-recon memory forget "Coffee Shop NYC" [--entity brisken-llc]
    expense-recon memory reset [--table merchant_category] [--entity X]   # preview
    expense-recon memory reset --yes                                      # apply
    expense-recon memory seed-zoho --entity "Corporate Services" --org 822741658 \
        [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--dry-run]             # L2 seed
    expense-recon memory set "Anthropic" --entity "Corporate Services" \
        --category "Software & Subscriptions" \
        --account "Other Infra and IT Costs for Cloud Business"          # standing rule

The store defaults to `<EXPENSE_RECON_WEB_DATA>/learning.sqlite` (same dir
the web workbench writes), overridable with `--db PATH`. A vendor argument
is normalized the same way the matcher and the store normalize keys, so
you type the name as you see it.

`seed-zoho` (L2) teaches merchant memory from Zoho Books posting history:
each Books expense record carries vendor_name + account_name (the account
it was actually posted to), so a vendor whose records all agree on ONE
account becomes a learned row with `zoho_account` = the real Books account
name and `category` = a keyword-mapped one of the tool's 8 categories.
Runs DEV-SIDE only (Zoho creds from the gitignored client context/.env,
never on the server).

`set` (Slice 10) authors ONE standing vendor -> category/account rule
directly, for a vendor that has no Zoho posting history yet (the canonical
case: Anthropic -> "Other Infra and IT Costs for Cloud Business", a
standing instruction from Nicolas). The rule lands as a normal
merchant_category row (source_run "manual-set"), so the charge categorizer
recalls it as Tier-1 LEARNED and `forget` / `reset` correct it the same
way as any learned row.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from .learning import LearningStore, normalize_vendor
from .matching.types import EXPENSE_CATEGORIES
from .zoho.client import ZohoAPIError, ZohoAuthError, ZohoClient, ZohoConfig

_DEFAULT_DATA = "recon-web-data"


def _resolve_db(args) -> Path:
    if getattr(args, "db", None):
        return Path(args.db).resolve()
    data_root = os.environ.get("EXPENSE_RECON_WEB_DATA", _DEFAULT_DATA)
    return (Path(data_root) / "learning.sqlite").resolve()


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", type=Path, help="path to learning.sqlite directly")
    p.add_argument("--entity", help="restrict to one legal_entity_id")


def cmd_list(args) -> int:
    db = _resolve_db(args)
    if not db.exists():
        print(f"no learned memory yet ({db} not found)")
        return 0
    entity = args.entity
    with LearningStore(db) as s:
        cats = s.all_merchant_categories(entity)
        aliases = s.get_vendor_aliases(entity)
        fx = s.all_merchant_fx(entity)

    scope = entity or "all entities"
    print(f"LEARNED MEMORY  ({scope})  db: {db}\n")

    print(f"merchant_category ({len(cats)}):")
    for c in cats:
        acct = f"  [{c.zoho_account}]" if c.zoho_account else ""
        ent = f"  {{{c.legal_entity_id}}}" if entity is None else ""
        print(
            f"  {c.vendor_norm:28} -> {c.category or '(none)'}{acct}"
            f"  (x{c.decision_count}, last {c.last_confirmed_at or '-'}){ent}"
        )

    print(f"\nvendor_alias ({len(aliases)}):")
    for a in aliases:
        ent = f"  {{{a.legal_entity_id}}}" if entity is None else ""
        print(f"  {a.stmt_vendor_norm:28} == {a.receipt_vendor_norm}  (x{a.confirmed_count}){ent}")

    print(f"\nmerchant_fx ({len(fx)}):")
    for f in fx:
        ent = f"  {{{f.legal_entity_id}}}" if entity is None else ""
        mean = f"{f.mean:.4f}" if f.mean is not None else "-"
        lo = f"{f.min:.4f}" if f.min is not None else "-"
        hi = f"{f.max:.4f}" if f.max is not None else "-"
        print(f"  {f.vendor_norm:24} {f.from_ccy}->{f.to_ccy}  mean {mean} [{lo}, {hi}] n={f.count}{ent}")
    return 0


def cmd_forget(args) -> int:
    db = _resolve_db(args)
    if not db.exists():
        print(f"no learned memory yet ({db} not found)", file=sys.stderr)
        return 1
    if not args.entity:
        print("forget needs --entity (the legal_entity_id the vendor was learned under)", file=sys.stderr)
        return 2
    vendor_norm = normalize_vendor(args.vendor)
    if not vendor_norm:
        print(f"vendor {args.vendor!r} normalizes to empty; nothing to forget", file=sys.stderr)
        return 2
    with LearningStore(db) as s:
        counts = s.forget_vendor(args.entity, vendor_norm)
    total = sum(counts.values())
    if total == 0:
        print(f"nothing learned for vendor '{vendor_norm}' in {args.entity}")
        return 0
    print(
        f"forgot '{vendor_norm}' in {args.entity}: "
        f"{counts['merchant_category']} category, "
        f"{counts['vendor_alias']} alias, {counts['merchant_fx']} fx row(s)"
    )
    return 0


def cmd_reset(args) -> int:
    db = _resolve_db(args)
    if not db.exists():
        print(f"no learned memory yet ({db} not found)")
        return 0
    try:
        with LearningStore(db) as s:
            if not args.yes:
                preview = s.count_rows(args.entity)
                scope = args.entity or "all entities"
                tables = [args.table] if args.table else list(preview)
                print(f"reset would delete (scope: {scope}):")
                for t in tables:
                    print(f"  {t}: {preview.get(t, 0)} row(s)")
                print("\nre-run with --yes to apply.")
                return 0
            counts = s.reset(args.table, args.entity)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("reset done: " + ", ".join(f"{t} {n}" for t, n in counts.items()))
    return 0


def cmd_set(args) -> int:
    """Author one standing vendor -> category/account rule (Slice 10)."""
    if args.category not in EXPENSE_CATEGORIES:
        print(
            f"ERROR: category {args.category!r} is not one of the tool's "
            f"{len(EXPENSE_CATEGORIES)} categories:",
            file=sys.stderr,
        )
        for c in EXPENSE_CATEGORIES:
            print(f"  {c}", file=sys.stderr)
        return 2
    vendor_norm = normalize_vendor(args.vendor)
    if not vendor_norm:
        print(
            f"vendor {args.vendor!r} normalizes to empty; nothing to set",
            file=sys.stderr,
        )
        return 2
    db = _resolve_db(args)
    db.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    with LearningStore(db) as s:
        s.record_merchant_category(
            args.entity, vendor_norm, args.category, args.account, now, "manual-set"
        )
    acct = f"  [{args.account}]" if args.account else ""
    print(
        f"set '{vendor_norm}' -> {args.category}{acct}  (entity: {args.entity})\n"
        f"db: {db}"
    )
    if not args.account:
        print(
            "note: no --account given; the rule carries the category only. "
            "Add --account with the real Zoho Books account name to make the "
            "charge postable through the COA gate."
        )
    return 0


# -- seed-zoho (L2): teach memory from Zoho Books posting history ---------

# Account-name KEYWORD -> one of the 8 EXPENSE_CATEGORIES
# (matching.types.EXPENSE_CATEGORIES). Matched as whole words in the Books
# account name, in insertion order, so the specific signals sit above the
# generic ones ("Office Rent" hits "rent" -> premises before "office").
# An account name with no keyword hit is NOT seeded (never invent a
# category); the run reports the distinct unmapped names so the operator
# can extend this map.
ACCOUNT_TO_CATEGORY: dict[str, str] = {
    # Travel & Transport
    "travel": "Travel & Transport",
    "transport": "Travel & Transport",
    "transportation": "Travel & Transport",
    "mileage": "Travel & Transport",
    "vehicle": "Travel & Transport",
    # Meals & Entertainment
    "meals": "Meals & Entertainment",
    "meal": "Meals & Entertainment",
    "entertainment": "Meals & Entertainment",
    # Utilities & Premises (before the generic "office")
    "rent": "Utilities & Premises",
    "utilities": "Utilities & Premises",
    "electricity": "Utilities & Premises",
    "water": "Utilities & Premises",
    "insurance": "Utilities & Premises",
    "telephone": "Utilities & Premises",
    # Software & Subscriptions
    "software": "Software & Subscriptions",
    "subscription": "Software & Subscriptions",
    "subscriptions": "Software & Subscriptions",
    "saas": "Software & Subscriptions",
    "cloud": "Software & Subscriptions",
    "infra": "Software & Subscriptions",
    "infrastructure": "Software & Subscriptions",
    "it": "Software & Subscriptions",
    "internet": "Software & Subscriptions",
    "hosting": "Software & Subscriptions",
    # Equipment & Hardware
    "equipment": "Equipment & Hardware",
    "hardware": "Equipment & Hardware",
    "computer": "Equipment & Hardware",
    "computers": "Equipment & Hardware",
    "furniture": "Equipment & Hardware",
    # Marketing & Advertising
    "marketing": "Marketing & Advertising",
    "advertising": "Marketing & Advertising",
    "selling": "Marketing & Advertising",
    "promotion": "Marketing & Advertising",
    # Professional Services
    "professional": "Professional Services",
    "legal": "Professional Services",
    "consulting": "Professional Services",
    "consultant": "Professional Services",
    "consultancy": "Professional Services",
    "accounting": "Professional Services",
    "audit": "Professional Services",
    "bank": "Professional Services",
    "fees": "Professional Services",
    # Office Supplies & Consumables (generic words last)
    "supplies": "Office Supplies & Consumables",
    "stationery": "Office Supplies & Consumables",
    "printing": "Office Supplies & Consumables",
    "postage": "Office Supplies & Consumables",
    "office": "Office Supplies & Consumables",
    "admin": "Office Supplies & Consumables",
    "administrative": "Office Supplies & Consumables",
}

_ACCOUNT_WORD_RE = re.compile(r"[a-z]+")

# Per-data-center default domains when ZOHO_API_DOMAIN / ZOHO_ACCOUNTS_DOMAIN
# are not set explicitly. Brisken's tenant is EU, hence the default.
_ZOHO_DC_DOMAINS: dict[str, tuple[str, str]] = {
    "us": ("https://www.zohoapis.com", "https://accounts.zoho.com"),
    "eu": ("https://www.zohoapis.eu", "https://accounts.zoho.eu"),
    "in": ("https://www.zohoapis.in", "https://accounts.zoho.in"),
    "au": ("https://www.zohoapis.com.au", "https://accounts.zoho.com.au"),
}


def _map_account_to_category(account_name: str) -> str | None:
    """First ACCOUNT_TO_CATEGORY keyword appearing as a whole word in the
    account name wins; None when nothing hits (the vendor is then skipped,
    never taught a made-up category)."""
    words = set(_ACCOUNT_WORD_RE.findall(account_name.lower()))
    for keyword, category in ACCOUNT_TO_CATEGORY.items():
        if keyword in words:
            return category
    return None


def _zoho_config_from_env(org_id: str, env: Mapping[str, str] | None = None) -> ZohoConfig:
    """Build the seed's ZohoConfig. Differs from ZohoConfig.from_env in three
    ways: the Books-scoped ZOHO_BOOKS_REFRESH_TOKEN wins over the generic
    ZOHO_REFRESH_TOKEN, the org id comes from --org (not ZOHO_ORG_ID), and
    unset domains derive from ZOHO_DC (default eu, this tenant's DC)."""
    env = os.environ if env is None else env
    client_id = env.get("ZOHO_CLIENT_ID")
    client_secret = env.get("ZOHO_CLIENT_SECRET")
    refresh_token = env.get("ZOHO_BOOKS_REFRESH_TOKEN") or env.get("ZOHO_REFRESH_TOKEN")
    missing = [
        var
        for var, val in (
            ("ZOHO_CLIENT_ID", client_id),
            ("ZOHO_CLIENT_SECRET", client_secret),
            ("ZOHO_BOOKS_REFRESH_TOKEN (or ZOHO_REFRESH_TOKEN)", refresh_token),
        )
        if not val
    ]
    if missing:
        raise ValueError(
            f"Zoho credentials missing from environment: {', '.join(missing)}"
        )
    dc = (env.get("ZOHO_DC") or "eu").strip().lower()
    default_api, default_accounts = _ZOHO_DC_DOMAINS.get(dc, _ZOHO_DC_DOMAINS["eu"])
    return ZohoConfig(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        org_id=org_id,
        api_domain=env.get("ZOHO_API_DOMAIN") or default_api,
        accounts_domain=env.get("ZOHO_ACCOUNTS_DOMAIN") or default_accounts,
    )


def _make_zoho_client(config: ZohoConfig) -> ZohoClient:
    """Client factory, a seam so tests inject a fake without network I/O."""
    return ZohoClient(config)


def cmd_seed_zoho(args) -> int:
    db = _resolve_db(args)
    try:
        config = _zoho_config_from_env(args.org)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    client = _make_zoho_client(config)
    try:
        expenses = client.list_expenses(date_start=args.since, date_end=args.until)
    except (ZohoAuthError, ZohoAPIError) as exc:
        print(f"ERROR: Zoho Books fetch failed: {exc}", file=sys.stderr)
        return 1

    # Group by normalized vendor. A vendor is teachable only when every
    # posted record agrees on ONE account name (mirrors learn_from_run:
    # never teach ambiguous facts).
    accounts_by_vendor: dict[str, set[str]] = {}
    skipped_no_vendor = 0
    for rec in expenses:
        vendor = rec.get("vendor_name")
        vnorm = normalize_vendor(vendor) if vendor else ""
        if not vnorm:
            skipped_no_vendor += 1
            continue
        accounts = accounts_by_vendor.setdefault(vnorm, set())
        if rec.get("account_name"):
            accounts.add(rec["account_name"])

    seeded: list[tuple[str, str, str]] = []  # (vendor_norm, account, category)
    skipped_mixed: list[str] = []
    skipped_unmapped: list[str] = []
    unmapped_accounts: set[str] = set()
    for vnorm in sorted(accounts_by_vendor):
        accounts = accounts_by_vendor[vnorm]
        if len(accounts) > 1:
            skipped_mixed.append(vnorm)
            continue
        if not accounts:
            skipped_unmapped.append(vnorm)
            unmapped_accounts.add("(record carries no account_name)")
            continue
        account = next(iter(accounts))
        category = _map_account_to_category(account)
        if category is None:
            skipped_unmapped.append(vnorm)
            unmapped_accounts.add(account)
            continue
        seeded.append((vnorm, account, category))

    header = "DRY RUN: would seed" if args.dry_run else "seeding"
    print(
        f"{header} {len(seeded)} vendor(s) from {len(expenses)} Zoho Books "
        f"expense record(s) into {db}  (entity: {args.entity})"
    )
    for vnorm, account, category in seeded:
        print(f"  {vnorm:28} -> {category}  [{account}]")

    if not args.dry_run and seeded:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        source_run = f"zoho-seed:{args.org}"
        with LearningStore(db) as s:
            for vnorm, account, category in seeded:
                s.record_merchant_category(
                    args.entity, vnorm, category, account, now, source_run
                )

    print(
        f"\ncounts: seeded {len(seeded)}, skipped_mixed {len(skipped_mixed)}, "
        f"skipped_no_vendor {skipped_no_vendor}, "
        f"skipped_unmapped {len(skipped_unmapped)}"
    )
    if skipped_mixed:
        print("skipped (mixed accounts): " + ", ".join(skipped_mixed))
    if unmapped_accounts:
        print("unmapped account names (extend ACCOUNT_TO_CATEGORY to cover):")
        for name in sorted(unmapped_accounts):
            print(f"  {name}")
    if args.dry_run:
        print("\ndry run: nothing written.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon memory",
        description="Inspect / forget / reset the cross-run learning store.",
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="show learned categories, aliases, and FX")
    _add_common(p_list)

    p_forget = sub.add_parser("forget", help="drop everything learned for one vendor")
    p_forget.add_argument("vendor", help="vendor name (as you see it; normalized internally)")
    _add_common(p_forget)

    p_reset = sub.add_parser("reset", help="delete learned rows (dry-run unless --yes)")
    p_reset.add_argument("--table", choices=LearningStore.TABLES, help="restrict to one table")
    p_reset.add_argument("--yes", action="store_true", help="actually delete (default is preview)")
    _add_common(p_reset)

    p_set = sub.add_parser(
        "set",
        help="author a standing vendor -> category/account rule directly",
    )
    p_set.add_argument("vendor", help="vendor name (as it appears; normalized internally)")
    p_set.add_argument("--category", required=True,
                       help="one of the tool's 8 expense categories (exact)")
    p_set.add_argument("--account",
                       help="Zoho Books account name to post to (recommended)")
    p_set.add_argument("--entity", required=True,
                       help="legal_entity_id the rule applies under")
    p_set.add_argument("--db", type=Path, help="path to learning.sqlite directly")

    p_seed = sub.add_parser(
        "seed-zoho",
        help="seed merchant memory from Zoho Books posting history (dev-side)",
    )
    p_seed.add_argument("--entity", required=True, help="legal_entity_id to seed under")
    p_seed.add_argument("--org", required=True, help="Zoho Books organization_id")
    p_seed.add_argument("--since", help="only expenses dated >= YYYY-MM-DD (inclusive)")
    p_seed.add_argument("--until", help="only expenses dated <= YYYY-MM-DD (inclusive)")
    p_seed.add_argument("--dry-run", action="store_true",
                        help="print what would be seeded; write nothing")
    p_seed.add_argument("--db", type=Path, help="path to learning.sqlite directly")

    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "forget":
        return cmd_forget(args)
    if args.command == "reset":
        return cmd_reset(args)
    if args.command == "set":
        return cmd_set(args)
    if args.command == "seed-zoho":
        return cmd_seed_zoho(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
