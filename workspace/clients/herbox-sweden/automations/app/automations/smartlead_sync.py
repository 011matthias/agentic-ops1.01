"""
Automation A6.5: SmartLead Lead Sync

Spec: specs/automations/a6.5-smartlead-sync.md
Trigger: POST /webhooks/airtable-lead-sync

Syncs validated leads from Airtable to SmartLead campaigns.
Handles field mapping, validation, and status updates.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from pydantic import BaseModel

from ..clients.airtable import AirtableClient
from ..clients.smartlead import SmartleadClient
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration (from spec)
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"  # Herbox Base
AIRTABLE_TABLE_CONTACTS_ID = "tblsI8jeqv1B16MTk"  # Contacts table


class WebhookPayload(BaseModel):
    """Webhook payload structure."""
    recordId: str


class LeadValidationError(Exception):
    """Raised when lead validation fails."""
    pass


def map_lead_to_smartlead(lead: dict[str, Any]) -> dict[str, Any]:
    """
    Map Airtable lead fields to SmartLead format.

    Args:
        lead: Airtable lead record fields

    Returns:
        Lead data in SmartLead format
    """
    # Get website - Airtable stores as array, take first if exists
    website = lead.get("Website", [""])[0] if lead.get("Website") else ""

    return {
        "first_name": lead.get("SL_firstName", ""),
        "last_name": lead.get("Last Name", ""),
        "email": lead.get("Email", ""),
        "company_name": lead.get("SL_company", ""),
        "website": website,
        "location": "",  # Not available from Airtable
        "custom_fields": {
            "job_title": lead.get("SL_title", ""),
            "sl_personalization": lead.get("SL_Personalization", ""),
        },
        "linkedin_profile": lead.get("Linkedin URL", ""),
    }


def validate_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """
    Validate lead for sync to SmartLead.

    Args:
        lead: Airtable lead record fields

    Returns:
        Validation result with 'valid' bool and optional 'reason'

    Raises:
        LeadValidationError: If validation fails
    """
    # Check campaign assignment
    campaign_ids = lead.get("Campaign ID", [])
    if not campaign_ids:
        raise LeadValidationError("no_campaign")

    # Check email exists
    email = lead.get("Email")
    if not email:
        raise LeadValidationError("missing_email")

    # Check email verification status
    email_status = lead.get("Email Verification Status")
    if email_status == "Invalid":
        raise LeadValidationError("invalid_email")

    # Get campaign ID (use most recent if multiple)
    campaign_id = campaign_ids[-1] if isinstance(campaign_ids, list) else campaign_ids

    return {
        "valid": True,
        "campaign_id": campaign_id,
    }


class SmartLeadSync:
    """
    Syncs validated leads from Airtable to SmartLead campaigns.

    Triggered by webhook when a lead's Outbound Status changes to
    "Ready for Sync". Fetches the lead, validates, maps fields,
    adds to SmartLead campaign, and updates Airtable status.
    """

    automation_id = "a6_5_smartlead_sync"

    def __init__(
        self,
        airtable_token: str | None = None,
        smartlead_api_key: str | None = None,
    ):
        self.airtable_token = airtable_token or settings.airtable_token
        self.smartlead_api_key = smartlead_api_key or settings.smartlead_api
        self.airtable_client: AirtableClient | None = None
        self.smartlead_client: SmartleadClient | None = None

    async def _init_clients(self) -> None:
        """Initialize API clients."""
        if not self.airtable_token:
            raise ValueError("AIRTABLE_TOKEN not configured")
        if not self.smartlead_api_key:
            raise ValueError("SMARTLEAD_API_KEY not configured")

        self.airtable_client = AirtableClient(
            token=self.airtable_token,
            base_id=AIRTABLE_BASE_ID,
        )
        self.smartlead_client = SmartleadClient(api_key=self.smartlead_api_key)

    async def _close_clients(self) -> None:
        """Close API clients."""
        if self.airtable_client:
            await self.airtable_client.close()
        if self.smartlead_client:
            await self.smartlead_client.close()

    async def run(
        self,
        payload: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Run the automation for an Airtable webhook event.

        Args:
            payload: Webhook payload with recordId
            dry_run: If True, simulate without making changes

        Returns:
            Result dictionary with status and details
        """
        exec_logger = ExecutionLogger(self.automation_id, trigger="webhook")

        try:
            # 1. Initialize - Extract and validate record ID
            with exec_logger.step("Initialize"):
                webhook_payload = WebhookPayload(**payload)
                record_id = webhook_payload.recordId
                logger.info(f"Processing lead sync for record: {record_id}")

                await self._init_clients()

            # 2. Fetch lead from Airtable
            with exec_logger.step("Fetch Lead") as step:
                lead_record = await self.airtable_client.get_record(
                    AIRTABLE_TABLE_CONTACTS_ID,
                    record_id,
                )
                lead = lead_record.fields
                lead_email = lead.get("Email", "unknown")
                step.output_summary = f"Fetched lead: {lead_email}"

            # 3. Validate lead
            with exec_logger.step("Validate Lead") as step:
                try:
                    validation = validate_lead(lead)
                    campaign_id = validation["campaign_id"]
                    step.output_summary = f"Valid, campaign: {campaign_id}"
                except LeadValidationError as e:
                    reason = str(e)
                    step.output_summary = f"Validation failed: {reason}"

                    if reason == "invalid_email":
                        await self._update_invalid_email_status(record_id)
                    elif reason in ("no_campaign", "missing_email"):
                        # Skip sync, no error status update needed
                        pass

                    exec_logger.finalize("skipped", error=reason)
                    return {
                        "status": "skipped",
                        "reason": reason,
                        "record_id": record_id,
                    }

            # 4. Map lead data to SmartLead format
            with exec_logger.step("Map Fields") as step:
                smartlead_lead = map_lead_to_smartlead(lead)
                step.output_summary = f"Mapped fields for {smartlead_lead.get('email')}"

            # 5. Add lead to SmartLead campaign
            with exec_logger.step("Sync to SmartLead") as step:
                if dry_run:
                    step.output_summary = f"Dry run: would sync to campaign {campaign_id}"
                    exec_logger.finalize("success")
                    return {
                        "status": "success",
                        "dry_run": True,
                        "would_sync": True,
                        "campaign_id": campaign_id,
                        "record_id": record_id,
                    }

                try:
                    response = await self.smartlead_client.add_leads_to_campaign(
                        campaign_id=int(campaign_id),
                        leads=[smartlead_lead],
                        return_lead_ids=True,
                    )

                    # Extract lead ID from response
                    lead_ids = response.get("lead_ids", [])
                    smartlead_lead_id = lead_ids[0] if lead_ids else None

                    step.output_summary = f"Added to campaign {campaign_id}"

                except Exception as e:
                    logger.error(f"SmartLead sync failed: {e}")
                    await self._update_error_status(record_id, str(e))
                    exec_logger.finalize("failed", error=str(e))
                    return {
                        "status": "error",
                        "reason": "smartlead_api_error",
                        "error": str(e),
                        "record_id": record_id,
                    }

            # 6. Update Airtable with success
            with exec_logger.step("Update Airtable") as step:
                await self._update_success_status(
                    record_id,
                    smartlead_lead_id,
                )
                step.output_summary = "Status updated to Added to Campaign"

            exec_logger.finalize("success")
            return {
                "status": "success",
                "campaign_id": campaign_id,
                "smartlead_lead_id": smartlead_lead_id,
                "record_id": record_id,
            }

        except Exception as e:
            logger.error(f"SmartLead sync automation failed: {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

        finally:
            await self._close_clients()

    async def _update_success_status(
        self,
        record_id: str,
        smartlead_lead_id: int | None,
    ) -> None:
        """Update Airtable with successful sync status."""
        fields = {
            "Outbound Status": "Added to Campaign",
        }
        if smartlead_lead_id:
            fields["SL Contact ID"] = str(smartlead_lead_id)

        await self.airtable_client.update_record(
            AIRTABLE_TABLE_CONTACTS_ID,
            record_id,
            fields,
        )

    async def _update_error_status(
        self,
        record_id: str,
        error_message: str,
    ) -> None:
        """Update Airtable with error status."""
        await self.airtable_client.update_record(
            AIRTABLE_TABLE_CONTACTS_ID,
            record_id,
            {
                "Outbound Status": "Sync Error",
                "Sync Error Log": error_message,
            },
        )

    async def _update_invalid_email_status(self, record_id: str) -> None:
        """Update Airtable for invalid email."""
        await self.airtable_client.update_record(
            AIRTABLE_TABLE_CONTACTS_ID,
            record_id,
            {
                "Outbound Status": "Invalid Email",
            },
        )


# Async function for direct usage
async def run_smartlead_sync(
    record_id: str,
    dry_run: bool = False,
    airtable_token: str | None = None,
    smartlead_api_key: str | None = None,
) -> dict[str, Any]:
    """
    Run SmartLead lead sync as async function.

    This is the preferred way to run the automation when
    already in an async context.
    """
    airtable_key = airtable_token or settings.airtable_token
    smartlead_key = smartlead_api_key or settings.smartlead_api

    sync = SmartLeadSync(
        airtable_token=airtable_key,
        smartlead_api_key=smartlead_key,
    )

    return await sync.run(
        payload={"recordId": record_id},
        dry_run=dry_run,
    )


# CLI for testing
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        dry_run = "--dry-run" in sys.argv

        if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
            print("Usage: python -m app.automations.smartlead_sync <record_id> [--dry-run]")
            sys.exit(1)

        record_id = sys.argv[1]

        print(f"Running SmartLead Lead Sync (dry_run={dry_run})...")
        result = await run_smartlead_sync(record_id, dry_run=dry_run)

        print(f"\nResult:")
        print(f"  Status: {result.get('status')}")
        print(f"  Record ID: {result.get('record_id')}")

        if result.get('status') == 'success':
            print(f"  Campaign ID: {result.get('campaign_id')}")
            print(f"  SmartLead Lead ID: {result.get('smartlead_lead_id')}")
        elif result.get('reason'):
            print(f"  Reason: {result.get('reason')}")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")

    asyncio.run(main())
