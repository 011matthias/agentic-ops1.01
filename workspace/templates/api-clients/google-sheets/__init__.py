"""
Google Sheets API Client.

Async client for reading and writing Google Sheets.

Setup:
    1. Run OAuth setup to get refresh token:
       uv run templates/api-clients/google-oauth/cli_setup.py --scopes spreadsheets

    2. Add to Railway environment:
       GOOGLE_CLIENT_ID=xxx
       GOOGLE_CLIENT_SECRET=xxx
       GOOGLE_REFRESH_TOKEN=xxx

Usage:
    from google_sheets import GoogleSheetsClient

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
"""

from .client import GoogleSheetsClient, GoogleSheetsError
from .models import (
    # Enums
    ValueInputOption,
    ValueRenderOption,
    InsertDataOption,
    DateTimeRenderOption,
    # Spreadsheet models
    Spreadsheet,
    SpreadsheetProperties,
    Sheet,
    SheetProperties,
    GridProperties,
    # Value models
    ValueRange,
    UpdateValuesResponse,
    AppendValuesResponse,
    ClearValuesResponse,
    BatchGetValuesResponse,
    BatchUpdateValuesResponse,
)

__all__ = [
    # Client
    "GoogleSheetsClient",
    "GoogleSheetsError",
    # Enums
    "ValueInputOption",
    "ValueRenderOption",
    "InsertDataOption",
    "DateTimeRenderOption",
    # Spreadsheet models
    "Spreadsheet",
    "SpreadsheetProperties",
    "Sheet",
    "SheetProperties",
    "GridProperties",
    # Value models
    "ValueRange",
    "UpdateValuesResponse",
    "AppendValuesResponse",
    "ClearValuesResponse",
    "BatchGetValuesResponse",
    "BatchUpdateValuesResponse",
]
