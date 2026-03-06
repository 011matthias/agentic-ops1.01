"""
Tests for A7: Smartlead Campaign Sync

Spec: specs/automations/a7-smartlead-campaign-sync.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.automations.smartlead_campaign_sync import (
    SmartleadCampaignSync,
    transform_status,
    map_to_airtable,
    run_smartlead_campaign_sync,
)
from app.clients.smartlead.client import (
    SmartleadClient,
    CampaignListItem,
    CampaignAnalytics,
    CampaignLeadStats,
)
from app.clients.airtable.client import AirtableClient, AirtableRecord


class TestTransformStatus:
    """Test status normalization to sentence case."""

    def test_uppercase_status(self):
        """ACTIVE -> Active"""
        assert transform_status("ACTIVE") == "Active"

    def test_lowercase_status(self):
        """completed -> Completed"""
        assert transform_status("completed") == "Completed"

    def test_underscore_status(self):
        """ramp_up -> Ramp Up"""
        assert transform_status("ramp_up") == "Ramp Up"

    def test_mixed_case_status(self):
        """InProgress -> Inprogress"""
        assert transform_status("InProgress") == "Inprogress"

    def test_empty_status(self):
        """Empty string returns Unknown"""
        assert transform_status("") == "Unknown"

    def test_none_status(self):
        """None returns Unknown"""
        assert transform_status(None) == "Unknown"


class TestMapToAirtable:
    """Test field mapping for Airtable upsert."""

    def test_full_mapping(self):
        """Test mapping all fields correctly."""
        analytics = {
            "id": 123,
            "name": "Test Campaign",
            "status": "active",
            "campaign_lead_stats": {
                "total": 100,
                "inprogress": 30,
                "completed": 50,
                "interested": 10,
                "notStarted": 10,
            },
            "unique_sent_count": 80,
            "sent_count": 200,
            "open_count": 150,
            "reply_count": 25,
            "bounce_count": 5,
            "sequence_count": 3,
        }

        result = map_to_airtable(123, analytics)

        assert result["Campaign ID"] == "123"
        assert result["Campaign Name"] == "Test Campaign"
        assert result["Status"] == "Active"
        assert result["Total Leads"] == 100
        assert result["Leads In Progress"] == 30
        assert result["Leads Completed"] == 50
        assert result["Leads Not Started"] == 10
        assert result["Email Replied (Positive)"] == 10
        assert result["Prospects Contacted"] == 80
        assert result["Email Sent"] == 200
        assert result["Email Opened"] == 150
        assert result["Email Replied"] == 25
        assert result["Email Bounced"] == 5
        assert result["Total Emails"] == 100
        assert result["Number Of Sequences"] == 3

    def test_missing_stats(self):
        """Test handling missing campaign_lead_stats."""
        analytics = {
            "id": 456,
            "name": "Minimal Campaign",
            "status": "draft",
        }

        result = map_to_airtable(456, analytics)

        assert result["Campaign ID"] == "456"
        assert result["Campaign Name"] == "Minimal Campaign"
        assert result["Status"] == "Draft"
        assert result["Total Leads"] == 0
        assert result["Prospects Contacted"] == 0

    def test_campaign_id_as_string(self):
        """Campaign ID should be converted to string."""
        analytics = {"name": "Test", "status": "active"}
        result = map_to_airtable(789, analytics)
        assert result["Campaign ID"] == "789"
        assert isinstance(result["Campaign ID"], str)


class TestSmartleadClient:
    """Test Smartlead API client."""

    @pytest.fixture
    def client(self):
        return SmartleadClient(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_get_campaign_list(self, client):
        """Test parsing campaign list response."""
        mock_response = {
            "data": {
                "campaign_list": [
                    {"id": 123, "name": "Campaign 1", "status": "active"},
                    {"id": 456, "name": "Campaign 2", "status": "completed"},
                ]
            }
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            campaigns = await client.get_campaign_list()

            assert len(campaigns) == 2
            assert campaigns[0].id == 123
            assert campaigns[0].name == "Campaign 1"
            assert campaigns[1].id == 456

    @pytest.mark.asyncio
    async def test_get_campaign_list_includes_drafts(self, client):
        """Test that draft campaigns are included by default."""
        # Response from /campaigns endpoint (list format)
        mock_response = [
            {"id": 123, "name": "Active Campaign", "status": "ACTIVE"},
            {"id": 456, "name": "Draft Campaign", "status": "DRAFTED"},
            {"id": 789, "name": "Completed Campaign", "status": "COMPLETED"},
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            campaigns = await client.get_campaign_list(include_drafts=True)

            assert len(campaigns) == 3
            statuses = [c.status for c in campaigns]
            assert "DRAFTED" in statuses
            assert "ACTIVE" in statuses
            assert "COMPLETED" in statuses

    @pytest.mark.asyncio
    async def test_get_campaign_list_exclude_drafts(self, client):
        """Test filtering out draft campaigns when requested."""
        mock_response = [
            {"id": 123, "name": "Active Campaign", "status": "ACTIVE"},
            {"id": 456, "name": "Draft Campaign", "status": "DRAFTED"},
            {"id": 789, "name": "Completed Campaign", "status": "COMPLETED"},
        ]

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            campaigns = await client.get_campaign_list(include_drafts=False)

            assert len(campaigns) == 2
            statuses = [c.status for c in campaigns]
            assert "DRAFTED" not in statuses
            assert "ACTIVE" in statuses
            assert "COMPLETED" in statuses

    @pytest.mark.asyncio
    async def test_get_campaign_analytics(self, client):
        """Test parsing campaign analytics response."""
        mock_response = {
            "id": 123,
            "name": "Test Campaign",
            "status": "active",
            "campaign_lead_stats": {
                "total": 100,
                "inprogress": 30,
                "completed": 50,
                "interested": 10,
                "notStarted": 10,
            },
            "unique_sent_count": 80,
            "sent_count": 200,
            "open_count": 150,
            "reply_count": 25,
            "bounce_count": 5,
            "sequence_count": 3,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            analytics = await client.get_campaign_analytics(123)

            assert analytics.id == 123
            assert analytics.name == "Test Campaign"
            assert analytics.status == "active"
            assert analytics.campaign_lead_stats.total == 100
            assert analytics.campaign_lead_stats.interested == 10
            assert analytics.sent_count == 200
            assert analytics.reply_count == 25


class TestAirtableUpsert:
    """Test Airtable upsert functionality."""

    @pytest.fixture
    def client(self):
        return AirtableClient(token="test_token", base_id="appXXX")

    @pytest.mark.asyncio
    async def test_upsert_single_record(self, client):
        """Test upserting a single record."""
        mock_response = {
            "records": [
                {
                    "id": "recXXX",
                    "fields": {"Campaign ID": "123", "Campaign Name": "Test"},
                    "createdTime": "2026-01-01T00:00:00.000Z",
                }
            ]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            records = [{"Campaign ID": "123", "Campaign Name": "Test"}]
            results = await client.upsert_records("tblXXX", records, merge_on=["Campaign ID"])

            assert len(results) == 1
            assert results[0].id == "recXXX"
            assert results[0].fields["Campaign ID"] == "123"

            # Verify request format
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "PATCH"
            assert call_args[1]["json"]["performUpsert"]["fieldsToMergeOn"] == ["Campaign ID"]

    @pytest.mark.asyncio
    async def test_upsert_batches_records(self, client):
        """Test that upsert batches records in groups of 10."""
        # Create 15 records to test batching
        records = [{"Campaign ID": str(i)} for i in range(15)]

        mock_response = {
            "records": [{"id": f"rec{i}", "fields": {"Campaign ID": str(i)}} for i in range(10)]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.upsert_records("tblXXX", records, merge_on=["Campaign ID"])

            # Should be called twice (10 + 5 records)
            assert mock_request.call_count == 2


class TestSmartleadCampaignSyncAutomation:
    """Test the full automation."""

    @pytest.mark.asyncio
    async def test_empty_campaign_list(self):
        """Test handling empty campaign list."""
        with patch("app.automations.smartlead_campaign_sync.SmartleadClient") as MockSmartlead:
            with patch("app.automations.smartlead_campaign_sync.AirtableClient") as MockAirtable:
                mock_smartlead = AsyncMock()
                mock_smartlead.get_campaign_list.return_value = []
                mock_smartlead.close = AsyncMock()
                MockSmartlead.return_value = mock_smartlead

                mock_airtable = AsyncMock()
                mock_airtable.close = AsyncMock()
                MockAirtable.return_value = mock_airtable

                with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
                    mock_settings.smartlead_api = "test_key"
                    mock_settings.airtable_token = "test_token"

                    result = await run_smartlead_campaign_sync(dry_run=True)

                    assert result["campaigns_found"] == 0
                    assert result["campaigns_synced"] == 0
                    assert result["campaigns_failed"] == 0

    @pytest.mark.asyncio
    async def test_dry_run_mode(self):
        """Test dry run doesn't make actual changes."""
        with patch("app.automations.smartlead_campaign_sync.SmartleadClient") as MockSmartlead:
            with patch("app.automations.smartlead_campaign_sync.AirtableClient") as MockAirtable:
                mock_smartlead = AsyncMock()
                mock_smartlead.get_campaign_list.return_value = [
                    CampaignListItem(id=123, name="Test Campaign", status="active")
                ]
                mock_smartlead.get_campaign_analytics.return_value = CampaignAnalytics(
                    id=123,
                    name="Test Campaign",
                    status="active",
                    campaign_lead_stats=CampaignLeadStats(),
                )
                mock_smartlead.close = AsyncMock()
                MockSmartlead.return_value = mock_smartlead

                mock_airtable = AsyncMock()
                mock_airtable.close = AsyncMock()
                MockAirtable.return_value = mock_airtable

                with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
                    mock_settings.smartlead_api = "test_key"
                    mock_settings.airtable_token = "test_token"

                    result = await run_smartlead_campaign_sync(dry_run=True)

                    assert result["dry_run"] is True
                    assert result["campaigns_synced"] == 1
                    # Airtable upsert should NOT have been called
                    mock_airtable.upsert_records.assert_not_called()

    @pytest.mark.asyncio
    async def test_continues_on_campaign_error(self):
        """Test that errors on one campaign don't stop the sync."""
        with patch("app.automations.smartlead_campaign_sync.SmartleadClient") as MockSmartlead:
            with patch("app.automations.smartlead_campaign_sync.AirtableClient") as MockAirtable:
                mock_smartlead = AsyncMock()
                mock_smartlead.get_campaign_list.return_value = [
                    CampaignListItem(id=123, name="Good Campaign", status="active"),
                    CampaignListItem(id=456, name="Bad Campaign", status="active"),
                    CampaignListItem(id=789, name="Another Good", status="active"),
                ]

                # First and third campaign succeed, second fails
                async def mock_analytics(campaign_id):
                    if campaign_id == 456:
                        raise Exception("API Error")
                    return CampaignAnalytics(
                        id=campaign_id,
                        name=f"Campaign {campaign_id}",
                        status="active",
                        campaign_lead_stats=CampaignLeadStats(),
                    )

                mock_smartlead.get_campaign_analytics = mock_analytics
                mock_smartlead.close = AsyncMock()
                MockSmartlead.return_value = mock_smartlead

                mock_airtable = AsyncMock()
                mock_airtable.upsert_records.return_value = [
                    AirtableRecord(id="recXXX", fields={})
                ]
                mock_airtable.close = AsyncMock()
                MockAirtable.return_value = mock_airtable

                with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
                    mock_settings.smartlead_api = "test_key"
                    mock_settings.airtable_token = "test_token"

                    # Reduce delay for faster tests
                    with patch("app.automations.smartlead_campaign_sync.CAMPAIGN_DELAY_SECONDS", 0):
                        result = await run_smartlead_campaign_sync(dry_run=False)

                        assert result["campaigns_found"] == 3
                        assert result["campaigns_synced"] == 2
                        assert result["campaigns_failed"] == 1
                        assert len(result["failed"]) == 1
                        assert result["failed"][0]["id"] == 456


    @pytest.mark.asyncio
    async def test_syncs_draft_campaigns(self):
        """Test that draft campaigns are synced to Airtable."""
        with patch("app.automations.smartlead_campaign_sync.SmartleadClient") as MockSmartlead:
            with patch("app.automations.smartlead_campaign_sync.AirtableClient") as MockAirtable:
                mock_smartlead = AsyncMock()
                # Include a draft campaign in the list
                mock_smartlead.get_campaign_list.return_value = [
                    CampaignListItem(id=123, name="Active Campaign", status="ACTIVE"),
                    CampaignListItem(id=456, name="Draft Campaign", status="DRAFTED"),
                ]

                async def mock_analytics(campaign_id):
                    return CampaignAnalytics(
                        id=campaign_id,
                        name="Draft Campaign" if campaign_id == 456 else "Active Campaign",
                        status="DRAFTED" if campaign_id == 456 else "ACTIVE",
                        campaign_lead_stats=CampaignLeadStats(),
                    )

                mock_smartlead.get_campaign_analytics = mock_analytics
                mock_smartlead.close = AsyncMock()
                MockSmartlead.return_value = mock_smartlead

                mock_airtable = AsyncMock()
                mock_airtable.upsert_records.return_value = [
                    AirtableRecord(id="recXXX", fields={})
                ]
                mock_airtable.close = AsyncMock()
                MockAirtable.return_value = mock_airtable

                with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
                    mock_settings.smartlead_api = "test_key"
                    mock_settings.airtable_token = "test_token"

                    with patch("app.automations.smartlead_campaign_sync.CAMPAIGN_DELAY_SECONDS", 0):
                        result = await run_smartlead_campaign_sync(dry_run=False)

                        # Both campaigns should be synced (including the draft)
                        assert result["campaigns_found"] == 2
                        assert result["campaigns_synced"] == 2
                        # Verify draft campaign was synced
                        synced_ids = [c["id"] for c in result["synced"]]
                        assert 456 in synced_ids  # Draft campaign ID


class TestConfigValidation:
    """Test configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_smartlead_key(self):
        """Test error when Smartlead API key is missing."""
        with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
            mock_settings.smartlead_api = None
            mock_settings.airtable_token = "test_token"

            with pytest.raises(ValueError, match="SMARTLEAD_API_KEY"):
                await run_smartlead_campaign_sync()

    @pytest.mark.asyncio
    async def test_missing_airtable_token(self):
        """Test error when Airtable token is missing."""
        with patch("app.automations.smartlead_campaign_sync.settings") as mock_settings:
            mock_settings.smartlead_api = "test_key"
            mock_settings.airtable_token = None

            with pytest.raises(ValueError, match="AIRTABLE_TOKEN"):
                await run_smartlead_campaign_sync()
