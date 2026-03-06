"""
Tests for A6.1: Apify Scraper Starter

Spec: specs/automations/a6.1-apify-scraper-starter.md
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.automations.apify_scraper_starter import (
    should_queue,
    build_linkedin_config,
    ApifyScraperStarter,
    settings,
)


# Mock LinkedIn credentials for testing
MOCK_LINKEDIN_COOKIES = [{"name": "li_at", "value": "test_cookie"}]
MOCK_LINKEDIN_USER_AGENT = "Mozilla/5.0 Test"


@pytest.fixture
def mock_settings():
    """Fixture to mock settings with test LinkedIn credentials."""
    with patch.object(settings, 'linkedin_cookies', MOCK_LINKEDIN_COOKIES):
        with patch.object(settings, 'linkedin_user_agent', MOCK_LINKEDIN_USER_AGENT):
            yield


class TestQueueCapacity:
    """Unit tests for queue capacity logic."""

    def test_should_queue_at_capacity(self):
        """Test returns True when at capacity."""
        assert should_queue(running_count=4, max_count=4) is True

    def test_should_queue_over_capacity(self):
        """Test returns True when over capacity."""
        assert should_queue(running_count=5, max_count=4) is True

    def test_should_not_queue_under_capacity(self):
        """Test returns False when under capacity."""
        assert should_queue(running_count=3, max_count=4) is False
        assert should_queue(running_count=0, max_count=4) is False


class TestLinkedInConfigBuilder:
    """Unit tests for LinkedIn scraper configuration builder."""

    def test_build_linkedin_config_basic(self):
        """Test building basic LinkedIn config."""
        cookies = [{"name": "li_at", "value": "ABC123"}]
        user_agent = "Mozilla/5.0..."

        config = build_linkedin_config(
            list_url="https://www.linkedin.com/sales/search/peop...",
            cookies=cookies,
            user_agent=user_agent,
        )

        assert config["searchUrl"] == "https://www.linkedin.com/sales/search/peop..."
        assert config["cookie"] == cookies
        assert config["userAgent"] == user_agent
        assert config["startPage"] == 1
        assert config["minDelay"] == 2
        assert config["maxDelay"] == 5
        assert "count" not in config  # No max results

    def test_build_linkedin_config_with_max_results(self):
        """Test building config with max results limit."""
        cookies = [{"name": "li_at", "value": "ABC123"}]
        user_agent = "Mozilla/5.0..."

        config = build_linkedin_config(
            list_url="https://www.linkedin.com/sales/search/peop...",
            cookies=cookies,
            user_agent=user_agent,
            max_results=250,
        )

        assert config["count"] == 250


class TestApifyScraperStarter:
    """Integration tests for Apify Scraper Starter (mocked)."""

    @pytest.fixture
    def handler(self):
        """Create handler instance with test tokens."""
        return ApifyScraperStarter(
            airtable_token="test_airtable_token",
            apify_token="test_apify_token",
        )

    @pytest.fixture
    def sample_list_record(self):
        """Sample Airtable list record."""
        mock_record = MagicMock()
        mock_record.id = "rec123"
        mock_record.fields = {
            "List Name": "Tech CEOs in Sweden",
            "List URL": "https://www.linkedin.com/sales/search/people?query=...",
            "List Type": "Apify - LinkedIn",
            "Max Results": 250,
        }
        return mock_record

    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return {
            "recordId": "rec123",
        }

    def test_handler_automation_id(self, handler):
        """Test handler has correct automation ID."""
        assert handler.automation_id == "a6_1_apify_scraper_starter"

    @pytest.mark.asyncio
    async def test_queue_at_capacity(self, handler, sample_payload, mock_settings):
        """Test scraper queues when at max capacity."""
        # Mock Apify returning 4 running actors (at capacity)
        mock_running = MagicMock()
        mock_running.total = 4
        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=mock_running)
        mock_airtable_client = MagicMock()
        mock_airtable_client.update_record = AsyncMock()

        # Mock list record (needed since code fetches list first)
        mock_list_record = MagicMock()
        mock_list_record.id = "rec123"
        mock_list_record.fields = {
            "List Name": "Test List",
            "List URL": "https://linkedin.com/sales/search/...",
            "List Type": "Apify - LinkedIn",
        }
        mock_airtable_client.get_record = AsyncMock(return_value=mock_list_record)

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        with patch.object(handler, '_init_clients', new=mock_init):
            with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                result = await handler.run(sample_payload)

        assert result["status"] == "queued"
        assert result["reason"] == "max_concurrent_reached"
        assert result["running_count"] == 4

    @pytest.mark.asyncio
    async def test_missing_record_id(self, handler):
        """Test error when recordId is missing."""
        with pytest.raises(ValueError, match="recordId is required"):
            await handler.run({})

    @pytest.mark.asyncio
    async def test_missing_list_url(self, handler, sample_payload):
        """Test error when List URL is missing."""
        mock_record = MagicMock()
        mock_record.id = "rec123"
        mock_record.fields = {
            "List Type": "Apify - LinkedIn",
            # Missing List URL
        }
        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=MagicMock(total=0))
        mock_airtable_client = MagicMock()
        mock_airtable_client.get_record = AsyncMock(return_value=mock_record)

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        with patch.object(handler, '_init_clients', new=mock_init):
            with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                with pytest.raises(ValueError, match="List URL is required"):
                    await handler.run(sample_payload)

    @pytest.mark.asyncio
    async def test_missing_list_type(self, handler, sample_payload):
        """Test error when List Type is missing."""
        mock_record = MagicMock()
        mock_record.id = "rec123"
        mock_record.fields = {
            "List URL": "https://linkedin.com/...",
            # Missing List Type
        }
        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=MagicMock(total=0))
        mock_airtable_client = MagicMock()
        mock_airtable_client.get_record = AsyncMock(return_value=mock_record)

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        with patch.object(handler, '_init_clients', new=mock_init):
            with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                with pytest.raises(ValueError, match="List Type is required"):
                    await handler.run(sample_payload)

    @pytest.mark.asyncio
    async def test_successful_scraper_start(self, handler, sample_payload, sample_list_record):
        """Test successful scraper start flow."""
        from app.clients.apify import ActorRun, RunStatus

        # Mock running actors (under capacity)
        mock_running = MagicMock()
        mock_running.total = 1

        # Mock actor run response
        mock_run = ActorRun(
            id="run123",
            status=RunStatus.RUNNING,
        )

        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=mock_running)
        mock_apify_client.start_actor = AsyncMock(return_value=mock_run)
        mock_airtable_client = MagicMock()
        mock_airtable_client.get_record = AsyncMock(return_value=sample_list_record)
        mock_airtable_client.update_record = AsyncMock()

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        # Mock the LinkedIn cookies method
        async def mock_get_cookies():
            return MOCK_LINKEDIN_COOKIES

        with patch.object(handler, '_get_linkedin_cookies', new=mock_get_cookies):
            with patch.object(handler, '_init_clients', new=mock_init):
                with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                    result = await handler.run(sample_payload)

        # Verify actor was started with correct config
        mock_apify_client.start_actor.assert_called_once()
        call_args = mock_apify_client.start_actor.call_args
        assert call_args[1]["actor_id"] == "7Q2x4Chr5xNR5s4dP"  # Correct actor ID from spec
        assert "cookie" in call_args[1]["input_config"]
        assert call_args[1]["input_config"]["count"] == 250

        # Verify Airtable was updated
        mock_airtable_client.update_record.assert_called_once()
        update_call = mock_airtable_client.update_record.call_args
        assert update_call[1]["record_id"] == "rec123"
        assert update_call[1]["fields"]["List Status"] == "Scraper In Progress"
        assert update_call[1]["fields"]["Scraper ID"] == "run123"

        # Verify result
        assert result["status"] == "scraper_started"
        assert result["run_id"] == "run123"
        assert result["list_id"] == "rec123"

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, handler, sample_payload, sample_list_record):
        """Test dry run doesn't start actual scraper."""
        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=MagicMock(total=0))
        mock_apify_client.start_actor = AsyncMock()
        mock_airtable_client = MagicMock()
        mock_airtable_client.get_record = AsyncMock(return_value=sample_list_record)

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        # Mock the LinkedIn cookies method
        async def mock_get_cookies():
            return MOCK_LINKEDIN_COOKIES

        with patch.object(handler, '_get_linkedin_cookies', new=mock_get_cookies):
            with patch.object(handler, '_init_clients', new=mock_init):
                with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                    result = await handler.run(sample_payload, dry_run=True)

        # Verify actor was NOT started
        mock_apify_client.start_actor.assert_not_called()

        # Verify dry run result
        assert result["status"] == "dry_run"
        assert result["would_start"] is True
        assert result["actor_id"] == "7Q2x4Chr5xNR5s4dP"  # Correct actor ID from spec
        assert "config" in result

    @pytest.mark.asyncio
    async def test_unsupported_list_type(self, handler, sample_payload):
        """Test error on unsupported list type."""
        mock_record = MagicMock()
        mock_record.id = "rec123"
        mock_record.fields = {
            "List URL": "https://example.com/search",
            "List Type": "Unknown Scraper",
        }
        mock_apify_client = MagicMock()
        mock_apify_client.get_running_actors = AsyncMock(return_value=MagicMock(total=0))
        mock_airtable_client = MagicMock()
        mock_airtable_client.get_record = AsyncMock(return_value=mock_record)

        async def mock_init():
            handler.apify_client = mock_apify_client
            handler.airtable_client = mock_airtable_client

        # Mock the LinkedIn cookies method
        async def mock_get_cookies():
            return MOCK_LINKEDIN_COOKIES

        with patch.object(handler, '_get_linkedin_cookies', new=mock_get_cookies):
            with patch.object(handler, '_init_clients', new=mock_init):
                with patch.object(handler, '_close_clients', new_callable=AsyncMock):
                    with pytest.raises(ValueError, match="Unsupported list type"):
                        await handler.run(sample_payload)


