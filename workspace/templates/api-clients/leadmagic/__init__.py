"""
LeadMagic API Client.

A typed Python client for the LeadMagic B2B data enrichment API.

Usage:
    from leadmagic import LeadMagicClient

    client = LeadMagicClient(api_key="your-api-key")

    # Check credits
    credits = client.check_credits()

    # Find email
    result = client.find_email(first_name="Bill", last_name="Gates", domain="microsoft.com")
"""

from .client import (
    LeadMagicClient,
    AsyncLeadMagicClient,
    LeadMagicError,
    LeadMagicAuthError,
    LeadMagicInsufficientCreditsError,
    LeadMagicNotFoundError,
    LeadMagicRateLimitError,
)

from .models import (
    # Request models
    EmailFinderRequest,
    EmailValidateRequest,
    MobileFinderRequest,
    ProfileSearchRequest,
    PersonalEmailRequest,
    RoleFinderRequest,
    CompanySearchRequest,
    CompetitorsSearchRequest,
    # Response models
    CreditsResponse,
    EmailFinderResponse,
    EmailValidateResponse,
    MobileFinderResponse,
    ProfileSearchResponse,
    PersonalEmailResponse,
    RoleFinderResponse,
    CompanySearchResponse,
    CompetitorsSearchResponse,
    # Shared models
    CompanyLocation,
    PersonalWebsite,
    WorkExperience,
    Education,
    Certification,
    Honor,
    CompanyLocationDetail,
    EmployeeCountRange,
    FoundedOn,
    CompetitorInfo,
)

__all__ = [
    # Clients
    "LeadMagicClient",
    "AsyncLeadMagicClient",
    # Errors
    "LeadMagicError",
    "LeadMagicAuthError",
    "LeadMagicInsufficientCreditsError",
    "LeadMagicNotFoundError",
    "LeadMagicRateLimitError",
    # Request models
    "EmailFinderRequest",
    "EmailValidateRequest",
    "MobileFinderRequest",
    "ProfileSearchRequest",
    "PersonalEmailRequest",
    "RoleFinderRequest",
    "CompanySearchRequest",
    "CompetitorsSearchRequest",
    # Response models
    "CreditsResponse",
    "EmailFinderResponse",
    "EmailValidateResponse",
    "MobileFinderResponse",
    "ProfileSearchResponse",
    "PersonalEmailResponse",
    "RoleFinderResponse",
    "CompanySearchResponse",
    "CompetitorsSearchResponse",
    # Shared models
    "CompanyLocation",
    "PersonalWebsite",
    "WorkExperience",
    "Education",
    "Certification",
    "Honor",
    "CompanyLocationDetail",
    "EmployeeCountRange",
    "FoundedOn",
    "CompetitorInfo",
]
