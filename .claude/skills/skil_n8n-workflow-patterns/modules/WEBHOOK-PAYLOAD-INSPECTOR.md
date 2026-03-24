# Webhook Payload Inspector (n8n)

Discover the actual payload structure from a webhook source before building expressions. n8n's execution history is directly readable — no data-store tap needed.

---

## When to Use

- Integrating a new webhook source for the first time
- Webhook data structure is undocumented or uncertain
- Expressions return undefined and you need to see the actual data shape

**Check first:** See `webhook-inspector/modules/KNOWN-PROVIDERS.md` for pre-documented formats (Tally, Typeform, Stripe, HubSpot, Google Forms). If listed, skip to the expression translation table below.

---

## Procedure

### Step 1: Create or Identify Webhook Workflow

If the workflow doesn't exist yet:
```
n8n_create_workflow({
  name: "INSPECT - {Provider} Webhook",
  nodes: [Webhook node + Respond to Webhook (200 OK)]
})
```

Activate it so the webhook URL registers:
```
n8n_update_partial_workflow({id, operations: [{type: "activateWorkflow"}]})
```

### Step 2: Send Test Request

Send a real or simulated webhook from the source system. If you can't trigger from the source:
```bash
curl -X POST https://{n8n-instance}/webhook/{path} \
  -H "Content-Type: application/json" \
  -d '{"test": "payload", "name": "Inspector Test"}'
```

### Step 3: Read Execution Data

```
n8n_executions({action: "list", workflowId: "{id}", limit: 1})
```

Get the execution ID from the result, then:

```
n8n_executions({action: "get", id: "{executionId}", mode: "full"})
```

Find the Webhook node's output in the execution data. The payload is under the Webhook node's `json` output.

### Step 4: Map the Structure

From the Webhook node output, document:
1. **Top-level keys** — what's at `$json.body.*`
2. **Nesting depth** — flat object? Nested arrays? Event envelope?
3. **Field types** — strings, numbers, arrays, objects
4. **Dynamic keys** — fields that vary per submission (e.g., form field IDs)

### Step 5: Generate Expression Map

Create a cheat sheet mapping each needed field to its n8n expression:

```markdown
## {Provider} Webhook Expressions

| Field | Expression |
|-------|-----------|
| Name | `{{$json.body.data.fields[0].value}}` |
| Email | `{{$json.body.data.fields[1].value}}` |
| Event type | `{{$json.body.type}}` |
```

### Step 6: Save to Client Context

Save the cheat sheet to `workspace/clients/{client}/context/webhook-payloads.md`. This persists across sessions and prevents re-discovery.

---

## n8n Expression Translation Table

For providers documented in `KNOWN-PROVIDERS.md`, here are the n8n `{{ }}` equivalents:

### Tally
| Field | n8n Expression |
|-------|---------------|
| Field by label | `{{$json.body.data.fields.find(f => f.label === "Your Name").value}}` |
| Field by key | `{{$json.body.data.fields.find(f => f.key === "question_3EKz4n").value}}` |
| Form name | `{{$json.body.data.formName}}` |
| Submission ID | `{{$json.body.data.submissionId}}` |
| Timestamp | `{{$json.body.createdAt}}` |

**Note:** Tally's `fields` array requires `.find()` — use a Code node if you need multiple fields (cleaner than chaining `.find()` in expressions).

### Typeform
| Field | n8n Expression |
|-------|---------------|
| Text answer | `{{$json.body.form_response.answers.find(a => a.field.id === "field_1").text}}` |
| Email answer | `{{$json.body.form_response.answers.find(a => a.field.id === "field_2").email}}` |
| Number answer | `{{$json.body.form_response.answers.find(a => a.field.id === "field_3").number}}` |
| Form ID | `{{$json.body.form_response.form_id}}` |
| Submitted at | `{{$json.body.form_response.submitted_at}}` |

### Stripe
| Field | n8n Expression |
|-------|---------------|
| Event type | `{{$json.body.type}}` |
| Amount (cents) | `{{$json.body.data.object.amount}}` |
| Currency | `{{$json.body.data.object.currency}}` |
| Customer ID | `{{$json.body.data.object.customer}}` |
| Metadata field | `{{$json.body.data.object.metadata.order_id}}` |

### HubSpot
| Field | n8n Expression |
|-------|---------------|
| Event type | `{{$json.body[0].subscriptionType}}` |
| Object ID | `{{$json.body[0].objectId}}` |
| Property name | `{{$json.body[0].propertyName}}` |
| Property value | `{{$json.body[0].propertyValue}}` |

**Note:** HubSpot sends an array — use SplitInBatches if multiple events arrive per webhook. Typically need a follow-up HTTP Request to fetch full object data from HubSpot API.

### Google Forms (via Apps Script)
| Field | n8n Expression |
|-------|---------------|
| Named field | `{{$json.body["Your Name"]}}` |
| Email | `{{$json.body.email}}` |
| Timestamp | `{{$json.body.timestamp}}` |

---

## Cleanup

After discovering the payload and building the real workflow:
- Deactivate and delete the INSPECT workflow (it's dev-only)
- Keep the cheat sheet in `context/webhook-payloads.md` — it's permanent reference
