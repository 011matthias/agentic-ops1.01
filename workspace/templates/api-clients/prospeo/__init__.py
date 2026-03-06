"""
Prospeo API Client

A Python client for the Prospeo B2B enrichment and search API.
"""

from .client import (
    ProspeoAuthError,
    ProspeoClient,
    ProspeoError,
    ProspeoInsufficientCreditsError,
    ProspeoRateLimitError,
)
from .models import (
    AccountInfo,
    AccountInfoResponse,
    BulkEnrichCompanyResponse,
    BulkEnrichPersonResponse,
    Company,
    EnrichCompanyResponse,
    EnrichPersonResponse,
    MatchedCompany,
    MatchedPerson,
    Pagination,
    Person,
    RateLimitInfo,
    SearchCompanyResponse,
    SearchPersonResponse,
)

__all__ = [
    # Client
    "ProspeoClient",
    # Exceptions
    "ProspeoError",
    "ProspeoAuthError",
    "ProspeoRateLimitError",
    "ProspeoInsufficientCreditsError",
    # Response Models
    "AccountInfo",
    "AccountInfoResponse",
    "EnrichPersonResponse",
    "BulkEnrichPersonResponse",
    "EnrichCompanyResponse",
    "BulkEnrichCompanyResponse",
    "SearchPersonResponse",
    "SearchCompanyResponse",
    # Data Models
    "Person",
    "Company",
    "MatchedPerson",
    "MatchedCompany",
    "Pagination",
    "RateLimitInfo",
]
