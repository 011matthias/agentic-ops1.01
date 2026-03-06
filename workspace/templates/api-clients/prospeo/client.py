"""
Prospeo API Client
Generated from: https://prospeo.io/api-docs

Usage:
    from prospeo import ProspeoClient

    client = ProspeoClient(api_key="your_api_key")

    # Get account info
    account = client.get_account_info()

    # Enrich a person
    person = client.enrich_person(
        first_name="John",
        last_name="Doe",
        company_website="intercom.com",
        only_verified_email=True,
    )

    # Bulk enrich persons
    results = client.bulk_enrich_persons([
        {"identifier": "1", "full_name": "Eva Kiegler", "company_website": "intercom.com"},
        {"identifier": "2", "linkedin_url": "https://linkedin.com/in/johndoe"},
    ])

    # Enrich a company
    company = client.enrich_company(company_website="stripe.com")

    # Search persons
    results = client.search_persons(
        filters={"person_seniority": {"include": ["Founder/Owner"]}},
        page=1,
    )
"""

import logging
from typing import Any

import httpx

from .models import (
    AccountInfoResponse,
    BulkCompanyEnrichData,
    BulkEnrichCompanyRequest,
    BulkEnrichCompanyResponse,
    BulkEnrichPersonRequest,
    BulkEnrichPersonResponse,
    BulkPersonEnrichData,
    CompanyEnrichData,
    EnrichCompanyRequest,
    EnrichCompanyResponse,
    EnrichPersonRequest,
    EnrichPersonResponse,
    PersonEnrichData,
    RateLimitInfo,
    SearchCompanyRequest,
    SearchCompanyResponse,
    SearchFilters,
    SearchPersonRequest,
    SearchPersonResponse,
)

logger = logging.getLogger(__name__)


