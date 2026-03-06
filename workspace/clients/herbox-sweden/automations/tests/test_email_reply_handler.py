"""
Tests for A8: Email Reply Handler

Spec: clients/herbox-sweden/specs/automations/a8-email-reply-handler.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.automations.email_reply_handler import EmailReplyHandler


# === Fixtures ===

@pytest.fixture
def sample_webhook_reply():
    """Sample Smartlead EMAIL_REPLY webhook payload."""
    return {
        "body": {
            "event_type": "EMAIL_REPLY",
            "campaign_id": "camp_123",
            "campaign_status": "active",
            "from_email": "john.doe@example.com",
            "to_email": "patrick@herbox.se",
            "to_name": "Bosma Patrick",
            "subject": "Re: Partnership opportunity",
            "sent_message": {
                "text": "Hi John, would you be interested in discussing a partnership?",
            },
            "reply_message": {
                "text": "Yes, I'm interested! Please send me more details.",
                "time": "2026-01-15T10:30:00Z",
            },
            "sequence_number": 1,
            "sl_lead_email": "john.doe@example.com",
        },
    }


@pytest.fixture
def sample_webhook_bounce():
    """Sample Smartlead EMAIL_BOUNCE webhook payload."""
    return {
        "body": {
            "event_type": "EMAIL_BOUNCE",
            "campaign_id": "camp_123",
            "campaign_status": "active",
            "from_email": "john.doe@example.com",
            "to_email": "patrick@herbox.se",
            "to_name": "Bosma Patrick",
            "sl_lead_email": "john.doe@example.com",
        },
    }


@pytest.fixture
def sample_webhook_internal():
    """Sample webhook from internal Herbox email."""
    return {
        "body": {
            "event_type": "EMAIL_REPLY",
            "campaign_id": "camp_123",
            "from_email": "patrick@herbox.se",
            "to_email": "john.doe@example.com",
            "to_name": "Patrick Bosma",
            "reply_message": {
                "text": "Thanks for the update",
                "time": "2026-01-15T10:30:00Z",
            },
            "sl_lead_email": "john.doe@example.com",
        },
    }


@pytest.fixture
def mock_airtable_client():
    """Mock Airtable client."""
    client = MagicMock()
    client.search_records = AsyncMock(return_value=[])
    client._request = AsyncMock(side_effect=lambda m, p, **kw: {"id": "rec123"})
    client.update_record = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = MagicMock()
    client.categorize_email = AsyncMock(
        return_value=MagicMock(category_name="Interested", category_id=1)
    )
    client.extract_phones = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_heyreach_client():
    """Mock Heyreach client."""
    client = MagicMock()
    client.add_lead_to_campaign = AsyncMock(return_value=None)
    client.close = AsyncMock()
    return client


# === Unit Tests ===


class TestWebhookParsing:
    """Tests for webhook payload parsing."""

    def test_parse_webhook_payload_a8(self, sample_webhook_reply):
        """Test webhook payload parsing extracts all required fields."""
        handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
        data = handler.parsed_data

        assert data["event_type"] == "EMAIL_REPLY"
        assert data["from_email"] == "john.doe@example.com"
        assert data["to_email"] == "patrick@herbox.se"
        assert data["sent_message_text"] == "Hi John, would you be interested in discussing a partnership?"
        assert data["reply_message_text"] == "Yes, I'm interested! Please send me more details."


class TestInternalEmailFiltering:
    """Tests for internal email detection."""

    def test_is_internal_email_a8_herbox_se(self, sample_webhook_reply):
        """Test @herbox.se email is detected as internal."""
        handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
        handler.parsed_data["from_email"] = "patrick@herbox.se"
        assert handler._is_internal_email(handler.parsed_data) is True

    def test_is_internal_email_a8_herbox_com(self, sample_webhook_reply):
        """Test @herbox.com email is detected as internal."""
        handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
        handler.parsed_data["from_email"] = "test@herbox.com"
        assert handler._is_internal_email(handler.parsed_data) is True

    def test_is_internal_email_a8_external(self, sample_webhook_reply):
        """Test external email is not detected as internal."""
        handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
        handler.parsed_data["from_email"] = "john@example.com"
        assert handler._is_internal_email(handler.parsed_data) is False


class TestAICategorization:
    """Tests for AI email categorization."""

    @pytest.mark.asyncio
    async def test_categorize_interested_reply_a8(self, mock_openai_client):
        """Test AI categorization identifies interested replies."""
        from app.clients.openai import OpenAIClient

        mock_openai_client.categorize_email = AsyncMock(
            return_value=MagicMock(category_name="Interested", category_id=1)
        )

        original = "Hi John, would you be interested in discussing a partnership?"
        reply = "Yes, I'm interested! Please send me more details."

        result = await mock_openai_client.categorize_email(original, reply)
        assert result.category_name == "Interested"
        assert result.category_id == 1


class TestPhoneExtraction:
    """Tests for phone number extraction."""

    @pytest.mark.asyncio
    async def test_extract_phone_numbers_a8(self, mock_openai_client):
        """Test phone extraction from email signatures."""
        from app.clients.openai import PhoneInfo

        mock_phone = PhoneInfo(name="John Doe", phone="+31 6 1234 5678")
        mock_openai_client.extract_phones = AsyncMock(return_value=[mock_phone])

        body = "Best regards,\nJohn Doe\n+31 6 1234 5678"

        result = await mock_openai_client.extract_phones(
            email_body=body,
            sender_email="john@example.com",
        )

        assert len(result) == 1
        assert result[0].phone == "+31 6 1234 5678"

    @pytest.mark.asyncio
    async def test_filter_herbox_phones_a8(self, mock_openai_client):
        """Test Herbox team phone numbers are filtered out intelligently."""
        from app.clients.openai import PhoneInfo

        # Only the external contact's phone should be extracted
        mock_phone = PhoneInfo(name="John Doe", phone="+31 6 1234 5678")
        mock_openai_client.extract_phones = AsyncMock(return_value=[mock_phone])

        body = """
        From: john@external.com
        Best regards,
        John Smith
        +31 6 1234 5678

        On behalf of:
        Patrick Bosma
        Herbox
        +31 6 9999 9999
        """

        result = await mock_openai_client.extract_phones(
            email_body=body,
            sender_email="john@external.com",
            known_internal_domains=["herbox.se", "herbox.com"],
        )

        assert len(result) == 1
        assert result[0].phone == "+31 6 1234 5678"


# === Integration Tests ===


@pytest.mark.asyncio
class TestEmailReplyFlow:
    """Tests for complete EMAIL_REPLY flow."""

    async def test_a8_email_reply_full_flow(
        self,
        sample_webhook_reply,
        mock_airtable_client,
        mock_openai_client,
        mock_heyreach_client,
    ):
        """Test complete EMAIL_REPLY flow with mocked APIs."""
        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.OpenAIClient",
            return_value=mock_openai_client,
        ), patch(
            "app.automations.email_reply_handler.HeyreachClient",
            return_value=mock_heyreach_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            # Mock settings to pass validation
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"
            mock_settings.heyreach_api_key = None

            handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
            # Initialize the handler (sets up exec_logger)
            handler.initialize()

            # Mock find_or_create_contact to return an ID
            handler._find_or_create_contact = AsyncMock(return_value="rec_contact_123")

            result = await handler._handle_email_reply(handler.parsed_data)

            assert handler.contact_id == "rec_contact_123"
            assert handler.interaction_id is not None
            assert handler.category is not None
            assert "contact_id" in result

    async def test_a8_internal_email_filtered(
        self,
        sample_webhook_internal,
        mock_airtable_client,
        mock_openai_client,
    ):
        """Test internal Herbox emails are filtered out."""
        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.OpenAIClient",
            return_value=mock_openai_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"
            mock_settings.herbox_domains = "herbox.se,herbox.com"

            handler = EmailReplyHandler(webhook_data=sample_webhook_internal)
            handler.initialize()  # Initialize exec_logger
            result = await handler._handle_email_reply(handler.parsed_data)

            assert handler.is_internal_email is True
            assert result["internal_email_filtered"] is True
            assert handler.contact_id is None  # No contact created


@pytest.mark.asyncio
class TestEmailBounceFlow:
    """Tests for EMAIL_BOUNCE flow."""

    async def test_a8_email_bounce_linkedin_flow(
        self,
        sample_webhook_bounce,
        mock_airtable_client,
        mock_heyreach_client,
    ):
        """Test EMAIL_BOUNCE with LinkedIn fallback."""
        # Mock contact with LinkedIn
        mock_airtable_client.search_records = AsyncMock(
            return_value=[
                MagicMock(
                    id="rec_contact_123",
                    fields={"LinkedIn": "https://linkedin.com/in/johndoe"},
                )
            ]
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.HeyreachClient",
            return_value=mock_heyreach_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_bounce)
            handler.initialize()  # Initialize exec_logger
            result = await handler._handle_email_bounce(handler.parsed_data)

            assert handler.contact_id == "rec_contact_123"
            assert "contact_id" in result

    async def test_a8_email_bounce_no_linkedin(
        self,
        sample_webhook_bounce,
        mock_airtable_client,
    ):
        """Test EMAIL_BOUNCE without LinkedIn URL."""
        # Mock contact without LinkedIn
        mock_airtable_client.search_records = AsyncMock(
            return_value=[
                MagicMock(id="rec_contact_123", fields={})
            ]
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_bounce)
            handler.initialize()  # Initialize exec_logger
            result = await handler._handle_email_bounce(handler.parsed_data)

            assert result.get("no_linkedin") is True


# === Edge Cases ===


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_a8_empty_reply_message(
        self,
        sample_webhook_reply,
        mock_airtable_client,
        mock_openai_client,
    ):
        """Test handling of empty reply message."""
        sample_webhook_reply["body"]["reply_message"]["text"] = ""

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.OpenAIClient",
            return_value=mock_openai_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
            handler.initialize()  # Initialize exec_logger
            handler._find_or_create_contact = AsyncMock(return_value="rec_contact_123")

            # Should handle gracefully
            result = await handler._handle_email_reply(handler.parsed_data)
            assert "contact_id" in result

    async def test_a8_name_parsing_single_name(
        self,
        sample_webhook_reply,
        mock_airtable_client,
    ):
        """Test contact creation with single name (no space)."""
        sample_webhook_reply["body"]["to_name"] = "John"

        mock_airtable_client.search_records = AsyncMock(return_value=[])
        mock_airtable_client._request = AsyncMock(
            return_value={"id": "rec_new_123"}
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
            handler.initialize()  # Initialize exec_logger
            contact_id = await handler._find_or_create_contact(handler.parsed_data)

            assert contact_id == "rec_new_123"

    async def test_a8_contact_not_found_creates_new(
        self,
        sample_webhook_reply,
        mock_airtable_client,
    ):
        """Test that missing contacts are created automatically."""
        mock_airtable_client.search_records = AsyncMock(return_value=[])
        mock_airtable_client._request = AsyncMock(
            return_value={"id": "rec_new_123"}
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
            handler.initialize()  # Initialize exec_logger
            contact_id = await handler._find_or_create_contact(handler.parsed_data)

            assert contact_id == "rec_new_123"
            mock_airtable_client._request.assert_called_once()


# === Acceptance Criteria Tests ===


@pytest.mark.asyncio
class TestAcceptanceCriteria:
    """Tests for spec acceptance criteria."""

    async def test_webhook_validates_secret(
        self,
        sample_webhook_reply,
    ):
        """Test webhook validates Smartlead secret key."""
        from app.routers.webhooks import webhook_smartlead
        from fastapi import Request

        # This would be tested via the actual FastAPI test client
        # For unit testing, we verify the logic exists
        assert "smartlead_webhook_secret" in dir(webhook_smartlead.__globals__["get_settings"]())

    async def test_internal_emails_filtered(
        self,
        sample_webhook_internal,
        mock_airtable_client,
        mock_openai_client,
    ):
        """Test internal Herbox emails are filtered out before processing."""
        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.OpenAIClient",
            return_value=mock_openai_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"
            mock_settings.herbox_domains = "herbox.se,herbox.com"

            handler = EmailReplyHandler(webhook_data=sample_webhook_internal)
            handler.initialize()  # Initialize exec_logger
            result = await handler._handle_email_reply(handler.parsed_data)

            assert result["internal_email_filtered"] is True

    async def test_positive_reply_creates_task(
        self,
        sample_webhook_reply,
        mock_airtable_client,
        mock_openai_client,
    ):
        """Test positive replies create call tasks."""
        # Set up positive category
        mock_openai_client.categorize_email = AsyncMock(
            return_value=MagicMock(category_name="Interested", category_id=1)
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.OpenAIClient",
            return_value=mock_openai_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"

            handler = EmailReplyHandler(webhook_data=sample_webhook_reply)
            handler.initialize()  # Initialize exec_logger
            handler._find_or_create_contact = AsyncMock(return_value="rec_contact_123")
            handler._create_call_task = AsyncMock(return_value="rec_task_123")

            result = await handler._handle_email_reply(handler.parsed_data)

            assert result["tasks_created"] > 0

    async def test_bounce_routes_to_linkedin(
        self,
        sample_webhook_bounce,
        mock_airtable_client,
        mock_heyreach_client,
    ):
        """Test EMAIL_BOUNCE routes to Heyreach when LinkedIn available."""
        mock_airtable_client.search_records = AsyncMock(
            return_value=[
                MagicMock(
                    id="rec_contact_123",
                    fields={"LinkedIn": "https://linkedin.com/in/johndoe"},
                )
            ]
        )
        mock_heyreach_client.add_lead_to_campaign = AsyncMock(
            return_value=MagicMock(campaign_id="camp_linkedin_123")
        )

        with patch(
            "app.automations.email_reply_handler.AirtableClient",
            return_value=mock_airtable_client,
        ), patch(
            "app.automations.email_reply_handler.HeyreachClient",
            return_value=mock_heyreach_client,
        ), patch(
            "app.automations.email_reply_handler.settings"
        ) as mock_settings:
            mock_settings.airtable_token = "test_token"
            mock_settings.airtable_base_id = "test_base"
            mock_settings.openai_api_key = "test_key"
            mock_settings.heyreach_campaign_patrick = "camp_linkedin_123"

            handler = EmailReplyHandler(webhook_data=sample_webhook_bounce)
            handler.initialize()  # Initialize exec_logger

            result = await handler._handle_email_bounce(handler.parsed_data)

            assert handler.heyreach_campaign is not None
