"""
Webhook endpoints for receiving events from external systems.

Add routes here for each integration (Fortnox, Upsales, etc.).
"""

from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Any
import logging

from ..db import SessionLocal
from ..automations import is_automation_enabled

router = APIRouter()
logger = logging.getLogger(__name__)


def run_if_enabled(automation_id: str, background_tasks: BackgroundTasks, automation_instance):
    """Run automation only if enabled, else log and skip."""
    db = SessionLocal()
    try:
        if is_automation_enabled(automation_id, db):
            background_tasks.add_task(automation_instance.run)
        else:
            logger.info(f"Webhook received for disabled automation '{automation_id}', skipping")
    finally:
        db.close()


class WebhookPayload(BaseModel):
    """Generic webhook payload."""
    event: str | None = None
    data: dict[str, Any] = {}


@router.post("/example")
async def webhook_example(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Example webhook endpoint.

    Replace with actual integrations like:
    - POST /webhook/fortnox
    - POST /webhook/upsales
    """
    logger.info(f"Received webhook: {payload.event}")

    # Process in background to return 200 quickly
    # background_tasks.add_task(process_webhook, payload)

    return {"status": "received", "event": payload.event}


# Add your webhook handlers below:

# @router.post("/fortnox")
# async def webhook_fortnox(request: Request, background_tasks: BackgroundTasks):
#     """Handle Fortnox webhooks."""
#     payload = await request.json()
#     background_tasks.add_task(handle_fortnox_event, payload)
#     return {"status": "received"}

# @router.post("/upsales")
# async def webhook_upsales(request: Request, background_tasks: BackgroundTasks):
#     """Handle Upsales webhooks."""
#     payload = await request.json()
#     background_tasks.add_task(handle_upsales_event, payload)
#     return {"status": "received"}
