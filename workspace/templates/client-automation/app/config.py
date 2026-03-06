"""
Configuration management using Pydantic Settings.
Loads from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Client identification
    client_id: str = "template-client"

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

    # === API Integrations ===

    # Airtable
    airtable_token: str | None = None
    airtable_base_id: str = ""

    # OpenRouter (for AI calls)
    openrouter_api: str | None = None

    # === AI Model Configuration ===
    # Centralized AI model management across all automations.
    #
    # Pattern: When adding a new automation that uses AI:
    #   1. Add an entry below with key: "ai_model_{operation_name}"
    #   2. Use `settings.get_ai_model("{operation_name}")` in your code
    #   3. Document the operation purpose for future reference
    #
    # Available models: https://openrouter.ai/models
    # Common choices: "openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-flash"

    # Default model for operations not explicitly listed below
    ai_model_default: str = "openai/gpt-4o-mini"

    # Per-operation model overrides
    # Example: ai_model_email_classification: str = "openai/gpt-4o-mini"  # A1: Classify emails

    def get_ai_model(self, operation: str) -> str:
        """
        Get the AI model for a specific operation.

        Usage:
            model = settings.get_ai_model("email_classification")
            # Returns: "openai/gpt-4o-mini" (or custom override)

        Args:
            operation: Operation key (e.g., "email_classification", "company_cleaning")

        Returns:
            Model identifier for OpenRouter
        """
        model_key = f"ai_model_{operation}"
        model = getattr(self, model_key, None)
        return model if model else self.ai_model_default

    # Add your API integrations below
    # example_api_token: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
