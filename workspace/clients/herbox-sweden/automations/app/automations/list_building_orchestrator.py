"""
Automation A6: List Building Orchestrator

Spec: specs/automations/a6-list-building.md
Trigger: POST /webhooks/list-status-changed

Pure orchestrator that watches Airtable record status changes and
delegates to appropriate sub-automations. Contains no business logic.
"""

import json
import logging
from enum import Enum
from typing import Any
from pydantic import BaseModel

from ..clients.airtable import AirtableClient
from ..clients.apify import ApifyClient
from ..logger import ExecutionLogger
from ..config import get_settings

# Import sub-automations for orchestration
from .contact_enrichment import ContactEnrichment
from .data_cleaning import run_data_cleaning

logger = logging.getLogger(__name__)
settings = get_settings()


# Configuration constants
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"
AIRTABLE_TABLE_LIST_BUILDING = "tblcFFxDCN0788xjF"
AIRTABLE_TABLE_CONFIG = "tblOizkzkLtBjIpBt"  # Configs table for LinkedIn credentials
MAX_CONCURRENT_SCRAPERS = 4
LINKEDIN_SCRAPER_ID = "7Q2x4Chr5xNR5s4dP"
APOLLO_SCRAPER_ID = "3HXDJqKfVlhmEHt7A"

# LinkedIn credentials from Airtable Configs table
# Will try each in order until one works
LINKEDIN_COOKIE_FIELDS = [
    "Linkedin_cookie_a",
    "Linkedin_cookie_b",
    "Linkedin_cookie_c",
    "Linkedin_cookie_d",
]
LINKEDIN_USER_AGENT_FIELDS = [
    "linkedin_user_agent_a",
]


def should_queue_scraper(running: int, max_allowed: int = MAX_CONCURRENT_SCRAPERS) -> bool:
    """Check if scraper should be queued due to capacity."""
    return running >= max_allowed


def build_apollo_config(record: "ListRecord") -> dict[str, Any]:
    """Build Apollo scraper configuration."""
    return {
        "url": record.list_url,
        "getPersonalEmails": True,
        "getWorkEmails": True,
    }


def build_sales_nav_config(
    record: "ListRecord",
    cookies: list[dict[str, Any]],
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
) -> dict[str, Any]:
    """Build LinkedIn Sales Navigator scraper configuration."""
    config: dict[str, Any] = {
        "searchUrl": record.list_url,
        "cookie": cookies,  # Cookie-Editor JSON format
        "deepScrape": True,
        "minDelay": 5,
        "maxDelay": 30,
        "userAgent": user_agent,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyCountry": "US",
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }
    if record.max_results:
        config["count"] = record.max_results
    return config


# Alias for backwards compatibility
build_linkedin_config = build_sales_nav_config


class ListStatus(str, Enum):
    """List status values from Airtable."""
    SCRAPER_STARTED = "Scraper Started"
    SCRAPER_QUEUED = "Scraper Queued"
    SCRAPER_IN_PROGRESS = "Scraper In Progress"
    LIST_STANDARDIZATION = "List Standardization"
    ENRICHMENT_STARTED = "Enrichment & Verification Started"
    LIST_CLEANING = "List Cleaning Started"
    UPLOAD_TO_SEQUENCER = "Upload to Email Sequencer"


class ListType(str, Enum):
    """List type values from Airtable."""
    APOLLO = "Apify - Apollo"
    SALES_NAV = "Apify - Sales Navigator"


class SubFlow(str, Enum):
    """Sub-flow identifiers."""
    LEAD_SOURCING = "lead_sourcing"
    STANDARDIZATION = "standardization"
    ENRICHMENT = "enrichment"
    CLEANING = "cleaning"
    UPLOAD = "upload"


class WebhookPayload(BaseModel):
    """Webhook payload from Airtable."""
    recordId: str


class ListRecord(BaseModel):
    """Airtable list building record."""
    id: str
    list_name: str | None = None
    list_status: str | None = None
    list_type: str | None = None
    list_url: str | None = None
    max_results: int | None = None
    scraper_id: str | None = None

    @classmethod
    def from_airtable(cls, record_id: str, fields: dict[str, Any]) -> "ListRecord":
        """Create from Airtable record fields."""
        return cls(
            id=record_id,
            list_name=fields.get("List Name"),
            list_status=fields.get("List Status"),
            list_type=fields.get("List Type"),
            list_url=fields.get("List URL"),
            max_results=fields.get("Max Results"),
            scraper_id=fields.get("Scraper ID"),
        )


