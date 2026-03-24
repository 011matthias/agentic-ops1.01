# Webhook Payload Inspector

Automatically discovers the actual webhook payload structure from a live form submission. Eliminates the #1 friction point: specs assuming one payload format while the real form sends another.

## When to Use

- After creating a webhook-triggered scenario and the form provider is connected
- When you suspect payload structure mismatch (e.g., form sends nested data, blueprint expects flat)
- Before writing IML expressions that reference webhook fields
- After switching form providers (Tally → Typeform → custom)

## Prerequisites

- Webhook exists and is connected to a scenario (`hooks_list` → find webhook)
- Scenario is activated (`scenarios_activate`)
- At least 1 real form submission has been sent (or user can submit a test)

## Procedure

### Step 1: Trigger a Test Submission

If no submission has been received yet:
1. Ask the user to submit a test form, OR
2. If the webhook URL is known and you have a test payload, POST it via curl:
   ```bash
   curl -s -X POST "{WEBHOOK_URL}" -H "Content-Type: application/json" -d '{...}'
   ```
3. Wait 5-10 seconds for the execution to complete

### Step 2: Capture Execution Data

```
1. executions_list(scenarioId, limit: 1) → get latest execution
2. executions_get_detail(executionId) → inspect module 1 (webhook) output
```

**Note:** `executions_get_detail` may not expose the raw webhook body for successful executions (Make.com API limitation). If not available:

**Fallback approach — Determine Data Structure:**
1. Check `hooks_get(hookId)` → look for `data` or `parameters` fields
2. If the scenario uses `gateway:CustomWebHook`:
   - Check the hook's `udt` (User Data Type) value
   - `udt: 1` → data at `{{1.body.*}}` (custom data structure defined)
   - `udt: 0` or missing → data at `{{1.*}}` (direct webhook body)
3. If you have access to the form provider's docs:
   - Check `webhook-inspector` skill → KNOWN-PROVIDERS.md for pre-documented formats
   - Tally: `data.fields[]` array with `{key, label, type, value}` objects
   - Typeform: `form_response.answers[]` array
   - JotForm: flat `{fieldN: value}` structure
   - Generic HTML form: flat `{field_name: value}` structure

### Step 3: Generate IML Field-Access Cheat Sheet

Based on the discovered payload structure, generate a mapping table:

```markdown
## Webhook Payload: {FormProvider} → Scenario {ScenarioName}

| Field Name | Type | IML Expression |
|-----------|------|----------------|
| Name | string | `{{first(map(1.data.fields; "value"; "label"; "What's your name?"))}}` |
| Email | email | `{{first(map(1.data.fields; "value"; "label"; "Email"))}}` |
| ... | ... | ... |
```

### For Flat Payloads (direct field access):
```
| Field | IML Expression |
|-------|----------------|
| name | `{{1.name}}` |
| email | `{{1.email}}` |
```

### For Tally `data.fields[]`:
```
| Field | Label (from Tally) | IML Expression |
|-------|-------------------|----------------|
| Name | "What's your name?" | `{{first(map(1.data.fields; "value"; "label"; "What's your name?"))}}` |
| Email | "Email address" | `{{first(map(1.data.fields; "value"; "label"; "Email address"))}}` |
```

**Important:** The `label` parameter in `first(map(...))` must match EXACTLY what the form provider sends — including capitalization, punctuation, and spaces.

### For Typeform `form_response.answers[]`:
```
| Field | Field ID | IML Expression |
|-------|---------|----------------|
| Name | field_1 | `{{first(map(1.form_response.answers; "text"; "field.id"; "field_1"))}}` |
| Email | field_2 | `{{first(map(1.form_response.answers; "email"; "field.id"; "field_2"))}}` |
```

### Step 4: Update Client Context

Save the cheat sheet to: `workspace/clients/{client}/context/webhook-payload-map.md`

This becomes the single source of truth for how webhook fields are accessed in IML expressions.

### Step 5: Update Spec (if exists)

If the automation spec references webhook fields, update it with the actual payload structure:
- Add a "Webhook Payload Format" section with the cheat sheet
- Flag any field names in the spec that don't match the actual payload

## Common Gotchas

1. **Tally label changes break everything** — If the client renames a form field in Tally, the `label` parameter in `first(map(...))` stops matching. Document this risk in client handover docs.
2. **Date fields come as strings** — Tally sends dates as `"2026-06-15"` (ISO 8601 string), not a Date object. Use `parseDate()` if date math is needed.
3. **Number fields may come as strings** — Budget/value fields from form providers may be strings. Use `toNumber()` for arithmetic.
4. **Empty optional fields** — Optional form fields may be `null`, empty string, or omitted entirely. Use `ifempty()` for safe access.
