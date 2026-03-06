# Webhook Capture Pattern

Use Make.com data stores as a diagnostic buffer to capture raw webhook payloads from any external source.

---

## Prerequisites

- Make.com MCP tools available (`data-stores_create`, `scenarios_create`, `hooks_list`, `data-store-records_list`)
- Team ID for the client's Make.com organization

---

## Step 1: Create or Reuse a Diagnostic Data Store

Check if a diagnostic data store already exists:

```
data-stores_list(teamId) → look for "Webhook Inspector" or "Diagnostic Captures"
```

If none exists, create one:

```
data-stores_create({
  teamId: {TEAM_ID},
  name: "Diagnostic Captures",
  dataStructureId: null    // Flexible schema — stores any JSON
})
```

**Note the data store ID** — you'll need it for the inspector scenario.

The data store is reusable across all inspections. Don't delete it after each use — just clear old records.

---

## Step 2: Create an Inspector Scenario

Build a minimal scenario that captures the full webhook body into the data store:

```json
{
  "name": "UTIL - Webhook Inspector",
  "flow": [
    {
      "id": 1,
      "module": "gateway:CustomWebHook",
      "version": 1,
      "parameters": { "hook": null, "maxResults": 1 },
      "mapper": {},
      "metadata": { "designer": { "x": 0, "y": 0 } }
    },
    {
      "id": 2,
      "module": "datastore:addRecord",
      "version": 1,
      "parameters": { "dataStoreId": "{DATA_STORE_ID}" },
      "mapper": {
        "key": "{{formatDate(now; \"YYYYMMDD-HHmmss\")}}",
        "data": "{{toString(1.body)}}"
      },
      "metadata": { "designer": { "x": 300, "y": 0 } }
    },
    {
      "id": 3,
      "module": "gateway:WebhookRespond",
      "version": 1,
      "parameters": {},
      "mapper": {
        "status": 200,
        "body": "{\"status\": \"captured\"}",
        "headers": [{ "key": "Content-Type", "value": "application/json" }]
      },
      "metadata": { "designer": { "x": 600, "y": 0 } }
    }
  ],
  "metadata": {
    "instant": true,
    "version": 1,
    "scenario": { "roundtrips": 1, "maxErrors": 3, "autoCommit": true, "sequential": false }
  }
}
```

Deploy via MCP:

```
scenarios_create({
  teamId: {TEAM_ID},
  blueprint: {above JSON},
  scheduling: { "type": "immediately" }
})
```

Then:
1. Get the webhook URL: `hooks_list(teamId)` → find the new hook → copy URL
2. Activate: `scenarios_activate(scenarioId)`

---

## Step 3: Point the Source at the Inspector

- For forms (Tally, Typeform): Update the webhook URL in the form's settings to point at the inspector
- For APIs: Send the webhook/callback URL to the inspector endpoint
- For testing: Use `curl` with the inspector's webhook URL

---

## Step 4: Trigger the Source

- Submit the form / trigger the API event / send a test payload
- The inspector captures the full body into the data store

---

## Step 5: Read the Captured Data

```
data-store-records_list(dataStoreId) → read the captured payload
```

The `data` field contains the full stringified webhook body. Parse it to understand:
- Top-level structure (flat vs nested)
- Field names, types, and nesting depth
- Array structures (like Tally's `data.fields[]`)
- Special fields (IDs, timestamps, metadata)

See [ANALYZE-PAYLOAD.md](ANALYZE-PAYLOAD.md) for how to extract schema and build mapper expressions.

---

## Step 6: Clean Up

After capturing what you need:

1. **Deactivate the inspector:** `scenarios_deactivate(scenarioId)`
2. **Delete old records:** `data-store-records_delete(dataStoreId, key)` for each record
3. **Keep the data store** — reuse it next time
4. **Restore the webhook URL** — point the source back at the production scenario
5. **Optionally delete the inspector scenario** — or keep it for future use (deactivated)

**Important:** The inspector scenario should be prefixed with `UTIL -` to clearly distinguish it from production scenarios. Delete it when done if the client's Make account should only contain production automations.

---

## Alternative: Debug Tap on Existing Scenario

If you don't want to create a separate inspector scenario, you can add a data store module directly to the existing production scenario:

1. Get the current blueprint: `scenarios_get(scenarioId)`
2. Insert a `datastore:addRecord` module after the webhook module (before any processing)
3. Store `{{toString(1.body)}}` in the data store
4. Deploy the modified blueprint: `scenarios_update(scenarioId, blueprint)`
5. Trigger the webhook
6. Read the data store
7. **Remove the debug tap** and redeploy the original blueprint

This approach is faster but modifies the production scenario temporarily. Use it when you can't change the webhook URL (e.g., it's already registered in a third-party system).
