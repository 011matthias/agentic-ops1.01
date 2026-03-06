"""
Automation A6.2: Lead Sourcing Completed Handler

Spec: specs/automations/a6.2-lead-sourcing-completed.md
Trigger: POST /webhooks/lead-sourcing-finished

Handles Apify webhook callbacks when scraper runs complete.
Fetches dataset, transforms lead data, and upserts to Airtable.
"""

import logging
from datetime import datetime
from typing import Any
from pydantic import BaseModel

from ..clients.airtable import AirtableClient
from ..clients.apify import ApifyClient, RunStatus
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration
# Note: These should match your Herbox Airtable base
AIRTABLE_BASE_ID = settings.airtable_base_id  # Use from config
AIRTABLE_TABLE_LIST_BUILDING = "tblcFFxDCN0788xjF"
AIRTABLE_TABLE_CONTACTS = "tblsI8jeqv1B16MTk"
AIRTABLE_TABLE_ACCOUNTS = "tblIJVWxf1QbpowuS"

# Processing configuration
BATCH_SIZE = 5


class ApifyWebhookPayload(BaseModel):
    """Apify webhook payload structure."""
    eventType: str
    eventData: dict[str, Any] | None = None
    resource: dict[str, Any] | None = None


class ProcessingSettings(BaseModel):
    """Extracted settings from webhook payload."""
    apify_actor_run_id: str
    apify_actor_dataset_id: str
    apify_actor_status: str


