"""
Automation A7: Smartlead Campaign Sync

Spec: specs/automations/a7-smartlead-campaign-sync.md
Trigger: CRON daily at 10:00 Stockholm time

Syncs all Smartlead campaign analytics to Airtable Campaigns table.
"""

import asyncio
import logging
from typing import Any

from .base import BaseAutomation
from ..clients.smartlead import SmartleadClient
from ..clients.airtable import AirtableClient
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration (from spec)
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"  # Herbox Base
AIRTABLE_TABLE_ID = "tbl78Dq8VtWYjxsya"  # Campaigns
AIRTABLE_MATCH_FIELD = "Campaign ID"

# Rate limit delay between campaigns (2s as per spec)
CAMPAIGN_DELAY_SECONDS = 2


def transform_status(status: str) -> str:
    """
    Transform status to sentence case.

    Examples:
        "ACTIVE" -> "Active"
        "completed" -> "Completed"
        "ramp_up" -> "Ramp Up"
    """
    if not status:
        return "Unknown"

    # Replace underscores with spaces
    status = status.replace("_", " ")

    # Title case each word
    return status.title()


def map_to_airtable(campaign_id: int, analytics: dict[str, Any]) -> dict[str, Any]:
    """
    Map Smartlead analytics to Airtable field names.

    Args:
        campaign_id: Smartlead campaign ID
        analytics: CampaignAnalytics as dict

    Returns:
        Dictionary with Airtable field names
    """
    lead_stats = analytics.get("campaign_lead_stats", {})

    return {
        "Campaign ID": str(campaign_id),
        "Campaign Name": analytics.get("name", ""),
        "Status": transform_status(analytics.get("status", "")),
        "Total Leads": lead_stats.get("total", 0),
        "Leads In Progress": lead_stats.get("inprogress", 0),
        "Leads Completed": lead_stats.get("completed", 0),
        "Leads Not Started": lead_stats.get("notStarted", 0),
        "Email Replied (Positive)": lead_stats.get("interested", 0),
        "Prospects Contacted": analytics.get("unique_sent_count", 0),
        "Email Sent": analytics.get("sent_count", 0),
        "Email Opened": analytics.get("open_count", 0),
        "Email Replied": analytics.get("reply_count", 0),
        "Email Bounced": analytics.get("bounce_count", 0),
        "Total Emails": lead_stats.get("total", 0),
        "Number Of Sequences": analytics.get("sequence_count", 0),
    }


