# /// script
# dependencies = [
#     "httpx",
#     "pydantic",
#     "pydantic-settings",
#     "sqlalchemy",
# ]
# ///

"""
A6.1 Real Data Test - Dry Run Mode

Runs the actual A6.1 automation with a real Airtable record,
but in dry-run mode so it doesn't start any scrapers.

This will verify:
1. The record can be fetched from Airtable
2. All required fields are present
3. The scraper configuration would be built correctly

Usage:
    uv run scripts/test_a6_1_real_data.py recYOUR_RECORD_ID
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.automations.apify_scraper_starter import ApifyScraperStarter
from app.config import get_settings

settings = get_settings()


async def test_with_real_data(record_id: str, dry_run: bool = True):
    """Test A6.1 with a real Airtable record."""
    print(f"\n{'='*60}")
    print("A6.1 APIFY SCRAPER STARTER - REAL DATA TEST")
    print(f"{'='*60}\n")
    print(f"Record ID: {record_id}")
    print(f"Dry Run: {dry_run}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    print("="*60)
    print("ENVIRONMENT CHECK")
    print("="*60)

    checks = []

    # Check Airtable token
    if settings.airtable_token:
        print("✅ AIRTABLE_TOKEN: Set")
        checks.append(True)
    else:
        print("❌ AIRTABLE_TOKEN: Missing")
        checks.append(False)

    # Check Apify token
    if settings.apify_api_token:
        print("✅ APIFY_API_TOKEN: Set")
        checks.append(True)
    else:
        print("❌ APIFY_API_TOKEN: Missing")
        checks.append(False)

    # Check LinkedIn credentials (now in Airtable config table)
    if dry_run:
        print("⏭️  LINKEDIN_COOKIES: Skipped (dry run mode)")
        print("⏭️  LINKEDIN_USER_AGENT: Skipped (dry run mode)")
        checks.append(True)
        checks.append(True)
    else:
        # Cookies are in Airtable, not environment - skip check
        print("⏭️  LINKEDIN_COOKIES: Fetched from Airtable Configs table")
        checks.append(True)

        if settings.linkedin_user_agent:
            print("✅ LINKEDIN_USER_AGENT: Set")
            checks.append(True)
        else:
            print("❌ LINKEDIN_USER_AGENT: Missing (needed for live run)")
            checks.append(False)

    if not all(checks):
        print("\n❌ Some required environment variables are missing.")
        print("   Please set them in the .env file.")
        return False

    print("\n" + "="*60)
    print("RUNNING AUTOMATION")
    print("="*60 + "\n")

    handler = ApifyScraperStarter()

    payload = {"recordId": record_id}

    try:
        result = await handler.run(payload, dry_run=dry_run)

        print("\n" + "="*60)
        print("RESULT")
        print("="*60 + "\n")
        print(json.dumps(result, indent=2))

        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60 + "\n")

        if result.get("status") == "dry_run":
            print("✅ Dry run successful!")
            print(f"\nThe scraper WOULD start with these settings:")
            print(f"  - Actor ID: {result.get('actor_id')}")
            print(f"  - Max Results: {result.get('config', {}).get('count', 'Not specified')}")
            print(f"  - Search URL: {result.get('config', {}).get('searchUrl', 'Not specified')}")
            print("\nTo actually start the scraper, run without --dry-run")
            return True

        elif result.get("status") == "queued":
            print("⏸️  Scraper would be queued")
            print(f"  Reason: {result.get('reason')}")
            print(f"  Running: {result.get('running_count')}/{result.get('max_concurrent')}")
            return True

        elif result.get("status") == "scraper_started":
            print("✅ Scraper started!")
            print(f"  Run ID: {result.get('run_id')}")
            print(f"  Status: {result.get('run_status')}")
            return True

        else:
            print(f"⚠️  Unexpected status: {result.get('status')}")
            return result.get("status") not in ["failed", "error"]

    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        print("\nThis usually means:")
        print("  - The record is missing a required field")
        print("  - The field name in the code doesn't match Airtable")
        print("\nRun 'verify_airtable_formats.py' to check the actual field names.")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/test_a6_1_real_data.py <record_id>")
        print("\nExample:")
        print("  uv run scripts/test_a6_1_real_data.py recABC123XYZ")
        print("\nTo get a record ID:")
        print("  1. Open Airtable List Building table")
        print("  2. Click on any record")
        print("  3. Copy the record ID from the URL (starts with 'rec')")
        sys.exit(1)

    record_id = sys.argv[1]
    dry_run = "--live" not in sys.argv

    if not record_id.startswith("rec"):
        print(f"⚠️  Warning: '{record_id}' doesn't look like a valid record ID")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

    if not dry_run:
        print("\n⚠️  LIVE MODE: This will start an actual scraper!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            sys.exit(0)

    success = asyncio.run(test_with_real_data(record_id, dry_run))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
