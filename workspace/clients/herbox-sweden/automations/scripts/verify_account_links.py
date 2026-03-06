#!/usr/bin/env python3
"""Verify contacts are linked to accounts."""

import asyncio
import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = "app4gZ66mB8m3Vvj0"
CONTACTS_TABLE = "tblsI8jeqv1B16MTk"


async def verify_links():
    """Check if contacts have account links."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{CONTACTS_TABLE}"

    async with httpx.AsyncClient() as client:
        # Get recent contacts from our test list
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"},
            params={"maxRecords": 5}
        )

        data = response.json()

        print("\n" + "="*60)
        print("CONTACT TO ACCOUNT LINK VERIFICATION")
        print("="*60 + "\n")

        for record in data.get("records", []):
            fields = record["fields"]
            name = f"{fields.get('First Name', '')} {fields.get('Last Name', '')}"
            company = fields.get("DEV - Account Name", "N/A")
            account_link = fields.get("Account", None)

            print(f"Contact: {name}")
            print(f"  Company: {company}")
            print(f"  Account Link: {'✅ YES' if account_link else '❌ NO'}")
            if account_link:
                print(f"  Account ID: {account_link[0]}")
            print()


if __name__ == "__main__":
    asyncio.run(verify_links())