class SmartleadCampaignSync(BaseAutomation):
    """
    Syncs Smartlead campaign analytics to Airtable.

    Runs daily at 10:00 Stockholm time. Fetches all campaigns,
    retrieves detailed analytics for each, and upserts to Airtable
    using Campaign ID as the match key.
    """

    automation_id = "a7_smartlead_campaign_sync"

    def __init__(
        self,
        smartlead_api_key: str | None = None,
        airtable_token: str | None = None,
        airtable_base_id: str | None = None,
    ):
        self.smartlead_api_key = smartlead_api_key or settings.smartlead_api
        self.airtable_token = airtable_token or settings.airtable_token
        self.airtable_base_id = airtable_base_id or AIRTABLE_BASE_ID

        self.smartlead_client: SmartleadClient | None = None
        self.airtable_client: AirtableClient | None = None

        # Track sync results
        self._campaigns_synced: list[dict[str, Any]] = []
        self._campaigns_failed: list[dict[str, Any]] = []

    def initialize(self) -> None:
        """Initialize API clients."""
        if not self.smartlead_api_key:
            raise ValueError("SMARTLEAD_API_KEY not configured")
        if not self.airtable_token:
            raise ValueError("AIRTABLE_TOKEN not configured")

        self.smartlead_client = SmartleadClient(api_key=self.smartlead_api_key)
        self.airtable_client = AirtableClient(
            token=self.airtable_token,
            base_id=self.airtable_base_id,
        )

    def fetch_data(self) -> Any:
        """Fetch campaign list from Smartlead (sync wrapper)."""
        return asyncio.get_event_loop().run_until_complete(
            self._fetch_campaigns()
        )

    async def _fetch_campaigns(self) -> list[dict[str, Any]]:
        """Fetch campaign list from Smartlead."""
        campaigns = await self.smartlead_client.get_campaign_list()
        return [{"id": c.id, "name": c.name, "status": c.status} for c in campaigns]

    def transform(self, data: Any) -> Any:
        """No transformation needed at this stage."""
        return data

    def execute(self, data: Any) -> Any:
        """Sync campaigns to Airtable (sync wrapper)."""
        return asyncio.get_event_loop().run_until_complete(
            self._sync_campaigns(data)
        )

    async def _sync_campaigns(self, campaigns: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Sync all campaigns to Airtable.

        Processes one campaign at a time with rate limiting.
        Continues on individual campaign errors.
        """
        if not campaigns:
            logger.info("No campaigns to sync")
            return {
                "campaigns_found": 0,
                "campaigns_synced": 0,
                "campaigns_failed": 0,
            }

        self._campaigns_synced = []
        self._campaigns_failed = []

        for i, campaign in enumerate(campaigns):
            campaign_id = campaign["id"]
            campaign_name = campaign.get("name", f"Campaign {campaign_id}")

            try:
                logger.info(f"Processing campaign {i + 1}/{len(campaigns)}: {campaign_name}")

                # Get detailed analytics
                analytics = await self.smartlead_client.get_campaign_analytics(campaign_id)

                # Map to Airtable fields
                airtable_fields = map_to_airtable(campaign_id, analytics.model_dump())

                # Upsert to Airtable
                await self.airtable_client.upsert_records(
                    AIRTABLE_TABLE_ID,
                    [airtable_fields],
                    merge_on=[AIRTABLE_MATCH_FIELD],
                )

                self._campaigns_synced.append({
                    "id": campaign_id,
                    "name": campaign_name,
                })

                logger.info(f"Synced campaign: {campaign_name}")

            except Exception as e:
                logger.error(f"Failed to sync campaign {campaign_name}: {e}")
                self._campaigns_failed.append({
                    "id": campaign_id,
                    "name": campaign_name,
                    "error": str(e),
                })
                # Continue with other campaigns

            # Rate limiting between campaigns
            if i < len(campaigns) - 1:
                await asyncio.sleep(CAMPAIGN_DELAY_SECONDS)

        return {
            "campaigns_found": len(campaigns),
            "campaigns_synced": len(self._campaigns_synced),
            "campaigns_failed": len(self._campaigns_failed),
            "synced": self._campaigns_synced,
            "failed": self._campaigns_failed,
        }

    def finalize(self, result: Any) -> None:
        """Cleanup and log summary."""
        # Close clients
        if self.smartlead_client:
            asyncio.get_event_loop().run_until_complete(
                self.smartlead_client.close()
            )
        if self.airtable_client:
            asyncio.get_event_loop().run_until_complete(
                self.airtable_client.close()
            )

        # Log summary
        logger.info(
            f"Sync complete: {result.get('campaigns_synced', 0)} synced, "
            f"{result.get('campaigns_failed', 0)} failed"
        )

        if self._campaigns_failed:
            logger.warning(f"Failed campaigns: {self._campaigns_failed}")


# Async-native version for direct async usage
async def run_smartlead_campaign_sync(
    dry_run: bool = False,
    smartlead_api_key: str | None = None,
    airtable_token: str | None = None,
) -> dict[str, Any]:
    """
    Run Smartlead campaign sync as async function.

    This is the preferred way to run the automation when
    already in an async context.
    """
    smartlead_key = smartlead_api_key or settings.smartlead_api
    airtable_key = airtable_token or settings.airtable_token

    if not smartlead_key:
        raise ValueError("SMARTLEAD_API_KEY not configured")
    if not airtable_key:
        raise ValueError("AIRTABLE_TOKEN not configured")

    exec_logger = ExecutionLogger("a7_smartlead_campaign_sync", trigger="cron")
    smartlead_client: SmartleadClient | None = None
    airtable_client: AirtableClient | None = None

    try:
        with exec_logger.step("Initialize"):
            smartlead_client = SmartleadClient(api_key=smartlead_key)
            airtable_client = AirtableClient(
                token=airtable_key,
                base_id=AIRTABLE_BASE_ID,
            )

        with exec_logger.step("Fetch campaigns") as step:
            campaigns = await smartlead_client.get_campaign_list()
            step.output_summary = f"Found {len(campaigns)} campaigns"

        if not campaigns:
            logger.info("No campaigns found")
            exec_logger.finalize("success")
            return {
                "dry_run": dry_run,
                "campaigns_found": 0,
                "campaigns_synced": 0,
                "campaigns_failed": 0,
            }

        campaigns_synced: list[dict[str, Any]] = []
        campaigns_failed: list[dict[str, Any]] = []

        with exec_logger.step("Sync campaigns") as step:
            for i, campaign in enumerate(campaigns):
                campaign_id = campaign.id
                campaign_name = campaign.name or f"Campaign {campaign_id}"

                try:
                    logger.info(f"Processing {i + 1}/{len(campaigns)}: {campaign_name}")

                    # Get detailed analytics
                    analytics = await smartlead_client.get_campaign_analytics(campaign_id)

                    # Map to Airtable fields
                    airtable_fields = map_to_airtable(campaign_id, analytics.model_dump())

                    if dry_run:
                        logger.info(f"[DRY RUN] Would upsert: {campaign_name}")
                    else:
                        await airtable_client.upsert_records(
                            AIRTABLE_TABLE_ID,
                            [airtable_fields],
                            merge_on=[AIRTABLE_MATCH_FIELD],
                        )

                    campaigns_synced.append({
                        "id": campaign_id,
                        "name": campaign_name,
                    })

                except Exception as e:
                    logger.error(f"Failed to sync {campaign_name}: {e}")
                    campaigns_failed.append({
                        "id": campaign_id,
                        "name": campaign_name,
                        "error": str(e),
                    })

                # Rate limiting
                if i < len(campaigns) - 1:
                    await asyncio.sleep(CAMPAIGN_DELAY_SECONDS)

            step.output_summary = f"Synced {len(campaigns_synced)}, failed {len(campaigns_failed)}"

        exec_logger.finalize("success")

        return {
            "dry_run": dry_run,
            "campaigns_found": len(campaigns),
            "campaigns_synced": len(campaigns_synced),
            "campaigns_failed": len(campaigns_failed),
            "synced": campaigns_synced,
            "failed": campaigns_failed,
        }

    except Exception as e:
        logger.error(f"Campaign sync failed: {e}")
        exec_logger.finalize("failed", error=str(e))
        raise

    finally:
        if smartlead_client:
            await smartlead_client.close()
        if airtable_client:
            await airtable_client.close()


# CLI for testing
if __name__ == "__main__":
    import sys

    async def main():
        dry_run = "--dry-run" in sys.argv

        print(f"Running Smartlead Campaign Sync (dry_run={dry_run})...")
        result = await run_smartlead_campaign_sync(dry_run=dry_run)

        print(f"\nResult:")
        print(f"  Campaigns found: {result['campaigns_found']}")
        print(f"  Campaigns synced: {result['campaigns_synced']}")
        print(f"  Campaigns failed: {result['campaigns_failed']}")

        if result.get("failed"):
            print(f"\nFailed campaigns:")
            for f in result["failed"]:
                print(f"  - {f['name']}: {f['error']}")

    asyncio.run(main())
