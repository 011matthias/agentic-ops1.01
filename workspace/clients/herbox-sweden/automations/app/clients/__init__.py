# API Client wrappers
# Add client modules here for each integration (Fortnox, Upsales, etc.)

from .airtable import AirtableClient
from .apify import ApifyClient
from .leadmagic import LeadmagicClient
from .trykitt import TrykittClient
from .usebouncer import UsebouncerClient
from .openrouter import OpenRouterClient

__all__ = [
    "AirtableClient",
    "ApifyClient",
    "LeadmagicClient",
    "TrykittClient",
    "UsebouncerClient",
    "OpenRouterClient",
]
