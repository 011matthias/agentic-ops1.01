# N8N Expression Conversion

Reference for converting N8N expressions to Python syntax.

---

## Basic Data Access

### Current Item Data

| N8N | Python |
|-----|--------|
| `{{ $json }}` | `data` |
| `{{ $json.field }}` | `data["field"]` |
| `{{ $json.nested.field }}` | `data["nested"]["field"]` |
| `{{ $json["field-name"] }}` | `data["field-name"]` |
| `{{ $json.items[0] }}` | `data["items"][0]` |

### Previous Node Data

| N8N | Python |
|-----|--------|
| `{{ $node["NodeName"].json }}` | `steps["node_name"]` |
| `{{ $node["NodeName"].json.field }}` | `steps["node_name"]["field"]` |
| `{{ $("NodeName").item.json }}` | `steps["node_name"]` |

**Note:** Convert node names to snake_case for Python variables.

### Input Data

| N8N | Python |
|-----|--------|
| `{{ $input.first().json }}` | `input_data[0]` |
| `{{ $input.last().json }}` | `input_data[-1]` |
| `{{ $input.all() }}` | `input_data` |
| `{{ $input.item.json }}` | `current_item` |

---

## Built-in Variables

### Workflow Context

| N8N | Python |
|-----|--------|
| `{{ $workflow.id }}` | `os.environ.get("WORKFLOW_ID", "unknown")` |
| `{{ $workflow.name }}` | `self.__class__.__name__` |
| `{{ $execution.id }}` | `self.execution_id` |
| `{{ $runIndex }}` | `loop_index` (in loop context) |
| `{{ $itemIndex }}` | `item_index` (in loop context) |

### Environment Variables

| N8N | Python |
|-----|--------|
| `{{ $env.VAR_NAME }}` | `os.environ["VAR_NAME"]` |
| `{{ $env["VAR-NAME"] }}` | `os.environ["VAR-NAME"]` |

---

## Date/Time Functions

### Current Time

| N8N | Python |
|-----|--------|
| `{{ $now }}` | `datetime.now()` |
| `{{ $now.toISO() }}` | `datetime.now().isoformat()` |
| `{{ $now.format("YYYY-MM-DD") }}` | `datetime.now().strftime("%Y-%m-%d")` |
| `{{ $today }}` | `datetime.now().date()` |

### Date Manipulation

| N8N | Python |
|-----|--------|
| `{{ $now.plus({days: 7}) }}` | `datetime.now() + timedelta(days=7)` |
| `{{ $now.minus({hours: 2}) }}` | `datetime.now() - timedelta(hours=2)` |
| `{{ $now.startOf("month") }}` | `datetime.now().replace(day=1, hour=0, minute=0, second=0)` |
| `{{ $now.endOf("month") }}` | `(datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)` |

### Date Parsing

| N8N | Python |
|-----|--------|
| `{{ DateTime.fromISO($json.date) }}` | `datetime.fromisoformat(data["date"])` |
| `{{ DateTime.fromFormat($json.date, "dd/MM/yyyy") }}` | `datetime.strptime(data["date"], "%d/%m/%Y")` |

**Required imports:**
```python
from datetime import datetime, timedelta
```

---

## String Functions

| N8N | Python |
|-----|--------|
| `{{ $json.name.toUpperCase() }}` | `data["name"].upper()` |
| `{{ $json.name.toLowerCase() }}` | `data["name"].lower()` |
| `{{ $json.text.trim() }}` | `data["text"].strip()` |
| `{{ $json.text.split(",") }}` | `data["text"].split(",")` |
| `{{ $json.items.join(", ") }}` | `", ".join(data["items"])` |
| `{{ $json.text.replace("old", "new") }}` | `data["text"].replace("old", "new")` |
| `{{ $json.text.slice(0, 10) }}` | `data["text"][:10]` |
| `{{ $json.text.includes("search") }}` | `"search" in data["text"]` |
| `{{ $json.text.length }}` | `len(data["text"])` |

### Template Strings

| N8N | Python |
|-----|--------|
| `{{ "Hello " + $json.name }}` | `f"Hello {data['name']}"` |
| `` {{ `Order #${$json.id}` }} `` | `f"Order #{data['id']}"` |

---

## Number Functions

