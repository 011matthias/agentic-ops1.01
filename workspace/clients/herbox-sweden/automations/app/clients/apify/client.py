"""
Apify API client for managing actor runs.

API Reference: https://docs.apify.com/api/v2
Rate Limit: ~100 requests per minute
"""

import httpx
import asyncio
import logging
from typing import Any
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

APIFY_API_URL = "https://api.apify.com/v2"


class RunStatus(str, Enum):
    """Apify actor run statuses."""
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    TIMING_OUT = "TIMING-OUT"
    TIMED_OUT = "TIMED-OUT"


class ActorRun(BaseModel):
    """Apify actor run model."""
    id: str
    act_id: str | None = None
    status: RunStatus
    started_at: str | None = None
    finished_at: str | None = None


class ActorRunsResponse(BaseModel):
    """Response from list actor runs endpoint."""
    total: int
    items: list[ActorRun]


class ApifyClient:
    """
    Async Apify API client.

    Usage:
        client = ApifyClient(token="apify_api_...")
        runs = await client.get_running_actors()
        run = await client.start_actor(actor_id, config)
    """

    def __init__(self, token: str):
        self.token = token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=APIFY_API_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
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
        """Make API request with retry logic."""
        client = await self._get_client()

        for attempt in range(retries):
            try:
                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Apify API error: {e.response.status_code} - {e.response.text}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                logger.error(f"Apify request error: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def get_running_actors(self) -> ActorRunsResponse:
        """
        Get count and list of currently running actor runs.

        Returns:
            ActorRunsResponse with total count and list of running actors
        """
        logger.info("Fetching running actor runs")
        data = await self._request(
            "GET",
            "/actor-runs",
            params={"status": "RUNNING"},
        )

        items = [
            ActorRun(
                id=item["id"],
                act_id=item.get("actId"),
                status=RunStatus(item["status"]),
                started_at=item.get("startedAt"),
                finished_at=item.get("finishedAt"),
            )
            for item in data.get("data", {}).get("items", [])
        ]

        return ActorRunsResponse(
            total=data.get("data", {}).get("total", 0),
            items=items,
        )

    async def start_actor(
        self,
        actor_id: str,
        input_config: dict[str, Any],
        *,
        timeout_secs: int = 86400,  # 24 hours default
    ) -> ActorRun:
        """
        Start an actor run with the given configuration.

        Args:
            actor_id: Actor ID (e.g., "jljBwyyQakqrL1wae")
            input_config: Actor input configuration
            timeout_secs: Run timeout in seconds (default 24h)

        Returns:
            ActorRun with the new run's details
        """
        logger.info(f"Starting actor {actor_id}")
        data = await self._request(
            "POST",
            f"/acts/{actor_id}/runs",
            params={"timeout": timeout_secs},
            json=input_config,
        )

        run_data = data.get("data", {})
        return ActorRun(
            id=run_data["id"],
            act_id=run_data.get("actId"),
            status=RunStatus(run_data["status"]),
            started_at=run_data.get("startedAt"),
            finished_at=run_data.get("finishedAt"),
        )

    async def get_run(self, run_id: str) -> ActorRun:
        """
        Get details of a specific actor run.

        Args:
            run_id: Run ID

        Returns:
            ActorRun with current status
        """
        logger.info(f"Fetching run {run_id}")
        data = await self._request("GET", f"/actor-runs/{run_id}")

        run_data = data.get("data", {})
        return ActorRun(
            id=run_data["id"],
            act_id=run_data.get("actId"),
            status=RunStatus(run_data["status"]),
            started_at=run_data.get("startedAt"),
            finished_at=run_data.get("finishedAt"),
        )

    async def abort_run(self, run_id: str) -> ActorRun:
        """
        Abort a running actor.

        Args:
            run_id: Run ID to abort

        Returns:
            ActorRun with updated status
        """
        logger.info(f"Aborting run {run_id}")
        data = await self._request("POST", f"/actor-runs/{run_id}/abort")

        run_data = data.get("data", {})
        return ActorRun(
            id=run_data["id"],
            act_id=run_data.get("actId"),
            status=RunStatus(run_data["status"]),
            started_at=run_data.get("startedAt"),
            finished_at=run_data.get("finishedAt"),
        )

    async def get_dataset_items(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get items from a dataset.

        Args:
            dataset_id: Dataset ID (e.g., "Pj8FRjHZu9KxRvMiZ")
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of dataset items as dictionaries
        """
        logger.info(f"Fetching dataset items: {dataset_id}")

        params: dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        client = await self._get_client()

        # Dataset items endpoint returns array directly, not wrapped in data
        response = await client.get(
            f"/datasets/{dataset_id}/items",
            params=params,
        )
        response.raise_for_status()

        items = response.json()
        logger.info(f"Fetched {len(items)} items from dataset")
        return items
