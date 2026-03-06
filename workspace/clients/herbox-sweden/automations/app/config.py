"""
Configuration management using Pydantic Settings.
Loads from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Client identification
    client_id: str = "herbox"
    client_display_name: str = "Herbox"  # Proper display name for UI

    # Database
    database_url: str = "sqlite:///./logs.db"

    # Dashboard authentication
    dashboard_password: str = "changeme"

    # Internal API key (for cron jobs)
    internal_api_key: str = "changeme"

    # Self-healing webhook (optional)
    self_healing_webhook: str | None = None

    # Notifications (optional)
    slack_webhook_url: str | None = None

    # Railway provides this automatically
    railway_public_domain: str | None = None

    # n8n webhook base URL (for Order Approval Dashboard -> Fortnox order creation)
    n8n_webhook_base_url: str = "https://primary-production-ef56.up.railway.app"

    # === API Integrations ===

    # Airtable
    airtable_token: str | None = None
    airtable_base_id: str = ""  # Must be set via environment variable

    # Apify
    apify_api_token: str | None = None

    # OpenRouter (for AI calls)
    openrouter_api: str | None = None

    # === AI Model Configuration ===
    # Centralized AI model management across all automations.
    #
    # Pattern: When adding a new automation that uses AI:
    #   1. Add an entry below with key: "ai_model_{automation_name}"
    #   2. Use `settings.get_ai_model("{automation_name}")` in your code
    #   3. Document the operation purpose for future reference
    #
    # Available models: https://openrouter.ai/models
    # Common choices: "openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash"

    # Default model for operations not explicitly listed below
    ai_model_default: str = "openai/gpt-4o-mini"

    # Per-operation model overrides
    ai_model_company_cleaning: str = "openai/gpt-4o-mini"  # A6.4: Normalize company names
    ai_model_title_translation: str = "openai/gpt-4o-mini"  # A6.4: Dutch job title translation
    ai_model_email_reply: str = "openai/gpt-4o-mini"  # A8: Email reply classification/drafting

    def get_ai_model(self, operation: str) -> str:
        """
        Get the AI model for a specific operation.

        Usage:
            model = settings.get_ai_model("company_cleaning")
            # Returns: "openai/gpt-4o-mini" (or custom override)

        Args:
            operation: Operation key (e.g., "company_cleaning", "title_translation")

        Returns:
            Model identifier for OpenRouter
        """
        model_key = f"ai_model_{operation}"
        model = getattr(self, model_key, None)
        return model if model else self.ai_model_default

    # Smartlead (for email sequencing)
    smartlead_api: str | None = None
    smartlead_api_test: str | None = None  # Testing API key
    smartlead_webhook_secret: str | None = None  # Validate Smartlead webhooks

    # OpenAI (for A8 Email Reply Handler)
    openai_api_key: str | None = None

    # Heyreach (for A8 Email Reply Handler - LinkedIn campaigns)
    heyreach_api_key: str | None = None
    heyreach_campaign_patrick: str | None = None  # Patrick's LinkedIn campaign ID
    heyreach_campaign_koen: str | None = None  # Koen's LinkedIn campaign ID

    # Herbox internal domains (for A8 internal email filtering)
    herbox_domains: str = "herbox.se,herbox.com"  # Comma-separated internal domains

    # LinkedIn (for A6 List Building - testing profile)
    linkedin_cookies: str | None = None  # JSON array from Cookie-Editor extension
    linkedin_user_agent: str | None = None  # Browser user agent string

    # Email Enrichment (for A6.3 Contact Enrichment)
    leadmagic_api_key: str | None = None
    trykitt_api_key: str | None = None
    usebouncer_api_key: str | None = None

    # === TEST VARIABLES - REMOVE AFTER TESTING ===
    apify_api_token_test: str | None = None  # Test Apify token for A6.2
    apify_dataset_id_test: str | None = None  # Test dataset ID for A6.2


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