| N8N | Python |
|-----|--------|
| `{{ Math.round($json.value) }}` | `round(data["value"])` |
| `{{ Math.floor($json.value) }}` | `int(data["value"])` |
| `{{ Math.ceil($json.value) }}` | `import math; math.ceil(data["value"])` |
| `{{ Math.abs($json.value) }}` | `abs(data["value"])` |
| `{{ Math.max(1, 2, 3) }}` | `max(1, 2, 3)` |
| `{{ Math.min(1, 2, 3) }}` | `min(1, 2, 3)` |
| `{{ Number($json.text) }}` | `float(data["text"])` or `int(data["text"])` |
| `{{ $json.price.toFixed(2) }}` | `f"{data['price']:.2f}"` |

---

## Array Functions

| N8N | Python |
|-----|--------|
| `{{ $json.items.length }}` | `len(data["items"])` |
| `{{ $json.items[0] }}` | `data["items"][0]` |
| `{{ $json.items.at(-1) }}` | `data["items"][-1]` |
| `{{ $json.items.map(i => i.name) }}` | `[i["name"] for i in data["items"]]` |
| `{{ $json.items.filter(i => i.active) }}` | `[i for i in data["items"] if i["active"]]` |
| `{{ $json.items.find(i => i.id === 1) }}` | `next((i for i in data["items"] if i["id"] == 1), None)` |
| `{{ $json.items.some(i => i.active) }}` | `any(i["active"] for i in data["items"])` |
| `{{ $json.items.every(i => i.valid) }}` | `all(i["valid"] for i in data["items"])` |
| `{{ $json.items.includes("value") }}` | `"value" in data["items"]` |
| `{{ $json.items.concat(other) }}` | `data["items"] + other` |
| `{{ $json.items.reverse() }}` | `data["items"][::-1]` |
| `{{ $json.items.sort() }}` | `sorted(data["items"])` |

### Array Reduce

```javascript
// N8N
{{ $json.items.reduce((sum, i) => sum + i.value, 0) }}

// Python
sum(i["value"] for i in data["items"])
```

---

## Object Functions

| N8N | Python |
|-----|--------|
| `{{ Object.keys($json) }}` | `list(data.keys())` |
| `{{ Object.values($json) }}` | `list(data.values())` |
| `{{ Object.entries($json) }}` | `list(data.items())` |
| `{{ {...$json, newField: "value"} }}` | `{**data, "newField": "value"}` |
| `{{ $json.field ?? "default" }}` | `data.get("field", "default")` |
| `{{ $json.field?.nested }}` | `data.get("field", {}).get("nested")` |

---

## Conditional Expressions

| N8N | Python |
|-----|--------|
| `{{ $json.active ? "Yes" : "No" }}` | `"Yes" if data["active"] else "No"` |
| `{{ $json.value ?? "default" }}` | `data.get("value", "default")` |
| `{{ $json.value \|\| "fallback" }}` | `data.get("value") or "fallback"` |

---

## Type Checking

| N8N | Python |
|-----|--------|
| `{{ typeof $json.field }}` | `type(data["field"]).__name__` |
| `{{ Array.isArray($json.items) }}` | `isinstance(data["items"], list)` |
| `{{ $json.field === undefined }}` | `"field" not in data` |
| `{{ $json.field === null }}` | `data["field"] is None` |

---

## JSON Functions

| N8N | Python |
|-----|--------|
| `{{ JSON.stringify($json) }}` | `json.dumps(data)` |
| `{{ JSON.parse($json.text) }}` | `json.loads(data["text"])` |

**Required imports:**
```python
import json
```

---

## Complex Expression Examples

### Conditional Data Transformation
```javascript
// N8N
{{ $json.items.filter(i => i.status === "active").map(i => ({
    id: i.id,
    name: i.name.toUpperCase(),
    total: i.quantity * i.price
})) }}

// Python
[
    {
        "id": i["id"],
        "name": i["name"].upper(),
        "total": i["quantity"] * i["price"]
    }
    for i in data["items"]
    if i["status"] == "active"
]
```

### Nested Data Access with Defaults
```javascript
// N8N
{{ $json.customer?.address?.city ?? "Unknown" }}

// Python
data.get("customer", {}).get("address", {}).get("city", "Unknown")
```

### Building Dynamic Objects
```javascript
// N8N
{{
  {
    ...$json,
    processedAt: $now.toISO(),
    status: $json.amount > 100 ? "large" : "small"
  }
}}

// Python
{
    **data,
    "processedAt": datetime.now().isoformat(),
    "status": "large" if data["amount"] > 100 else "small"
}
```

---

## Notes

- Always add necessary imports at the top of the file
- Handle potential `KeyError` with `.get()` for optional fields
- N8N's loose typing may require explicit type conversion in Python
- Test expressions with sample data before deployment
