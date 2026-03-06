"""
Tests for automations.
"""

import pytest
from python.automations.example import ExampleAutomation


def test_example_automation_dry_run():
    """Test example automation in dry run mode."""
    automation = ExampleAutomation()
    result = automation.run(trigger="test", dry_run=True)

    assert result["dry_run"] is True
    assert "would_process" in result


def test_example_automation_transform():
    """Test example automation transformation logic."""
    automation = ExampleAutomation()

    input_data = [
        {"id": 1, "name": "Test", "value": 100}
    ]

    transformed = automation.transform(input_data)

    assert len(transformed) == 1
    assert transformed[0]["external_id"] == "1"
    assert transformed[0]["display_name"] == "TEST"
    assert transformed[0]["amount"] == 125.0
