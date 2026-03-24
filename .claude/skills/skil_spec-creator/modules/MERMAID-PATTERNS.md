# Mermaid Flow Patterns

Flow diagram templates organized by orchestrator type.

---

## Code-Based Patterns (Trigger.dev / FastAPI)

All code-based automations follow the 5-step BaseAutomation pattern.

### Base Pattern

Every automation uses this structure:

```mermaid
flowchart TD
    TRIGGER["Trigger"] --> INIT["1. Initialize"]
    INIT --> FETCH["2. Fetch Data"]
    FETCH --> TRANSFORM["3. Transform"]
    TRANSFORM --> EXECUTE["4. Execute"]
    EXECUTE --> FINALIZE["5. Finalize"]
```

### Filter Pattern

When fetching data and filtering before processing:

```mermaid
flowchart TD
    TRIGGER["CRON 08:00"] --> INIT["1. Initialize"]
    INIT --> FETCH["2. Fetch All Items"]
    FETCH --> CHECK{{"Items found?"}}
    CHECK -->|No| SKIP["Log: No items"]
    CHECK -->|Yes| FILTER["Filter: Match criteria"]
    FILTER --> TRANSFORM["3. Transform"]
    TRANSFORM --> EXECUTE["4. Execute"]
    EXECUTE --> FINALIZE["5. Finalize"]
    SKIP --> FINALIZE
```

### Duplicate Check Pattern

When preventing duplicate creation:

```mermaid
flowchart TD
    TRANSFORM["3. Transform"] --> LOOP["For each item"]
    LOOP --> DUP{{"Already exists?"}}
    DUP -->|Yes| LOG["Log: Skip"]
    DUP -->|No| CREATE["Create item"]
    LOG --> NEXT["Next item"]
    CREATE --> NEXT
    NEXT --> LOOP
    NEXT -->|Done| FINALIZE["5. Finalize"]
```

### Webhook Classification Pattern

When classifying incoming webhooks:

```mermaid
flowchart TD
    TRIGGER["Webhook"] --> INIT["1. Initialize"]
    INIT --> EXTRACT["2. Extract Data"]
    EXTRACT --> CLASSIFY["3. Classify (AI)"]
    CLASSIFY --> DECISION{{"Classification"}}
    DECISION -->|Positive| ACTION["4. Take Action"]
    DECISION -->|Negative| SKIP["Log Only"]
    ACTION --> NOTIFY["Send Notification"]
    SKIP --> FINALIZE["5. Finalize"]
    NOTIFY --> FINALIZE
```

### Sync Pattern

When syncing data between systems:

```mermaid
flowchart TD
    TRIGGER["CRON"] --> INIT["1. Initialize"]
    INIT --> FETCH_SRC["2a. Fetch Source"]
    FETCH_SRC --> FETCH_DST["2b. Fetch Destination"]
    FETCH_DST --> COMPARE["3. Compare"]
    COMPARE --> DIFF{{"Difference?"}}
    DIFF -->|New| CREATE["Create"]
    DIFF -->|Updated| UPDATE["Update"]
    DIFF -->|Deleted| ARCHIVE["Archive"]
    DIFF -->|Same| SKIP["Skip"]
    CREATE --> FINALIZE["5. Finalize"]
    UPDATE --> FINALIZE
    ARCHIVE --> FINALIZE
    SKIP --> FINALIZE
```

### Multi-System Pipeline

When data flows through multiple systems:

```mermaid
flowchart TD
    TRIGGER["Webhook from A"] --> INIT["1. Initialize"]
    INIT --> FETCH_A["2. Fetch from A"]
    FETCH_A --> ENRICH["Fetch from B"]
    ENRICH --> TRANSFORM["3. Transform"]
    TRANSFORM --> EXECUTE_C["4. Create in C"]
    EXECUTE_C --> NOTIFY["Notify via D"]
    NOTIFY --> FINALIZE["5. Finalize"]
```

---

## n8n Workflow Patterns

n8n workflows use node-based patterns. Diagrams reference node types and operations directly.

### Node Naming Conventions

