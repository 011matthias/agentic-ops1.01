#!/usr/bin/env python3
"""Create a Smartlead campaign with sample B2B outreach copy for Herbox.

Usage:
    cd clients/herbox-sweden/automations
    uv run python scripts/create_sample_campaign.py

This script will:
1. Create a new campaign
2. Add 3 email sequences with sample copy
3. Display the campaign ID for reference

Variables available in Smartlead:
- {{first_name}} - Contact's first name
- {{last_name}} - Contact's last name
- {{email}} - Contact's email
- {{company_name}} - Company name
- {{website}} - Company website
- {{location}} - Contact location
- Any custom fields you upload with leads
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
#     "httpx>=0.25.0",
# ]
# ///

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API")
SMARTLEAD_API_URL = "https://server.smartlead.ai/api/v1"

# Sample email sequences for B2B outreach
# Note: API expects {"sequences": [...]} format with:
#   - seq_delay_details object (not seq_delay_days)
#   - variant_label required on each variant
SAMPLE_SEQUENCES = {
    "sequences": [
        {
            "seq_number": 1,
            "seq_delay_details": {"delay_in_days": 0},
            "seq_variants": [
                {
                    "variant_label": "A",
                    "subject": "Quick question about {{company_name}}",
                    "email_body": """<p>Hi {{first_name}},</p>

<p>I noticed {{company_name}} is growing in the Swedish market - congratulations on your progress!</p>

<p>I'm reaching out because we help companies like yours streamline their operations by connecting their CRM and ERP systems. This typically saves our clients 10-15 hours per week on manual data entry.</p>

<p>Would you be open to a quick 15-minute call to see if this could be relevant for {{company_name}}?</p>

<p>Best regards,<br>
Nils</p>"""
                }
            ]
        },
        {
            "seq_number": 2,
            "seq_delay_details": {"delay_in_days": 3},
            "seq_variants": [
                {
                    "variant_label": "A",
                    "subject": "Re: Quick question about {{company_name}}",
                    "email_body": """<p>Hi {{first_name}},</p>

<p>Just wanted to follow up on my previous email.</p>

<p>I understand you're probably busy, but I thought you might find this interesting: one of our clients reduced their order processing time by 40% after implementing our automation solution.</p>

<p>If this sounds relevant, I'd be happy to share more details in a brief call.</p>

<p>Best,<br>
Nils</p>"""
                }
            ]
        },
        {
            "seq_number": 3,
            "seq_delay_details": {"delay_in_days": 4},
            "seq_variants": [
                {
                    "variant_label": "A",
                    "subject": "Last attempt - {{company_name}}",
                    "email_body": """<p>Hi {{first_name}},</p>

<p>I don't want to keep bothering you, so this will be my last email.</p>

<p>If automating your business processes isn't a priority right now, I completely understand. But if you ever want to explore how other Swedish companies are saving time on repetitive tasks, feel free to reach out.</p>

<p>Wishing you and {{company_name}} continued success!</p>

<p>Best regards,<br>
Nils</p>"""
                }
            ]
        }
    ]
}


async def create_campaign_with_sequences():
    """Create a Smartlead campaign and add email sequences."""

    if not SMARTLEAD_API_KEY:
        print("ERROR: SMARTLEAD_API not set in .env")
        print("Please add SMARTLEAD_API=your_api_key to clients/herbox-sweden/automations/.env")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create the campaign
        print("\n" + "=" * 60)
        print("Creating Smartlead Campaign for Herbox")
        print("=" * 60)

        campaign_name = "Herbox - B2B Outreach Sample"

        create_response = await client.post(
            f"{SMARTLEAD_API_URL}/campaigns/create",
            params={"api_key": SMARTLEAD_API_KEY},
            json={"name": campaign_name}
        )

        if create_response.status_code != 200:
            print(f"ERROR: Failed to create campaign")
            print(f"Status: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            sys.exit(1)

        campaign_data = create_response.json()
        campaign_id = campaign_data.get("id")

        if not campaign_id:
            print(f"ERROR: No campaign ID returned")
            print(f"Response: {json.dumps(campaign_data, indent=2)}")
            sys.exit(1)

        print(f"\n Campaign created successfully!")
        print(f"   Campaign ID: {campaign_id}")
        print(f"   Name: {campaign_name}")

        # Step 2: Add email sequences
        print("\n" + "-" * 40)
        print("Adding email sequences...")
        print("-" * 40)

        sequence_response = await client.post(
            f"{SMARTLEAD_API_URL}/campaigns/{campaign_id}/sequences",
            params={"api_key": SMARTLEAD_API_KEY},
            json=SAMPLE_SEQUENCES
        )

        if sequence_response.status_code != 200:
            print(f"ERROR: Failed to add sequences")
            print(f"Status: {sequence_response.status_code}")
            print(f"Response: {sequence_response.text}")
            # Campaign was created, so don't exit - just warn
        else:
            print(f"\n Email sequences added!")
            print(f"   Total sequences: {len(SAMPLE_SEQUENCES['sequences'])}")

            for seq in SAMPLE_SEQUENCES["sequences"]:
                delay = seq["seq_delay_details"]["delay_in_days"]
                subject = seq["seq_variants"][0]["subject"]
                print(f"   - Step {seq['seq_number']}: \"{subject}\" (Day {delay})")

        # Summary
        print("\n" + "=" * 60)
        print("CAMPAIGN SUMMARY")
        print("=" * 60)
        print(f"Campaign ID: {campaign_id}")
        print(f"Campaign Name: {campaign_name}")
        print(f"Status: Draft (ready to configure)")
        print(f"\nNext steps:")
        print(f"1. Go to Smartlead dashboard")
        print(f"2. Add email accounts to the campaign")
        print(f"3. Add leads (or use the automation sync)")
        print(f"4. Configure sending schedule")
        print(f"5. Start the campaign")
        print(f"\nVariables used in copy:")
        print(f"  - {{{{first_name}}}} - Contact's first name")
        print(f"  - {{{{company_name}}}} - Company name")
        print("=" * 60)

        return campaign_id


async def main():
    try:
        campaign_id = await create_campaign_with_sequences()
        print(f"\nDone! Campaign ID: {campaign_id}")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
