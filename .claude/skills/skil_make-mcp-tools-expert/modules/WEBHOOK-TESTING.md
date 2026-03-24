# Webhook Testing (Local)

Test any Make.com webhook-triggered scenario from the local machine using `curl`. Zero Make resources consumed beyond the scenario execution itself.

---

## Basic Pattern

```bash
curl -s -X POST "{WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d '{TEST_PAYLOAD}'
```

The webhook URL is found via `hooks_list` (teamId) → match by `url` field.

---

## When to Use

- **First integration test** — verify a new scenario processes data correctly
- **After blueprint changes** — confirm fixes work without user filling forms
- **Testing edge cases** — missing fields, unusual values, boundary conditions
- **Both priority routes** — send payloads that trigger different router paths

---

## Standard Test Payloads

### Enquiry Form (Meji Media pattern)

**Standard priority:**
```json
{
  "name": "Test User",
  "email": "neumanic2@gmail.com",
  "phone": "+49123456789",
  "event_type": "Wedding",
  "event_date": "2026-06-15",
  "event_value": "3000",
  "message": "Automated test - standard priority",
  "source": "webhook_test"
}
```

**High priority (event_value > 5000):**
```json
{
  "name": "High Value Client",
  "email": "neumanic2@gmail.com",
  "phone": "+49987654321",
  "event_type": "Corporate Gala",
  "event_date": "2026-09-20",
  "event_value": "8000",
  "message": "Automated test - HIGH priority route",
  "source": "webhook_test"
}
```

**Missing fields (edge case):**
```json
{
  "name": "Minimal Test",
  "email": "neumanic2@gmail.com"
}
```

---

## Verifying Results

After sending a test payload:

1. **Check execution status:**
   ```
   executions_list(scenarioId) → look at latest execution
   - status: 1 = success
   - status: 3 = error (check error.message)
   ```

2. **If success:** Check the scenario's output (sheet data, email sent, etc.)
3. **If error:** Read the error message, fix the blueprint, re-test

---

## Important Notes

- The scenario must be **activated** for webhook triggers to work
- `curl` sends raw JSON — field names must match the blueprint's `1.body.*` references
- When integrating with external forms (Tally, Typeform, etc.), first test with clean JSON to verify the blueprint works, THEN map form-specific field names
- **Always use your own email** for test payloads to avoid sending to real contacts
- Test payloads with `"source": "webhook_test"` are easy to identify and clean up later

---

## Adapting for Other Form Providers

When a form provider (Tally, Typeform, website form) sends different field names:

1. **Check known formats first** — see the `webhook-inspector` skill → KNOWN-PROVIDERS.md
2. Send clean JSON via curl to verify the blueprint works with expected field names
3. If clean JSON works → the issue is form field naming, not the blueprint
4. **Discover the form's actual payload** — use `webhook-inspector` skill → CAPTURE-PATTERN.md, or check the provider's docs
5. Update the blueprint mapper to reference the form's actual field structure
6. Re-test with curl using the form's payload format to confirm

---

## Form Provider Test Payloads

When testing a scenario that receives data from a specific form provider, use these payload templates to simulate real submissions.

### Tally Format

Tally sends a nested `data.fields[]` array. The blueprint must use `first(map(...))` to extract values.

**Standard priority (Tally format):**
```json
{
  "eventId": "test-001",
  "eventType": "FORM_RESPONSE",
  "createdAt": "2026-02-25T12:00:00.000Z",
  "data": {
    "responseId": "test-resp-001",
    "submissionId": "test-sub-001",
    "formId": "test-form",
    "formName": "Enquiry Form",
    "createdAt": "2026-02-25T12:00:00.000Z",
    "fields": [
      { "key": "q_name", "label": "Name", "type": "INPUT_TEXT", "value": "Test User" },
      { "key": "q_email", "label": "Email", "type": "INPUT_EMAIL", "value": "neumanic2@gmail.com" },
      { "key": "q_phone", "label": "Phone", "type": "INPUT_PHONE_NUMBER", "value": "+49123456789" },
      { "key": "q_event_type", "label": "Event Type", "type": "INPUT_TEXT", "value": "Wedding" },
      { "key": "q_event_date", "label": "Event Date", "type": "INPUT_DATE", "value": "2026-06-15" },
      { "key": "q_budget", "label": "Budget", "type": "INPUT_NUMBER", "value": 3000 },
      { "key": "q_message", "label": "Message", "type": "TEXTAREA", "value": "Automated test - Tally format - standard priority" }
    ]
  }
}
```

**High priority (Tally format, budget > 5000):**
```json
{
  "eventId": "test-002",
  "eventType": "FORM_RESPONSE",
  "createdAt": "2026-02-25T12:00:00.000Z",
  "data": {
    "responseId": "test-resp-002",
    "submissionId": "test-sub-002",
    "formId": "test-form",
    "formName": "Enquiry Form",
    "createdAt": "2026-02-25T12:00:00.000Z",
    "fields": [
      { "key": "q_name", "label": "Name", "type": "INPUT_TEXT", "value": "High Value Client" },
      { "key": "q_email", "label": "Email", "type": "INPUT_EMAIL", "value": "neumanic2@gmail.com" },
      { "key": "q_phone", "label": "Phone", "type": "INPUT_PHONE_NUMBER", "value": "+49987654321" },
      { "key": "q_event_type", "label": "Event Type", "type": "INPUT_TEXT", "value": "Corporate Gala" },
      { "key": "q_event_date", "label": "Event Date", "type": "INPUT_DATE", "value": "2026-09-20" },
      { "key": "q_budget", "label": "Budget", "type": "INPUT_NUMBER", "value": 8000 },
      { "key": "q_message", "label": "Message", "type": "TEXTAREA", "value": "Automated test - Tally format - HIGH priority" }
    ]
  }
}
```

**Note:** The `label` values in these templates are placeholders. Replace them with the actual field labels from the client's Tally form. Use the `webhook-inspector` skill to discover exact labels if unknown.

### Typeform Format

Typeform sends a nested `form_response.answers[]` array.

```json
{
  "event_id": "test-001",
  "event_type": "form_response",
  "form_response": {
    "form_id": "test-form",
    "token": "test-token-001",
    "submitted_at": "2026-02-25T12:00:00Z",
    "answers": [
      { "field": { "id": "field_1", "type": "short_text" }, "type": "text", "text": "Test User" },
      { "field": { "id": "field_2", "type": "email" }, "type": "email", "email": "neumanic2@gmail.com" },
      { "field": { "id": "field_3", "type": "number" }, "type": "number", "number": 3000 }
    ]
  }
}
```
