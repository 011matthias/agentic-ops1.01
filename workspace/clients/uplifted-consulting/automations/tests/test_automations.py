"""
Tests for Uplifted Consulting automations.
"""

import pytest
from python.automations.positive_reply_notifier import PositiveReplyNotifierAutomation


def test_positive_reply_notifier_fetch_data():
    """Test webhook data extraction."""
    webhook_data = {
        "preview_text": "Yes, I'm interested!",
        "from_email": "lead@example.com",
        "to_email": "sales@uplifted.com",
        "to_name": "Jane Doe",
        "subject": "Re: Our services",
        "campaign_name": "Q1 Outreach",
        "campaign_id": 123,
        "ui_master_inbox_link": "https://app.smartlead.ai/inbox/123",
    }

    automation = PositiveReplyNotifierAutomation(webhook_data=webhook_data)
    data = automation.fetch_data()

    assert data["reply_text"] == "Yes, I'm interested!"
    assert data["from_email"] == "lead@example.com"
    assert data["to_name"] == "Jane Doe"
    assert data["campaign_name"] == "Q1 Outreach"
    assert data["inbox_link"] == "https://app.smartlead.ai/inbox/123"


def test_positive_reply_notifier_empty_reply():
    """Test classification of empty reply text."""
    webhook_data = {
        "preview_text": "",
        "from_email": "lead@example.com",
    }

    automation = PositiveReplyNotifierAutomation(webhook_data=webhook_data)
    data = automation.fetch_data()
    result = automation.transform(data)

    assert result["classification"]["is_positive"] is False
    assert result["classification"]["confidence"] == 1.0
    assert "Empty" in result["classification"]["reasoning"]


def test_positive_reply_notifier_missing_fields():
    """Test handling of webhook data with missing fields."""
    automation = PositiveReplyNotifierAutomation(webhook_data={})
    data = automation.fetch_data()

    assert data["reply_text"] == ""
    assert data["from_email"] == ""
    assert data["to_name"] == "Unknown"
    assert data["campaign_name"] == "Unknown Campaign"
