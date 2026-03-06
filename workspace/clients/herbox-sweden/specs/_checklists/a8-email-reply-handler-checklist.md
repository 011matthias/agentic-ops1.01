# Testing Checklist: Email Reply Handler

**Automation ID:** a8_email_reply_handler
**Client:** herbox
**Generated:** 2026-01-15

---

## Pre-Test Setup

### Environment Variables

Set these in your local `.env` or Railway:

| Variable | Required | Description |
|----------|----------|-------------|
| `AIRTABLE_TOKEN` | Yes | Airtable API access token |
| `AIRTABLE_BASE_ID` | Yes | Base ID: apppGZKPtSKo2H41f |
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI categorization & phone extraction |
| `SMARTLEAD_WEBHOOK_SECRET` | Yes | Secret to validate Smartlead webhooks |
| `HERBOX_DOMAINS` | No | Internal domains (default: herbox.se,herbox.com) |
| `HEYREACH_API_KEY` | No | Heyreach API for LinkedIn campaigns |
| `HEYREACH_CAMPAIGN_PATRICK` | No | Patrick's LinkedIn campaign ID |
| `HEYREACH_CAMPAIGN_KOEN` | No | Koen's LinkedIn campaign ID |

- [ ] All environment variables configured

### Test Data

Prepare test data in Smartlead/Airtable:

- [ ] Test contact in Airtable Contacts table (tblsI8jeqv1B16MTk)
  - [ ] Contact with email: test@example.com
  - [ ] Contact with LinkedIn URL populated
  - [ ] Contact without LinkedIn URL
- [ ] Smartlead test campaign
  - [ ] Campaign ID for testing
  - [ ] Test lead email address
- [ ] Prepare test webhook payloads
  - [ ] EMAIL_REPLY payload (interested response)
  - [ ] EMAIL_REPLY payload (out of office)
  - [ ] EMAIL_REPLY payload (from internal @herbox.se email)
  - [ ] EMAIL_BOUNCE payload

### Dependencies

```bash
cd clients/herbox-sweden/automations
uv sync
```

- [ ] Dependencies installed

---

## Local Testing (Unit Tests)

```bash
cd clients/herbox-sweden/automations
uv run pytest tests/test_email_reply_handler.py -v
```

**Expected output:**
```
18 passed in ~0.6s
```

- [ ] All 18 unit tests pass
- [ ] No import errors
- [ ] Test coverage report looks good

**Test scenarios covered:**
- [ ] Webhook payload parsing
- [ ] Internal email filtering (@herbox.se, @herbox.com)
- [ ] AI categorization (Interested, Not Interested, OOO, etc.)
- [ ] Phone extraction with Herbox filtering
- [ ] Email reply full flow
- [ ] Email bounce with LinkedIn fallback
- [ ] Edge cases (empty reply, single name, missing contact)
- [ ] Acceptance criteria

---

## Local Testing (Webhook Simulation)

Since this is a webhook-triggered automation, test by sending simulated webhooks:

### 1. Start the FastAPI server locally

```bash
cd clients/herbox-sweden/automations
uv run uvicorn app.main:app --reload --port 8000
```

- [ ] Server starts without errors
- [ ] Health check passes: `curl http://localhost:8000/health`

### 2. Test EMAIL_REPLY webhook

```bash
curl -X POST http://localhost:8000/webhooks/smartlead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_TEST_SECRET" \
  -d '{
    "body": {
      "event_type": "EMAIL_REPLY",
      "campaign_id": "test_campaign",
      "campaign_status": "active",
      "from_email": "john.doe@example.com",
      "to_email": "patrick@herbox.se",
      "to_name": "Bosma Patrick",
      "subject": "Re: Partnership",
      "sent_message": {"text": "Hi, would you be interested?"},
      "reply_message": {
        "text": "Yes, I am interested! Please send pricing.",
        "time": "2026-01-15T10:30:00Z"
      },
      "sequence_number": 1,
      "sl_lead_email": "john.doe@example.com"
    }
  }'
```

**Expected behavior:**
- [ ] Returns 200 OK with `{"status": "received", "event": "EMAIL_REPLY"}`
- [ ] Check logs: "Received Smartlead webhook: EMAIL_REPLY"
- [ ] Check Airtable: New interaction logged
- [ ] Check Airtable: Contact created/updated
- [ ] Check Airtable: Call task created (for positive reply)
- [ ] Check logs: AI categorization result

