"""
Example automation demonstrating the base class pattern.

Spec: specs/example-automation.md
Trigger: Manual via Trigger.dev dashboard

This is a template - copy and modify for real automations.
"""

import sys
import json
import logging

from .base import BaseAutomation

logger = logging.getLogger(__name__)


class ExampleAutomation(BaseAutomation):
    """
    Example automation that demonstrates the pattern.

    In a real automation, this would:
    1. Connect to source system (e.g., CRM)
    2. Fetch relevant data
    3. Transform for destination
    4. Send to destination system (e.g., ERP)
    5. Log/notify on completion
    """

    automation_id = "example"

    def __init__(self):
        self.source_client = None
        self.dest_client = None

    def initialize(self) -> None:
        logger.info("Initializing example automation")

    def fetch_data(self) -> list[dict]:
        logger.info("Fetching example data")
        return [
            {"id": 1, "name": "Item A", "value": 100},
            {"id": 2, "name": "Item B", "value": 200},
            {"id": 3, "name": "Item C", "value": 300},
        ]

    def transform(self, data: list[dict]) -> list[dict]:
        logger.info(f"Transforming {len(data)} items")
        transformed = []
        for item in data:
            transformed.append({
                "external_id": str(item["id"]),
                "display_name": item["name"].upper(),
                "amount": item["value"] * 1.25,
            })
        return transformed

    def execute(self, data: list[dict]) -> dict:
        logger.info(f"Executing on {len(data)} items")
        return {
            "created": len(data),
            "items": [{"id": f"new_{d['external_id']}", **d} for d in data],
        }

    def finalize(self, result: dict) -> None:
        logger.info(f"Example automation completed: {result['created']} items created")


if __name__ == "__main__":
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    automation = ExampleAutomation()
    result = automation.run(
        dry_run=payload.get("dry_run", False),
        limit=payload.get("limit"),
        record_ids=payload.get("record_ids"),
    )
    print(json.dumps(result))
