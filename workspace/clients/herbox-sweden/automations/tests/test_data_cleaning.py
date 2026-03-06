"""
Tests for A6.4: Lead Data Cleaning.

Spec: specs/automations/a6.4-data-cleaning.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.automations.data_cleaning import (
    DataCleaning,
    run_data_cleaning,
    AIRTABLE_BASE_ID,
    AIRTABLE_TABLE_ACCOUNTS_ID,
    AIRTABLE_TABLE_CONTACTS_ID,
    GPT_DELAY_SECONDS,
)


@dataclass
class MockAirtableRecord:
    """Mock Airtable record for testing."""
    id: str
    fields: dict


class TestDataCleaningInit:
    """Tests for DataCleaning initialization."""

    def test_init_with_defaults(self):
        """Initialize with default settings."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "test_openrouter_key"
            mock_settings.airtable_token = "test_airtable_key"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            cleaner = DataCleaning()

            assert cleaner.openrouter_api_key == "test_openrouter_key"
            assert cleaner.airtable_token == "test_airtable_key"
            assert cleaner.airtable_base_id == AIRTABLE_BASE_ID

    def test_init_with_custom_values(self):
        """Initialize with custom API keys."""
        cleaner = DataCleaning(
            openrouter_api_key="custom_openrouter",
            airtable_token="custom_airtable",
            airtable_base_id="custom_base",
        )

        assert cleaner.openrouter_api_key == "custom_openrouter"
        assert cleaner.airtable_token == "custom_airtable"
        assert cleaner.airtable_base_id == "custom_base"

    def test_init_has_clients_none(self):
        """Clients are initialized as None."""
        cleaner = DataCleaning(
            openrouter_api_key="key",
            airtable_token="token",
        )

        assert cleaner.openrouter_client is None
        assert cleaner.airtable_client is None


class TestDataCleaningRun:
    """Tests for DataCleaning.run() async method."""

    @pytest.mark.asyncio
    async def test_run_calls_run_data_cleaning(self):
        """DataCleaning.run() delegates to run_data_cleaning function."""
        cleaner = DataCleaning(
            openrouter_api_key="key",
            airtable_token="token",
        )

        with patch("app.automations.data_cleaning.run_data_cleaning") as mock_run:
            mock_run.return_value = {"accounts_cleaned": 5, "contacts_cleaned": 10}

            result = await cleaner.run(dry_run=True)

            mock_run.assert_called_once_with(
                dry_run=True,
                openrouter_api_key="key",
                airtable_token="token",
                list_id=None,
            )
            assert result["accounts_cleaned"] == 5
            assert result["contacts_cleaned"] == 10

    @pytest.mark.asyncio
    async def test_run_with_list_id(self):
        """DataCleaning.run() passes list_id parameter."""
        cleaner = DataCleaning(
            openrouter_api_key="key",
            airtable_token="token",
        )

        with patch("app.automations.data_cleaning.run_data_cleaning") as mock_run:
            mock_run.return_value = {}

            await cleaner.run(list_id="rec123")

            mock_run.assert_called_once_with(
                dry_run=False,
                openrouter_api_key="key",
                airtable_token="token",
                list_id="rec123",
            )


