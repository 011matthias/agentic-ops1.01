# Operation Patterns Guide

Minimal valid configurations for top n8n nodes. Adapt and extend as needed.

---

## HTTP Request (nodes-base.httpRequest)

```javascript
// GET
{ "method": "GET", "url": "https://api.example.com/users", "authentication": "none" }

// GET with query params
{ "method": "GET", "url": "https://api.example.com/users", "authentication": "none",
  "sendQuery": true, "queryParameters": { "parameters": [
    { "name": "limit", "value": "100" },
    { "name": "offset", "value": "={{$json.offset}}" }
  ]} }

// GET with auth
{ "method": "GET", "url": "https://api.example.com/users",
  "authentication": "predefinedCredentialType", "nodeCredentialType": "httpHeaderAuth" }

// POST with JSON body — GOTCHA: sendBody must be true!
{ "method": "POST", "url": "https://api.example.com/users", "authentication": "none",
  "sendBody": true, "body": { "contentType": "json",
    "content": { "name": "={{$json.name}}", "email": "={{$json.email}}" } } }

// DELETE (no body)
{ "method": "DELETE", "url": "https://api.example.com/users/123", "authentication": "none" }
```

---

## Webhook (nodes-base.webhook)

```javascript
// Basic — GOTCHA: data is under $json.body, not $json!
{ "path": "my-webhook", "httpMethod": "POST", "responseMode": "onReceived" }

// With header auth
{ "path": "secure-webhook", "httpMethod": "POST", "responseMode": "onReceived",
  "authentication": "headerAuth",
  "options": { "responseCode": 200, "responseData": "{\"success\": true}" } }

// Return data from last node
{ "path": "my-webhook", "httpMethod": "POST", "responseMode": "lastNode",
  "options": { "responseCode": 201 } }
```

---

## Slack (nodes-base.slack)

```javascript
// Post message — GOTCHA: channel must start with # or be a channel ID
{ "resource": "message", "operation": "post", "channel": "#general", "text": "Hello!" }

// Dynamic content
{ "resource": "message", "operation": "post",
  "channel": "={{$json.channel}}", "text": "New user: {{$json.name}}" }

// Update message (messageId required)
{ "resource": "message", "operation": "update",
  "messageId": "1234567890.123456", "text": "Updated content" }

// Create channel — GOTCHA: name must be lowercase, no spaces, 1-80 chars
{ "resource": "channel", "operation": "create", "name": "new-project", "isPrivate": false }
```

---

## Gmail (nodes-base.gmail)

```javascript
// Send email
{ "resource": "message", "operation": "send",
  "to": "={{$json.email}}", "subject": "Order #{{$json.orderId}}",
  "message": "Dear {{$json.name}},\n\nYour order has been confirmed." }

// Get emails with filter
{ "resource": "message", "operation": "getAll", "returnAll": false, "limit": 50,
  "filters": { "q": "is:unread from:important@example.com", "labelIds": ["INBOX"] } }
```

---

## Postgres (nodes-base.postgres)

```javascript
// SELECT — GOTCHA: always use parameterized queries for user input!
{ "operation": "executeQuery",
  "query": "SELECT * FROM users WHERE email = $1 AND active = $2",
  "additionalFields": { "mode": "list", "queryParameters": "={{$json.email}},true" } }

// ❌ SQL injection risk:
//   "query": "SELECT * FROM users WHERE email = '{{$json.email}}'"
// ✅ Use $1 placeholders + queryParameters instead

// INSERT
{ "operation": "insert", "table": "users", "columns": "name,email",
  "additionalFields": { "mode": "list", "queryParameters": "={{$json.name}},={{$json.email}}" } }
```

---

## Set (nodes-base.set)

