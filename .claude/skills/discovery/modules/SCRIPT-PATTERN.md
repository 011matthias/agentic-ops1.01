# Script Pattern

All generated discovery scripts use PEP 723 inline dependencies and run with `uv run` — no venv setup required.

## Template

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "python-dotenv"]
# ///

"""
Discovery: {question being answered}
Client: {client name}
Run: uv run workspace/clients/{client}/context/discovery/{YYYY-MM-DD}-{slug}.py
"""

import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv("workspace/clients/{client}/automations/.env")

# Load relevant credentials
API_KEY = os.getenv("API_KEY_VAR_NAME")


def main():
    client = httpx.Client(
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30.0,
    )

    results = {}

    # Targeted API calls to answer the specific question
    # Always print the full raw response — assume nothing about structure
    response = client.get("https://api.example.com/endpoint")
    response.raise_for_status()
    data = response.json()

    results["question"] = "What does the API return for X?"
    results["raw_response"] = data        # Always include for inspection
    results["answer"] = "..."             # Distilled answer

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

## Core Rules

- **Always print raw API response** — Claude and the user both need to see what the API actually returns. Never filter prematurely.
- **PEP 723 inline deps** — declare all dependencies in the `# dependencies = [...]` block. `uv` installs them automatically.
- **Load .env from workspace root** — always use the path relative to workspace root: `load_dotenv("workspace/clients/{client}/automations/.env")`
- **Don't assume field names** — if unsure, fetch the full object and print everything
- **Try variants** — for filter/parameter discovery, try 2-3 candidate names in one script and show which returns data
- **ensure_ascii=False** — required for Dutch/non-ASCII field names in Airtable etc.

## Common Script Patterns

### Fetch one record and print all fields

```python
response = client.get(f"https://api.example.com/v1/resource/{record_id}")
data = response.json()
print(json.dumps(data, indent=2, ensure_ascii=False))
```

### Test multiple filter parameter names

```python
from datetime import datetime, timedelta, timezone

since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

variants = {
    "modDate":       f"modDate=gt:{since}",
    "modifiedSince": f"modifiedSince={since}",
    "updatedAt":     f"updatedAt=gt:{since}",
    "updatedAfter":  f"updatedAfter={since}",
}

results = {}
for name, param in variants.items():
    try:
        r = client.get(f"https://api.example.com/v1/orders?{param}")
        results[name] = {
            "status": r.status_code,
            "count": len(r.json().get("data", [])),
            "sample": r.json().get("data", [])[:1],
        }
    except Exception as e:
        results[name] = {"error": str(e)}
```

### Check cross-system reference fields

```python
# Fetch N most recent records and print specific reference fields
response = client.get("https://api.example.com/v1/orders?limit=3&sort=-createdAt")
orders = response.json()["data"]

reference_fields = ["YourOrderNumber", "ExternalReference", "OurReference", "YourReference"]
for order in orders:
    print(f"\nOrder {order['id']}:")
    for field in reference_fields:
        print(f"  {field}: {order.get(field, '<not present>')}")
```

### Test API schema via validation error

```python
# POST with known-bad data to see full field validation error (reveals all accepted fields)
try:
    r = client.post("https://api.example.com/v1/invoices", json={"__test__": True})
    print(json.dumps(r.json(), indent=2))
except httpx.HTTPStatusError as e:
    # Validation errors reveal accepted fields
    print(json.dumps(e.response.json(), indent=2))
```

### Fetch table/schema fields (e.g. Airtable)

For services with a dedicated schema/metadata API, fetch the field list directly rather than guessing from a sample record. Airtable is the most common case — field names are often in foreign languages and impossible to guess.

```python
# Airtable Metadata API — returns all fields with types and select options
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = "contracten of locaties"  # exact name

url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"
response = client.get(url)
response.raise_for_status()

tables = response.json()["tables"]
target = next((t for t in tables if t["name"] == TABLE_NAME), None)

if not target:
    print(json.dumps({"error": f"Table not found", "available": [t["name"] for t in tables]},
                     ensure_ascii=False))
else:
    fields = []
    for field in target["fields"]:
        info = {"name": field["name"], "type": field["type"]}
        if field["type"] in ("singleSelect", "multipleSelects"):
            info["options"] = [c["name"] for c in field.get("options", {}).get("choices", [])]
        fields.append(info)
    print(json.dumps({"table": TABLE_NAME, "fields": fields}, indent=2, ensure_ascii=False))
```

After running, format results as a markdown table for the spec:

```markdown
| Field Name | Type | Options / Notes |
|------------|------|-----------------|
| Locationnaam | text | |
| Leveringstatus | singleSelect | Gepland, Verstuurd, Geannuleerd |
| Leveringstype | singleSelect | Startlevering, Herlevering, Extra bestelling |
| Land | text | "Land" = Dutch for "Country" |
```

Add translation notes in the Notes column for non-English field names.

## Script File Naming

Save to: `workspace/clients/{client}/context/discovery/{YYYY-MM-DD}-{slug}.py`

Slug examples:
- `airtable-contracten-fields`
- `upsales-order-filter-param`
- `fortnox-upsales-reference-check`
- `teamleader-invoice-schema`

Create the `context/discovery/` directory if it doesn't exist:
```bash
mkdir -p workspace/clients/{client}/context/discovery
```

## Adding Dependencies

Add to the `# dependencies = [...]` block as needed:

| Need | Package |
|------|---------|
| HTTP client | `httpx` (always include) |
| Env loading | `python-dotenv` (always include) |
| OAuth2 | `httpx-auth` |
| Date parsing | `python-dateutil` |
| Rich output | `rich` (for tables) |
