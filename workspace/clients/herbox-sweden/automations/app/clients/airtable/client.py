"""
Airtable API client with rate limiting and retry logic.

API Reference: https://airtable.com/developers/web/api/introduction
Rate Limit: 5 requests per second per base
"""

import httpx
import asyncio
import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

AIRTABLE_API_URL = "https://api.airtable.com/v0"


class AirtableRecord(BaseModel):
    """Airtable record model."""
    id: str
    fields: dict[str, Any]
    created_time: str | None = None


class AirtableClient:
    """
    Async Airtable API client.

    Usage:
        client = AirtableClient(token="pat...", base_id="app...")
        record = await client.get_record(table_id, record_id)
        await client.update_record(table_id, record_id, {"Status": "Done"})
    """

    def __init__(self, token: str, base_id: str):
        self.token = token
        self.base_id = base_id
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_delay = 0.2  # 5 req/sec = 200ms between requests

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=AIRTABLE_API_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Make API request with rate limiting and retry."""
        client = await self._get_client()
        url = f"/{self.base_id}/{path}"

        for attempt in range(retries):
            try:
                # Rate limiting
                await asyncio.sleep(self._rate_limit_delay)

                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Airtable API error: {e.response.status_code} - {e.response.text}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.RequestError as e:
                logger.error(f"Airtable request error: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def get_record(self, table_id: str, record_id: str) -> AirtableRecord:
        """
        Get a single record by ID.

        Args:
            table_id: Table ID (e.g., tblXXX)
            record_id: Record ID (e.g., recXXX)

        Returns:
            AirtableRecord with id, fields, created_time
        """
        logger.info(f"Fetching record {record_id} from table {table_id}")
        data = await self._request("GET", f"{table_id}/{record_id}")
        return AirtableRecord(
            id=data["id"],
            fields=data["fields"],
            created_time=data.get("createdTime"),
        )

    async def update_record(
        self,
        table_id: str,
        record_id: str,
        fields: dict[str, Any],
    ) -> AirtableRecord:
        """
        Update a record's fields.

        Args:
            table_id: Table ID
            record_id: Record ID
            fields: Dictionary of field names to new values

        Returns:
            Updated AirtableRecord
        """
        logger.info(f"Updating record {record_id} in table {table_id}")
        data = await self._request(
            "PATCH",
            f"{table_id}/{record_id}",
            json={"fields": fields},
        )
        return AirtableRecord(
            id=data["id"],
            fields=data["fields"],
            created_time=data.get("createdTime"),
        )

    async def search_records(
        self,
        table_id: str,
        *,
        formula: str | None = None,
        max_records: int | None = None,
        view: str | None = None,
    ) -> list[AirtableRecord]:
        """
        Search records with optional filter formula.

        Args:
            table_id: Table ID
            formula: Airtable formula for filtering (e.g., "{Status}='Active'")
            max_records: Maximum number of records to return
            view: View ID or name to use

        Returns:
            List of matching AirtableRecords
        """
        logger.info(f"Searching records in table {table_id}")
        params: dict[str, Any] = {}
        if formula:
            params["filterByFormula"] = formula
        if max_records:
            params["maxRecords"] = max_records
        if view:
            params["view"] = view

        records: list[AirtableRecord] = []
        offset: str | None = None

        while True:
            if offset:
                params["offset"] = offset

            data = await self._request("GET", table_id, params=params)

            for record in data.get("records", []):
                records.append(AirtableRecord(
                    id=record["id"],
                    fields=record["fields"],
                    created_time=record.get("createdTime"),
                ))

            offset = data.get("offset")
            if not offset:
                break

        logger.info(f"Found {len(records)} records")
        return records

    async def upsert_records(
        self,
        table_id: str,
        records: list[dict[str, Any]],
        merge_on: list[str],
    ) -> list[AirtableRecord]:
        """
        Upsert records - update existing or create new.

        Args:
            table_id: Table ID
            records: List of field dictionaries to upsert
            merge_on: Field names to match existing records on

        Returns:
            List of upserted AirtableRecords
        """
        logger.info(f"Upserting {len(records)} records to table {table_id}")

        # Airtable upsert allows max 10 records per request
        batch_size = 10
        results: list[AirtableRecord] = []

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            data = await self._request(
                "PATCH",
                table_id,
                json={
                    "performUpsert": {
                        "fieldsToMergeOn": merge_on,
                    },
                    "records": [{"fields": r} for r in batch],
                },
            )

            for record in data.get("records", []):
                results.append(AirtableRecord(
                    id=record["id"],
                    fields=record["fields"],
                    created_time=record.get("createdTime"),
                ))

        logger.info(f"Upserted {len(results)} records")
        return results
