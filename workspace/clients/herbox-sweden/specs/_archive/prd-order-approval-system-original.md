# PRD: Herbox Order Approval Dashboard

**Version:** 1.0.0
**Date:** 2026-02-13
**Status:** Draft
**Owner:** Riccardo / Rebecca (Herbox)

---

## 1. Problem Statement

Rebecca (Operations Manager, Herbox) spends ~60% of her time manually checking contract due dates and creating recurring orders in Fortnox. The current A1 Recurring Order workflow auto-generates draft orders directly in Fortnox with **no review step** — Rebecca cannot inspect, edit, or reject orders before they're created.

Additionally, the current workflow is missing several fields:
- **Administration fee** and **freight** from the contract are not carried over
- **Remarks** from the previous order are lost
- **Period start** is not properly postponed by the invoice interval
- New orders from Upsales also need a similar review workflow (future)

## 2. Solution Overview

Add a **human-in-the-loop approval step** between order generation and Fortnox creation:

1. The A1 n8n workflow generates and enriches orders, then stores them in a database as "pending" (instead of creating in Fortnox)
2. Rebecca reviews pending orders in a new dashboard section within the existing Railway app
3. She can edit, approve, or deny orders individually or in bulk
4. Approved orders are automatically created in Fortnox via n8n (which holds the OAuth2 credentials)

## 3. Business Value

- **Time saved:** Rebecca no longer creates orders manually (~20 hrs/week)
- **Quality:** Orders include all required fields (admin fee, freight, remarks)
- **Control:** Human review prevents incorrect orders from being created
- **Visibility:** Dashboard provides clear overview of order pipeline

---

## 4. Architecture

```
┌─────────────────┐                          ┌──────────────────────────────────┐
│  A1 Workflow     │   POST /webhook/         │  Railway FastAPI App             │
│  (n8n, daily     │──pending-orders─────────>│                                  │
│   08:00 CET)     │                          │  Postgres DB                     │
│                  │                          │  ┌────────────────────────────┐  │
│  Enriches:       │                          │  │ pending_orders             │  │
│  - Admin fee     │                          │  │ approval_log               │  │
│  - Freight       │                          │  └────────────────────────────┘  │
│  - Remarks       │                          │                                  │
│  - Period start  │                          │  Dashboard (Jinja2)              │
└─────────────────┘                          │  /orders → review & approve      │
                                              └──────────┬───────────────────────┘
                                                         │ on approve
                                                         v
                                              ┌─────────────────┐
                                              │  Order Creator   │
                                              │  (n8n webhook)   │
                                              │  POST /3/orders  │
                                              │  to Fortnox      │
                                              └─────────────────┘
```

### Data Flow

1. **A1 (n8n, daily 08:00)** → fetches contracts → enriches order data → POSTs to FastAPI webhook → stored in Postgres as `status='pending'`
2. **Dashboard (FastAPI/Jinja2)** → reads from Postgres → Rebecca reviews orders
3. **On approve** → FastAPI calls n8n webhook → n8n creates order in Fortnox (has OAuth2 creds) → returns result → FastAPI updates DB status to `'created'`

### Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Database | Existing Railway Postgres | Already running, has SQLAlchemy setup |
| Frontend | Jinja2 templates in FastAPI | Matches existing dashboard patterns |
| Auth | Existing cookie session | `require_auth()` already works |
| Order generation | n8n workflow (modified A1) | Already has contract fetching + OAuth2 |
| Order creation | n8n webhook (new workflow) | Fortnox OAuth2 creds live in n8n |
| Hosting | Railway (existing) | No new infrastructure needed |

---

## 5. Key Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Copy Remarks from previous order of the **same contract** | Query `YourOrderNumber LIKE 'C{DocNum}-%'` to find contract-specific history |
| 2 | "New Orders" tab is a **placeholder** for now | Build the tab structure; define data source later (likely Upsales) |
| 3 | **Full editing** of orders including line items | Rebecca can modify quantities, prices, add/remove rows before approval |
| 4 | Admin Fee + Freight from **Fortnox Contract** fields | `contract.AdministrationFee` and `contract.Freight` |
| 5 | Build on **existing Railway app** | No new infrastructure; reuse Postgres, auth, templates |
| 6 | Fortnox API calls stay in **n8n** | OAuth2 token management already configured there |

---

## 6. Database Schema

