"""
Tests for A6: List Building Orchestrator.

Spec: specs/automations/a6-list-building.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.automations.list_building_orchestrator import (
    ListBuildingOrchestrator,
    ListRecord,
    ListStatus,
    ListType,
    SubFlow,
    get_sub_flow,
    should_queue_scraper,
    build_apollo_config,
    build_sales_nav_config,
)


class TestRouting:
    """Tests for status routing logic."""

    def test_route_scraper_started(self):
        """Scraper Started routes to lead_sourcing."""
        assert get_sub_flow("Scraper Started") == SubFlow.LEAD_SOURCING

    def test_route_list_standardization(self):
        """List Standardization routes to standardization."""
        assert get_sub_flow("List Standardization") == SubFlow.STANDARDIZATION

    def test_route_enrichment_started(self):
        """Enrichment & Verification Started routes to enrichment."""
        assert get_sub_flow("Enrichment & Verification Started") == SubFlow.ENRICHMENT

    def test_route_list_cleaning(self):
        """List Cleaning Started routes to cleaning."""
        assert get_sub_flow("List Cleaning Started") == SubFlow.CLEANING

    def test_route_upload_to_sequencer(self):
        """Upload to Email Sequencer routes to upload."""
        assert get_sub_flow("Upload to Email Sequencer") == SubFlow.UPLOAD

    def test_route_unknown_status(self):
        """Unknown status returns None."""
        assert get_sub_flow("Unknown Status") is None
        assert get_sub_flow("") is None
        assert get_sub_flow("In Progress") is None


class TestQueueCapacity:
    """Tests for scraper queue capacity logic."""

    def test_should_not_queue_when_under_capacity(self):
        """Don't queue when under max capacity."""
        assert should_queue_scraper(running=0, max_allowed=4) is False
        assert should_queue_scraper(running=1, max_allowed=4) is False
        assert should_queue_scraper(running=3, max_allowed=4) is False

    def test_should_queue_at_capacity(self):
        """Queue when at max capacity."""
        assert should_queue_scraper(running=4, max_allowed=4) is True

    def test_should_queue_over_capacity(self):
        """Queue when over max capacity."""
        assert should_queue_scraper(running=5, max_allowed=4) is True
        assert should_queue_scraper(running=10, max_allowed=4) is True


class TestApolloConfig:
    """Tests for Apollo scraper configuration."""

    def test_build_apollo_config_basic(self):
        """Build basic Apollo config."""
        record = ListRecord(
            id="rec123",
            list_url="https://app.apollo.io/#/people?search=...",
        )

        config = build_apollo_config(record)

        assert config["getPersonalEmails"] is True
        assert config["getWorkEmails"] is True
        assert config["url"] == "https://app.apollo.io/#/people?search=..."

    def test_build_apollo_config_ignores_max_results(self):
        """Apollo config doesn't use max_results (only Sales Nav does)."""
        record = ListRecord(
            id="rec123",
            list_url="https://app.apollo.io/...",
            max_results=100,
        )

        config = build_apollo_config(record)

        # Apollo config doesn't support count
        assert "count" not in config


class TestSalesNavConfig:
    """Tests for Sales Navigator scraper configuration."""

    def test_build_sales_nav_config_basic(self):
        """Build basic Sales Nav config."""
        record = ListRecord(
            id="rec123",
            list_url="https://www.linkedin.com/sales/search/...",
        )
        cookie = "li_at=AQEDATU..."

        config = build_sales_nav_config(record, cookie)

        assert config["deepScrape"] is True
        assert config["cookie"] == cookie
        assert config["maxDelay"] == 30
        assert config["minDelay"] == 5
        assert config["searchUrl"] == "https://www.linkedin.com/sales/search/..."
        assert config["proxy"]["useApifyProxy"] is True
        assert config["proxy"]["apifyProxyCountry"] == "US"
        assert "RESIDENTIAL" in config["proxy"]["apifyProxyGroups"]
        assert "userAgent" in config

    def test_build_sales_nav_config_with_max_results(self):
        """Sales Nav config includes count when max_results provided."""
        record = ListRecord(
            id="rec123",
            list_url="https://www.linkedin.com/...",
            max_results=250,
        )
        cookie = "li_at=..."

        config = build_sales_nav_config(record, cookie)

        assert config["count"] == 250

    def test_build_sales_nav_config_without_max_results(self):
        """Sales Nav config omits count when max_results not provided."""
        record = ListRecord(
            id="rec123",
            list_url="https://www.linkedin.com/...",
        )
        cookie = "li_at=..."

        config = build_sales_nav_config(record, cookie)

        assert "count" not in config


