"""
Order Approval Dashboard routes.

PRD: specs/prd-order-dashboard.md
Phase 4: specs/phases/phase-4-dashboard.md
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import asyncio
import json
import logging
import uuid
import httpx

from ..db import get_db
from ..auth import require_auth
from ..config import get_settings
from ..models.pending_orders import PendingOrder, ApprovalLog

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/orders", response_class=HTMLResponse)
async def orders_page(
    request: Request,
    tab: str = "recurring",
    status: str = "pending",
    sort: str = "delivery_date",
    delivery_from: Optional[date] = None,
    delivery_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Main orders page with table, tabs, filters."""
    # Build base query (exclude soft-deleted orders from all views)
    query = db.query(PendingOrder).filter(PendingOrder.status != "deleted")

    # Tab filter
    if tab in ("recurring", "new"):
        query = query.filter(PendingOrder.source == tab)

    # Date range filter (recurring tab only)
    if tab == "recurring":
        if delivery_from:
            query = query.filter(PendingOrder.delivery_date >= delivery_from)
        if delivery_to:
            query = query.filter(PendingOrder.delivery_date <= delivery_to)

    # Status filter
    if status != "all":
        query = query.filter(PendingOrder.status == status)

    # Sorting
    sort_map = {
        "delivery_date": PendingOrder.delivery_date,
        "customer_name": PendingOrder.customer_name,
        "total_amount": desc(PendingOrder.total_amount),
    }
    order_col = sort_map.get(sort, PendingOrder.delivery_date)
    query = query.order_by(order_col)

    orders = query.all()

    # Stats (always for the active tab, regardless of status filter; exclude deleted)
    tab_query = db.query(PendingOrder).filter(
        PendingOrder.source == tab,
        PendingOrder.status != "deleted",
    )
    pending_count = tab_query.filter(PendingOrder.status == "pending").count()
    total_value = tab_query.filter(PendingOrder.status == "pending").with_entities(
        func.coalesce(func.sum(PendingOrder.total_amount), 0)
    ).scalar()
    approved_count = tab_query.filter(PendingOrder.status == "approved").count()
    created_count = tab_query.filter(PendingOrder.status == "created").count()

    # Tab counts
    recurring_count = db.query(PendingOrder).filter(
        PendingOrder.source == "recurring",
        PendingOrder.status == "pending",
    ).count()
    new_count = db.query(PendingOrder).filter(
        PendingOrder.source == "new",
        PendingOrder.status == "pending",
    ).count()

    # Flash message from query param
    flash = request.query_params.get("flash", "")

    return templates.TemplateResponse("orders.html", {
        "request": request,
        "client_display_name": settings.client_display_name,
        "orders": orders,
        "active_tab": tab,
        "active_status": status,
        "active_sort": sort,
        "stats": {
            "pending_count": pending_count,
            "total_value": float(total_value) if total_value else 0,
            "approved_count": approved_count,
            "created_count": created_count,
        },
        "recurring_count": recurring_count,
        "new_count": new_count,
        "flash": flash,
        "delivery_from": delivery_from.isoformat() if delivery_from else "",
        "delivery_to": delivery_to.isoformat() if delivery_to else "",
    })


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Order detail page with editing capability."""
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = db.query(PendingOrder).filter(PendingOrder.id == order_uuid).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Parse order rows from payload
    payload = order.order_payload or {}
    order_data = payload.get("Order", payload)
    order_rows = order_data.get("OrderRows", [])

    # Fetch audit log
    logs = db.query(ApprovalLog).filter(
        ApprovalLog.order_id == order_uuid
    ).order_by(desc(ApprovalLog.created_at)).all()

    flash = request.query_params.get("flash", "")
    delivery_from = request.query_params.get("delivery_from", "")
    delivery_to = request.query_params.get("delivery_to", "")

    return templates.TemplateResponse("order_detail.html", {
        "request": request,
        "client_display_name": settings.client_display_name,
        "order": order,
        "order_rows": order_rows,
        "logs": logs,
        "flash": flash,
        "delivery_from": delivery_from,
        "delivery_to": delivery_to,
    })


@router.post("/orders/{order_id}/edit")
async def edit_order(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Save order edits (order-level fields + line items)."""
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = db.query(PendingOrder).filter(PendingOrder.id == order_uuid).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("pending", "failed"):
        return RedirectResponse(
            url=f"/orders/{order_id}?flash=Cannot edit order with status '{order.status}'",
            status_code=302,
        )

    form = await request.form()

    # Track changes for audit log
    changes = {}

    # Update order-level fields
    new_remarks = form.get("remarks", "")
    if new_remarks != (order.remarks or ""):
        changes["remarks"] = {"old": order.remarks, "new": new_remarks}
        order.remarks = new_remarks

    new_freight = Decimal(form.get("freight", "0") or "0")
    if new_freight != (order.freight or Decimal("0")):
        changes["freight"] = {"old": str(order.freight), "new": str(new_freight)}
        order.freight = new_freight

    new_admin_fee = Decimal(form.get("administration_fee", "0") or "0")
    if new_admin_fee != (order.administration_fee or Decimal("0")):
        changes["administration_fee"] = {"old": str(order.administration_fee), "new": str(new_admin_fee)}
        order.administration_fee = new_admin_fee

    new_delivery_date = form.get("delivery_date", "")
    if new_delivery_date:
        parsed_date = datetime.strptime(new_delivery_date, "%Y-%m-%d").date()
        if parsed_date != order.delivery_date:
            changes["delivery_date"] = {"old": str(order.delivery_date), "new": str(parsed_date)}
            order.delivery_date = parsed_date
            order.order_date = parsed_date

    new_period_start = form.get("period_start", "")
    if new_period_start:
        parsed_ps = datetime.strptime(new_period_start, "%Y-%m-%d").date()
        if parsed_ps != order.period_start:
            changes["period_start"] = {"old": str(order.period_start), "new": str(parsed_ps)}
            order.period_start = parsed_ps

    new_period_end = form.get("period_end", "")
    if new_period_end:
        parsed_pe = datetime.strptime(new_period_end, "%Y-%m-%d").date()
        if parsed_pe != order.period_end:
            changes["period_end"] = {"old": str(order.period_end), "new": str(parsed_pe)}
            order.period_end = parsed_pe
            # Keep enrichment payload in sync so Fortnox PUT sends PeriodEnd
            if "Order" in (order.order_payload or {}):
                order.order_payload["Order"]["PeriodEnd"] = new_period_end

    # Parse line items from form
    rows_json = form.get("rows_json", "")
    if rows_json:
        try:
            new_rows = json.loads(rows_json)
        except json.JSONDecodeError:
            return RedirectResponse(
                url=f"/orders/{order_id}?flash=Invalid line items data",
                status_code=302,
            )

        changes["order_rows"] = "updated"

        # Rebuild order payload
        payload = order.order_payload or {}
        order_obj = payload.get("Order", payload)
        order_obj["OrderRows"] = new_rows
        order_obj["Remarks"] = new_remarks
        order_obj["Freight"] = float(new_freight)
        order_obj["AdministrationFee"] = float(new_admin_fee)
        if new_delivery_date:
            order_obj["DeliveryDate"] = new_delivery_date
            order_obj["OrderDate"] = new_delivery_date

        if "Order" in payload:
            payload["Order"] = order_obj
        else:
            payload = order_obj
        order.order_payload = payload

        # Update denormalized fields
        order.item_count = len(new_rows)
        total_items = sum(
            float(r.get("DeliveredQuantity", 0)) * float(r.get("Price", 0))
            for r in new_rows
        )
        order.total_amount = Decimal(str(total_items)) + new_admin_fee + new_freight
        order.item_summary = ", ".join(
            f"{int(float(r.get('DeliveredQuantity', 0)))}x {r.get('Description', '?')}"
            for r in new_rows[:5]
        )

    order.updated_at = datetime.utcnow()

    # Log the edit
    if changes:
        log_entry = ApprovalLog(
            order_id=order_uuid,
            action="edited",
            performed_by="dashboard",
            details=changes,
        )
        db.add(log_entry)

    db.commit()
    logger.info(f"Order {order_id} edited: {list(changes.keys())}")

    return RedirectResponse(
        url=f"/orders/{order_id}?flash=Changes saved",
        status_code=302,
    )