class TestRunDataCleaning:
    """Tests for run_data_cleaning async function."""

    @pytest.mark.asyncio
    async def test_missing_openrouter_key(self):
        """Raise error when OpenRouter key missing."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = None
            mock_settings.airtable_token = "token"

            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                await run_data_cleaning()

    @pytest.mark.asyncio
    async def test_missing_airtable_token(self):
        """Raise error when Airtable token missing."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = None

            with pytest.raises(ValueError, match="AIRTABLE_TOKEN"):
                await run_data_cleaning()

    @pytest.mark.asyncio
    async def test_no_data_to_clean(self):
        """Return zero counts when no data to clean."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(return_value=[])
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=True)

                    assert result["accounts_found"] == 0
                    assert result["accounts_cleaned"] == 0
                    assert result["contacts_found"] == 0
                    assert result["contacts_cleaned"] == 0

    @pytest.mark.asyncio
    async def test_dry_run_mode(self):
        """Dry run doesn't update Airtable."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_account = MockAirtableRecord(
                id="rec_account_1",
                fields={"Name": "Acme Inc.", "Website": "acme.com"},
            )
            mock_contact = MockAirtableRecord(
                id="rec_contact_1",
                fields={"Title": "CEO"},
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[
                            [mock_account],  # First call: accounts
                            [mock_contact],  # Second call: contacts
                        ]
                    )
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.clean_company_name = AsyncMock(return_value="Acme")
                    mock_openrouter.translate_job_title_to_swedish = AsyncMock(return_value="CEO")
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=True)

                    assert result["dry_run"] is True
                    assert result["accounts_found"] == 1
                    assert result["contacts_found"] == 1
                    # Dry run should NOT call update_record
                    mock_airtable.update_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_cleaning(self):
        """Successfully clean accounts and contacts."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_account = MockAirtableRecord(
                id="rec_account_1",
                fields={"Name": "Acme Inc., LLC", "Website": "acme.com"},
            )
            mock_contact = MockAirtableRecord(
                id="rec_contact_1",
                fields={"Title": "Chief Executive Officer"},
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[
                            [mock_account],
                            [mock_contact],
                        ]
                    )
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.clean_company_name = AsyncMock(return_value="Acme")
                    mock_openrouter.translate_job_title_to_swedish = AsyncMock(return_value="Algemeen Directeur")
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    assert result["accounts_cleaned"] == 1
                    assert result["contacts_cleaned"] == 1
                    assert result["accounts_failed"] == 0
                    assert result["contacts_failed"] == 0

                    # Verify Airtable was updated
                    assert mock_airtable.update_record.call_count == 2

    @pytest.mark.asyncio
    async def test_skip_account_without_name(self):
        """Skip accounts without name field."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_account = MockAirtableRecord(
                id="rec_account_no_name",
                fields={"Website": "example.com"},  # No Name field
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[
                            [mock_account],
                            [],  # No contacts
                        ]
                    )
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    assert result["accounts_found"] == 1
                    assert result["accounts_cleaned"] == 0
                    assert result["accounts_failed"] == 1

    @pytest.mark.asyncio
    async def test_skip_contact_without_title(self):
        """Skip contacts without title field."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_contact = MockAirtableRecord(
                id="rec_contact_no_title",
                fields={"Name": "John Doe"},  # No Title field
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[
                            [],  # No accounts
                            [mock_contact],
                        ]
                    )
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    assert result["contacts_found"] == 1
                    assert result["contacts_cleaned"] == 0
                    assert result["contacts_failed"] == 1

    @pytest.mark.asyncio
    async def test_handle_gpt_error(self):
        """Handle GPT API errors gracefully."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_account = MockAirtableRecord(
                id="rec_account_1",
                fields={"Name": "Test Company"},
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[
                            [mock_account],
                            [],
                        ]
                    )
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.clean_company_name = AsyncMock(
                        side_effect=Exception("GPT API error")
                    )
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    assert result["accounts_found"] == 1
                    assert result["accounts_cleaned"] == 0
                    assert result["accounts_failed"] == 1
                    assert "GPT API error" in result["failed_accounts"][0]["error"]


class TestCompanyNameCleaning:
    """Tests for company name cleaning logic (acceptance criteria)."""

    @pytest.mark.asyncio
    async def test_clean_company_name_removes_llc(self):
        """Company name cleaning removes LLC suffix."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_account = MockAirtableRecord(
                id="rec1",
                fields={"Name": "Acme Corp, LLC"},
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(side_effect=[[mock_account], []])
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.clean_company_name = AsyncMock(return_value="Acme Corp")
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    # Verify OpenRouter was called with correct params
                    mock_openrouter.clean_company_name.assert_called_once()
                    call_args = mock_openrouter.clean_company_name.call_args
                    assert call_args.kwargs["company_name"] == "Acme Corp, LLC"

                    # Verify result
                    assert result["accounts_cleaned"] == 1
                    assert result["cleaned_accounts"][0]["cleaned"] == "Acme Corp"


class TestJobTitleTranslation:
    """Tests for job title translation logic (acceptance criteria)."""

    @pytest.mark.asyncio
    async def test_translate_job_title_to_swedish(self):
        """Job title translated to Swedish."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_contact = MockAirtableRecord(
                id="rec1",
                fields={"Title": "Chief Technology Officer"},
            )

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(side_effect=[[], [mock_contact]])
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.translate_job_title_to_swedish = AsyncMock(
                        return_value="Chief Technology Officer"
                    )
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    # Verify OpenRouter was called with correct params
                    mock_openrouter.translate_job_title_to_swedish.assert_called_once()
                    call_args = mock_openrouter.translate_job_title_to_swedish.call_args
                    assert call_args.kwargs["title"] == "Chief Technology Officer"

                    # Verify result
                    assert result["contacts_cleaned"] == 1


