"""
Automation A6.4: Lead Data Cleaning

Spec: specs/automations/a6.4-data-cleaning.md
Trigger: CRON daily at midnight

Uses OpenRouter (GPT-4) to:
1. Normalize company names (remove LLC, Inc, special chars)
2. Translate job titles to grammatically correct Swedish
"""

import asyncio
import logging
from typing import Any

from ..clients.openrouter import OpenRouterClient
from ..clients.airtable import AirtableClient
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration (from spec)
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"  # Herbox Base
AIRTABLE_TABLE_ACCOUNTS_ID = "tblIJVWxf1QbpowuS"  # Accounts
AIRTABLE_TABLE_CONTACTS_ID = "tblsI8jeqv1B16MTk"  # Contacts

# AI models (from centralized config)
MODEL_COMPANY_CLEANING = settings.get_ai_model("company_cleaning")
MODEL_TITLE_TRANSLATION = settings.get_ai_model("title_translation")

# Processing configuration
# Airtable rate limit: 5 requests/sec per base
# We limit concurrency to prevent hitting rate limits
CONCURRENT_LIMIT = 5  # Max concurrent API operations
GPT_DELAY_SECONDS = 0.3  # Delay between operations (300ms)


class DataCleaning:
    """
    Lead Data Cleaning automation (async-first).

    Fetches accounts and contacts from Airtable, uses GPT-4 to clean
    company names and translate job titles to Swedish, then updates
    Airtable with the cleaned values.

    Runs daily at midnight via CRON.
    """

    automation_id = "a6_4_data_cleaning"

    def __init__(
        self,
        openrouter_api_key: str | None = None,
        airtable_token: str | None = None,
        airtable_base_id: str | None = None,
    ):
        self.openrouter_api_key = openrouter_api_key or settings.openrouter_api
        self.airtable_token = airtable_token or settings.airtable_token
        self.airtable_base_id = airtable_base_id or AIRTABLE_BASE_ID

        self.openrouter_client: OpenRouterClient | None = None
        self.airtable_client: AirtableClient | None = None

    async def run(
        self,
        dry_run: bool = False,
        list_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run data cleaning as async function.

        Args:
            dry_run: If True, skip actual updates
            list_id: If provided, only process accounts/contacts linked to this list

        Returns:
            Dict with cleaning statistics
        """
        return await run_data_cleaning(
            dry_run=dry_run,
            openrouter_api_key=self.openrouter_api_key,
            airtable_token=self.airtable_token,
            list_id=list_id,
        )


# Async-native version for direct async usage
async def run_data_cleaning(
    dry_run: bool = False,
    openrouter_api_key: str | None = None,
    airtable_token: str | None = None,
    list_id: str | None = None,
) -> dict[str, Any]:
    """
    Run data cleaning as async function.

    This is the preferred way to run the automation when
    already in an async context.

    Args:
        dry_run: If True, skip actual updates
        openrouter_api_key: OpenRouter API key
        airtable_token: Airtable API token
        list_id: If provided, only process accounts/contacts linked to this list

    Returns:
        Dict with cleaning statistics
    """
    openrouter_key = openrouter_api_key or settings.openrouter_api
    airtable_key = airtable_token or settings.airtable_token

    if not openrouter_key:
        raise ValueError("OPENROUTER_API_KEY not configured")
    if not airtable_key:
        raise ValueError("AIRTABLE_TOKEN not configured")

    exec_logger = ExecutionLogger("a6_4_data_cleaning", trigger="cron" if not list_id else "orchestrator")
    openrouter_client: OpenRouterClient | None = None
    airtable_client: AirtableClient | None = None

    try:
        with exec_logger.step("Initialize"):
            openrouter_client = OpenRouterClient(api_key=openrouter_key)
            airtable_client = AirtableClient(
                token=airtable_key,
                base_id=AIRTABLE_BASE_ID,
            )

        with exec_logger.step("Fetch data") as step:
            # Build formulas - filter by list if provided
            if list_id:
                accounts_formula = f"AND(NOT({{Account Name (Cleaned)}}), FIND('{list_id}', ARRAYJOIN({{List}})))"
                contacts_formula = f"AND({{Title}}, NOT({{SL_title}}), FIND('{list_id}', ARRAYJOIN({{List}})))"
            else:
                accounts_formula = "NOT({Account Name (Cleaned)})"
                contacts_formula = "AND({Title},NOT({SL_title}))"

            # Fetch accounts without cleaned name
            accounts = await airtable_client.search_records(
                table_id=AIRTABLE_TABLE_ACCOUNTS_ID,
                formula=accounts_formula,
            )

            # Fetch contacts with title but no SL_title
            contacts = await airtable_client.search_records(
                table_id=AIRTABLE_TABLE_CONTACTS_ID,
                formula=contacts_formula,
            )

            step.output_summary = f"Found {len(accounts)} accounts, {len(contacts)} contacts to clean"

        if not accounts and not contacts:
            logger.info("No data to clean")
            exec_logger.finalize("success")
            return {
                "dry_run": dry_run,
                "accounts_found": 0,
                "accounts_cleaned": 0,
                "accounts_failed": 0,
                "contacts_found": 0,
                "contacts_cleaned": 0,
                "contacts_failed": 0,
            }

        accounts_cleaned: list[dict[str, Any]] = []
        accounts_failed: list[dict[str, Any]] = []
        contacts_cleaned: list[dict[str, Any]] = []
        contacts_failed: list[dict[str, Any]] = []

        async def clean_account(account: Any, index: int) -> None:
            """Clean a single account."""
            account_id = account.id
            fields = account.fields

            account_name = fields.get("Name") or fields.get("Account Name", "")
            website = fields.get("Website", "")

            if not account_name:
                logger.warning(f"Account {account_id} has no name, skipping")
                accounts_failed.append({"id": account_id, "error": "No account name"})
                return

            try:
                logger.info(f"Cleaning account {index + 1}/{len(accounts)}: {account_name}")

                cleaned_name = await openrouter_client.clean_company_name(
                    company_name=account_name,
                    website=website,
                    model=MODEL_COMPANY_CLEANING,
                )

                if dry_run:
                    logger.info(f"[DRY RUN] Would update account: '{account_name}' → '{cleaned_name}'")
                else:
                    await airtable_client.update_record(
                        table_id=AIRTABLE_TABLE_ACCOUNTS_ID,
                        record_id=account_id,
                        fields={"Account Name (Cleaned)": cleaned_name},
                    )

                accounts_cleaned.append({
                    "id": account_id,
                    "original": account_name,
                    "cleaned": cleaned_name,
                })

                logger.info(f"Cleaned: '{account_name}' → '{cleaned_name}'")

            except Exception as e:
                logger.error(f"Failed to clean account {account_id}: {e}")
                accounts_failed.append({"id": account_id, "error": str(e)})

            await asyncio.sleep(GPT_DELAY_SECONDS)

        async def clean_contact(contact: Any, index: int) -> None:
            """Clean a single contact."""
            contact_id = contact.id
            fields = contact.fields

            title = fields.get("Title", "")

            if not title:
                logger.warning(f"Contact {contact_id} has no title, skipping")
                contacts_failed.append({"id": contact_id, "error": "No title"})
                return

            try:
                logger.info(f"Cleaning contact {index + 1}/{len(contacts)}: {title}")

                swedish_title = await openrouter_client.translate_job_title_to_swedish(
                    title=title,
                    model=MODEL_TITLE_TRANSLATION,
                )

                if dry_run:
                    logger.info(f"[DRY RUN] Would update contact: '{title}' → '{swedish_title}'")
                else:
                    await airtable_client.update_record(
                        table_id=AIRTABLE_TABLE_CONTACTS_ID,
                        record_id=contact_id,
                        fields={"SL_title": swedish_title},
                    )

                contacts_cleaned.append({
                    "id": contact_id,
                    "original": title,
                    "swedish": swedish_title,
                })

                logger.info(f"Translated: '{title}' → '{swedish_title}'")

            except Exception as e:
                logger.error(f"Failed to clean contact {contact_id}: {e}")
                contacts_failed.append({"id": contact_id, "error": str(e)})

            await asyncio.sleep(GPT_DELAY_SECONDS)

        # Use semaphore to limit concurrent operations (prevents Airtable rate limiting)
        semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

        async def clean_account_limited(acc: Any, idx: int) -> None:
            """Clean account with semaphore limiting concurrency."""
            async with semaphore:
                await clean_account(acc, idx)

        async def clean_contact_limited(con: Any, idx: int) -> None:
            """Clean contact with semaphore limiting concurrency."""
            async with semaphore:
                await clean_contact(con, idx)

        # Create tasks with concurrency limiting
        account_tasks = [clean_account_limited(acc, i) for i, acc in enumerate(accounts)]
        contact_tasks = [clean_contact_limited(con, i) for i, con in enumerate(contacts)]

        with exec_logger.step(f"Clean data (concurrency: {CONCURRENT_LIMIT})") as step:
            # Process accounts first, then contacts to avoid overwhelming Airtable
            await asyncio.gather(*account_tasks)
            await asyncio.gather(*contact_tasks)

            step.output_summary = (
                f"Cleaned {len(accounts_cleaned)} accounts, {len(contacts_cleaned)} contacts; "
                f"failed {len(accounts_failed)} accounts, {len(contacts_failed)} contacts"
            )

        exec_logger.finalize("success")

        return {
            "dry_run": dry_run,
            "accounts_found": len(accounts),
            "accounts_cleaned": len(accounts_cleaned),
            "accounts_failed": len(accounts_failed),
            "contacts_found": len(contacts),
            "contacts_cleaned": len(contacts_cleaned),
            "contacts_failed": len(contacts_failed),
            "cleaned_accounts": accounts_cleaned,
            "cleaned_contacts": contacts_cleaned,
            "failed_accounts": accounts_failed,
            "failed_contacts": contacts_failed,
        }

    except Exception as e:
        logger.error(f"Data cleaning failed: {e}")
        exec_logger.finalize("failed", error=str(e))
        raise

    finally:
        if openrouter_client:
            await openrouter_client.close()
        if airtable_client:
            await airtable_client.close()


# CLI for testing
if __name__ == "__main__":
    import sys

    async def main():
        dry_run = "--dry-run" in sys.argv

        print(f"Running Data Cleaning (dry_run={dry_run})...")
        result = await run_data_cleaning(dry_run=dry_run)

        print(f"\nResult:")
        print(f"  Accounts found: {result['accounts_found']}")
        print(f"  Accounts cleaned: {result['accounts_cleaned']}")
        print(f"  Accounts failed: {result['accounts_failed']}")
        print(f"  Contacts found: {result['contacts_found']}")
        print(f"  Contacts cleaned: {result['contacts_cleaned']}")
        print(f"  Contacts failed: {result['contacts_failed']}")

        if result.get("cleaned_accounts"):
            print(f"\nSample cleaned accounts:")
            for acc in result["cleaned_accounts"][:3]:
                print(f"  - '{acc['original']}' → '{acc['cleaned']}'")

        if result.get("cleaned_contacts"):
            print(f"\nSample cleaned contacts:")
            for con in result["cleaned_contacts"][:3]:
                print(f"  - '{con['original']}' → '{con['swedish']}'")

        if result.get("failed_accounts"):
            print(f"\nFailed accounts:")
            for f in result["failed_accounts"][:5]:
                print(f"  - {f['id']}: {f['error']}")

        if result.get("failed_contacts"):
            print(f"\nFailed contacts:")
            for f in result["failed_contacts"][:5]:
                print(f"  - {f['id']}: {f['error']}")

    asyncio.run(main())
