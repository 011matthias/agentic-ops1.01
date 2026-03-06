"""
OpenRouter API client for LLM completions.

API Reference: https://openrouter.ai/docs
Provides unified access to multiple LLM providers.
"""

import httpx
import asyncio
import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""
    content: str
    model: str
    tokens_used: int | None = None


class OpenRouterClient:
    """
    Async OpenRouter API client.

    Usage:
        client = OpenRouterClient(api_key="sk-or-...")
        response = await client.chat(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0
        )
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_delay = 0.1  # 100ms between requests

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://herbox.se",
                    "X-Title": "Herbox Automations",
                },
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Make API request with rate limiting and retry."""
        client = await self._get_client()
        url = f"/{path}"

        for attempt in range(retries):
            try:
                # Rate limiting
                await asyncio.sleep(self._rate_limit_delay)

                response = await client.request(
                    method,
                    url,
                    json=json,
                )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.RequestError as e:
                logger.error(f"OpenRouter request error: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Max retries exceeded")

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str] | ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletionResponse:
        """
        Create a chat completion.

        Args:
            model: Model identifier (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-haiku")
            messages: List of message dictionaries with "role" and "content"
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            ChatCompletionResponse with content, model, and tokens_used
        """
        logger.info(f"Creating chat completion with model: {model}")

        # Convert ChatMessage objects to dicts if needed
        message_dicts = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                message_dicts.append({"role": msg.role, "content": msg.content})
            else:
                message_dicts.append(msg)

        request_body: dict[str, Any] = {
            "model": model,
            "messages": message_dicts,
            "temperature": temperature,
        }

        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens

        data = await self._request("POST", "chat/completions", json=request_body)

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned from OpenRouter")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens")

        return ChatCompletionResponse(
            content=content,
            model=data.get("model", model),
            tokens_used=tokens_used,
        )

    async def clean_company_name(
        self,
        company_name: str,
        website: str,
        model: str = "openai/gpt-4o-mini",
    ) -> str:
        """
        Clean and normalize company name using GPT-4.

        Args:
            company_name: Raw company name
            website: Company website domain
            model: Model to use (default: openai/gpt-4o-mini)

        Returns:
            Cleaned company name
        """
        prompt = f"""Objective:
Normalize the provided Company Name by eliminating any extraneous words, phrases, or contexts while adhering strictly to the information given in both the Company Name and Website Domain.

Instructions:
- Primary Reference: Utilize the Company Name in conjunction with the Website Domain. Remove any words from the Company Name not reinforced by the Website Domain.
- Acronyms and Abbreviations: When an acronym or abbreviation is commonly recognized and supported by the domain, use it as the output. (e.g., 'American Council of Learned Societies (ACLS)' → 'ACLS')
- Legal Entity Suffixes: Strip away suffixes like 'LLC', 'Inc.', 'Corp.', 'DBA.'
- Special Characters: Strip '™', '©', '®', emojis, and characters like '|', '-' with spacing/text after (unless critical to the name)
- Word Limit: Restrict output to maximum 3 words
- Capitalization: Format to title case, except abbreviations stay uppercase

Company Name: {company_name}
Company Website: {website}

Respond only with the cleaned company name. No explanation."""

        response = await self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        return response.content.strip()

    async def translate_job_title_to_swedish(
        self,
        title: str,
        model: str = "openai/gpt-4o-mini",
    ) -> str:
        """
        Translate job title to Swedish using GPT-4.

        Args:
            title: English job title from LinkedIn
            model: Model to use (default: openai/gpt-4o-mini)

        Returns:
            Swedish job title for email personalization
        """
        prompt = f"""Du är en assistent som omvandlar jobbtitlar från LinkedIn Sales Navigator till korta, tydliga svenska jobbtitlar som grammatiskt passar i meningen:

"Jag såg att du är {{job}} på företag XYZ."

Regler:
- Svara endast med den standardiserade svenska jobbtiteln.
- Ingen förklaring, inga meningar, inga extra ord.
- Använd gemener, förutom för standardförkortningar som HR eller IT.
- Välj alltid den vanligaste svenska jobbtiteln, kort och neutral.

Logik:
- Facility/facilities/workplace/real estate/operations (fastighetsrelaterat):
  - Management/senior: "fastighetsansvarig"
  - Koordinering/stödjande: "fastighetskoordinator"
- Inköpsrelaterat: "inköpare"
- HR/People/Talent/Recruitment: "HR-ansvarig"
- IT/Tech/Developer: "IT-ansvarig" eller lämplig teknisk titel
- CEO/VD/Managing Director: "VD"
- CFO/Finance Director: "ekonomichef"
- COO/Operations: "operativ chef"
- Annat område: kort generisk svensk titel

Omvandla nu denna jobbtitel:
{title}"""

        response = await self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        return response.content.strip()
