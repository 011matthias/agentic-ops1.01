"""
Smartlead API Client

A typed Python client for the Smartlead cold email platform.

Base URL: https://server.smartlead.ai/api/v1
Auth: API key as query parameter (?api_key=xxx)

Usage:
    from smartlead import SmartleadClient

    client = SmartleadClient(api_key="your_api_key")

    # List email accounts
    accounts = client.list_email_accounts()

    # Add leads to campaign
    client.add_leads_to_campaign(
        campaign_id=123,
        leads=[{"email": "test@example.com", "first_name": "John"}]
    )

    # Get inbox replies
    replies = client.get_inbox_replies()
"""

from .client import AsyncSmartleadClient, SmartleadClient, SmartleadError
from .models import (
    AddToBlockListRequest,
    BlockListEntry,
    Campaign,
    CampaignSettings,
    CampaignStats,
    EmailAccount,
    EmailAccountCreate,
    EmailAccountUpdate,
    EmailMessage,
    EmailType,
    InboxLead,
    Lead,
    LeadAddRequest,
    LeadBase,
    LeadCategory,
    LeadCreate,
    LeadStatus,
    SequenceStep,
    SequenceVariant,
    UpdateCategoryRequest,
    VariantDistributionType,
    WarmupSettings,
    WarmupStats,
    WebhookPayload,
    WinningMetricProperty,
)

__all__ = [
    # Client
    "SmartleadClient",
    "AsyncSmartleadClient",
    "SmartleadError",
    # Enums
    "LeadStatus",
    "VariantDistributionType",
    "WinningMetricProperty",
    "EmailType",
    "LeadCategory",
    # Email Account Models
    "EmailAccount",
    "EmailAccountCreate",
    "EmailAccountUpdate",
    "WarmupSettings",
    "WarmupStats",
    # Lead Models
    "LeadBase",
    "LeadCreate",
    "Lead",
    "LeadAddRequest",
    # Campaign Models
    "SequenceVariant",
    "SequenceStep",
    "CampaignSettings",
    "Campaign",
    "CampaignStats",
    # Master Inbox Models
    "EmailMessage",
    "InboxLead",
    "UpdateCategoryRequest",
    # Webhook Models
    "WebhookPayload",
    # Block List Models
    "BlockListEntry",
    "AddToBlockListRequest",
]