def transform_lead(item: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize lead data from different scraper formats.

    Handles both Apollo and Sales Navigator data formats.
    """
    # Get nested organization data safely
    org = item.get("organization", {}) or {}
    positions = item.get("positions", [])
    first_position = positions[0] if positions else {}

    return {
        "first_name": item.get("first_name") or item.get("firstName", ""),
        "last_name": item.get("last_name") or item.get("lastName", ""),
        "linkedin_url": item.get("linkedin_url") or item.get("publicUrl", ""),
        "email": item.get("email", ""),
        "job_title": item.get("title") or item.get("jobTitle", ""),
        "phone_number": item.get("organization_phone", ""),
        "profile_summary": item.get("summary", ""),
        "profile_headline": item.get("headline", ""),
        "organization_name": org.get("name") or item.get("companyName", ""),
        "organization_industry": org.get("industry", ""),
        "organization_linkedin_url": (
            org.get("linkedin_url") or item.get("companyLinkedinUrl", "")
        ),
        "organization_employee_count": org.get("estimated_num_employees"),
        "organization_hq_address": (
            item.get("organization_raw_address") or
            first_position.get("location", "")
        ),
        "organization_city": item.get("organization_city", ""),
        "organization_website": (
            item.get("organization_website_url") or
            item.get("companyWebsite", "")
        ),
    }


def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class LeadSourcingCompletedHandler:
    """
    Handles Apify scraper run completion webhooks.

    Fetches scraped dataset, transforms lead data to standard format,
    and upserts contacts/accounts to Airtable.
    """

    automation_id = "a6_2_lead_sourcing_completed"

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
        Run the automation for an Apify webhook event.

        Args:
            payload: Apify webhook payload
            dry_run: If True, simulate without making changes

        Returns:
            Result dictionary with status and details
        """
        exec_logger = ExecutionLogger(self.automation_id, trigger="webhook")

        try:
            # 1. Initialize - Extract run details
            with exec_logger.step("Initialize"):
                webhook = ApifyWebhookPayload(**payload)
                event_data = webhook.eventData or {}
                resource = webhook.resource or {}
                proc_settings = ProcessingSettings(
                    apify_actor_run_id=event_data.get("actorRunId") or resource.get("id", ""),
                    apify_actor_dataset_id=resource.get("defaultDatasetId", ""),
                    apify_actor_status=resource.get("status", ""),
                )
                logger.info(f"Processing run: {proc_settings.apify_actor_run_id}")

                await self._init_clients()

            # Check run status - only proceed if SUCCEEDED
            if proc_settings.apify_actor_status != RunStatus.SUCCEEDED.value:
                logger.warning(f"Run did not succeed: {proc_settings.apify_actor_status}")

                # Log error to list record
                await self._log_error_to_list(
                    proc_settings.apify_actor_run_id,
                    f"Scraper run failed with status: {proc_settings.apify_actor_status}",
                    exec_logger,
                )

                exec_logger.finalize("skipped", error="scraper_failed")
                return {
                    "status": "skipped",
                    "reason": "scraper_failed",
                    "run_status": proc_settings.apify_actor_status,
                }

            # 2. Lookup list record by Scraper ID
            with exec_logger.step("Lookup List") as step:
                list_records = await self.airtable_client.search_records(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    formula=f"{{Scraper ID}}='{proc_settings.apify_actor_run_id}'",
                    max_records=1,
                )

                if not list_records:
                    logger.error(f"List not found for Scraper ID: {proc_settings.apify_actor_run_id}")
                    exec_logger.finalize("failed", error="list_not_found")
                    return {
                        "status": "failed",
                        "error": "list_not_found",
                        "scraper_id": proc_settings.apify_actor_run_id,
                    }

                list_record = list_records[0]
                list_id = list_record.id
                list_name = list_record.fields.get("List Name", "Unknown")
                step.output_summary = f"Found list: {list_name}"

            # 3. Fetch dataset from Apify
            with exec_logger.step("Fetch Dataset") as step:
                if not self.apify_client:
                    raise ValueError("APIFY_API_TOKEN not configured")

                try:
                    items = await self.apify_client.get_dataset_items(
                        proc_settings.apify_actor_dataset_id
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch dataset: {e}")
                    await self._log_error_to_list(
                        proc_settings.apify_actor_run_id,
                        f"Dataset fetch failed: {e}",
                        exec_logger,
                    )
                    raise

                step.output_summary = f"Fetched {len(items)} items"

                if not items:
                    logger.warning("Dataset is empty")
                    await self._update_list_status(list_id, "Scraper Completed")
                    exec_logger.finalize("success")
                    return {
                        "status": "success",
                        "processed_count": 0,
                        "message": "Dataset empty",
                        "dry_run": dry_run,
                    }

            # 4. Process batches - transform and upsert
            with exec_logger.step("Process Batches") as step:
                if dry_run:
                    # Transform all items but don't upsert
                    transformed = [transform_lead(item) for item in items]
                    step.output_summary = f"Dry run: would process {len(transformed)} leads"
                    return {
                        "status": "success",
                        "dry_run": True,
                        "would_process_count": len(transformed),
                        "sample_lead": transformed[0] if transformed else None,
                    }

                # First, transform all items
                all_transformed = [transform_lead(item) for item in items]

                # Phase 1: Upsert all unique accounts
                account_records_map = {}
                for lead in all_transformed:
                    if lead["organization_linkedin_url"]:  # Skip if no company LinkedIn
                        url = lead["organization_linkedin_url"]
                        if url not in account_records_map:
                            account_records_map[url] = {
                                "List": [list_id],
                                "Linkedin URL": url,
                                "Account Name": lead["organization_name"],
                                "Industry": lead["organization_industry"],
                                "Employee Count": lead["organization_employee_count"],
                                "Website": lead["organization_website"],
                                "HQ Address": lead["organization_hq_address"],
                                "City": lead["organization_city"],
                            }

                account_records = list(account_records_map.values())
                accounts_upserted = 0

                # Upsert accounts in batches
                for batch in chunks(account_records, BATCH_SIZE):
                    await self.airtable_client.upsert_records(
                        AIRTABLE_TABLE_ACCOUNTS,
                        batch,
                        merge_on=["Linkedin URL"],
                    )
                    accounts_upserted += len(batch)

                # Phase 2: Query accounts to get record IDs for linking
                # Query each account individually (more reliable with special characters)
                account_id_map = {}  # LinkedIn URL -> Account Record ID

                for url in account_records_map.keys():
                    # Use exact match with escaped URL
                    escaped_url = url.replace("'", "\\'")
                    formula = f"{{Linkedin URL}} = '{escaped_url}'"

                    records = await self.airtable_client.search_records(
                        AIRTABLE_TABLE_ACCOUNTS,
                        formula=formula,
                        max_records=1,
                    )

                    if records:
                        account_id_map[url] = records[0].id

                # Phase 3: Upsert contacts with account links
                contacts_upserted = 0

                for batch in chunks(all_transformed, BATCH_SIZE):
                    contact_records = []
                    for lead in batch:
                        if not lead["linkedin_url"]:
                            continue

                        contact_record = {
                            "Email Verified": False,
                            "Linkedin URL": lead["linkedin_url"],
                            "First Name": lead["first_name"],
                            "Last Name": lead["last_name"],
                            "Email": lead["email"],
                            "Title": lead["job_title"],
                            "DEV - Account Name": lead["organization_name"],
                            "List": [list_id],
                        }

                        # Link to account if exists
                        account_url = lead["organization_linkedin_url"]
                        if account_url and account_url in account_id_map:
                            contact_record["Account"] = [account_id_map[account_url]]

                        contact_records.append(contact_record)

                    if contact_records:
                        await self.airtable_client.upsert_records(
                            AIRTABLE_TABLE_CONTACTS,
                            contact_records,
                            merge_on=["Linkedin URL"],
                        )
                        contacts_upserted += len(contact_records)

                step.output_summary = f"Upserted {contacts_upserted} contacts, {accounts_upserted} accounts (with links)"

            # 5. Finalize - update list status
            with exec_logger.step("Finalize") as step:
                await self._update_list_status(list_id, "Scraper Completed")
                step.output_summary = "List status updated"

            exec_logger.finalize("success")
            return {
                "status": "success",
                "contacts_upserted": contacts_upserted,
                "accounts_upserted": accounts_upserted,
                "list_id": list_id,
                "list_name": list_name,
            }

        except Exception as e:
            logger.error(f"Lead sourcing completed handler failed: {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

        finally:
            await self._close_clients()

    async def _update_list_status(self, list_id: str, status: str) -> None:
        """Update the list record status in Airtable."""
        await self.airtable_client.update_record(
            AIRTABLE_TABLE_LIST_BUILDING,
            list_id,
            {"List Status": status},
        )

    async def _log_error_to_list(
        self,
        scraper_id: str,
        error_message: str,
        exec_logger: ExecutionLogger,
    ) -> None:
        """Log error to the list record's Scraper Log field."""
        try:
            with exec_logger.step("Log Error") as step:
                # Find list by Scraper ID
                list_records = await self.airtable_client.search_records(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    formula=f"{{Scraper ID}}='{scraper_id}'",
                    max_records=1,
                )

                if not list_records:
                    logger.warning(f"Cannot log error - list not found for Scraper ID: {scraper_id}")
                    step.output_summary = "List not found for error logging"
                    return

                list_record = list_records[0]
                existing_log = list_record.fields.get("Scraper Log", "") or ""
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

                new_log = (
                    f"{existing_log}\n{timestamp} - Error: {error_message}"
                    if existing_log
                    else f"{timestamp} - Error: {error_message}"
                )

                await self.airtable_client.update_record(
                    AIRTABLE_TABLE_LIST_BUILDING,
                    list_record.id,
                    {"Scraper Log": new_log},
                )
                step.output_summary = f"Error logged to list {list_record.id}"

        except Exception as e:
            logger.error(f"Failed to log error to list: {e}")


# Allow running directly for testing
if __name__ == "__main__":
    import asyncio
    import sys
    import json

    async def main():
        dry_run = "--dry-run" in sys.argv

        # Example payload for testing
        test_payload = {
            "eventType": "ACTOR.RUN.SUCCEEDED",
            "eventData": {"actorRunId": "test123"},
            "resource": {
                "id": "test123",
                "status": "SUCCEEDED",
                "defaultDatasetId": "dataset456",
            },
        }

        # Check if payload JSON file provided
        for arg in sys.argv[1:]:
            if arg.endswith(".json"):
                with open(arg) as f:
                    test_payload = json.load(f)
                break

        handler = LeadSourcingCompletedHandler()
        result = await handler.run(test_payload, dry_run=dry_run)
        print(f"Result: {json.dumps(result, indent=2)}")

    asyncio.run(main())