| Node Type | Naming in Diagram | Example |
|-----------|-------------------|---------|
| HTTP Request | Method + path | `"GET /orders"`, `"POST /customers"` |
| Native node | Node name + action | `"Slack: Post Message"` |
| Code node | `Code:` + purpose | `"Code: Transform Data"`, `"Code: Build Payload"` |
| IF node | Question format | `"Status = ACTIVE?"`, `"Due within 7 days?"` |
| Trigger | Type + context | `"CRON: 08:00 CET"`, `"Webhook: POST"` |

### HTTP API Pattern

Scheduled fetching from APIs with filtering and creation:

```mermaid
flowchart TD
    TRIGGER(("CRON: 08:00")) --> FETCH["GET /resource\n(paginated)"]
    FETCH --> EXTRACT["Extract Items"]
    EXTRACT --> FILTER{{"Match criteria?"}}
    FILTER -->|No| SKIP["Skip"]
    FILTER -->|Yes| DETAILS["GET /resource/{id}\n(fetch details)"]
    DETAILS --> TRANSFORM["Code: Transform"]
    TRANSFORM --> CREATE["POST /target"]
    CREATE --> NOTIFY["Slack: Notify"]
```

### Webhook Processing Pattern

Receiving and processing webhook events:

```mermaid
flowchart TD
    TRIGGER(("Webhook: POST")) --> EXTRACT["Extract Body"]
    EXTRACT --> VALIDATE{{"Valid payload?"}}
    VALIDATE -->|No| ERROR["Return 400"]
    VALIDATE -->|Yes| PROCESS["Code: Process Data"]
    PROCESS --> ACTION["POST /target"]
    ACTION --> NOTIFY["Slack: Success"]
```

### Enrichment Pattern

Fetching an item and enriching it with additional data:

```mermaid
flowchart TD
    TRIGGER["Manual Trigger\n(item ID input)"] --> FETCH["GET /item/{id}"]
    FETCH --> CHECK{{"Needs enrichment?"}}
    CHECK -->|No| SKIP["Already complete\n→ Stop"]
    CHECK -->|Yes| LOOKUP["GET /related/{ref}"]
    LOOKUP --> BUILD["Code: Build\nUpdate Payload"]
    BUILD --> UPDATE["PUT /item/{id}"]
    UPDATE --> DONE["Done"]
```

### Duplicate Detection Pattern

Checking for existing items before creation:

```mermaid
flowchart TD
    TRANSFORM["Code: Format Item"] --> CHECK["GET /existing\n?filter=identifier"]
    CHECK --> EXISTS{{"Already exists?"}}
    EXISTS -->|Yes| SKIP["Skip: Log duplicate"]
    EXISTS -->|No| CREATE["POST /create"]
    CREATE --> NEXT["Next Item"]
    SKIP --> NEXT
```

### Sync Pattern (n8n)

Syncing data between two systems:

```mermaid
flowchart TD
    TRIGGER(("CRON: Hourly")) --> FETCH_A["GET /system-a/items"]
    FETCH_A --> FETCH_B["GET /system-b/items"]
    FETCH_B --> COMPARE["Code: Compare\nby ID"]
    COMPARE --> NEW{{"New items?"}}
    NEW -->|Yes| CREATE["POST /system-b"]
    NEW -->|No| UPDATED{{"Updated?"}}
    UPDATED -->|Yes| UPDATE["PUT /system-b/{id}"]
    UPDATED -->|No| DONE["Done"]
```

### Phased Pattern

Building incrementally (manual first, then automated):

```mermaid
flowchart TD
    subgraph "Phase 1 (Manual)"
        MANUAL["Manual Trigger\n(input form)"] --> CORE["Core Logic"]
    end
    subgraph "Phase 2 (Automated)"
        WEBHOOK(("Webhook")) --> WAIT["Wait 5 min"]
        WAIT --> SEARCH["Search for item"]
        SEARCH --> CORE
    end
    CORE --> PROCESS["Process & Update"]
```

---

## Make.com Scenario Patterns

Make.com scenarios use module-based patterns. Diagrams reference module types and apps.

### Module Naming Conventions

