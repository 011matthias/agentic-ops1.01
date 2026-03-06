#!/usr/bin/env python3
"""Reset test list for re-running A6.2 test."""

import asyncio
import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID = "app4gZ66mB8m3Vvj0"
LIST_TABLE = "tblcFFxDCN0788xjF"
RECORD_ID = "rec6feTHf4u1OmMu1"


async def reset_list():
    url = f"https://api.airtable.com/v0/{BASE_ID}/{LIST_TABLE}/{RECORD_ID}"

    async with httpx.AsyncClient() as client:
        # Reset status to Scraper Started
        response = await client.patch(
            url,
            headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"},
            json={"fields": {"List Status": "Scraper Started"}}
        )
        print(f"Status reset: {response.status_code}")

        if response.status_code == 200:
            print("Test list ready for re-run")
            print(f"List Status: Scraper Started")


if __name__ == "__main__":
    asyncio.run(reset_list())
