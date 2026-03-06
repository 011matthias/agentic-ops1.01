# Phase 4: Dashboard Frontend

**Depends on:** Phase 1 (Database Models)
**Estimated effort:** 2-3 hours
**Output:** `/orders` page with table, tabs, filters, edit, approve/deny, bulk actions

---

## Objective

Add an Orders section to the existing Herbox FastAPI dashboard. Rebecca can view, filter, edit, approve, and deny pending orders. The UI follows the existing Jinja2 template patterns (inline CSS, no build tools).

---

## Files to Create

### `app/routers/orders.py`

New router with dashboard pages and API endpoints:

```python
"""
Order Approval Dashboard routes.

PRD: specs/prd-order-dashboard.md
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
import json
import logging

from ..db import get_db
from ..auth import require_auth
from ..config import get_settings
from ..models.pending_orders import PendingOrder, ApprovalLog

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()
logger = logging.getLogger(__name__)
```

**Routes:**

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/orders` | GET | Yes | Main orders page with table |
| `/orders/{id}` | GET | Yes | Order detail + edit page |
| `/orders/{id}/edit` | POST | Yes | Save order edits |
| `/orders/approve` | POST | Yes | Approve selected orders |
| `/orders/deny` | POST | Yes | Deny selected orders |
| `/api/orders` | GET | Yes | JSON API for dynamic updates |

#### GET `/orders`

Query `pending_orders` with filters:
- `?tab=recurring` (default) or `?tab=new`
- `?status=pending` (default) or `?status=all`, `approved`, `denied`, `created`, `failed`
- `?sort=delivery_date` (default), `customer_name`, `total_amount`

Return `orders.html` template with:
- `orders`: list of PendingOrder objects
- `stats`: `{ pending_count, total_value, approved_count, denied_count }`
- `active_tab`: 'recurring' or 'new'
- `active_status`: filter value
- Standard context: `request`, `client_display_name`

#### GET `/orders/{id}`

Fetch single PendingOrder by UUID.
Parse `order_payload` JSON to extract OrderRows for display.
Fetch related ApprovalLog entries.
Return `order_detail.html`.

#### POST `/orders/{id}/edit`

Accept form data with:
- Order-level: `remarks`, `freight`, `administration_fee`, `delivery_date`
- Line items: `rows` as JSON string (array of {ArticleNumber, Description, DeliveredQuantity, Price, VAT, Unit})

Update both `order_payload` JSONB and denormalized display fields.
Log edit in `approval_log`.
Redirect back to `/orders/{id}`.

#### POST `/orders/approve`

Accept form data: `order_ids` (comma-separated UUIDs).

For each order:
1. Update status to `'approved'`
2. Set `reviewed_at` to now
3. Call n8n webhook to create in Fortnox (see Phase 5)
4. On success: update status to `'created'`, set `fortnox_order_number`
5. On failure: update status to `'failed'`, set `error_message`
6. Log in `approval_log`

Redirect back to `/orders` with flash message.

#### POST `/orders/deny`

Accept form data: `order_ids` (comma-separated UUIDs).
Update status to `'denied'`, set `reviewed_at`.
Log in `approval_log`.
Redirect back to `/orders`.

---

### `app/templates/orders.html`

Main orders page. Follows the existing styling from `index.html` (inline CSS, same header/nav).

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  Herbox - Automations              [nav links]      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Stats: 12 pending | 45,230 SEK total               │
│                                                     │
│  [Recurring Orders (8)] [New Orders (--)]           │
│                                                     │
│  Status: [Pending ▼]                                │
│                                                     │
│  ┌──┬──────────┬─────────┬──────┬─────┬──────┬────┐ │
│  │☐ │ Customer │ Items   │ Del. │Admin│Freig│Total│ │
│  │  │          │         │ Date │ Fee │  ht │     │ │
│  ├──┼──────────┼─────────┼──────┼─────┼──────┼────┤ │
│  │☐ │ Foretag  │ 3x Mens │02-20│ 150 │ 499 │4850│ │
│  │  │ #100     │ skydd   │     │ SEK │ SEK │SEK │ │
│  ├──┼──────────┼─────────┼──────┼─────┼──────┼────┤ │
│  │☐ │ Kommun   │ 5x Tvatt│02-22│   0 │ 499 │2499│ │
│  │  │ #205     │ lapp    │     │ SEK │ SEK │SEK │ │
│  └──┴──────────┴─────────┴──────┴─────┴──────┴────┘ │
│                                                     │
│  [✓ Approve 2 selected] [✗ Deny 2 selected]        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Key elements:**

1. **Header nav:** Add "Orders" link between "Dashboard" and "Automations"
2. **Stats bar:** Aggregate counts and values
3. **Tab bar:** "Recurring Orders (N)" and "New Orders (--)" — tabs link to `?tab=recurring` / `?tab=new`
4. **Status filter:** Dropdown that links to `?status=pending` etc.
5. **Table:** Each row has:
   - Checkbox (value = order UUID)
   - Customer (name + number)
   - Items (truncated `item_summary`)
   - Delivery Date
   - Admin Fee
   - Freight
   - Total
   - Status badge (color-coded)
   - Actions: "View" link to `/orders/{id}`
6. **Bulk action bar:** Fixed at bottom, shown via JavaScript when checkboxes selected
   - "Approve X selected" button (submits form to `/orders/approve`)
   - "Deny X selected" button (submits form to `/orders/deny`)
   - Confirmation dialog before submit

**Status badges:**

| Status | Color | Background |
|--------|-------|------------|
| pending | #b06000 | #fef7e0 |
| approved | #1565c0 | #e3f2fd |
| created | #1e7e34 | #e6f4ea |
| denied | #666 | #f5f5f5 |
| failed | #c5221f | #fce8e6 |

**JavaScript (inline):**

```javascript
// Checkbox selection tracking
const checkboxes = document.querySelectorAll('.order-checkbox');
const selectAll = document.getElementById('select-all');
const bulkBar = document.getElementById('bulk-actions');
const approveBtn = document.getElementById('bulk-approve');
const denyBtn = document.getElementById('bulk-deny');

