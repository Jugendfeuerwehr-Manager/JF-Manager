"""Write user strings as XLSX text, preserving native numeric and date values."""

from datetime import date, datetime

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def write_safe_cell(sheet, row, column, value):
    if isinstance(value, str):
        value = ILLEGAL_CHARACTERS_RE.sub("", value)
    if isinstance(value, datetime) and value.tzinfo is not None:
        value = value.astimezone().replace(tzinfo=None)
    cell = sheet.cell(row=row, column=column, value=value)
    if isinstance(value, str):
        cell.data_type = "s"
    elif isinstance(value, datetime):
        cell.number_format = "DD.MM.YYYY HH:MM"
    elif isinstance(value, date):
        cell.number_format = "DD.MM.YYYY"
    return cell


def append_safe_row(sheet, values):
    sheet.append([None] * len(values))
    row = sheet.max_row
    for column, value in enumerate(values, start=1):
        write_safe_cell(sheet, row, column, value)
