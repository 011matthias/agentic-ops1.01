"""`expense-recon memory` — inspect / forget / reset the learning store
(Phase 2 PR 2d). The escape hatch: stale or wrong learned data is a real
failure mode, so Chris can correct it without hand-editing SQLite. This
lands BEFORE any consult path (2b/2c) reads the store.

    expense-recon memory list [--entity brisken-llc]
    expense-recon memory forget "Coffee Shop NYC" [--entity brisken-llc]
    expense-recon memory reset [--table merchant_category] [--entity X]   # preview
    expense-recon memory reset --yes                                      # apply
    expense-recon memory set "Anthropic" --entity "Corporate Services" \
        --category "Software & Subscriptions" \
        --account "Other Infra and IT Costs for Cloud Business"          # standing rule

The store defaults to `<EXPENSE_RECON_WEB_DATA>/learning.sqlite` (same dir
the web workbench writes), overridable with `--db PATH`. A vendor argument
is normalized the same way the matcher and the store normalize keys, so
you type the name as you see it.

The one-time `seed-zoho` importer (which read a Books posting history to
teach the store its first 103 rows) was removed 2026-08-22 with the rest of
the accounting-API connection. Those rows live on in the store and are
edited in the app; new rows come from the reviewer's own corrections.

`set` (Slice 10) authors ONE standing vendor -> category/account rule
directly, for a vendor the store has never seen (the canonical
case: Anthropic -> "Other Infra and IT Costs for Cloud Business", a
standing instruction from Nicolas). The rule lands as a normal
merchant_category row (source_run "manual-set"), so the charge categorizer
recalls it as Tier-1 LEARNED and `forget` / `reset` correct it the same
way as any learned row.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .learning import LearningStore, normalize_vendor
from .matching.types import EXPENSE_CATEGORIES

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

    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "forget":
        return cmd_forget(args)
    if args.command == "reset":
        return cmd_reset(args)
    if args.command == "set":
        return cmd_set(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
