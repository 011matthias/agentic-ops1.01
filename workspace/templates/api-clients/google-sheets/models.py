"""
Pydantic models for Google Sheets API.

Based on the Google Sheets API v4 schema:
https://developers.google.com/sheets/api/reference/rest
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# Enums
class ValueInputOption(str, Enum):
    """How input data should be interpreted."""

    RAW = "RAW"  # Values are stored as-is
    USER_ENTERED = "USER_ENTERED"  # Values are parsed as if typed by user


class ValueRenderOption(str, Enum):
    """How values should be rendered in the output."""

    FORMATTED_VALUE = "FORMATTED_VALUE"  # Values rendered as they appear in the UI
    UNFORMATTED_VALUE = "UNFORMATTED_VALUE"  # Values without formatting
    FORMULA = "FORMULA"  # Values will be formulas if a formula was entered


class InsertDataOption(str, Enum):
    """How new rows should be inserted when appending."""

    OVERWRITE = "OVERWRITE"  # Overwrite existing data
    INSERT_ROWS = "INSERT_ROWS"  # Insert new rows for the new data


class DateTimeRenderOption(str, Enum):
    """How dates should be rendered in the output."""

    SERIAL_NUMBER = "SERIAL_NUMBER"  # As a number (days since Dec 30, 1899)
    FORMATTED_STRING = "FORMATTED_STRING"  # As a formatted string


# Sheet Properties
class GridProperties(BaseModel):
    """Properties of a grid (the rectangular area of cells)."""

    row_count: int | None = Field(None, alias="rowCount")
    column_count: int | None = Field(None, alias="columnCount")
    frozen_row_count: int | None = Field(None, alias="frozenRowCount")
    frozen_column_count: int | None = Field(None, alias="frozenColumnCount")

    class Config:
        populate_by_name = True


class SheetProperties(BaseModel):
    """Properties of a sheet within a spreadsheet."""

    sheet_id: int | None = Field(None, alias="sheetId")
    title: str | None = None
    index: int | None = None
    sheet_type: str | None = Field(None, alias="sheetType")
    grid_properties: GridProperties | None = Field(None, alias="gridProperties")

    class Config:
        populate_by_name = True


class Sheet(BaseModel):
    """A sheet within a spreadsheet."""

    properties: SheetProperties | None = None


class SpreadsheetProperties(BaseModel):
    """Properties of a spreadsheet."""

    title: str | None = None
    locale: str | None = None
    time_zone: str | None = Field(None, alias="timeZone")
    auto_recalc: str | None = Field(None, alias="autoRecalc")

    class Config:
        populate_by_name = True


class Spreadsheet(BaseModel):
    """A Google Spreadsheet."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    properties: SpreadsheetProperties | None = None
    sheets: list[Sheet] | None = None
    spreadsheet_url: str | None = Field(None, alias="spreadsheetUrl")

    class Config:
        populate_by_name = True


# Value Ranges
class ValueRange(BaseModel):
    """A range of values in a spreadsheet."""

    range: str | None = None
    major_dimension: str | None = Field("ROWS", alias="majorDimension")
    values: list[list[Any]] | None = None

    class Config:
        populate_by_name = True


class UpdateValuesResponse(BaseModel):
    """Response from updating values."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    updated_range: str | None = Field(None, alias="updatedRange")
    updated_rows: int | None = Field(None, alias="updatedRows")
    updated_columns: int | None = Field(None, alias="updatedColumns")
    updated_cells: int | None = Field(None, alias="updatedCells")
    updated_data: ValueRange | None = Field(None, alias="updatedData")

    class Config:
        populate_by_name = True


class AppendValuesResponse(BaseModel):
    """Response from appending values."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    table_range: str | None = Field(None, alias="tableRange")
    updates: UpdateValuesResponse | None = None

    class Config:
        populate_by_name = True


class ClearValuesResponse(BaseModel):
    """Response from clearing values."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    cleared_range: str | None = Field(None, alias="clearedRange")

    class Config:
        populate_by_name = True


# Batch Operations
class BatchGetValuesResponse(BaseModel):
    """Response from batch get values."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    value_ranges: list[ValueRange] | None = Field(None, alias="valueRanges")

    class Config:
        populate_by_name = True


class BatchUpdateValuesRequest(BaseModel):
    """Request for batch update values."""

    value_input_option: ValueInputOption | str = Field(
        ValueInputOption.USER_ENTERED, alias="valueInputOption"
    )
    data: list[ValueRange] | None = None
    include_values_in_response: bool | None = Field(None, alias="includeValuesInResponse")
    response_value_render_option: ValueRenderOption | str | None = Field(
        None, alias="responseValueRenderOption"
    )

    class Config:
        populate_by_name = True


class BatchUpdateValuesResponse(BaseModel):
    """Response from batch update values."""

    spreadsheet_id: str | None = Field(None, alias="spreadsheetId")
    total_updated_rows: int | None = Field(None, alias="totalUpdatedRows")
    total_updated_columns: int | None = Field(None, alias="totalUpdatedColumns")
    total_updated_cells: int | None = Field(None, alias="totalUpdatedCells")
    total_updated_sheets: int | None = Field(None, alias="totalUpdatedSheets")
    responses: list[UpdateValuesResponse] | None = None

    class Config:
        populate_by_name = True
