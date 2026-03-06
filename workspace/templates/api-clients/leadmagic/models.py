"""
Pydantic models for LeadMagic API.

API Documentation: https://leadmagic.io/docs/v1/reference/check-credits
"""

from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Shared Models
# =============================================================================


class CompanyLocation(BaseModel):
    """Company location details."""

    name: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    metro: Optional[str] = None
    country: Optional[str] = None
    continent: Optional[str] = None
    street_address: Optional[str] = None
    address_line_2: Optional[str] = None
    postal_code: Optional[str] = None
    geo: Optional[str] = None


class PersonalWebsite(BaseModel):
    """Personal website details."""

    name: Optional[str] = None
    link: Optional[str] = None


class WorkExperience(BaseModel):
    """Work experience entry."""

    position_title: Optional[str] = None
    company_name: Optional[str] = None
    employment_period: Optional[str] = None
    company_website: Optional[str] = None
    company_logo_url: Optional[str] = None


class Education(BaseModel):
    """Education entry."""

    institution_name: Optional[str] = None
    degree: Optional[str] = None
    attendance_period: Optional[str] = None


class Certification(BaseModel):
    """Certification entry."""

    certification_name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None


class Honor(BaseModel):
    """Honor/award entry."""

    title: Optional[str] = None
    description: Optional[str] = None


class CompanyLocationDetail(BaseModel):
    """Detailed company location."""

    country: Optional[str] = None
    city: Optional[str] = None
    geographicArea: Optional[str] = None
    postalCode: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    description: Optional[str] = None
    headquarter: Optional[bool] = None
    localizedName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class EmployeeCountRange(BaseModel):
    """Employee count range."""

    start: Optional[int] = None
    end: Optional[int] = None


class FoundedOn(BaseModel):
    """Company founding date."""

    month: Optional[int] = None
    year: Optional[int] = None
    day: Optional[int] = None


# =============================================================================
# Request Models
# =============================================================================


class EmailFinderRequest(BaseModel):
    """Request for email finder endpoint."""

    first_name: str = Field(..., description="Person's first name")
    last_name: Optional[str] = Field(None, description="Person's last name (optional)")
    domain: Optional[str] = Field(
        None, description="Company domain name (preferred, more accurate)"
    )
    company_name: Optional[str] = Field(
        None, description="Company name (less accurate than domain)"
    )


class EmailValidateRequest(BaseModel):
    """Request for email validation endpoint."""

    email: str = Field(..., description="Email address to validate")
    first_name: Optional[str] = Field(None, description="Person's first name")
    last_name: Optional[str] = Field(None, description="Person's last name")


class MobileFinderRequest(BaseModel):
    """Request for mobile finder endpoint."""

    profile_url: Optional[str] = Field(None, description="LinkedIn profile URL or username")
    work_email: Optional[str] = Field(None, description="Work email address")
    personal_email: Optional[str] = Field(None, description="Personal email address")


class ProfileSearchRequest(BaseModel):
    """Request for profile search endpoint."""

    profile_url: str = Field(
        ...,
        description="LinkedIn profile URL or username (e.g. 'jesseoue', 'linkedin.com/in/jesseoue')",
    )


class PersonalEmailRequest(BaseModel):
    """Request for personal email finder endpoint."""

    profile_url: str = Field(..., description="LinkedIn profile URL")


class RoleFinderRequest(BaseModel):
    """Request for role finder endpoint."""

    company_name: Optional[str] = Field(None, description="Company name")
    company_domain: Optional[str] = Field(None, description="Company domain")
    job_title: str = Field(..., description="Job title to search for (e.g. 'ceo', 'cto')")


class CompanySearchRequest(BaseModel):
    """Request for company search endpoint."""

    profile_url: Optional[str] = Field(None, description="LinkedIn company URL")
    company_domain: Optional[str] = Field(None, description="Company domain")
    company_name: Optional[str] = Field(None, description="Company name")


class CompetitorsSearchRequest(BaseModel):
    """Request for competitors search endpoint."""

    company_domain: Optional[str] = Field(None, description="Company domain")
    profile_url: Optional[str] = Field(None, description="LinkedIn company URL")
    company_name: Optional[str] = Field(None, description="Company name")


# =============================================================================
# Response Models
# =============================================================================


class CreditsResponse(BaseModel):
    """Response from credits check endpoint."""

    credits: float


