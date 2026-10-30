# Error Catalog

Quick-reference for n8n validation errors with fixes.

---

## Error Priority

| Type | Priority | Auto-Fix | Frequency |
|---|---|---|---|
| `missing_required` | Highest | No | 45% |
| `invalid_value` | High | No | 28% |
| `type_mismatch` | Medium | No | 12% |
| `invalid_expression` | Medium | No | 8% |
| `invalid_reference` | Low | No | 5% |
| `operator_structure` | Lowest | **Yes** | 2% |

---

## Errors (Must Fix)

### 1. missing_required

Required field not provided. Most common error.

**Typical causes:** New node missing fields, switching operations, conditional requirements.

```javascript
// ❌ Slack: missing channel
{ "resource": "message", "operation": "post" }

// ✅ Fix
{ "resource": "message", "operation": "post", "channel": "#general" }
```

```javascript
// ❌ HTTP Request: missing url
{ "method": "GET", "authentication": "none" }

// ✅ Fix
{ "method": "GET", "authentication": "none", "url": "https://api.example.com/data" }
```

```javascript
// ❌ Conditional required: sendBody=true but no body
{ "method": "POST", "url": "https://api.example.com", "sendBody": true }

// ✅ Fix: add the conditionally-required field
{ "method": "POST", "url": "https://api.example.com", "sendBody": true,
  "body": { "contentType": "json", "content": { "name": "John" } } }
```

**How to find required fields:** Use `get_node({ nodeType: "nodes-base.slack" })` and check `required: true` properties.

---

### 2. invalid_value

Value doesn't match allowed options. Second most common.

```javascript
// ❌ Invalid operation name
{ "resource": "message", "operation": "send" }
// ✅ Use valid value: "post" (check allowed: ["post", "update", "delete", "get"])

// ❌ Wrong channel format
{ "channel": "General" }
// ✅ Must start with #: "#general"

// ❌ Case-sensitive enums
{ "resource": "Message" }
// ✅ Lowercase: "message"
```

---

### 3. type_mismatch

Wrong data type (string vs number, etc.).

```javascript
// ❌ String instead of number
{ "limit": "100" }
// ✅ Use number: 100

// ❌ String instead of boolean
{ "sendHeaders": "true" }
// ✅ Use boolean: true

// ❌ Object instead of array
{ "tags": {"tag": "important"} }
// ✅ Use array: ["important", "alerts"]
```

---

### 4. invalid_expression

Expression syntax errors. See also **n8n Expression Syntax** skill.

```javascript
// ❌ Missing {{}} wrapper
{ "text": "$json.name" }
// ✅ Wrap: "={{$json.name}}"

// ❌ Typo in node name
{ "value": "={{$node['HTTP Requets'].json.data}}" }
// ✅ Correct: "={{$node['HTTP Request'].json.data}}"

// ❌ Unsafe deep access
{ "text": "={{$json.data.user.name}}" }
// ✅ Safe navigation: "={{$json.data?.user?.name || 'Unknown'}}"

// ❌ Webhook data: missing .body
{ "value": "={{$json.email}}" }
// ✅ Webhook data is under .body: "={{$json.body.email}}"
```

---

### 5. invalid_reference

Node referenced doesn't exist in workflow.

```javascript
// ❌ Deleted/renamed node
{ "value": "={{$node['Transform Data'].json.result}}" }
// ✅ Update to existing node name, or use cleanStaleConnections:
// n8n_update_partial_workflow({ id, operations: [{ type: "cleanStaleConnections" }] })
```

---

## Warnings (Should Fix)

### 6. best_practice

Works but risky. Fix for production workflows.

```javascript
// ⚠️ No error handling on external API calls
{ "resource": "message", "operation": "post", "channel": "#alerts" }
// Recommended: add continueOnFail: true, retryOnFail: true, maxTries: 3
```

### 7. deprecated

Old API version. Update eventually.

```javascript
// ⚠️ Old typeVersion
{ "type": "n8n-nodes-base.slack", "typeVersion": 1 }
// Recommended: "typeVersion": 2 (may need config updates)
```

### 8. performance

May cause issues at scale.

```javascript
// ⚠️ Unbounded query
"SELECT * FROM users WHERE active = true"
// Add LIMIT: "SELECT * FROM users WHERE active = true LIMIT 1000"
```

---

## Auto-Fixed: operator_structure

IF/Switch operator structure issues are **auto-fixed on save**. Don't manually fix these.

- Binary operators (equals, contains): `singleValue` removed if present
- Unary operators (isEmpty, isNotEmpty): `singleValue: true` added if missing

---

## Recovery Patterns

1. **Progressive validation** — Start with minimal valid config, add features one by one, validate after each addition
2. **Error triage** — Fix errors first (must), then warnings (should), then suggestions (optional)
3. **Use get_node** — Check requirements before configuring: `get_node({ nodeType: "nodes-base.slack" })`

---

## Related

- [SKILL.md](../SKILL.md) — Main validation guide
- [FALSE-POSITIVES.md](FALSE-POSITIVES.md) — When to ignore warnings
- **n8n Expression Syntax** skill — Fix expression errors
