# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27.0",
#     "pydantic>=2.0.0",
# ]
# ///

"""
Automation A6.3: Contact Enrichment & Verification

Spec: specs/automations/a6.3-contact-enrichment.md
Trigger: CRON (every 6 hours)

Enriches contacts with email addresses using a multi-vendor waterfall approach,
then verifies deliverability with Leadmagic Email Validation.
"""

import asyncio
import logging
import sys
from typing import Any

from ..clients.airtable import AirtableClient
from ..clients.leadmagic import LeadmagicClient
from ..clients.trykitt import TrykittClient
from ..logger import ExecutionLogger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable configuration
AIRTABLE_BASE_ID = "app4gZ66mB8m3Vvj0"
AIRTABLE_TABLE_CONTACTS_ID = "tblsI8jeqv1B16MTk"

# Processing configuration
# See: docs/configuration-decisions.md for reasoning
MAX_CONTACTS = 20  # Testing limit - increase for production
CONCURRENT_LIMIT = 10  # Process up to 10 contacts simultaneously
RATE_LIMIT_DELAY = 0.5  # Seconds between verification API calls


class ContactEnrichment:
    """
    Contact enrichment and verification automation.

    Waterfall enrichment flow:
    1. If email exists: verify and update status
    2. If no email: try Leadmagic Email Finder
    3. If still no email: try Trykitt
    4. If still no email: try Leadmagic LinkedIn Profile
    5. After finding email: verify with Leadmagic Email Validation
    6. Update Airtable with results
    """

    automation_id = "a6_3_contact_enrichment"

    def __init__(
        self,
        airtable_token: str | None = None,
        leadmagic_api_key: str | None = None,
        trykitt_api_key: str | None = None,
    ):
        self.airtable_token = airtable_token or settings.airtable_token
        self.leadmagic_api_key = leadmagic_api_key or settings.leadmagic_api_key
        self.trykitt_api_key = trykitt_api_key or settings.trykitt_api_key

        self.airtable_client: AirtableClient | None = None
        self.leadmagic_client: LeadmagicClient | None = None
        self.trykitt_client: TrykittClient | None = None

    async def _init_clients(self) -> None:
        """Initialize API clients."""
        if not self.airtable_token:
            raise ValueError("AIRTABLE_TOKEN not configured")

        self.airtable_client = AirtableClient(
            token=self.airtable_token,
            base_id=AIRTABLE_BASE_ID,
        )

        if self.leadmagic_api_key:
            self.leadmagic_client = LeadmagicClient(api_key=self.leadmagic_api_key)

        if self.trykitt_api_key:
            self.trykitt_client = TrykittClient(api_key=self.trykitt_api_key)

    async def _close_clients(self) -> None:
        """Close API clients."""
        if self.airtable_client:
            await self.airtable_client.close()
        if self.leadmagic_client:
            await self.leadmagic_client.close()
        if self.trykitt_client:
            await self.trykitt_client.close()

    @staticmethod
    def extract_domain(website: str | None) -> str | None:
        """Extract domain from website URL."""
        if not website:
            return None

        # Remove protocol
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "")

        # Remove path
        domain = domain.split("/")[0]

        return domain if domain and "." in domain else None

    @staticmethod
    def standardize_status(status: str | None) -> str:
        """
        Map vendor-specific statuses to Airtable Email Verification Status options.

        Airtable options: Valid, Catch-All, Invalid, Unknown

        Vendor status mappings:
        - Leadmagic: deliverable, undeliverable, risky, catch-all, unknown
        - Usebouncer: ok, valid, invalid, risky, catch_all
        - Generic: safe, accept_all, etc.
        """
        if not status:
            return "Unknown"

        status_lower = status.lower().replace("_", "-")

        # Valid statuses
        if status_lower in ["ok", "valid", "safe", "deliverable"]:
            return "Valid"

        # Catch-All statuses (risky but may work)
        if status_lower in ["risky", "catch-all", "accept-all"]:
            return "Catch-All"

        # Invalid statuses
        if status_lower in ["invalid", "undeliverable", "bounce", "spam-trap", "disposable"]:
            return "Invalid"

        # Default to Unknown for anything else
        return "Unknown"

    async def _enrich_contact(
        self,
        contact: Any,
    ) -> dict[str, Any]:
        """
        Enrich a single contact with email verification.

        Returns dict with fields to update in Airtable.
        """
        fields = contact.fields
        first_name = fields.get("First Name", "")
        last_name = fields.get("Last Name", "")
        email = fields.get("Email", "")
        linkedin_url = fields.get("Linkedin URL", "")

        # Extract website/company - may be list or string
        website_raw = fields.get("Website", [""])[0] if fields.get("Website") else ""
        company_name_raw = fields.get("Company Name", [""])[0] if fields.get("Company Name") else ""
        website = website_raw if isinstance(website_raw, str) else ""
        company_name = company_name_raw if isinstance(company_name_raw, str) else ""

        domain = self.extract_domain(website)
        full_name = f"{first_name} {last_name}".strip()

        enrichment_result = {
            "email": email,
            "vendor": None,
            "verification_status": None,
            "verification_vendor": None,
            "enrichment_status": "Pending",
        }

        # If email already exists, verify it
        if email:
            logger.info(f"Contact already has email: {email}")
            enrichment_result["vendor"] = fields.get("Enrichment Vendor", "Existing")

        # Otherwise, try waterfall enrichment
        else:
            # 1. Leadmagic Email Finder
            if self.leadmagic_client and domain:
                logger.info(f"Trying Leadmagic Email Finder for {full_name} @ {domain}")
                result = await self.leadmagic_client.email_finder(
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain,
                    company_name=company_name,
                )
                if result.get("email"):
                    enrichment_result["email"] = result["email"]
                    enrichment_result["vendor"] = "Leadmagic"

            # 2. Trykitt
            if not enrichment_result["email"] and self.trykitt_client:
                logger.info(f"Trying Trykitt for {full_name}")
                result = await self.trykitt_client.find_email(
                    full_name=full_name,
                    domain=domain or website or company_name,
                    linkedin_url=linkedin_url,
                    realtime=True,
                )
                email_found = result.get("email")
                if email_found and email_found != "no-results-found":
                    enrichment_result["email"] = email_found
                    enrichment_result["vendor"] = "Trykitt"

            # 3. Leadmagic LinkedIn Profile
            if not enrichment_result["email"] and self.leadmagic_client and linkedin_url:
                logger.info(f"Trying Leadmagic LinkedIn for {linkedin_url}")
                result = await self.leadmagic_client.b2b_profile_email(
                    profile_url=linkedin_url,
                )
                if result.get("email"):
                    enrichment_result["email"] = result["email"]
                    enrichment_result["vendor"] = "Leadmagic-LinkedIn"

        # Verify email with Leadmagic if found
        if enrichment_result["email"] and self.leadmagic_client:
            # Rate limiting to avoid 429 errors
            await asyncio.sleep(RATE_LIMIT_DELAY)

            logger.info(f"Verifying email with Leadmagic: {enrichment_result['email']}")
            verification = await self.leadmagic_client.verify_email(
                email=enrichment_result["email"],
                first_name=first_name,
                last_name=last_name,
            )

            # Handle verification response
            # Leadmagic returns: status (valid/invalid/risky/catch-all), is_catch_all, message
            if not verification.get("error"):
                enrichment_result["verification_status"] = verification.get("status")
                enrichment_result["verification_vendor"] = "Leadmagic"
            else:
                logger.warning(f"Verification failed: {verification.get('error')}")
                enrichment_result["verification_status"] = "unknown"
                enrichment_result["verification_vendor"] = "Leadmagic"

        # Determine enrichment status
        # "Enriched + Verified" = went through both processes (regardless of verification result)
        if enrichment_result["email"]:
            enrichment_result["enrichment_status"] = "Enriched + Verified"
        else:
            enrichment_result["enrichment_status"] = "No Email Found"

        return enrichment_result

    async def _process_single_contact(
        self,
        contact: Any,
        dry_run: bool,
        index: int,
        total: int,
    ) -> dict[str, Any]:
        """
        Process a single contact - designed for concurrent execution.

        Returns dict with processing results.
        """
        contact_id = contact.id
        contact_name = f"{contact.fields.get('First Name', '')} {contact.fields.get('Last Name', '')}".strip()

        result = {
            "contact_id": contact_id,
            "contact_name": contact_name,
            "success": False,
            "enriched": False,
            "error": None,
        }

        try:
            logger.info(f"Processing contact {index}/{total}: {contact_name} ({contact_id})")

            enrichment = await self._enrich_contact(contact)

            # Build update fields
            update_fields: dict[str, Any] = {
                "Enrichment Status": enrichment["enrichment_status"],
            }

            if enrichment["email"]:
                update_fields["Email"] = enrichment["email"]
                if enrichment["vendor"]:
                    update_fields["Enrichment Vendor"] = enrichment["vendor"]
                if enrichment["verification_status"]:
                    update_fields["Email Verification Status"] = self.standardize_status(
                        enrichment["verification_status"]
                    )
                if enrichment["verification_vendor"]:
                    update_fields["Verification Vendor"] = enrichment["verification_vendor"]

                result["enriched"] = True
                result["vendor"] = enrichment["vendor"]
            else:
                result["enriched"] = False

            # Update Airtable
            if not dry_run:
                await self.airtable_client.update_record(
                    AIRTABLE_TABLE_CONTACTS_ID,
                    contact_id,
                    update_fields,
                )
            else:
                logger.info(f"[DRY RUN] Would update: {update_fields}")

            result["success"] = True

        except Exception as e:
            logger.error(f"Error processing contact {contact_id}: {e}")
            result["error"] = str(e)

        return result

    async def run(
        self,
        dry_run: bool = False,
        list_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run the contact enrichment automation.

        Args:
            dry_run: If True, simulate without making changes
            list_id: If provided, only process contacts linked to this list

        Returns:
            Result dictionary with status and details
        """
        exec_logger = ExecutionLogger(self.automation_id, trigger="cron" if not list_id else "orchestrator")

        try:
            # 1. Initialize
            with exec_logger.step("Initialize"):
                await self._init_clients()

            # 2. Fetch pending contacts
            with exec_logger.step("Fetch Pending Contacts") as step:
                # Build formula - filter by list if provided
                if list_id:
                    formula = f"AND({{Enrichment Status}}='Pending', FIND('{list_id}', ARRAYJOIN({{List}})))"
                else:
                    formula = "{Enrichment Status}='Pending'"

                contacts = await self.airtable_client.search_records(
                    AIRTABLE_TABLE_CONTACTS_ID,
                    formula=formula,
                    max_records=MAX_CONTACTS,
                )
                step.output_summary = f"Found {len(contacts)} pending contacts"

                if not contacts:
                    logger.info("No pending contacts to enrich")
                    exec_logger.finalize("success")
                    return {
                        "status": "success",
                        "processed_count": 0,
                        "message": "No pending contacts",
                        "dry_run": dry_run,
                    }

            # 3. Process contacts in parallel
            with exec_logger.step(f"Process {len(contacts)} Contacts (Concurrency: {CONCURRENT_LIMIT})"):
                semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

                async def process_with_limit(contact: Any, index: int) -> dict[str, Any]:
                    """Process contact with semaphore limiting concurrency."""
                    async with semaphore:
                        return await self._process_single_contact(
                            contact=contact,
                            dry_run=dry_run,
                            index=index,
                            total=len(contacts),
                        )

                # Process all contacts concurrently
                tasks = [
                    process_with_limit(contact, i)
                    for i, contact in enumerate(contacts, 1)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

            # 4. Tally results
            enriched_count = 0
            no_email_count = 0
            error_count = 0

            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Task exception: {result}")
                elif result.get("error"):
                    error_count += 1
                elif result.get("enriched"):
                    enriched_count += 1
                else:
                    no_email_count += 1

            # 5. Finalize
            with exec_logger.step("Finalize") as step:
                summary = (
                    f"Processed: {len(contacts)} | "
                    f"Enriched: {enriched_count} | "
                    f"No Email: {no_email_count} | "
                    f"Errors: {error_count}"
                )
                step.output_summary = summary

            exec_logger.finalize("success")
            return {
                "status": "success",
                "processed_count": len(contacts),
                "enriched_count": enriched_count,
                "no_email_count": no_email_count,
                "error_count": error_count,
                "dry_run": dry_run,
            }

        except Exception as e:
            logger.error(f"Contact enrichment failed: {e}")
            exec_logger.finalize("failed", error=str(e))
            raise

        finally:
            await self._close_clients()


async def main() -> None:
    """Run the automation for testing."""
    dry_run = "--dry-run" in sys.argv

    enrichment = ContactEnrichment()
    result = await enrichment.run(dry_run=dry_run)

    print(f"\n{'=' * 50}")
    print(f"Result: {result['status']}")
    print(f"Processed: {result.get('processed_count', 0)}")
    print(f"Enriched: {result.get('enriched_count', 0)}")
    print(f"No Email Found: {result.get('no_email_count', 0)}")
    print(f"Errors: {result.get('error_count', 0)}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    asyncio.run(main())
