"""
Automation A6.1: Apify Scraper Starter

Spec: specs/automations/a6.1-apify-scraper-starter.md
Trigger: POST /webhooks/apify-scraper-starter

Checks queue capacity and starts Apify LinkedIn scraper with proper configuration.
"""

import json
import logging
from typing import Any
from pydantic import BaseModel

from ..clients.airtable import AirtableClient
from ..clients.apify import ApifyClient
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"
AIRTABLE_TABLE_LIST_BUILDING = "tblcFFxDCN0788xjF"
AIRTABLE_TABLE_CONFIG = "tblOizkzkLtBjIpBt"  # Configs table for LinkedIn cookies

# Apify configuration
LINKEDIN_SCRAPER_ID = "7Q2x4Chr5xNR5s4dP"
MAX_CONCURRENT_SCRAPERS = 4

# LinkedIn configuration
# LinkedIn cookies are stored in Airtable config table as:
# - Linkedin_cookie_a (primary)
# - Linkedin_cookie_b (backup)
# - etc.
# Note: Field names have capital L in Airtable
LINKEDIN_COOKIE_FIELDS = ["Linkedin_cookie_a", "Linkedin_cookie_b", "Linkedin_cookie_c"]


class WebhookPayload(BaseModel):
    """Webhook payload from A6 orchestrator."""
    recordId: str


def should_queue(running_count: int, max_count: int) -> bool:
    """Check if scraper should queue based on running count."""
    return running_count >= max_count


def build_linkedin_config(
    list_url: str,
    cookies: list[dict[str, str]],
    user_agent: str,
    max_results: int | None = None,
) -> dict[str, Any]:
    """
    Build LinkedIn scraper configuration.

    Args:
        list_url: LinkedIn Sales Navigator search URL
        cookies: LinkedIn cookies from Cookie-Editor format
        user_agent: Browser user agent string
        max_results: Optional maximum results limit

    Returns:
        Configuration dictionary for Apify actor
    """
    config = {
        "cookie": cookies,
        "searchUrl": list_url,
        "userAgent": user_agent,
        "startPage": 1,
        "minDelay": 2,
        "maxDelay": 5,
        # Proxy configuration (required for this actor)
        "proxy": {
            "useApifyProxy": True,
        },
    }

    if max_results:
        config["count"] = max_results

    return config