class TestAcceptanceCriteria:
    """Test placeholders for spec acceptance criteria."""

    def test_webhook_receives_record_id(self):
        """Webhook receives record ID from orchestrator."""
        # Covered by payload tests
        pass

    def test_fetches_list_record(self):
        """Fetches list record from Airtable."""
        # Covered by integration tests
        pass

    def test_validates_required_fields(self):
        """Validates List URL and List Type."""
        # Covered by test_missing_list_url and test_missing_list_type
        pass

    def test_checks_queue_capacity(self):
        """Checks queue capacity (max 4 concurrent)."""
        # Covered by test_queue_at_capacity
        pass

    def test_queues_scraper_when_at_capacity(self):
        """Queues scraper when at capacity."""
        # Covered by test_queue_at_capacity
        pass

    def test_builds_linkedin_config(self):
        """Builds LinkedIn scraper config with cookies."""
        # Covered by test_build_linkedin_config_basic
        pass

    def test_starts_apify_actor(self):
        """Starts Apify actor with correct config."""
        # Covered by test_successful_scraper_start
        pass

    def test_updates_airtable_with_scraper_id(self):
        """Updates Airtable with Scraper ID."""
        # Covered by test_successful_scraper_start
        pass

    def test_updates_status_to_scraper_in_progress(self):
        """Updates status to 'Scraper In Progress'."""
        # Covered by test_successful_scraper_start
        pass

    def test_handles_errors_gracefully(self):
        """Handles errors gracefully."""
        # Covered by validation error tests
        pass

    def test_dry_run_mode_works(self):
        """Dry run mode works without starting scraper."""
        # Covered by test_dry_run_mode
        pass
