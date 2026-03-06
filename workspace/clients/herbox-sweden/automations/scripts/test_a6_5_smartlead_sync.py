#!/usr/bin/env python3
"""Dev test for A6.5 SmartLead Lead Sync with real APIs.

This script tests the complete flow:
1. Fetches lead from Airtable
2. Validates lead (campaign assignment, email status)
3. Maps fields to SmartLead format
4. Adds lead to SmartLead campaign
5. Updates Airtable with success/error status

Usage:
    python test_a6_5_smartlead_sync.py <record_id> [--dry-run] [--use-test-api]

Examples:
    # Dry run (validates and shows what would happen)
    python test_a6_5_smartlead_sync.py rec123 --dry-run

    # Live test with main SmartLead API
    python test_a6_5_smartlead_sync.py rec123

    # Live test with test SmartLead API
    python test_a6_5_smartlead_sync.py rec123 --use-test-api
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

from app.automations.smartlead_sync import (
    SmartLeadSync,
    map_lead_to_smartlead,
    validate_lead,
    LeadValidationError,
)
from app.clients.airtable import AirtableClient
from app.clients.smartlead import SmartleadClient


# Airtable configuration
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"  # Herbox Base
AIRTABLE_TABLE_CONTACTS_ID = "tblsI8jeqv1B16MTk"  # Contacts table


async def test_fetch_lead(airtable_client: AirtableClient, record_id: str) -> dict:
    """Test fetching lead from Airtable."""
    print(f"\n{'='*60}")
    print(f"Step 1: Fetching Lead from Airtable")
    print(f"{'='*60}")
    print(f"Record ID: {record_id}")

    try:
        lead_record = await airtable_client.get_record(
            AIRTABLE_TABLE_CONTACTS_ID,
            record_id,
        )
        lead = lead_record.fields

        print(f"✓ Lead fetched successfully")
        print(f"\nLead Data:")
        print(f"  Email: {lead.get('Email', 'N/A')}")
        print(f"  Name: {lead.get('SL_firstName', '')} {lead.get('Last Name', '')}")
        print(f"  Company: {lead.get('SL_company', 'N/A')}")
        print(f"  Campaign IDs: {lead.get('Campaign ID', [])}")
        print(f"  Email Status: {lead.get('Email Verification Status', 'N/A')}")
        print(f"  Outbound Status: {lead.get('Outbound Status', 'N/A')}")

        return lead

    except Exception as e:
        print(f"✗ Error fetching lead: {e}")
        raise


async def test_validation(lead: dict) -> dict:
    """Test lead validation."""
    print(f"\n{'='*60}")
    print(f"Step 2: Validating Lead")
    print(f"{'='*60}")

    try:
        validation = validate_lead(lead)
        campaign_id = validation["campaign_id"]

        print(f"✓ Lead validated successfully")
        print(f"  Campaign ID: {campaign_id}")
        print(f"  Email: {lead.get('Email')}")
        print(f"  Email Status: {lead.get('Email Verification Status')}")

        return validation

    except LeadValidationError as e:
        reason = str(e)
        print(f"✗ Validation failed: {reason}")

        if reason == "no_campaign":
            print(f"  → No campaign assigned to this lead")
        elif reason == "missing_email":
            print(f"  → Email field is empty")
        elif reason == "invalid_email":
            print(f"  → Email verification status is 'Invalid'")

        return {"valid": False, "reason": reason}


async def test_field_mapping(lead: dict) -> dict:
    """Test field mapping to SmartLead format."""
    print(f"\n{'='*60}")
    print(f"Step 3: Mapping Fields to SmartLead Format")
    print(f"{'='*60}")

    smartlead_lead = map_lead_to_smartlead(lead)

    print(f"✓ Fields mapped successfully")
    print(f"\nMapped Data:")
    print(f"  first_name: {smartlead_lead.get('first_name')}")
    print(f"  last_name: {smartlead_lead.get('last_name')}")
    print(f"  email: {smartlead_lead.get('email')}")
    print(f"  company_name: {smartlead_lead.get('company_name')}")
    print(f"  website: {smartlead_lead.get('website')}")
    print(f"  linkedin_profile: {smartlead_lead.get('linkedin_profile')}")
    print(f"  custom_fields:")
    print(f"    job_title: {smartlead_lead.get('custom_fields', {}).get('job_title')}")
    print(f"    sl_personalization: {smartlead_lead.get('custom_fields', {}).get('sl_personalization')[:50]}..." if smartlead_lead.get('custom_fields', {}).get('sl_personalization') else "    sl_personalization: (empty)")

    return smartlead_lead


async def test_smartlead_sync(
    smartlead_client: SmartleadClient,
    campaign_id: str,
    smartlead_lead: dict,
) -> dict:
    """Test adding lead to SmartLead campaign."""
    print(f"\n{'='*60}")
    print(f"Step 4: Adding Lead to SmartLead Campaign")
    print(f"{'='*60}")
    print(f"Campaign ID: {campaign_id}")
    print(f"Email: {smartlead_lead.get('email')}")

    try:
        response = await smartlead_client.add_leads_to_campaign(
            campaign_id=int(campaign_id),
            leads=[smartlead_lead],
            return_lead_ids=True,
        )

        print(f"✓ Lead added to campaign successfully")

        # Extract lead ID
        lead_ids = response.get("lead_ids", [])
        smartlead_lead_id = lead_ids[0] if lead_ids else None

        print(f"  SmartLead Lead ID: {smartlead_lead_id}")

        return {
            "success": True,
            "lead_id": smartlead_lead_id,
            "response": response,
        }

    except Exception as e:
        print(f"✗ Error adding lead to campaign: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def test_airtable_update(
    airtable_client: AirtableClient,
    record_id: str,
    success: bool,
    smartlead_lead_id: int | None = None,
    error_message: str = "",
) -> None:
    """Test updating Airtable with sync result."""
    print(f"\n{'='*60}")
    print(f"Step 5: Updating Airtable Status")
    print(f"{'='*60}")

    try:
        if success:
            fields = {
                "Outbound Status": "Added to Campaign",
            }
            if smartlead_lead_id:
                fields["SL Contact ID"] = str(smartlead_lead_id)

            print(f"Updating to: Added to Campaign")
            if smartlead_lead_id:
                print(f"SL Contact ID: {smartlead_lead_id}")

        else:
            fields = {
                "Outbound Status": "Sync Error",
                "Sync Error Log": error_message[:1000],  # Limit to 1000 chars
            }
            print(f"Updating to: Sync Error")
            print(f"Error: {error_message[:100]}...")

        await airtable_client.update_record(
            AIRTABLE_TABLE_CONTACTS_ID,
            record_id,
            fields,
        )

        print(f"✓ Airtable updated successfully")

    except Exception as e:
        print(f"✗ Error updating Airtable: {e}")
        raise


async def main():
    # Load .env from parent directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    import os

    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    use_test_api = "--use-test-api" in sys.argv

    # Get record ID and campaign ID override
    record_id = None
    override_campaign_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("rec") and not arg.startswith("--"):
            record_id = arg
        elif arg.startswith("--campaign-id="):
            override_campaign_id = arg.split("=", 1)[1]

    if not record_id:
        print("Usage: python test_a6_5_smartlead_sync.py <record_id> [--dry-run] [--use-test-api] [--campaign-id=<id>]")
        print("\nExamples:")
        print("  python test_a6_5_smartlead_sync.py rec123 --dry-run")
        print("  python test_a6_5_smartlead_sync.py rec123")
        print("  python test_a6_5_smartlead_sync.py rec123 --campaign-id=2844659")
        print("\nNote: --campaign-id overrides the Campaign ID from Airtable (useful for testing)")
        sys.exit(1)

    # Get credentials
    airtable_token = os.getenv("AIRTABLE_TOKEN")
    smartlead_api = os.getenv("SMARTLEAD_API_TEST" if use_test_api else "SMARTLEAD_API")

    if not airtable_token:
        print("ERROR: AIRTABLE_TOKEN not set in .env")
        sys.exit(1)

    if not smartlead_api:
        api_name = "SMARTLEAD_API_TEST" if use_test_api else "SMARTLEAD_API"
        print(f"ERROR: {api_name} not set in .env")
        sys.exit(1)

    # Print test configuration
    print(f"\n{'='*60}")
    print(f"A6.5 SmartLead Lead Sync - Dev Test")
    print(f"{'='*60}")
    print(f"Record ID: {record_id}")
    if override_campaign_id:
        print(f"Campaign ID: {override_campaign_id} (OVERRIDE)")
    print(f"Dry Run: {dry_run}")
    print(f"SmartLead API: {'TEST' if use_test_api else 'MAIN'}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Initialize clients
    airtable_client = AirtableClient(
        token=airtable_token,
        base_id=AIRTABLE_BASE_ID,
    )
    smartlead_client = SmartleadClient(api_key=smartlead_api)

    try:
        # Step 1: Fetch lead
        lead = await test_fetch_lead(airtable_client, record_id)

        # Step 2: Validate lead (or use override campaign ID)
        if override_campaign_id:
            # Skip campaign validation when override is provided
            print(f"\nUsing override campaign ID: {override_campaign_id}")
            campaign_id = override_campaign_id
        else:
            validation = await test_validation(lead)

            if not validation.get("valid"):
                print(f"\n{'='*60}")
                print(f"Test Result: SKIPPED")
                print(f"{'='*60}")
                print(f"Reason: {validation.get('reason')}")
                print(f"\nThis lead does not meet the criteria for SmartLead sync.")
                print(f"Please choose a lead with:")
                print(f"  - Campaign ID assigned")
                print(f"  - Email present and valid")
                print(f"\nOr use --campaign-id=<id> to override the campaign ID.")
                return

            campaign_id = validation["campaign_id"]

        # Step 3: Map fields
        smartlead_lead = await test_field_mapping(lead)

        # Step 4: Sync to SmartLead (skip in dry run)
        if dry_run:
            print(f"\n{'='*60}")
            print(f"DRY RUN - Skipping SmartLead sync")
            print(f"{'='*60}")
            print(f"Would sync to campaign: {campaign_id}")
            print(f"\n✓ Dry run completed successfully")
            return

        sync_result = await test_smartlead_sync(
            smartlead_client,
            campaign_id,
            smartlead_lead,
        )

        # Step 5: Update Airtable
        if sync_result["success"]:
            await test_airtable_update(
                airtable_client,
                record_id,
                success=True,
                smartlead_lead_id=sync_result["lead_id"],
            )

            print(f"\n{'='*60}")
            print(f"Test Result: SUCCESS")
            print(f"{'='*60}")
            print(f"✓ Lead synced to SmartLead campaign {campaign_id}")
            print(f"✓ Airtable status updated to 'Added to Campaign'")
            print(f"✓ SmartLead Lead ID: {sync_result['lead_id']}")
        else:
            await test_airtable_update(
                airtable_client,
                record_id,
                success=False,
                error_message=sync_result["error"],
            )

            print(f"\n{'='*60}")
            print(f"Test Result: FAILED")
            print(f"{'='*60}")
            print(f"✗ SmartLead sync failed")
            print(f"✓ Airtable status updated to 'Sync Error'")
            print(f"Error: {sync_result['error']}")

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Test Result: ERROR")
        print(f"{'='*60}")
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await airtable_client.close()
        await smartlead_client.close()


if __name__ == "__main__":
    asyncio.run(main())
