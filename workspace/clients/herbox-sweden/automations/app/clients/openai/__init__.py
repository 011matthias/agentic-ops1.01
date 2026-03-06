"""OpenAI API client for email categorization and phone extraction."""

from .client import OpenAIClient, EmailCategory, PhoneInfo

__all__ = ["OpenAIClient", "EmailCategory", "PhoneInfo"]