class TestParallelProcessing:
    """Tests for parallel processing of accounts and contacts."""

    @pytest.mark.asyncio
    async def test_process_accounts_and_contacts_in_parallel(self):
        """Accounts and contacts processed in parallel."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            mock_accounts = [
                MockAirtableRecord(id=f"rec_acc_{i}", fields={"Name": f"Company {i}"})
                for i in range(3)
            ]
            mock_contacts = [
                MockAirtableRecord(id=f"rec_con_{i}", fields={"Title": f"Title {i}"})
                for i in range(3)
            ]

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(
                        side_effect=[mock_accounts, mock_contacts]
                    )
                    mock_airtable.update_record = AsyncMock()
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.clean_company_name = AsyncMock(return_value="Cleaned")
                    mock_openrouter.translate_job_title_to_swedish = AsyncMock(return_value="Translated")
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    result = await run_data_cleaning(dry_run=False)

                    # Verify both accounts and contacts were processed
                    assert result["accounts_found"] == 3
                    assert result["contacts_found"] == 3
                    assert result["accounts_cleaned"] == 3
                    assert result["contacts_cleaned"] == 3

                    # Verify correct number of GPT calls
                    assert mock_openrouter.clean_company_name.call_count == 3
                    assert mock_openrouter.translate_job_title_to_swedish.call_count == 3

                    # Verify correct number of Airtable updates
                    assert mock_airtable.update_record.call_count == 6


class TestAirtableFormulas:
    """Tests for Airtable query formulas."""

    @pytest.mark.asyncio
    async def test_accounts_formula(self):
        """Accounts query uses correct formula."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(return_value=[])
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    await run_data_cleaning(dry_run=True)

                    # Check accounts query
                    calls = mock_airtable.search_records.call_args_list
                    accounts_call = calls[0]
                    assert accounts_call.kwargs["table_id"] == AIRTABLE_TABLE_ACCOUNTS_ID
                    assert accounts_call.kwargs["formula"] == "NOT({Account Name (Cleaned)})"

    @pytest.mark.asyncio
    async def test_contacts_formula(self):
        """Contacts query uses correct formula."""
        with patch("app.automations.data_cleaning.settings") as mock_settings:
            mock_settings.openrouter_api = "key"
            mock_settings.airtable_token = "token"
            mock_settings.get_ai_model.return_value = "openai/gpt-4o-mini"

            with patch("app.automations.data_cleaning.OpenRouterClient") as mock_or:
                with patch("app.automations.data_cleaning.AirtableClient") as mock_at:
                    mock_airtable = AsyncMock()
                    mock_airtable.search_records = AsyncMock(return_value=[])
                    mock_airtable.close = AsyncMock()
                    mock_at.return_value = mock_airtable

                    mock_openrouter = AsyncMock()
                    mock_openrouter.close = AsyncMock()
                    mock_or.return_value = mock_openrouter

                    await run_data_cleaning(dry_run=True)

                    # Check contacts query
                    calls = mock_airtable.search_records.call_args_list
                    contacts_call = calls[1]
                    assert contacts_call.kwargs["table_id"] == AIRTABLE_TABLE_CONTACTS_ID
                    assert contacts_call.kwargs["formula"] == "AND({Title},NOT({SL_title}))"
