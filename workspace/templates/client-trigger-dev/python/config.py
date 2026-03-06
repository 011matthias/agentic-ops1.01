"""
Configuration management using Pydantic Settings.
Loads from environment variables (set in Trigger.dev dashboard).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Client identification
    client_id: str = "template-client"

    # Notifications (optional)
    slack_webhook_url: str | None = None

    # === API Integrations ===

    # Airtable
    airtable_token: str | None = None
    airtable_base_id: str = ""

    # OpenRouter (for AI calls)
    openrouter_api: str | None = None

    # === AI Model Configuration ===
    ai_model_default: str = "openai/gpt-4o-mini"

    def get_ai_model(self, operation: str) -> str:
        """Get the AI model for a specific operation."""
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