def get_sub_flow(status: str) -> SubFlow | None:
    """Route status to appropriate sub-flow."""
    routing = {
        ListStatus.SCRAPER_STARTED.value: SubFlow.LEAD_SOURCING,
        ListStatus.SCRAPER_QUEUED.value: SubFlow.LEAD_SOURCING,  # Re-check queue
        ListStatus.LIST_STANDARDIZATION.value: SubFlow.STANDARDIZATION,
        ListStatus.ENRICHMENT_STARTED.value: SubFlow.ENRICHMENT,
        ListStatus.LIST_CLEANING.value: SubFlow.CLEANING,
        ListStatus.UPLOAD_TO_SEQUENCER.value: SubFlow.UPLOAD,
    }
    return routing.get(status)


class ListBuildingOrchestrator:
    """
    Pure orchestrator for the list building pipeline.

    Handles webhook events from Airtable when List Status changes,
    delegates to appropriate sub-automation.
    """

    automation_id = "a6_list_building"

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

    async def run(
        self,
        payload: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Run the orchestrator for a webhook event.

        Args:
            payload: Webhook payload with recordId
            dry_run: If True, simulate without making changes

        Returns:
            Result dictionary with status and details
        """
        exec_logger = ExecutionLogger(self.automation_id, trigger="webhook")

        try:
            # Validate payload
            if "recordId" not in payload:
                logger.error("Missing recordId in payload")
                exec_logger.finalize("failed", error="missing_record_id")
                return {"error": "missing_record_id", "message": "Payload must contain recordId"}

            record_id = payload["recordId"]
            logger.info(f"Processing list record: {record_id}")

            with exec_logger.step("Initialize"):
                await self._init_clients()

            # Fetch the record
            with exec_logger.step("Fetch record") as step:
                airtable_record = await self.airtable_client.get_record(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    record_id,
                )
                record = ListRecord.from_airtable(record_id, airtable_record.fields)
                step.output_summary = f"Record: {record.list_name} ({record.list_status})"

            # Route to sub-flow
            with exec_logger.step("Route by status") as step:
                sub_flow = get_sub_flow(record.list_status)
                if not sub_flow:
                    logger.warning(f"Unknown status: {record.list_status}")
                    exec_logger.finalize("skipped", error=f"Unknown status: {record.list_status}")
                    return {
                        "status": "skipped",
                        "reason": f"No handler for status: {record.list_status}",
                    }
                step.output_summary = f"Routing to: {sub_flow.value}"

            # Execute sub-flow
            result: dict[str, Any]

            if sub_flow == SubFlow.LEAD_SOURCING:
                result = await self._handle_lead_sourcing(record, dry_run, exec_logger)
            elif sub_flow == SubFlow.STANDARDIZATION:
                result = await self._handle_standardization(record, dry_run, exec_logger)
            elif sub_flow == SubFlow.ENRICHMENT:
                result = await self._handle_enrichment(record, dry_run, exec_logger)
            elif sub_flow == SubFlow.CLEANING:
                result = await self._handle_cleaning(record, dry_run, exec_logger)
            elif sub_flow == SubFlow.UPLOAD:
                result = await self._handle_upload(record, dry_run, exec_logger)
            else:
                result = {"status": "unknown_flow"}

            exec_logger.finalize("success")
            return result

        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

        finally:
            await self._close_clients()

    async def _handle_lead_sourcing(
        self,
        record: ListRecord,
        dry_run: bool,
        exec_logger: ExecutionLogger,
    ) -> dict[str, Any]:
        """Handle Scraper Started status - Lead Sourcing flow."""
        logger.info(f"Lead sourcing flow for: {record.list_name}")

        # Validate required fields
        if not record.list_url:
            logger.error("Missing List URL")
            return {"error": "missing_list_url", "record_id": record.id}

        if not record.list_type:
            logger.error("Missing List Type")
            return {"error": "missing_list_type", "record_id": record.id}

        # Check scraper queue capacity
        with exec_logger.step("Check queue capacity") as step:
            if not self.apify_client:
                return {"error": "apify_not_configured"}

            running_actors = await self.apify_client.get_running_actors()
            running_count = running_actors.total
            step.output_summary = f"{running_count} scrapers running"

            if should_queue_scraper(running_count, MAX_CONCURRENT_SCRAPERS):
                logger.info(f"Queueing scraper - {running_count} already running")

                if not dry_run:
                    await self.airtable_client.update_record(
                        AIRTABLE_TABLE_LIST_BUILDING,
                        record.id,
                        {"List Status": ListStatus.SCRAPER_QUEUED.value},
                    )

                return {
                    "status": "queued",
                    "reason": f"Max concurrent scrapers ({MAX_CONCURRENT_SCRAPERS}) reached",
                    "running_count": running_count,
                    "dry_run": dry_run,
                }

        # Build scraper config
        with exec_logger.step("Configure scraper") as step:
            if record.list_type == ListType.APOLLO.value:
                scraper_id = APOLLO_SCRAPER_ID
                scraper_config = build_apollo_config(record)
                step.output_summary = "Apollo scraper configured"
            elif record.list_type == ListType.SALES_NAV.value:
                # Get LinkedIn credentials from Airtable Configs table
                linkedin_cookies, user_agent = await self._get_linkedin_credentials()
                if not linkedin_cookies or not user_agent:
                    return {"error": "linkedin_credentials_not_configured"}
                scraper_id = LINKEDIN_SCRAPER_ID
                scraper_config = build_sales_nav_config(record, linkedin_cookies, user_agent)
                step.output_summary = "Sales Navigator scraper configured"
            else:
                logger.error(f"Invalid List Type: {record.list_type}")
                return {"error": "invalid_list_type", "list_type": record.list_type}

        # Start the scraper
        with exec_logger.step("Start scraper") as step:
            if dry_run:
                step.output_summary = f"Would start scraper {scraper_id}"
                return {
                    "status": "would_start_scraper",
                    "scraper_id": scraper_id,
                    "config": scraper_config,
                    "dry_run": True,
                }

            run = await self.apify_client.start_actor(scraper_id, scraper_config)
            step.output_summary = f"Started run: {run.id}"

        # Update Airtable with scraper ID
        with exec_logger.step("Update Airtable") as step:
            await self.airtable_client.update_record(
                AIRTABLE_TABLE_LIST_BUILDING,
                record.id,
                {
                    "List Status": ListStatus.SCRAPER_IN_PROGRESS.value,
                    "Scraper ID": run.id,
                },
            )
            step.output_summary = f"Updated status to In Progress"

        return {
            "status": "scraper_started",
            "run_id": run.id,
            "scraper_id": scraper_id,
            "record_id": record.id,
        }

    async def _get_linkedin_credentials(self) -> tuple[list[dict[str, Any]] | None, str | None]:
        """
        Get LinkedIn credentials from Airtable Configs table.

        Fetches cookies and user agent from Airtable, trying each configured
        cookie field in order until finding valid credentials.

        Returns:
            Tuple of (cookies_list, user_agent) or (None, None) if not configured
        """
        if not self.airtable_client:
            logger.error("Airtable client not initialized")
            return None, None

        # Fetch all config records
        try:
            config_records = await self.airtable_client.search_records(
                table_id=AIRTABLE_TABLE_CONFIG,
                max_records=50,
            )
        except Exception as e:
            logger.error(f"Failed to fetch config table: {e}")
            return None, None

        if not config_records:
            logger.error("No config records found in Airtable")
            return None, None

        # Build a dict of Field -> Value from all records
        config_map = {}
        for record in config_records:
            field_name = record.fields.get("Field")
            field_value = record.fields.get("Value")
            if field_name and field_value:
                config_map[field_name] = field_value

        # Get user agent (try each configured field)
        user_agent = None
        for ua_field in LINKEDIN_USER_AGENT_FIELDS:
            if ua_field in config_map:
                user_agent = config_map[ua_field]
                logger.info(f"Using user agent from {ua_field}")
                break

        if not user_agent:
            logger.error(f"No user agent found. Checked: {LINKEDIN_USER_AGENT_FIELDS}")
            return None, None

        # Try each cookie field in order until finding valid cookies
        for cookie_field in LINKEDIN_COOKIE_FIELDS:
            try:
                cookies_json = config_map.get(cookie_field)
                if not cookies_json:
                    continue

                cookies = json.loads(cookies_json)
                if isinstance(cookies, list) and len(cookies) > 0:
                    logger.info(f"Using LinkedIn cookies from {cookie_field}")
                    return cookies, user_agent

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {cookie_field}: {e}")
                continue

        logger.error(f"No valid LinkedIn cookies found. Checked: {LINKEDIN_COOKIE_FIELDS}")
        return None, None

    async def _handle_standardization(
        self,
        record: ListRecord,
        dry_run: bool,
        exec_logger: ExecutionLogger,
    ) -> dict[str, Any]:
        """Handle List Standardization status."""
        # TODO: Implement standardization sub-workflow
        logger.info(f"Standardization flow for: {record.list_name}")
        with exec_logger.step("Standardization (not implemented)") as step:
            step.output_summary = "Sub-workflow pending implementation"
        return {
            "status": "not_implemented",
            "sub_flow": "standardization",
            "record_id": record.id,
        }

    async def _handle_enrichment(
        self,
        record: ListRecord,
        dry_run: bool,
        exec_logger: ExecutionLogger,
    ) -> dict[str, Any]:
        """
        Handle Enrichment & Verification Started status.

        Calls A6.3 ContactEnrichment for contacts linked to this list.
        """
        logger.info(f"Enrichment flow for: {record.list_name}")

        with exec_logger.step("Run Contact Enrichment (A6.3)") as step:
            enrichment = ContactEnrichment()
            result = await enrichment.run(dry_run=dry_run, list_id=record.id)
            step.output_summary = (
                f"Processed: {result.get('processed_count', 0)}, "
                f"Enriched: {result.get('enriched_count', 0)}, "
                f"Errors: {result.get('error_count', 0)}"
            )

        # Update list status to next step if not dry run
        if not dry_run and result.get("status") == "success":
            with exec_logger.step("Update List Status") as step:
                await self.airtable_client.update_record(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    record.id,
                    {"List Status": "Enrichment Completed"},
                )
                step.output_summary = "Status updated to 'Enrichment Completed'"

        return {
            "status": "enrichment_completed",
            "sub_flow": "enrichment",
            "record_id": record.id,
            "list_name": record.list_name,
            "dry_run": dry_run,
            **result,
        }

    async def _handle_cleaning(
        self,
        record: ListRecord,
        dry_run: bool,
        exec_logger: ExecutionLogger,
    ) -> dict[str, Any]:
        """
        Handle List Cleaning Started status.

        Calls A6.4 Data Cleaning for accounts/contacts linked to this list.
        """
        logger.info(f"Cleaning flow for: {record.list_name}")

        with exec_logger.step("Run Data Cleaning (A6.4)") as step:
            result = await run_data_cleaning(dry_run=dry_run, list_id=record.id)
            step.output_summary = (
                f"Accounts: {result.get('accounts_cleaned', 0)}/{result.get('accounts_found', 0)}, "
                f"Contacts: {result.get('contacts_cleaned', 0)}/{result.get('contacts_found', 0)}"
            )

        # Update list status to next step if not dry run
        if not dry_run:
            with exec_logger.step("Update List Status") as step:
                await self.airtable_client.update_record(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    record.id,
                    {"List Status": "Cleaning Completed"},
                )
                step.output_summary = "Status updated to 'Cleaning Completed'"

        return {
            "status": "cleaning_completed",
            "sub_flow": "cleaning",
            "record_id": record.id,
            "list_name": record.list_name,
            "dry_run": dry_run,
            **result,
        }

    async def _handle_upload(
        self,
        record: ListRecord,
        dry_run: bool,
        exec_logger: ExecutionLogger,
    ) -> dict[str, Any]:
        """Handle Upload to Email Sequencer status."""
        # TODO: Implement upload sub-workflow
        logger.info(f"Upload flow for: {record.list_name}")
        with exec_logger.step("Upload (not implemented)") as step:
            step.output_summary = "Sub-workflow pending implementation"
        return {
            "status": "not_implemented",
            "sub_flow": "upload",
            "record_id": record.id,
        }


# Allow running directly for testing
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        dry_run = "--dry-run" in sys.argv
        record_id = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].startswith("--") else None

        if not record_id:
            print("Usage: python -m app.automations.list_building_orchestrator <record_id> [--dry-run]")
            sys.exit(1)

        orchestrator = ListBuildingOrchestrator()
        result = await orchestrator.run({"recordId": record_id}, dry_run=dry_run)
        print(f"Result: {result}")

    asyncio.run(main())
