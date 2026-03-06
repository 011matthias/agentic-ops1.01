"""
Automations registry.

Register your automations here for the /run/{automation_id} endpoint.
"""

from dataclasses import dataclass
from typing import Optional
import logging
from sqlalchemy.orm import Session
from .base import BaseAutomation
from .example import ExampleAutomation


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
    "example": AutomationInfo(
        id="example",
        name="Example Automation",
        description="A sample automation to demonstrate the structure",
        trigger="manual",
        schedule=None,
        doc_id=None,
    ),
    # Add your automation metadata here:
    # "a1_recurring_orders": AutomationInfo(
    #     id="a1_recurring_orders",
    #     name="Recurring Orders",
    #     description="Generates recurring orders from templates",
    #     trigger="cron",
    #     schedule="08:00 daily",
    #     doc_id="a1-recurring-orders",
    # ),
}

# Registry of available automations (for execution)
_AUTOMATIONS: dict[str, type[BaseAutomation]] = {
    "example": ExampleAutomation,
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
