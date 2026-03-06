#!/usr/bin/env python3
"""SmartLead Campaign Utility - Create, list, and delete test campaigns.

Usage:
    python smartlead_campaign_util.py list
    python smartlead_campaign_util.py create "Test Campaign Name"
    python smartlead_campaign_util.py delete <campaign_id>

Examples:
    # List all campaigns
    python smartlead_campaign_util.py list

    # Create a test campaign
    python smartlead_campaign_util.py create "Dev Test Campaign"

    # Delete a campaign by ID
    python smartlead_campaign_util.py delete 12345
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
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.smartlead import SmartleadClient


async def list_campaigns(client: SmartleadClient) -> None:
    """List all SmartLead campaigns."""
    print(f"\n{'='*60}")
    print(f"SmartLead Campaigns")
    print(f"{'='*60}")

    try:
        campaigns = await client.get_campaign_list()

        if not campaigns:
            print("No campaigns found.")
            return

        print(f"\nFound {len(campaigns)} campaigns:\n")
        print(f"{'ID':<10} {'Name':<40} {'Status':<15}")
        print("-" * 65)

        for campaign in campaigns:
            print(f"{campaign.id:<10} {campaign.name or 'N/A':<40} {campaign.status or 'N/A':<15}")

    except Exception as e:
        print(f"Error listing campaigns: {e}")
        sys.exit(1)


async def create_campaign(client: SmartleadClient, name: str) -> None:
    """Create a new SmartLead campaign."""
    print(f"\n{'='*60}")
    print(f"Creating SmartLead Campaign")
    print(f"{'='*60}")
    print(f"Campaign Name: {name}")

    try:
        result = await client.create_campaign(name)

        campaign_id = result.get("id")
        if campaign_id:
            print(f"\n✓ Campaign created successfully!")
            print(f"  Campaign ID: {campaign_id}")
            print(f"  Name: {result.get('name', name)}")
            print(f"  Status: {result.get('status', 'draft')}")
            print(f"\nYou can now use this campaign ID for testing A6.5 SmartLead Sync.")
        else:
            print(f"\n✗ Campaign creation failed - no ID returned")
            print(f"Response: {json.dumps(result, indent=2)}")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error creating campaign: {e}")
        sys.exit(1)


async def delete_campaign(client: SmartleadClient, campaign_id: int) -> None:
    """Delete a SmartLead campaign."""
    print(f"\n{'='*60}")
    print(f"Deleting SmartLead Campaign")
    print(f"{'='*60}")
    print(f"Campaign ID: {campaign_id}")

    # Confirm before deleting
    confirm = input(f"\nAre you sure you want to delete campaign {campaign_id}? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        return

    try:
        result = await client.delete_campaign(campaign_id)
        print(f"\n✓ Campaign deleted successfully!")
        print(f"Response: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"\n✗ Error deleting campaign: {e}")
        sys.exit(1)


async def main():
    # Load .env from parent directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    import os

    # Get API key
    smartlead_api = os.getenv("SMARTLEAD_API")

    if not smartlead_api:
        print("ERROR: SMARTLEAD_API not set in .env")
        sys.exit(1)

    # Parse command
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    # Initialize client
    client = SmartleadClient(api_key=smartlead_api)

    try:
        if command == "list":
            await list_campaigns(client)

        elif command == "create":
            if len(sys.argv) < 3:
                print("Usage: python smartlead_campaign_util.py create \"Campaign Name\"")
                sys.exit(1)

            campaign_name = " ".join(sys.argv[2:])
            await create_campaign(client, campaign_name)

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: python smartlead_campaign_util.py delete <campaign_id>")
                sys.exit(1)

            try:
                campaign_id = int(sys.argv[2])
            except ValueError:
                print(f"Invalid campaign ID: {sys.argv[2]}")
                sys.exit(1)

            await delete_campaign(client, campaign_id)

        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
