#!/usr/bin/env python3
"""
Airtable Records Testing Utility

Provides helper functions for testing Airtable record operations.

Usage:
    # Create a single record
    uv run python scripts/testing-utils/airtable_records.py create \\
        --base-id appXXXXX --table-id tblXXXXX \\
        --field Name "John Doe" --field Email "john@example.com"

    # Create records from JSON file
    uv run python scripts/testing-utils/airtable_records.py create \\
        --base-id appXXXXX --table-id tblXXXXX \\
        --input records.json

    # List records
    uv run python scripts/testing-utils/airtable_records.py list \\
        --base-id appXXXXX --table-id tblXXXXX

    # Get a specific record
    uv run python scripts/testing-utils/airtable_records.py get \\
        --base-id appXXXXX --table-id tblXXXXX \\
        --record-id recXXXXX
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.25.0",
# ]
# ///

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx


# --- Client ---


class AirtableTestClient:
    """Simple client for testing Airtable operations."""

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

    def create_record(
        self, base_id: str, table_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a single record."""
        return self._request(
            "POST",
            f"/{base_id}/{table_id}",
            json={"fields": fields},
        )

    def create_records(
        self, base_id: str, table_id: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create multiple records (max 10 per request)."""
        return self._request(
            "POST",
            f"/{base_id}/{table_id}",
            json={"records": [{"fields": r} for r in records]},
        )

    def get_record(
        self, base_id: str, table_id: str, record_id: str
    ) -> dict[str, Any]:
        """Get a single record."""
        return self._request("GET", f"/{base_id}/{table_id}/{record_id}")

    def list_records(
        self,
        base_id: str,
        table_id: str,
        max_records: int | None = None,
        offset: str | None = None,
    ) -> dict[str, Any]:
        """List records from a table."""
        params = {}
        if max_records:
            params["maxRecords"] = max_records
        if offset:
            params["offset"] = offset

        return self._request(
            "GET",
            f"/{base_id}/{table_id}",
            params=params if params else None,
        )

    def list_all_records(
        self, base_id: str, table_id: str
    ) -> list[dict[str, Any]]:
        """List all records, handling pagination."""
        all_records = []
        offset = None

        while True:
            result = self.list_records(base_id, table_id, offset=offset)
            all_records.extend(result.get("records", []))

            offset = result.get("offset")
            if not offset:
                break

        return all_records

    def update_record(
        self,
        base_id: str,
        table_id: str,
        record_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a single record."""
        return self._request(
            "PATCH",
            f"/{base_id}/{table_id}/{record_id}",
            json={"fields": fields},
        )

    def delete_record(
        self, base_id: str, table_id: str, record_id: str
    ) -> dict[str, Any]:
        """Delete a single record."""
        return self._request("DELETE", f"/{base_id}/{table_id}/{record_id}")

    def delete_records(
        self, base_id: str, table_id: str, record_ids: list[str]
    ) -> dict[str, Any]:
        """Delete multiple records (max 10 per request)."""
        return self._request(
            "DELETE",
            f"/{base_id}/{table_id}",
            params={"records[]": record_ids},
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


# --- Utilities ---


def load_records_from_file(path: Path) -> list[dict[str, Any]]:
    """Load records from a JSON file."""
    data = json.loads(path.read_text())

    if "records" in data:
        return data["records"]
    elif isinstance(data, list):
        return data
    else:
        return [data]


def parse_field_pairs(pairs: list[str]) -> dict[str, Any]:
    """Parse key=value pairs into a dict."""
    fields = {}
    for pair in pairs:
        if "=" not in pair:
            print(f"Warning: Invalid field pair '{pair}', skipping", file=sys.stderr)
            continue
        key, value = pair.split("=", 1)

        # Try to parse as JSON for complex types
        try:
            fields[key] = json.loads(value)
        except json.JSONDecodeError:
            fields[key] = value

    return fields


# --- Commands ---


def cmd_create(args: argparse.Namespace) -> None:
    """Create records in Airtable."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableTestClient(api_key)

    try:
        if args.input:
            records = load_records_from_file(Path(args.input))

            if len(records) > 10:
                print("Note: More than 10 records, will create in batches...")
                all_created = []
                for i in range(0, len(records), 10):
                    batch = records[i : i + 10]
                    result = client.create_records(args.base_id, args.table_id, batch)
                    all_created.extend(result.get("records", []))
                    print(f"Created batch {i // 10 + 1}: {len(batch)} records")

                print(f"Total: {len(all_created)} records created")
            else:
                result = client.create_records(args.base_id, args.table_id, records)
                created = result.get("records", [])
                print(f"Created {len(created)} record(s)")

                for record in created:
                    print(f"  - ID: {record.get('id')}")

        elif args.field:
            fields = parse_field_pairs(args.field)
            result = client.create_record(args.base_id, args.table_id, fields)
            record = result
            print(f"Created record: {record.get('id')}")
            print(f"Fields: {json.dumps(record.get('fields', {}), indent=2)}")
        else:
            print("Error: Must provide --input or --field", file=sys.stderr)
            sys.exit(1)
    finally:
        client.close()


def cmd_get(args: argparse.Namespace) -> None:
    """Get a specific record."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableTestClient(api_key)

    try:
        record = client.get_record(args.base_id, args.table_id, args.record_id)
        print(f"Record: {record.get('id')}")
        print(f"Created: {record.get('createdTime')}")
        print("Fields:")
        for key, value in record.get("fields", {}).items():
            print(f"  {key}: {value}")
    finally:
        client.close()


def cmd_list(args: argparse.Namespace) -> None:
    """List records in a table."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableTestClient(api_key)

    try:
        if args.all:
            records = client.list_all_records(args.base_id, args.table_id)
            print(f"All records in table ({len(records)} total):")
        else:
            result = client.list_records(
                args.base_id, args.table_id, max_records=args.max_records
            )
            records = result.get("records", [])
            print(f"Records in table (showing {len(records)}):")

        print()
        for record in records:
            record_id = record.get("id", "N/A")
            fields = record.get("fields", {})
            # Try to find a name/title field
            name = fields.get("Name") or fields.get("Title") or fields.get("name") or fields.get("title") or "N/A"
            print(f"  [{record_id}] {name}")

    finally:
        client.close()


def cmd_update(args: argparse.Namespace) -> None:
    """Update a record."""
    api_key = args.api_key or get_env_var("AIRTABLE_API_KEY")
    client = AirtableTestClient(api_key)

    try:
        fields = parse_field_pairs(args.field)
        result = client.update_record(
            args.base_id, args.table_id, args.record_id, fields
        )
        record = result
        print(f"Updated record: {record.get('id')}")
        print(f"Fields: {json.dumps(record.get('fields', {}), indent=2)}")
    finally:
        client.close()


def get_env_var(name: str) -> str:
    """Get environment variable or exit."""
    import os

    value = os.getenv(name)
    if not value:
        print(f"Error: {name} environment variable not set", file=sys.stderr)
        sys.exit(1)
    return value


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Airtable Records Testing Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a single record
  python airtable_records.py create --base-id appXXXXX --table-id tblXXXXX \\
      --field Name="John Doe" --field Email="john@example.com"

  # Create records from JSON file
  python airtable_records.py create --base-id appXXXXX --table-id tblXXXXX \\
      --input records.json

  # List records
  python airtable_records.py list --base-id appXXXXX --table-id tblXXXXX

  # List all records (pagination handled)
  python airtable_records.py list --base-id appXXXXX --table-id tblXXXXX --all

  # Get a specific record
  python airtable_records.py get --base-id appXXXXX --table-id tblXXXXX \\
      --record-id recXXXXX

  # Update a record
  python airtable_records.py update --base-id appXXXXX --table-id tblXXXXX \\
      --record-id recXXXXX --field Name="Jane Doe"
        """,
    )

    parser.add_argument(
        "--api-key",
        help="Airtable API key (or set AIRTABLE_API_KEY env var)",
    )
    parser.add_argument(
        "--base-id",
        help="Airtable Base ID (e.g., appXXXXX)",
    )
    parser.add_argument(
        "--table-id",
        help="Airtable Table ID (e.g., tblXXXXX or table name)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create
    parser_create = subparsers.add_parser("create", help="Create record(s)")
    parser_create.add_argument("--input", help="JSON file with records")
    parser_create.add_argument(
        "--field",
        action="append",
        help="Field as key=value (can be used multiple times)",
    )

    # get
    parser_get = subparsers.add_parser("get", help="Get a specific record")
    parser_get.add_argument("--record-id", required=True, help="Record ID")

    # list
    parser_list = subparsers.add_parser("list", help="List records")
    parser_list.add_argument(
        "--max-records",
        type=int,
        default=100,
        help="Maximum records to return (default: 100)",
    )
    parser_list.add_argument("--all", action="store_true", help="List all records")

    # update
    parser_update = subparsers.add_parser("update", help="Update a record")
    parser_update.add_argument("--record-id", required=True, help="Record ID")
    parser_update.add_argument(
        "--field",
        action="append",
        required=True,
        help="Field as key=value (can be used multiple times)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Validate base_id and table_id for most commands
    if args.command not in [] and not args.base_id:
        print("Error: --base-id is required", file=sys.stderr)
        sys.exit(1)
    if args.command not in [] and not args.table_id:
        print("Error: --table-id is required", file=sys.stderr)
        sys.exit(1)

    commands = {
        "create": cmd_create,
        "get": cmd_get,
        "list": cmd_list,
        "update": cmd_update,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
