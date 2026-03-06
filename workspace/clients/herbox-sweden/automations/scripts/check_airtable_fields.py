#!/usr/bin/env python3
"""Check actual field names in Airtable List Building table."""

# /// script
# dependencies = [
#     "httpx",
#     "pydantic",
#     "python-dotenv",
# ]
# ///

import asyncio
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = "app4gZ66mB8m3Vvj0"
TABLE_ID = "tblcFFxDCN0788xjF"


async def check_fields():
    """Fetch and display field names from Airtable."""
    print(f"\n{'='*60}")
    print("AIRTABLE FIELD CHECK")
    print(f"{'='*60}\n")
    print(f"Base ID: {BASE_ID}")
    print(f"Table ID: {TABLE_ID}\n")

    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"},
            params={"maxRecords": 1}
        )

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return

        data = response.json()

        if not data.get("records"):
            print("⚠️  No records found in table")
            return

        record = data["records"][0]

        print("="*60)
        print("ACTUAL FIELD NAMES IN YOUR TABLE")
        print("="*60)
        print(f"\nFound {len(record['fields'])} fields:\n")

        for i, (key, value) in enumerate(record["fields"].items(), 1):
            value_preview = str(value)[:50] if value else "(empty)"
            if len(str(value)) > 50:
                value_preview += "..."
            print(f"  {i:2d}. {key}")
            print(f"      Value: {value_preview}\n")

        print("="*60)
        print("STATUS FIELD CHECK")
        print("="*60)

        # Look for status-related fields
        status_fields = [k for k in record["fields"].keys()
                        if "status" in k.lower() or "state" in k.lower()]

        if status_fields:
            print(f"\n✅ Found status-related fields:")
            for field in status_fields:
                print(f"  - {field}")
        else:
            print("\n❌ No status-related fields found!")
            print("   You may need to create a 'List Status' field in Airtable")


if __name__ == "__main__":
    asyncio.run(check_fields())