class ApifyScraperStarter:
    """
    Starts Apify scrapers with queue capacity management.

    Flow:
    1. Receive record ID from webhook
    2. Fetch list record from Airtable
    3. Check queue capacity (max 4 concurrent)
    4. Build scraper config with LinkedIn credentials
    5. Start Apify actor
    6. Update Airtable with Scraper ID
    """

    automation_id = "a6_1_apify_scraper_starter"

    def __init__(
        self,
        airtable_token: str | None = None,
        apify_token: str | None = None,
    ):
        self.airtable_token = airtable_token or settings.airtable_token
        self.apify_token = apify_token or settings.apify_api_token
        self.airtable_client: AirtableClient | None = None
        self.apify_client: ApifyClient | None = None

    async def _init_clients(self) -> None:
        """Initialize API clients."""
        if not self.airtable_token:
            raise ValueError("AIRTABLE_TOKEN not configured")

        self.airtable_client = AirtableClient(
            token=self.airtable_token,
            base_id=AIRTABLE_BASE_ID,
        )

        if self.apify_token:
            self.apify_client = ApifyClient(token=self.apify_token)

    async def _close_clients(self) -> None:
        """Close API clients."""
        if self.airtable_client:
            await self.airtable_client.close()
        if self.apify_client:
            await self.apify_client.close()

    async def _get_linkedin_cookies(self) -> list[dict[str, Any]]:
        """
        Fetch LinkedIn cookies from Airtable config table.

        The Configs table uses a Field/Value structure where:
        - Field column contains the field name (e.g., "Linkedin_cookie_a")
        - Value column contains the JSON cookies

        Checks multiple cookie fields (linkedin_cookie_a, linkedin_cookie_b, etc.)
        and returns the first available set of valid cookies.

        Returns:
            LinkedIn cookies in Cookie-Editor JSON format

        Raises:
            ValueError: If no valid LinkedIn cookies found in config
        """
        if not self.airtable_client:
            raise ValueError("Airtable client not initialized")

        # Fetch all config records to find cookie fields
        try:
            config_records = await self.airtable_client.search_records(
                table_id=AIRTABLE_TABLE_CONFIG,
                max_records=50,  # Get more records to find cookie fields
            )
        except Exception as e:
            raise ValueError(f"Failed to fetch config table: {e}")

        if not config_records or len(config_records) == 0:
            raise ValueError(
                f"No config records found in Airtable table '{AIRTABLE_TABLE_CONFIG}'. "
                f"Please create config records with Field/Value structure."
            )

        # Build a dict of Field -> Value from all records
        config_map = {}
        for record in config_records:
            field_name = record.fields.get("Field")
            field_value = record.fields.get("Value")
            if field_name and field_value:
                config_map[field_name] = field_value

        # Try each cookie field in order
        for cookie_field in LINKEDIN_COOKIE_FIELDS:
            try:
                cookies_json = config_map.get(cookie_field)

                if not cookies_json:
                    continue

                # Parse the JSON cookies
                cookies = json.loads(cookies_json)

                # Validate cookies have basic structure
                if isinstance(cookies, list) and len(cookies) > 0:
                    logger.info(f"Using LinkedIn cookies from {cookie_field}")
                    return cookies

            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to parse {cookie_field}: {e}")
                continue

        raise ValueError(
            f"No valid LinkedIn cookies found in config table. "
            f"Checked fields: {', '.join(LINKEDIN_COOKIE_FIELDS)}"
        )

    async def run(
        self,
        payload: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Run the automation for a scraper start request.

        Args:
            payload: Webhook payload with recordId
            dry_run: If True, simulate without starting scraper

        Returns:
            Result dictionary with status and details
        """
        exec_logger = ExecutionLogger(self.automation_id, trigger="webhook")

        try:
            # 1. Initialize - Extract record ID
            with exec_logger.step("Initialize") as step:
                record_id = payload.get("recordId")
                if not record_id:
                    raise ValueError("recordId is required in payload")

                step.output_summary = f"Processing list record: {record_id}"
                await self._init_clients()

            # 2. Fetch List Record from Airtable
            with exec_logger.step("Fetch List Record") as step:
                list_record = await self.airtable_client.get_record(
                    table_id=AIRTABLE_TABLE_LIST_BUILDING,
                    record_id=record_id,
                )

                # Extract required fields
                list_url = list_record.fields.get("List URL")
                list_type = list_record.fields.get("List Type")
                max_results = list_record.fields.get("Max Results")

                # Validate required fields
                if not list_url:
                    raise ValueError("List URL is required")
                if not list_type:
                    raise ValueError("List Type is required")

                step.output_summary = f"List: {list_record.fields.get('List Name', 'Unknown')} ({list_type})"

            # 3. Check Queue Capacity
            with exec_logger.step("Check Queue Capacity") as step:
                if not self.apify_client:
                    raise ValueError("APIFY_API_TOKEN not configured")

                running_response = await self.apify_client.get_running_actors()
                running_count = running_response.total
                step.output_summary = f"Running actors: {running_count}/{MAX_CONCURRENT_SCRAPERS}"

                if should_queue(running_count, MAX_CONCURRENT_SCRAPERS):
                    # Queue the scraper
                    await self.airtable_client.update_record(
                        table_id=AIRTABLE_TABLE_LIST_BUILDING,
                        record_id=record_id,
                        fields={"List Status": "Scraper Queued"},
                    )
                    exec_logger.finalize("success")
                    return {
                        "status": "queued",
                        "reason": "max_concurrent_reached",
                        "running_count": running_count,
                        "max_concurrent": MAX_CONCURRENT_SCRAPERS,
                        "dry_run": dry_run,
                    }

            # 4. Build Scraper Configuration
            with exec_logger.step("Build Scraper Config") as step:
                # Get LinkedIn credentials from Airtable config table (or use mock in dry run)
                if dry_run:
                    # Use mock cookies for dry run mode
                    linkedin_cookies = [{"name": "li_at", "value": "DRY_RUN_MOCK_COOKIE"}]
                    step.output_summary = "Using mock cookies (dry run mode)"
                else:
                    linkedin_cookies = await self._get_linkedin_cookies()

                # User agent still from environment (single value, not secret)
                if not settings.linkedin_user_agent:
                    raise ValueError("LINKEDIN_USER_AGENT not configured")
                user_agent = settings.linkedin_user_agent

                # Build config based on list type
                if "LinkedIn" in list_type or "Sales Navigator" in list_type:
                    scraper_config = build_linkedin_config(
                        list_url=list_url,
                        cookies=linkedin_cookies,
                        user_agent=user_agent,
                        max_results=max_results,
                    )
                    actor_id = LINKEDIN_SCRAPER_ID
                else:
                    raise ValueError(f"Unsupported list type: {list_type}")

                if not dry_run:
                    step.output_summary = f"Config built for {list_type}"

            # 5. Start Apify Actor
            with exec_logger.step("Start Apify Actor") as step:
                if dry_run:
                    step.output_summary = "Dry run: would start scraper"
                    exec_logger.finalize("success")
                    return {
                        "status": "dry_run",
                        "would_start": True,
                        "actor_id": actor_id,
                        "config": scraper_config,
                    }

                run = await self.apify_client.start_actor(
                    actor_id=actor_id,
                    input_config=scraper_config,
                    timeout_secs=86400,  # 24 hours
                )
                step.output_summary = f"Started run: {run.id} (status: {run.status})"

            # 6. Update Airtable Status
            with exec_logger.step("Update Airtable") as step:
                await self.airtable_client.update_record(
                    table_id=AIRTABLE_TABLE_LIST_BUILDING,
                    record_id=record_id,
                    fields={
                        "List Status": "Scraper In Progress",
                        "Scraper ID": run.id,
                    },
                )
                step.output_summary = f"Status updated to Scraper In Progress"

            exec_logger.finalize("success")
            return {
                "status": "scraper_started",
                "run_id": run.id,
                "run_status": run.status.value,
                "actor_id": actor_id,
                "list_id": record_id,
            }

        except Exception as e:
            logger.error(f"Apify scraper starter failed: {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

        finally:
            await self._close_clients()


# Allow running directly for testing
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        dry_run = "--dry-run" in sys.argv

        # Example payload for testing
        test_payload = {
            "recordId": "rec123",
        }

        # Check if record ID provided as argument
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                test_payload["recordId"] = arg
                break

        handler = ApifyScraperStarter()
        result = await handler.run(test_payload, dry_run=dry_run)
        print(f"Result: {result}")

    asyncio.run(main())