### 3. Test internal email filtering

```bash
curl -X POST http://localhost:8000/webhooks/smartlead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_TEST_SECRET" \
  -d '{
    "body": {
      "event_type": "EMAIL_REPLY",
      "from_email": "patrick@herbox.se",
      "to_email": "john@example.com",
      "reply_message": {"text": "Thanks", "time": "2026-01-15T10:30:00Z"},
      "sl_lead_email": "john@example.com"
    }
  }'
```

**Expected behavior:**
- [ ] Returns 200 OK
- [ ] Check logs: "Internal email detected, filtering out"
- [ ] No Airtable records created (filtered out)

### 4. Test EMAIL_BOUNCE webhook

```bash
curl -X POST http://localhost:8000/webhooks/smartlead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_TEST_SECRET" \
  -d '{
    "body": {
      "event_type": "EMAIL_BOUNCE",
      "campaign_id": "test_campaign",
      "from_email": "john.doe@example.com",
      "to_email": "patrick@herbox.se",
      "to_name": "Bosma Patrick",
      "sl_lead_email": "john.doe@example.com"
    }
  }'
```

**Expected behavior:**
- [ ] Returns 200 OK
- [ ] If contact has LinkedIn: Added to Heyreach campaign
- [ ] Check logs: Heyreach campaign ID used

### 5. Test webhook secret validation

```bash
# Try without secret or with wrong secret
curl -X POST http://localhost:8000/webhooks/smartlead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: WRONG_SECRET" \
  -d '{"body": {"event_type": "EMAIL_REPLY"}}'
```

**Expected behavior:**
- [ ] Returns 401 Unauthorized
- [ ] Check logs: "Smartlead webhook secret validation failed"

---

## Live Test (Sandbox/Dev Environment)

### Deploy to Railway (test project)

```bash
cd clients/herbox-sweden/automations
railway up  # Make sure you're in test project
```

- [ ] Deployment successful
- [ ] All environment variables set in Railway

### Test with real Smartlead webhook

1. **Get your Railway URL:**
```bash
railway domain
```

2. **Configure Smartlead webhook:**
   - URL: `https://your-app.railway.app/webhooks/smartlead`
   - Secret: Use `SMARTLEAD_WEBHOOK_SECRET` value
   - Events: EMAIL_REPLY, EMAIL_BOUNCE

3. **Send test email from Smartlead:**
   - Use test campaign
   - Send to your test email
   - Reply with various responses

**Verify in Airtable:**
- [ ] Contact created/updated in Contacts table
- [ ] Interaction logged in Interactions table
- [ ] Task created in Tasks table (for actionable replies)
- [ ] Phone number extracted and updated (if in signature)
- [ ] Last Replied Date updated

**Verify Dashboard:**
- [ ] Navigate to `/logs`
- [ ] See execution history with steps
- [ ] Check step outputs for categorization, phone extraction

---

## Test Suite Summary

```bash
cd clients/herbox-sweden/automations
uv run pytest tests/test_email_reply_handler.py -v --cov=app/automations/email_reply_handler --cov-report=term-missing
```

**Coverage target:**
- [ ] >80% code coverage
- [ ] All critical paths covered

---

## Deployment (Production)

### Commit Changes

```bash
git add clients/herbox-sweden/automations
git add clients/herbox-sweden/specs/automations/a8-email-reply-handler.md
git commit -m "Implement A8: Email Reply Handler

- OpenAI client for email categorization & phone extraction
- Heyreach client for LinkedIn campaign integration
- Smartlead webhook endpoint for EMAIL_REPLY/EMAIL_BOUNCE
- Internal email filtering for Herbox domains
- AI-powered response categorization
- Intelligent phone extraction
- Call task creation for actionable replies
- Tests: 18 passed"
```

- [ ] Changes committed

### Push to Railway (production)

```bash
cd clients/herbox-sweden/automations
railway up  # Or use deployer agent: /deploy herbox
```

