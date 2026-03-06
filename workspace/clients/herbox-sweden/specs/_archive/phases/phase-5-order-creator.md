# Phase 5: Order Creator Workflow

**Depends on:** Phase 4 (Dashboard with approve route)
**Estimated effort:** 1-2 hours
**Output:** n8n webhook that creates Fortnox orders + FastAPI approve route that calls it

---

## Objective

When Rebecca approves orders in the dashboard, the FastAPI app calls an n8n webhook which creates the order in Fortnox (n8n holds the OAuth2 credentials). The result is returned to FastAPI which updates the order status.

---

## Component 1: New n8n Workflow — "Order Creator"

Create a new workflow via `n8n_create_workflow` MCP tool.

### Workflow Structure

```
Webhook Trigger (POST /webhook/create-fortnox-order)
    → Create Fortnox Order (POST /3/orders)
    → Format Response (Code node)
    → Respond to Webhook
```

### Nodes

#### Node 1: Webhook Trigger

```json
{
  "id": "wh-trigger-001",
  "name": "Webhook Trigger",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2,
  "position": [0, 300],
  "parameters": {
    "httpMethod": "POST",
    "path": "create-fortnox-order",
    "responseMode": "responseNode",
    "options": {}
  },
  "webhookId": "create-fortnox-order"
}
```

#### Node 2: Create Fortnox Order

```json
{
  "id": "create-order-001",
  "name": "Create Fortnox Order",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [300, 300],
  "parameters": {
    "method": "POST",
    "url": "https://api.fortnox.se/3/orders",
    "authentication": "genericCredentialType",
    "genericAuthType": "oAuth2Api",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        { "name": "Content-Type", "value": "application/json" },
        { "name": "Accept", "value": "application/json" }
      ]
    },
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ JSON.stringify($json.order_payload) }}",
    "options": {
      "response": { "response": { "responseFormat": "json" } }
    }
  },
  "credentials": {
    "oAuth2Api": {
      "id": "jwn2NCWpooneGXpx",
      "name": "Herbox - OAuth2 Credentials"
    }
  },
  "continueOnFail": true
}
```

#### Node 3: Format Response

```json
{
  "id": "format-response-001",
  "name": "Format Response",
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [600, 300],
  "parameters": {
    "jsCode": "const input = $input.first().json;\nconst webhookData = $node['Webhook Trigger'].json;\nconst orderId = webhookData.order_id;\n\n// Check if the HTTP request succeeded\nif (input.Order && input.Order.DocumentNumber) {\n  return {\n    json: {\n      success: true,\n      order_id: orderId,\n      fortnox_order_number: String(input.Order.DocumentNumber),\n      document_number: String(input.Order.DocumentNumber),\n    }\n  };\n} else {\n  // Error case\n  const errorMsg = input.ErrorInformation?.Message || input.message || JSON.stringify(input);\n  return {\n    json: {\n      success: false,\n      order_id: orderId,\n      error: errorMsg,\n    }\n  };\n}"
  }
}
```

#### Node 4: Respond to Webhook

```json
{
  "id": "respond-001",
  "name": "Respond to Webhook",
  "type": "n8n-nodes-base.respondToWebhook",
  "typeVersion": 1.1,
  "position": [900, 300],
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ $json }}"
  }
}
```

### Connections

```json
{
  "Webhook Trigger": {
    "main": [[ { "node": "Create Fortnox Order", "type": "main", "index": 0 } ]]
  },
  "Create Fortnox Order": {
    "main": [[ { "node": "Format Response", "type": "main", "index": 0 } ]]
  },
  "Format Response": {
    "main": [[ { "node": "Respond to Webhook", "type": "main", "index": 0 } ]]
  }
}
```

### Activation

After creation, activate the workflow so the webhook is live. The webhook URL will be:
`https://primary-production-ef56.up.railway.app/webhook/create-fortnox-order`

---

## Component 2: FastAPI Approve Route

### `app/routers/orders.py` — approve handler

The `/orders/approve` POST route (defined in Phase 4) needs to call the n8n webhook for each approved order:

```python
import httpx

@router.post("/orders/approve")
async def approve_orders(
    request: Request,
    order_ids: str = Form(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Approve selected orders and create them in Fortnox via n8n."""
    ids = [id.strip() for id in order_ids.split(",") if id.strip()]

    results = {"created": 0, "failed": 0, "errors": []}
    n8n_webhook_url = settings.n8n_create_order_webhook

    for order_id in ids:
        order = db.query(PendingOrder).filter(PendingOrder.id == order_id).first()
        if not order or order.status not in ("pending", "failed"):
            continue

        # Update status to approved
        order.status = "approved"
        order.reviewed_at = datetime.utcnow()
        db.commit()

        # Call n8n webhook to create in Fortnox
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json={
                        "order_id": str(order.id),
                        "order_payload": order.order_payload,
                    },
                )
                result = response.json()

            if result.get("success"):
                order.status = "created"
                order.fortnox_order_number = result.get("fortnox_order_number")
                results["created"] += 1

                # Log success
                log_entry = ApprovalLog(
                    order_id=order.id,
                    action="created",
                    performed_by="rebecca",
                    details={"fortnox_order_number": result.get("fortnox_order_number")},
                )
                db.add(log_entry)
            else:
                order.status = "failed"
                order.error_message = result.get("error", "Unknown error")
                results["failed"] += 1
                results["errors"].append(f"{order.customer_name}: {order.error_message}")

                # Log failure
                log_entry = ApprovalLog(
                    order_id=order.id,
                    action="failed",
                    performed_by="rebecca",
                    details={"error": order.error_message},
                )
                db.add(log_entry)

        except Exception as e:
            order.status = "failed"
            order.error_message = str(e)
            results["failed"] += 1
            results["errors"].append(f"{order.customer_name}: {str(e)}")

            log_entry = ApprovalLog(
                order_id=order.id,
                action="failed",
                performed_by="rebecca",
                details={"error": str(e)},
            )
            db.add(log_entry)

        db.commit()

    # Redirect back with results as query params
    return RedirectResponse(
        url=f"/orders?msg=Created {results['created']} orders, {results['failed']} failed",
        status_code=302,
    )
```

---

## Configuration

### `app/config.py`

Add n8n webhook URL setting:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # n8n Order Creator webhook URL
    n8n_create_order_webhook: str = ""  # Set via N8N_CREATE_ORDER_WEBHOOK env var
```

### Environment Variables

| Variable | Value | Where |
|----------|-------|-------|
| `N8N_CREATE_ORDER_WEBHOOK` | `https://primary-production-ef56.up.railway.app/webhook/create-fortnox-order` | Railway FastAPI app |

---

## Rate Limiting

Fortnox allows 4 req/sec. When bulk-approving many orders, the sequential processing in the approve loop naturally spaces requests (each takes ~500ms for the HTTP round-trip). For safety, add a small delay if needed:

```python
import asyncio
# After each n8n call:
await asyncio.sleep(0.3)  # 300ms delay between Fortnox API calls
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| n8n webhook unreachable | Set status='failed', error_message="Connection error" |
| n8n returns non-200 | Set status='failed', capture HTTP status + body |
| Fortnox rejects order (400) | n8n returns `{ success: false, error: "..." }` → status='failed' |
| Fortnox auth expired (401) | n8n auto-refreshes OAuth2 token → retry happens in n8n |
| Fortnox rate limit (429) | n8n retries (built-in) |
| Partial failure in bulk | Each order handled independently; some may succeed, others fail |

Failed orders remain in the dashboard with `status='failed'` and `error_message`. Rebecca can fix the issue and re-approve them (the approve route accepts `status in ('pending', 'failed')`).

---

## Verification

1. **Create n8n workflow** via MCP tools
2. **Test webhook directly:**

```bash
curl -X POST https://primary-production-ef56.up.railway.app/webhook/create-fortnox-order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-123",
    "order_payload": {
      "Order": {
        "CustomerNumber": "100",
        "DeliveryDate": "2026-03-01",
        "OrderRows": [
          {
            "ArticleNumber": "TEST-001",
            "Description": "Test Product",
            "DeliveredQuantity": 1,
            "Price": 100
          }
        ]
      }
    }
  }'