### `pending_orders` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Unique identifier |
| `contract_number` | VARCHAR(50) | Fortnox Contract DocumentNumber |
| `customer_number` | VARCHAR(50) | Fortnox CustomerNumber |
| `customer_name` | VARCHAR(255) | Display name (denormalized) |
| `source` | VARCHAR(20) | `'recurring'` or `'new'` — maps to dashboard tabs |
| `order_payload` | JSON | Complete Fortnox Order body, ready to POST |
| `delivery_date` | DATE | For display and sorting |
| `order_date` | DATE | = DeliveryDate |
| `total_amount` | DECIMAL(12,2) | Sum of items + admin fee + freight |
| `currency` | VARCHAR(10) | Default 'SEK' |
| `item_count` | INTEGER | Number of order rows |
| `item_summary` | TEXT | e.g. "3x Mensskydd Tena, 2x Tvattlapp" |
| `administration_fee` | DECIMAL(12,2) | From contract AdministrationFee |
| `freight` | DECIMAL(12,2) | From contract Freight |
| `remarks` | TEXT | Copied from previous order (same contract) |
| `period_start` | DATE | Postponed by InvoiceInterval |
| `status` | VARCHAR(20) | `pending` / `approved` / `denied` / `created` / `failed` |
| `your_order_number` | VARCHAR(100) UNIQUE | `C{DocNum}-{PeriodEnd}` — duplicate prevention |
| `fortnox_order_number` | VARCHAR(50) | Set after Fortnox creation |
| `error_message` | TEXT | Set if creation fails |
| `generated_at` | TIMESTAMPTZ | When A1 generated this order |
| `reviewed_at` | TIMESTAMPTZ | When approved/denied |
| `created_at` | TIMESTAMPTZ | Row creation time |
| `updated_at` | TIMESTAMPTZ | Last modification |

### `approval_log` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Unique identifier |
| `order_id` | UUID FK | References pending_orders.id |
| `action` | VARCHAR(20) | `approved` / `denied` / `edited` / `created` / `failed` |
| `performed_by` | VARCHAR(100) | Who performed the action |
| `details` | JSON | What changed (for edits) |
| `created_at` | TIMESTAMPTZ | When action was performed |

---

## 7. User Interface

### Dashboard Navigation

Add "Orders" link to the existing header nav bar (alongside Dashboard, Automations, Settings, Logs, Docs).

### Orders Page (`/orders`)

**Layout:**
- **Stats bar:** "12 pending | 45,230 SEK total value"
- **Tabs:** [Recurring Orders (8)] [New Orders (--)] — "New Orders" is placeholder
- **Filter bar:** Status dropdown (Pending/Approved/Denied/Created/All), date range
- **Table:** Full-width with columns below
- **Bulk action bar:** Appears when checkboxes are selected

**Table Columns:**

| Column | Data | Sortable |
|--------|------|----------|
| Checkbox | — | No |
| Customer | `customer_name` + `customer_number` subtitle | Yes |
| Items | `item_summary` (truncated) | No |
| Delivery Date | `delivery_date` formatted | Yes |
| Admin Fee | `administration_fee` + " SEK" | Yes |
| Freight | `freight` + " SEK" | Yes |
| Total | `total_amount` + " SEK" | Yes |
| Remarks | `remarks` (truncated) | No |
| Status | Color-coded badge | Yes |
| Actions | View / Approve / Deny buttons | No |

**Bulk Actions:**
- Select all checkbox in header
- "Approve X selected" (green button) — requires confirmation
- "Deny X selected" (red button) — requires confirmation

### Order Detail Page (`/orders/{id}`)

**Sections:**
1. **Order header:** Customer name, contract number, delivery date, status badge
2. **Order-level fields** (editable): Remarks, Freight, Administration Fee, Delivery Date, Period Start
3. **Line items table** (editable): ArticleNumber, Description, Quantity, Price, VAT, Unit — with add/remove row buttons
4. **Action buttons:** Save Changes / Approve / Deny / Back to list
5. **Audit log:** List of all actions taken on this order (from `approval_log`)

---

## 8. API Contracts

### n8n → FastAPI: Store Pending Order

**Endpoint:** `POST /webhook/pending-orders`

