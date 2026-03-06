# Known Webhook Provider Payload Formats

Pre-documented structures for common webhook sources. Check here BEFORE using the capture pattern — if the provider is listed, you already know the structure.

---

## Tally (Form Provider)

**Payload structure:**
```json
{
  "eventId": "a4cb511e-...",
  "eventType": "FORM_RESPONSE",
  "createdAt": "2023-06-28T15:00:21.889Z",
  "data": {
    "responseId": "2wgx4n",
    "submissionId": "2wgx4n",
    "respondentId": "dwQKYm",
    "formId": "VwbNEw",
    "formName": "Contact Form",
    "createdAt": "2023-06-28T15:00:21.000Z",
    "fields": [
      {
        "key": "question_3EKz4n",
        "label": "Your Name",
        "type": "INPUT_TEXT",
        "value": "John Doe"
      },
      {
        "key": "question_w4Q4Xn",
        "label": "Email",
        "type": "INPUT_EMAIL",
        "value": "john@example.com"
      },
      {
        "key": "question_3qL4Gm",
        "label": "Service Type",
        "type": "MULTIPLE_CHOICE",
        "value": ["option-id-1"],
        "options": [
          { "id": "option-id-1", "text": "Wedding" },
          { "id": "option-id-2", "text": "Corporate" }
        ]
      }
    ]
  }
}
```

**Key characteristics:**
- All form data is in `data.fields[]` array
- Each field has `key` (unique ID), `label` (human-readable), `type`, and `value`
- Multiple choice fields have `value` as array of option IDs + `options` array for text lookup
- Hidden fields have `type: "HIDDEN_FIELDS"`
- File uploads have `value` as array of `{id, name, url}` objects

**Mapper pattern:**
```
{{first(map(1.body.data.fields; "value"; "label"; "Your Name"))}}
```

**Field types:** `INPUT_TEXT`, `INPUT_EMAIL`, `INPUT_PHONE_NUMBER`, `INPUT_NUMBER`, `INPUT_DATE`, `INPUT_LINK`, `TEXTAREA`, `MULTIPLE_CHOICE`, `DROPDOWN`, `CHECKBOXES`, `LINEAR_SCALE`, `FILE_UPLOAD`, `HIDDEN_FIELDS`, `CALCULATED_FIELDS`

**Docs:** https://tally.so/help/webhooks

---

## Typeform (Form Provider)

**Payload structure:**
```json
{
  "event_id": "abc123",
  "event_type": "form_response",
  "form_response": {
    "form_id": "xyz789",
    "token": "unique-token",
    "submitted_at": "2023-06-28T15:00:21Z",
    "definition": {
      "fields": [
        { "id": "field_1", "title": "Your Name", "type": "short_text" }
      ]
    },
    "answers": [
      {
        "field": { "id": "field_1", "type": "short_text" },
        "type": "text",
        "text": "John Doe"
      },
      {
        "field": { "id": "field_2", "type": "email" },
        "type": "email",
        "email": "john@example.com"
      }
    ]
  }
}
```

**Key characteristics:**
- Form data is in `form_response.answers[]` array
- Each answer has a `field` reference (ID + type) and a typed value property (`text`, `email`, `number`, etc.)
- Field definitions are in `form_response.definition.fields[]`
- Value property name varies by type: `text`, `email`, `number`, `boolean`, `choice.label`, `date`

**Mapper pattern:**
```
{{first(map(1.body.form_response.answers; "text"; "field.id"; "field_1"))}}
```

**Docs:** https://www.typeform.com/developers/webhooks/

---

## Stripe (Payment Provider)

**Payload structure:**
```json
{
  "id": "evt_123",
  "object": "event",
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_123",
      "amount": 5000,
      "currency": "usd",
      "customer": "cus_123",
      "metadata": { "order_id": "ORD-456" }
    }
  }
}
```

**Key characteristics:**
- Event type is in `type` field (use for routing)
- Actual data is in `data.object` (deeply nested)
- Amount is in smallest currency unit (cents for USD)
- Metadata is a flat key-value object

**Mapper pattern:**
```
{{1.body.data.object.amount}}
{{1.body.data.object.metadata.order_id}}
```

**Docs:** https://docs.stripe.com/webhooks

---

## HubSpot (CRM)

**Payload structure:**
```json
[
  {
    "eventId": 123,
    "subscriptionType": "contact.creation",
    "objectId": 456,
    "propertyName": "email",
    "propertyValue": "john@example.com",
    "occurredAt": 1672531200000
  }
]
```

**Key characteristics:**
- Payload is an ARRAY (not object) — multiple events per webhook
- Each event has limited data — use `objectId` to fetch full record via API
- `subscriptionType` defines the event type
- Timestamps are Unix milliseconds

**Mapper pattern:**
- Use an Iterator to process the array
- Typically need a follow-up HTTP module to fetch full object data from HubSpot API

---

## Google Forms (via Apps Script webhook)

**Payload structure (when using Apps Script to forward):**
```json
{
  "timestamp": "2023-06-28T15:00:21.000Z",
  "email": "john@example.com",
  "Your Name": "John Doe",
  "Phone Number": "123456"
}
```

**Key characteristics:**
- FLAT structure — field labels are top-level keys
- Depends on how the Apps Script is configured
- Native Google Forms doesn't have webhooks — requires Apps Script

**Mapper pattern:**
```
{{1.body["Your Name"]}}
{{1.body.email}}
```

---

## When Provider is Not Listed

If the webhook source isn't documented here:
1. Use the [CAPTURE-PATTERN](CAPTURE-PATTERN.md) to capture a real payload
2. Analyze it using [ANALYZE-PAYLOAD](ANALYZE-PAYLOAD.md)
3. **Add the provider to this file** after discovering its structure — this grows the knowledge base for future integrations
