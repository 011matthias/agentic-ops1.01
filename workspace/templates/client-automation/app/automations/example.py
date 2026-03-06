"""
Example automation demonstrating the base class pattern.

Spec: specs/example-automation.md
Trigger: Manual or POST /run/example

This is a template - copy and modify for real automations.
"""

from typing import Any
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
        """Setup API clients and validate configuration."""
        logger.info("Initializing example automation")
        # In real automation:
        # self.source_client = SourceAPIClient()
        # self.dest_client = DestinationAPIClient()

    def fetch_data(self) -> list[dict]:
        """Fetch data from source system."""
        logger.info("Fetching example data")
        # In real automation:
        # return self.source_client.get_items()
        return [
            {"id": 1, "name": "Item A", "value": 100},
            {"id": 2, "name": "Item B", "value": 200},
            {"id": 3, "name": "Item C", "value": 300},
        ]

    def transform(self, data: list[dict]) -> list[dict]:
        """Transform data for destination format."""
        logger.info(f"Transforming {len(data)} items")
        transformed = []
        for item in data:
            transformed.append({
                "external_id": str(item["id"]),
                "display_name": item["name"].upper(),
                "amount": item["value"] * 1.25,  # Add 25% markup
            })
        return transformed

    def execute(self, data: list[dict]) -> dict:
        """Send transformed data to destination."""
        logger.info(f"Executing on {len(data)} items")
        # In real automation:
        # results = []
        # for item in data:
        #     result = self.dest_client.create_item(item)
        #     results.append(result)
        # return {"created": len(results), "items": results}

        # Simulate successful creation
        return {
            "created": len(data),
            "items": [{"id": f"new_{d['external_id']}", **d} for d in data]
        }

    def finalize(self, result: dict) -> None:
        """Log completion and send notifications."""
        logger.info(f"Example automation completed: {result['created']} items created")
        # In real automation:
        # send_slack_notification(f"Created {result['created']} items")


# Allow running directly for testing
if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    automation = ExampleAutomation()
    result = automation.run(trigger="manual", dry_run=dry_run)
    print(f"Result: {result}")
