"""
Automations registry.

Register your automations here for the /run/{automation_id} endpoint.
"""

from dataclasses import dataclass
from typing import Optional
import logging
from sqlalchemy.orm import Session
from .base import BaseAutomation
from .smartlead_campaign_sync import SmartleadCampaignSync
from .lead_sourcing_completed import LeadSourcingCompletedHandler
from .apify_scraper_starter import ApifyScraperStarter
from .smartlead_sync import SmartLeadSync
from .contact_enrichment import ContactEnrichment
from .data_cleaning import DataCleaning
from .email_reply_handler import EmailReplyHandler


@dataclass
class AutomationInfo:
    """Metadata about an automation for display in the dashboard."""
    id: str
    name: str
    description: str
    trigger: str  # "cron", "webhook", "manual"
    schedule: str | None  # "08:00 daily", "hourly", etc.
    doc_id: str | None  # Links to docs/client/{doc_id}.md


# Registry of automation metadata
_AUTOMATION_INFO: dict[str, AutomationInfo] = {
    "a7_smartlead_campaign_sync": AutomationInfo(
        id="a7_smartlead_campaign_sync",
        name="Smartlead Campaign Sync",
        description="Syncs Smartlead campaign analytics to Airtable daily",
        trigger="cron",
        schedule="10:00 daily",
        doc_id="a7-smartlead-sync",
    ),
    "a6_list_building": AutomationInfo(
        id="a6_list_building",
        name="List Building: Orchestrator",
        description="Orchestrates lead list building pipeline from Airtable status changes",
        trigger="webhook",
        schedule=None,
        doc_id="a6-list-building",
    ),
    "a6_1_apify_scraper_starter": AutomationInfo(
        id="a6_1_apify_scraper_starter",
        name="List Building: 1. Scraper Starter",
        description="Checks queue capacity and starts Apify LinkedIn scraper",
        trigger="webhook",
        schedule=None,
        doc_id="a6.1-apify-scraper-starter",
    ),
    "a6_2_lead_sourcing_completed": AutomationInfo(
        id="a6_2_lead_sourcing_completed",
        name="List Building: 2. Lead Import",
        description="Imports scraped leads from Apify into Airtable when scraper runs complete",
        trigger="webhook",
        schedule=None,
        doc_id="a6.2-lead-sourcing-completed",
    ),
    "a6_3_contact_enrichment": AutomationInfo(
        id="a6_3_contact_enrichment",
        name="List Building: 3. Enrichment",
        description="Multi-vendor email enrichment (Leadmagic, Trykitt) + Bouncer verification",
        trigger="cron",
        schedule="Every 6 hours",
        doc_id="a6.3-contact-enrichment",
    ),
    "a6_4_data_cleaning": AutomationInfo(
        id="a6_4_data_cleaning",
        name="List Building: 4. Data Cleaning",
        description="GPT-4 company name normalization + Swedish job title translation",
        trigger="cron",
        schedule="Daily at midnight",
        doc_id="a6.4-data-cleaning",
    ),
    "a6_5_smartlead_sync": AutomationInfo(
        id="a6_5_smartlead_sync",
        name="List Building: 5. SmartLead Sync",
        description="Syncs validated leads from Airtable to SmartLead campaigns",
        trigger="webhook",
        schedule=None,
        doc_id="a6.5-smartlead-sync",
    ),
    "a8_email_reply_handler": AutomationInfo(
        id="a8_email_reply_handler",
        name="Email Reply Handler",
        description="Processes Smartlead webhooks for email replies and bounces with AI categorization",
        trigger="webhook",
        schedule=None,
        doc_id="a8-email-reply-handler",
    ),
}

# Registry of available automations (for execution)
_AUTOMATIONS: dict[str, type[BaseAutomation]] = {
    "a7_smartlead_campaign_sync": SmartleadCampaignSync,
    "a6_3_contact_enrichment": ContactEnrichment,
    "a6_4_data_cleaning": DataCleaning,
    # Add your automations here:
    # "a1_recurring_orders": RecurringOrdersAutomation,
    # "a2_crm_sync": CRMSyncAutomation,
}


def get_automation(automation_id: str) -> Optional[BaseAutomation]:
    """Get automation instance by ID."""
    automation_class = _AUTOMATIONS.get(automation_id)
    if automation_class:
        return automation_class()
    return None


def list_automations() -> list[str]:
    """List all registered automation IDs."""
    return list(_AUTOMATIONS.keys())


def list_automation_info() -> list[AutomationInfo]:
    """List all registered automation metadata for dashboard display."""
    return list(_AUTOMATION_INFO.values())


def is_automation_enabled(automation_id: str, db: Session) -> bool:
    """Check if automation is enabled. Returns False if database fails (fail-safe)."""
    try:
        from ..db import get_or_create_automation_setting
        setting = get_or_create_automation_setting(db, automation_id)
        return setting.enabled
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Database error checking enabled state for {automation_id}: {e}. "
            f"Defaulting to DISABLED for safety."
        )
        return False  # Fail-safe: disable on database errors
