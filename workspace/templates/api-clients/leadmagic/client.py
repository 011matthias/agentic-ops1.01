"""
LeadMagic API Client.

A typed Python client for the LeadMagic B2B data enrichment API.

API Documentation: https://leadmagic.io/docs/v1/reference/check-credits
Base URL: https://api.leadmagic.io
Authentication: X-API-Key header

Usage:
    from leadmagic.client import LeadMagicClient

    client = LeadMagicClient(api_key="your-api-key")

    # Check credits
    credits = client.check_credits()
    print(f"Available credits: {credits.credits}")

    # Find email
    result = client.find_email(
        first_name="Bill",
        last_name="Gates",
        domain="microsoft.com"
    )
    print(f"Email: {result.email}, Status: {result.status}")
"""

import httpx
from typing import Optional

from .models import (
    CreditsResponse,
    EmailFinderRequest,
    EmailFinderResponse,
    EmailValidateRequest,
    EmailValidateResponse,
    MobileFinderRequest,
    MobileFinderResponse,
    ProfileSearchRequest,
    ProfileSearchResponse,
    PersonalEmailRequest,
    PersonalEmailResponse,
    RoleFinderRequest,
    RoleFinderResponse,
    CompanySearchRequest,
    CompanySearchResponse,
    CompetitorsSearchRequest,
    CompetitorsSearchResponse,
)