selectAll.addEventListener('change', (e) => {
  checkboxes.forEach(cb => cb.checked = e.target.checked);
  updateBulkBar();
});

checkboxes.forEach(cb => cb.addEventListener('change', updateBulkBar));

function updateBulkBar() {
  const selected = document.querySelectorAll('.order-checkbox:checked');
  if (selected.length > 0) {
    bulkBar.style.display = 'flex';
    approveBtn.textContent = `Approve ${selected.length} selected`;
    denyBtn.textContent = `Deny ${selected.length} selected`;
  } else {
    bulkBar.style.display = 'none';
  }
}

function submitBulkAction(action) {
  const selected = document.querySelectorAll('.order-checkbox:checked');
  const ids = Array.from(selected).map(cb => cb.value);
  if (ids.length === 0) return;

  const confirmMsg = action === 'approve'
    ? `Approve ${ids.length} orders and create them in Fortnox?`
    : `Deny ${ids.length} orders?`;

  if (!confirm(confirmMsg)) return;

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `/orders/${action}`;

  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'order_ids';
  input.value = ids.join(',');
  form.appendChild(input);

  document.body.appendChild(form);
  form.submit();
}
```

---

### `app/templates/order_detail.html`

Full order view with editing capability.

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  ← Back to Orders                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Order: C12345-2026-02-20        [pending]          │
│  Customer: Foretag AB (#100)                        │
│  Contract: #12345                                   │
│                                                     │
│  ── Order Details ──────────────────────────────── │
│                                                     │
│  Delivery Date: [2026-02-20    ]                    │
│  Period Start:  [2026-05-20    ]                    │
│  Admin Fee:     [150           ] SEK                │
│  Freight:       [499           ] SEK                │
│  Remarks:       [Leverans varannan manad         ]  │
│                                                     │
│  ── Line Items ─────────────────────────────────── │
│                                                     │
│  Article    │ Description │ Qty │ Price  │ VAT │    │
│  ───────────┼─────────────┼─────┼────────┼─────┼── │
│  MENS-001   │ Mensskydd   │ [3] │ [150]  │ 25% │ ✗ │
│  TVAT-002   │ Tvattlapp   │ [5] │ [80]   │ 25% │ ✗ │
│                                                     │
│  [+ Add Row]                                        │
│                                                     │
│  Total: 4,850 SEK                                   │
│                                                     │
│  [Save Changes]  [Approve]  [Deny]                  │
│                                                     │
│  ── Audit Log ──────────────────────────────────── │
│  2026-02-13 08:00 - Generated by A1 workflow        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Editable fields:**
- All order-level fields (delivery_date, period_start, administration_fee, freight, remarks)
- Each line item row: ArticleNumber, Description, DeliveredQuantity, Price, VAT, Unit
- Remove row button (✗) per row
- "Add Row" button adds empty row

**JavaScript for line items:**

```javascript
// Add new row
function addRow() {
  const tbody = document.getElementById('order-rows');
  const rowIndex = tbody.children.length;
  const row = document.createElement('tr');
  row.innerHTML = `
    <td><input name="rows[${rowIndex}][ArticleNumber]" value="" /></td>
    <td><input name="rows[${rowIndex}][Description]" value="" /></td>
    <td><input name="rows[${rowIndex}][DeliveredQuantity]" type="number" value="1" /></td>
    <td><input name="rows[${rowIndex}][Price]" type="number" step="0.01" value="0" /></td>
    <td><input name="rows[${rowIndex}][VAT]" type="number" value="25" /></td>
    <td><input name="rows[${rowIndex}][Unit]" value="" /></td>
    <td><button type="button" onclick="removeRow(this)">✗</button></td>
  `;
  tbody.appendChild(row);
}

