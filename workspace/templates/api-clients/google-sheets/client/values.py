"""
Values operations mixin for Google Sheets API.

Handles reading, writing, appending, and clearing cell values.
"""

from typing import Any

from ..models import (
    ValueRange,
    UpdateValuesResponse,
    AppendValuesResponse,
    ClearValuesResponse,
    ValueInputOption,
    ValueRenderOption,
    InsertDataOption,
    DateTimeRenderOption,
)


class ValuesMixin:
    """Mixin for spreadsheet values operations."""

    async def get_values(
        self,
        spreadsheet_id: str,
        range: str,
        major_dimension: str = "ROWS",
        value_render_option: ValueRenderOption | str = ValueRenderOption.FORMATTED_VALUE,
        date_time_render_option: DateTimeRenderOption | str = DateTimeRenderOption.FORMATTED_STRING,
    ) -> ValueRange:
        """
        Get values from a range in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID (from the URL)
            range: A1 notation range (e.g., "Sheet1!A1:D10")
            major_dimension: "ROWS" or "COLUMNS"
            value_render_option: How values should be rendered
            date_time_render_option: How dates should be rendered

        Returns:
            ValueRange with the cell values

        Example:
            values = await client.get_values("spreadsheet_id", "Sheet1!A1:D10")
            for row in values.values or []:
                print(row)
        """
        response = await self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/values/{range}",
            params={
                "majorDimension": major_dimension,
                "valueRenderOption": str(value_render_option.value if hasattr(value_render_option, 'value') else value_render_option),
                "dateTimeRenderOption": str(date_time_render_option.value if hasattr(date_time_render_option, 'value') else date_time_render_option),
            },
        )
        return ValueRange.model_validate(response)

    async def update_values(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: ValueInputOption | str = ValueInputOption.USER_ENTERED,
        include_values_in_response: bool = False,
    ) -> UpdateValuesResponse:
        """
        Update values in a range.

        Args:
            spreadsheet_id: The spreadsheet ID
            range: A1 notation range (e.g., "Sheet1!A1")
            values: 2D array of values to write
            value_input_option: RAW or USER_ENTERED
            include_values_in_response: Include updated values in response

        Returns:
            UpdateValuesResponse with update statistics

        Example:
            # Write headers
            await client.update_values(
                "spreadsheet_id",
                "Sheet1!A1",
                [["Name", "Email", "Phone"]]
            )

            # Write multiple rows
            await client.update_values(
                "spreadsheet_id",
                "Sheet1!A2",
                [
                    ["Alice", "alice@example.com", "555-1234"],
                    ["Bob", "bob@example.com", "555-5678"],
                ]
            )
        """
        response = await self._request(
            "PUT",
            f"/spreadsheets/{spreadsheet_id}/values/{range}",
            params={
                "valueInputOption": str(value_input_option.value if hasattr(value_input_option, 'value') else value_input_option),
                "includeValuesInResponse": include_values_in_response,
            },
            json={
                "range": range,
                "majorDimension": "ROWS",
                "values": values,
            },
        )
        return UpdateValuesResponse.model_validate(response)

    async def append_values(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: ValueInputOption | str = ValueInputOption.USER_ENTERED,
        insert_data_option: InsertDataOption | str = InsertDataOption.INSERT_ROWS,
        include_values_in_response: bool = False,
    ) -> AppendValuesResponse:
        """
        Append values to a table in a spreadsheet.

        Finds the last row with data and appends after it.

        Args:
            spreadsheet_id: The spreadsheet ID
            range: A1 notation of the table range (e.g., "Sheet1!A:D")
            values: 2D array of values to append
            value_input_option: RAW or USER_ENTERED
            insert_data_option: OVERWRITE or INSERT_ROWS
            include_values_in_response: Include appended values in response

        Returns:
            AppendValuesResponse with append statistics

        Example:
            # Append new rows to a table
            await client.append_values(
                "spreadsheet_id",
                "Sheet1!A:D",
                [
                    ["New Row 1", "value1", "value2", "value3"],
                    ["New Row 2", "value4", "value5", "value6"],
                ]
            )
        """
        response = await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values/{range}:append",
            params={
                "valueInputOption": str(value_input_option.value if hasattr(value_input_option, 'value') else value_input_option),
                "insertDataOption": str(insert_data_option.value if hasattr(insert_data_option, 'value') else insert_data_option),
                "includeValuesInResponse": include_values_in_response,
            },
            json={
                "range": range,
                "majorDimension": "ROWS",
                "values": values,
            },
        )
        return AppendValuesResponse.model_validate(response)

    async def clear_values(
        self,
        spreadsheet_id: str,
        range: str,
    ) -> ClearValuesResponse:
        """
        Clear values from a range (keeps formatting).

        Args:
            spreadsheet_id: The spreadsheet ID
            range: A1 notation range to clear (e.g., "Sheet1!A2:D100")

        Returns:
            ClearValuesResponse with the cleared range

        Example:
            # Clear all data except headers
            await client.clear_values("spreadsheet_id", "Sheet1!A2:Z")
        """
        response = await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values/{range}:clear",
        )
        return ClearValuesResponse.model_validate(response)
