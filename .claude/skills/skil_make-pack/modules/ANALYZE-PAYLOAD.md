# Analyzing Captured Payloads

After capturing a webhook payload using the [CAPTURE-PATTERN](CAPTURE-PATTERN.md), analyze it to build correct mapper expressions.

---

## Step 1: Read the Raw Payload

```
data-store-records_list(dataStoreId) → find the latest record → read the "data" field
```

The `data` field contains the full webhook body as a string. Parse it mentally or with tools to understand the structure.

---

## Step 2: Identify the Structure Type

### Flat (Direct Fields)
```json
{ "name": "John", "email": "john@example.com", "phone": "123456" }
```
**Mapper:** `{{1.body.name}}`, `{{1.body.email}}` — straightforward.

### Nested Object
```json
{ "data": { "contact": { "name": "John", "email": "john@example.com" } } }
```
**Mapper:** `{{1.body.data.contact.name}}`, `{{1.body.data.contact.email}}`

### Nested Array of Fields (Common for form providers)
```json
{ "data": { "fields": [ { "label": "Name", "value": "John" }, { "label": "Email", "value": "john@example.com" } ] } }
```
**Mapper:** `{{first(map(1.body.data.fields; "value"; "label"; "Name"))}}`

### Event Envelope (Common for SaaS webhooks)
```json
{ "event": "payment.completed", "data": { "id": "pay_123", "amount": 5000 } }
```
**Mapper:** `{{1.body.data.amount}}`, with `{{1.body.event}}` for routing.

---

## Step 3: Build Mapper Expressions

### For Flat Structures
```
{{1.body.fieldName}}
{{ifempty(1.body.optionalField; "default")}}
```

### For Nested Objects
```
{{1.body.path.to.field}}
{{ifempty(1.body.path.to.optionalField; "default")}}
```

### For Field Arrays (Tally, Typeform, etc.)
Use `first(map(...))` to search by label/key:
```
{{first(map(1.body.data.fields; "value"; "label"; "Field Label"))}}
```

With fallback:
```
{{ifempty(first(map(1.body.data.fields; "value"; "label"; "Field Label")); "default")}}
```

For numeric values (needed for filters/comparisons):
```
{{parseNumber(ifempty(first(map(1.body.data.fields; "value"; "label"; "Budget")); "0"); ".")}}
```

### For Multiple Choice / Dropdown Fields
Some form providers return option IDs instead of text. You may need to:
1. Get the `value` (which is an option ID)
2. Cross-reference with the `options` array to get the text

---

## Step 4: Document the Schema

After analyzing, document the mapping in the spec or blueprint file:

```
Source Field (webhook)                    → Target Field (mapper expression)
─────────────────────────────────────────────────────────────────────────
data.fields[label="Name"].value           → {{first(map(1.body.data.fields; "value"; "label"; "Name"))}}
data.fields[label="Email"].value          → {{first(map(1.body.data.fields; "value"; "label"; "Email"))}}
data.fields[label="Phone"].value          → {{first(map(1.body.data.fields; "value"; "label"; "Phone"))}}
```

This serves as a reference for future debugging and for the local blueprint file.

---

## Step 5: Verify with Curl

Before deploying to the production scenario, test the mapper expressions with a `curl` command that mimics the captured payload structure:

```bash
curl -s -X POST "{PRODUCTION_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d '{CAPTURED_PAYLOAD_STRUCTURE_WITH_TEST_DATA}'
```

This verifies the mapper will work with real data before asking the user to trigger the actual source.