class LeadMagicError(Exception):
    """Base exception for LeadMagic API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class LeadMagicAuthError(LeadMagicError):
    """Authentication error (401)."""
    pass


class LeadMagicInsufficientCreditsError(LeadMagicError):
    """Insufficient credits error (402)."""
    pass


class LeadMagicNotFoundError(LeadMagicError):
    """Resource not found error (404)."""
    pass


class LeadMagicRateLimitError(LeadMagicError):
    """Rate limit exceeded error (429)."""
    pass


class LeadMagicClient:
    """
    LeadMagic API client for B2B data enrichment.

    Features:
    - Email finder: Find work emails by name + company
    - Email validation: Validate email addresses
    - Mobile finder: Find mobile numbers
    - Profile search: Get LinkedIn profile data
    - Personal email: Find personal emails
    - Role finder: Find people by job title in company
    - Company search: Get company information
    - Competitors search: Find company competitors

    Rate Limits (requests per minute):
    - Email Finder: 400
    - Email Validation: 1000
    - Mobile Finder: 300
    - Profile Search: 300
    - Personal Email: 500
    - Role Finder: 500
    - Company Search: 300
    """

    BASE_URL = "https://api.leadmagic.io"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the LeadMagic client.

        Args:
            api_key: Your LeadMagic API key
            timeout: Request timeout in seconds (default: 30)
            base_url: Override the base URL (optional)
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "LeadMagicClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
        except Exception:
            error_data = {"message": response.text}

        message = error_data.get("message", f"HTTP {response.status_code}")

        if response.status_code == 400:
            raise LeadMagicError(message, response.status_code, error_data)
        elif response.status_code == 401:
            raise LeadMagicAuthError(message, response.status_code, error_data)
        elif response.status_code == 402:
            raise LeadMagicInsufficientCreditsError(message, response.status_code, error_data)
        elif response.status_code == 404:
            raise LeadMagicNotFoundError(message, response.status_code, error_data)
        elif response.status_code == 429:
            raise LeadMagicRateLimitError(message, response.status_code, error_data)
        else:
            raise LeadMagicError(message, response.status_code, error_data)

    # =========================================================================
    # Credits
    # =========================================================================

    def check_credits(self) -> CreditsResponse:
        """
        Check available credits.

        Returns:
            CreditsResponse with current credit balance
        """
        response = self.client.post("/credits")
        data = self._handle_response(response)
        return CreditsResponse(**data)

    # =========================================================================
    # People Enrichment
    # =========================================================================

    def find_email(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        domain: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> EmailFinderResponse:
        """
        Find a work email address.

        You must provide either domain or company_name. Domain is more accurate.

        Costs: 1 credit per valid email (no charge for catch-all)
        Rate limit: 400 requests/minute

        Args:
            first_name: Person's first name
            last_name: Person's last name (optional)
            domain: Company domain (preferred, e.g. "microsoft.com")
            company_name: Company name (e.g. "Microsoft")

        Returns:
            EmailFinderResponse with email and validation status

        Status codes returned:
            - valid: 100% valid email, safe to send
            - valid_catch_all: Valid with engagement data, <5% bounce rate
            - catch_all: Risky, requires further validation
            - not_found: No email found
        """
        request = EmailFinderRequest(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            company_name=company_name,
        )
        response = self.client.post(
            "/email-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return EmailFinderResponse(**data)

    def validate_email(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> EmailValidateResponse:
        """
        Validate an email address.

        Costs: 1 credit per 20 validations
        Rate limit: 1000 requests/minute

        Args:
            email: Email address to validate
            first_name: Person's first name (optional)
            last_name: Person's last name (optional)

        Returns:
            EmailValidateResponse with validation status

        Status codes returned:
            - valid: 100% valid, safe to email
            - valid_catch_all: Valid with engagement data, <5% bounce rate
            - catch_all: Risky (free, no charge)
            - unknown: Domain did not respond (free, no charge)
            - invalid: Not valid, do not email
        """
        request = EmailValidateRequest(
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        response = self.client.post(
            "/email-validate",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return EmailValidateResponse(**data)

    def find_mobile(
        self,
        profile_url: Optional[str] = None,
        work_email: Optional[str] = None,
        personal_email: Optional[str] = None,
    ) -> MobileFinderResponse:
        """
        Find a mobile phone number.

        You must provide at least one of: profile_url, work_email, or personal_email.

        Costs: 5 credits per valid mobile found
        Rate limit: 300 requests/minute

        Args:
            profile_url: LinkedIn profile URL or username
            work_email: Work email address
            personal_email: Personal email address

        Returns:
            MobileFinderResponse with mobile number
        """
        request = MobileFinderRequest(
            profile_url=profile_url,
            work_email=work_email,
            personal_email=personal_email,
        )
        response = self.client.post(
            "/mobile-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return MobileFinderResponse(**data)

    def search_profile(self, profile_url: str) -> ProfileSearchResponse:
        """
        Get LinkedIn profile information.

        Costs: 1 credit per profile search
        Rate limit: 300 requests/minute

        Args:
            profile_url: LinkedIn profile URL or username
                (e.g. "jesseoue", "in/jesseoue", "linkedin.com/in/jesseoue")

        Returns:
            ProfileSearchResponse with full profile data including:
            - Name and title
            - Company info
            - Work experience
            - Education
            - Certifications
            - Honors
        """
        request = ProfileSearchRequest(profile_url=profile_url)
        response = self.client.post(
            "/profile-search",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return ProfileSearchResponse(**data)

    def find_personal_email(self, profile_url: str) -> PersonalEmailResponse:
        """
        Find personal email addresses for a LinkedIn profile.

        Costs: 2 credits per found personal email
        Rate limit: 500 requests/minute

        Args:
            profile_url: LinkedIn profile URL

        Returns:
            PersonalEmailResponse with personal email addresses
        """
        request = PersonalEmailRequest(profile_url=profile_url)
        response = self.client.post(
            "/personal-email",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return PersonalEmailResponse(**data)

    def find_role(
        self,
        job_title: str,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None,
    ) -> RoleFinderResponse:
        """
        Find a person by job title in a company.

        Costs: 2 credits per found role
        Rate limit: 500 requests/minute

        Args:
            job_title: Job title to search (e.g. "ceo", "cto", "head of sales")
            company_name: Company name
            company_domain: Company domain

        Returns:
            RoleFinderResponse with person's name and profile URL
        """
        request = RoleFinderRequest(
            job_title=job_title,
            company_name=company_name,
            company_domain=company_domain,
        )
        response = self.client.post(
            "/role-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return RoleFinderResponse(**data)

    # =========================================================================
    # Company Enrichment
    # =========================================================================

    def search_company(
        self,
        profile_url: Optional[str] = None,
        company_domain: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> CompanySearchResponse:
        """
        Get company information.

        You must provide at least one of: profile_url, company_domain, or company_name.

        Costs: 1 credit per company search
        Rate limit: 300 requests/minute

        Args:
            profile_url: LinkedIn company URL
            company_domain: Company domain (e.g. "stripe.com")
            company_name: Company name (e.g. "Stripe")

        Returns:
            CompanySearchResponse with comprehensive company data including:
            - Name, description, tagline
            - Employee count and range
            - Locations and headquarters
            - Industry and specialties
            - Funding information
            - Social media URLs
            - Competitors
        """
        request = CompanySearchRequest(
            profile_url=profile_url,
            company_domain=company_domain,
            company_name=company_name,
        )
        response = self.client.post(
            "/company-search",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return CompanySearchResponse(**data)

    def search_competitors(
        self,
        company_domain: Optional[str] = None,
        profile_url: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> CompetitorsSearchResponse:
        """
        Find company competitors.

        You must provide at least one of: company_domain, profile_url, or company_name.

        Args:
            company_domain: Company domain (e.g. "gong.io")
            profile_url: LinkedIn company URL
            company_name: Company name

        Returns:
            CompetitorsSearchResponse with list of competitors
        """
        request = CompetitorsSearchRequest(
            company_domain=company_domain,
            profile_url=profile_url,
            company_name=company_name,
        )
        response = self.client.post(
            "/competitors",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return CompetitorsSearchResponse(**data)


# =============================================================================
# Async Client
# =============================================================================


class AsyncLeadMagicClient:
    """
    Async LeadMagic API client.

    Same features as LeadMagicClient but with async/await support.

    Usage:
        async with AsyncLeadMagicClient(api_key="your-key") as client:
            credits = await client.check_credits()
    """

    BASE_URL = "https://api.leadmagic.io"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncLeadMagicClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json()
        except Exception:
            error_data = {"message": response.text}

        message = error_data.get("message", f"HTTP {response.status_code}")

        if response.status_code == 400:
            raise LeadMagicError(message, response.status_code, error_data)
        elif response.status_code == 401:
            raise LeadMagicAuthError(message, response.status_code, error_data)
        elif response.status_code == 402:
            raise LeadMagicInsufficientCreditsError(message, response.status_code, error_data)
        elif response.status_code == 404:
            raise LeadMagicNotFoundError(message, response.status_code, error_data)
        elif response.status_code == 429:
            raise LeadMagicRateLimitError(message, response.status_code, error_data)
        else:
            raise LeadMagicError(message, response.status_code, error_data)

    async def check_credits(self) -> CreditsResponse:
        """Check available credits."""
        response = await self.client.post("/credits")
        data = self._handle_response(response)
        return CreditsResponse(**data)

    async def find_email(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        domain: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> EmailFinderResponse:
        """Find a work email address."""
        request = EmailFinderRequest(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            company_name=company_name,
        )
        response = await self.client.post(
            "/email-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return EmailFinderResponse(**data)

    async def validate_email(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> EmailValidateResponse:
        """Validate an email address."""
        request = EmailValidateRequest(
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        response = await self.client.post(
            "/email-validate",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return EmailValidateResponse(**data)

    async def find_mobile(
        self,
        profile_url: Optional[str] = None,
        work_email: Optional[str] = None,
        personal_email: Optional[str] = None,
    ) -> MobileFinderResponse:
        """Find a mobile phone number."""
        request = MobileFinderRequest(
            profile_url=profile_url,
            work_email=work_email,
            personal_email=personal_email,
        )
        response = await self.client.post(
            "/mobile-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return MobileFinderResponse(**data)

    async def search_profile(self, profile_url: str) -> ProfileSearchResponse:
        """Get LinkedIn profile information."""
        request = ProfileSearchRequest(profile_url=profile_url)
        response = await self.client.post(
            "/profile-search",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return ProfileSearchResponse(**data)

    async def find_personal_email(self, profile_url: str) -> PersonalEmailResponse:
        """Find personal email addresses for a LinkedIn profile."""
        request = PersonalEmailRequest(profile_url=profile_url)
        response = await self.client.post(
            "/personal-email",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return PersonalEmailResponse(**data)

    async def find_role(
        self,
        job_title: str,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None,
    ) -> RoleFinderResponse:
        """Find a person by job title in a company."""
        request = RoleFinderRequest(
            job_title=job_title,
            company_name=company_name,
            company_domain=company_domain,
        )
        response = await self.client.post(
            "/role-finder",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return RoleFinderResponse(**data)

    async def search_company(
        self,
        profile_url: Optional[str] = None,
        company_domain: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> CompanySearchResponse:
        """Get company information."""
        request = CompanySearchRequest(
            profile_url=profile_url,
            company_domain=company_domain,
            company_name=company_name,
        )
        response = await self.client.post(
            "/company-search",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return CompanySearchResponse(**data)

    async def search_competitors(
        self,
        company_domain: Optional[str] = None,
        profile_url: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> CompetitorsSearchResponse:
        """Find company competitors."""
        request = CompetitorsSearchRequest(
            company_domain=company_domain,
            profile_url=profile_url,
            company_name=company_name,
        )
        response = await self.client.post(
            "/competitors",
            json=request.model_dump(exclude_none=True),
        )
        data = self._handle_response(response)
        return CompetitorsSearchResponse(**data)
