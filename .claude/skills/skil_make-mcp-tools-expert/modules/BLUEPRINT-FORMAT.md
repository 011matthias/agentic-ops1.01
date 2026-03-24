# Make.com Blueprint JSON Format

Complete reference for the Make.com scenario blueprint structure.

---

## Top-Level Structure

```json
{
  "flow": [ ... ],
  "metadata": { ... },
  "scheduling": { "type": "immediately" },
  "interface": { "input": [], "output": [] }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `flow` | Yes | Ordered list of modules (the automation steps) |
| `metadata` | Yes | Scenario settings and designer layout |
| `scheduling` | UI import only | Scheduling config (`"immediately"` for webhook, `{"type":"indefinitely","interval":N}` for polling) |
| `interface` | UI import only | Interface definition (usually `{"input":[],"output":[]}`) |

> **API vs UI import — different accepted keys:**
> - **UI import** (three-dots menu → Import Blueprint): Accepts `flow`, `metadata`, `scheduling`, `interface`. This is the format Make.com's own "Export Blueprint" produces. Use this format for handover blueprints.
> - **API deployment** (`scenarios_update` blueprint param): Accepts only `flow` and `metadata`. Do NOT include `scheduling` or `interface` — set those via `scenarios_update` scheduling param and `scenarios_set_interface` respectively.
> - **`name` at the top level:** Make.com's own "Export Blueprint" includes `name`, and the UI import silently ignores it. However, the API schema validator rejects it. **Omit `name` from handover blueprints** to be safe — set the scenario name via `scenarios_update` (API) or the scenario editor title bar (UI).
>
> **Validation tool scope:** `validate_blueprint_schema` (MCP tool) only validates API deployment format (`flow` + `metadata`). It will NOT catch missing UI-import fields (`scheduling`, `interface`, `designer.orphans`, `dataloss`). Run `blueprint-reconciler` > HANDOVER-FORMAT-CHECKER for UI import validation.

---

## Flow Array (Modules)

Each module in the `flow` array represents one step in the scenario:

```json
{
  "id": 1,
  "module": "gateway:CustomWebhook",
  "version": 1,
  "parameters": {
    "hook": "{{webhook_id}}"
  },
  "mapper": {
    "field_name": "{{1.body.email}}"
  },
  "filter": {
    "name": "Only high-value",
    "conditions": [[{
      "a": "{{1.body.event_type}}",
      "b": "wedding",
      "o": "text:equal"
    }]]
  },
  "metadata": {
    "designer": { "x": 0, "y": 150 },
    "restore": {},
    "parameters": []
  }
}
```

### Module Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique numeric ID within the scenario (1, 2, 3...) |
| `module` | Yes | Module type string: `app:operation` |
| `version` | Yes | Module version number |
| `parameters` | Yes | Module configuration (connections, settings) |
| `mapper` | No | Data mappings (input field values from previous modules) |
| `filter` | No | Conditional filter before this module executes |
| `metadata` | No | UI positioning and display settings |

---

## Common Module Types

### Triggers

| Module | Description |
|--------|-------------|
| `gateway:CustomWebhook` | Custom webhook endpoint |
| `google-sheets:watchRows` | Watch for new rows in Google Sheets |
| `gmail:watchEmails` | Watch for new emails |
| `builtin:BasicScheduler` | Schedule-based trigger |

### Actions

| Module | Description |
|--------|-------------|
| `google-sheets:addRow` | Add row to Google Sheets |
| `google-sheets:updateRow` | Update existing row |
| `google-sheets:searchRows` | Search for rows |
| `gmail:sendEmail` | Send email via Gmail |
| `http:ActionSendData` | HTTP request (POST/PUT/PATCH) |
| `http:ActionGetData` | HTTP request (GET) |
| `airtable:ActionCreateRecord` | Create Airtable record |
| `airtable:ActionUpdateRecord` | Update Airtable record |
| `airtable:ActionSearchRecords` | Search Airtable records |

### Flow Control

| Module | Description |
|--------|-------------|
| `builtin:BasicRouter` | Router (conditional branching) |
| `builtin:BasicFeeder` | Iterator (loop over array items) |
| `builtin:BasicAggregator` | Aggregator (combine items back) |
| `builtin:Sleep` | Sleep/delay between steps |
| `builtin:TextAggregator` | Aggregate text values |
| `builtin:ArrayAggregator` | Aggregate into array |

### Utilities

| Module | Description |
|--------|-------------|
| `util:SetVariable2` | Set variable |
| `util:GetVariable2` | Get variable |
| `util:FunctionLetToNumber` | Convert to number |
| `builtin:WebhookResponse` | Respond to webhook |

---

## Router Module (Branching)

Routers create conditional branches. Each route is a separate path with its own filter:

```json
{
  "id": 3,
  "module": "builtin:BasicRouter",
  "version": 1,
  "parameters": {},
  "mapper": null,
  "metadata": {
    "designer": { "x": 300, "y": 0 }
  },
  "routes": [
    {
      "flow": [
        {
          "id": 4,
          "module": "gmail:sendEmail",
          "version": 1,
          "parameters": { "account": "{{connection_id}}" },
          "mapper": {
            "to": "{{1.body.email}}",
            "subject": "Thank you for your enquiry",
            "html": "<p>Hi {{1.body.name}},</p>"
          },
          "filter": {
            "name": "High priority",
            "conditions": [[{
              "a": "{{1.body.event_value}}",
              "b": "5000",
              "o": "number:greater"
            }]]
          }
        }
      ]
    },
    {
      "flow": [
        {
          "id": 5,
          "module": "gmail:sendEmail",
          "version": 1,
          "parameters": { "account": "{{connection_id}}" },
          "mapper": {
            "to": "{{1.body.email}}",
            "subject": "Thanks for reaching out",
            "html": "<p>Hi {{1.body.name}},</p>"
          },
          "filter": {
            "name": "Standard priority",
            "conditions": [[{
              "a": "{{1.body.event_value}}",
              "b": "5000",
              "o": "number:lessEqual"
            }]]
          }
        }
      ]
    }
  ]
}
```

---

## Filter Syntax

Filters control whether a module (or route) executes:

```json
{
  "name": "Filter description",
  "conditions": [
    [
      {
        "a": "{{1.body.field}}",
        "b": "value",
        "o": "text:equal"
      }
    ]
  ]
}
```

### Operators

| Operator | Description |
|----------|-------------|
| `text:equal` | Text equals |
| `text:notEqual` | Text not equals |
| `text:contain` | Text contains |
| `text:notContain` | Text does not contain |
| `text:startsWith` | Text starts with |
| `text:endsWith` | Text ends with |
| `number:equal` | Number equals |
| `number:greater` | Number greater than |
| `number:less` | Number less than |
| `number:greaterEqual` | Number greater or equal |
| `number:lessEqual` | Number less or equal |
| `boolean:equal` | Boolean equals |
| `exist` | Value exists (not empty) |
| `notExist` | Value does not exist |

### AND / OR Logic

- **AND:** Multiple conditions in the same inner array
- **OR:** Multiple inner arrays

```json
"conditions": [
  [
    {"a": "{{1.email}}", "o": "exist"},
    {"a": "{{1.status}}", "b": "new", "o": "text:equal"}
  ],
  [
    {"a": "{{1.priority}}", "b": "urgent", "o": "text:equal"}
  ]
]
```
This means: (email exists AND status = "new") OR (priority = "urgent")

---

## Data Mapping (Mapper)

The `mapper` object maps data from previous modules into the current module's inputs:

```json
"mapper": {
  "to": "{{1.body.email}}",
  "subject": "Re: {{1.body.enquiry_subject}}",
  "html": "<p>Hi {{1.body.first_name}},</p><p>Thank you for your enquiry about {{1.body.service}}.</p>"
}
```

### Reference Syntax

| Syntax | Description |
|--------|-------------|
| `{{N.field}}` | Reference field from module with id=N |
| `{{N.body.field}}` | Reference webhook body field |
| `{{N.`__IMTLENGTH__`}}` | Number of items from iterator |

### Common Functions

| Function | Description |
|----------|-------------|
| `{{ifempty(value; fallback)}}` | Use fallback if value is empty |
| `{{if(condition; trueVal; falseVal)}}` | Conditional value |
| `{{lower(text)}}` | Lowercase |
| `{{upper(text)}}` | Uppercase |
| `{{trim(text)}}` | Remove whitespace |
| `{{length(text)}}` | String length |
| `{{formatDate(date; format)}}` | Format a date |
| `{{parseDate(text; format)}}` | Parse text to date |
| `{{now}}` | Current timestamp |
| `{{addDays(date; N)}}` | Add N days |
| `{{toString(value)}}` | Convert to string |
| `{{toNumber(value)}}` | Convert to number |

---

## Metadata Structure

```json
{
  "metadata": {
    "version": 1,
    "instant": false,
    "scenario": {
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      "autoCommitTriggerLast": true,
      "sequential": false,
      "confidential": false,
      "dataloss": false
    },
    "designer": {
      "orphans": []
    },
    "zone": "us1.make.com"
  }
}
```

| Field | Description |
|-------|-------------|
| `instant` | `true` for webhook-triggered (instant) scenarios |
| `roundtrips` | Max cycles per execution (1 = default) |
| `maxErrors` | Max consecutive errors before pausing scenario |
| `autoCommit` | Auto-commit data store changes |
| `sequential` | Process items one-at-a-time (slower, safer) |

---

## Error Handler Attachment

Error handlers are attached to modules using a special `onerror` array:

```json
{
  "id": 4,
  "module": "http:ActionSendData",
  "version": 3,
  "parameters": {},
  "mapper": {},
  "onerror": [
    {
      "id": 5,
      "module": "builtin:Break",
      "version": 1,
      "parameters": {},
      "mapper": {
        "maxRetries": 3,
        "interval": 60
      }
    }
  ]
}
```

### Error Handler Types

| Module | Use When |
|--------|----------|
| `builtin:Break` | Fatal errors (5xx, timeout) — stop and retry |
| `builtin:Resume` | Non-fatal (404, validation) — skip and continue |
| `builtin:Ignore` | Expected/harmless — discard silently |
| `builtin:Rollback` | Need undo — revert previous actions |

---

## Complete Example: Webhook → Google Sheets → Gmail

```json
{
  "flow": [
    {
      "id": 1,
      "module": "gateway:CustomWebHook",
      "version": 1,
      "parameters": {
        "hook": null,
        "maxResults": 1
      },
      "mapper": {},
      "metadata": {
        "restore": {
          "parameters": {
            "hook": { "label": "Enquiry Form" }
          }
        },
        "designer": { "x": 0, "y": 0 }
      }
    },
    {
      "id": 2,
      "module": "google-sheets:addRow",
      "version": 2,
      "parameters": {
        "__IMTCONN__": 12345
      },
      "mapper": {
        "values": {
          "0": "{{1.body.name}}",
          "1": "{{1.body.email}}",
          "2": "{{1.body.service}}",
          "3": "{{now}}",
          "4": "new",
          "5": "1"
        }
      },
      "metadata": {
        "restore": {
          "parameters": {
            "__IMTCONN__": { "label": "Google Sheets (you@example.com)" }
          }
        },
        "designer": { "x": 300, "y": 0 }
      }
    },
    {
      "id": 3,
      "module": "google-email:sendAnEmail",
      "version": 4,
      "parameters": {
        "__IMTCONN__": 12346
      },
      "mapper": {
        "to": "{{1.body.email}}",
        "subject": "Thanks for your enquiry, {{1.body.name}}!",
        "html": "<p>Hi {{1.body.name}},</p><p>Thanks for reaching out.</p>"
      },
      "metadata": {
        "restore": {
          "parameters": {
            "__IMTCONN__": { "label": "Gmail (you@example.com)" }
          }
        },
        "designer": { "x": 600, "y": 0 }
      }
    }
  ],
  "metadata": {
    "version": 1,
    "instant": true,
    "designer": {
      "orphans": []
    },
    "scenario": {
      "dataloss": false,
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      "sequential": false,
      "confidential": false,
      "autoCommitTriggerLast": true
    }
  },
  "scheduling": {
    "type": "immediately"
  },
  "interface": {
    "input": [],
    "output": []
  }
}
```

---

## Blueprint Portability Notes

- **Connection IDs** must be replaced when deploying to a different org
- **Webhook IDs** are generated on scenario creation — you can't pre-set them
- **Designer coordinates** are optional but improve UI layout
- **Module versions** should match what's available in the target org
- Store blueprints in `workspace/clients/{client}/automations/blueprints/` for version control
