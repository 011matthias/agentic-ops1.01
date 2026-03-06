"""
Smartlead API Client

Composes all mixins into a unified client interface.
"""

from .analytics import AnalyticsMixin, AsyncAnalyticsMixin
from .base import AsyncBaseClient, BaseClient, SmartleadError
from .block_list import AsyncBlockListMixin, BlockListMixin
from .campaigns import AsyncCampaignsMixin, CampaignsMixin
from .email_accounts import AsyncEmailAccountsMixin, EmailAccountsMixin
from .leads import AsyncLeadsMixin, LeadsMixin
from .master_inbox import AsyncMasterInboxMixin, MasterInboxMixin
from .subsequences import AsyncSubsequencesMixin, SubsequencesMixin


class SmartleadClient(
    EmailAccountsMixin,
    CampaignsMixin,
    LeadsMixin,
    MasterInboxMixin,
    AnalyticsMixin,
    BlockListMixin,
    SubsequencesMixin,
    BaseClient,  # Must be last
):
    """
    Smartlead API client with all API methods.

    Usage:
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

    pass


class AsyncSmartleadClient(
    AsyncEmailAccountsMixin,
    AsyncCampaignsMixin,
    AsyncLeadsMixin,
    AsyncMasterInboxMixin,
    AsyncAnalyticsMixin,
    AsyncBlockListMixin,
    AsyncSubsequencesMixin,
    AsyncBaseClient,  # Must be last
):
    """
    Async Smartlead API client with all API methods.

    Usage:
        async with AsyncSmartleadClient(api_key="your_api_key") as client:
            accounts = await client.list_email_accounts()
    """

    pass


__all__ = [
    "SmartleadClient",
    "AsyncSmartleadClient",
    "SmartleadError",
    # Base classes (for extension)
    "BaseClient",
    "AsyncBaseClient",
    # Mixins (for custom compositions)
    "EmailAccountsMixin",
    "AsyncEmailAccountsMixin",
    "CampaignsMixin",
    "AsyncCampaignsMixin",
    "LeadsMixin",
    "AsyncLeadsMixin",
    "MasterInboxMixin",
    "AsyncMasterInboxMixin",
    "AnalyticsMixin",
    "AsyncAnalyticsMixin",
    "BlockListMixin",
    "AsyncBlockListMixin",
    "SubsequencesMixin",
    "AsyncSubsequencesMixin",
]