- [ ] Deployment successful
- [ ] Environment variables set in Railway dashboard
  - Navigate to: https://railway.app/project/herbox/variables
  - Verify: `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `OPENAI_API_KEY`, `SMARTLEAD_WEBHOOK_SECRET`
  - Optional: `HERBOX_DOMAINS`, `HEYREACH_API_KEY`, `HEYREACH_CAMPAIGN_PATRICK`, `HEYREACH_CAMPAIGN_KOEN`

---

## Post-Deployment Verification

### Check Logs

```bash
cd clients/herbox-sweden/automations
railway logs --tail
```

- [ ] No error messages in logs
- [ ] Webhook endpoint responding
- [ ] OpenAI API calls successful
- [ ] Airtable API calls successful

### Configure Smartlead Webhook

1. **Get production URL:**
   - Railway dashboard → Domains
   - Copy public URL

2. **Configure in Smartlead:**
   - Navigate to Webhooks settings
   - Add webhook: `https://your-app.railway.app/webhooks/smartlead`
   - Set secret header: `X-Webhook-Secret`
   - Enable: EMAIL_REPLY, EMAIL_BOUNCE

3. **Test webhook:**
   - Use Smartlead's "Send test webhook" feature
   - Verify 200 OK response

### Verify in Systems

**Airtable:**
- [ ] Contacts table: Records being created/updated
- [ ] Interactions table: New interactions logged with full message content
- [ ] Tasks table: Call tasks created for positive replies
- [ ] Phone numbers: Populated from email signatures

**Smartlead:**
- [ ] Webhook delivery status shows success

**Dashboard:**
- [ ] Navigate to `/logs`
- [ ] See recent executions
- [ ] Step-by-step progress visible

### Monitor for 24 Hours

- [ ] Check for errors in logs
- [ ] Verify internal emails are filtered (no false positives)
- [ ] Verify phone extraction is working correctly
- [ ] Verify AI categorization is accurate
- [ ] Check Heyreach integration (if enabled)

---

## Acceptance Criteria

From spec: clients/herbox-sweden/specs/automations/a8-email-reply-handler.md

- [ ] Webhook validates Smartlead secret key (401 on mismatch)
- [ ] Internal Herbox emails are filtered out before processing
- [ ] EMAIL_REPLY creates/updates contact in Airtable
- [ ] Interaction record logged with message content
- [ ] AI categorization returns valid Smartlead category
- [ ] Phone numbers extracted intelligently (excluding Herbox contacts)
- [ ] Call tasks created for actionable replies
- [ ] EMAIL_BOUNCE routes to Heyreach when LinkedIn available
- [ ] Errors logged but don't break flow
- [ ] Dry run mode processes without side effects

---

## Edge Cases to Test

- [ ] **Empty reply message** - Should handle gracefully, categorize as "Uncategorizable"
- [ ] **Single word name** - Should parse correctly (e.g., "John" → First: "John", Last: "")
- [ ] **Contact not found** - Should create new contact automatically
- [ ] **Multiple phone numbers** - Should extract all, filter Herbox numbers
- [ ] **No phone numbers** - Should continue without error
- [ ] **OpenAI API timeout** - Should retry 3x, fall back to "Uncategorizable"
- [ ] **Airtable rate limit** - Should retry with backoff
- [ ] **Heyreach API error** - Should log error, continue (non-blocking)
- [ ] **Malformed webhook** - Should log error, return 400/500

---

## Troubleshooting

### Webhook returns 401
- Check `SMARTLEAD_WEBHOOK_SECRET` matches in both places
- Verify header name: `X-Webhook-Secret`

### Contact not created
- Check `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID`
- Verify table IDs: Contacts (tblsI8jeqv1B16MTk)
- Check logs for Airtable API errors

### AI categorization fails
- Check `OPENAI_API_KEY` is valid
- Verify model: `gpt-4o-mini` available
- Check OpenAI API quota

### Phone numbers not extracted
- Check email body contains phone numbers
- Verify prompt excludes Herbox domains
- Check logs for extraction results

### Heyreach not working
- Verify `HEYREACH_API_KEY` is set
- Check campaign IDs are correct
- Contact has LinkedIn URL populated

---

## Rollback Plan

If issues occur:

1. **Disable automation in dashboard:**
   - Navigate to `/automations`
   - Toggle "A8: Email Reply Handler" to disabled

2. **Remove webhook from Smartlead:**
   - Delete webhook configuration

3. **Revert deployment:**
   ```bash
   railway rollback
   ```

4. **Fix issue and redeploy**
