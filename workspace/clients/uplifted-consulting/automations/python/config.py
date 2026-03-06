"""
Configuration management using Pydantic Settings.
Loads from environment variables (set in Trigger.dev dashboard).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Client identification
    client_id: str = "uplifted-consulting"

    # Smartlead
    smartlead_api_key: str | None = None

    # OpenRouter (AI classification)
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"

    # Slack (notifications)
    slack_bot_token: str | None = None
    slack_channel_id: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
