"""
Google Sheets API Client.

Composed from mixins for different operation types.
"""

from .base import BaseClient, GoogleSheetsError
from .values import ValuesMixin
from .spreadsheets import SpreadsheetsMixin
from .batch import BatchMixin


class GoogleSheetsClient(SpreadsheetsMixin, ValuesMixin, BatchMixin, BaseClient):
    """
    Async client for Google Sheets API v4.

    Uses OAuth 2.0 with refresh token for authentication.
    Automatically handles token refresh.

    Usage:
        async with GoogleSheetsClient(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            refresh_token=settings.google_refresh_token,
        ) as client:
            # Read values
            data = await client.get_values("spreadsheet_id", "Sheet1!A1:D10")

            # Write values
            await client.update_values("spreadsheet_id", "Sheet1!A1", [["Name", "Email"]])

            # Append rows
            await client.append_values("spreadsheet_id", "Sheet1!A:D", [["New", "Row"]])

            # Get spreadsheet metadata
            sheet = await client.get_spreadsheet("spreadsheet_id")
            print(f"Title: {sheet.properties.title}")

    Environment variables needed:
        GOOGLE_CLIENT_ID: OAuth client ID
        GOOGLE_CLIENT_SECRET: OAuth client secret
        GOOGLE_REFRESH_TOKEN: Refresh token from OAuth setup

    Rate limits:
        - Read requests: 60 per minute per user
        - Write requests: 60 per minute per user
    """

    pass


__all__ = ["GoogleSheetsClient", "GoogleSheetsError"]
