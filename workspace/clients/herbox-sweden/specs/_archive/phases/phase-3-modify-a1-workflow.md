# Phase 3: Modify A1 n8n Workflow

**Depends on:** Phase 2 (Webhook Receiver deployed)
**Estimated effort:** 1-2 hours
**Output:** A1 workflow stores pending orders in FastAPI instead of creating in Fortnox

---

## Objective

Modify the live A1 Recurring Order workflow (ID: `qJHgvXLKFdCBja1o`) to:
1. Fetch the previous order's Remarks (from the same contract)
2. Enrich orders with administration fee, freight, postponed period start
3. POST formatted orders to the FastAPI webhook instead of directly creating in Fortnox
4. Update the notification to reflect "pending review" instead of "created"

---

## Current Workflow Chain (Stage 3-4)

```
Is Not Duplicate? (41087c8a)
    → Format Fortnox Order1 (0b958555) [Code node]
    → [DISCONNECTED]

CREATE Fortnox Order (203ce602) [HTTP Request]
    → Format Notification (6e9d99b0)
    → Send Notification (341a3a66)
```

Note: `Format Fortnox Order1` is currently NOT connected to `CREATE Fortnox Order`. The CREATE node was intentionally left disconnected during testing.

---

## Target Workflow Chain (Stage 3-4)

```
Is Not Duplicate? (41087c8a)
    → GET Previous Order [NEW HTTP node]
    → Enrich & Format Order [REPLACE Format Fortnox Order1 code]
    → POST to FastAPI [NEW HTTP node — replaces CREATE Fortnox Order]
    → Format Notification (6e9d99b0) [UPDATE text]
    → Send Notification (341a3a66)
```

---

## Operations (via `n8n_update_partial_workflow`)

### Operation 1: Add "GET Previous Order" Node

**Type:** `addNode`

A new HTTP Request node that fetches the most recent order from the same contract:

```json
{
  "type": "addNode",
  "node": {
    "id": "prev-order-001",
    "name": "GET Previous Order",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [4050, 496],
    "parameters": {
      "method": "GET",
      "url": "=https://api.fortnox.se/3/orders?customernumber={{ $json.CustomerNumber }}",
      "authentication": "genericCredentialType",
      "genericAuthType": "oAuth2Api",
      "sendHeaders": true,
      "headerParameters": {
        "parameters": [
          { "name": "Accept", "value": "application/json" }
        ]
      },
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
}
```

### Operation 2: Update "Format Fortnox Order1" Code

**Type:** `updateNode`

Replace the JavaScript in the existing Code node with the enriched version:

```json
{
  "type": "updateNode",
  "nodeId": "0b958555-5a7f-4b33-9d00-7d3ad0211155",
  "changes": {
    "name": "Enrich & Format Order",
    "parameters": {
      "jsCode": "<see Enrichment Code below>"
    }
  }
}
```

### Operation 3: Add "POST to FastAPI" Node

**Type:** `addNode`

New HTTP Request node that sends the formatted order to the Railway FastAPI webhook:

```json
{
  "type": "addNode",
  "node": {
    "id": "post-fastapi-001",
    "name": "POST to FastAPI",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [4500, 496],
    "parameters": {
      "method": "POST",
      "url": "={{ $env.RAILWAY_WEBHOOK_URL }}/webhook/pending-orders",
      "sendBody": true,
      "bodyParameters": {
        "parameters": []
      },
      "specifyBody": "json",
      "jsonBody": "={{ JSON.stringify({ orders: [$json] }) }}",
      "options": {
        "response": { "response": { "responseFormat": "json" } }
      }
    },
    "continueOnFail": true
  }
}
```

> Note: `RAILWAY_WEBHOOK_URL` must be set as an n8n environment variable pointing to the Railway app URL.

### Operation 4: Rewire Connections

Remove old connections and add new ones:

