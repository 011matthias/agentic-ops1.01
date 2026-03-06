#!/usr/bin/env python3
"""
Airtable Table Cleanup Utility

Provides helper functions for cleaning up Airtable tables during testing.

Usage:
    # Delete all records from a table (with confirmation)
    uv run python scripts/testing-utils/airtable_cleanup.py delete-all \\
        --base-id appXXXXX --table-id tblXXXXX

    # Delete records matching a formula
    uv run python scripts/testing-utils/airtable_cleanup.py delete-matching \\
        --base-id appXXXXX --table-id tblXXXXX \\
        --formula "NOT({Status} = 'active')"

    # Dry run (show what would be deleted)
    uv run python scripts/testing-utils/airtable_cleanup.py delete-all \\
        --base-id appXXXXX --table-id tblXXXXX --dry-run

    # List record count
    uv run python scripts/testing-utils/airtable_cleanup.py count \\
        --base-id appXXXXX --table-id tblXXXXX
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
# ]
# ///

import argparse
import sys
from typing import Any

import httpx


# --- Client ---


class AirtableCleanupClient:
    """Client for Airtable cleanup operations."""

    def __init__(self, api_key: str, base_url: str = "https://api.airtable.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0
        )

    def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make a request to Airtable API."""
        url = f"{self.base_url}/v0{path}"

        response = self.client.request(method, url, **kwargs)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code}", file=sys.stderr)
            print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)

        return response.json()

    def list_records(
        self,
        base_id: str,
        table_id: str,
        filter_by_formula: str | None = None,
        offset: str | None = None,
    ) -> dict[str, Any]:
        """List records from a table."""
        params = {}
        if filter_by_formula:
            params["filterByFormula"] = filter_by_formula
        if offset:
            params["offset"] = offset

        return self._request(
            "GET",
            f"/{base_id}/{table_id}",
            params=params if params else None,
        )

    def list_all_records(
        self,
        base_id: str,
        table_id: str,
        filter_by_formula: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all records, handling pagination."""
        all_records = []
        offset = None

        while True:
            result = self.list_records(
                base_id,
                table_id,
                filter_by_formula=filter_by_formula,
                offset=offset,
            )
            all_records.extend(result.get("records", []))

            offset = result.get("offset")
            if not offset:
                break

        return all_records

    def delete_records(
        self, base_id: str, table_id: str, record_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Delete multiple records (max 10 per request)."""
        all_deleted = []

        # Delete in batches of 10
        for i in range(0, len(record_ids), 10):
            batch = record_ids[i : i + 10]
            result = self._request(
                "DELETE",
                f"/{base_id}/{table_id}",
                params={"records[]": batch},
            )
            all_deleted.extend(result.get("records", []))

        return all_deleted

    def delete_all_records(
        self, base_id: str, table_id: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """Delete all records from a table."""
        records = self.list_all_records(base_id, table_id)
        record_ids = [r["id"] for r in records]

        if dry_run:
            return {
                "deleted": [],
                "would_delete_count": len(record_ids),
                "records": records,
            }

        deleted = self.delete_records(base_id, table_id, record_ids)
        return {
            "deleted": deleted,
            "deleted_count": len(deleted),
        }

    def delete_matching_records(
        self,
        base_id: str,
        table_id: str,
        formula: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Delete records matching a formula."""
        records = self.list_all_records(base_id, table_id, filter_by_formula=formula)
        record_ids = [r["id"] for r in records]

        if dry_run:
            return {
                "deleted": [],
                "would_delete_count": len(record_ids),
                "records": records,
            }

        deleted = self.delete_records(base_id, table_id, record_ids)
        return {
            "deleted": deleted,
            "deleted_count": len(deleted),
        }

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


# --- Utilities ---


def confirm_action(message: str) -> bool:
    """Ask user for confirmation."""
    response = input(f"{message} (yes/no): ").strip().lower()
    return response in ("yes", "y")


def get_env_var(name: str) -> str:
    """Get environment variable or exit."""
    import os

    value = os.getenv(name)
    if not value:
        print(f"Error: {name} environment variable not set", file=sys.stderr)
        sys.exit(1)
    return value


# --- Commands ---


def cmd_count(args: argparse.Namespace) -> None:
    """Count records in a table."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableCleanupClient(api_key)

    try:
        if args.formula:
            records = client.list_all_records(
                args.base_id, args.table_id, filter_by_formula=args.formula
            )
            print(f"Records matching formula: {len(records)}")
        else:
            records = client.list_all_records(args.base_id, args.table_id)
            print(f"Total records in table: {len(records)}")
    finally:
        client.close()


def cmd_delete_all(args: argparse.Namespace) -> None:
    """Delete all records from a table."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableCleanupClient(api_key)

    try:
        # First, get count
        records = client.list_all_records(args.base_id, args.table_id)
        count = len(records)

        if count == 0:
            print("No records to delete.")
            return

        print(f"Found {count} record(s) in table.")

        if args.dry_run:
            print("Dry run mode - would delete the following records:")
            for record in records[:10]:  # Show first 10
                fields = record.get("fields", {})
                name = (
                    fields.get("Name")
                    or fields.get("Title")
                    or fields.get("name")
                    or fields.get("title")
                    or "N/A"
                )
                print(f"  - [{record.get('id')}] {name}")
            if count > 10:
                print(f"  ... and {count - 10} more")
            return

        # Confirm
        if not args.force and not confirm_action(
            f"Delete all {count} record(s) from table?"
        ):
            print("Aborted.")
            return

        # Delete
        result = client.delete_all_records(
            args.base_id, args.table_id, dry_run=False
        )
        print(f"Deleted {result['deleted_count']} record(s).")

    finally:
        client.close()


def cmd_delete_matching(args: argparse.Namespace) -> None:
    """Delete records matching a formula."""
    if not args.formula:
        print("Error: --formula is required for delete-matching", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableCleanupClient(api_key)

    try:
        # First, get matching records
        records = client.list_all_records(
            args.base_id, args.table_id, filter_by_formula=args.formula
        )
        count = len(records)

        if count == 0:
            print("No matching records found.")
            return

        print(f"Found {count} record(s) matching formula.")

        if args.dry_run:
            print("Dry run mode - would delete the following records:")
            for record in records[:10]:  # Show first 10
                fields = record.get("fields", {})
                name = (
                    fields.get("Name")
                    or fields.get("Title")
                    or fields.get("name")
                    or fields.get("title")
                    or "N/A"
                )
                print(f"  - [{record.get('id')}] {name}")
            if count > 10:
                print(f"  ... and {count - 10} more")
            return

        # Confirm
        if not args.force and not confirm_action(
            f"Delete {count} matching record(s) from table?"
        ):
            print("Aborted.")
            return

        # Delete
        result = client.delete_matching_records(
            args.base_id, args.table_id, args.formula, dry_run=False
        )
        print(f"Deleted {result['deleted_count']} record(s).")

    finally:
        client.close()


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Airtable Table Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Count records
  python airtable_cleanup.py count --base-id appXXXXX --table-id tblXXXXX

  # Count records matching a formula
  python airtable_cleanup.py count --base-id appXXXXX --table-id tblXXXXX \\
      --formula "NOT({Status} = 'active')"

  # Delete all records (with confirmation)
  python airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX

  # Delete all records (no confirmation)
  python airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX --force

  # Dry run to see what would be deleted
  python airtable_cleanup.py delete-all --base-id appXXXXX --table-id tblXXXXX --dry-run

  # Delete records matching a formula
  python airtable_cleanup.py delete-matching --base-id appXXXXX --table-id tblXXXXX \\
      --formula "{Created} < DATETIME_PARSE('2024-01-01')}"
        """,
    )

    parser.add_argument(
        "--api-key",
        help="Airtable API key (or set AIRTABLE_API_KEY env var)",
    )
    parser.add_argument(
        "--base-id",
        required=True,
        help="Airtable Base ID (e.g., appXXXXX)",
    )
    parser.add_argument(
        "--table-id",
        required=True,
        help="Airtable Table ID (e.g., tblXXXXX or table name)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # count
    parser_count = subparsers.add_parser("count", help="Count records in table")
    parser_count.add_argument(
        "--formula", help="Airtable formula to filter records"
    )

    # delete-all
    parser_delete_all = subparsers.add_parser(
        "delete-all", help="Delete all records from table"
    )
    parser_delete_all.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation"
    )
    parser_delete_all.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be deleted"
    )

    # delete-matching
    parser_delete_matching = subparsers.add_parser(
        "delete-matching", help="Delete records matching a formula"
    )
    parser_delete_matching.add_argument(
        "--formula", required=True, help="Airtable formula to match records"
    )
    parser_delete_matching.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation"
    )
    parser_delete_matching.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be deleted"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "count": cmd_count,
        "delete-all": cmd_delete_all,
        "delete-matching": cmd_delete_matching,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
