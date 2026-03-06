"""
Webhook endpoints for receiving events from external systems.

Add routes here for each integration (Fortnox, Upsales, etc.).
"""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Any
import logging
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..automations import is_automation_enabled
from ..automations.list_building_orchestrator import ListBuildingOrchestrator
from ..automations.lead_sourcing_completed import LeadSourcingCompletedHandler
from ..automations.apify_scraper_starter import ApifyScraperStarter
from ..automations.smartlead_sync import SmartLeadSync
from ..automations.email_reply_handler import EmailReplyHandler
from ..config import get_settings

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


# === A6: List Building Orchestrator ===

class ListStatusPayload(BaseModel):
    """Payload from Airtable list-status-changed webhook."""
    recordId: str


async def process_list_status_change(payload: dict[str, Any]) -> None:
    """Background task to process list status change."""
    try:
        orchestrator = ListBuildingOrchestrator()
        result = await orchestrator.run(payload)
        logger.info(f"List building result: {result}")
    except Exception as e:
        logger.error(f"List building failed: {e}")


@router.post("/list-status-changed")
async def webhook_list_status_changed(
    payload: ListStatusPayload,
    background_tasks: BackgroundTasks,
):
    """
    Handle Airtable webhook when List Status field changes.

    Spec: specs/automations/a6-list-building.md

    Airtable automation should send:
    {"recordId": "recXXX"}
    """
    logger.info(f"Received list-status-changed webhook: {payload.recordId}")

    # Process in background to return 200 quickly
    background_tasks.add_task(process_list_status_change, payload.model_dump())

    return {"status": "received", "recordId": payload.recordId}


# === A6.2: Lead Sourcing Completed Handler ===

async def process_lead_sourcing_finished(payload: dict[str, Any]) -> None:
    """Background task to process Apify run completion webhook."""
    try:
        handler = LeadSourcingCompletedHandler()
        result = await handler.run(payload)
        logger.info(f"Lead sourcing completed result: {result}")
    except Exception as e:
        logger.error(f"Lead sourcing completed handler failed: {e}")