```json
[
  {
    "type": "removeConnection",
    "source": "Is Not Duplicate?",
    "target": "Format Fortnox Order1",
    "sourcePort": "main",
    "targetPort": "main"
  },
  {
    "type": "addConnection",
    "source": "Is Not Duplicate?",
    "target": "GET Previous Order",
    "sourcePort": "main",
    "targetPort": "main",
    "branch": "true"
  },
  {
    "type": "addConnection",
    "source": "GET Previous Order",
    "target": "Enrich & Format Order",
    "sourcePort": "main",
    "targetPort": "main"
  },
  {
    "type": "addConnection",
    "source": "Enrich & Format Order",
    "target": "POST to FastAPI",
    "sourcePort": "main",
    "targetPort": "main"
  },
  {
    "type": "addConnection",
    "source": "POST to FastAPI",
    "target": "Format Notification",
    "sourcePort": "main",
    "targetPort": "main"
  }
]
```

### Operation 5: Update Notification Text

**Type:** `updateNode`

Update `Format Notification` code to say "pending review":

```json
{
  "type": "updateNode",
  "nodeId": "6e9d99b0-574e-4107-9321-c3b0730acf75",
  "changes": {
    "parameters": {
      "jsCode": "<see Notification Code below>"
    }
  }
}
```

---

## Enrichment Code (for "Enrich & Format Order" node)

```javascript
// Input: contract data from Extract Contract Detail1 + previous orders from GET Previous Order
const contract = $json;
const previousOrdersResponse = $node['GET Previous Order'].json;
const previousOrders = previousOrdersResponse?.Orders || [];

// Find the most recent order from the SAME contract (YourOrderNumber starts with C{DocNum}-)
const contractPrefix = `C${contract.DocumentNumber}-`;
const previousContractOrder = previousOrders.find(o =>
  o.YourOrderNumber && o.YourOrderNumber.startsWith(contractPrefix)
);

// Build OrderRows from InvoiceRows
const orderRows = (contract.InvoiceRows || []).map(row => {
  const orderRow = {
    ArticleNumber: row.ArticleNumber,
    Description: row.Description,
    DeliveredQuantity: row.DeliveredQuantity || row.Quantity || 1,
    Price: row.Price,
    VAT: row.VAT,
  };
  if (row.Unit) orderRow.Unit = row.Unit;
  if (row.Discount) orderRow.Discount = row.Discount;
  if (row.AccountNumber) orderRow.AccountNumber = row.AccountNumber;
  if (row.CostCenter) orderRow.CostCenter = row.CostCenter;
  if (row.Project) orderRow.Project = row.Project;
  return orderRow;
});

// Calculate postponed PeriodStart
const invoiceInterval = contract.InvoiceInterval || 3; // months
const currentPeriodStart = contract.PeriodStart ? new Date(contract.PeriodStart) : new Date();
const newPeriodStart = new Date(currentPeriodStart);
newPeriodStart.setMonth(newPeriodStart.getMonth() + invoiceInterval);
const periodStartStr = newPeriodStart.toISOString().split('T')[0];

// DeliveryDate = PeriodEnd; OrderDate = DeliveryDate
const deliveryDate = contract.PeriodEnd;

// Copy Remarks from previous order of the same contract
const remarks = previousContractOrder?.Remarks || '';

// Administration fee and freight from contract
const administrationFee = contract.AdministrationFee || 0;
const freight = contract.Freight || 0;

// Build the complete Order payload
const order = {
  CustomerNumber: String(contract.CustomerNumber),
  DeliveryDate: deliveryDate,
  OrderDate: deliveryDate,
  OrderRows: orderRows,
  Comments: `Auto-generated from contract #${contract.DocumentNumber}`,
  YourOrderNumber: `C${contract.DocumentNumber}-${contract.PeriodEnd}`,
  YourReference: contract.YourReference || '',
  OurReference: contract.OurReference || '',
  AdministrationFee: administrationFee,
  Freight: freight,
  Remarks: remarks,
};

// Copy optional fields from contract
if (contract.Currency) order.Currency = contract.Currency;
if (contract.TermsOfDelivery) order.TermsOfDelivery = contract.TermsOfDelivery;
if (contract.TermsOfPayment) order.TermsOfPayment = contract.TermsOfPayment;
if (contract.WayOfDelivery) order.WayOfDelivery = contract.WayOfDelivery;
if (contract.PriceList) order.PriceList = contract.PriceList;
order.CostCenter = '2';
order.StockPointCode = '2';
if (contract.Project) order.Project = contract.Project;

