# Make.com Scenario Building Guide

Instructions for building and managing Make.com scenarios, guided by specs.

## Core Principles

### 1. Specs as Blueprints
Scenarios are built in the Make.com UI. The spec defines architecture, module selection, data mappings, and error handling. Always read the spec before opening Make.com.

### 2. Native Apps First
Always check if Make.com has a native app module for a system before using the generic HTTP module. Native apps handle auth, pagination, and rate limiting automatically.

### 3. Error Handlers on Critical Modules
Every module that writes data (POST, PUT, DELETE) or calls an external API should have an error handler route attached.

### 4. Naming Convention
Scenarios: `{AutomationID} - {Description}` (e.g., `A3 - Daily Order Sync`)
Variables: `snake_case` (e.g., `order_count`, `last_sync_date`)

### 5. Test Before Activating
Always test with "Run once" before turning on scheduling. Never activate an untested scenario.

## Scenario Organization

### Organization Structure
- Each client has their own Make.com organization (or team within a shared org)
- Scenarios grouped by domain or automation group using Make.com folders
- One scenario per automation spec (matching the spec ID)

### Naming Convention
```
{ID} - {Short Description}
```
Examples:
- `A1 - Daily CRM Sync`
- `A2 - Webhook Order Processor`
- `A3.1 - Invoice Line Item Enrichment`

### Variables & Data Stores
- Use scenario-level variables for configuration (equivalent to n8n's Config node)
- Use Make.com Data Stores for persistent state (duplicate tracking, counters, etc.)
- Document all variables and data stores in the spec's Implementation Notes section

## Error Handling Patterns

### Error Handler Types

| Type | Use When | Behavior |
|------|----------|----------|
| **Break** | Fatal error, must stop | Stops scenario, saves to incomplete executions |
| **Resume** | Non-fatal, skip and continue | Skips failed item, continues with next |
| **Ignore** | Error is expected/harmless | Discards error silently (use sparingly) |
| **Rollback** | Need to undo previous actions | Undoes previous module actions (transactional) |

### Standard Error Handler Pattern

For HTTP/write modules:
```
Module --> [Error Handler]
             |-- Break route (for 5xx, timeout --> stop and alert)
             |-- Resume route (for 404, validation errors --> skip item)
```

### Retry Pattern

For transient failures (429, 5xx, timeouts):
```
Module --> Error Handler --> Sleep (exponential backoff) --> HTTP (retry same request)
```

## Webhook Setup

### Instant Triggers
1. Add "Custom Webhook" or app-specific instant trigger module
2. Copy the webhook URL from Make.com
3. Register the URL in the source system
4. Click "Run once" in Make.com (it waits for incoming data)
5. Send a test event from the source system
6. Make.com learns the payload structure automatically

### Important
- Webhook URLs change if you delete and recreate the trigger module
- Use "Determine data structure" to teach Make.com the payload format if needed
- Verify webhook delivery in the source system's logs/settings
- For production: ensure the source system uses the final webhook URL

## Scheduling

### Schedule Triggers
- Configure interval: every X minutes, hours, or days
- Set specific execution time if needed (e.g., daily at 08:00)
- Make.com schedule uses the organization's timezone setting
- Minimum interval depends on the Make.com plan

### Rate Limiting
- Add Sleep modules between iterator items to avoid API rate limits
- Typical: 200-500ms between requests for most APIs
- Check target API documentation for specific rate limits
- Use the `sleep()` function or a dedicated Sleep module

## Connection Management

### Setup
- Configure connections in Make.com's Connections page (sidebar)
- Use OAuth2 where available (Make.com handles token refresh automatically)
- API keys: store in the connection configuration, not hardcoded in module parameters

### Credential Rotation
- OAuth2: Make.com auto-refreshes tokens if the connection is healthy
- API keys: update in Make.com Connections UI when rotated, then test the connection
- After updating any connection, run the scenario once to verify it works

## Data Mapping Best Practices

### Common Functions
- `ifempty(value, default)` -- handle missing or empty fields
- `parseDate(string, format)` -- parse date strings into Date objects
- `formatDate(date, format)` -- format dates for output
- `toString()`, `parseNumber(value; ".")` -- type conversion (NOT `toNumber`, which doesn't exist)
- `length(array)` -- check array size before iterating
- `emptyarray` -- initialize empty collections
- `get(object, key)` -- safe property access

### Iterator + Aggregator Pattern
When processing arrays of items:
```
Source Module --> Iterator --> Process Module --> Aggregator --> Next Module
```
- Iterator flattens an array into individual bundles (one per item)
- Aggregator collects processed results back into an array
- Always add a Sleep module inside the iterator if calling external APIs

### Router Pattern
For conditional branching:
```
Source Module --> Router
                   |-- Route 1 (filter: condition A) --> Action A
                   |-- Route 2 (filter: condition B) --> Action B
                   |-- Fallback route --> Default Action
```
- Each route has a filter condition (evaluated top to bottom)
- Use a fallback route for items that don't match any condition
- Routes execute in parallel by default

## Execution Monitoring

### Execution History
- Make.com retains execution history based on your plan tier
- Review failed executions regularly in the scenario's history tab
- "Incomplete executions" contain runs stopped by Break error handlers
- Resolve incomplete executions promptly to avoid data loss

### Key Metrics
- **Operations used** -- each module execution counts as one operation (monthly quota)
- **Error rate** -- failed vs successful executions
- **Execution time** -- per-scenario, monitor for performance degradation

## Integration with Agentic Ops

### Spec Workflow
1. Create spec with `/spec-creator` (set `orchestrator: make`)
2. Review spec -- ensure all modules, mappings, and error handling are defined
3. Build scenario in Make.com UI following the spec blueprint
4. Test with "Run once" and verify in target systems
5. Activate scheduling
6. Update spec frontmatter: `stage: live`

### Client Folder Structure
```
workspace/clients/{client}/
├── specs/                # Specs guide the scenario building
├── context/              # Client notes, Make.com org details
├── infrastructure.yaml   # Make.com instance tracking (type: make)
└── automations/
    └── README.md         # Links to Make.com org, scenario index
```

### infrastructure.yaml Entry
```yaml
instances:
  - type: make
    name: make-{client-name}
    org_url: https://www.make.com/en/organizations/{org-id}
    team: {team-name}            # Optional, if using teams
```
