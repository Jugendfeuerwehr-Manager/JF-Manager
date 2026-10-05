# renderers.py
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from rest_framework.renderers import BaseRenderer

from jf_manager_backend.safe_exports import append_safe_row


class MemberExcelRenderer(BaseRenderer):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    format = "xlsx"

    def boolean_to_string(self, boolean_value):
        return "Ja" if boolean_value else "Nein"

    def render(self, data, media_type=None, renderer_context=None):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Mitglieder"
        n_parents_to_render = 2
        # Write header
        header_member = [
            "Vorname",
            "Nachname",
            "Geburtstag",
            "E-Mail",
            "Straße",
            "PLZ",
            "Ort",
            "Telefon",
            "Mobil",
            "Bemerkungen",
            "Eingetreten",
            "Ausweis Nummer",
            "Schwimmer",
            "Status",
        ]

        header_parent_1 = [
            "EB 1 Vorname",
            "EB 1 Nachname",
            "EB 1 E-Mail",
            "EB 1 E-Mail 2",
            "EB 1 Straße",
            "EB 1 PLZ",
            "EB 1 Ort",
            "EB 1 Telefon",
            "EB 1 Mobil",
            "EB 1 Bemerkungen",
        ]

        header_parent_2 = [
            "EB 2 Vorname",
            "EB 2 Nachname",
            "EB 2 E-Mail",
            "EB 2 E-Mail 2",
            "EB 2 Straße",
            "EB 2 PLZ",
            "EB 2 Ort",
            "EB 2 Telefon",
            "EB 2 Mobil",
            "EB 2 Bemerkungen",
        ]

        headers = header_member + header_parent_1 + header_parent_2
        append_safe_row(sheet, headers)

        # Write rows
        # for parent in data:
        #    for child in parent['children']:
        #        sheet.append([parent['name'], child['child_name']])
        for member in data:
            can_swimm = self.boolean_to_string(member["canSwimm"])

            row = [
                member["name"],
                member["lastname"],
                date.fromisoformat(member["birthday"]) if member["birthday"] else None,
                member["email"],
                member["street"],
                member["zip_code"],
                member["city"],
                member["phone"],
                member["mobile"],
                member["notes"],
                date.fromisoformat(member["joined"]) if member["joined"] else None,
                member["identityCardNumber"],
                can_swimm,
                member["status"],
            ]

            for counter, current_parent in enumerate(member["parents"]):
                parent_row_data = [
                    current_parent["name"],
                    current_parent["lastname"],
                    current_parent["email"],
                    current_parent["email2"],
                    current_parent["street"],
                    current_parent["zip_code"],
                    current_parent["city"],
                    current_parent["phone"],
                    current_parent["mobile"],
                    current_parent["notes"],
                ]
                row = row + parent_row_data
                if counter + 1 >= n_parents_to_render:
                    break

            append_safe_row(sheet, row)
        # Save workbook to BytesIO object
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()
