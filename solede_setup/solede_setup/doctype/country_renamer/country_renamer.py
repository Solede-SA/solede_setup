"""
Country Renamer

Rename countries from CSV/Excel file.

Template columns:
- Current Name: Current country name (must exist)
- New Name: New country name
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc

from solede_setup.utils.importer_base import (
    get_file,
    read_file_data,
    validate_columns,
    generate_csv_template,
    download_template_response,
)

# Column configuration
COLUMNS = ["Current Name", "New Name"]
EXPECTED_COLUMNS = 2


class CountryRenamer(Document):
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
            current_name = row[0].strip() if len(row) > 0 else ""
            new_name = row[1].strip() if len(row) > 1 else ""

            if not current_name or not new_name:
                continue

            # Check if country exists
            exists = frappe.db.exists("Country", current_name)

            preview_data.append({
                "current_name": current_name,
                "new_name": new_name,
                "exists": exists,
                "status": "OK" if exists else "Not Found"
            })
        return preview_data
    else:
        return {"show_import_button": 1}


@frappe.whitelist()
def rename_countries(file_name: str) -> dict:
    """Rename countries from file."""
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    renamed = 0
    errors = []

    for row in data:
        current_name = row[0].strip() if len(row) > 0 else ""
        new_name = row[1].strip() if len(row) > 1 else ""

        if not current_name or not new_name:
            continue

        if current_name == new_name:
            continue

        if not frappe.db.exists("Country", current_name):
            errors.append(f"Country '{current_name}' not found")
            continue

        if frappe.db.exists("Country", new_name):
            errors.append(f"Country '{new_name}' already exists")
            continue

        try:
            rename_doc("Country", current_name, new_name, force=True)
            # Update country_name field as well
            frappe.db.set_value("Country", new_name, "country_name", new_name)
            renamed += 1
        except Exception as e:
            errors.append(f"Error renaming '{current_name}': {str(e)}")

    frappe.db.commit()

    result = {
        "success": True,
        "message": _("{0} countries renamed").format(renamed),
        "renamed": renamed
    }

    if errors:
        result["errors"] = errors

    return result


@frappe.whitelist()
def get_all_countries() -> list:
    """Get all countries for reference."""
    return frappe.get_all(
        "Country",
        fields=["name", "country_name", "code"],
        order_by="name"
    )


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["Italy", "Italia"],
        ["Germany", "Germania"],
        ["France", "Francia"],
        ["Spain", "Spagna"],
        ["United States", "Stati Uniti"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Country Renamer")
