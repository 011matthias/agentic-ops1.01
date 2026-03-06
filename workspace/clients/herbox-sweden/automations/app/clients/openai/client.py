"""
OpenAI API client for email categorization and phone extraction.

API Reference: https://platform.openai.com/docs/api-reference
Rate Limit: 60 requests per minute
"""

import httpx
import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1"


class EmailCategory(BaseModel):
    """Email categorization result."""
    category_name: str
    category_id: int


class PhoneInfo(BaseModel):
    """Extracted phone information."""
    name: str
    phone: str


class OpenAIClient:
    """
    Async OpenAI API client for email processing.

    Usage:
        client = OpenAIClient(api_key="sk-...")
        category = await client.categorize_email(original, reply)
        phones = await client.extract_phones(email_body, sender_email)
    """

    # Smartlead email categories
    CATEGORIES = {
        "Interested": 1,
        "Meeting Request": 2,
        "Not Interested": 3,
        "Do Not Contact": 4,
        "Information Request": 5,
        "Out Of Office": 6,
        "Wrong Person": 7,
        "Uncategorizable by AI": 8,
        "Sender Originated Bounce": 9,
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        endpoint: str,
        *,
        json: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        for attempt in range(retries):
            try:
                response = await client.post(endpoint, json=json)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                logger.error(f"OpenAI request error: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def categorize_email(
        self,
        original_email: str,
        reply_email: str,
        model: str = "gpt-4o-mini",
    ) -> EmailCategory:
        """
        Categorize an email reply using AI.

        Args:
            original_email: The original sent email
            reply_email: The reply received from the lead
            model: OpenAI model to use

        Returns:
            EmailCategory with category_name and category_id
        """
        logger.info("Categorizing email reply with AI")

        categories_list = "\n".join([
            f"{name} (ID: {id})" for name, id in self.CATEGORIES.items()
        ])

        system_prompt = f"""You are an email categorization specialist for cold email campaigns.

Analyze the reply email and categorize it into one of these categories:
{categories_list}

Respond ONLY with a JSON object in this exact format:
{{"CategoryName": "...", "CategoryID": N}}

Rules:
- "Interested": Shows interest, mentions pricing/demo, positive language
- "Meeting Request": Explicitly requests meeting/call
- "Not Interested": Clearly declines, not interested right now
- "Do Not Contact": Explicitly requests removal/unsubscribe
- "Information Request": Asks questions, wants more details
- "Out Of Office": Auto-reply, temporary unavailability, back on date
- "Wrong Person": Not the right contact, forward to someone else
- "Uncategorizable by AI": Ambiguous, unclear, or very short replies
- "Sender Originated Bounce": Delivery failure, bounced message"""

        user_prompt = f"""Original email sent:
{original_email}

Reply received:
{reply_email}

Categorize this reply."""

        try:
            response = await self._request(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )

            content = response["choices"][0]["message"]["content"]
            import json
            result = json.loads(content)

            category_name = result.get("CategoryName", "Uncategorizable by AI")
            category_id = result.get("CategoryID", 8)

            # Validate and map to known categories
            if category_name in self.CATEGORIES:
                category_id = self.CATEGORIES[category_name]
            elif category_id in self.CATEGORIES.values():
                # Map ID back to name
                for name, id_ in self.CATEGORIES.items():
                    if id_ == category_id:
                        category_name = name
                        break
            else:
                category_name = "Uncategorizable by AI"
                category_id = 8

            logger.info(f"Categorized as: {category_name} (ID: {category_id})")
            return EmailCategory(category_name=category_name, category_id=category_id)

        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            # Fall back to uncategorizable
            return EmailCategory(category_name="Uncategorizable by AI", category_id=8)

    async def extract_phones(
        self,
        email_body: str,
        sender_email: str,
        known_internal_domains: list[str] | None = None,
        model: str = "gpt-4o-mini",
    ) -> list[PhoneInfo]:
        """
        Extract phone numbers from an email, intelligently filtering out internal contacts.

        Args:
            email_body: The email body text to extract from
            sender_email: Email of the person who sent this reply (to filter their info)
            known_internal_domains: List of internal company domains (e.g., ["herbox.se", "herbox.com"])
            model: OpenAI model to use

        Returns:
            List of PhoneInfo objects with name and phone (normalized to international format)
        """
        logger.info(f"Extracting phone numbers from email (sender: {sender_email})")

        if known_internal_domains is None:
            known_internal_domains = ["herbox.se", "herbox.com"]

        # Build filter instructions
        filter_instructions = "\n".join([
            f"- Do NOT extract phone numbers from emails ending in @{domain}"
            for domain in known_internal_domains
        ])
        filter_instructions += f"\n- Do NOT extract phone numbers associated with {sender_email}"

        system_prompt = f"""You are a phone number extraction specialist.

Extract phone numbers from the email signature and body. Follow these rules:
{filter_instructions}

For each valid phone number found (excluding internal contacts):
1. Extract the name associated with the phone number
2. Normalize to international format (e.g., +31 6 4695 9939)
3. Return as JSON array

Respond ONLY with a JSON array in this exact format:
[{{"name": "John Smith", "phone": "+31 6 1234 5678"}}]

If no valid phone numbers are found, return an empty array: []"""

        user_prompt = f"""Email body:
{email_body}

Extract phone numbers from external contacts only."""

        try:
            response = await self._request(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )

            content = response["choices"][0]["message"]["content"]
            import json
            results = json.loads(content)

            if isinstance(results, list):
                phones = [PhoneInfo(**item) for item in results]
                logger.info(f"Extracted {len(phones)} phone numbers")
                return phones

            return []

        except Exception as e:
            logger.error(f"Phone extraction failed: {e}")
            return []


# Import at module level for retry logic
import asyncio