| Module Type | Naming in Diagram | Example |
|-------------|-------------------|---------|
| App action | `App: Action` | `"Fortnox: List orders"`, `"Slack: Post message"` |
| HTTP module | `HTTP: Method path` | `"HTTP: GET /orders"`, `"HTTP: POST /items"` |
| Router | `Router` | `"Router"` |
| Iterator | `Iterator: purpose` | `"Iterator: Process items"` |
| Aggregator | `Aggregator: purpose` | `"Aggregator: Collect results"` |
| Filter | `Filter: condition` | `"Filter: Status = Active"` |
| Tools | `Tools: Action` | `"Tools: Set variable"` |
| Trigger | `Type + app` | `"Watch: New orders"`, `"Webhook: POST"` |

### Scheduled API Pattern (Make.com)

```mermaid
flowchart TD
    TRIGGER(("Schedule: Every day")) --> FETCH["Fortnox: List orders"]
    FETCH --> ITERATOR["Iterator: Process items"]
    ITERATOR --> FILTER{{"Status = Active?"}}
    FILTER -->|No| SKIP["Skip"]
    FILTER -->|Yes| TRANSFORM["Tools: Set variable"]
    TRANSFORM --> CREATE["Upsales: Create deal"]
    CREATE --> NOTIFY["Slack: Post message"]
```

### Webhook Processing Pattern (Make.com)

```mermaid
flowchart TD
    TRIGGER(("Webhook: POST")) --> ROUTER["Router"]
    ROUTER -->|Order event| FETCH["HTTP: GET /order/{id}"]
    ROUTER -->|Other event| LOG["Tools: Set variable\n(log only)"]
    FETCH --> TRANSFORM["Tools: Set variable\n(build payload)"]
    TRANSFORM --> CREATE["Target App: Create item"]
    CREATE --> RESPONSE["Webhook Response: 200"]
    LOG --> RESPONSE
```

### Data Sync Pattern (Make.com)

```mermaid
flowchart TD
    TRIGGER(("Schedule: Hourly")) --> FETCH_A["System A: List items"]
    FETCH_A --> ITERATOR["Iterator: Each item"]
    ITERATOR --> LOOKUP["System B: Search item"]
    LOOKUP --> EXISTS{{"Exists in B?"}}
    EXISTS -->|No| CREATE["System B: Create"]
    EXISTS -->|Yes| COMPARE{{"Changed?"}}
    COMPARE -->|Yes| UPDATE["System B: Update"]
    COMPARE -->|No| SKIP["Skip"]
```

---

## Style Guidelines

### Node Shapes

| Shape | Syntax | Use For |
|-------|--------|---------|
| Rectangle | `["text"]` | Steps, actions, nodes |
| Diamond | `{{"text"}}` | Decision points (IF/Switch) |
| Stadium | `(("text"))` | Triggers (CRON, Webhook) |
| Parallelogram | `[/"text"/]` | Input/Output |

### Naming Conventions

- **Triggers:** Stadium shape with context: `(("CRON: 08:00 CET"))` or `(("Webhook: POST"))`
- **Code-based:** Numbered steps (1-5) for main automation steps
- **n8n:** Show what the node DOES, not generic names
- **Make.com:** Show app name + action (e.g., "Fortnox: List orders")
- **Decisions:** Question format in diamond nodes
- **Multiline:** Use `\n` for complex node labels

### Complexity Limits

- Maximum 15-20 nodes for readability
- Break complex flows into sub-diagrams if needed
- Show main flow, detail edge cases in text
- Use subgraphs for logical grouping:

```mermaid
flowchart TD
    subgraph Fetch
        A --> B
        B --> C
    end
    subgraph Process
        D --> E
    end
    C --> D
```

## Trigger Node Examples

| Trigger Type | Code-Based | n8n | Make.com |
|--------------|-----------|-----|---------|
| Daily CRON | `["CRON 08:00"]` | `(("CRON: 08:00 CET"))` | `(("Schedule: Every day"))` |
| Hourly CRON | `["CRON Hourly"]` | `(("CRON: Every Hour"))` | `(("Schedule: Hourly"))` |
| Webhook | `["Webhook: {event}"]` | `(("Webhook: POST"))` | `(("Webhook: POST"))` |
| Manual | `["Manual Trigger"]` | `["Manual Trigger\n(input form)"]` | `["Run once\n(manual)"]` |
| Watch/Poll | — | — | `(("Watch: New items"))` |
