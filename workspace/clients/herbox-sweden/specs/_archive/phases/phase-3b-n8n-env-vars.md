# Phase 3b: Set n8n Environment Variables

**Depends on:** Phase 3 (A1 workflow modified)
**Estimated effort:** 2 minutes
**Output:** n8n workflow can reach the Railway FastAPI app

---

## Objective

Set the two environment variables the modified A1 workflow needs to POST pending orders to Railway and link to the dashboard in notifications.

---

## Variables to Set

| Variable | Value | Used By |
|----------|-------|---------|
| `RAILWAY_WEBHOOK_URL` | `https://herbox-automations-production.up.railway.app` | POST to FastAPI node — appends `/webhook/pending-orders` |
| `RAILWAY_PUBLIC_URL` | `https://herbox-automations-production.up.railway.app` | Format Notification node — links to `/orders` |

> Both are the same base URL. They're separate env vars in case the webhook and public URLs ever diverge (e.g. internal vs external).

---

## Steps

1. Open the Herbox n8n instance
2. Go to **Settings → Environment Variables**
3. Add `RAILWAY_WEBHOOK_URL` = `https://herbox-automations-production.up.railway.app`
4. Add `RAILWAY_PUBLIC_URL` = `https://herbox-automations-production.up.railway.app`
5. Save

---

## Verification

After setting the variables, test the A1 workflow manually (with DEBUG NODE limit = 2):

1. Click **Test workflow** on Schedule Trigger1
2. Check **POST to FastAPI** node output — should get `200` with `{"status": "received", "stored": N}`
3. Check **Format Notification** output — review link should show the full URL

---

## Status: Not started