@router.post("/orders/approve")
async def approve_orders(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Approve selected orders and create them in Fortnox via n8n webhook."""
    form = await request.form()
    order_ids_str = form.get("order_ids", "")
    if not order_ids_str:
        return RedirectResponse(url="/orders?flash=No orders selected", status_code=302)

    order_ids = [s.strip() for s in order_ids_str.split(",") if s.strip()]
    redirect_tab = form.get("tab", "recurring")
    redirect_from = form.get("delivery_from", "")
    redirect_to = form.get("delivery_to", "")
    approved = 0
    created = 0
    failed = 0

    for oid in order_ids:
        try:
            order_uuid = uuid.UUID(oid)
        except ValueError:
            continue

        order = db.query(PendingOrder).filter(PendingOrder.id == order_uuid).first()
        if not order or order.status not in ("pending", "failed"):
            continue

        order.status = "approved"
        order.reviewed_at = datetime.utcnow()
        order.error_message = None
        approved += 1

        # Log approval
        db.add(ApprovalLog(
            order_id=order_uuid,
            action="approved",
            performed_by="dashboard",
        ))

        # Call n8n webhook to create or update the order in Fortnox
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if order.fortnox_order_number:
                    # Upsales enrichment flow — UPDATE the existing Fortnox order + create contract
                    url = f"{settings.n8n_webhook_base_url}/webhook/update-fortnox-order"
                    # Reconstruct customer update payload from stored customer_info
                    customer_update_payload: dict = {"Customer": {}}
                    if order.customer_info:
                        info = order.customer_info
                        if info.get("phone"):
                            customer_update_payload["Customer"]["Phone1"] = info["phone"]
                        if info.get("email"):
                            customer_update_payload["Customer"]["Email"] = info["email"]
                        if info.get("address1"):
                            customer_update_payload["Customer"]["DeliveryAddress1"] = info["address1"]
                            customer_update_payload["Customer"]["DeliveryCity"] = info.get("city", "")
                            customer_update_payload["Customer"]["DeliveryZipCode"] = info.get("zip", "")
                            customer_update_payload["Customer"]["DeliveryCountry"] = info.get("country", "SE")
                    payload = {
                        "order_id": str(order.id),
                        "fortnox_order_number": order.fortnox_order_number,
                        "enrichment_payload": order.order_payload,
                        "customer_number": order.customer_number,
                        "customer_update_payload": customer_update_payload,
                        "invoice_interval": order.invoice_interval,
                        "delivery_date": str(order.delivery_date),
                    }
                else:
                    # Recurring order flow — CREATE a new Fortnox order + advance contract PeriodStart
                    url = f"{settings.n8n_webhook_base_url}/webhook/create-fortnox-order"
                    payload = {
                        "order_id": str(order.id),
                        "order_payload": order.order_payload,
                        "contract_number": order.contract_number,
                        "period_start": str(order.period_start) if order.period_start else None,
                        "invoice_interval": order.invoice_interval,
                    }

                resp = await client.post(url, json=payload)
                result = resp.json()

            if result.get("success"):
                order.status = "created"
                # Use returned number if present, otherwise keep the pre-existing one
                order.fortnox_order_number = result.get("fortnox_order_number") or order.fortnox_order_number
                created += 1
                db.add(ApprovalLog(
                    order_id=order_uuid,
                    action="created",
                    performed_by="n8n",
                    details={"fortnox_order_number": order.fortnox_order_number},
                ))
                logger.info(f"Order {oid} created in Fortnox: {order.fortnox_order_number}")
            else:
                order.status = "failed"
                order.error_message = result.get("error", "Unknown error from n8n")
                failed += 1
                db.add(ApprovalLog(
                    order_id=order_uuid,
                    action="failed",
                    performed_by="n8n",
                    details={"error": order.error_message},
                ))
                logger.error(f"Order {oid} creation failed: {order.error_message}")

        except Exception as e:
            order.status = "failed"
            order.error_message = f"n8n webhook error: {str(e)}"
            failed += 1
            db.add(ApprovalLog(
                order_id=order_uuid,
                action="failed",
                performed_by="system",
                details={"error": str(e)},
            ))
            logger.error(f"Order {oid} n8n call failed: {e}")

        db.commit()

        # Rate limit: Fortnox allows 4 req/sec, add delay between orders
        await asyncio.sleep(0.3)

    flash = f"Approved: {approved}"
    if created:
        flash += f", Created in Fortnox: {created}"
    if failed:
        flash += f", Failed: {failed}"

    redirect_url = f"/orders?tab={redirect_tab}&flash={flash}"
    if redirect_from:
        redirect_url += f"&delivery_from={redirect_from}"
    if redirect_to:
        redirect_url += f"&delivery_to={redirect_to}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/orders/deny")
async def deny_orders(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Deny selected orders."""
    form = await request.form()
    order_ids_str = form.get("order_ids", "")
    if not order_ids_str:
        return RedirectResponse(url="/orders?flash=No orders selected", status_code=302)

    order_ids = [s.strip() for s in order_ids_str.split(",") if s.strip()]
    redirect_tab = form.get("tab", "recurring")
    redirect_from = form.get("delivery_from", "")
    redirect_to = form.get("delivery_to", "")
    denied = 0

    for oid in order_ids:
        try:
            order_uuid = uuid.UUID(oid)
        except ValueError:
            continue

        order = db.query(PendingOrder).filter(PendingOrder.id == order_uuid).first()
        if not order or order.status != "pending":
            continue

        order.status = "denied"
        order.reviewed_at = datetime.utcnow()
        denied += 1

        db.add(ApprovalLog(
            order_id=order_uuid,
            action="denied",
            performed_by="dashboard",
        ))

    db.commit()
    logger.info(f"Denied {denied} orders")

    redirect_url = f"/orders?tab={redirect_tab}&flash={denied} orders denied"
    if redirect_from:
        redirect_url += f"&delivery_from={redirect_from}"
    if redirect_to:
        redirect_url += f"&delivery_to={redirect_to}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/orders/delete")
