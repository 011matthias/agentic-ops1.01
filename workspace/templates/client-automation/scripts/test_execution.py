"""
Test execution helper for live automation testing.

This script provides a generic way to run automations with test limits
for development and production testing.

Usage:
    uv run scripts/test_execution.py {automation_id} --limit 3
    uv run scripts/test_execution.py {automation_id} --record-ids rec123 rec456
    uv run scripts/test_execution.py {automation_id} --limit 1 --record-ids rec999

Dependencies (PEP 723):
    /// script
    /// requires-python = ">=3.11"
    /// dependencies = [
    ///     "pydantic>=2.0",
    /// ]
    ///
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.automations import AUTOMATIONS
    from app.config import get_settings
except ImportError:
    print("Error: Could not import app modules. Run from client automations directory.")
    sys.exit(1)


def run_test(automation_id: str, limit: int | None = None, record_ids: list[str] | None = None) -> int:
    """
    Run automation with test limits.

    Args:
        automation_id: ID of the automation to run
        limit: Maximum records to process (safety for testing)
        record_ids: Specific record IDs to process (for testing)

    Returns:
        0 on success, 1 on failure
    """
    # Validate automation exists
    if automation_id not in AUTOMATIONS:
        print(f"❌ Automation '{automation_id}' not found")
        print(f"Available automations: {', '.join(AUTOMATIONS.keys())}")
        return 1

    # Get automation class
    automation_class = AUTOMATIONS[automation_id]

    # Show execution preview
    print("\n" + "=" * 60)
    print("🧪 TEST EXECUTION")
    print("=" * 60)
    print(f"Automation: {automation_id}")
    print(f"Class: {automation_class.__name__}")
    print(f"Limit: {limit if limit else 'None (unlimited)'}")
    print(f"Record IDs: {len(record_ids) if record_ids else 0} specified")
    print("=" * 60)

    # Confirmation for safety
    if limit is None and not record_ids:
        print("\n⚠️  WARNING: Running without limits or specific record IDs")
        print("   This will process ALL records. Consider using --limit or --record-ids")
        confirm = input("Continue anyway? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return 1
    else:
        print("\n✓ Safety limits in place")
        confirm = input("Proceed with test? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return 1

    # Run the automation
    print(f"\n🚀 Starting automation: {automation_id}")
    print(f"   Started at: {datetime.now().isoformat()}")

    try:
        automation = automation_class()
        result = automation.run(
            trigger="test",
            dry_run=False,
            limit=limit,
            record_ids=record_ids
        )

        # Show results
        print(f"\n✅ Test completed successfully")
        print(f"   Finished at: {datetime.now().isoformat()}")
        print(f"   Result: {result}")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run automation with test limits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with limit of 5 records
  %(prog)s a6.4 --limit 5

  # Run with specific record IDs
  %(prog)s a6.4 --record-ids rec123 rec456 rec789

  # Run with both limit and record IDs
  %(prog)s a6.4 --limit 10 --record-ids rec123

  # Run without limits (processes all records - use with caution!)
  %(prog)s a6.4
        """
    )

    parser.add_argument(
        "automation_id",
        help="ID of the automation to run (e.g., a6.4, a7)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum records to process (default: 5 for dev, 1 for production)"
    )
    parser.add_argument(
        "--record-ids",
        nargs="+",
        default=None,
        help="Specific record IDs to process (space-separated)"
    )

    args = parser.parse_args()

    # Set default limit if neither limit nor record_ids provided
    if args.limit is None and args.record_ids is None:
        print("ℹ️  No limit or record IDs specified. Defaulting to --limit 5")
        args.limit = 5

    sys.exit(run_test(args.automation_id, args.limit, args.record_ids))


if __name__ == "__main__":
    main()