// Calculate display fields for the dashboard
const itemTotal = orderRows.reduce((sum, r) =>
  sum + ((r.Price || 0) * (r.DeliveredQuantity || 1)), 0
);
const totalAmount = itemTotal + administrationFee + freight;

const itemSummary = orderRows
  .map(r => `${r.DeliveredQuantity || 1}x ${r.Description || r.ArticleNumber}`)
  .join(', ');

// Return the webhook payload format
return {
  json: {
    contract_number: String(contract.DocumentNumber),
    customer_number: String(contract.CustomerNumber),
    customer_name: contract.CustomerName || '',
    source: 'recurring',
    order_payload: { Order: order },
    delivery_date: deliveryDate,
    order_date: deliveryDate,
    total_amount: Math.round(totalAmount * 100) / 100,
    currency: order.Currency || 'SEK',
    item_count: orderRows.length,
    item_summary: itemSummary,
    administration_fee: administrationFee,
    freight: freight,
    remarks: remarks,
    period_start: periodStartStr,
    your_order_number: order.YourOrderNumber,
  }
};
```

---

## Notification Code (for "Format Notification" node)

```javascript
// Updated to say "pending review" instead of "created"
const order = $json;

const message = [
  `*Order Pending Review*`,
  `Contract: #${order.contract_number}`,
  `Customer: ${order.customer_name} (${order.customer_number})`,
  `Delivery: ${order.delivery_date}`,
  `Items: ${order.item_summary}`,
  `Total: ${order.total_amount} ${order.currency}`,
  `Admin Fee: ${order.administration_fee} ${order.currency}`,
  `Freight: ${order.freight} ${order.currency}`,
  order.remarks ? `Remarks: ${order.remarks}` : '',
  ``,
  `Review at: ${$env.RAILWAY_PUBLIC_URL || 'dashboard'}/orders`,
].filter(Boolean).join('\n');

return { json: { text: message } };
```

---

## Environment Variables to Set in n8n

| Variable | Value | Purpose |
|----------|-------|---------|
| `RAILWAY_WEBHOOK_URL` | `https://<railway-domain>` | FastAPI app URL for webhook POST |
| `RAILWAY_PUBLIC_URL` | `https://<railway-domain>` | For notification links to dashboard |

Set these in the n8n instance Settings > Environment Variables.

---

## Testing

1. **Set DEBUG NODE limit to 2** (already in place)
2. **Run the workflow manually** via n8n UI (click "Test workflow" button on Schedule Trigger1)
3. **Check "GET Previous Order" output:** Should return orders for each customer
4. **Check "Enrich & Format Order" output:** Verify enriched fields:
   - `administration_fee` has a value from contract
   - `freight` has a value from contract
   - `remarks` copied from previous order (may be empty for first run)
   - `period_start` is future date (PeriodStart + InvoiceInterval months)
   - `order_date` = `delivery_date`
5. **Check "POST to FastAPI" output:** 200 response with `{"status": "received", "stored": N}`
6. **Check Railway app database:** Rows in `pending_orders` table
7. **Check notification:** Slack message says "Order Pending Review"

### Rollback

If something goes wrong, the original `Format Fortnox Order1` code is preserved in `clients/herbox-sweden/context/a1-n8n-workflow.json`. The `CREATE Fortnox Order` node was removed during implementation (validation doesn't allow disconnected nodes) but can be recreated from the backup. The workflow also has version history via `n8n_workflow_versions`.

---

## Implementation Notes (2026-02-13)

**Status:** Done

**Key deviation from spec:**
- The enrichment code uses `$node['Calculate Order Timing1'].json` for contract data (not `$json`) because inserting the GET Previous Order HTTP Request node between Is Not Duplicate? and the Code node replaces `$json` with the API response. The spec's code had `const contract = $json` which would have been incorrect.
- `CREATE Fortnox Order` node was removed (not just disconnected) because n8n validation rejects disconnected non-sticky nodes. Full backup exists in `a1-n8n-workflow.json`.
- Used typeVersion 4.1 for new HTTP nodes (matching existing nodes) instead of 4.2 from spec.

**Environment variables still needed in n8n:**
- `RAILWAY_WEBHOOK_URL` — Railway app base URL for webhook POST
- `RAILWAY_PUBLIC_URL` — For notification links to dashboard
