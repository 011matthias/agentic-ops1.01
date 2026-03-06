"""
Internal API endpoints for manual triggers and self-healing.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Any
import logging

from ..auth import verify_internal_key
from ..config import get_settings
from ..db import get_db

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


class HealRequest(BaseModel):
    """Self-healing request payload."""
    automation_id: str
    run_id: str
    error: str
    steps: list[dict[str, Any]]


class RunAutomationRequest(BaseModel):
    """Request model for manual automation trigger with test parameters."""
    dry_run: bool = False
    limit: int | None = None
    record_ids: list[str] | None = None
    test_mode: bool = False


@router.post("/run/{automation_id}")
async def run_automation(
    automation_id: str,
    background_tasks: BackgroundTasks,
    request: RunAutomationRequest | None = None,
    db: Any = Depends(get_db),
    _: None = Depends(verify_internal_key)
):
    """
    Manually trigger an automation.

    Called by cron jobs, manual testing, or production tests.

    Test Parameters:
    - limit: Maximum records to process (safety for testing)
    - record_ids: Specific record IDs to process
    - test_mode: Log test execution for tracking
    """
    # Handle backward compatibility: if no request body, use defaults
    if request is None:
        request = RunAutomationRequest()

    # Log test mode if enabled
    if request.test_mode:
        logger.info(
            f"TEST MODE: {automation_id} - "
            f"limit={request.limit}, "
            f"record_ids={len(request.record_ids) if request.record_ids else 0}"
        )

    # Check if automation is enabled
    from ..automations import is_automation_enabled
    if not is_automation_enabled(automation_id, db):
        logger.info(f"Automation '{automation_id}' is disabled, skipping")
        return {
            "status": "skipped",
            "automation_id": automation_id,
            "reason": "disabled"
        }

    # Import automations dynamically to avoid circular imports
    try:
        from ..automations import get_automation
        automation = get_automation(automation_id)
        if not automation:
            raise HTTPException(status_code=404, detail=f"Automation '{automation_id}' not found")

        # Run in background to return quickly
        background_tasks.add_task(
            automation.run,
            trigger="internal_api",
            dry_run=request.dry_run,
            limit=request.limit,
            record_ids=request.record_ids
        )

        return {
            "status": "triggered",
            "automation_id": automation_id,
            "dry_run": request.dry_run,
            "test_mode": request.test_mode,
            "limit": request.limit,
            "record_ids_count": len(request.record_ids) if request.record_ids else 0
        }
    except ImportError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/heal")
async def self_heal(
    request: HealRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_internal_key)
):
    """
    Self-healing endpoint.

    Called when an automation fails. Can trigger retry or
    notify external systems (Claude agent) for complex fixes.
    """
    # Log the healing request
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        f"Self-healing triggered for {request.automation_id}: {request.error}"
    )

    # Basic self-healing: retry the automation
    # More complex healing (token refresh, code fixes) would be handled
    # by an external Claude agent via webhook

    if settings.self_healing_webhook:
        import httpx
        background_tasks.add_task(
            notify_healing_webhook,
            settings.self_healing_webhook,
            request.model_dump()
        )

    return {"status": "healing_initiated", "automation_id": request.automation_id}


async def notify_healing_webhook(url: str, payload: dict):
    """Send failure details to external healing system."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=30)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to notify healing webhook: {e}")
