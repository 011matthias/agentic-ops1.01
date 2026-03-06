# /// script
# dependencies = [
#     "httpx",
#     "pydantic",
#     "pydantic-settings",
#     "sqlalchemy",
# ]
# ///

"""
Airtable Format Verification Script

Fetches a real record from Airtable to verify field names and structure.
This helps ensure our tests use correct field formats.

Usage:
    uv run scripts/verify_airtable_formats.py recYOUR_RECORD_ID
"""

import asyncio
import sys
import json
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.airtable import AirtableClient
from app.config import get_settings

settings = get_settings()

# Airtable configuration
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"
AIRTABLE_TABLE_LIST_BUILDING = "tblcFFxDCN0788xjF"


async def verify_record(record_id: str):
    """Fetch and display a real Airtable record."""
    print(f"\n{'='*60}")
    print("AIRTABLE FORMAT VERIFICATION")
    print(f"{'='*60}\n")
    print(f"Fetching record: {record_id}")
    print(f"Table ID: {AIRTABLE_TABLE_LIST_BUILDING}")
    print(f"Base ID: {AIRTABLE_BASE_ID}\n")

    client = AirtableClient(
        token=settings.airtable_token,
        base_id=AIRTABLE_BASE_ID
    )

    try:
        record = await client.get_record(
            table_id=AIRTABLE_TABLE_LIST_BUILDING,
            record_id=record_id
        )

        print("✅ Record fetched successfully!\n")
        print("="*60)
        print("RECORD DATA")
        print("="*60)
        print(f"\nID: {record.id}")
        print(f"Created Time: {record.created_time}\n")

        print("="*60)
        print("FIELD NAMES AND VALUES")
        print("="*60)
        print("\nThis is the EXACT format you should use in tests:\n")
        print("{")
        for key, value in record.fields.items():
            if isinstance(value, str):
                print(f'    "{key}": "{value}",')
            elif isinstance(value, list):
                print(f'    "{key}": {value},')
            elif isinstance(value, (int, float, bool)):
                print(f'    "{key}": {value},')
            else:
                print(f'    "{key}": {json.dumps(value)},')
        print("}\n")

        print("="*60)
        print("REQUIRED FIELDS CHECK")
        print("="*60)
        required_fields = ["List URL", "List Type"]
        for field in required_fields:
            status = "✅ Present" if field in record.fields else "❌ Missing"
            print(f"  {field}: {status}")

        print("\n" + "="*60)
        print("OPTIONAL FIELDS")
        print("="*60)
        optional_fields = ["Max Results", "List Name"]
        for field in optional_fields:
            status = f"= {record.fields.get(field, 'Not set')}" if field in record.fields else "Not present"
            print(f"  {field}: {status}")

        print("\n" + "="*60)
        print("COPY THIS FOR YOUR TESTS")
        print("="*60)
        print("\nmock_record.fields = {")
        for key, value in record.fields.items():
            if isinstance(value, str):
                # Truncate long strings
                display_value = value[:50] + "..." if len(value) > 50 else value
                print(f'    "{key}": "{display_value}",')
            elif isinstance(value, list):
                print(f'    "{key}": [],  # List with {len(value)} items')
            else:
                print(f'    "{key}": {value},')
        print("}\n")

    except Exception as e:
        print(f"❌ Error fetching record: {e}")
        print("\nPossible issues:")
        print("  1. Record ID is incorrect")
        print("  2. AIRTABLE_TOKEN is invalid")
        print("  3. Base ID or Table ID is wrong")
        return False

    finally:
        await client.close()

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/verify_airtable_formats.py <record_id>")
        print("\nExample:")
        print("  uv run scripts/verify_airtable_formats.py recABC123XYZ")
        print("\nTo get a record ID:")
        print("  1. Open Airtable List Building table")
        print("  2. Click on any record")
        print("  3. Copy the record ID from the URL (starts with 'rec')")
        sys.exit(1)

    record_id = sys.argv[1]

    if not record_id.startswith("rec"):
        print(f"⚠️  Warning: '{record_id}' doesn't look like a valid record ID")
        print("   Record IDs usually start with 'rec' followed by characters.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

    success = asyncio.run(verify_record(record_id))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
