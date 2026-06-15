"""`expense-recon memory` — inspect / forget / reset the learning store
(Phase 2 PR 2d). The escape hatch: stale or wrong learned data is a real
failure mode, so Chris can correct it without hand-editing SQLite. This
lands BEFORE any consult path (2b/2c) reads the store.

    expense-recon memory list [--entity brisken-llc]
    expense-recon memory forget "Coffee Shop NYC" [--entity brisken-llc]
    expense-recon memory reset [--table merchant_category] [--entity X]   # preview
    expense-recon memory reset --yes                                      # apply

The store defaults to `<EXPENSE_RECON_WEB_DATA>/learning.sqlite` (same dir
the web workbench writes), overridable with `--db PATH`. A vendor argument
is normalized the same way the matcher and the store normalize keys, so
you type the name as you see it.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .learning import LearningStore, normalize_vendor

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

    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "forget":
        return cmd_forget(args)
    if args.command == "reset":
        return cmd_reset(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