class EmailFinderResponse(BaseModel):
    """Response from email finder endpoint."""

    email: Optional[str] = None
    status: Optional[str] = Field(
        None, description="valid, valid_catch_all, catch_all, not_found"
    )
    credits_consumed: Optional[int] = None
    message: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    domain: Optional[str] = None
    is_domain_catch_all: Optional[bool] = None
    mx_record: Optional[str] = None
    mx_provider: Optional[str] = None
    mx_security_gateway: Optional[bool] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    company_size: Optional[str] = None
    company_founded: Optional[int] = None
    company_location: Optional[CompanyLocation] = None
    company_linkedin_url: Optional[str] = None
    company_linkedin_id: Optional[str] = None
    company_facebook_url: Optional[str] = None
    company_twitter_url: Optional[str] = None
    company_type: Optional[str] = None


class EmailValidateResponse(BaseModel):
    """Response from email validation endpoint."""

    email: Optional[str] = None
    email_status: Optional[str] = Field(
        None, description="valid, valid_catch_all, catch_all, unknown, invalid"
    )
    credits_consumed: Optional[float] = None
    message: Optional[str] = None
    is_domain_catch_all: Optional[bool] = None
    mx_record: Optional[str] = None
    mx_provider: Optional[str] = None
    mx_security_gateway: Optional[bool] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    company_size: Optional[str] = None
    company_founded: Optional[int] = None
    company_location: Optional[CompanyLocation] = None
    company_linkedin_url: Optional[str] = None
    company_linkedin_id: Optional[str] = None
    company_facebook_url: Optional[str] = None
    company_twitter_url: Optional[str] = None
    company_type: Optional[str] = None


class MobileFinderResponse(BaseModel):
    """Response from mobile finder endpoint."""

    profile_url: Optional[str] = None
    mobile_number: Optional[int] = None
    credits_consumed: Optional[int] = None


class ProfileSearchResponse(BaseModel):
    """Response from profile search endpoint."""

    profile_url: Optional[str] = None
    credits_consumed: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    professional_title: Optional[str] = None
    bio: Optional[str] = None
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    company_website: Optional[str] = None
    total_tenure_months: Optional[str] = None
    total_tenure_days: Optional[str] = None
    total_tenure_years: Optional[str] = None
    followers_range: Optional[str] = None
    personal_website: Optional[PersonalWebsite] = None
    country: Optional[str] = None
    location: Optional[str] = None
    work_experience: Optional[list[WorkExperience]] = None
    education: Optional[list[Education]] = None
    certifications: Optional[list[Certification]] = None
    honors: Optional[list[Honor]] = None


class PersonalEmailResponse(BaseModel):
    """Response from personal email finder endpoint."""

    profile_url: Optional[str] = None
    credits_consumed: Optional[int] = None
    message: Optional[str] = None
    name: Optional[str] = None
    first_personal_email: Optional[str] = None
    personal_emails: Optional[list[str]] = None


class RoleFinderResponse(BaseModel):
    """Response from role finder endpoint."""

    name: Optional[str] = None
    profile_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    message: Optional[str] = None
    credits_consumed: Optional[int] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None


class CompanySearchResponse(BaseModel):
    """Response from company search endpoint."""

    companyName: Optional[str] = None
    companyId: Optional[int] = None
    locations: Optional[list[CompanyLocationDetail]] = None
    employeeCount: Optional[int] = None
    specialities: Optional[list[str]] = None
    employeeCountRange: Optional[EmployeeCountRange] = None
    tagline: Optional[str] = None
    followerCount: Optional[int] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    websiteUrl: Optional[str] = None
    headquarter: Optional[CompanyLocationDetail] = None
    foundedOn: Optional[FoundedOn] = None
    universalName: Optional[str] = None
    hashtag: Optional[str] = None
    url: Optional[str] = None
    logo_url: Optional[str] = None
    founded_year: Optional[str] = None
    ownership_status: Optional[str] = None
    revenue: Optional[float] = None
    revenue_formatted: Optional[str] = None
    employee_range: Optional[str] = None
    total_funding: Optional[str] = None
    funding_rounds: Optional[int] = None
    last_funding_round: Optional[str] = None
    last_funding_amount: Optional[float] = None
    last_funding_date: Optional[str] = None
    competitors: Optional[list[str]] = None
    acquisitions_count: Optional[int] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    stock_ticker: Optional[str] = None


class CompetitorInfo(BaseModel):
    """Competitor information."""

    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None


class CompetitorsSearchResponse(BaseModel):
    """Response from competitors search endpoint."""

    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    competitors: Optional[list[CompetitorInfo]] = None
    credits_consumed: Optional[int] = None