**Request body:**
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
          "OrderRows": [...],
          "DeliveryDate": "2026-02-20",
          "OrderDate": "2026-02-20",
          "AdministrationFee": 150,
          "Freight": 499,
          "Remarks": "Leverans varannan manad",
          "YourOrderNumber": "C12345-2026-02-20",
          ...
        }
      },
      "delivery_date": "2026-02-20",
      "order_date": "2026-02-20",
      "total_amount": 4850.00,
      "currency": "SEK",
      "item_count": 3,
      "item_summary": "3x Mensskydd Tena, 2x Tvattlapp",
      "administration_fee": 150.00,
      "freight": 499.00,
      "remarks": "Leverans varannan manad",
      "period_start": "2026-05-20",
      "your_order_number": "C12345-2026-02-20"
    }
  ]
}
```

**Response:** `{"status": "received", "stored": 5, "duplicates_skipped": 0}`

### FastAPI → n8n: Create Fortnox Order

**Endpoint:** n8n webhook `POST /webhook/create-fortnox-order`

**Request body:**
```json
{
  "order_id": "uuid-here",
  "order_payload": {
    "Order": {
      "CustomerNumber": "100",
      "OrderRows": [...],
      ...
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "fortnox_order_number": "54321",
  "document_number": "54321"
}
```

Or on failure:
```json
{
  "success": false,
  "error": "Fortnox API returned 400: Invalid CustomerNumber"
}
```

---

## 9. n8n Workflow Changes

### Modified A1 Workflow (ID: `qJHgvXLKFdCBja1o`)

**Current end of chain:**
```
Is Not Duplicate? → Format Fortnox Order1 → [disconnected] → CREATE Fortnox Order → Format Notification → Send Notification
```

**New end of chain:**
```
Is Not Duplicate? → GET Previous Order → Enrich & Format Order → POST to FastAPI → Update Notification
```

**Nodes to add:**
1. "GET Previous Order" — HTTP Request fetching most recent order from same contract
2. "Enrich & Format Order" — Code node replacing `Format Fortnox Order1` with enrichment logic

**Nodes to replace:**
3. Replace `CREATE Fortnox Order` connection target with HTTP POST to Railway FastAPI
4. Update `Format Notification` to say "X orders pending review"

### New Order Creator Workflow

A separate n8n workflow with:
- Webhook trigger (POST `/webhook/create-fortnox-order`)
- Fortnox POST `/3/orders` using existing OAuth2 credentials
- Respond to Webhook node returning success/failure

---

## 10. Implementation Phases

| Phase | Name | Description | Depends On | Status |
|-------|------|-------------|------------|--------|
| 1 | Database | SQLAlchemy models + table creation | — | Done |
| 2 | Webhook Receiver | `/webhook/pending-orders` endpoint | Phase 1 | Done |
| 3 | Modify A1 Workflow | n8n changes to store instead of create | Phase 2 | Done |
| 4 | Dashboard | Orders page with edit/approve/deny | Phase 1 | Done |
| 5 | Order Creator | n8n webhook + FastAPI approve route | Phase 4 | Done |
| 6 | Railway Deploy | Deploy updated FastAPI app to Railway | Phase 1, 2, 4, 5 | Done |
| 7 | Testing | End-to-end validation | Phase 3, 6 | Not started |

Detailed specs for each phase are in `specs/phases/`.

---

## 11. Success Criteria

- [ ] A1 runs daily and stores pending orders in Postgres (no direct Fortnox creation)
- [ ] Orders include administration fee, freight, and remarks from previous order
- [ ] Period start is correctly postponed by invoice interval
- [ ] Dashboard shows pending orders with two tabs (Recurring + New placeholder)
- [ ] Rebecca can approve/deny individual orders
- [ ] Rebecca can bulk-approve multiple orders
- [ ] Rebecca can edit all order fields including line items before approval
- [ ] Approved orders are correctly created in Fortnox
- [ ] Duplicate orders are prevented (UNIQUE constraint on `your_order_number`)
- [ ] Existing dashboard pages (`/`, `/logs`, `/settings`) still work
- [ ] Audit log records all approval actions

---

## 12. Existing Infrastructure Reference

| File | What It Provides |
|------|-----------------|
| `app/db.py` | SQLAlchemy `Base`, `engine`, `SessionLocal`, `get_db()`, `init_db()` |
| `app/config.py` | `Settings` class with `dashboard_password`, env var loading |
| `app/auth.py` | `require_auth()` — cookie + Basic Auth check |
| `app/main.py` | FastAPI app, `lifespan()` calls `init_db()`, router mounting |
| `app/routers/dashboard.py` | Jinja2 templates, auth patterns, DB queries |
| `app/routers/webhooks.py` | Webhook patterns (Background tasks, validation) |
| `app/routers/__init__.py` | Router registration |
| `app/templates/index.html` | CSS styles, header nav, section patterns |

### n8n Workflow Structure (ID: `qJHgvXLKFdCBja1o`)

| Node Name | ID | Type | Position in Chain |
|-----------|-----|------|------------------|
| Schedule Trigger1 | `3571c1b2` | scheduleTrigger | Start |
| GET Fortnox Contracts1 | `1e4ec3bc` | httpRequest | Stage 1 |
| Extract Contracts1 | `575a125b` | code | Stage 1 |
| Filter Active & Ending in X Days | `a5be9c0d` | if | Stage 1 |
| DEBUG NODE | `a20b3c07` | limit | Stage 1 (testing) |
| GET Contract Details1 | `8506ceaf` | httpRequest | Stage 2 |
| Extract Contract Detail1 | `437ff0b1` | code | Stage 2 |
| Calculate Order Timing1 | `eaa5d32e` | code | Stage 2 |
| Should Generate Order?1 | `f4cf70c8` | if | Stage 2 |
| Check Existing Orders | `378c1688` | httpRequest | Stage 3 |
| Filter Duplicates | `4d044808` | code | Stage 3 |
| Is Not Duplicate? | `41087c8a` | if | Stage 3 |
| **Format Fortnox Order1** | `0b958555` | code | **Stage 4 (to replace)** |
| **CREATE Fortnox Order** | `203ce602` | httpRequest | **Stage 4 (to redirect)** |
| Format Notification | `6e9d99b0` | code | Stage 4 |
| Send Notification | `341a3a66` | httpRequest | Stage 4 |
