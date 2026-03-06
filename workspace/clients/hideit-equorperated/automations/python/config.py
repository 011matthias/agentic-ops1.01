"""
Configuration for HideItEquorperated OmniBoard automations.
Loaded from environment variables (set in Trigger.dev dashboard or .env).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    client_id: str = "hideit-equorperated"

    # OmniBoard Hono API
    omniboard_api_url: str = "http://localhost:3001/api"

    # OpenRouter (for A3 AI insights)
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
