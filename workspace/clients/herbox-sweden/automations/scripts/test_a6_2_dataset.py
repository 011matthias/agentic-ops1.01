#!/usr/bin/env python3
"""Test script to fetch and inspect Apify dataset for A6.2 testing.

NOTE: Requires APIFY_API_TOKEN_TEST and APIFY_DATASET_ID_TEST in .env
Remove these test variables after testing is complete.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx",
#     "pydantic",
#     "python-dotenv",
# ]
# ///

import asyncio
import httpx
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (automations/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Load test credentials from .env
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN_TEST")
DATASET_ID = os.getenv("APIFY_DATASET_ID_TEST")

if not APIFY_TOKEN or not DATASET_ID:
    print("ERROR: Test environment variables not set!")
    print("Please set APIFY_API_TOKEN_TEST and APIFY_DATASET_ID_TEST in .env")
    exit(1)


async def fetch_dataset():
    """Fetch dataset items from Apify."""
    url = f"https://api.apify.com/v2/datasets/{DATASET_ID}/items"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
            params={"limit": 100, "clean": True}
        )

        response.raise_for_status()
        return response.json()


def print_dataset_info(items):
    """Print information about the dataset."""
    print(f"\n{'='*60}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Total items: {len(items)}")
    print(f"{'='*60}\n")

    if not items:
        print("Dataset is empty!")
        return

    # Print first item as sample
    print("Sample item (first):")
    print(json.dumps(items[0], indent=2, default=str))
    print()

    # Print all available fields
    all_fields = set()
    for item in items:
        all_fields.update(item.keys())

    print(f"\nAvailable fields ({len(all_fields)}):")
    for field in sorted(all_fields):
        print(f"  - {field}")

    # Print field coverage
    print(f"\nField coverage (non-empty values):")
    for field in sorted(all_fields):
        count = sum(1 for item in items if item.get(field))
        pct = (count / len(items)) * 100
        print(f"  - {field}: {count}/{len(items)} ({pct:.1f}%)")


def create_test_payload():
    """Create a test webhook payload for A6.2."""
    # Use a fake run ID for testing
    fake_run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    payload = {
        "eventType": "ACTOR.RUN.SUCCEEDED",
        "eventData": {
            "actorRunId": fake_run_id
        },
        "resource": {
            "id": fake_run_id,
            "status": "SUCCEEDED",
            "defaultDatasetId": DATASET_ID
        }
    }

    # Save to scripts directory
    scripts_dir = Path(__file__).parent
    filename = scripts_dir / f"test_payload_{fake_run_id}.json"
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nTest payload saved to: {filename}")
    print(f"Scraper ID: {fake_run_id}")
    print(f"Dataset ID: {DATASET_ID}")

    return filename, fake_run_id


async def main():
    """Main test function."""
    print("Fetching Apify dataset...")
    print(f"Dataset ID: {DATASET_ID}")
    print("(Using APIFY_API_TOKEN_TEST from .env)")

    items = await fetch_dataset()
    print_dataset_info(items)

    # Create test payload
    payload_file, run_id = create_test_payload()

    print(f"\n{'='*60}")
    print("Next steps:")
    print(f"{'='*60}")
    print(f"""
1. Create a test list record in Airtable:
   - Go to List Building table (tblcFFxDCN0788xjF)
   - Create new record with:
     * Scraper ID: {run_id}
     * List Status: "Scraper Running"
     * List Name: "Test List A6.2"

2. Run dry-run test:
   cd clients/herbox-sweden/automations
   uv run python -m app.automations.lead_sourcing_complete ../scripts/{payload_file.name} --dry-run

3. Run live test (will upsert to Airtable):
   uv run python -m app.automations.lead_sourcing_completed ../scripts/{payload_file.name}

4. Verify in Airtable:
   - Check Contacts table for new records
   - Check Accounts table for new records
   - Check List status changed to "Scraper Completed"
    """)


if __name__ == "__main__":
    asyncio.run(main())
