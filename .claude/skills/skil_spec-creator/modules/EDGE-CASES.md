# Common Edge Cases

Reference this module to add appropriate edge cases based on the systems involved and the orchestrator type.

## API Integrations (General)

These apply to all orchestrators:

| Scenario | Handling | Recovery |
|----------|----------|----------|
| Rate limit (429) | Retry with exponential backoff (3 attempts) | Auto-retry |
| Auth expired (401) | Refresh token, retry once | Auto-retry |
| Not found (404) | Log warning, skip item | Continue |
| Server error (5xx) | Fail step, trigger self-healing | Manual review |
| Timeout | Retry 3x with increasing timeout (5s, 10s, 30s) | Auto-retry |
| Connection refused | Wait 60s, retry 3x | Auto-retry |
| Invalid response format | Log error, skip item | Continue |

## By System

### Fortnox

| Scenario | Handling |
|----------|----------|
| Customer number not found | Log error, skip order creation |
| Invalid article number | Log error, skip line item |
| Concurrent modification | Retry with latest version |
| Deleted record | Skip, log as "deleted_in_source" |

### Upsales

| Scenario | Handling |
|----------|----------|
| Company without org number | Use company name as identifier |
| Missing required fields | Log error, skip sync |
| Webhook replay (duplicate) | Check idempotency, skip if processed |

### Slack

| Scenario | Handling |
|----------|----------|
| Channel not found | Fall back to default channel |
| Message too long | Truncate or split into parts |
| Rate limit | Queue messages, send with delay |

### Google Sheets

| Scenario | Handling |
|----------|----------|
| Sheet not found | Create sheet or fail with clear error |
| Row limit exceeded | Create new sheet or archive old data |
| Cell format error | Force string type, log warning |

### OpenRouter / AI Classification

| Scenario | Handling |
|----------|----------|
| Empty input | Return default classification |
| Invalid JSON response | Parse with fallback regex |
| Low confidence (<70%) | Flag for manual review |
| API timeout | Use cached result or default |
| Model unavailable | Fall back to alternative model |

## Webhook-Specific

| Scenario | Handling |
|----------|----------|
| Duplicate webhook (idempotency) | Check event ID, skip if processed |
| Missing required fields | Log error, return 400 |
| Invalid signature | Reject with 401, log attempt |
| Payload too large | Log error, return 413 |
| Out-of-order events | Check timestamps, process in order |

## Data Transformation

| Scenario | Handling |
|----------|----------|
| Null/missing required field | Use default value or skip record |
| Invalid date format | Try multiple formats, fail gracefully |
| Encoding issues | Normalize to UTF-8, replace invalid chars |
| Numeric overflow | Cap at max value, log warning |
| Unexpected data type | Coerce if possible, skip if not |

## Duplicate Handling

| Scenario | Handling |
|----------|----------|
| Item already exists | Skip, log as "already_exists" |
| Partial duplicate | Update existing, log as "updated" |
| Conflicting data | Use source of truth, log conflict |

## Business Logic

| Scenario | Handling |
|----------|----------|
| Business hours only | Queue for next business day |
| Weekend/holiday | Skip or queue |
| User not found | Create user or skip with log |
| Invalid state transition | Log error, notify admin |

---

## n8n-Specific Edge Cases

These apply when `orchestrator: n8n`. n8n handles errors at the node level.

### Node Error Handling

| Scenario | Handling | n8n Configuration |
|----------|----------|-------------------|
| HTTP 429 (rate limit) | Node retry with backoff | Settings → Retry On Fail → 3 attempts |
| HTTP 401 (auth expired) | Credential auto-refresh | Use OAuth2 credentials in n8n |
| HTTP 404 (not found) | Skip item, continue workflow | Settings → Continue On Fail → Enable |
| HTTP 5xx (server error) | Node retry, then fail | Settings → Retry On Fail → 3 attempts |
| Node timeout | Increase timeout or split batch | Settings → Timeout → 30000ms |
| Invalid response | Continue workflow, log in execution | Enable Continue On Fail |
| Expression error | Workflow fails at node | Check expression syntax, add fallback |

### Credential Issues

| Scenario | Handling |
|----------|----------|
| OAuth2 token expired | n8n auto-refreshes if credential configured correctly |
| API key invalid | Manual update in n8n Credentials UI |
| Missing credential | Workflow fails at first node using it |
| Credential scope insufficient | Update credential permissions, re-authorize |

### n8n Data Handling

| Scenario | Handling |
|----------|----------|
| Empty input items | Check with IF node: `{{ $json.length > 0 }}` |
| Missing field | Use expression fallback: `{{ $json.field ?? 'default' }}` |
| Large payload (>16MB) | Split with "Split In Batches" node |
| Invalid JSON from Code node | Use try/catch in Code node |
| Pagination needed | Loop with HTTP Request + merge results |

### Workflow Execution

| Scenario | Handling |
|----------|----------|
| Workflow timeout | Set timeout in workflow settings |
| Concurrent executions | Limit max concurrent in workflow settings |
| Schedule missed (instance down) | Execution runs on next available slot |
| Manual test leaves data | Use Limit nodes + disable write nodes during testing |

## Make.com-Specific Edge Cases

These apply when `orchestrator: make`. Make.com handles errors at the module level using error handler routes.

### Module Error Handling

| Scenario | Handling | Make.com Configuration |
|----------|----------|----------------------|
| HTTP 429 (rate limit) | Auto-retry or sleep | Error handler → Sleep module → Retry |
| HTTP 401 (auth expired) | Connection auto-refresh | Reconfigure connection in Make.com |
| HTTP 404 (not found) | Skip item | Error handler → Resume route |
| HTTP 5xx (server error) | Retry, then stop | Error handler → Break route |
| Module timeout | Increase timeout | Scenario settings → Timeout |
| Incomplete execution | Resume or rollback | Execution history → "Resume" or "Rollback" |

### Connection Issues

| Scenario | Handling |
|----------|----------|
| OAuth2 token expired | Make.com auto-refreshes if connection is healthy |
| API key invalid | Reconnect in Make.com Connections UI |
| App unavailable | Error handler captures, retry later |
| Connection scope insufficient | Re-authorize with updated permissions |

### Data Handling

| Scenario | Handling |
|----------|----------|
| Empty array input | Check with filter or router before iterator |
| Missing mapped field | Use `ifempty(value, default)` in mapping |
| Large data volume | Use iterator with sleep to avoid rate limits |
| Incomplete execution backlog | Check "Incomplete executions" in scenario settings |

### Scenario Execution

| Scenario | Handling |
|----------|----------|
| Operations quota exceeded | Scenario pauses until quota resets (monthly) |
| Concurrent execution conflict | Enable "Sequential processing" in scenario settings |
| Schedule missed (org paused) | Execution runs on next available slot |
| Webhook URL changed | Re-register URL in source system |

## Self-Healing Triggers

When an error occurs that can't be auto-recovered:

**Code-based:**
1. Log full error context to database
2. Trigger self-healing webhook (if configured)
3. Include: automation_id, step, error, input data
4. Mark execution as "failed" (can become "auto_resolved" if self-healing succeeds)

**n8n:**
1. Error is visible in n8n Execution log with full node details
2. Add error workflow handler (n8n Error Trigger node) for critical workflows
3. Send Slack notification on failure with error details

**Make.com:**
1. Error is visible in execution history with full module details
2. Incomplete executions are saved for manual resume (if using Break handler)
3. Add a notification module (Slack, email) in the error handler route for alerting
