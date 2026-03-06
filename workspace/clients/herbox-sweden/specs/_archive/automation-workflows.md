# Herbox Sweden - Automation Workflows

Specifications for Herbox Sweden automations. This document is the source of truth.

---

## A1: Recurring Order Generator

**Status:** Planned
**Trigger:** Daily CRON at 08:00 CET
**Systems:** Fortnox

### Problem
Rebecca spends 60% of her time manually checking due dates and creating orders.

### Solution
Auto-generate draft orders for contracts due within 7 days.

### Flow
1. Fetch active contracts from Fortnox
2. Filter contracts due within 7 days
3. Create draft orders for each due contract
4. Notify via dashboard/Slack

### Acceptance Criteria
- [ ] Draft orders created correctly
- [ ] No duplicate orders for same contract
- [ ] Dashboard shows created orders

---

## A2: CRM-to-ERP Sync

**Status:** Planned
**Trigger:** Webhook from Upsales (deal closed)
**Systems:** Upsales, Fortnox

### Problem
Manual data entry from CRM to ERP when deals close.

### Solution
Auto-create Fortnox customer when Upsales deal closes.

### Flow
1. Receive webhook from Upsales (deal status = closed)
2. Fetch company details from Upsales
3. Check if customer exists in Fortnox
4. Create customer in Fortnox if new
5. Log sync result

### Acceptance Criteria
- [ ] Customer created with correct fields
- [ ] No duplicate customers
- [ ] Handles existing customers gracefully

---

## A3: Order Field Enrichment

**Status:** Planned
**Trigger:** Webhook from Upsales (order updated)
**Systems:** Upsales, Fortnox

### Problem
Missing information on Fortnox orders that exists in Upsales.

### Solution
Detect when Upsales deal gets order number, enrich Fortnox order.

### Flow
1. Receive webhook from Upsales
2. Extract order number from deal
3. Fetch additional data from Upsales deal
4. Update Fortnox order with enriched fields

### Acceptance Criteria
- [ ] Fields updated correctly
- [ ] No data overwritten incorrectly

---

## A4: Subscription Agreement Creator

**Status:** Planned
**Trigger:** Webhook from Fortnox (invoice created)
**Systems:** Fortnox

### Problem
Manual creation of subscription agreements for recurring customers.

### Solution
Auto-create subscription agreement when first invoice is created.

### Flow
1. Receive webhook from Fortnox (invoice created)
2. Check if subscription agreement already exists
3. Create agreement based on invoice terms
4. Log creation

### Acceptance Criteria
- [ ] Agreement created with correct terms
- [ ] No duplicate agreements

---

## A5: Reporting Sync

**Status:** Planned
**Trigger:** Hourly CRON
**Systems:** Fortnox, Google Sheets

### Problem
Manual data export for reporting.

### Solution
Sync key metrics to Google Sheets automatically.

### Flow
1. Fetch metrics from Fortnox
2. Update Google Sheet with current data
3. Log sync result

### Acceptance Criteria
- [ ] Data synced correctly
- [ ] Sheet formatted properly