@router.post("/lead-sourcing-finished")
async def webhook_lead_sourcing_finished(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle Apify webhook when scraper run completes.

    Spec: specs/automations/a6.2-lead-sourcing-completed.md

    Apify sends this webhook for ACTOR.RUN.SUCCEEDED and ACTOR.RUN.FAILED events.
    Payload includes run ID and dataset ID.
    """
    payload = await request.json()
    event_type = payload.get("eventType", "unknown")
    event_data = payload.get("eventData") or {}
    run_id = event_data.get("actorRunId") or payload.get("resource", {}).get("id", "unknown")

    logger.info(f"Received lead-sourcing-finished webhook: {event_type} (run: {run_id})")

    # Process in background to return 200 quickly
    background_tasks.add_task(process_lead_sourcing_finished, payload)

    return {"status": "received", "event": event_type, "run_id": run_id}


# === A6.1: Apify Scraper Starter ===

async def process_apify_scraper_starter(payload: dict[str, Any]) -> None:
    """Background task to process scraper start request."""
    try:
        handler = ApifyScraperStarter()
        result = await handler.run(payload)
        logger.info(f"Apify scraper starter result: {result}")
    except Exception as e:
        logger.error(f"Apify scraper starter failed: {e}")


@router.post("/apify-scraper-starter")
async def webhook_apify_scraper_starter(
    payload: ListStatusPayload,
    background_tasks: BackgroundTasks,
):
    """
    Handle scraper start request from A6 orchestrator.

    Spec: specs/automations/a6.1-apify-scraper-starter.md

    A6 orchestrator sends this when List Status = "Scraper Started".
    Payload includes recordId of the list to scrape.
    """
    logger.info(f"Received apify-scraper-starter webhook: {payload.recordId}")

    # Process in background to return 200 quickly
    background_tasks.add_task(process_apify_scraper_starter, payload.model_dump())

    return {"status": "received", "recordId": payload.recordId}


# === A6.5: SmartLead Lead Sync ===

async def process_airtable_lead_sync(payload: dict[str, Any]) -> None:
    """Background task to sync lead from Airtable to SmartLead."""
    try:
        sync = SmartLeadSync()
        result = await sync.run(payload)
        logger.info(f"SmartLead sync result: {result}")
    except Exception as e:
        logger.error(f"SmartLead sync failed: {e}")


@router.post("/airtable-lead-sync")
async def webhook_airtable_lead_sync(
    payload: ListStatusPayload,
    background_tasks: BackgroundTasks,
):
    """
    Handle Airtable webhook when lead is ready for SmartLead sync.

    Spec: specs/automations/a6.5-smartlead-sync.md

    Airtable automation should send when Outbound Status = "Ready for Sync":
    {"recordId": "recXXX"}
    """
    logger.info(f"Received airtable-lead-sync webhook: {payload.recordId}")

    # Process in background to return 200 quickly
    background_tasks.add_task(process_airtable_lead_sync, payload.model_dump())

    return {"status": "received", "recordId": payload.recordId}


# === A8: Email Reply Handler ===

async def process_smartlead_webhook(payload: dict[str, Any]) -> None:
    """Background task to process Smartlead email reply/bounce webhook."""
    try:
        handler = EmailReplyHandler(webhook_data=payload)
        result = await handler.run(trigger="webhook")
        logger.info(f"Smartlead webhook processed: {result}")
    except Exception as e:
        logger.error(f"Smartlead webhook processing failed: {e}")


@router.post("/smartlead")
async def webhook_smartlead(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle Smartlead webhooks for email replies and bounces.

    Spec: specs/automations/a8-email-reply-handler.md

    Validates webhook secret and processes:
    - EMAIL_REPLY: Categorize response, update CRM, create tasks
    - EMAIL_BOUNCE: Route to LinkedIn if available

    Smartlead sends events when leads reply to campaigns or emails bounce.
    """
    payload = await request.json()
    settings = get_settings()

    # Validate webhook secret if configured
    webhook_secret = request.headers.get("X-Webhook-Secret")
    if settings.smartlead_webhook_secret and webhook_secret != settings.smartlead_webhook_secret:
        logger.warning("Smartlead webhook secret validation failed")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    event_type = payload.get("body", {}).get("event_type", "unknown")
    logger.info(f"Received Smartlead webhook: {event_type}")

    # Process in background to return 200 quickly
    background_tasks.add_task(process_smartlead_webhook, payload)

    return {"status": "received", "event": event_type}


# === Order Approval Dashboard: Pending Orders Receiver ===

from pydantic import BaseModel as PydanticBaseModel


class PendingOrderPayload(PydanticBaseModel):
    """Single pending order from n8n A1 workflow."""
    contract_number: str
    customer_number: str
    customer_name: str = ""
    source: str = "recurring"  # 'recurring' | 'new'
    order_payload: dict  # Complete { Order: {...} } for Fortnox POST
    delivery_date: str  # ISO date string
    order_date: str | None = None
    total_amount: float = 0
    currency: str = "SEK"
    item_count: int = 0
    item_summary: str = ""
    administration_fee: float = 0
    freight: float = 0
    remarks: str = ""
    period_start: str | None = None  # ISO date string
    period_end: str | None = None    # ISO date string (YYYY-MM-DD)
    interval: str | None = None      # Upsales billing interval: Kvartal / Halvår / Helår
    invoice_interval: int | None = None  # Months: 3, 6, 12. NULL = no subscription.
    your_order_number: str  # UNIQUE — used for duplicate prevention
    fortnox_order_number: str | None = None  # Pre-populated for Upsales enrichments
    customer_info: dict | None = None  # Populated by Fix3 from Upsales customer data


class PendingOrdersRequest(PydanticBaseModel):
    """Batch of pending orders from n8n."""
    orders: list[PendingOrderPayload]


@router.post("/pending-orders")
async def receive_pending_orders(payload: PendingOrdersRequest):
    """
    Receive pending orders from A1 n8n workflow.

    PRD: specs/prd-order-dashboard.md

    Called daily by the modified A1 Recurring Order workflow.
    Stores orders as 'pending' for review in the dashboard.
    Duplicates (same your_order_number) are skipped.
    """
    from ..models.pending_orders import PendingOrder
    from datetime import datetime

    db = SessionLocal()
    stored = 0
    duplicates_skipped = 0

    try:
        for order_data in payload.orders:
            # Check for duplicate — match any status including soft-deleted,
            # because the unique DB constraint applies regardless of status.
            existing = db.query(PendingOrder).filter(
                PendingOrder.your_order_number == order_data.your_order_number,
            ).first()

            if existing:
                duplicates_skipped += 1
                logger.info(
                    f"Skipping duplicate order: {order_data.your_order_number}"
                )
                continue

            # Parse dates
            delivery_date = datetime.strptime(order_data.delivery_date, "%Y-%m-%d").date()
            order_date = (
                datetime.strptime(order_data.order_date, "%Y-%m-%d").date()
                if order_data.order_date
                else delivery_date
            )
            period_start = (
                datetime.strptime(order_data.period_start, "%Y-%m-%d").date()
                if order_data.period_start
                else None
            )
            period_end = (
                datetime.strptime(order_data.period_end, "%Y-%m-%d").date()
                if order_data.period_end
                else None
            )

            pending_order = PendingOrder(
                contract_number=order_data.contract_number,
                customer_number=order_data.customer_number,
                customer_name=order_data.customer_name,
                source=order_data.source,
                order_payload=order_data.order_payload,
                delivery_date=delivery_date,
                order_date=order_date,
                total_amount=order_data.total_amount,
                currency=order_data.currency,
                item_count=order_data.item_count,
                item_summary=order_data.item_summary,
                administration_fee=order_data.administration_fee,
                freight=order_data.freight,
                remarks=order_data.remarks,
                period_start=period_start,
                period_end=period_end,
                interval=order_data.interval or None,
                invoice_interval=order_data.invoice_interval,
                your_order_number=order_data.your_order_number,
                fortnox_order_number=order_data.fortnox_order_number or "",
                customer_info=order_data.customer_info or None,
                status="pending",
                generated_at=datetime.utcnow(),
            )

            db.add(pending_order)
            stored += 1

        try:
            db.commit()
        except IntegrityError:
            # Race condition: another request inserted the same your_order_number
            # between our duplicate check and commit. Treat as duplicate.
            db.rollback()
            stored = 0
            duplicates_skipped = len(payload.orders)
            logger.warning("IntegrityError on commit — treated as duplicate(s)")
        logger.info(
            f"Pending orders received: {stored} stored, {duplicates_skipped} duplicates skipped"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store pending orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store orders: {str(e)}")
    finally:
        db.close()

    return {
        "status": "received",
        "stored": stored,
        "duplicates_skipped": duplicates_skipped,
    }
