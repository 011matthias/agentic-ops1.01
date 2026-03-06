#!/usr/bin/env python3
"""Add email sequences to an existing Smartlead campaign.

Usage:
    cd clients/herbox-sweden/automations
    uv run python scripts/add_sequences_to_campaign.py 2863522

This script adds 3 sample B2B outreach email sequences to an existing campaign.
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


async def add_sequences(campaign_id: int):
    """Add email sequences to an existing campaign."""

    if not SMARTLEAD_API_KEY:
        print("ERROR: SMARTLEAD_API not set in .env")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n{'='*60}")
        print(f"Adding Sequences to Campaign {campaign_id}")
        print(f"{'='*60}")

        response = await client.post(
            f"{SMARTLEAD_API_URL}/campaigns/{campaign_id}/sequences",
            params={"api_key": SMARTLEAD_API_KEY},
            json=SAMPLE_SEQUENCES
        )

        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print(f"\n Email sequences added successfully!")
            print(f"\nSequences:")
            for seq in SAMPLE_SEQUENCES["sequences"]:
                delay = seq["seq_delay_details"]["delay_in_days"]
                subject = seq["seq_variants"][0]["subject"]
                print(f"   - Step {seq['seq_number']}: \"{subject}\" (Day {delay})")
        else:
            print(f"\n ERROR: Failed to add sequences")


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/add_sequences_to_campaign.py <campaign_id>")
        print("Example: uv run python scripts/add_sequences_to_campaign.py 2863522")
        sys.exit(1)

    try:
        campaign_id = int(sys.argv[1])
    except ValueError:
        print(f"Invalid campaign ID: {sys.argv[1]}")
        sys.exit(1)

    await add_sequences(campaign_id)


if __name__ == "__main__":
    asyncio.run(main())