class TestListRecord:
    """Tests for ListRecord model."""

    def test_from_airtable_full_fields(self):
        """Create ListRecord from full Airtable fields."""
        fields = {
            "List Name": "Tech Leads Q1",
            "List Status": "Scraper Started",
            "List Type": "Apify - Apollo",
            "List URL": "https://apollo.io/...",
            "Max Results": 500,
            "Scraper ID": "run_abc123",
        }

        record = ListRecord.from_airtable("rec123", fields)

        assert record.id == "rec123"
        assert record.list_name == "Tech Leads Q1"
        assert record.list_status == "Scraper Started"
        assert record.list_type == "Apify - Apollo"
        assert record.list_url == "https://apollo.io/..."
        assert record.max_results == 500
        assert record.scraper_id == "run_abc123"

    def test_from_airtable_minimal_fields(self):
        """Create ListRecord with only some fields."""
        fields = {
            "List Name": "My List",
        }

        record = ListRecord.from_airtable("rec456", fields)

        assert record.id == "rec456"
        assert record.list_name == "My List"
        assert record.list_status is None
        assert record.list_type is None
        assert record.list_url is None
        assert record.max_results is None


class TestOrchestrator:
    """Tests for ListBuildingOrchestrator."""

    def test_missing_record_id(self):
        """Orchestrator fails gracefully with missing recordId."""
        # This would need async test setup - marked as integration test
        pass

    @pytest.mark.asyncio
    async def test_run_missing_record_id(self):
        """Run fails with missing recordId."""
        orchestrator = ListBuildingOrchestrator(
            airtable_token="test_token",
            apify_token="test_token",
        )

        result = await orchestrator.run({})

        assert result["error"] == "missing_record_id"

    @pytest.mark.asyncio
    async def test_run_dry_run_scraper_started(self):
        """Dry run for Scraper Started status."""
        orchestrator = ListBuildingOrchestrator(
            airtable_token="test_token",
            apify_token="test_token",
        )

        # Mock clients
        with patch.object(orchestrator, "_init_clients", new_callable=AsyncMock):
            with patch.object(orchestrator, "_close_clients", new_callable=AsyncMock):
                # Mock Airtable response
                mock_airtable = AsyncMock()
                mock_airtable.get_record = AsyncMock(return_value=MagicMock(
                    fields={
                        "List Name": "Test List",
                        "List Status": "Scraper Started",
                        "List Type": "Apify - Apollo",
                        "List URL": "https://apollo.io/search/...",
                    }
                ))
                orchestrator.airtable_client = mock_airtable

                # Mock Apify response
                mock_apify = AsyncMock()
                mock_apify.get_running_actors = AsyncMock(return_value=MagicMock(total=2))
                orchestrator.apify_client = mock_apify

                result = await orchestrator.run({"recordId": "rec123"}, dry_run=True)

        assert result["status"] == "would_start_scraper"
        assert result["dry_run"] is True
        assert "config" in result


class TestEnums:
    """Tests for enum values matching spec."""

    def test_list_status_values(self):
        """ListStatus enum values match Airtable field values."""
        assert ListStatus.SCRAPER_STARTED.value == "Scraper Started"
        assert ListStatus.SCRAPER_QUEUED.value == "Scraper Queued"
        assert ListStatus.SCRAPER_IN_PROGRESS.value == "Scraper In Progress"

    def test_list_type_values(self):
        """ListType enum values match Airtable field values."""
        assert ListType.APOLLO.value == "Apify - Apollo"
        assert ListType.SALES_NAV.value == "Apify - Sales Navigator"
