# Phase 6: Integration Testing

**Depends on:** All previous phases (1-5)
**Estimated effort:** 1-2 hours
**Output:** Verified end-to-end system, production-ready

---

## Objective

Validate the complete order approval flow end-to-end: from A1 generating orders through to Fortnox order creation. Ensure existing functionality is not broken.

---

## End-to-End Test Sequence

### Test 1: A1 Generates Pending Orders

**Steps:**
1. Ensure A1 workflow has DEBUG NODE limit set to 2
2. Ensure `RAILWAY_WEBHOOK_URL` environment variable is set in n8n
3. Run A1 workflow manually via n8n UI
4. Check n8n execution log — all nodes should complete green

**Verify:**
- [ ] "GET Previous Order" node executed (may return empty for first run)
- [ ] "Enrich & Format Order" node output includes: `administration_fee`, `freight`, `remarks`, `period_start`, `order_date` = `delivery_date`
- [ ] "POST to FastAPI" node returned 200 with `{"status": "received", "stored": N}`
- [ ] "Format Notification" includes "Pending Review" text
- [ ] Database: `pending_orders` table has N new rows with `status='pending'`

### Test 2: Dashboard Displays Orders

**Steps:**
1. Navigate to `https://<railway-url>/login` → enter password
2. Click "Orders" in navigation bar
3. Check the Recurring Orders tab

**Verify:**
- [ ] Orders from Test 1 appear in the table
- [ ] Customer name, items, delivery date, admin fee, freight, total are correct
- [ ] Status shows "pending" badge (amber/yellow)
- [ ] "New Orders" tab shows placeholder/empty state
- [ ] Stats bar shows correct pending count and total value

### Test 3: Order Detail & Editing

**Steps:**
1. Click "View" on one of the pending orders
2. Change the Remarks field
3. Change the Freight value
4. Add a new line item row
5. Click "Save Changes"
6. Reload the page

**Verify:**
- [ ] All edited fields are persisted
- [ ] `order_payload` in database reflects the changes
- [ ] New line item appears in OrderRows within `order_payload`
- [ ] Total amount recalculated correctly
- [ ] Audit log shows "edited" entry

### Test 4: Single Order Approval

**Steps:**
1. From the order detail page, click "Approve"
2. Wait for the page to redirect

**Verify:**
- [ ] Order status changed to "created" in database
- [ ] `fortnox_order_number` is set
- [ ] Order appears in Fortnox as a draft order
- [ ] Draft order in Fortnox has correct: CustomerNumber, OrderRows, DeliveryDate, AdministrationFee, Freight, Remarks
- [ ] Audit log shows "created" entry with `fortnox_order_number`

### Test 5: Bulk Approval

**Steps:**
1. Go back to `/orders`
2. Check the checkboxes for 2+ pending orders
3. Click "Approve X selected"
4. Confirm the dialog

**Verify:**
- [ ] All selected orders have status "created"
- [ ] Each has a unique `fortnox_order_number`
- [ ] All orders appear in Fortnox
- [ ] Results message shows correct count

### Test 6: Order Denial

**Steps:**
1. From `/orders`, check one pending order
2. Click "Deny 1 selected"
3. Confirm

**Verify:**
- [ ] Order status is "denied"
- [ ] `reviewed_at` is set
- [ ] Order does NOT appear in Fortnox
- [ ] Audit log shows "denied" entry
- [ ] Denied order appears in "All" status filter but not "Pending"

### Test 7: Duplicate Prevention

**Steps:**
1. Run A1 workflow again (with same DEBUG limit=2)
2. Check the webhook response

**Verify:**
- [ ] Response shows `"duplicates_skipped": N` (matching previously stored orders)
- [ ] No duplicate rows in `pending_orders` table
- [ ] `your_order_number` UNIQUE constraint enforced

### Test 8: Error Handling

**Steps:**
1. Temporarily modify a pending order's `order_payload` to have an invalid `CustomerNumber` (e.g., "INVALID")
2. Try to approve it

**Verify:**
- [ ] Order status is "failed"
- [ ] `error_message` contains Fortnox error details
- [ ] Other orders in bulk approve still process correctly (independent processing)
- [ ] Failed order can be edited and re-approved

### Test 9: Existing Dashboard Unchanged

**Steps:**
1. Navigate to `/` (main dashboard)
2. Navigate to `/logs`
3. Navigate to `/settings`
4. Navigate to `/automations`

**Verify:**
- [ ] All pages load correctly
- [ ] "Orders" link appears in navigation on all pages
- [ ] No errors in browser console
- [ ] Execution logs still display correctly

---

## Edge Cases Checklist

| # | Scenario | Expected Behavior |
|---|----------|------------------|
| 1 | A1 runs but no contracts are due | No orders posted to webhook, no DB rows |
| 2 | Contract has no InvoiceRows | Order created with empty OrderRows (valid but worth flagging) |
| 3 | Contract has no previous order (first time) | Remarks = empty string |
| 4 | Contract InvoiceInterval is 0 or null | Default to 3 months |
| 5 | Contract AdministrationFee is null | Default to 0 |
| 6 | Contract Freight is null | Default to 0 |
| 7 | Very long item_summary (many products) | Truncated in table, full in detail |
| 8 | Fortnox OAuth token expired during bulk approve | n8n auto-refreshes; at most 1 order delayed |
| 9 | Fortnox rate limit hit during bulk approve | n8n retries; 300ms delay between orders |
| 10 | Rebecca edits order then approves | Edited payload sent to Fortnox |
| 11 | Railway app restarts during approval | Only the in-flight order may fail; rest are unaffected |
| 12 | n8n webhook is unreachable | Order marked as 'failed' with connection error |

---

## Production Readiness Checklist

Before going live:

- [ ] Remove or increase DEBUG NODE limit (or remove the node entirely)
- [ ] Set `RAILWAY_WEBHOOK_URL` in n8n environment variables
- [ ] Set `N8N_CREATE_ORDER_WEBHOOK` in Railway environment variables
- [ ] Activate the A1 workflow schedule (currently inactive)
- [ ] Activate the Order Creator webhook workflow
- [ ] Configure Slack webhook URL in "Send Notification" node
- [ ] Test with Rebecca: walkthrough of approve/deny/edit flow
- [ ] Confirm Fortnox order format is correct with Nils/Rebecca
- [ ] Document the dashboard URL and login for Rebecca

---

## Monitoring

After go-live, monitor:

1. **n8n executions:** Check A1 runs daily at 08:00 without errors
2. **Pending orders:** Dashboard should show new orders each morning
3. **Fortnox orders:** Verify approved orders appear correctly
4. **Error rate:** Check for failed orders in the dashboard
5. **Railway logs:** `uvicorn` output for webhook errors
