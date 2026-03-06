"""
Smartlead API Pydantic Models

Generated from: https://api.smartlead.ai/reference/welcome
Base URL: https://server.smartlead.ai/api/v1
Auth: API key as query parameter (?api_key=xxx)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class LeadStatus(str, Enum):
    """Lead status in a campaign."""

    STARTED = "STARTED"  # Scheduled to start, yet to receive 1st email
    INPROGRESS = "INPROGRESS"  # Has received at least one email
    COMPLETED = "COMPLETED"  # Received all emails in campaign
    BLOCKED = "BLOCKED"  # Email bounced or in global block list
    PAUSED = "PAUSED"  # Paused, no further emails sent
    STOPPED = "STOPPED"  # Stopped, usually due to reply received


class VariantDistributionType(str, Enum):
    """A/B variant distribution strategy."""

    MANUAL_EQUAL = "MANUAL_EQUAL"  # Equal distribution across leads
    AI_EQUAL = "AI_EQUAL"  # AI-optimized, needs winning_metric_property
    MANUAL_PERCENTAGE = "MANUAL_PERCENTAGE"  # Custom % per variant


class WinningMetricProperty(str, Enum):
    """Metric for AI A/B testing optimization."""

    OPEN_RATE = "OPEN_RATE"
    CLICK_RATE = "CLICK_RATE"
    REPLY_RATE = "REPLY_RATE"
    POSITIVE_REPLY_RATE = "POSITIVE_REPLY_RATE"


class EmailType(str, Enum):
    """Type of email in conversation history."""

    SENT = "SENT"
    REPLY = "REPLY"


class LeadCategory(str, Enum):
    """Lead categorization after reply."""

    INTERESTED = "Interested"
    NOT_INTERESTED = "Not Interested"
    MEETING_BOOKED = "Meeting Booked"
    OUT_OF_OFFICE = "Out of Office"
    WRONG_PERSON = "Wrong Person"
    DO_NOT_CONTACT = "Do Not Contact"
    INFORMATION_REQUEST = "Information Request"


# --- Email Account Models ---


class EmailAccountBase(BaseModel):
    """Base email account fields."""

    from_name: str | None = Field(None, description="Sender display name")
    from_email: str | None = Field(None, description="Sender email address")
    smtp_host: str | None = Field(None, description="SMTP server host")
    smtp_port: int | None = Field(None, description="SMTP server port")
    smtp_username: str | None = Field(None, description="SMTP username")
    smtp_password: str | None = Field(None, description="SMTP password")
    imap_host: str | None = Field(None, description="IMAP server host")
    imap_port: int | None = Field(None, description="IMAP server port")
    imap_username: str | None = Field(None, description="IMAP username")
    imap_password: str | None = Field(None, description="IMAP password")
    max_email_per_day: int | None = Field(None, description="Daily send limit")
    warmup_enabled: bool | None = Field(None, description="Warmup enabled flag")
    signature: str | None = Field(None, description="Email signature HTML")


class EmailAccountCreate(EmailAccountBase):
    """Create a new email account."""

    from_name: str = Field(..., description="Sender display name")
    from_email: str = Field(..., description="Sender email address")


class EmailAccountUpdate(EmailAccountBase):
    """Update an existing email account."""

    pass


class EmailAccount(EmailAccountBase):
    """Email account response."""

    id: int = Field(..., description="Email account ID")
    from_name: str
    from_email: str
    is_connected: bool | None = Field(None, description="Connection status")
    warmup_reputation: float | None = Field(None, description="Warmup reputation score")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        extra = "allow"


class WarmupSettings(BaseModel):
    """Warmup configuration for email account."""

    warmup_enabled: bool = Field(True, description="Enable warmup")
    total_warmup_per_day: int = Field(20, description="Warmup emails per day")
    daily_rampup: int = Field(2, description="Daily rampup increment")
    reply_rate_percentage: float = Field(30, description="Reply rate percentage")
    warmup_max_limit: int | None = Field(None, description="Max warmup limit")


class WarmupStats(BaseModel):
    """Warmup statistics for email account."""

    warmup_score: float | None = None
    emails_sent: int | None = None
    emails_received: int | None = None
    emails_landed_in_spam: int | None = None

    class Config:
        extra = "allow"


# --- Lead Models ---


class LeadBase(BaseModel):
    """Base lead fields."""

    email: str = Field(..., description="Lead email address")
    first_name: str | None = Field(None, description="Lead first name")
    last_name: str | None = Field(None, description="Lead last name")
    company_name: str | None = Field(None, description="Lead company name")
    phone_number: str | None = Field(None, description="Lead phone number")
    website: str | None = Field(None, description="Lead website")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    custom_fields: dict[str, Any] | None = Field(None, description="Custom field values")


class LeadCreate(LeadBase):
    """Create a new lead."""

    pass


class Lead(LeadBase):
    """Lead response with campaign context."""

    id: int | None = Field(None, alias="email_lead_id", description="Lead ID")
    lead_email: str | None = Field(None, description="Lead email (alias)")
    lead_first_name: str | None = Field(None, description="First name (alias)")
    lead_last_name: str | None = Field(None, description="Last name (alias)")
    lead_status: LeadStatus | None = Field(None, description="Lead status")
    email_campaign_id: int | None = Field(None, description="Associated campaign ID")
    email_campaign_name: str | None = Field(None, description="Campaign name")
    current_sequence_number: int | None = Field(None, description="Current sequence step")
    is_unsubscribed: bool | None = Field(None, description="Unsubscribed flag")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        extra = "allow"
        populate_by_name = True


class LeadAddRequest(BaseModel):
    """Request to add leads to a campaign."""

    lead_list: list[LeadCreate] = Field(..., description="List of leads to add")
    settings: dict[str, Any] | None = Field(
        None, description="Optional settings for lead import"
    )


# --- Campaign Models ---


class SequenceVariant(BaseModel):
    """Email sequence variant for A/B testing."""

    id: int | None = Field(None, description="Variant ID (omit to create new)")
    subject: str | None = Field(None, description="Email subject line")
    email_body: str | None = Field(None, description="Email body HTML")
    seq_variant_distribution: float | None = Field(
        None, description="Distribution % for MANUAL_PERCENTAGE"
    )


class SequenceStep(BaseModel):
    """Campaign sequence step."""

    id: int | None = Field(None, description="Sequence ID (omit to create new)")
    seq_number: int | None = Field(None, description="Sequence position (1, 2, 3...)")
    seq_delay_days: int | None = Field(None, description="Days delay from previous step")
    seq_variants: list[SequenceVariant] | None = Field(
        None, description="A/B variants for this step"
    )
    variant_distribution_type: VariantDistributionType | None = Field(
        None, description="How to distribute variants"
    )
    winning_metric_property: WinningMetricProperty | None = Field(
        None, description="Metric for AI_EQUAL optimization"
    )
    lead_distribution_percentage: float | None = Field(
        None, description="% of leads for AI testing (min 20%)"
    )


class CampaignSettings(BaseModel):
    """Campaign general settings."""

    campaign_name: str | None = Field(None, description="Campaign name")
    timezone: str | None = Field(None, description="Campaign timezone")
    track_settings: dict[str, bool] | None = Field(
        None, description="Tracking settings (opens, clicks, etc.)"
    )
    stop_lead_settings: dict[str, bool] | None = Field(
        None, description="Auto-stop conditions"
    )

    class Config:
        extra = "allow"


class Campaign(BaseModel):
    """Campaign response."""

    id: int = Field(..., description="Campaign ID")
    name: str | None = Field(None, description="Campaign name")
    status: str | None = Field(None, description="Campaign status")
    created_at: datetime | None = None
    user_id: int | None = None

    class Config:
        extra = "allow"


# --- Master Inbox Models ---


class EmailMessage(BaseModel):
    """Email message in conversation history."""

    from_email: str | None = Field(None, alias="from", description="Sender email")
    to_email: str | None = Field(None, alias="to", description="Recipient email")
    type: EmailType | None = Field(None, description="SENT or REPLY")
    time: datetime | None = Field(None, description="Message timestamp")
    email_body: str | None = Field(None, description="Message content")
    subject: str | None = Field(None, description="Email subject")
    stats_id: str | None = Field(None, description="Stats record ID")

    class Config:
        extra = "allow"
        populate_by_name = True


class InboxLead(BaseModel):
    """Lead in master inbox with reply history."""

    email_lead_id: int | None = Field(None, description="Lead ID")
    lead_email: str | None = Field(None, description="Lead email")
    lead_first_name: str | None = Field(None, description="First name")
    lead_last_name: str | None = Field(None, description="Last name")
    lead_status: LeadStatus | None = Field(None, description="Lead status")
    email_campaign_id: int | None = Field(None, description="Campaign ID")
    email_campaign_name: str | None = Field(None, description="Campaign name")
    last_reply_time: datetime | None = Field(None, description="Last reply timestamp")
    last_sent_time: datetime | None = Field(None, description="Last sent timestamp")
    has_new_unread_email: bool | None = Field(None, description="Has unread messages")
    is_important: bool | None = Field(None, description="Marked as important")
    is_archived: bool | None = Field(None, description="Archived flag")
    is_snoozed: bool | None = Field(None, description="Snoozed flag")
    team_member_id: int | None = Field(None, description="Assigned team member")
    revenue: float | None = Field(None, description="Associated revenue")
    current_sequence_number: int | None = Field(None, description="Current sequence")
    email_history: list[EmailMessage] | None = Field(
        None, description="Conversation history"
    )

    class Config:
        extra = "allow"


class UpdateCategoryRequest(BaseModel):
    """Request to update lead category."""

    lead_id: int = Field(..., description="Lead ID to update")
    category: LeadCategory | None = Field(None, description="New category")
    campaign_id: int | None = Field(None, description="Campaign ID")


# --- Analytics Models ---


class CampaignStats(BaseModel):
    """Campaign statistics."""

    total_leads: int | None = None
    emails_sent: int | None = None
    emails_opened: int | None = None
    emails_clicked: int | None = None
    emails_replied: int | None = None
    emails_bounced: int | None = None
    unsubscribed: int | None = None
    open_rate: float | None = None
    click_rate: float | None = None
    reply_rate: float | None = None
    bounce_rate: float | None = None

    class Config:
        extra = "allow"


# --- Webhook Models ---


class WebhookPayload(BaseModel):
    """Webhook payload for EMAIL_REPLY event."""

    event_type: str | None = Field(None, description="Event type (EMAIL_REPLY)")
    campaign_id: int | None = None
    campaign_name: str | None = None
    campaign_status: str | None = None
    sl_email_lead_id: int | None = Field(None, description="Smartlead lead ID")
    sl_lead_email: str | None = Field(None, description="Lead email")
    from_email: str | None = None
    to_email: str | None = None
    to_name: str | None = None
    cc_emails: list[str] | None = None
    subject: str | None = None
    preview_text: str | None = None
    message_id: str | None = None
    time_replied: datetime | None = None
    event_timestamp: datetime | None = None
    sequence_number: int | None = None
    webhook_id: int | None = None
    webhook_name: str | None = None
    app_url: str | None = None
    ui_master_inbox_link: str | None = None
    description: str | None = None
    # Enhanced lead correspondence fields
    target_lead_email: str | None = Field(
        None, alias="targetLeadEmail", description="Original targeted email"
    )
    reply_received_from: str | None = Field(
        None, alias="replyReceivedFrom", description="Actual replier email"
    )
    replied_company_domain: str | None = Field(
        None,
        alias="repliedCompanyDomain",
        description="SameCompany, DifferentCompany, or Unknown",
    )

    class Config:
        extra = "allow"
        populate_by_name = True


# --- Block List Models ---


class BlockListEntry(BaseModel):
    """Entry in global block list."""

    email: str | None = Field(None, description="Blocked email address")
    domain: str | None = Field(None, description="Blocked domain")
    reason: str | None = Field(None, description="Block reason")
    created_at: datetime | None = None

    class Config:
        extra = "allow"


class AddToBlockListRequest(BaseModel):
    """Request to add email/domain to block list."""

    email: str | None = Field(None, description="Email to block")
    domain: str | None = Field(None, description="Domain to block")
