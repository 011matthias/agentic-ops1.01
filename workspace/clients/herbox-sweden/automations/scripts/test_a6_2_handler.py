#!/usr/bin/env python3
"""Test A6.2 handler with real Apify dataset.

Uses APIFY_API_TOKEN_TEST from .env for testing.
Remove test variables from .env after testing.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.automations.lead_sourcing_completed import LeadSourcingCompletedHandler


async def main():
    # Load .env from parent directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    import os

    # Get test credentials
    test_token = os.getenv("APIFY_API_TOKEN_TEST")
    airtable_token = os.getenv("AIRTABLE_TOKEN")

    if not airtable_token:
        print("ERROR: AIRTABLE_TOKEN not set in .env")
        sys.exit(1)

    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    # Get payload file
    payload_file = None
    for arg in sys.argv[1:]:
        if arg.endswith(".json") and not arg.startswith("--"):
            payload_file = arg
            break

    if not payload_file:
        print("Usage: python test_a6_2_handler.py <payload_file.json> [--dry-run]")
        sys.exit(1)

    # Load payload
    with open(payload_file) as f:
        payload = json.load(f)

    print(f"{'='*60}")
    print(f"A6.2 Handler Test")
    print(f"{'='*60}")
    print(f"Dry run: {dry_run}")
    print(f"Using test Apify token: {bool(test_token)}")
    print(f"Payload: {payload_file}")
    print(f"Scraper ID: {payload['eventData']['actorRunId']}")
    print(f"Dataset ID: {payload['resource']['defaultDatasetId']}")
    print()

    # Create handler with test token if available
    handler = LeadSourcingCompletedHandler(
        airtable_token=airtable_token,
        apify_token=test_token or os.getenv("APIFY_API_TOKEN"),
    )

    try:
        result = await handler.run(payload, dry_run=dry_run)

        print(f"\n{'='*60}")
        print(f"Result: {result.get('status')}")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))

        # Show summary
        if dry_run and result.get("sample_lead"):
            print(f"\n{'='*60}")
            print("Sample Transformed Lead:")
            print(f"{'='*60}")
            print(json.dumps(result["sample_lead"], indent=2))

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {e}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
