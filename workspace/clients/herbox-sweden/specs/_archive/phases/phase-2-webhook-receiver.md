# Phase 2: Webhook Receiver

**Depends on:** Phase 1 (Database Models)
**Estimated effort:** 30 minutes
**Output:** New endpoint `POST /webhook/pending-orders` that stores orders from n8n

---

## Objective

Add a webhook endpoint to the existing `webhooks.py` router that receives formatted orders from the A1 n8n workflow and stores them in the `pending_orders` table. This endpoint replaces the direct Fortnox order creation.

---

## Files to Modify

### `app/routers/webhooks.py`

Add the following at the end of the file (before the commented-out examples):

```python
# === Order Approval Dashboard: Pending Orders Receiver ===

from pydantic import BaseModel as PydanticBaseModel
from typing import Optional
from datetime import date


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
    your_order_number: str  # UNIQUE — used for duplicate prevention


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
            # Check for duplicate (upsert logic)
            existing = db.query(PendingOrder).filter(
                PendingOrder.your_order_number == order_data.your_order_number
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

            # Create pending order
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
                your_order_number=order_data.your_order_number,
                status="pending",
                generated_at=datetime.utcnow(),
            )

            db.add(pending_order)
            stored += 1

        db.commit()
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
```

---

## n8n Payload Format

The n8n workflow will POST a batch of orders. Example payload:

```json
{
  "orders": [
    {
      "contract_number": "12345",
      "customer_number": "100",
      "customer_name": "Foretag AB",
      "source": "recurring",
      "order_payload": {
        "Order": {
          "CustomerNumber": "100",
          "DeliveryDate": "2026-02-20",
          "OrderDate": "2026-02-20",
          "OrderRows": [
            {
              "ArticleNumber": "MENS-001",
              "Description": "Mensskydd Tena",
              "DeliveredQuantity": 3,
              "Price": 150.00,
              "VAT": 25
            }
          ],
          "AdministrationFee": 150,
          "Freight": 499,
          "Remarks": "Leverans varannan manad",
          "YourOrderNumber": "C12345-2026-02-20",
          "YourReference": "Anna Svensson",
          "OurReference": "Rebecca",
          "Currency": "SEK",
          "TermsOfPayment": "30",
          "CostCenter": "2",
          "StockPointCode": "2"
        }
      },
      "delivery_date": "2026-02-20",
      "order_date": "2026-02-20",
      "total_amount": 1099.00,
      "currency": "SEK",
      "item_count": 1,
      "item_summary": "3x Mensskydd Tena",
      "administration_fee": 150.00,
      "freight": 499.00,
      "remarks": "Leverans varannan manad",
      "period_start": "2026-05-20",
      "your_order_number": "C12345-2026-02-20"
    }
  ]
}
```

---

## Duplicate Prevention

The `your_order_number` column has a UNIQUE constraint. The webhook checks for existing rows with the same value before inserting. This means:

- Running A1 multiple times on the same day produces no duplicates
- The pattern `C{DocumentNumber}-{PeriodEnd}` ensures one order per contract per period

---

## Verification

1. Start the app locally
2. POST a test payload:

```bash
curl -X POST http://localhost:8000/webhook/pending-orders \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [{
      "contract_number": "99999",
      "customer_number": "TEST",
      "customer_name": "Test Company AB",
      "source": "recurring",
      "order_payload": {"Order": {"CustomerNumber": "TEST"}},
      "delivery_date": "2026-02-20",
      "total_amount": 500.00,
      "item_count": 1,
      "item_summary": "1x Test Product",
      "your_order_number": "C99999-2026-02-20"
    }]
  }'
```

3. Verify response: `{"status": "received", "stored": 1, "duplicates_skipped": 0}`
4. POST the same payload again — should get `{"stored": 0, "duplicates_skipped": 1}`
5. Check the database: row exists with `status='pending'`