// Remove row
function removeRow(btn) {
  btn.closest('tr').remove();
}
```

**Form submission:**
The edit form POSTs to `/orders/{id}/edit` with all fields. The router parses line items from form data and rebuilds `order_payload.Order.OrderRows`.

---

## Files to Modify

### `app/routers/__init__.py`

Add orders router:

```python
# API Routers
from . import webhooks, dashboard, internal, docs, orders
```

### `app/main.py`

Mount the orders router (add after line 86):

```python
from .routers import webhooks, dashboard, internal, docs, orders

# ... existing router includes ...
app.include_router(orders.router, tags=["orders"])
```

### `app/templates/index.html` (and all other templates)

Add "Orders" to the navigation bar:

```html
<nav>
    <a href="/">Dashboard</a>
    <a href="/orders">Orders</a>  <!-- NEW -->
    <a href="/automations">Automations</a>
    <a href="/settings">Settings</a>
    <a href="/logs">Logs</a>
    <a href="/docs">Docs</a>
    <a href="/logout">Logout</a>
</nav>
```

Update in all templates: `index.html`, `logs.html`, `log_detail.html`, `settings.html`, `docs.html`, `doc_view.html`.

---

## Verification

1. Start app locally with test data in DB (from Phase 2 verification)
2. Navigate to `/orders` — should see the orders table
3. Click an order — should see detail page with editable fields
4. Edit remarks and a line item quantity — save — verify `order_payload` updated in DB
5. Add a new row — save — verify row appears in `order_payload.Order.OrderRows`
6. Remove a row — save — verify row gone from payload
7. Check that `/` (main dashboard) still works with the new nav link
8. Check that `/orders?tab=new` shows placeholder (empty or "Coming soon" message)
9. Check status filter: `?status=all` shows all orders
