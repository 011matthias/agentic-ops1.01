"""
Spreadsheet operations mixin for Google Sheets API.

Handles spreadsheet-level operations like getting metadata and creating spreadsheets.
"""

from ..models import Spreadsheet


class SpreadsheetsMixin:
    """Mixin for spreadsheet-level operations."""

    async def get_spreadsheet(
        self,
        spreadsheet_id: str,
        include_grid_data: bool = False,
        ranges: list[str] | None = None,
    ) -> Spreadsheet:
        """
        Get spreadsheet metadata.

        Args:
            spreadsheet_id: The spreadsheet ID (from the URL)
            include_grid_data: Include cell data (can be large)
            ranges: Optional list of ranges to include grid data for

        Returns:
            Spreadsheet object with metadata and optionally data

        Example:
            sheet = await client.get_spreadsheet("spreadsheet_id")
            print(f"Title: {sheet.properties.title}")
            print(f"Sheets: {[s.properties.title for s in sheet.sheets]}")
        """
        params = {
            "includeGridData": include_grid_data,
        }
        if ranges:
            params["ranges"] = ranges

        response = await self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}",
            params=params,
        )
        return Spreadsheet.model_validate(response)

    async def create_spreadsheet(
        self,
        title: str,
        sheets: list[str] | None = None,
    ) -> Spreadsheet:
        """
        Create a new spreadsheet.

        Args:
            title: Title for the new spreadsheet
            sheets: Optional list of sheet names to create (default: one sheet named "Sheet1")

        Returns:
            Spreadsheet object with the new spreadsheet's metadata

        Example:
            new_sheet = await client.create_spreadsheet(
                "My New Spreadsheet",
                sheets=["Data", "Summary", "Charts"]
            )
            print(f"Created: {new_sheet.spreadsheet_url}")
        """
        # Build sheets configuration
        sheets_config = []
        if sheets:
            for i, sheet_name in enumerate(sheets):
                sheets_config.append({
                    "properties": {
                        "title": sheet_name,
                        "index": i,
                    }
                })

        body = {
            "properties": {
                "title": title,
            },
        }
        if sheets_config:
            body["sheets"] = sheets_config

        response = await self._request(
            "POST",
            "/spreadsheets",
            json=body,
        )
        return Spreadsheet.model_validate(response)

    async def get_sheet_names(self, spreadsheet_id: str) -> list[str]:
        """
        Get list of sheet names in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            List of sheet names

        Example:
            sheets = await client.get_sheet_names("spreadsheet_id")
            # ['Sheet1', 'Data', 'Summary']
        """
        spreadsheet = await self.get_spreadsheet(spreadsheet_id)
        return [
            sheet.properties.title
            for sheet in (spreadsheet.sheets or [])
            if sheet.properties and sheet.properties.title
        ]
