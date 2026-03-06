"""
Automation A8: Email Reply Handler

Spec: clients/herbox-sweden/specs/automations/a8-email-reply-handler.md

Processes Smartlead webhooks for email replies and bounces.
Categorizes responses using AI, updates CRM records, and triggers
appropriate follow-up actions (call tasks, LinkedIn outreach).
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from ..clients.airtable.client import AirtableClient
from ..clients.openai.client import OpenAIClient, EmailCategory, PhoneInfo
from ..clients.heyreach.client import HeyreachClient
from ..config import get_settings
from ..logger import ExecutionLogger
from .base import BaseAutomation

logger = logging.getLogger(__name__)
settings = get_settings()

# Airtable table IDs from spec
CONTACTS_TABLE = "tblsI8jeqv1B16MTk"
INTERACTIONS_TABLE = "tbl1ZihAu8yPKKfJC"
TASKS_TABLE = "tbl9K9CDQCuk3XYKj"

# Smartlead categories
POSITIVE_CATEGORIES = {"Interested", "Meeting Request"}
OUT_OF_OFFICE_CATEGORY = "Out Of Office"


class EmailReplyHandler(BaseAutomation):
    """
    Process Smartlead webhooks for email replies and bounces.

    Webhook path: /webhooks/smartlead
    Events: EMAIL_REPLY, EMAIL_BOUNCE

    Flow:
    1. Validate webhook secret
    2. Check for internal emails (filter out)
    3. Search/create contact in Airtable
    4. Log interaction
    5. AI categorize reply
    6. Extract phone numbers
    7. Create tasks for follow-up
    8. Handle bounced emails with LinkedIn fallback
    """

    automation_id = "a8_email_reply_handler"

    def __init__(self, webhook_data: dict[str, Any]):
        """
        Initialize with webhook data.

        Args:
            webhook_data: Full Smartlead webhook payload
        """
        self.webhook_data = webhook_data
        self._airtable: AirtableClient | None = None
        self._openai: OpenAIClient | None = None
        self._heyreach: HeyreachClient | None = None
        self._exec_logger: ExecutionLogger | None = None

        # Parse webhook payload
        self.parsed_data = self._parse_webhook(webhook_data)

        # Result tracking
        self.contact_id: str | None = None
        self.interaction_id: str | None = None
        self.category: EmailCategory | None = None
        self.phones_extracted: list[PhoneInfo] = []
        self.tasks_created: list[str] = []
        self.is_internal_email = False
        self.heyreach_campaign: str | None = None

    def initialize(self) -> None:
        """Initialize API clients and validate configuration."""
        # Validate required settings
        if not settings.airtable_token or not settings.airtable_base_id:
            raise ValueError("Airtable credentials not configured")

        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # Initialize clients
        self._airtable = AirtableClient(
            token=settings.airtable_token,
            base_id=settings.airtable_base_id,
        )

        self._openai = OpenAIClient(api_key=settings.openai_api_key)

        # Heyreach is optional (non-blocking)
        if settings.heyreach_api_key:
            self._heyreach = HeyreachClient(api_key=settings.heyreach_api_key)

        # Setup execution logger
        self._exec_logger = ExecutionLogger(self.automation_id, trigger="webhook")

    def fetch_data(self) -> dict[str, Any]:
        """Return parsed webhook data."""
        return self.parsed_data

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform webhook data into actionable data.

        For this automation, transformation happens during execute().
        This method validates the event type and returns routing info.
        """
        event_type = data.get("event_type")

        if event_type not in ("EMAIL_REPLY", "EMAIL_BOUNCE"):
            raise ValueError(f"Unknown event type: {event_type}")

        return data

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the automation logic based on event type.

        Args:
            data: Parsed webhook data

        Returns:
            Result summary with actions taken
        """
        event_type = data.get("event_type")

        if event_type == "EMAIL_REPLY":
            return await self._handle_email_reply(data)
        elif event_type == "EMAIL_BOUNCE":
            return await self._handle_email_bounce(data)

        raise ValueError(f"Unhandled event type: {event_type}")

    async def _handle_email_reply(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle EMAIL_REPLY event."""
        with self._exec_logger.step("Check internal email") as step:
            if self._is_internal_email(data):
                self.is_internal_email = True
                step.output_summary = "Internal email detected, filtering out"
                logger.info(f"Internal email from {data.get('from_email')}, skipping processing")
                return {"internal_email_filtered": True}

        with self._exec_logger.step("Find or create contact") as step:
            self.contact_id = await self._find_or_create_contact(data)
            step.output_summary = f"Contact: {self.contact_id}"

        with self._exec_logger.step("Log interaction") as step:
            self.interaction_id = await self._log_interaction(data)
            step.output_summary = f"Interaction: {self.interaction_id}"

        with self._exec_logger.step("AI categorize reply") as step:
            original = data.get("sent_message_text", "")
            reply = data.get("reply_message_text", "")
            self.category = await self._openai.categorize_email(original, reply)
            step.output_summary = f"Category: {self.category.category_name}"

        with self._exec_logger.step("Handle out of office") as step:
            if self.category.category_name == OUT_OF_OFFICE_CATEGORY:
                await self._handle_out_of_office(data)
                step.output_summary = self.heyreach_campaign or "No LinkedIn available"
            else:
                step.output_summary = "Not OOO, skipping LinkedIn"

        with self._exec_logger.step("Extract phone numbers") as step:
            self.phones_extracted = await self._openai.extract_phones(
                email_body=reply,
                sender_email=data.get("from_email", ""),
                known_internal_domains=self._get_internal_domains(),
            )
            if self.phones_extracted:
                # Update contact with first phone number
                await self._update_contact_phone(self.phones_extracted[0])
                step.output_summary = f"Extracted {len(self.phones_extracted)} phone(s), updated contact"
            else:
                step.output_summary = "No phone numbers extracted"

        with self._exec_logger.step("Create follow-up tasks") as step:
            task_count = await self._create_tasks(data)
            step.output_summary = f"Created {task_count} task(s)"

        return {
            "contact_id": self.contact_id,
            "interaction_id": self.interaction_id,
            "category": self.category.category_name,
            "phones_extracted": len(self.phones_extracted),
            "tasks_created": task_count,
            "heyreach_campaign": self.heyreach_campaign,
        }

    async def _handle_email_bounce(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle EMAIL_BOUNCE event - route to LinkedIn if available."""
        with self._exec_logger.step("Find contact") as step:
            contact = await self._find_contact_by_email(data.get("sl_lead_email"))
            if not contact:
                step.output_summary = "Contact not found"
                return {"contact_not_found": True}

            self.contact_id = contact["id"]
            step.output_summary = f"Contact: {self.contact_id}"

        with self._exec_logger.step("Check LinkedIn availability") as step:
            linkedin_url = contact.get("fields", {}).get("LinkedIn")
            if not linkedin_url:
                step.output_summary = "No LinkedIn URL"
                return {"no_linkedin": True}

        with self._exec_logger.step("Add to Heyreach campaign") as step:
            await self._handle_out_of_office(data)  # Same logic
            step.output_summary = self.heyreach_campaign or "Failed to add"

        return {
            "contact_id": self.contact_id,
            "heyreach_campaign": self.heyreach_campaign,
        }

    def finalize(self, result: dict[str, Any]) -> None:
        """Cleanup and final logging."""
        # Close clients
        if self._airtable:
            asyncio.create_task(self._airtable.close())
        if self._openai:
            asyncio.create_task(self._openai.close())
        if self._heyreach:
            asyncio.create_task(self._heyreach.close())

        # Finalize execution logger
        if self._exec_logger:
            self._exec_logger.finalize("success")

        logger.info(f"A8 completed: {result}")

    def _parse_webhook(self, webhook_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and normalize Smartlead webhook payload.

        Extracts:
        - event_type, campaign_id, campaign_status
        - from_email, to_email, to_name
        - subject, sent_message.text, reply_message.text
        - reply_message.time, sequence_number
        - sl_lead_email (original email)
        """
        body = webhook_data.get("body", {})

        return {
            "event_type": body.get("event_type"),
            "campaign_id": body.get("campaign_id"),
            "campaign_status": body.get("campaign_status"),
            "from_email": body.get("from_email"),
            "to_email": body.get("to_email"),
            "to_name": body.get("to_name"),
            "subject": body.get("subject"),
            "sent_message_text": body.get("sent_message", {}).get("text", ""),
            "reply_message_text": body.get("reply_message", {}).get("text", ""),
            "reply_message_time": body.get("reply_message", {}).get("time"),
            "sequence_number": body.get("sequence_number"),
            "sl_lead_email": body.get("sl_lead_email"),
        }

    def _is_internal_email(self, data: dict[str, Any]) -> bool:
        """Check if the reply is from an internal Herbox email address."""
        from_email = data.get("from_email", "")

        internal_domains = self._get_internal_domains()

        # Check if sender (from_email) is from internal domain
        for domain in internal_domains:
            if from_email.endswith(f"@{domain}"):
                return True

        return False

    def _get_internal_domains(self) -> list[str]:
        """Get list of internal Herbox domains from settings."""
        domains_str = settings.herbox_domains or "herbox.se,herbox.com"
        return [d.strip() for d in domains_str.split(",")]

    async def _find_or_create_contact(self, data: dict[str, Any]) -> str:
        """Find existing contact or create new one."""
        email = data.get("sl_lead_email") or data.get("to_email")

        # Search for existing contact
        records = await self._airtable.search_records(
            CONTACTS_TABLE,
            formula=f"{{Email}}='{email}'",
        )

        if records:
            logger.info(f"Found existing contact: {records[0].id}")
            return records[0].id

        # Create new contact
        name = data.get("to_name", "")
        if " " in name:
            # Note: N8N had this reversed - [1] for First, [0] for Last
            # Following spec guidance on Swedish naming convention
            parts = name.split(" ")
            first_name = parts[1] if len(parts) > 1 else ""
            last_name = parts[0]
        else:
            first_name = name
            last_name = ""

        fields = {
            "First Name": first_name,
            "Last Name": last_name,
            "Email": email,
            "Enrichment Status": "Enriched + Verified",
            "Email Verification Status": "Valid",
        }

        # Add replied date if available
        if reply_time := data.get("reply_message_time"):
            try:
                parsed_time = datetime.fromisoformat(reply_time.replace("Z", "+00:00"))
                fields["Last Replied Date"] = parsed_time.strftime("%Y-%m-%d")
            except Exception:
                pass

        result = await self._airtable._request(
            "POST",
            CONTACTS_TABLE,
            json={"fields": fields},
        )

        logger.info(f"Created new contact: {result['id']}")
        return result["id"]

    async def _find_contact_by_email(self, email: str | None) -> dict[str, Any] | None:
        """Find contact by email and return full record data."""
        if not email:
            return None

        records = await self._airtable.search_records(
            CONTACTS_TABLE,
            formula=f"{{Email}}='{email}'",
        )

        if records:
            return {"id": records[0].id, "fields": records[0].fields}

        return None

    async def _log_interaction(self, data: dict[str, Any]) -> str:
        """Create interaction record in Airtable."""
        fields = {
            "Contact": [self.contact_id],
            "Channel": "Cold Email",
            "Interaction Type": "Email Reply",
            "Message Sent": data.get("sent_message_text", ""),
            "Message Received": data.get("reply_message_text", ""),
        }

        # Add interaction date if available
        if reply_time := data.get("reply_message_time"):
            try:
                parsed_time = datetime.fromisoformat(reply_time.replace("Z", "+00:00"))
                fields["Interaction Date"] = parsed_time.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        result = await self._airtable._request(
            "POST",
            INTERACTIONS_TABLE,
            json={"fields": fields},
        )

        return result["id"]

    async def _handle_out_of_office(self, data: dict[str, Any]) -> None:
        """Add lead to Heyreach LinkedIn campaign if LinkedIn URL available."""
        if not self._heyreach:
            logger.info("Heyreach not configured, skipping LinkedIn campaign")
            return

        # Get contact to check for LinkedIn
        contact = await self._find_contact_by_email(data.get("sl_lead_email"))
        if not contact:
            return

        linkedin_url = contact.get("fields", {}).get("LinkedIn")
        if not linkedin_url:
            logger.info("No LinkedIn URL on contact, skipping Heyreach")
            return

        # Determine campaign based on original sender (to_name)
        to_name = data.get("to_name", "").lower()

        campaign_id = None
        if "patrick" in to_name and settings.heyreach_campaign_patrick:
            campaign_id = settings.heyreach_campaign_patrick
        elif "koen" in to_name and settings.heyreach_campaign_koen:
            campaign_id = settings.heyreach_campaign_koen

        if not campaign_id:
            logger.info("Could not determine campaign from sender name")
            return

        # Add to campaign
        result = await self._heyreach.add_lead_to_campaign(campaign_id, linkedin_url)
        if result:
            self.heyreach_campaign = campaign_id
            logger.info(f"Added lead to Heyreach campaign: {campaign_id}")
        else:
            logger.warning("Failed to add lead to Heyreach campaign")

    async def _update_contact_phone(self, phone_info: PhoneInfo) -> None:
        """Update contact with phone number."""
        await self._airtable.update_record(
            CONTACTS_TABLE,
            self.contact_id,
            {"Phone": phone_info.phone},
        )
        logger.info(f"Updated contact {self.contact_id} with phone: {phone_info.phone}")

    async def _create_tasks(self, data: dict[str, Any]) -> int:
        """Create follow-up tasks based on category and phone extraction."""
        tasks_created = 0

        # Create call task for positive replies
        if self.category.category_name in POSITIVE_CATEGORIES:
            await self._create_call_task()
            tasks_created += 1

        # Create call task if phone numbers extracted
        elif self.phones_extracted:
            await self._create_call_task()
            tasks_created += 1

        return tasks_created

    async def _create_call_task(self) -> str:
        """Create a call task in Airtable."""
        fields = {
            "Contact": [self.contact_id],
            "Task Type": "Call",
            "Status": "To Do",
        }

        result = await self._airtable._request(
            "POST",
            TASKS_TABLE,
            json={"fields": fields},
        )

        task_id = result["id"]
        self.tasks_created.append(task_id)
        logger.info(f"Created call task: {task_id}")
        return task_id