async def delete_orders(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Soft-delete selected orders (pending, denied, or failed only)."""
    form = await request.form()
    order_ids_str = form.get("order_ids", "")
    if not order_ids_str:
        return RedirectResponse(url="/orders?flash=No orders selected", status_code=302)

    order_ids = [s.strip() for s in order_ids_str.split(",") if s.strip()]
    DELETABLE_STATUSES = {"pending", "denied", "failed"}
    deleted_count = 0

    for oid in order_ids:
        try:
            order_uuid = uuid.UUID(oid)
        except ValueError:
            continue

        order = db.query(PendingOrder).filter(PendingOrder.id == order_uuid).first()
        if not order:
            continue
        if order.status not in DELETABLE_STATUSES:
            # Already sent to Fortnox — do not delete
            logger.warning(f"Skipping delete for order {oid} with status '{order.status}'")
            continue

        # Hard-delete: remove logs first (FK), then the order itself
        # This clears the unique constraint so A2 can re-submit the order
        db.query(ApprovalLog).filter(ApprovalLog.order_id == order_uuid).delete()
        db.delete(order)
        deleted_count += 1

    db.commit()
    logger.info(f"Deleted {deleted_count} orders")

    tab = form.get("tab", "recurring")
    redirect_from = form.get("delivery_from", "")
    redirect_to = form.get("delivery_to", "")
    redirect_url = f"/orders?tab={tab}&flash={deleted_count} orders deleted"
    if redirect_from:
        redirect_url += f"&delivery_from={redirect_from}"
    if redirect_to:
        redirect_url += f"&delivery_to={redirect_to}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/api/orders", response_class=JSONResponse)
async def api_orders(
    tab: str = "recurring",
    status: str = "pending",
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """JSON API for dynamic order data."""
    query = db.query(PendingOrder).filter(PendingOrder.status != "deleted")
    if tab in ("recurring", "new"):
        query = query.filter(PendingOrder.source == tab)
    if status != "all":
        query = query.filter(PendingOrder.status == status)

    orders = query.order_by(PendingOrder.delivery_date).all()

    return [
        {
            "id": str(o.id),
            "customer_name": o.customer_name,
            "customer_number": o.customer_number,
            "item_summary": o.item_summary,
            "delivery_date": str(o.delivery_date),
            "administration_fee": float(o.administration_fee or 0),
            "freight": float(o.freight or 0),
            "total_amount": float(o.total_amount or 0),
            "remarks": o.remarks,
            "status": o.status,
        }
        for o in orders
    ]
