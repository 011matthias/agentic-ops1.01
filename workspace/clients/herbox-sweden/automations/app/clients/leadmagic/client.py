# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///

"""
Leadmagic API client for email enrichment and verification.

API Reference:
- Email Finder: https://api.leadmagic.io/v1/people/email-finder
- LinkedIn Profile Email: https://api.leadmagic.io/v1/people/b2b-profile-email
- Email Verification: https://api.leadmagic.io/v1/email/verify
"""

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

LEADMAGIC_API_URL = "https://api.leadmagic.io"


class LeadmagicClient:
    """
    Async Leadmagic API client.

    Usage:
        client = LeadmagicClient(api_key="...")
        email = await client.email_finder("John", "Doe", "example.com")
        email = await client.b2b_profile_email("https://linkedin.com/in/johndoe")
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=LEADMAGIC_API_URL,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def email_finder(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find email using name and domain.

        Args:
            first_name: Contact's first name
            last_name: Contact's last name
            domain: Company domain (e.g., "example.com")
            company_name: Company name (optional, improves accuracy)

        Returns:
            Dict with "email" key (str | null) and metadata
        """
        client = await self._get_client()

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
        }
        if company_name:
            payload["company_name"] = company_name

        logger.info(f"Leadmagic email_finder: {first_name} {last_name} @ {domain}")

        try:
            response = await client.post(
                "/v1/people/email-finder",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("email"):
                logger.info(f"Email found: {data['email']}")
            else:
                logger.info("No email found")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Leadmagic API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise ValueError("Invalid Leadmagic API key") from e
            if e.response.status_code == 429:
                logger.warning("Leadmagic rate limit exceeded")
            return {"email": None, "error": str(e)}

        except httpx.RequestError as e:
            logger.error(f"Leadmagic request error: {e}")
            return {"email": None, "error": str(e)}

    async def b2b_profile_email(self, profile_url: str) -> dict[str, Any]:
        """
        Find email using LinkedIn profile URL.

        Args:
            profile_url: LinkedIn profile URL

        Returns:
            Dict with "email" key (str | null) and metadata
        """
        client = await self._get_client()

        logger.info(f"Leadmagic b2b_profile_email: {profile_url}")

        try:
            response = await client.post(
                "/v1/people/b2b-profile-email",
                json={"profile_url": profile_url},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("email"):
                logger.info(f"Email found: {data['email']}")
            else:
                logger.info("No email found")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Leadmagic API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise ValueError("Invalid Leadmagic API key") from e
            if e.response.status_code == 429:
                logger.warning("Leadmagic rate limit exceeded")
            return {"email": None, "error": str(e)}

        except httpx.RequestError as e:
            logger.error(f"Leadmagic request error: {e}")
            return {"email": None, "error": str(e)}

    async def verify_email(self, email: str, first_name: str | None = None, last_name: str | None = None) -> dict[str, Any]:
        """
        Verify email deliverability.

        Args:
            email: Email address to verify
            first_name: Contact's first name (optional, improves accuracy)
            last_name: Contact's last name (optional, improves accuracy)

        Returns:
            Dict with verification results:
            - "status": str (e.g., "valid", "invalid", "risky", "catch-all")
            - "is_catch_all": bool
            - "message": str (human-readable description)

        API Response fields:
            - email_status: "valid", "invalid", "risky", "catch-all", etc.
            - is_domain_catch_all: bool
            - message: str
        """
        client = await self._get_client()

        logger.info(f"Leadmagic verify_email: {email}")

        payload = {"email": email}
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name

        try:
            response = await client.post(
                "/v1/people/email-validation",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Map API response to standardized fields
            email_status = data.get("email_status")
            is_catch_all = data.get("is_domain_catch_all", False)

            # If domain is catch-all, override status
            if is_catch_all and email_status == "valid":
                email_status = "catch-all"

            logger.info(f"Verification result: {email_status} (catch-all: {is_catch_all})")

            return {
                "status": email_status,
                "is_catch_all": is_catch_all,
                "message": data.get("message"),
                "raw": data,  # Include full response for debugging
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Leadmagic verify API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise ValueError("Invalid Leadmagic API key") from e
            if e.response.status_code == 429:
                logger.warning("Leadmagic rate limit exceeded")
            return {"status": "unknown", "error": str(e)}

        except httpx.RequestError as e:
            logger.error(f"Leadmagic verify request error: {e}")
            return {"status": "unknown", "error": str(e)}