class ProspeoError(Exception):
    """Base exception for Prospeo API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ProspeoAuthError(ProspeoError):
    """Authentication error (401)."""

    pass


class ProspeoRateLimitError(ProspeoError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, rate_limit_info: RateLimitInfo | None = None):
        super().__init__(message, status_code=429, error_code="RATE_LIMITED")
        self.rate_limit_info = rate_limit_info


class ProspeoInsufficientCreditsError(ProspeoError):
    """Insufficient credits (400)."""

    pass


class ProspeoClient:
    """
    Async HTTP client for the Prospeo API.

    Provides methods for all Prospeo endpoints:
    - Account information
    - Person enrichment (single and bulk)
    - Company enrichment (single and bulk)
    - Person search
    - Company search
    """

    BASE_URL = "https://api.prospeo.io"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize the Prospeo client.

        Args:
            api_key: Your Prospeo API key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._last_rate_limit_info: RateLimitInfo | None = None

    async def __aenter__(self) -> "ProspeoClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "X-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def rate_limit_info(self) -> RateLimitInfo | None:
        """Get the rate limit info from the last request."""
        return self._last_rate_limit_info

    def _extract_rate_limit_info(self, headers: httpx.Headers) -> RateLimitInfo:
        """Extract rate limit information from response headers."""
        return RateLimitInfo(
            daily_request_left=_safe_int(headers.get("x-daily-request-left")),
            minute_request_left=_safe_int(headers.get("x-minute-request-left")),
            daily_reset_seconds=_safe_int(headers.get("x-daily-reset-seconds")),
            minute_reset_seconds=_safe_int(headers.get("x-minute-reset-seconds")),
            daily_rate_limit=_safe_int(headers.get("x-daily-rate-limit")),
            minute_rate_limit=_safe_int(headers.get("x-minute-rate-limit")),
            second_rate_limit=_safe_int(headers.get("x-second-rate-limit")),
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the API."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        response = await self._client.request(
            method=method,
            url=endpoint,
            json=json,
        )

        # Extract rate limit info
        self._last_rate_limit_info = self._extract_rate_limit_info(response.headers)

        # Handle errors
        if response.status_code == 401:
            raise ProspeoAuthError(
                "Invalid API key",
                status_code=401,
                error_code="INVALID_API_KEY",
            )

        if response.status_code == 429:
            raise ProspeoRateLimitError(
                "Rate limit exceeded",
                rate_limit_info=self._last_rate_limit_info,
            )

        data = response.json()

        if response.status_code == 400:
            error_code = data.get("code") or data.get("error_code")
            message = data.get("message", "Bad request")

            if error_code == "INSUFFICIENT_CREDITS":
                raise ProspeoInsufficientCreditsError(
                    message,
                    status_code=400,
                    error_code=error_code,
                )

            raise ProspeoError(
                message,
                status_code=400,
                error_code=error_code,
            )

        return data

    # ========================================================================
    # Account Endpoints
    # ========================================================================

    async def get_account_info(self) -> AccountInfoResponse:
        """
        Get account information including credits and plan details.

        Returns:
            AccountInfoResponse with current plan and credit usage

        Note:
            This endpoint is free to use.
        """
        data = await self._request("GET", "/account-information")
        return AccountInfoResponse.model_validate(data)

    # ========================================================================
    # Person Enrichment Endpoints
    # ========================================================================

    async def enrich_person(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        linkedin_url: str | None = None,
        email: str | None = None,
        company_name: str | None = None,
        company_website: str | None = None,
        company_linkedin_url: str | None = None,
        person_id: str | None = None,
        only_verified_email: bool = False,
        enrich_mobile: bool = False,
        only_verified_mobile: bool = False,
    ) -> EnrichPersonResponse:
        """
        Enrich a single person with email, mobile, and B2B data.

        Provide at least one of:
        - first_name + last_name + company identifier
        - full_name + company identifier
        - linkedin_url alone
        - email alone
        - person_id alone

        Args:
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)
            linkedin_url: LinkedIn profile URL
            email: Work email address
            company_name: Company name
            company_website: Company domain
            company_linkedin_url: Company LinkedIn URL
            person_id: ID from search-person endpoint
            only_verified_email: Only return verified emails
            enrich_mobile: Include mobile enrichment
            only_verified_mobile: Only return verified mobiles

        Returns:
            EnrichPersonResponse with enriched person and company data

        Cost:
            1 credit per match (no charge if no match)
        """
        request = EnrichPersonRequest(
            data=PersonEnrichData(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                linkedin_url=linkedin_url,
                email=email,
                company_name=company_name,
                company_website=company_website,
                company_linkedin_url=company_linkedin_url,
                person_id=person_id,
            ),
            only_verified_email=only_verified_email,
            enrich_mobile=enrich_mobile,
            only_verified_mobile=only_verified_mobile,
        )

        data = await self._request(
            "POST",
            "/enrich-person",
            json=request.model_dump(exclude_none=True),
        )
        return EnrichPersonResponse.model_validate(data)

    async def bulk_enrich_persons(
        self,
        persons: list[dict[str, str]],
        *,
        only_verified_email: bool = False,
        enrich_mobile: bool = False,
        only_verified_mobile: bool = False,
    ) -> BulkEnrichPersonResponse:
        """
        Enrich up to 50 persons at once.

        Each person dict must include an 'identifier' field plus at least one of:
        - first_name + last_name + company identifier
        - full_name + company identifier
        - linkedin_url alone
        - email alone
        - person_id alone

        Args:
            persons: List of person dicts (max 50). Each must have 'identifier'.
            only_verified_email: Only return verified emails
            enrich_mobile: Include mobile enrichment
            only_verified_mobile: Only return verified mobiles

        Returns:
            BulkEnrichPersonResponse with matched, not_matched, and invalid lists

        Cost:
            1 credit per matched record
        """
        if len(persons) > 50:
            raise ValueError("Maximum 50 persons per request")

        request = BulkEnrichPersonRequest(
            data=[BulkPersonEnrichData(**p) for p in persons],
            only_verified_email=only_verified_email,
            enrich_mobile=enrich_mobile,
            only_verified_mobile=only_verified_mobile,
        )

        data = await self._request(
            "POST",
            "/bulk-enrich-person",
            json=request.model_dump(exclude_none=True),
        )
        return BulkEnrichPersonResponse.model_validate(data)

    # ========================================================================
    # Company Enrichment Endpoints
    # ========================================================================

    async def enrich_company(
        self,
        *,
        company_website: str | None = None,
        company_linkedin_url: str | None = None,
        company_name: str | None = None,
    ) -> EnrichCompanyResponse:
        """
        Enrich a single company with funding, technology, and 50+ data points.

        Provide at least one identifier. Using company_website is recommended.

        Args:
            company_website: Company domain (recommended)
            company_linkedin_url: Company LinkedIn URL
            company_name: Company name (avoid using alone)

        Returns:
            EnrichCompanyResponse with enriched company data

        Cost:
            1 credit per match (free for duplicates previously enriched)
        """
        request = EnrichCompanyRequest(
            data=CompanyEnrichData(
                company_website=company_website,
                company_linkedin_url=company_linkedin_url,
                company_name=company_name,
            )
        )

        data = await self._request(
            "POST",
            "/enrich-company",
            json=request.model_dump(exclude_none=True),
        )
        return EnrichCompanyResponse.model_validate(data)

    async def bulk_enrich_companies(
        self,
        companies: list[dict[str, str]],
    ) -> BulkEnrichCompanyResponse:
        """
        Enrich up to 50 companies at once.

        Each company dict must include an 'identifier' field plus at least one of:
        - company_website (recommended)
        - company_linkedin_url
        - company_name

        Args:
            companies: List of company dicts (max 50). Each must have 'identifier'.

        Returns:
            BulkEnrichCompanyResponse with matched, not_matched, and invalid lists

        Cost:
            1 credit per matched record
        """
        if len(companies) > 50:
            raise ValueError("Maximum 50 companies per request")

        request = BulkEnrichCompanyRequest(
            data=[BulkCompanyEnrichData(**c) for c in companies],
        )

        data = await self._request(
            "POST",
            "/bulk-enrich-company",
            json=request.model_dump(exclude_none=True),
        )
        return BulkEnrichCompanyResponse.model_validate(data)

    # ========================================================================
    # Search Endpoints
    # ========================================================================

    async def search_persons(
        self,
        filters: dict[str, Any],
        *,
        page: int = 1,
    ) -> SearchPersonResponse:
        """
        Search 200M+ contacts with 30+ filters.

        Note: Email and mobile fields are excluded from results.
        Use the person_id with enrich_person() to reveal them.

        Args:
            filters: Filter configuration (see SearchFilters for options)
            page: Page number (default 1, max 1000)

        Returns:
            SearchPersonResponse with results and pagination

        Cost:
            1 credit per search (covers 25 results)
        """
        request = SearchPersonRequest(
            filters=SearchFilters(**filters),
            page=page,
        )

        data = await self._request(
            "POST",
            "/search-person",
            json=request.model_dump(exclude_none=True),
        )
        return SearchPersonResponse.model_validate(data)

    async def search_companies(
        self,
        filters: dict[str, Any],
        *,
        page: int = 1,
    ) -> SearchCompanyResponse:
        """
        Search 30M+ companies with filters.

        Args:
            filters: Filter configuration (see SearchFilters for options)
            page: Page number (default 1, max 1000)

        Returns:
            SearchCompanyResponse with results and pagination

        Cost:
            1 credit per search (covers 25 results)
        """
        request = SearchCompanyRequest(
            filters=SearchFilters(**filters),
            page=page,
        )

        data = await self._request(
            "POST",
            "/search-company",
            json=request.model_dump(exclude_none=True),
        )
        return SearchCompanyResponse.model_validate(data)


def _safe_int(value: str | None) -> int | None:
    """Safely convert a string to int."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
