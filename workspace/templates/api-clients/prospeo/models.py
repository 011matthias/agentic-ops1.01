"""
Prospeo API - Pydantic Models
Generated from: https://prospeo.io/api-docs
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Common Types
# ============================================================================


class RateLimitInfo(BaseModel):
    """Rate limit information from response headers."""

    daily_request_left: int | None = None
    minute_request_left: int | None = None
    daily_reset_seconds: int | None = None
    minute_reset_seconds: int | None = None
    daily_rate_limit: int | None = None
    minute_rate_limit: int | None = None
    second_rate_limit: int | None = None


class Location(BaseModel):
    """Location information for person or company."""

    country: str | None = None
    state: str | None = None
    city: str | None = None
    address: str | None = None


class Phone(BaseModel):
    """Phone number with various formats."""

    raw: str | None = None
    e164: str | None = None
    national: str | None = None
    international: str | None = None


class EmailTech(BaseModel):
    """Email technology information."""

    domain: str | None = None
    mx_provider: str | None = None


class Funding(BaseModel):
    """Company funding information."""

    count: int | None = None
    total_funding: int | None = None
    events: list[dict[str, Any]] | None = None


class Technology(BaseModel):
    """Company technology stack."""

    count: int | None = None
    names: list[str] | None = None
    categories: list[str] | None = None


class JobPostings(BaseModel):
    """Active job postings."""

    active_count: int | None = None
    titles: list[str] | None = None


class CompanyAttributes(BaseModel):
    """Company attribute flags."""

    is_b2b: bool | None = None
    has_demo: bool | None = None
    has_free_trial: bool | None = None
    has_self_serve: bool | None = None


# ============================================================================
# Person Models
# ============================================================================


class Person(BaseModel):
    """Enriched person data."""

    person_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    email_status: str | None = None
    mobile: str | None = None
    mobile_status: str | None = None
    linkedin_url: str | None = None
    title: str | None = None
    seniority: str | None = None
    department: str | None = None
    location: Location | None = None
    years_of_experience: int | None = None


class PersonEnrichData(BaseModel):
    """Data for enriching a person."""

    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    company_name: str | None = None
    company_website: str | None = None
    company_linkedin_url: str | None = None
    person_id: str | None = None


class BulkPersonEnrichData(PersonEnrichData):
    """Data for bulk enriching a person (includes identifier)."""

    identifier: str


# ============================================================================
# Company Models
# ============================================================================


class Company(BaseModel):
    """Enriched company data."""

    company_id: str | None = None
    name: str | None = None
    website: str | None = None
    domain: str | None = None
    description: str | None = None
    type: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    employee_range: str | None = None
    location: Location | None = None
    sic_codes: list[str] | None = None
    naics_codes: list[str] | None = None
    email_tech: EmailTech | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    facebook_url: str | None = None
    crunchbase_url: str | None = None
    instagram_url: str | None = None
    youtube_url: str | None = None
    phone_hq: Phone | None = None
    founded: int | None = None
    revenue_range: str | None = None
    keywords: list[str] | None = None
    logo_url: str | None = None
    attributes: CompanyAttributes | None = None
    funding: Funding | None = None
    technology: Technology | None = None
    job_postings: JobPostings | None = None


class CompanyEnrichData(BaseModel):
    """Data for enriching a company."""

    company_website: str | None = None
    company_linkedin_url: str | None = None
    company_name: str | None = None


class BulkCompanyEnrichData(CompanyEnrichData):
    """Data for bulk enriching a company (includes identifier)."""

    identifier: str


# ============================================================================
# Request Models
# ============================================================================


class EnrichPersonRequest(BaseModel):
    """Request for /enrich-person endpoint."""

    data: PersonEnrichData
    only_verified_email: bool = False
    enrich_mobile: bool = False
    only_verified_mobile: bool = False


class BulkEnrichPersonRequest(BaseModel):
    """Request for /bulk-enrich-person endpoint."""

    data: list[BulkPersonEnrichData] = Field(..., max_length=50)
    only_verified_email: bool = False
    enrich_mobile: bool = False
    only_verified_mobile: bool = False


class EnrichCompanyRequest(BaseModel):
    """Request for /enrich-company endpoint."""

    data: CompanyEnrichData


class BulkEnrichCompanyRequest(BaseModel):
    """Request for /bulk-enrich-company endpoint."""

    data: list[BulkCompanyEnrichData] = Field(..., max_length=50)


class SearchFilters(BaseModel):
    """Filters for search endpoints."""

    # Person filters
    person_seniority: dict[str, list[str]] | None = None
    person_departments: dict[str, list[str]] | None = None
    person_year_of_experience: dict[str, int] | None = None
    person_location: dict[str, list[str]] | None = None

    # Company filters
    company_industry: dict[str, list[str]] | None = None
    company_location: dict[str, list[str]] | None = None
    company_funding: dict[str, Any] | None = None
    company_technology: dict[str, list[str]] | None = None
    company_email_provider: dict[str, list[str]] | None = None
    company_naics: dict[str, list[str]] | None = None
    company_sics: dict[str, list[str]] | None = None
    company_employee_range: dict[str, list[str]] | None = None

    # Special filters (API-only, max 500)
    company_websites: list[str] | None = Field(None, max_length=500)
    company_names: list[str] | None = Field(None, max_length=500)

    class Config:
        extra = "allow"


class SearchPersonRequest(BaseModel):
    """Request for /search-person endpoint."""

    filters: SearchFilters
    page: int = 1


class SearchCompanyRequest(BaseModel):
    """Request for /search-company endpoint."""

    filters: SearchFilters
    page: int = 1


# ============================================================================
# Response Models
# ============================================================================


class Pagination(BaseModel):
    """Pagination information."""

    current_page: int
    per_page: int = 25
    total_page: int
    total_count: int


class AccountInfo(BaseModel):
    """Account information."""

    current_plan: str
    current_team_members: int
    remaining_credits: int
    used_credits: int
    next_quota_renewal_days: int
    next_quota_renewal_date: datetime


class AccountInfoResponse(BaseModel):
    """Response from /account-information endpoint."""

    error: bool
    response: AccountInfo


class EnrichPersonResponse(BaseModel):
    """Response from /enrich-person endpoint."""

    error: bool
    free_enrichment: bool | None = None
    person: Person | None = None
    company: Company | None = None


class MatchedPerson(BaseModel):
    """Matched person in bulk response."""

    identifier: str
    person: Person | None = None
    company: Company | None = None


class BulkEnrichPersonResponse(BaseModel):
    """Response from /bulk-enrich-person endpoint."""

    error: bool
    total_cost: int
    matched: list[MatchedPerson]
    not_matched: list[str]
    invalid_datapoints: list[str]


class EnrichCompanyResponse(BaseModel):
    """Response from /enrich-company endpoint."""

    error: bool
    free_enrichment: bool | None = None
    company: Company | None = None


class MatchedCompany(BaseModel):
    """Matched company in bulk response."""

    identifier: str
    company: Company | None = None


class BulkEnrichCompanyResponse(BaseModel):
    """Response from /bulk-enrich-company endpoint."""

    error: bool
    total_cost: int
    matched: list[MatchedCompany]
    not_matched: list[str]
    invalid_datapoints: list[str]


class SearchPersonResult(BaseModel):
    """Single result from person search."""

    person: Person | None = None
    company: Company | None = None


class SearchPersonResponse(BaseModel):
    """Response from /search-person endpoint."""

    error: bool
    results: list[SearchPersonResult]
    pagination: Pagination


class SearchCompanyResult(BaseModel):
    """Single result from company search."""

    company: Company | None = None


class SearchCompanyResponse(BaseModel):
    """Response from /search-company endpoint."""

    error: bool
    results: list[SearchCompanyResult]
    pagination: Pagination


# ============================================================================
# Error Models
# ============================================================================


class ProspeoErrorCode:
    """Known Prospeo error codes."""

    NO_MATCH = "NO_MATCH"
    NO_RESULTS = "NO_RESULTS"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_FILTERS = "INVALID_FILTERS"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_API_KEY = "INVALID_API_KEY"
    RATE_LIMITED = "RATE_LIMITED"


class ErrorResponse(BaseModel):
    """Error response from API."""

    error: bool = True
    message: str | None = None
    code: str | None = None
