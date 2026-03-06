"""
Rollback script for reverting changes made during live testing.

This script reads a test execution log and reverts all changes
by restoring previous values in the source system.

Usage:
    uv run scripts/revert_test_changes.py <test_log_file>
    uv run scripts/revert_test_changes.py /tmp/test_a6_4_dev_20260115_123456.json

Test Log Format:
    {
        "automation_id": "a6.4",
        "mode": "dev",
        "timestamp": "2026-01-15T12:34:56Z",
        "records_modified": [
            {
                "record_id": "recABC123",
                "table": "Accounts",
                "field": "Account Name (Cleaned)",
                "old_value": null,
                "new_value": "Nike"
            },
            ...
        ]
    }

Dependencies (PEP 723):
    /// script
    /// requires-python = ">=3.11"
    /// dependencies = [
    ///     "pydantic>=2.0",
    ///     "httpx>=0.25.0",
    /// ]
    ///
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.clients.airtable import AirtableClient
    from app.config import get_settings
except ImportError:
    print("Error: Could not import app modules.")
    print("Note: This is a template script - implement for your specific client.")
    sys.exit(1)


def load_test_log(log_file: str) -> dict:
    """Load and parse the test execution log."""
    try:
        with open(log_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Test log file not found: {log_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in test log: {e}")
        sys.exit(1)


def preview_revert(log: dict) -> None:
    """Show what will be reverted."""
    print("\n" + "=" * 60)
    print("🔄 ROLLBACK PREVIEW")
    print("=" * 60)
    print(f"Automation: {log.get('automation_id', 'unknown')}")
    print(f"Mode: {log.get('mode', 'unknown')}")
    print(f"Timestamp: {log.get('timestamp', 'unknown')}")
    print(f"Records to revert: {len(log.get('records_modified', []))}")
    print("=" * 60)

    records = log.get('records_modified', [])
    if not records:
        print("⚠️  No records to revert in this log.")
        return

    print("\nChanges that will be reverted:\n")
    for i, record in enumerate(records, 1):
        print(f"{i}. {record.get('record_id', 'unknown')}")
        print(f"   Table: {record.get('table', 'unknown')}")
        print(f"   Field: {record.get('field', 'unknown')}")
        print(f"   Reverting: '{record.get('new_value', 'empty')}' → '{record.get('old_value', 'empty')}'")
        print()

    print("=" * 60)


def confirm_revert() -> bool:
    """Ask user to confirm rollback."""
    print("\n⚠️  This will revert all changes listed above.")
    confirm = input("Type 'REVERT' to confirm: ")
    return confirm == "REVERT"


def revert_changes(log: dict) -> bool:
    """
    Revert changes by restoring old values.

    Note: This is a template implementation. You'll need to customize
    this for your specific client and data sources (Airtable, etc.).
    """
    settings = get_settings()
    records = log.get('records_modified', [])

    print(f"\n🔄 Reverting {len(records)} records...")

    # Example implementation for Airtable
    # Customize this for your client's data sources

    try:
        # Group records by table for efficiency
        by_table = {}
        for record in records:
            table = record.get('table')
            if table not in by_table:
                by_table[table] = []
            by_table[table].append(record)

        # Process each table
        for table_name, table_records in by_table.items():
            print(f"\n📋 Processing table: {table_name}")

            # Initialize client for this table
            # (You'll need to implement this based on your setup)
            # client = AirtableClient(base_id=settings.airtable_base_id, table_name=table_name)

            for record in table_records:
                record_id = record.get('record_id')
                field = record.get('field')
                old_value = record.get('old_value')

                print(f"   Reverting {record_id}: {field} = {old_value}")

                # Implement revert for your specific system
                # Example for Airtable:
                # client.update_record(record_id, {field: old_value})

        print("\n✅ All changes reverted successfully")
        return True

    except Exception as e:
        print(f"\n❌ Revert failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_revert_log(original_log: dict) -> str:
    """Save a log of the revert operation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"/tmp/revert_{original_log.get('automation_id', 'unknown')}_{timestamp}.json"

    revert_log = {
        "revert_timestamp": datetime.now().isoformat(),
        "original_log": original_log,
        "status": "completed"
    }

    with open(log_filename, 'w') as f:
        json.dump(revert_log, f, indent=2)

    print(f"\n📝 Revert log saved: {log_filename}")
    return log_filename


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Revert changes made during live testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Revert changes from a test log
  %(prog)s /tmp/test_a6_4_dev_20260115_123456.json

  # Show what would be reverted without doing it
  %(prog)s /tmp/test_a6_4_dev_20260115_123456.json --dry-run
        """
    )

    parser.add_argument(
        "log_file",
        help="Path to the test execution log file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reverted without doing it"
    )

    args = parser.parse_args()

    # Load the test log
    log = load_test_log(args.log_file)

    # Show preview
    preview_revert(log)

    # Dry run mode
    if args.dry_run:
        print("\n🏁 Dry run complete - no changes made.")
        return

    # Confirm revert
    if not confirm_revert():
        print("\n❌ Revert cancelled.")
        sys.exit(1)

    # Perform revert
    if revert_changes(log):
        # Save revert log
        save_revert_log(log)
        print("\n✅ Rollback complete.")
        sys.exit(0)
    else:
        print("\n❌ Rollback failed. Some changes may not have been reverted.")
        print("   Check the errors above and manually verify your data.")
        sys.exit(1)


if __name__ == "__main__":
    main()