```javascript
// Fixed values — GOTCHA: use correct type per field (number, not "number")
{ "mode": "manual", "duplicateItem": false,
  "assignments": { "assignments": [
    { "name": "status", "value": "active", "type": "string" },
    { "name": "count", "value": 100, "type": "number" }
  ] } }

// From input data
{ "mode": "manual", "duplicateItem": false,
  "assignments": { "assignments": [
    { "name": "fullName", "value": "={{$json.firstName}} {{$json.lastName}}", "type": "string" },
    { "name": "timestamp", "value": "={{$now.toISO()}}", "type": "string" }
  ] } }
```

---

## Code (nodes-base.code)

```javascript
// All items — GOTCHA: use $input.item.json not {{...}} in Code nodes!
{ "mode": "runOnceForAllItems",
  "jsCode": "return $input.all().map(item => ({ json: { name: item.json.name.toUpperCase() } }));" }

// Per-item
{ "mode": "runOnceForEachItem",
  "jsCode": "const data = $input.item.json;\nreturn { json: { fullName: `${data.firstName} ${data.lastName}` } };" }
```

---

## IF (nodes-base.if)

```javascript
// String equals (binary)
{ "conditions": { "string": [
    { "value1": "={{$json.status}}", "operation": "equals", "value2": "active" }
  ] } }

// isEmpty (unary) — GOTCHA: no value2 needed, singleValue auto-added
{ "conditions": { "string": [
    { "value1": "={{$json.email}}", "operation": "isEmpty" }
  ] } }

// Number comparison
{ "conditions": { "number": [
    { "value1": "={{$json.age}}", "operation": "larger", "value2": 18 }
  ] } }

// Multiple conditions (AND)
{ "conditions": {
    "string": [{ "value1": "={{$json.status}}", "operation": "equals", "value2": "active" }],
    "number": [{ "value1": "={{$json.age}}", "operation": "larger", "value2": 18 }]
  }, "combineOperation": "all" }

// OR logic
{ "combineOperation": "any" }
```

---

## Switch (nodes-base.switch)

```javascript
// Multi-way routing — GOTCHA: number of rules must match number of outputs
{ "mode": "rules",
  "rules": { "rules": [
    { "conditions": { "string": [{ "value1": "={{$json.status}}", "operation": "equals", "value2": "active" }] } },
    { "conditions": { "string": [{ "value1": "={{$json.status}}", "operation": "equals", "value2": "pending" }] } }
  ] },
  "fallbackOutput": "extra" }
```

---

## OpenAI (nodes-langchain.openAi)

```javascript
// Chat completion with system prompt
{ "resource": "chat", "operation": "complete",
  "messages": { "values": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "={{$json.prompt}}" }
  ] },
  "options": { "temperature": 0.7, "maxTokens": 500 } }
```

---

## Schedule Trigger (nodes-base.scheduleTrigger)

```javascript
// Daily at 9 AM — GOTCHA: always set timezone explicitly!
{ "rule": { "interval": [{ "field": "hours", "hoursInterval": 24 }],
    "hour": 9, "minute": 0, "timezone": "America/New_York" } }

// Every 15 minutes
{ "rule": { "interval": [{ "field": "minutes", "minutesInterval": 15 }] } }

// Cron
{ "mode": "cron", "cronExpression": "0 */2 * * *", "timezone": "America/New_York" }
```

---

## Key Gotchas Summary

| Node | Gotcha |
|---|---|
| HTTP Request | `sendBody: true` required for POST/PUT/PATCH |
| Webhook | Data under `$json.body`, not `$json` |
| Slack | Channel must start with `#` or be ID |
| Postgres | Use parameterized queries ($1) not string interpolation |
| Set | Match `type` field to actual value type |
| Code | Use `$input.item.json` not `{{...}}` expressions |
| IF | Unary operators (isEmpty) don't need `value2` |
| Switch | Rule count must match output count |
| Schedule | Always set timezone explicitly |

---

## Related

- [SKILL.md](../SKILL.md) — Configuration workflow
- [DEPENDENCIES.md](DEPENDENCIES.md) — Property dependency rules