```

3. **Verify response:** `{ "success": true, "fortnox_order_number": "XXXXX" }`
4. **Test from dashboard:** Approve a pending order → verify Fortnox order created
5. **Test bulk approve:** Select 3 orders → approve → all 3 created
6. **Test error case:** Submit invalid CustomerNumber → verify `status='failed'` with error message
7. **Test re-approve:** A failed order can be approved again

---

## Component 3: New n8n Workflow — "Order Updater" (for A2 Enrichment)

Create a separate workflow for **updating** existing Fortnox orders with enrichment data from A2. Keep it separate from Order Creator to avoid breaking the working creation flow.

**n8n workflow name:** `Order Updater`
**Webhook path:** `POST /webhook/update-fortnox-order`
**Called by:** FastAPI `approve_orders` when `order.fortnox_order_number` is pre-set (Upsales enrichment orders)

### Workflow Structure

```
Webhook Trigger (POST /webhook/update-fortnox-order)
    → Update Fortnox Order (PUT /3/orders/{fortnox_order_number})
    → Format Response (Code node)
    → Respond to Webhook
```

### Nodes

#### Node 1: Webhook Trigger

```json
{
  "name": "Webhook Trigger",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2,
  "parameters": {
    "httpMethod": "POST",
    "path": "update-fortnox-order",
    "responseMode": "responseNode",
    "options": {}
  }
}
```

#### Node 2: Update Fortnox Order

```json
{
  "name": "Update Fortnox Order",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "parameters": {
    "method": "PUT",
    "url": "=https://api.fortnox.se/3/orders/{{ $json.fortnox_order_number }}",
    "authentication": "genericCredentialType",
    "genericAuthType": "oAuth2Api",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        { "name": "Content-Type", "value": "application/json" },
        { "name": "Accept", "value": "application/json" }
      ]
    },
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ JSON.stringify($json.enrichment_payload) }}",
    "options": {
      "response": { "response": { "responseFormat": "json" } }
    }
  },
  "credentials": {
    "oAuth2Api": {
      "id": "jwn2NCWpooneGXpx",
      "name": "Herbox - OAuth2 Credentials"
    }
  },
  "continueOnFail": true
}
```

**Critical:** `enrichment_payload` contains ONLY the enrichment fields — NOT `OrderRows`. Fortnox deletes existing rows if `OrderRows` is included in a PUT request.

#### Node 3: Format Response

```javascript
const input = $input.first().json;
const webhookData = $('Webhook Trigger').first().json;
const orderId = webhookData.order_id;
const fortnoxOrderNumber = webhookData.fortnox_order_number;

if (input.Order && input.Order.DocumentNumber) {
  return {
    json: {
      success: true,
      order_id: orderId,
      fortnox_order_number: String(input.Order.DocumentNumber),
    }
  };
} else {
  const errorMsg = input.ErrorInformation?.Message || input.message || JSON.stringify(input);
  return {
    json: {
      success: false,
      order_id: orderId,
      fortnox_order_number: fortnoxOrderNumber,
      error: errorMsg,
    }
  };
}
```

#### Node 4: Respond to Webhook

```json
{
  "name": "Respond to Webhook",
  "type": "n8n-nodes-base.respondToWebhook",
  "typeVersion": 1.1,
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ $json }}"
  }
}
```

### Input Payload (from FastAPI)

```json
{
  "order_id": "uuid-from-dashboard",
  "fortnox_order_number": "12345",
  "enrichment_payload": {
    "Order": {
      "Phone1": "070-123 45 67",
      "DeliveryAddress1": "Testgatan 1",
      "DeliveryCity": "Stockholm",
      "DeliveryZipCode": "12345",
      "DeliveryCountry": "SE",
      "Freight": 299,
      "FreightVAT": 25,
      "Remarks": "Order synkad från Upsales"
    }
  }
}
```

### Response

```json
{ "success": true, "order_id": "uuid", "fortnox_order_number": "12345" }
```

### Verification

```bash
curl -X POST https://primary-production-ef56.up.railway.app/webhook/update-fortnox-order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-123",
    "fortnox_order_number": "EXISTING-ORDER-NUMBER",
    "enrichment_payload": {
      "Order": {
        "Remarks": "Test enrichment via Order Updater"
      }
    }
  }'
```

Expected: `{ "success": true, "fortnox_order_number": "EXISTING-ORDER-NUMBER" }`
Then verify in Fortnox UI that the Remarks field was updated and no order rows were modified.
