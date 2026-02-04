"""
Country Importer

Delete all countries and import from CSV/Excel file.

Template columns:
- Name: Country name (required)
- Code: ISO country code (e.g., IT, DE, FR)
- Date Format: Date format (e.g., dd-mm-yyyy)
- Time Format: Time format (e.g., HH:mm:ss)
- Time Zones: Time zones separated by newline
"""

import frappe
from frappe import _
from frappe.model.document import Document

from solede_setup.utils.importer_base import (
    get_file,
    read_file_data,
    validate_columns,
    generate_csv_template,
    download_template_response,
)

# Column configuration
COLUMNS = ["Name", "Code", "Date Format", "Time Format", "Time Zones"]
EXPECTED_COLUMNS = 5


class CountryImporter(Document):
    def validate(self):
        if self.import_file:
            get_preview_data(file_name=self.import_file, for_validate=1)


@frappe.whitelist()
def get_preview_data(file_name: str = None, for_validate: int = 0) -> list | dict:
    """Get preview data for display."""
    from frappe.utils import cint

    get_file(file_name)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    if not cint(for_validate):
        preview_data = []
        for row in data:
            name = row[0].strip() if len(row) > 0 and row[0] else ""
            code = row[1].strip() if len(row) > 1 and row[1] else ""
            date_format = row[2].strip() if len(row) > 2 and row[2] else ""
            time_format = row[3].strip() if len(row) > 3 and row[3] else ""
            time_zones = row[4].strip() if len(row) > 4 and row[4] else ""

            if not name:
                continue

            preview_data.append({
                "name": name,
                "code": code,
                "date_format": date_format,
                "time_format": time_format,
                "time_zones": time_zones,
            })
        return preview_data
    else:
        return {"show_import_button": 1}


@frappe.whitelist()
def import_countries(file_name: str) -> dict:
    """Delete all countries and import from file."""
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    # Delete all existing countries
    frappe.db.delete("Country")

    imported = 0
    errors = []

    for row in data:
        name = row[0].strip() if len(row) > 0 and row[0] else ""
        code = row[1].strip() if len(row) > 1 and row[1] else ""
        date_format = row[2].strip() if len(row) > 2 and row[2] else "dd-mm-yyyy"
        time_format = row[3].strip() if len(row) > 3 and row[3] else "HH:mm:ss"
        time_zones = row[4].strip() if len(row) > 4 and row[4] else ""

        if not name:
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Country",
                "country_name": name,
                "code": code,
                "date_format": date_format,
                "time_format": time_format,
                "time_zones": time_zones,
            })
            doc.insert(ignore_permissions=True)
            imported += 1
        except Exception as e:
            errors.append(f"Error importing '{name}': {str(e)}")

    frappe.db.commit()

    result = {
        "success": True,
        "message": _("{0} countries imported").format(imported),
        "imported": imported
    }

    if errors:
        result["errors"] = errors

    return result


@frappe.whitelist()
def get_current_countries_count() -> int:
    """Get count of current countries."""
    return frappe.db.count("Country")


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["Italia", "IT", "dd-mm-yyyy", "HH:mm:ss", "Europe/Rome"],
        ["Germania", "DE", "dd.mm.yyyy", "HH:mm:ss", "Europe/Berlin"],
        ["Francia", "FR", "dd/mm/yyyy", "HH:mm:ss", "Europe/Paris"],
        ["Spagna", "ES", "dd/mm/yyyy", "HH:mm:ss", "Europe/Madrid"],
        ["Svizzera", "CH", "dd.mm.yyyy", "HH:mm:ss", "Europe/Zurich"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Country Importer")
