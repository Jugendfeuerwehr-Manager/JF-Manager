"""Excel copy of an annual report in the order of the DJF statistics portal."""

from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill

from jf_manager_backend.safe_exports import write_safe_cell

HEADER = PatternFill("solid", fgColor="1F3A6B")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def _header(sheet, row, title):
    for column, value in enumerate((title, "M", "W", "D", "Gesamt"), start=1):
        cell = sheet.cell(row=row, column=column, value=value)
        cell.fill = HEADER
        cell.font = HEADER_FONT
    return row + 1


def _line(sheet, row, label, counts):
    write_safe_cell(sheet, row, 1, label)
    for column, key in enumerate(("m", "w", "d", "total"), start=2):
        sheet.cell(row=row, column=column, value=counts.get(key))
    return row + 1


def build_workbook(data):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"Jahresmeldung {data['year']}"
    sheet.column_dimensions["A"].width = 48
    organisation = data["organisation"]
    sheet["A1"] = f"Jahresbericht der Jugendfeuerwehr – Berichtsjahr {data['year']} (Stichtag 31.12.)"
    sheet["A1"].font = Font(bold=True, size=13)
    write_safe_cell(sheet, 2, 1, f"{organisation['name']} · Org.-ID {organisation['djf_org_id'] or '–'}")

    manual = data.get("manual") or {}
    row = _header(sheet, 4, "Mitglieder Berichtsjahr")
    row = _line(sheet, row, "Anzahl Betreuer:innen", manual.get("supervisors") or {})
    row = _line(sheet, row, "Anzahl Mitglieder", data["members"])
    for movement in data["movements"]:
        row = _line(sheet, row, f"Anzahl {movement['label']}", movement)
    for reason in data["exit_reasons"]:
        row = _line(sheet, row, f"  davon Grund: {reason['label']}", {"total": reason["total"]})

    row = _header(sheet, row + 1, "Altersstruktur")
    for age in data["age"]:
        row = _line(sheet, row, f"Anzahl mit Alter {age['label']}", age)

    activities = manual.get("activities") or []
    if activities:
        row = _header(sheet, row + 1, "Aktivitäten")
        for activity in activities:
            row = _line(sheet, row, activity.get("label", ""), {"total": activity.get("value")})

    row += 1
    sheet.cell(row=row, column=1, value="Plausibilität").font = Font(bold=True)
    for check in data["checks"]:
        row += 1
        write_safe_cell(sheet, row, 1, ("✓ " if check["ok"] else "✗ ") + check["message"])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
