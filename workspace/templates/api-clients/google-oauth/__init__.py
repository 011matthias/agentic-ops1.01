"""
Google OAuth Module

Shared OAuth 2.0 authentication for all Google APIs.

For CLI setup (developer workflow):
    uv run templates/api-clients/google-oauth/cli_setup.py --scopes spreadsheets

For web setup (client self-service):
    GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=xxx \
        uv run templates/api-clients/google-oauth/web_server.py

For runtime use in automations:
    from google_oauth import credentials_from_refresh_token

    credentials = credentials_from_refresh_token(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        refresh_token=settings.google_refresh_token,
    )
"""

from .google_auth import (
    # Core functions
    get_credentials,
    credentials_from_refresh_token,
    resolve_scopes,
    get_authorized_scopes,
    get_refresh_token,
    # Scope mapping
    SCOPE_ALIASES,
    # Convenience functions
    get_sheets_credentials,
    get_drive_credentials,
    get_docs_credentials,
    get_calendar_credentials,
)

__all__ = [
    "get_credentials",
    "credentials_from_refresh_token",
    "resolve_scopes",
    "get_authorized_scopes",
    "get_refresh_token",
    "SCOPE_ALIASES",
    "get_sheets_credentials",
    "get_drive_credentials",
    "get_docs_credentials",
    "get_calendar_credentials",
]
