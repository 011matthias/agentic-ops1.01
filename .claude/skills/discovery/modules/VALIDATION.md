# Spec Validation Mode

Validates spec field/parameter assumptions against real API data before building. Catches wrong field names, missing fields, and incorrect enum values early — before implementation starts.

## Command

```
/discovery --spec workspace/clients/{client}/specs/2-build/a1-invoicing-automation.md --validate-assumptions
```

## Process

1. **Read spec** — load the full spec file
2. **Extract field references** — find all field names mentioned in:
   - Step details (field mappings, API parameters)
   - Data model tables
   - API reference sections
3. **Group by system** — categorize fields by which API they belong to (Airtable, Upsales, Fortnox, etc.)
4. **Generate validation script** — fetch one sample record from each system and check each field
5. **Run** — `uv run` the script
6. **Report** — list which fields exist, which are missing, and which have unexpected values

## Scope

- ✅ Check fields exist on sample records (read-only GET)
- ✅ Check select/enum option values match what the spec expects
- ❌ No write tests — no POST/PUT/DELETE to any system

## Generated Script Pattern

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx", "python-dotenv"]
# ///

"""
Spec Validation: {spec_name}
Checks that field references in spec match real API data.
Run: uv run workspace/clients/{client}/context/discovery/{YYYY-MM-DD}-validate-{spec-slug}.py
"""

import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv("workspace/clients/{client}/automations/.env")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Fields extracted from the spec — edit these to match what the spec references
AIRTABLE_TABLE = "contracten of locaties"
AIRTABLE_FIELDS_TO_CHECK = [
    "Locationnaam", "Leveringstatus", "Leveringstype", "PO-nummer", "Land",
]
EXPECTED_LEVERINGSTYPE_OPTIONS = ["Startlevering", "Herlevering", "Extra bestelling"]


def main():
    results = {"validated": [], "issues": []}

    client = httpx.Client(
        headers={"Authorization": f"Bearer {AIRTABLE_API_KEY}"},
        timeout=30.0,
    )

    # --- Airtable: check field existence via Metadata API ---
    meta_url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
    tables = client.get(meta_url).raise_for_status().json()["tables"]
    target = next((t for t in tables if t["name"] == AIRTABLE_TABLE), None)

    if not target:
        results["issues"].append(f"✗ Airtable table not found: '{AIRTABLE_TABLE}'")
    else:
        actual_fields = {f["name"]: f for f in target["fields"]}

        for field in AIRTABLE_FIELDS_TO_CHECK:
            if field in actual_fields:
                results["validated"].append(f"✓ Field exists: {field} ({actual_fields[field]['type']})")
            else:
                # Check for close matches (e.g. different spacing/hyphen)
                close = [n for n in actual_fields if n.lower().replace("-", " ") == field.lower().replace("-", " ")]
                hint = f" — did you mean '{close[0]}'?" if close else ""
                results["issues"].append(f"✗ MISSING field: '{field}'{hint}")

        # Check enum options
        if "Leveringstype" in actual_fields:
            actual_options = [
                c["name"] for c in actual_fields["Leveringstype"].get("options", {}).get("choices", [])
            ]
            missing_opts = [o for o in EXPECTED_LEVERINGSTYPE_OPTIONS if o not in actual_options]
            if missing_opts:
                results["issues"].append(
                    f"✗ Leveringstype missing options: {missing_opts}\n"
                    f"  Actual options: {actual_options}"
                )
            else:
                results["validated"].append(f"✓ Leveringstype options match: {actual_options}")

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

## Output

```
=== Spec Validation: a1-invoicing-automation ===

✓ Field exists: Locationnaam (text)
✓ Field exists: Leveringstatus (singleSelect)
✗ MISSING field: 'PO-nummer' — did you mean 'PO nummer'?
✓ Field exists: Land (text)
✓ Leveringstype options match: ['Startlevering', 'Herlevering', 'Extra bestelling']

Issues found: 1
→ Fix spec field reference: "PO-nummer" → "PO nummer" (no hyphen)
```

## After Validation

- For each issue found: flag it in the conversation with the `⚠️ SPEC ASSUMPTION INCORRECT` format from [ANSWER-INTEGRATION.md](ANSWER-INTEGRATION.md)
- Ask user to confirm fixes before editing the spec
- Re-run validation after fixes to confirm clean
