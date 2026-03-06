"""
Batch operations mixin for Google Sheets API.

Handles batch read and write operations for efficiency.
"""

from typing import Any

from ..models import (
    ValueRange,
    BatchGetValuesResponse,
    BatchUpdateValuesResponse,
    ValueInputOption,
    ValueRenderOption,
    DateTimeRenderOption,
)


class BatchMixin:
    """Mixin for batch operations."""

    async def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
        major_dimension: str = "ROWS",
        value_render_option: ValueRenderOption | str = ValueRenderOption.FORMATTED_VALUE,
        date_time_render_option: DateTimeRenderOption | str = DateTimeRenderOption.FORMATTED_STRING,
    ) -> BatchGetValuesResponse:
        """
        Get values from multiple ranges in a single request.

        More efficient than making multiple get_values calls.

        Args:
            spreadsheet_id: The spreadsheet ID
            ranges: List of A1 notation ranges
            major_dimension: "ROWS" or "COLUMNS"
            value_render_option: How values should be rendered
            date_time_render_option: How dates should be rendered

        Returns:
            BatchGetValuesResponse with value_ranges list

        Example:
            result = await client.batch_get_values(
                "spreadsheet_id",
                ["Sheet1!A1:D10", "Sheet2!A1:B5", "Config!A:B"]
            )
            for value_range in result.value_ranges or []:
                print(f"{value_range.range}: {len(value_range.values or [])} rows")
        """
        response = await self._request(
            "GET",
            f"/spreadsheets/{spreadsheet_id}/values:batchGet",
            params={
                "ranges": ranges,
                "majorDimension": major_dimension,
                "valueRenderOption": str(value_render_option.value if hasattr(value_render_option, 'value') else value_render_option),
                "dateTimeRenderOption": str(date_time_render_option.value if hasattr(date_time_render_option, 'value') else date_time_render_option),
            },
        )
        return BatchGetValuesResponse.model_validate(response)

    async def batch_update_values(
        self,
        spreadsheet_id: str,
        data: list[dict[str, Any]],
        value_input_option: ValueInputOption | str = ValueInputOption.USER_ENTERED,
        include_values_in_response: bool = False,
    ) -> BatchUpdateValuesResponse:
        """
        Update values in multiple ranges in a single request.

        More efficient than making multiple update_values calls.

        Args:
            spreadsheet_id: The spreadsheet ID
            data: List of dicts with 'range' and 'values' keys
            value_input_option: RAW or USER_ENTERED
            include_values_in_response: Include updated values in response

        Returns:
            BatchUpdateValuesResponse with update statistics

        Example:
            await client.batch_update_values(
                "spreadsheet_id",
                [
                    {
                        "range": "Sheet1!A1",
                        "values": [["Header 1", "Header 2"]],
                    },
                    {
                        "range": "Sheet1!A2",
                        "values": [
                            ["Row 1 Col 1", "Row 1 Col 2"],
                            ["Row 2 Col 1", "Row 2 Col 2"],
                        ],
                    },
                    {
                        "range": "Config!A1",
                        "values": [["Last Updated", "2024-01-15"]],
                    },
                ]
            )
        """
        # Convert data to ValueRange format
        value_ranges = []
        for item in data:
            value_ranges.append({
                "range": item["range"],
                "majorDimension": "ROWS",
                "values": item["values"],
            })

        response = await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values:batchUpdate",
            json={
                "valueInputOption": str(value_input_option.value if hasattr(value_input_option, 'value') else value_input_option),
                "includeValuesInResponse": include_values_in_response,
                "data": value_ranges,
            },
        )
        return BatchUpdateValuesResponse.model_validate(response)

    async def batch_clear_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
    ) -> dict[str, Any]:
        """
        Clear values from multiple ranges in a single request.

        Args:
            spreadsheet_id: The spreadsheet ID
            ranges: List of A1 notation ranges to clear

        Returns:
            Response with cleared ranges

        Example:
            await client.batch_clear_values(
                "spreadsheet_id",
                ["Sheet1!A2:D100", "Sheet2!A2:B50"]
            )
        """
        response = await self._request(
            "POST",
            f"/spreadsheets/{spreadsheet_id}/values:batchClear",
            json={
                "ranges": ranges,
            },
        )
        return response
